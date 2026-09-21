from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from wqb_cli.cli import build_parser
from wqb_cli.commands.community import handle_community
from wqb_cli.core.community_client import CommunityClient, CommunityError, browser_write_context
from wqb_cli.core.community_publish import image_file, materialize_images, plan_images, upload_image, verify_post_page


PNG = b"\x89PNG\r\n\x1a\nfixture-image"


def reply(status, body):
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(body).encode("utf-8")
    return response


class SharedCsrfTests(unittest.TestCase):
    def test_api_writes_use_shared_token_from_page(self):
        context = {"current_session": {"csrf_token": "wrong-help-center-token", "shared_csrf_token": "shared-token"},
                   "current_brand_id": 123}
        page = reply(200, {})
        page._content = ("<script>HelpCenter.internal = " + json.dumps(context) + ";</script>").encode("utf-8")
        session = Mock()
        session.get.return_value = page
        session.request.return_value = reply(201, {"post": {"id": 100}})
        client = CommunityClient(session=session, brain_client=Mock())
        client.authenticated = True
        result = client.call("POST", "/api/v2/community/posts.json", json_body={"post": {"title": "fixture"}})
        self.assertTrue(result["ok"])
        self.assertEqual(session.request.call_args.kwargs["headers"]["X-CSRF-Token"], "shared-token")
        self.assertEqual(client.brand_id, "123")
        self.assertNotIn("shared-token", json.dumps(result))

    def test_missing_shared_token_prevents_write(self):
        session = Mock()
        session.get.return_value = reply(200, {})
        client = CommunityClient(session=session, brain_client=Mock())
        client.authenticated = True
        with self.assertRaisesRegex(CommunityError, "shared CSRF"):
            client.call("POST", "/api/v2/community/posts.json")
        session.request.assert_not_called()

    def test_context_parser_does_not_execute_javascript(self):
        self.assertEqual(browser_write_context("HelpCenter.internal = fetch('/private');"), {})
        self.assertEqual(browser_write_context('HelpCenter.internal = {"current_session":{"csrf_token":"wrong"}};'), {})


class PostVerificationTests(unittest.TestCase):
    def test_page_verification_compares_content_and_normalizes_image_urls(self):
        session = Mock()
        page = reply(200, {})
        page._content = '<h1>Research</h1><div class="post-body"><p>中文<br>Body</p><img src="https://support.worldquantbrain.com/hc/user_images/trace.png"></div>'.encode("utf-8")
        session.get.return_value = page
        client = CommunityClient(session=session, brain_client=Mock())
        client.authenticated = True
        result = verify_post_page(client, {"id": 100, "html_url": "https://support.worldquantbrain.com/hc/en-us/community/posts/100-Research",
                                          "title": "Research", "details": '<p>中文<br>Body</p><img src="/hc/user_images/trace.png">'})
        self.assertTrue(result["ok"])
        self.assertTrue(result["images_match"])
        session.request.assert_not_called()

    def test_page_with_changed_body_does_not_verify(self):
        client = Mock()
        page = reply(200, {})
        page._content = b'<h1>Research</h1><div class="post-body">Different body</div>'
        client.post_page.return_value = page
        result = verify_post_page(client, {"id": 100, "html_url": "https://support.worldquantbrain.com/hc/en-us/community/posts/100",
                                          "title": "Research", "details": "Expected body"})
        self.assertFalse(result["ok"])
        self.assertFalse(result["body_matches"])

    def test_page_verification_rejects_a_different_origin_or_post(self):
        session = Mock()
        client = CommunityClient(session=session, brain_client=Mock())
        for address in ("https://evil.invalid/hc/en-us/community/posts/100", "https://support.worldquantbrain.com/hc/en-us/community/posts/999"):
            with self.subTest(address=address), self.assertRaises(ValueError):
                client.post_page(address, "100")
        session.get.assert_not_called()


class ImagePublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.image = self.directory / "trace.png"
        self.image.write_bytes(PNG)

    def image_receipt(self):
        metadata, content = image_file(self.image)
        return {**metadata, "path": "/hc/user_images/trace.png", "url": "https://support.worldquantbrain.com/hc/user_images/trace.png",
                "brand_id": "123", "http_status": 201}

    def upload_client(self):
        client = Mock()
        client.session.trust_env = False
        client.timeout = 20
        client.write_context.return_value = {"brand_id": "123", "csrf_token": "shared-token"}
        client.call.side_effect = [
            {"ok": True, "response": {"status_code": 200, "body": {"upload": {
                "url": "https://aus-uploaded-assets-production.s3-accelerate.amazonaws.com/fixture?signature=private",
                "headers": {"Content-Type": "image/png"}, "token": "private-token"}}}},
            {"ok": True, "response": {"status_code": 201, "body": {"user_image": {"path": "/hc/user_images/trace.png"}}}},
        ]
        return client

    def test_upload_follows_three_steps_without_leaking_ticket(self):
        client = self.upload_client()
        transfer = Mock()
        transfer.put.return_value = reply(200, {})
        with patch("wqb_cli.core.community_publish.requests.Session", return_value=transfer):
            result = upload_image(client, self.image)
        self.assertEqual(result["path"], "/hc/user_images/trace.png")
        self.assertEqual(transfer.put.call_args.kwargs["data"], PNG)
        self.assertEqual(transfer.put.call_args.kwargs["headers"], {"Content-Type": "image/png"})
        self.assertFalse(transfer.put.call_args.kwargs["allow_redirects"])
        self.assertEqual(client.call.call_args_list[1].kwargs["json_body"], {"token": "private-token", "brand_id": "123"})
        self.assertNotIn("private", json.dumps(result))

    def test_upload_timeout_does_not_register_or_replay(self):
        client = self.upload_client()
        transfer = Mock()
        transfer.put.side_effect = requests.Timeout("private signed URL")
        with patch("wqb_cli.core.community_publish.requests.Session", return_value=transfer):
            with self.assertRaisesRegex(CommunityError, "outcome is unknown") as raised:
                upload_image(client, self.image)
        self.assertEqual(client.call.call_count, 1)
        self.assertEqual(transfer.put.call_count, 1)
        self.assertNotIn("private", str(raised.exception))

    def test_unexpected_upload_host_never_receives_image(self):
        client = self.upload_client()
        client.call.side_effect = [{"ok": True, "response": {"body": {"upload": {
            "url": "https://evil.invalid/upload", "headers": {}, "token": "private-token"}}}}]
        with patch("wqb_cli.core.community_publish.requests.Session") as transfer:
            with self.assertRaisesRegex(CommunityError, "unexpected image upload destination"):
                upload_image(client, self.image)
            transfer.assert_not_called()

    def test_repeated_references_and_retries_reuse_image_receipt(self):
        body = "<p>中文</p><a href='trace.png'><img src='trace.png'></a><img src=trace.png>"
        manifest = self.directory / "images.json"
        with patch("wqb_cli.core.community_publish.upload_image", return_value=self.image_receipt()) as uploaded:
            first, images = materialize_images(Mock(), body, self.directory, manifest, upload_local=True)
            second, cached = materialize_images(Mock(), body, self.directory, manifest, upload_local=True)
        self.assertEqual(uploaded.call_count, 1)
        self.assertEqual(first.count("/hc/user_images/trace.png"), 3)
        self.assertIn("中文", first)
        self.assertEqual(first, second)
        self.assertEqual(images, cached)

    def test_all_files_are_validated_before_any_upload(self):
        with patch("wqb_cli.core.community_publish.upload_image") as uploaded:
            with self.assertRaises(FileNotFoundError):
                materialize_images(Mock(), '<img src="trace.png"><img src="missing.png">',
                                   self.directory, self.directory / "images.json", upload_local=True)
            uploaded.assert_not_called()

    def test_paths_cannot_escape_the_input_directory(self):
        for source in ("../outside.png", "%2e%2e/outside.png", "https://external.invalid/image.png", "//external.invalid/image.png"):
            with self.subTest(source=source), self.assertRaises(ValueError):
                plan_images('<img src="' + source + '">', self.directory, upload_local=True)

    def test_html_cli_dry_run_never_authenticates_or_uploads(self):
        html = self.directory / "post.html"
        html.write_text('<p>中文</p><img src="trace.png">', encoding="utf-8")
        args = build_parser(plugins=[]).parse_args(["community", "create", "--html", str(html),
                                                  "--title", "Fixture", "--topic", "123", "--dry-run"])
        with patch("wqb_cli.commands.community.CommunityClient") as client, patch("wqb_cli.commands.community.write_json") as output:
            self.assertEqual(handle_community(args), 0)
        client.assert_not_called()
        preview = output.call_args.args[0]
        self.assertEqual(preview["images"][0]["file_size"], len(PNG))
        self.assertEqual(preview["request"]["json"]["post"]["topic_id"], 123)
        self.assertFalse(preview["request"]["json"]["notify_subscribers"])
        self.assertFalse((self.directory / "post.html.assets.json").exists())

    def test_html_cli_sends_materialized_body_and_reads_saved_post(self):
        html = self.directory / "post.html"
        html.write_text('<img src="trace.png">', encoding="utf-8")
        args = build_parser(plugins=[]).parse_args(["community", "create", "--html", str(html),
                                                  "--title", "Fixture", "--topic", "123"])
        client = Mock()
        client.call.side_effect = [
            {"ok": True, "response": {"body": {"post": {"id": 100}}}},
            {"ok": True, "response": {"body": {"post": {"id": 100, "details": '<img src="/hc/user_images/trace.png">'}}}},
        ]
        with patch("wqb_cli.commands.community._client", return_value=client), patch("wqb_cli.core.community_publish.upload_image", return_value=self.image_receipt()), patch("wqb_cli.commands.community.write_json") as output:
            self.assertEqual(handle_community(args), 0)
        self.assertEqual(client.call.call_args_list[0].kwargs["json_body"]["post"]["details"], '<img src="/hc/user_images/trace.png">')
        self.assertEqual(client.call.call_args_list[1].args, ("GET", "/api/v2/community/posts/100.json"))
        self.assertTrue(output.call_args.args[0]["verification"]["ok"])


if __name__ == "__main__":
    unittest.main()
