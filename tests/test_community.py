from __future__ import annotations

import copy
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from wqb_cli.cli import build_parser
from wqb_cli.commands.community import handle_community
from wqb_cli.core.community_client import CommunityClient, CommunityError, community_url, load_community_registry, prepare_community_request
from wqb_cli.core.community_sqlite import CommunityStore, get_local_post, import_storage, query_storage, readonly_connection, search_local_storage, stats_storage, writer_lock
from wqb_cli.core.community_sync import sync_storage


INDEX = "https://support.worldquantbrain.com/api/v2/community/posts.json"
NOW = datetime.now(timezone.utc)


def post(post_id="100", *, updated=None, title="Economic mechanism", count=0, section="10"):
    return {"id": int(post_id), "topic_id": int(section), "author_id": 20, "title": title, "details": "<p>cashflow signal</p>", "created_at": (NOW - timedelta(days=2)).isoformat(), "updated_at": updated or (NOW - timedelta(hours=1)).isoformat(), "comment_count": count, "vote_sum": 3, "html_url": "https://support.worldquantbrain.com/hc/en-us/community/posts/" + post_id}


def page(posts, next_url=None):
    return {"posts": posts, "next_page": next_url, "users": [{"id": 20, "name": "JL40454"}], "topics": [{"id": 10, "name": "Research", "post_count": 2}]}


def comment(post_id="100", comment_id="400", body="Useful explanation"):
    return {"id": int(comment_id), "post_id": int(post_id), "author_id": 20, "body": body, "created_at": (NOW - timedelta(hours=2)).isoformat(), "updated_at": (NOW - timedelta(hours=1)).isoformat(), "vote_sum": 1}


class ForumFixture:
    def __init__(self, pages, comments=None):
        self.pages = pages
        self.comment_map = comments or {}
        self.requests = []
        self.comment_calls = []
        self.fail_comments = False

    def get_json(self, address, *, params=None):
        self.requests.append((address, params))
        return copy.deepcopy(self.pages[address])

    def comments(self, post_id):
        self.comment_calls.append(post_id)
        if self.fail_comments:
            raise CommunityError("temporary comment failure")
        return copy.deepcopy(self.comment_map.get(post_id, [])), {"20": {"id": 20, "name": "JL40454"}}


def response(status, body=None, headers=None):
    reply = requests.Response()
    reply.status_code = status
    reply._content = json.dumps(body).encode("utf-8") if body is not None else b""
    reply.headers.update({"Content-Type": "application/json", **(headers or {})})
    return reply


class CommunityTransportTests(unittest.TestCase):
    def make_client(self, replies):
        session = Mock()
        session.request.side_effect = replies
        client = CommunityClient(session=session, brain_client=Mock(), sleeper=Mock())
        client.authenticated = True
        return client, session

    def test_read_429_honors_retry_after(self):
        client, session = self.make_client([response(429, {"error": "limited"}, {"Retry-After": "3"}), response(200, {"posts": []})])
        result = client.call("GET", INDEX)
        self.assertTrue(result["ok"])
        self.assertEqual(result["response"]["retries"], 1)
        client.sleeper.assert_called_once_with(3)
        self.assertEqual(session.request.call_count, 2)

    def test_read_retry_budget_is_bounded(self):
        client, session = self.make_client([response(429, {}, {"Retry-After": "999"})])
        result = client.call("GET", INDEX)
        self.assertFalse(result["ok"])
        self.assertEqual(session.request.call_count, 1)
        client.sleeper.assert_not_called()

    def test_unknown_write_is_never_replayed(self):
        client, session = self.make_client([requests.Timeout("secret URL must not be included")])
        client.csrf_token = "fixture-csrf"
        with self.assertRaisesRegex(CommunityError, "outcome is unknown") as raised:
            client.call("POST", INDEX, json_body={"post": {"title": "fixture"}})
        self.assertNotIn("secret URL", str(raised.exception))
        self.assertEqual(session.request.call_count, 1)

    def test_write_429_is_not_replayed(self):
        client, session = self.make_client([response(429, {}, {"Retry-After": "1"})])
        client.csrf_token = "fixture-csrf"
        self.assertFalse(client.call("POST", INDEX)["ok"])
        self.assertEqual(session.request.call_count, 1)

    def test_unexpected_origins_are_rejected_before_auth(self):
        client, session = self.make_client([])
        for address in ("https://example.com/api/v2/community/posts.json", "https://support.worldquantbrain.com@evil.test/api/v2/community/posts.json", "/api/v2/users/me.json"):
            with self.assertRaises(ValueError):
                client.call("GET", address)
        session.request.assert_not_called()

    def test_sso_rejects_unexpected_redirect_and_hides_token(self):
        brain = Mock()
        brain.call_once.return_value = {"ok": True, "response": {"status_code": 302, "location": "https://example.com/?jwt=private"}}
        client = CommunityClient(brain_client=brain, session=Mock())
        with self.assertRaisesRegex(CommunityError, "unexpected redirect") as raised:
            client.authenticate()
        self.assertNotIn("private", str(raised.exception))

    def test_sso_preserves_separate_forum_session(self):
        brain = Mock()
        brain.call_once.return_value = {"ok": True, "response": {"status_code": 302, "location": "https://worldquantbrain.zendesk.com/access/jwt?jwt=fixture"}}
        session = Mock()
        session.get.side_effect = [response(302, headers={"Location": "https://support.worldquantbrain.com/hc/en-us"}), response(200)]
        client = CommunityClient(brain_client=brain, session=session)
        client.authenticate()
        self.assertTrue(client.authenticated)
        self.assertEqual(session.get.call_count, 2)

    def test_expired_brain_redirect_renews_once_before_sso(self):
        brain = Mock()
        brain.login_payload_provider.return_value = {"email": "test@example.invalid", "password": "fixture"}
        brain.call_once.side_effect = [
            {"ok": True, "response": {"status_code": 302, "location": "https://platform.worldquantbrain.com/sign-in"}},
            {"ok": True, "response": {"status_code": 201}},
            {"ok": True, "response": {"status_code": 302, "location": "https://worldquantbrain.zendesk.com/access/jwt?jwt=fixture"}},
        ]
        session = Mock()
        session.get.return_value = response(200)
        client = CommunityClient(brain_client=brain, session=session)
        client.authenticate()
        self.assertTrue(client.authenticated)
        self.assertEqual(brain.login_payload_provider.call_count, 1)
        self.assertEqual(brain.call_once.call_count, 3)
        self.assertIn("text/html", session.get.call_args.kwargs["headers"]["Accept"])

    def test_comments_pagination_merges_authors(self):
        following = "https://support.worldquantbrain.com/api/v2/community/posts/100/comments.json?page=2"
        client, session = self.make_client([response(200, {"comments": [comment()], "users": [{"id": 20, "name": "first"}], "next_page": following}), response(200, {"comments": [comment(comment_id="401")], "users": [{"id": 21, "name": "second"}], "next_page": None})])
        comments, users = client.comments("100")
        self.assertEqual(len(comments), 2)
        self.assertEqual(set(users), {"20", "21"})

    def test_cursor_alias_keeps_the_same_comment_resource(self):
        following = "https://support.worldquantbrain.com/api/v2/help_center/community/posts/100/comments?page%5Bafter%5D=cursor"
        client, session = self.make_client([response(200, {"comments": [comment()], "meta": {"has_more": True}, "links": {"next": following}}), response(200, {"comments": [comment(comment_id="401")], "meta": {"has_more": False}, "links": {}})])
        self.assertEqual(len(client.comments("100")[0]), 2)

    def test_dry_run_never_constructs_authenticated_client(self):
        args = build_parser(plugins=[]).parse_args(["community", "create", "--json", '{"post":{"title":"draft"}}', "--dry-run"])
        with patch("wqb_cli.commands.community.CommunityClient") as client, patch("wqb_cli.commands.community.write_json") as output:
            self.assertEqual(handle_community(args), 0)
            client.assert_not_called()
            self.assertTrue(output.call_args.args[0]["dry_run"])

    def test_inventory_method_and_variable_validation(self):
        registry = load_community_registry()
        with self.assertRaises(ValueError):
            prepare_community_request(registry, "DELETE", "/api/v2/community/topics.json")
        with self.assertRaises(ValueError):
            prepare_community_request(registry, "GET", "/api/v2/community/posts/{post_id}.json", path_vars={"post_id": "../../users"})


class CommunityStorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "community.sqlite3"

    def test_sync_repeated_run_is_idempotent_and_searchable(self):
        fixture = ForumFixture({INDEX: page([post(count=1)])}, {"100": [comment()]})
        first = sync_storage(self.path, fixture)
        second = sync_storage(self.path, fixture)
        self.assertEqual(first["status"], "COMPLETE")
        self.assertEqual(second["counts"], {"unchanged": 1})
        self.assertEqual(fixture.comment_calls, ["100"])
        self.assertEqual(stats_storage(self.path)["counts"]["forum_comments"], 1)
        found = search_local_storage(self.path, author="JL40454", scope="topics")
        self.assertEqual(found["forum_topics"][0]["topic_id"], "100")
        matches = query_storage(self.path, "SELECT rowid FROM forum_topics_fts WHERE forum_topics_fts MATCH :query", parameters={"query": "cashflow"})
        self.assertEqual(matches["row_count"], 1)

    def test_comment_failure_keeps_job_and_completion_boundary(self):
        fixture = ForumFixture({INDEX: page([post(count=1)])}, {"100": [comment()]})
        fixture.fail_comments = True
        with self.assertRaises(CommunityError):
            sync_storage(self.path, fixture)
        self.assertEqual(stats_storage(self.path)["counts"]["forum_topics"], 0)
        self.assertEqual(query_storage(self.path, "SELECT * FROM community_sync_state")["row_count"], 0)
        fixture.fail_comments = False
        result = sync_storage(self.path, fixture)
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(len(fixture.requests), 1)
        self.assertEqual(stats_storage(self.path)["counts"]["forum_topics"], 1)

    def test_page_budget_resumes_without_refetching_saved_page(self):
        following = INDEX + "?page=2"
        fixture = ForumFixture({INDEX: page([post()], following), following: page([post("101")])})
        first = sync_storage(self.path, fixture, max_pages=1)
        self.assertEqual(first["status"], "PAUSED")
        self.assertIsNone(first["watermark"])
        second = sync_storage(self.path, fixture, max_pages=1)
        self.assertEqual(second["run_id"], first["run_id"])
        self.assertEqual(second["status"], "COMPLETE")
        self.assertEqual([request[0] for request in fixture.requests], [INDEX, following])

    def test_equal_boundary_timestamps_are_not_dropped(self):
        boundary = NOW - timedelta(days=1)
        following = INDEX + "?page=2"
        fixture = ForumFixture({INDEX: page([post(updated=boundary.isoformat())], following), following: page([post("101", updated=boundary.isoformat()), post("102", updated=(boundary - timedelta(seconds=1)).isoformat())], INDEX + "?page=3")})
        result = sync_storage(self.path, fixture, since=boundary.isoformat())
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(stats_storage(self.path)["counts"]["forum_topics"], 2)
        self.assertEqual(len(fixture.requests), 2)

    def test_changed_post_and_comment_replace_search_terms(self):
        fixture = ForumFixture({INDEX: page([post(count=1)])}, {"100": [comment(body="oldword")]})
        sync_storage(self.path, fixture)
        revised = post(count=1, title="newword", updated=NOW.isoformat())
        fixture.pages[INDEX] = page([revised])
        fixture.comment_map["100"] = [comment(body="replacement")]
        sync_storage(self.path, fixture)
        self.assertEqual(get_local_post(self.path, "100")["post"]["title"], "newword")
        self.assertEqual(query_storage(self.path, "SELECT rowid FROM forum_comments_fts WHERE forum_comments_fts MATCH 'oldword'")["row_count"], 0)
        self.assertEqual(query_storage(self.path, "SELECT rowid FROM forum_comments_fts WHERE forum_comments_fts MATCH 'replacement'")["row_count"], 1)

    def test_post_move_updates_comments_and_retains_single_post(self):
        fixture = ForumFixture({INDEX: page([post(count=1)])}, {"100": [comment()]})
        sync_storage(self.path, fixture)
        fixture.pages[INDEX] = page([post(count=1, section="11", updated=NOW.isoformat())])
        sync_storage(self.path, fixture)
        local = get_local_post(self.path, "100")
        self.assertEqual(local["post"]["community_id"], "11")
        self.assertEqual(local["comments"][0]["community_id"], "11")
        self.assertEqual(stats_storage(self.path)["counts"]["forum_topics"], 1)

    def test_import_merges_without_erasing_documentation(self):
        store = CommunityStore(self.path)
        with store.connection:
            store.upsert("docs_articles", {"category_id": "1", "section_id": "2", "article_id": "3", "title": "Documentation", "url": "https://example.com", "author": "Official", "datetime": NOW.isoformat(), "article_content": "retained", "last_crawled_at": NOW.isoformat(), "raw_json": "{}"})
        store.close()
        source = Path(self.temporary.name) / "plugin.json"
        source.write_text(json.dumps({"byCommunity": {"10": {"topics": {"100": {"title": "Imported", "postContent": "content", "url": "https://support.worldquantbrain.com/hc/en-us/community/posts/100-example"}}}}}), encoding="utf-8")
        import_storage(str(source), self.path)
        import_storage(str(source), self.path)
        counts = stats_storage(self.path)["counts"]
        self.assertEqual(counts["docs_articles"], 1)
        self.assertEqual(counts["forum_topics"], 1)

    def test_old_plugin_import_does_not_replace_synced_content(self):
        sync_storage(self.path, ForumFixture({INDEX: page([post(title="Current")])}))
        source = Path(self.temporary.name) / "older.json"
        source.write_text(json.dumps({"byCommunity": {"10": {"topics": {"100": {"title": "Old", "postContent": "obsolete", "lastCrawledAt": (NOW - timedelta(days=10)).isoformat()}}}}}), encoding="utf-8")
        result = import_storage(str(source), self.path)
        self.assertEqual(result["retained_newer_posts"], 1)
        self.assertEqual(get_local_post(self.path, "100")["post"]["title"], "Current")

    def test_cursor_alias_keeps_the_same_posts_resource(self):
        following = "https://support.worldquantbrain.com/api/v2/help_center/community/posts?page%5Bafter%5D=cursor"
        first = page([post()])
        first.update({"meta": {"has_more": True}, "links": {"next": following}})
        fixture = ForumFixture({INDEX: first, following: page([post("101")])})
        self.assertEqual(sync_storage(self.path, fixture)["status"], "COMPLETE")
        self.assertEqual(stats_storage(self.path)["counts"]["forum_topics"], 2)

    def test_confirmed_unavailable_post_does_not_delete_local_history(self):
        fixture = ForumFixture({INDEX: page([post(count=1)])}, {"100": [comment()]})
        sync_storage(self.path, fixture)
        fixture.pages[INDEX] = page([post(count=1, updated=NOW.isoformat())])
        original_read = fixture.get_json

        def missing_read(address, *, params=None):
            if address.endswith("/100.json"):
                raise CommunityError("Unavailable", status_code=404)
            return original_read(address, params=params)

        fixture.get_json = missing_read
        fixture.comments = Mock(side_effect=CommunityError("Unavailable", status_code=404))
        result = sync_storage(self.path, fixture)
        self.assertEqual(result["counts"], {"unavailable": 1})
        self.assertEqual(stats_storage(self.path)["counts"]["forum_topics"], 1)

    def test_sql_binds_parameters_and_reports_truncation(self):
        sync_storage(self.path, ForumFixture({INDEX: page([post(), post("101")])}))
        result = query_storage(self.path, "SELECT topic_id FROM forum_topics WHERE title=:title ORDER BY topic_id", parameters={"title": "Economic mechanism"}, max_rows=1)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["rows"], [["100"]])
        empty = query_storage(self.path, "SELECT topic_id FROM forum_topics WHERE title=:title", parameters={"title": "' OR 1=1 --"})
        self.assertEqual(empty["row_count"], 0)

    def test_sql_rejects_mutations_attachments_and_multiple_statements(self):
        sync_storage(self.path, ForumFixture({INDEX: page([post()])}))
        for sql in ("DELETE FROM forum_topics", "CREATE TABLE changed(value)", "ATTACH DATABASE ':memory:' AS elsewhere", "PRAGMA writable_schema=ON", "SELECT load_extension('anything')", "SELECT 1; SELECT 2"):
            with self.subTest(sql=sql), self.assertRaises(sqlite3.DatabaseError):
                query_storage(self.path, sql)
        self.assertEqual(stats_storage(self.path)["counts"]["forum_topics"], 1)

    def test_sql_deadline_stops_unbounded_recursive_query(self):
        CommunityStore(self.path).close()
        with self.assertRaises(sqlite3.OperationalError):
            query_storage(self.path, "WITH RECURSIVE counter(value) AS (SELECT 1 UNION ALL SELECT value+1 FROM counter) SELECT SUM(value) FROM counter", timeout=0.001)

    def test_writer_lock_prevents_competing_sync(self):
        with writer_lock(self.path):
            with self.assertRaisesRegex(RuntimeError, "Another sqlitecom writer"):
                with writer_lock(self.path):
                    self.fail("Competing writer unexpectedly acquired lock")

    def test_unordered_index_fails_without_advancing_watermark(self):
        fixture = ForumFixture({INDEX: page([post(updated=(NOW - timedelta(days=1)).isoformat()), post("101", updated=NOW.isoformat())])})
        with self.assertRaisesRegex(CommunityError, "ordering"):
            sync_storage(self.path, fixture)
        self.assertEqual(query_storage(self.path, "SELECT * FROM community_sync_state")["row_count"], 0)

    def test_stale_comments_can_be_refreshed_without_changed_parent(self):
        fixture = ForumFixture({INDEX: page([post(count=1)])}, {"100": [comment()]})
        sync_storage(self.path, fixture)
        fixture.comment_map["100"] = [comment(body="edited comment")]
        sync_storage(self.path, fixture, refresh_comments_days=0)
        self.assertEqual(get_local_post(self.path, "100")["comments"][0]["comment_content"], "edited comment")


if __name__ == "__main__":
    unittest.main()
