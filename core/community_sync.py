from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from .community_client import CommunityClient, CommunityError, community_resource, community_url, next_page_url
from .community_sqlite import CommunityStore, encode, fingerprint, now_iso, writer_lock


def timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def summarize_run(store: CommunityStore, run_id: str) -> dict[str, Any]:
    run = dict(store.connection.execute("SELECT * FROM community_sync_runs WHERE run_id=?", (run_id,)).fetchone())
    counts = dict(store.connection.execute("SELECT COALESCE(outcome,status),COUNT(*) FROM community_sync_items WHERE run_id=? GROUP BY COALESCE(outcome,status)", (run_id,)).fetchall())
    state = store.connection.execute("SELECT watermark FROM community_sync_state WHERE scope=?", (run["scope"],)).fetchone()
    return {"ok": run["status"] in ("COMPLETE", "PAUSED"), "sqlite_path": str(store.path), "run_id": run_id, "status": run["status"], "pages": run["pages"], "counts": counts, "watermark": state[0] if state else None, "resumable": run["status"] != "COMPLETE", "error": run["error"]}


def _start_run(store: CommunityStore, *, topic_id: str | None, since: str | None, overlap_hours: float, refresh_comments_days: float, reconcile: bool) -> dict[str, Any]:
    scope = "topic:" + topic_id if topic_id else "all"
    active = store.connection.execute("SELECT * FROM community_sync_runs WHERE scope=? AND status != 'COMPLETE' ORDER BY started_at DESC LIMIT 1", (scope,)).fetchone()
    if active:
        options = json.loads(active["options_json"])
        if since is not None and options["since"] != timestamp(since).isoformat() or reconcile and not options["reconcile"]:
            raise ValueError("An unfinished sync exists for this scope; resume it with its original since/reconcile settings")
        with store.connection:
            store.connection.execute("UPDATE community_sync_runs SET status='RUNNING',error=NULL,updated_at=? WHERE run_id=?", (now_iso(), active["run_id"]))
        return dict(store.connection.execute("SELECT * FROM community_sync_runs WHERE run_id=?", (active["run_id"],)).fetchone())
    state = store.connection.execute("SELECT watermark FROM community_sync_state WHERE scope=?", (scope,)).fetchone()
    lower = timestamp(since).isoformat() if since else None
    if lower is None and state and state["watermark"] and not reconcile:
        lower = (timestamp(state["watermark"]) - timedelta(hours=overlap_hours)).isoformat()
    if lower and timestamp(lower) > datetime.now(timezone.utc):
        raise ValueError("since must not be in the future")
    path = f"/api/v2/community/topics/{topic_id}/posts.json" if topic_id else "/api/v2/community/posts.json"
    options = {"since": timestamp(since).isoformat() if since else None, "overlap_hours": overlap_hours, "refresh_comments_days": refresh_comments_days, "reconcile": reconcile, "index_path": path}
    run_id = "com_" + uuid4().hex
    started = now_iso()
    with store.connection:
        store.connection.execute(
            "INSERT INTO community_sync_runs (run_id,scope,status,started_at,updated_at,lower_bound,next_url,params_json,options_json) VALUES (?,?,?,?,?,?,?,?,?)",
            (run_id, scope, "RUNNING", started, started, lower, community_url(path), encode({"sort_by": "updated_at", "sort_order": "desc", "page[size]": 100, "include": "users,topics"}), encode(options)),
        )
    return dict(store.connection.execute("SELECT * FROM community_sync_runs WHERE run_id=?", (run_id,)).fetchone())


def _unchanged(store: CommunityStore, post: dict[str, Any], refresh_days: float) -> bool:
    metadata = store.connection.execute("SELECT * FROM community_sync_posts WHERE post_id=?", (str(post["id"]),)).fetchone()
    if metadata is not None:
        return metadata["content_hash"] == fingerprint(post) and timestamp(metadata["comments_checked_at"]) >= datetime.now(timezone.utc) - timedelta(days=refresh_days)
    existing = store.find_post(str(post["id"]))
    if existing is None or not existing["last_crawled_at"]:
        return False
    local_count = store.connection.execute("SELECT COUNT(*) FROM forum_comments WHERE community_id=? AND topic_id=?", (existing["community_id"], str(post["id"]))).fetchone()[0]
    try:
        crawled = timestamp(existing["last_crawled_at"])
        return (
            crawled >= timestamp(post["updated_at"])
            and crawled >= datetime.now(timezone.utc) - timedelta(days=refresh_days)
            and existing["community_id"] == str(post["topic_id"])
            and existing["post_content"] == post["details"]
            and existing["title"] == post["title"]
            and local_count == int(post.get("comment_count", 0))
        )
    except (ValueError, TypeError):
        return False


def _finish_item(store: CommunityStore, client: CommunityClient, run: dict[str, Any], item: Any) -> None:
    payload = json.loads(item["payload_json"])
    post = payload["post"]
    options = json.loads(run["options_json"])
    if _unchanged(store, post, options["refresh_comments_days"]):
        with store.connection:
            store.connection.execute("UPDATE community_sync_items SET status='DONE',outcome='unchanged' WHERE run_id=? AND post_id=?", (run["run_id"], item["post_id"]))
        return
    users = payload["users"]
    try:
        comments, comment_users = client.comments(str(post["id"])) if int(post.get("comment_count", 0)) else ([], {})
    except CommunityError as error:
        if error.status_code != 404:
            raise
        try:
            latest = client.get_json(f"/api/v2/community/posts/{post['id']}.json", params={"include": "users,topics"})
        except CommunityError as confirmation:
            if confirmation.status_code != 404:
                raise
            with store.connection:
                store.connection.execute("UPDATE community_sync_items SET status='DONE',outcome='unavailable' WHERE run_id=? AND post_id=?", (run["run_id"], item["post_id"]))
            return
        post = latest["post"]
        comments, comment_users = client.comments(str(post["id"])) if int(post.get("comment_count", 0)) else ([], {})
        users.update({str(user["id"]): user for user in latest.get("users", [])})
        payload["topic"] = next((topic for topic in latest.get("topics", []) if str(topic["id"]) == str(post["topic_id"])), None)
    users.update(comment_users)
    if len(comments) < int(post.get("comment_count", 0)):
        latest = client.get_json(f"/api/v2/community/posts/{post['id']}.json", params={"include": "users,topics"})
        post = latest["post"]
        users.update({str(user["id"]): user for user in latest.get("users", [])})
        payload["topic"] = next((topic for topic in latest.get("topics", []) if str(topic["id"]) == str(post["topic_id"])), None)
        if len(comments) < int(post.get("comment_count", 0)):
            raise CommunityError("Comment pagination returned fewer visible comments than the post reports; the item remains pending")
    outcome = "updated" if store.find_post(str(post["id"])) else "inserted"
    with store.connection:
        store.save_post(post, users, payload.get("topic"), comments, checked_at=now_iso())
        store.connection.execute("UPDATE community_sync_items SET status='DONE',outcome=? WHERE run_id=? AND post_id=?", (outcome, run["run_id"], item["post_id"]))


def sync_storage(
    path: Path,
    client: CommunityClient,
    *,
    topic_id: str | None = None,
    since: str | None = None,
    overlap_hours: float = 48,
    refresh_comments_days: float = 7,
    max_pages: int = 0,
    reconcile: bool = False,
    emit: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    if overlap_hours < 0 or refresh_comments_days < 0 or max_pages < 0:
        raise ValueError("Sync overlap, comment refresh period and page budget must not be negative")
    if topic_id is not None and not topic_id.isdecimal():
        raise ValueError("topic_id must be numeric")
    with writer_lock(path):
        store = CommunityStore(path)
        run_id: str | None = None
        try:
            run = _start_run(store, topic_id=topic_id, since=since, overlap_hours=overlap_hours, refresh_comments_days=refresh_comments_days, reconcile=reconcile)
            run_id = run["run_id"]
            pages_this_call = 0
            seen_pages: set[str] = set()
            while True:
                pending = store.connection.execute("SELECT * FROM community_sync_items WHERE run_id=? AND status='PENDING' ORDER BY rowid", (run_id,)).fetchall()
                for item in pending:
                    _finish_item(store, client, run, item)
                run = dict(store.connection.execute("SELECT * FROM community_sync_runs WHERE run_id=?", (run_id,)).fetchone())
                if run["discovery_done"]:
                    with store.connection:
                        store.connection.execute("UPDATE community_sync_runs SET status='COMPLETE',updated_at=? WHERE run_id=?", (now_iso(), run_id))
                        store.connection.execute("INSERT INTO community_sync_state VALUES (?,?,?) ON CONFLICT(scope) DO UPDATE SET watermark=excluded.watermark,last_run_id=excluded.last_run_id", (run["scope"], run["started_at"], run_id))
                    return summarize_run(store, run_id)
                if max_pages and pages_this_call >= max_pages:
                    with store.connection:
                        store.connection.execute("UPDATE community_sync_runs SET status='PAUSED',updated_at=? WHERE run_id=?", (now_iso(), run_id))
                    return summarize_run(store, run_id)
                address = run["next_url"]
                if not address or address in seen_pages:
                    raise CommunityError("Forum post pagination repeated or omitted a page")
                seen_pages.add(address)
                body = client.get_json(address, params=json.loads(run["params_json"]) if run["params_json"] else None)
                posts = body.get("posts")
                if not isinstance(posts, list):
                    raise CommunityError("Forum list response is missing its posts array")
                required = {"id", "topic_id", "updated_at", "title", "details"}
                if any(not isinstance(post, dict) or not required <= post.keys() for post in posts):
                    raise CommunityError("Forum list is missing required post fields")
                times = [timestamp(post["updated_at"]) for post in posts]
                if times != sorted(times, reverse=True):
                    raise CommunityError("Forum did not honor descending updated_at ordering; completion boundary was not advanced")
                lower = timestamp(run["lower_bound"]) if run["lower_bound"] else None
                selected = [post for post in posts if lower is None or timestamp(post["updated_at"]) >= lower]
                following = next_page_url(body)
                index_path = json.loads(run["options_json"])["index_path"]
                if following and community_resource(following) != community_resource(index_path):
                    raise CommunityError("Forum posts next page changed resource")
                done = following is None or bool(lower and any(updated < lower for updated in times))
                users = {str(user["id"]): user for user in body.get("users", [])}
                topics = {str(topic["id"]): topic for topic in body.get("topics", [])}
                with store.connection:
                    for post in selected:
                        payload = {"post": post, "users": users, "topic": topics.get(str(post["topic_id"]))}
                        store.connection.execute("INSERT INTO community_sync_items (run_id,post_id,payload_json) VALUES (?,?,?) ON CONFLICT(run_id,post_id) DO NOTHING", (run_id, str(post["id"]), encode(payload)))
                    store.connection.execute("UPDATE community_sync_runs SET next_url=?,params_json=NULL,pages=pages+1,discovery_done=?,updated_at=? WHERE run_id=?", (following, int(done), now_iso(), run_id))
                pages_this_call += 1
                if emit:
                    emit({"event": "page_saved", "run_id": run_id, "posts": len(selected), "page": run["pages"] + 1})
        except Exception as error:
            if run_id is not None:
                with store.connection:
                    store.connection.execute("UPDATE community_sync_runs SET status='FAILED',error=?,updated_at=? WHERE run_id=?", (str(error), now_iso(), run_id))
                if emit:
                    emit({"event": "sync_failed", "run_id": run_id, "error_type": type(error).__name__})
            raise
        finally:
            store.close()
