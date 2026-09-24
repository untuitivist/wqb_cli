from __future__ import annotations

import json
import unittest
from unittest.mock import Mock, patch

import requests

from wqb_cli.cli import build_parser
from wqb_cli.commands.community import handle_community
from wqb_cli.core.community_client import CommunityChallengeError, CommunityClient, CommunityError


def response(status, headers=None, body=None):
    reply = requests.Response()
    reply.status_code = status
    reply.headers.update(headers or {})
    reply._content = json.dumps(body or {}).encode("utf-8")
    return reply


class CommunityAuthTests(unittest.TestCase):
    def client(self):
        brain = Mock()
        brain.call_once.return_value = {
            "ok": True, "response": {"status_code": 302,
                                      "location": "https://worldquantbrain.zendesk.com/access/jwt?jwt=secret"}}
        session = Mock()
        client = CommunityClient(brain_client=brain, session=session, sleeper=Mock(), max_wait_seconds=5)
        return client, brain, session

    def test_challenged_landing_is_not_retried_or_called_bad_credentials(self):
        client, brain, session = self.client()
        client.authenticated = True
        client.csrf_token = "old-secret"
        session.get.side_effect = [
            response(302, {"Location": "https://support.worldquantbrain.com/hc/en-us"}),
            response(403, {"cf-mitigated": "challenge"}),
        ]
        with self.assertRaises(CommunityChallengeError) as raised:
            client.authenticate()
        error = raised.exception.as_dict()
        self.assertEqual(error["code"], "browser_verification_required")
        self.assertEqual(error["stage"], "support_sso")
        self.assertEqual(error["status_code"], 403)
        self.assertNotIn("secret", json.dumps(error))
        self.assertEqual(session.get.call_count, 2)
        self.assertFalse(client.authenticated)
        self.assertIsNone(client.csrf_token)
        brain.login_payload_provider.assert_not_called()

    def test_api_challenge_does_not_trigger_another_login(self):
        client, brain, session = self.client()
        client.authenticated = True
        session.request.return_value = response(403, {"cf-mitigated": "challenge"})
        with self.assertRaises(CommunityChallengeError):
            client.call("GET", "/api/v2/community/posts.json")
        brain.call_once.assert_not_called()
        self.assertEqual(session.request.call_count, 1)
        self.assertFalse(client.authenticated)

    def test_sso_rate_limit_honors_retry_after(self):
        client, brain, session = self.client()
        session.get.side_effect = [response(429, {"Retry-After": "2"}), response(200)]
        client.authenticate()
        client.sleeper.assert_called_once_with(2)
        self.assertTrue(client.authenticated)

    def test_sso_retry_budget_and_failed_refresh_clear_state(self):
        client, brain, session = self.client()
        client.authenticated = True
        session.get.return_value = response(429, {"Retry-After": "20"})
        with self.assertRaises(CommunityError) as raised:
            client.authenticate()
        self.assertEqual(raised.exception.status_code, 429)
        client.sleeper.assert_not_called()
        self.assertFalse(client.authenticated)

    def test_restricted_redirect_never_becomes_authenticated(self):
        client, brain, session = self.client()
        session.get.return_value = response(302, {"Location": "/hc/restricted?return_to=private"})
        brain.call_once.return_value["response"]["location"] = "https://support.worldquantbrain.com/access/return_to"
        with self.assertRaises(CommunityError) as raised:
            client.authenticate()
        self.assertEqual(raised.exception.code, "community_login_required")
        self.assertEqual(session.get.call_count, 1)

    def test_brain_renewal_rate_limit_retries_within_budget(self):
        client, brain, session = self.client()
        brain.login_payload_provider.return_value = {"email": "fixture", "password": "private"}
        brain.call_once.side_effect = [
            {"ok": True, "response": {"location": "https://platform.worldquantbrain.com/sign-in"}},
            {"ok": False, "response": {"status_code": 429, "retry_after": "1"}},
            {"ok": True, "response": {"status_code": 201}},
            {"ok": True, "response": {"location": "https://support.worldquantbrain.com/hc/en-us"}},
        ]
        session.get.return_value = response(200)
        client.authenticate()
        client.sleeper.assert_called_once_with(1)
        self.assertEqual(brain.call_once.call_count, 4)
        self.assertTrue(client.authenticated)

    def test_page_read_refreshes_expired_session_once(self):
        client, brain, session = self.client()
        client.authenticated = True
        session.get.side_effect = [response(401), response(200), response(200)]
        reply = client.post_page("https://support.worldquantbrain.com/hc/en-us/community/posts/100", "100")
        self.assertEqual(reply.status_code, 200)
        self.assertEqual(brain.call_once.call_count, 1)
        self.assertEqual(session.get.call_count, 3)

    def test_api_expiry_is_refreshed_once(self):
        client, brain, session = self.client()
        client.authenticated = True
        session.get.return_value = response(200)
        session.request.side_effect = [response(401), response(401)]
        self.assertFalse(client.call("GET", "/api/v2/community/posts.json")["ok"])
        self.assertFalse(client.authenticated)
        self.assertEqual(brain.call_once.call_count, 1)
        self.assertEqual(session.request.call_count, 2)

    def test_rejected_write_is_not_replayed_and_clears_csrf(self):
        client, brain, session = self.client()
        client.authenticated = True
        client.csrf_token = "old"
        session.request.return_value = response(403)
        self.assertFalse(client.call("POST", "/api/v2/community/posts.json")["ok"])
        self.assertIsNone(client.csrf_token)
        self.assertFalse(client.authenticated)
        brain.call_once.assert_not_called()
        self.assertEqual(session.request.call_count, 1)

    def test_auth_dry_run_never_logs_in(self):
        args = build_parser(plugins=[]).parse_args(["community", "auth", "--dry-run"])
        with patch("wqb_cli.commands.community._client") as client, patch("wqb_cli.commands.community.write_json"):
            self.assertEqual(handle_community(args), 0)
        client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
