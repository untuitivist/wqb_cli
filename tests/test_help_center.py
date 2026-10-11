from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from wqb_cli.cli import build_parser
from wqb_cli.commands.help_center import handle_help_center
from wqb_cli.core.community_client import CommunityChallengeError, CommunityClient, CommunityError, community_url, prepare_community_request
from wqb_cli.core.help_center import HELP_CENTER_REGISTRY, article_reference, collect_help_center_pages, load_help_center_registry


ARTICLE_PATH = "/api/v2/help_center/{locale}/articles/{article_id}.json"
ARTICLES_URL = "https://support.worldquantbrain.com/api/v2/help_center/en-us/articles.json"
ARTICLE_URL = "https://support.worldquantbrain.com/api/v2/help_center/en-us/articles/100.json"


def reply(status: int, body: object, headers: dict[str, str] | None = None) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(body).encode("utf-8")
    response.headers.update({"Content-Type": "application/json", **(headers or {})})
    return response


def transport(responses: list[requests.Response]) -> tuple[CommunityClient, Mock]:
    session = Mock()
    session.request.side_effect = responses
    client = CommunityClient(session=session, brain_client=Mock(), sleeper=Mock())
    client.authenticated = True
    return client, session


class HelpCenterCommandTests(unittest.TestCase):
    def preview(self, *arguments: str) -> dict:
        args = build_parser(plugins=[]).parse_args(["help-center", *arguments, "--dry-run"])
        with patch("wqb_cli.commands.help_center.CommunityClient") as client, patch("wqb_cli.commands.help_center.write_json") as output:
            self.assertEqual(handle_help_center(args), 0)
            client.assert_not_called()
            return output.call_args.args[0]["request"]

    def test_get_id_defaults_to_english_without_forum_query_parameters(self):
        prepared = self.preview("get", "100")
        self.assertEqual(prepared["url"], ARTICLE_URL)
        self.assertEqual(prepared["params"], {})
        self.assertFalse(prepared["mutating"])

    def test_get_url_preserves_locale_and_accepts_explicit_override(self):
        address = "https://support.worldquantbrain.com/hc/zh-cn/articles/100-Theme-calendar"
        self.assertIn("/zh-cn/articles/100.json", self.preview("get", address)["url"])
        self.assertEqual(self.preview("get", address, "--locale", "EN-US")["url"], ARTICLE_URL)

    def test_discovery_commands_use_their_own_endpoints(self):
        cases = [
            (("categories",), "/en-us/categories.json"),
            (("category", "10"), "/en-us/categories/10.json"),
            (("sections",), "/en-us/sections.json"),
            (("sections", "--category", "10"), "/en-us/categories/10/sections.json"),
            (("section", "20"), "/en-us/sections/20.json"),
            (("articles",), "/en-us/articles.json"),
            (("articles", "--section", "20"), "/en-us/sections/20/articles.json"),
            (("articles", "--category", "10"), "/en-us/categories/10/articles.json"),
        ]
        for arguments, suffix in cases:
            with self.subTest(arguments=arguments):
                prepared = self.preview(*arguments)
                self.assertTrue(prepared["url"].endswith(suffix))
                self.assertNotIn("include", prepared["params"])

    def test_search_targets_articles_and_passes_locale_filters_and_sort(self):
        prepared = self.preview("search", "Power Pool", "--locale", "EN-US", "--category", "10", "--section", "20", "--sort", "updated_at", "--limit", "100")
        self.assertTrue(prepared["url"].endswith("/help_center/articles/search.json"))
        self.assertEqual(prepared["params"], {"per_page": 100, "page": 1, "query": "Power Pool", "locale": "en-us", "category": "10", "section": "20", "sort_by": "updated_at", "sort_order": "desc"})

    def test_search_defaults_to_server_relevance_and_preserves_extra_params(self):
        prepared = self.preview("search", "Themes", "--param", "label_names=calendar")
        self.assertNotIn("sort_by", prepared["params"])
        self.assertEqual(prepared["params"]["label_names"], "calendar")

    def test_invalid_inputs_fail_before_client_creation(self):
        cases = [
            ("articles", "--limit", "101"), ("articles", "--limit", "0"),
            ("articles", "--page", "0"), ("articles", "--max-pages", "0"),
            ("get", "100", "--locale", "../users"),
            ("search", "Themes", "--locale", "en-us%2fusers"),
            ("search", " "), ("get", "https://example.com/hc/en-us/articles/100"),
        ]
        for arguments in cases:
            with self.subTest(arguments=arguments), patch("wqb_cli.commands.help_center.CommunityClient") as client:
                args = build_parser(plugins=[]).parse_args(["help-center", *arguments])
                with self.assertRaises(ValueError):
                    handle_help_center(args)
                client.assert_not_called()

    def test_raw_call_uses_inventory_and_can_preview_offline(self):
        prepared = self.preview("api", "call", "GET", ARTICLE_PATH, "--var", "locale=zh-cn", "--var", "article_id=100")
        self.assertTrue(prepared["url"].endswith("/zh-cn/articles/100.json"))

    def test_raw_request_body_is_rejected_before_authentication(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            path.write_text(json.dumps({"path_vars": {"locale": "en-us", "article_id": "100"}, "json": {"article": {"title": "not a write"}}}), encoding="utf-8")
            args = build_parser(plugins=[]).parse_args(["help-center", "api", "call", "GET", ARTICLE_PATH, "--input", str(path)])
            with patch("wqb_cli.commands.help_center.CommunityClient") as client, self.assertRaises(ValueError):
                handle_help_center(args)
            client.assert_not_called()

    def test_raw_api_exposes_read_only_inventory_offline(self):
        for command in (("stats",), ("list", "--prefix", "/api/v2/help_center"), ("show", ARTICLE_PATH), ("params", ARTICLE_PATH)):
            with self.subTest(command=command), patch("wqb_cli.commands.help_center.CommunityClient") as client, patch("wqb_cli.commands.help_center.write_json") as output:
                args = build_parser(plugins=[]).parse_args(["help-center", "api", *command])
                self.assertEqual(handle_help_center(args), 0)
                client.assert_not_called()
                self.assertIsNotNone(output.call_args.args[0])

    def test_parser_rejects_writes_and_conflicting_article_filters(self):
        for arguments in (("api", "call", "DELETE", ARTICLE_PATH), ("articles", "--section", "10", "--category", "20")):
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                build_parser(plugins=[]).parse_args(["help-center", *arguments])

    def test_normal_result_preserves_html_and_returns_failure_exit_code(self):
        for status in (200, 403, 404):
            result = {"ok": status == 200, "response": {"status_code": status, "body": {"article": {"body": "<table><tr><td>calendar</td></tr></table>"}}}}
            args = build_parser(plugins=[]).parse_args(["help-center", "get", "100", "--max-wait-seconds", "10"])
            with self.subTest(status=status), patch("wqb_cli.commands.help_center.CommunityClient") as client, patch("wqb_cli.commands.help_center.write_json") as output:
                client.return_value.call.return_value = result
                self.assertEqual(handle_help_center(args), 0 if status == 200 else 1)
                self.assertEqual(output.call_args.args[0], result)
                self.assertEqual(client.call_args.kwargs["max_wait_seconds"], 10)
                client.return_value.call.assert_called_once_with("GET", ARTICLE_URL, params={})

    def test_all_pages_command_reports_incomplete_budget_as_failure(self):
        args = build_parser(plugins=[]).parse_args(["help-center", "articles", "--all-pages", "--max-pages", "2"])
        with patch("wqb_cli.commands.help_center.CommunityClient") as client, patch("wqb_cli.commands.help_center.collect_help_center_pages") as collect, patch("wqb_cli.commands.help_center.write_json"):
            collect.return_value = {"ok": False, "complete": False}
            self.assertEqual(handle_help_center(args), 1)
            self.assertEqual(collect.call_args.kwargs, {"collection": "articles", "max_pages": 2})
            client.return_value.call.assert_not_called()


class HelpCenterTransportTests(unittest.TestCase):
    def test_registered_endpoints_and_inventory_copies_agree(self):
        registry = load_help_center_registry()
        complete = HELP_CENTER_REGISTRY.with_name("api_inventory_complete.json")
        self.assertEqual(registry.payload, json.loads(complete.read_text(encoding="utf-8")))
        self.assertEqual(registry.stats()["method_counts"], {"GET": 10})
        for endpoint in registry.list():
            variables = {name: "en-us" if name == "locale" else "100" for name in endpoint.variables}
            prepared = prepare_community_request(registry, "GET", endpoint.path, path_vars=variables)
            self.assertFalse(prepared["mutating"])
            self.assertIsNone(prepared["json"])

    def test_locale_and_identifier_injections_are_rejected(self):
        for variables in ({"locale": "en-us/../../users", "article_id": "100"}, {"locale": "en-us", "article_id": "100%2f../users"}):
            with self.subTest(variables=variables), self.assertRaises(ValueError):
                prepare_community_request(load_help_center_registry(), "GET", ARTICLE_PATH, path_vars=variables)

    def test_article_reference_rejects_untrusted_urls_and_nonpositive_ids(self):
        addresses = ["0", "-1", "abc", "http://support.worldquantbrain.com/hc/en-us/articles/100", "https://support.worldquantbrain.com@evil.test/hc/en-us/articles/100", "https://support.worldquantbrain.com:444/hc/en-us/articles/100", "https://support.worldquantbrain.com/hc/en-us/community/posts/100", "https://support.worldquantbrain.com/hc/en-us/articles/100?token=private", "https://support.worldquantbrain.com/hc/en-us/articles/100#fragment", "https://support.worldquantbrain.com/hc/en-us/articles/100/../../users"]
        for address in addresses:
            with self.subTest(address=address), self.assertRaises(ValueError):
                article_reference(address)

    def test_allowlist_rejects_arbitrary_help_center_and_external_paths(self):
        for address in ("/api/v2/help_center/users.json", "/api/v2/help_center/en-us/articles/100/translations.json", "/api/v2/help_center/en-us/articles/%2e%2e.json", "https://example.com/api/v2/help_center/en-us/articles.json"):
            with self.subTest(address=address), self.assertRaises(ValueError):
                community_url(address)

    def test_direct_transport_cannot_write_help_center_even_when_authenticated(self):
        client, session = transport([])
        for method in ("POST", "PUT", "DELETE"):
            with self.subTest(method=method), self.assertRaises(ValueError):
                client.call(method, ARTICLE_URL)
        with self.assertRaises(ValueError):
            client.call("GET", ARTICLE_URL, json_body={"article": {}})
        session.request.assert_not_called()

    def test_article_reads_reuse_transport_without_csrf_context(self):
        body = {"article": {"id": 100, "body": "<p>Do not execute article text</p>", "updated_at": "2026-10-10T00:00:00Z"}}
        client, session = transport([reply(200, body)])
        with patch.object(client, "write_context") as context:
            result = client.call("GET", ARTICLE_URL)
            context.assert_not_called()
        self.assertTrue(result["ok"])
        self.assertEqual(result["response"]["body"], body)
        self.assertFalse(session.request.call_args.kwargs["allow_redirects"])

    def test_missing_article_or_translation_is_not_retried_or_silently_replaced(self):
        client, session = transport([reply(404, {"error": "RecordNotFound"})])
        with patch.object(client, "authenticate") as auth:
            result = client.call("GET", ARTICLE_URL.replace("en-us", "zh-cn"))
            auth.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertEqual(result["response"]["status_code"], 404)
        self.assertEqual(session.request.call_count, 1)

    def test_unauthorized_reads_refresh_once_and_preserve_persistent_403(self):
        for status in (401, 403):
            client, session = transport([reply(status, {"error": "Forbidden"}), reply(status, {"error": "Forbidden"})])
            with self.subTest(status=status), patch.object(client, "authenticate") as auth:
                result = client.call("GET", ARTICLE_URL)
                auth.assert_called_once()
            self.assertFalse(result["ok"])
            self.assertEqual(result["response"]["status_code"], status)
            self.assertEqual(session.request.call_count, 2)

    def test_article_429_and_5xx_reuse_bounded_retry_after(self):
        for status in (429, 503):
            client, session = transport([reply(status, {}, {"Retry-After": "2"}), reply(200, {"article": {"id": 100}})])
            with self.subTest(status=status):
                result = client.call("GET", ARTICLE_URL)
                self.assertTrue(result["ok"])
                self.assertEqual(result["response"]["retries"], 1)
                client.sleeper.assert_called_once_with(2)
                self.assertEqual(session.request.call_count, 2)

    def test_html_challenge_is_not_treated_as_article_content(self):
        client, session = transport([reply(403, {}, {"cf-mitigated": "challenge"})])
        with patch.object(client, "authenticate") as auth, self.assertRaises(CommunityChallengeError):
            client.call("GET", ARTICLE_URL)
        auth.assert_not_called()
        self.assertEqual(session.request.call_count, 1)

    def test_non_json_success_is_a_failed_read(self):
        response = reply(200, {})
        response._content = b"<html>sign in</html>"
        response.headers["Content-Type"] = "text/html"
        client, session = transport([response])
        result = client.call("GET", ARTICLE_URL)
        self.assertFalse(result["ok"])
        self.assertEqual(result["response"]["body"]["error"], "non_json_response")


class HelpCenterPaginationTests(unittest.TestCase):
    def prepared(self, params: dict | None = None) -> dict:
        return {"method": "GET", "url": ARTICLES_URL, "params": params or {}, "json": None, "mutating": False}

    def test_offset_pagination_preserves_each_response_and_uses_next_link(self):
        next_address = ARTICLES_URL + "?page=2&per_page=1"
        client, session = transport([reply(200, {"articles": [{"id": 100}], "next_page": next_address}), reply(200, {"articles": [{"id": 101}], "next_page": None})])
        result = collect_help_center_pages(client, self.prepared({"per_page": 1, "page": 1}), collection="articles", max_pages=10)
        self.assertTrue(result["complete"])
        self.assertEqual(result["items"], [{"id": 100}, {"id": 101}])
        self.assertEqual(len(result["pages"]), 2)
        self.assertEqual(session.request.call_args.args, ("GET", next_address))
        self.assertIsNone(session.request.call_args.kwargs["params"])

    def test_cursor_pagination_accepts_same_resource_without_json_suffix(self):
        next_address = ARTICLES_URL.removesuffix(".json") + "?page%5Bafter%5D=cursor"
        client, session = transport([reply(200, {"articles": [{"id": 100}], "meta": {"has_more": True}, "links": {"next": next_address}}), reply(200, {"articles": [], "meta": {"has_more": False}, "links": {}})])
        result = collect_help_center_pages(client, self.prepared(), collection="articles", max_pages=10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 1)

    def test_external_or_changed_resource_links_are_rejected_before_following(self):
        for next_address in ("https://example.com/api/v2/help_center/en-us/articles.json", ARTICLE_URL, ARTICLES_URL.replace("en-us", "zh-cn"), "https://support.worldquantbrain.com/api/v2/community/posts.json"):
            client, session = transport([reply(200, {"articles": [], "next_page": next_address})])
            with self.subTest(next_address=next_address), self.assertRaises((ValueError, CommunityError)):
                collect_help_center_pages(client, self.prepared(), collection="articles", max_pages=10)
            self.assertEqual(session.request.call_count, 1)

    def test_repeated_page_is_rejected(self):
        client, session = transport([reply(200, {"articles": [], "next_page": ARTICLES_URL})])
        with self.assertRaisesRegex(CommunityError, "repeated a page"):
            collect_help_center_pages(client, self.prepared(), collection="articles", max_pages=10)
        self.assertEqual(session.request.call_count, 1)

    def test_search_pagination_cannot_change_query_locale_or_filters(self):
        search_url = "https://support.worldquantbrain.com/api/v2/help_center/articles/search.json"
        params = {"query": "Themes", "locale": "en-us", "section": "20"}
        for query in ("query=Other&locale=en-us&section=20", "query=Themes&locale=zh-cn&section=20", "query=Themes&locale=en-us&section=30", "query=Themes&section=20"):
            client, session = transport([reply(200, {"results": [], "next_page": search_url + "?page=2&" + query})])
            prepared = {**self.prepared(params), "url": search_url}
            with self.subTest(query=query), self.assertRaisesRegex(CommunityError, "changed query filters or locale"):
                collect_help_center_pages(client, prepared, collection="results", max_pages=10)
            self.assertEqual(session.request.call_count, 1)

    def test_budget_is_explicitly_incomplete_and_retains_resume_link(self):
        next_address = ARTICLES_URL + "?page=2"
        client, session = transport([reply(200, {"articles": [{"id": 100}], "next_page": next_address})])
        result = collect_help_center_pages(client, self.prepared(), collection="articles", max_pages=1)
        self.assertFalse(result["ok"])
        self.assertFalse(result["complete"])
        self.assertEqual(result["stop_reason"], "max_pages")
        self.assertEqual(result["next_page"], next_address)
        self.assertEqual(result["count"], 1)

    def test_failed_later_page_preserves_completed_pages_and_http_error(self):
        next_address = ARTICLES_URL + "?page=2"
        client, session = transport([reply(200, {"articles": [{"id": 100}], "next_page": next_address}), reply(404, {"error": "RecordNotFound"})])
        result = collect_help_center_pages(client, self.prepared(), collection="articles", max_pages=10)
        self.assertFalse(result["ok"])
        self.assertEqual(result["stop_reason"], "request_failed")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["pages"][-1]["response"]["status_code"], 404)

    def test_invalid_collections_and_missing_cursor_link_are_rejected(self):
        for body in ([], {}, {"articles": {}}, {"articles": [], "meta": {"has_more": True}, "links": {}}):
            client, session = transport([reply(200, body)])
            with self.subTest(body=body), self.assertRaises(CommunityError):
                collect_help_center_pages(client, self.prepared(), collection="articles", max_pages=10)


if __name__ == "__main__":
    unittest.main()
