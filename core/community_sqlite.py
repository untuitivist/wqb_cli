from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .community_store import flatten_docs, flatten_forum_topics, init_sqlite_schema, load_community_export


TABLE_KEYS = {
    "forum_communities": ("community_id",),
    "forum_topics": ("community_id", "topic_id"),
    "forum_comments": ("community_id", "topic_id", "comment_id"),
    "docs_categories": ("category_id",),
    "docs_sections": ("category_id", "section_id"),
    "docs_articles": ("category_id", "section_id", "article_id"),
}
FTS_COLUMNS = {
    "forum_topics": ("community_id", "topic_id", "title", "post_content"),
    "forum_comments": ("community_id", "topic_id", "comment_id", "author", "comment_content"),
    "docs_articles": ("category_id", "section_id", "article_id", "title", "author", "article_content"),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return hashlib.sha256(encode(value).encode("utf-8")).hexdigest()


def readonly_connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def writer_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.with_name(path.name + ".sync.lock").open("a+b")
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise RuntimeError("Another sqlitecom writer is using this database") from None
    try:
        yield
    finally:
        handle.close()


class CommunityStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.connection = sqlite3.connect(path, timeout=30)
        self.connection.row_factory = sqlite3.Row
        init_sqlite_schema(self.connection)
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS community_sync_state (
                scope TEXT PRIMARY KEY, watermark TEXT, last_run_id TEXT
            );
            CREATE TABLE IF NOT EXISTS community_sync_runs (
                run_id TEXT PRIMARY KEY, scope TEXT NOT NULL, status TEXT NOT NULL,
                started_at TEXT NOT NULL, updated_at TEXT NOT NULL, lower_bound TEXT,
                next_url TEXT, params_json TEXT, pages INTEGER NOT NULL DEFAULT 0,
                discovery_done INTEGER NOT NULL DEFAULT 0, error TEXT, options_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS community_sync_items (
                run_id TEXT NOT NULL, post_id TEXT NOT NULL, payload_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING', outcome TEXT,
                PRIMARY KEY(run_id, post_id)
            );
            CREATE TABLE IF NOT EXISTS community_sync_posts (
                post_id TEXT PRIMARY KEY, source_updated_at TEXT NOT NULL,
                content_hash TEXT NOT NULL, comments_checked_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS community_row_history (
                table_name TEXT NOT NULL, snapshot_hash TEXT NOT NULL,
                post_id TEXT NOT NULL, canonical_community_id TEXT NOT NULL,
                archived_at TEXT NOT NULL, snapshot_json TEXT NOT NULL,
                PRIMARY KEY(table_name, snapshot_hash)
            );
            CREATE INDEX IF NOT EXISTS community_sync_items_pending ON community_sync_items(run_id, status);
            CREATE INDEX IF NOT EXISTS forum_topics_post_id ON forum_topics(topic_id);
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def upsert(self, table: str, values: dict[str, Any]) -> bool:
        keys = TABLE_KEYS[table]
        columns = tuple(values)
        if not set(columns) <= {row[1] for row in self.connection.execute(f"PRAGMA table_info({table})")}:
            raise ValueError("Unexpected community storage column")
        where = " AND ".join(f"{key}=?" for key in keys)
        existing = self.connection.execute(f"SELECT rowid, * FROM {table} WHERE {where}", tuple(values[key] for key in keys)).fetchone()
        changed = existing is None or any(existing[column] != values[column] for column in columns)
        if not changed:
            return False
        fts_columns = FTS_COLUMNS.get(table)
        if existing is not None and fts_columns:
            self._fts_delete(table, existing)
        updates = ",".join(f"{column}=excluded.{column}" for column in columns if column not in keys)
        self.connection.execute(
            f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for column in columns)}) "
            f"ON CONFLICT({','.join(keys)}) DO UPDATE SET {updates}",
            tuple(values[column] for column in columns),
        )
        if fts_columns:
            current = self.connection.execute(f"SELECT rowid, * FROM {table} WHERE {where}", tuple(values[key] for key in keys)).fetchone()
            self._fts_insert(table, current)
        return True

    def _fts_delete(self, table: str, record: sqlite3.Row) -> None:
        columns = FTS_COLUMNS[table]
        name = table + "_fts"
        self.connection.execute(
            f"INSERT INTO {name}({name},rowid,{','.join(columns)}) VALUES ('delete',?,{','.join('?' for column in columns)})",
            (record["rowid"], *(record[column] or "" for column in columns)),
        )

    def _fts_insert(self, table: str, record: sqlite3.Row) -> None:
        columns = FTS_COLUMNS[table]
        self.connection.execute(
            f"INSERT INTO {table}_fts(rowid,{','.join(columns)}) VALUES (?,{','.join('?' for column in columns)})",
            (record["rowid"], *(record[column] or "" for column in columns)),
        )

    def find_post(self, post_id: str, community_id: str | None = None) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT rowid,* FROM forum_topics WHERE topic_id=? "
            "ORDER BY (community_id=?) DESC, "
            "julianday(COALESCE(json_extract(raw_json,'$.api.updated_at'),"
            "json_extract(raw_json,'$.updatedAt'),last_crawled_at)) DESC,community_id LIMIT 1",
            (post_id, community_id),
        ).fetchone()

    def move_post(self, post_id: str, community_id: str) -> None:
        existing = self.find_post(post_id, community_id)
        if existing is None:
            return
        rows_by_table = {
            table: self.connection.execute(f"SELECT rowid,* FROM {table} WHERE topic_id=?", (post_id,)).fetchall()
            for table in ("forum_topics", "forum_comments")
        }
        if all(record["community_id"] == community_id for rows in rows_by_table.values() for record in rows):
            return
        for table in ("forum_topics", "forum_comments"):
            rows = rows_by_table[table]
            for record in rows:
                snapshot = {key: record[key] for key in record.keys() if key != "rowid"}
                self.connection.execute(
                    "INSERT OR IGNORE INTO community_row_history VALUES (?,?,?,?,?,?)",
                    (table, fingerprint(snapshot), post_id, community_id, now_iso(), encode(snapshot)),
                )
            if table == "forum_topics":
                selected = [existing]
            else:
                grouped: dict[str, sqlite3.Row] = {}
                for record in rows:
                    previous = grouped.get(record["comment_id"])
                    if previous is None or self._comment_priority(record, community_id) > self._comment_priority(previous, community_id):
                        grouped[record["comment_id"]] = record
                selected = list(grouped.values())
            for record in rows:
                self._fts_delete(table, record)
                self.connection.execute(f"DELETE FROM {table} WHERE rowid=?", (record["rowid"],))
            for record in selected:
                values = {key: record[key] for key in record.keys() if key != "rowid"}
                values["community_id"] = community_id
                self.upsert(table, values)

    @staticmethod
    def _comment_priority(record: sqlite3.Row, community_id: str) -> tuple[float, bool, str]:
        raw = json.loads(record["raw_json"])
        modified = (raw.get("api") or {}).get("updated_at") or raw.get("updatedAt") or record["comment_time"]
        try:
            parsed = datetime.fromisoformat(modified.replace("Z", "+00:00"))
            value = parsed.replace(tzinfo=timezone.utc).timestamp() if parsed.tzinfo is None else parsed.timestamp()
        except (AttributeError, ValueError, TypeError, OverflowError):
            value = float("-inf")
        return value, record["community_id"] == community_id, record["community_id"]

    def save_post(self, post: dict[str, Any], users: dict[str, dict[str, Any]], topic: dict[str, Any] | None, comments: list[dict[str, Any]], *, checked_at: str) -> None:
        post_id = str(post["id"])
        community_id = str(post["topic_id"])
        author = users.get(str(post.get("author_id")), {}).get("name")
        self.move_post(post_id, community_id)
        existing = self.find_post(post_id, community_id)
        previous_raw = json.loads(existing["raw_json"]) if existing else {}
        author = author or previous_raw.get("author") or str(post.get("author_id") or "")
        raw = {**previous_raw, "author": author, "datetime": post.get("created_at"), "updatedAt": post["updated_at"], "voteNum": post.get("vote_sum", 0),
               "title": post["title"], "url": post.get("html_url"), "commentNum": post.get("comment_count", 0), "postContent": post["details"], "lastCrawledAt": checked_at, "api": post}
        raw.pop("comments", None)
        raw["commentsSource"] = "forum_comments"
        if topic:
            self.upsert("forum_communities", {"community_id": community_id, "title": topic.get("name"), "url": topic.get("html_url"), "posts": topic.get("post_count", 0), "followers": topic.get("follower_count", 0), "raw_json": encode(topic)})
        self.upsert("forum_topics", {"community_id": community_id, "topic_id": post_id, "title": post["title"], "url": post.get("html_url"), "comment_num": post.get("comment_count", 0), "post_content": post["details"], "last_crawled_at": checked_at, "raw_json": encode(raw)})
        for comment in comments:
            comment_id = str(comment["id"])
            local_comment = self.connection.execute("SELECT author FROM forum_comments WHERE community_id=? AND topic_id=? AND comment_id=?", (community_id, post_id, comment_id)).fetchone()
            comment_author = users.get(str(comment.get("author_id")), {}).get("name") or (local_comment["author"] if local_comment else None) or str(comment.get("author_id") or "")
            comment_raw = {"author": comment_author, "commentTimeDatetime": comment.get("created_at"), "updatedAt": comment.get("updated_at"), "voteNum": comment.get("vote_sum", 0), "commentContent": comment["body"], "api": comment}
            self.upsert("forum_comments", {"community_id": community_id, "topic_id": post_id, "comment_id": comment_id, "author": comment_author, "comment_time": comment.get("created_at"), "vote_num": comment.get("vote_sum", 0), "comment_content": comment["body"], "raw_json": encode(comment_raw)})
        self.connection.execute(
            "INSERT INTO community_sync_posts VALUES (?,?,?,?) ON CONFLICT(post_id) DO UPDATE SET source_updated_at=excluded.source_updated_at,content_hash=excluded.content_hash,comments_checked_at=excluded.comments_checked_at",
            (post_id, post["updated_at"], fingerprint(post), checked_at),
        )


def import_storage(source: str | None, path: Path) -> dict[str, Any]:
    source_file, payload, source_format = load_community_export(source)
    flattened = (*flatten_forum_topics(payload), *flatten_docs(payload))
    with writer_lock(path):
        store = CommunityStore(path)
        try:
            counts = {}
            retained_posts = set()
            for post in flattened[1]:
                synced = store.connection.execute("SELECT comments_checked_at FROM community_sync_posts WHERE post_id=?", (post["topic_id"],)).fetchone()
                if synced:
                    incoming = post.get("last_crawled_at")
                    try:
                        incoming_time = datetime.fromisoformat(incoming.replace("Z", "+00:00")) if incoming else None
                        if incoming_time is not None and incoming_time.tzinfo is None:
                            incoming_time = incoming_time.replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        incoming_time = None
                    if incoming_time is None or incoming_time <= datetime.fromisoformat(synced["comments_checked_at"]):
                        retained_posts.add(post["topic_id"])
            with store.connection:
                for table, rows in zip(TABLE_KEYS, flattened, strict=True):
                    selected = [row for row in rows if table not in {"forum_topics", "forum_comments"} or row["topic_id"] not in retained_posts]
                    counts[table] = sum(store.upsert(table, row) for row in selected)
                    if table == "forum_topics":
                        store.connection.executemany("DELETE FROM community_sync_posts WHERE post_id=?", ((row["topic_id"],) for row in selected))
                store.connection.execute("INSERT OR REPLACE INTO metadata VALUES (?,?)", ("last_sqlitecom_import", encode({"source": str(source_file), "at": now_iso()})))
            return {"ok": True, "sqlite_path": str(path), "source_file": str(source_file), "source_format": source_format, "changed": counts, "mode": "merge", "retained_newer_posts": len(retained_posts)}
        finally:
            store.close()


def query_storage(path: Path, sql: str, *, parameters: dict[str, Any] | list[Any] | None = None, max_rows: int = 200, timeout: float = 10) -> dict[str, Any]:
    if not 1 <= max_rows <= 10000 or timeout <= 0:
        raise ValueError("max_rows must be 1..10000 and timeout must be positive")
    connection = readonly_connection(path)
    for table in FTS_COLUMNS:
        name = table + "_fts"
        if connection.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone():
            connection.execute(f"SELECT rowid FROM {name} LIMIT 0")
    allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}
    forbidden_functions = {"load_extension", "writefile", "readfile"}

    def authorize(action, first, second, database, source):
        if action == sqlite3.SQLITE_PRAGMA and first == "data_version" and second is None:
            return sqlite3.SQLITE_OK
        if action not in allowed or action == sqlite3.SQLITE_FUNCTION and str(second).lower() in forbidden_functions:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    deadline = time.monotonic() + timeout
    try:
        connection.set_authorizer(authorize)
        connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        cursor = connection.execute(sql, parameters if parameters is not None else {})
        rows = cursor.fetchmany(max_rows + 1)
        return {"ok": True, "sqlite_path": str(path), "columns": [column[0] for column in cursor.description or []], "rows": [list(row) for row in rows[:max_rows]], "row_count": min(len(rows), max_rows), "truncated": len(rows) > max_rows, "read_only": True}
    finally:
        connection.close()


def schema_storage(path: Path) -> dict[str, Any]:
    connection = readonly_connection(path)
    try:
        tables = connection.execute("SELECT name,sql FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        return {"ok": True, "sqlite_path": str(path), "tables": [dict(row) for row in tables]}
    finally:
        connection.close()


def stats_storage(path: Path) -> dict[str, Any]:
    connection = readonly_connection(path)
    try:
        names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts = {table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLE_KEYS if table in names}
        runs = [dict(row) for row in connection.execute("SELECT * FROM community_sync_runs ORDER BY started_at DESC LIMIT 10")] if "community_sync_runs" in names else []
        return {"ok": True, "sqlite_path": str(path), "counts": counts, "runs": runs}
    finally:
        connection.close()


def get_local_post(path: Path, post_id: str) -> dict[str, Any]:
    connection = readonly_connection(path)
    try:
        post = connection.execute("SELECT * FROM forum_topics WHERE topic_id=?", (post_id,)).fetchone()
        if post is None:
            return {"ok": False, "reason": "post_not_found", "post_id": post_id}
        comments = connection.execute("SELECT * FROM forum_comments WHERE community_id=? AND topic_id=? ORDER BY comment_time,comment_id", (post["community_id"], post_id)).fetchall()
        return {"ok": True, "post": dict(post), "comments": [dict(comment) for comment in comments]}
    finally:
        connection.close()


def search_local_storage(path: Path, query: str = "", *, scope: str = "all", author: str | None = None, since: str | None = None, sort: str = "newest", limit: int = 20) -> dict[str, Any]:
    if not 1 <= limit <= 200:
        raise ValueError("Search limit must be 1..200")
    if sort not in {"newest", "updated", "votes"}:
        raise ValueError("Unknown search sort")
    if since is not None:
        datetime.fromisoformat(since.replace("Z", "+00:00"))
    parameters = {"query": "%" + query + "%", "author": author, "since": since, "limit": limit}
    groups = {
        "forum_topics": (scope in {"all", "forum", "topics"}, "topic_id,community_id,title,url,comment_num,post_content", "COALESCE(json_extract(raw_json,'$.author'),'')", "json_extract(raw_json,'$.datetime')", "COALESCE(json_extract(raw_json,'$.api.updated_at'),json_extract(raw_json,'$.updatedAt'),last_crawled_at)", "COALESCE(json_extract(raw_json,'$.voteNum'),0)", "title LIKE :query OR post_content LIKE :query"),
        "forum_comments": (scope in {"all", "forum", "comments"}, "topic_id,community_id,comment_id,comment_content", "author", "comment_time", "COALESCE(json_extract(raw_json,'$.api.updated_at'),json_extract(raw_json,'$.updatedAt'),comment_time)", "vote_num", "comment_content LIKE :query"),
        "docs_articles": (scope in {"all", "docs", "articles"}, "article_id,category_id,section_id,title,url,article_content", "author", "datetime", "last_crawled_at", "0", "title LIKE :query OR article_content LIKE :query"),
    }
    connection = readonly_connection(path)
    try:
        result: dict[str, Any] = {"ok": True, "sqlite_path": str(path), "query": query, "scope": scope, "author": author}
        for table, (enabled, fields, author_sql, created_sql, updated_sql, votes_sql, match) in groups.items():
            result[table] = []
            if not enabled:
                continue
            order_sql = {"newest": created_sql, "updated": updated_sql, "votes": votes_sql}[sort]
            sql = f"SELECT {fields},{author_sql} AS author,{created_sql} AS created_at,{updated_sql} AS updated_at,{votes_sql} AS votes FROM {table} WHERE ({match} OR {author_sql} LIKE :query) AND (:author IS NULL OR {author_sql}=:author) AND (:since IS NULL OR datetime({created_sql})>=datetime(:since)) ORDER BY {order_sql} DESC LIMIT :limit"
            result[table] = [dict(row) for row in connection.execute(sql, parameters)]
        return result
    finally:
        connection.close()
