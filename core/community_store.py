from __future__ import annotations

import json
import re
import sqlite3
import tempfile
import zlib
from datetime import datetime
from pathlib import Path
from typing import Any

import msgpack

from .paths import DEFAULT_COMMUNITY_DIR, DEFAULT_COMMUNITY_SQLITE_PATH


_POST_URL_ID_RE = re.compile(r"/community/posts/(?P<post_id>\d+)-")


def candidate_export_files() -> list[Path]:
    patterns = ("WQPCommunityState_*.json", "WQPCommunityState_*.wqcs")
    roots = [
        DEFAULT_COMMUNITY_DIR,
        Path.home() / "Downloads",
        Path(r"U:\Project\MainCode\3.Work\WQB\WebDataScope-0.9.3"),
    ]
    candidates: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for pattern in patterns:
            candidates.extend(root.glob(pattern))
    unique = {path.resolve(): path for path in candidates if path.is_file()}
    return sorted(unique.values(), key=lambda path: path.stat().st_mtime, reverse=True)


def export_community_storage(
    *,
    source_path: str | Path | None = None,
    sqlite_path: str | Path | None = None,
    export_json: bool = False,
) -> dict[str, Any]:
    source_file = _resolve_source_file(source_path)
    payload, source_format = _load_payload(source_file)
    sqlite_target = Path(sqlite_path) if sqlite_path else DEFAULT_COMMUNITY_SQLITE_PATH
    counts = write_sqlite(payload, sqlite_target)

    raw_json_path = None
    if export_json:
        raw_json_path = sqlite_target.with_suffix(".json")
        raw_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "source_file": str(source_file),
        "source_format": source_format,
        "sqlite_path": str(sqlite_target),
        "json_path": str(raw_json_path) if raw_json_path else None,
        "payload_stats": payload_stats(payload),
        "counts": counts,
    }


def search_community_storage(
    query: str,
    *,
    sqlite_path: str | Path | None = None,
    scope: str = "all",
    limit: int = 20,
) -> dict[str, Any]:
    db_path = Path(sqlite_path) if sqlite_path else DEFAULT_COMMUNITY_SQLITE_PATH
    if not db_path.exists():
        raise FileNotFoundError(f"Community sqlite dataset not found: {db_path}")
    limit = max(1, min(int(limit), 200))
    scope = scope.lower().strip()
    like = f"%{query}%"
    conn = sqlite3.connect(db_path)
    try:
        result: dict[str, Any] = {
            "sqlite_path": str(db_path),
            "query": query,
            "scope": scope,
            "forum_topics": [],
            "forum_comments": [],
            "docs_articles": [],
        }
        if scope in ("all", "forum", "topics"):
            cur = conn.execute(
                """
                SELECT
                    t.community_id,
                    fc.title AS community_title,
                    t.topic_id,
                    t.title,
                    t.url,
                    t.comment_num,
                    t.last_crawled_at
                FROM forum_topics t
                LEFT JOIN forum_communities fc
                  ON fc.community_id = t.community_id
                WHERE COALESCE(t.title, '') LIKE ?
                   OR COALESCE(t.post_content, '') LIKE ?
                LIMIT ?
                """,
                (like, like, limit),
            )
            result["forum_topics"] = row_dicts(cur)
        if scope in ("all", "forum", "comments"):
            cur = conn.execute(
                """
                SELECT
                    c.community_id,
                    fc.title AS community_title,
                    c.topic_id,
                    c.comment_id,
                    c.author,
                    c.comment_time,
                    c.vote_num
                FROM forum_comments c
                LEFT JOIN forum_communities fc
                  ON fc.community_id = c.community_id
                WHERE COALESCE(c.author, '') LIKE ?
                   OR COALESCE(c.comment_content, '') LIKE ?
                LIMIT ?
                """,
                (like, like, limit),
            )
            result["forum_comments"] = row_dicts(cur)
        if scope in ("all", "docs", "articles"):
            cur = conn.execute(
                """
                SELECT a.category_id, a.section_id, a.article_id, a.title, a.url, a.author, a.datetime
                FROM docs_articles a
                WHERE COALESCE(a.title, '') LIKE ?
                   OR COALESCE(a.author, '') LIKE ?
                   OR COALESCE(a.article_content, '') LIKE ?
                LIMIT ?
                """,
                (like, like, like, limit),
            )
            result["docs_articles"] = row_dicts(cur)
        return result
    finally:
        conn.close()


def payload_stats(payload: dict[str, Any]) -> dict[str, int]:
    by_community = payload.get("byCommunity") or {}
    by_category = payload.get("byCategory") or {}
    topic_count = 0
    comment_count = 0
    for community in by_community.values():
        topics = (community or {}).get("topics") or {}
        topic_count += len(topics)
        for topic in topics.values():
            comment_count += len(((topic or {}).get("comments") or {}))
    article_count = 0
    section_count = 0
    for category in by_category.values():
        sections = (category or {}).get("sections") or {}
        section_count += len(sections)
        for section in sections.values():
            article_count += len(((section or {}).get("articles") or {}))
    return {
        "communities": len(by_community),
        "topics": topic_count,
        "comments": comment_count,
        "categories": len(by_category),
        "sections": section_count,
        "articles": article_count,
    }


def write_sqlite(payload: dict[str, Any], sqlite_path: Path) -> dict[str, int]:
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = tempfile.NamedTemporaryFile(prefix="wqb_forum_build_", suffix=".sqlite3", delete=False)
    temp_path = Path(temp_file.name)
    temp_file.close()
    conn = sqlite3.connect(temp_path)
    try:
        init_sqlite_schema(conn)
        communities, topics, comments = flatten_forum_topics(payload)
        categories, sections, articles = flatten_docs(payload)
        conn.executemany(
            """
            INSERT OR REPLACE INTO forum_communities (
                community_id, title, url, posts, followers, raw_json
            ) VALUES (
                :community_id, :title, :url, :posts, :followers, :raw_json
            )
            """,
            communities,
        )
        conn.executemany(
            """
            INSERT OR REPLACE INTO forum_topics (
                community_id, topic_id, title, url, comment_num, post_content, last_crawled_at, raw_json
            ) VALUES (
                :community_id, :topic_id, :title, :url, :comment_num, :post_content, :last_crawled_at, :raw_json
            )
            """,
            topics,
        )
        conn.executemany(
            """
            INSERT OR REPLACE INTO forum_comments (
                community_id, topic_id, comment_id, author, comment_time, vote_num, comment_content, raw_json
            ) VALUES (
                :community_id, :topic_id, :comment_id, :author, :comment_time, :vote_num, :comment_content, :raw_json
            )
            """,
            comments,
        )
        conn.executemany(
            """
            INSERT OR REPLACE INTO docs_categories (
                category_id, title, url, last_crawled_at, raw_json
            ) VALUES (
                :category_id, :title, :url, :last_crawled_at, :raw_json
            )
            """,
            categories,
        )
        conn.executemany(
            """
            INSERT OR REPLACE INTO docs_sections (
                category_id, section_id, title, url
            ) VALUES (
                :category_id, :section_id, :title, :url
            )
            """,
            sections,
        )
        conn.executemany(
            """
            INSERT OR REPLACE INTO docs_articles (
                category_id, section_id, article_id, title, url, author, datetime, article_content,
                last_crawled_at, raw_json
            ) VALUES (
                :category_id, :section_id, :article_id, :title, :url, :author, :datetime,
                :article_content, :last_crawled_at, :raw_json
            )
            """,
            articles,
        )
        rebuild_fts(conn)
        conn.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
            ("community_state_json", json.dumps(payload, ensure_ascii=False)),
        )
        conn.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
            ("exported_at", json.dumps({"value": datetime.now().isoformat()})),
        )
        conn.commit()
        conn.close()
        sqlite_path.write_bytes(temp_path.read_bytes())
        return {
            "forum_communities": len(communities),
            "forum_topics": len(topics),
            "forum_comments": len(comments),
            "docs_categories": len(categories),
            "docs_sections": len(sections),
            "docs_articles": len(articles),
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass
        for suffix in ("-shm", "-wal", "-journal"):
            Path(f"{temp_path}{suffix}").unlink(missing_ok=True)
        temp_path.unlink(missing_ok=True)


def init_sqlite_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode=DELETE;
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS forum_communities (
            community_id TEXT PRIMARY KEY,
            title TEXT,
            url TEXT,
            posts INTEGER,
            followers INTEGER,
            raw_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS forum_topics (
            community_id TEXT NOT NULL,
            topic_id TEXT NOT NULL,
            title TEXT,
            url TEXT,
            comment_num INTEGER,
            post_content TEXT,
            last_crawled_at TEXT,
            raw_json TEXT NOT NULL,
            PRIMARY KEY (community_id, topic_id)
        );
        CREATE TABLE IF NOT EXISTS forum_comments (
            community_id TEXT NOT NULL,
            topic_id TEXT NOT NULL,
            comment_id TEXT NOT NULL,
            author TEXT,
            comment_time TEXT,
            vote_num INTEGER,
            comment_content TEXT,
            raw_json TEXT NOT NULL,
            PRIMARY KEY (community_id, topic_id, comment_id)
        );
        CREATE TABLE IF NOT EXISTS docs_categories (
            category_id TEXT PRIMARY KEY,
            title TEXT,
            url TEXT,
            last_crawled_at TEXT,
            raw_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS docs_sections (
            category_id TEXT NOT NULL,
            section_id TEXT NOT NULL,
            title TEXT,
            url TEXT,
            PRIMARY KEY (category_id, section_id)
        );
        CREATE TABLE IF NOT EXISTS docs_articles (
            category_id TEXT NOT NULL,
            section_id TEXT NOT NULL,
            article_id TEXT NOT NULL,
            title TEXT,
            url TEXT,
            author TEXT,
            datetime TEXT,
            article_content TEXT,
            last_crawled_at TEXT,
            raw_json TEXT NOT NULL,
            PRIMARY KEY (category_id, section_id, article_id)
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS forum_topics_fts USING fts5(
            community_id,
            topic_id,
            title,
            post_content,
            content=''
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS forum_comments_fts USING fts5(
            community_id,
            topic_id,
            comment_id,
            author,
            comment_content,
            content=''
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS docs_articles_fts USING fts5(
            category_id,
            section_id,
            article_id,
            title,
            author,
            article_content,
            content=''
        );
        """
    )


def rebuild_fts(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM forum_topics_fts")
    conn.execute("DELETE FROM forum_comments_fts")
    conn.execute("DELETE FROM docs_articles_fts")
    conn.execute(
        """
        INSERT INTO forum_topics_fts(rowid, community_id, topic_id, title, post_content)
        SELECT rowid, community_id, topic_id, COALESCE(title, ''), COALESCE(post_content, '')
        FROM forum_topics
        """
    )
    conn.execute(
        """
        INSERT INTO forum_comments_fts(rowid, community_id, topic_id, comment_id, author, comment_content)
        SELECT rowid, community_id, topic_id, comment_id, COALESCE(author, ''), COALESCE(comment_content, '')
        FROM forum_comments
        """
    )
    conn.execute(
        """
        INSERT INTO docs_articles_fts(rowid, category_id, section_id, article_id, title, author, article_content)
        SELECT rowid, category_id, section_id, article_id, COALESCE(title, ''), COALESCE(author, ''), COALESCE(article_content, '')
        FROM docs_articles
        """
    )


def flatten_forum_topics(
    payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    communities: list[dict[str, Any]] = []
    topics: list[dict[str, Any]] = []
    comments: list[dict[str, Any]] = []
    for community_id, community in (payload.get("byCommunity") or {}).items():
        community = community or {}
        reported_posts = int(community.get("posts") or 0)
        communities.append(
            {
                "community_id": str(community_id),
                "title": community.get("title"),
                "url": community.get("url"),
                "posts": reported_posts,
                "followers": int(community.get("followers") or 0),
                "raw_json": json.dumps(community, ensure_ascii=False),
            }
        )
        topic_map = (community.get("topics") or {}) or {}
        use_url_canonical = _should_use_url_canonical(topic_map, reported_posts)
        for topic_id, topic in topic_map.items():
            topic = topic or {}
            actual_topic_id = _canonical_topic_id(topic_id, topic, use_url_canonical)
            topics.append(
                {
                    "community_id": str(community_id),
                    "topic_id": actual_topic_id,
                    "title": topic.get("title"),
                    "url": topic.get("url"),
                    "comment_num": int(topic.get("commentNum") or 0),
                    "post_content": topic.get("postContent"),
                    "last_crawled_at": topic.get("lastCrawledAt"),
                    "raw_json": json.dumps(topic, ensure_ascii=False),
                }
            )
            for comment_id, comment in ((topic.get("comments") or {}) or {}).items():
                comment = comment or {}
                comments.append(
                    {
                        "community_id": str(community_id),
                        "topic_id": actual_topic_id,
                        "comment_id": str(comment_id),
                        "author": comment.get("author"),
                        "comment_time": comment.get("commentTimeDatetime"),
                        "vote_num": int(comment.get("voteNum") or 0),
                        "comment_content": comment.get("commentContent"),
                        "raw_json": json.dumps(comment, ensure_ascii=False),
                    }
                )
    return communities, topics, comments


def flatten_docs(
    payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    categories: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    articles: list[dict[str, Any]] = []
    for category_id, category in (payload.get("byCategory") or {}).items():
        category = category or {}
        categories.append(
            {
                "category_id": str(category_id),
                "title": category.get("title"),
                "url": category.get("url"),
                "last_crawled_at": category.get("lastCrawledAt") or payload.get("byCategoryTime"),
                "raw_json": json.dumps(category, ensure_ascii=False),
            }
        )
        for section_id, section in ((category.get("sections") or {}) or {}).items():
            section = section or {}
            sections.append(
                {
                    "category_id": str(category_id),
                    "section_id": str(section_id),
                    "title": section.get("title"),
                    "url": section.get("url"),
                }
            )
            for article_id, article in ((section.get("articles") or {}) or {}).items():
                article = article or {}
                articles.append(
                    {
                        "category_id": str(category_id),
                        "section_id": str(section_id),
                        "article_id": str(article_id),
                        "title": article.get("title"),
                        "url": article.get("url"),
                        "author": article.get("author"),
                        "datetime": article.get("datetime"),
                        "article_content": article.get("articleContent"),
                        "last_crawled_at": article.get("lastCrawledAt"),
                        "raw_json": json.dumps(article, ensure_ascii=False),
                    }
                )
    return categories, sections, articles


def row_dicts(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    cols = [description[0] for description in cursor.description]
    return [dict(zip(cols, row, strict=False)) for row in cursor.fetchall()]


def _resolve_source_file(source_path: str | Path | None) -> Path:
    if source_path:
        path = Path(source_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Community export file not found: {path}")
        return path
    candidates = candidate_export_files()
    if not candidates:
        raise FileNotFoundError("No WQPCommunityState_*.json or *.wqcs export file found.")
    return candidates[0]


def _load_payload(source_file: Path) -> tuple[dict[str, Any], str]:
    suffix = source_file.suffix.lower()
    if suffix == ".json":
        payload = json.loads(source_file.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Community export JSON must decode to dict: {source_file}")
        return payload, "json"
    if suffix == ".wqcs":
        payload = msgpack.loads(zlib.decompress(source_file.read_bytes()), raw=False)
        if not isinstance(payload, dict):
            raise ValueError(f"Community export WQCS must decode to dict: {source_file}")
        return payload, "wqcs"
    raise ValueError(f"Unsupported community export format: {source_file}")


def _should_use_url_canonical(topic_map: dict[str, Any], reported_posts: int) -> bool:
    raw_ids: set[str] = set()
    url_ids: set[str] = set()
    for topic_id, topic in topic_map.items():
        topic = topic or {}
        raw_ids.add(str(topic_id))
        url_ids.add(_canonical_topic_id(topic_id, topic, True))
    if reported_posts <= 0:
        return True
    return abs(len(url_ids) - reported_posts) <= abs(len(raw_ids) - reported_posts)


def _canonical_topic_id(topic_id: Any, topic: dict[str, Any], use_url_canonical: bool) -> str:
    if not use_url_canonical:
        return str(topic_id)
    topic_url = topic.get("url")
    if isinstance(topic_url, str):
        match = _POST_URL_ID_RE.search(topic_url)
        if match:
            return match.group("post_id")
    return str(topic.get("id") or topic_id)
