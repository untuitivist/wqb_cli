from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any

import requests

from wqb_cli.core.auth import clear_worldquantbrain_cookies, session_from_cookies
from wqb_cli.core.client import AutoAuthPolicy, WqbClient
from wqb_cli.core.registry import EndpointRegistry


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        body: Any = None,
        *,
        retry_after: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.reason = {200: "OK", 201: "Created", 204: "No Content", 401: "Unauthorized", 429: "Too Many Requests"}.get(
            status_code,
            "Response",
        )
        self.headers = {"Content-Type": "application/json"}
        if retry_after is not None:
            self.headers["Retry-After"] = retry_after
        self.text = ""
        self._body = body if body is not None else {}

    def json(self) -> Any:
        return self._body


class SequenceSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def request(self, *args: Any, **kwargs: Any) -> FakeResponse:
        self.calls.append((args, kwargs))
        if not self.responses:
            raise AssertionError("unexpected request")
        return self.responses.pop(0)


class ClientPrepareTests(unittest.TestCase):
    @staticmethod
    def auto_auth_registry() -> EndpointRegistry:
        return EndpointRegistry(
            {
                "base_url": "https://api.worldquantbrain.com",
                "endpoints": [
                    {"path": "/authentication", "methods": ["POST"]},
                    {"path": "/simulations", "methods": ["POST"]},
                    {"path": "/simulations/{simulation_id}", "methods": ["GET"]},
                ],
            }
        )

    def auto_auth_client(
        self,
        session: Any,
        *,
        policy: AutoAuthPolicy | None = None,
    ) -> WqbClient:
        return WqbClient(
            self.auto_auth_registry(),
            session,
            auto_auth_policy=policy
            or AutoAuthPolicy(request_replays=3, login_attempts=3, delay_seconds=0),
            login_payload_provider=lambda: {
                "email": "researcher@example.com",
                "password": "secret",
                "expiry": 3600,
            },
            cookie_saver=lambda _session, _path: None,
            sleeper=lambda _seconds: None,
        )

    def test_mutating_request_is_executable_without_execute_flag(self) -> None:
        registry = EndpointRegistry(
            {
                "base_url": "https://api.worldquantbrain.com",
                "endpoints": [{"path": "/simulations", "methods": ["POST"]}],
            }
        )
        client = WqbClient(registry, requests.Session())

        prepared = client.prepare(registry.get("/simulations"), "POST", json_body={"type": "REGULAR"})

        self.assertTrue(prepared.mutating)
        self.assertTrue(prepared.executable)
        self.assertIsNone(prepared.reason)

    def test_legacy_cookie_payload_loads_one_host_cookie(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cookie_path = Path(temp_dir) / "cookies.json"
            cookie_path.write_text(
                json.dumps({"cookies": {"session": "saved"}}),
                encoding="utf-8",
            )

            session = session_from_cookies(str(cookie_path))

        cookies = list(session.cookies)
        self.assertEqual(len(cookies), 1)
        self.assertEqual(cookies[0].domain, "api.worldquantbrain.com")

    def test_cookie_cleanup_removes_only_worldquantbrain_domains(self) -> None:
        session = requests.Session()
        session.cookies.set("session", "parent", domain=".worldquantbrain.com")
        session.cookies.set("session", "host", domain="api.worldquantbrain.com")
        session.cookies.set("keep", "value", domain="example.com")

        clear_worldquantbrain_cookies(session)

        self.assertEqual(
            [(cookie.name, cookie.domain) for cookie in session.cookies],
            [("keep", "example.com")],
        )

    def test_call_once_does_not_follow_retry_after(self) -> None:
        class FakeResponse:
            status_code = 200
            reason = "OK"
            headers = {"Content-Type": "application/json", "Retry-After": "30"}
            text = ""

            @staticmethod
            def json() -> dict[str, str]:
                return {"status": "PENDING"}

        class FakeSession:
            def __init__(self) -> None:
                self.calls = 0

            def request(self, *args: object, **kwargs: object) -> FakeResponse:
                self.calls += 1
                return FakeResponse()

        registry = EndpointRegistry(
            {
                "base_url": "https://api.worldquantbrain.com",
                "endpoints": [{"path": "/simulations/{simulation_id}", "methods": ["GET"]}],
            }
        )
        session = FakeSession()
        client = WqbClient(registry, session)
        prepared = client.prepare(
            registry.get("/simulations/{simulation_id}"),
            "GET",
            path_vars={"simulation_id": "demo"},
        )

        result = client.call_once(prepared)

        self.assertTrue(result["ok"])
        self.assertEqual(session.calls, 1)
        self.assertEqual(result["response"]["retry_after"], "30")

    def test_401_reauthenticates_and_replays_globally(self) -> None:
        session = SequenceSession(
            [
                FakeResponse(401),
                FakeResponse(201),
                FakeResponse(200, {"status": "PENDING"}),
            ]
        )
        client = self.auto_auth_client(session)
        registry = client.registry
        prepared = client.prepare(
            registry.get("/simulations/{simulation_id}"),
            "GET",
            path_vars={"simulation_id": "demo"},
        )

        result = client.call_once(prepared)

        self.assertEqual(result["response"]["status_code"], 200)
        self.assertEqual([call[0][0] for call in session.calls], ["GET", "POST", "GET"])
        auth_call = session.calls[1]
        self.assertEqual(auth_call[1]["auth"], ("researcher@example.com", "secret"))
        self.assertEqual(auth_call[1]["json"], {"expiry": 3600})
        authentication = result["response"]["authentication"]
        self.assertEqual(authentication["replays"], 1)
        self.assertFalse(authentication["exhausted"])
        self.assertTrue(authentication["events"][0]["refresh"]["ok"])

    def test_reauthentication_clears_conflicting_cookie_domains_before_replay(self) -> None:
        class CookieReplacingSession:
            def __init__(self) -> None:
                self.cookies = requests.cookies.RequestsCookieJar()
                self.cookies.set("session", "stale-parent", domain=".worldquantbrain.com")
                self.cookies.set("session", "stale-host", domain="api.worldquantbrain.com")
                self.calls = 0

            def request(self, method: str, *args: Any, **kwargs: Any) -> FakeResponse:
                self.calls += 1
                if self.calls == 1:
                    return FakeResponse(401)
                if method == "POST":
                    brain_cookies = [
                        cookie
                        for cookie in self.cookies
                        if "worldquantbrain.com" in (cookie.domain or "")
                    ]
                    if brain_cookies:
                        raise AssertionError("stale BRAIN cookies were not cleared")
                    self.cookies.set(
                        "session",
                        "fresh",
                        domain="api.worldquantbrain.com",
                    )
                    return FakeResponse(201)
                values = [
                    cookie.value
                    for cookie in self.cookies
                    if cookie.name == "session"
                ]
                return FakeResponse(200 if values == ["fresh"] else 401)

        session = CookieReplacingSession()
        client = self.auto_auth_client(session)
        prepared = client.prepare(
            client.registry.get("/simulations/{simulation_id}"),
            "GET",
            path_vars={"simulation_id": "demo"},
        )

        result = client.call_once(prepared)

        self.assertEqual(result["response"]["status_code"], 200)
        self.assertEqual(session.calls, 3)

    def test_204_and_429_also_trigger_global_reauthentication(self) -> None:
        for trigger in (204, 429):
            with self.subTest(trigger=trigger):
                session = SequenceSession(
                    [
                        FakeResponse(trigger),
                        FakeResponse(201),
                        FakeResponse(200, {"status": "PENDING"}),
                    ]
                )
                client = self.auto_auth_client(session)
                prepared = client.prepare(
                    client.registry.get("/simulations/{simulation_id}"),
                    "GET",
                    path_vars={"simulation_id": "demo"},
                )

                result = client.call_once(prepared)

                self.assertEqual(result["response"]["status_code"], 200)
                event = result["response"]["authentication"]["events"][0]
                self.assertEqual(event["trigger_status"], trigger)

    def test_authentication_retries_before_replaying_request(self) -> None:
        session = SequenceSession(
            [
                FakeResponse(429),
                FakeResponse(429),
                FakeResponse(201),
                FakeResponse(200),
            ]
        )
        client = self.auto_auth_client(session)
        prepared = client.prepare(
            client.registry.get("/simulations/{simulation_id}"),
            "GET",
            path_vars={"simulation_id": "demo"},
        )

        result = client.call_once(prepared)

        attempts = result["response"]["authentication"]["events"][0]["refresh"]["attempts"]
        self.assertEqual([attempt["status_code"] for attempt in attempts], [429, 201])
        self.assertEqual(result["response"]["status_code"], 200)

    def test_authentication_endpoint_does_not_recursively_reauthenticate(self) -> None:
        session = SequenceSession([FakeResponse(401)])
        client = self.auto_auth_client(session)
        prepared = client.prepare(
            client.registry.get("/authentication"),
            "POST",
            json_body={
                "email": "researcher@example.com",
                "password": "secret",
                "expiry": 3600,
            },
        )

        result = client.call_once(prepared)

        self.assertEqual(result["response"]["status_code"], 401)
        self.assertNotIn("authentication", result["response"])
        self.assertEqual(len(session.calls), 1)

    def test_mutating_204_reauthenticates_like_wqb_session(self) -> None:
        session = SequenceSession(
            [
                FakeResponse(204),
                FakeResponse(201),
                FakeResponse(201),
            ]
        )
        client = self.auto_auth_client(session)
        prepared = client.prepare(
            client.registry.get("/simulations"),
            "POST",
            json_body={"type": "REGULAR"},
        )

        result = client.call_once(prepared)

        self.assertTrue(result["ok"])
        self.assertEqual(result["response"]["status_code"], 201)
        self.assertEqual([call[0][0] for call in session.calls], ["POST", "POST", "POST"])

    def test_per_call_auto_auth_override_bypasses_reauthentication(self) -> None:
        session = SequenceSession([FakeResponse(401)])
        client = self.auto_auth_client(session)
        prepared = client.prepare(
            client.registry.get("/simulations/{simulation_id}"),
            "GET",
            path_vars={"simulation_id": "demo"},
        )

        result = client.call_once(prepared, auto_auth=False)

        self.assertEqual(result["response"]["status_code"], 401)
        self.assertEqual(len(session.calls), 1)
        self.assertNotIn("authentication", result["response"])

    def test_login_requires_wqb_sessions_expected_201_status(self) -> None:
        session = SequenceSession([FakeResponse(204)])
        client = self.auto_auth_client(session)
        prepared = client.prepare(
            client.registry.get("/authentication"),
            "POST",
            json_body={
                "email": "researcher@example.com",
                "password": "secret",
                "expiry": 3600,
            },
        )

        result = client.call_once(prepared)

        self.assertFalse(result["ok"])
        self.assertEqual(result["response"]["status_code"], 204)

    def test_global_reauthentication_has_strict_attempt_bounds(self) -> None:
        policy = AutoAuthPolicy(request_replays=2, login_attempts=2, delay_seconds=0)
        session = SequenceSession(
            [
                FakeResponse(401),
                FakeResponse(401),
                FakeResponse(401),
                FakeResponse(401),
                FakeResponse(401),
                FakeResponse(401),
                FakeResponse(401),
            ]
        )
        client = self.auto_auth_client(session, policy=policy)
        prepared = client.prepare(
            client.registry.get("/simulations/{simulation_id}"),
            "GET",
            path_vars={"simulation_id": "demo"},
        )

        result = client.call_once(prepared)

        authentication = result["response"]["authentication"]
        self.assertEqual(authentication["replays"], 2)
        self.assertTrue(authentication["exhausted"])
        self.assertEqual(len(authentication["events"]), 2)
        self.assertEqual(
            [len(event["refresh"]["attempts"]) for event in authentication["events"]],
            [2, 2],
        )
        self.assertEqual(len(session.calls), 7)

    def test_concurrent_401_responses_share_one_login(self) -> None:
        class ConcurrentSession:
            def __init__(self) -> None:
                self.barrier = threading.Barrier(2)
                self.lock = threading.Lock()
                self.get_calls = 0
                self.auth_calls = 0

            def request(self, method: str, *args: Any, **kwargs: Any) -> FakeResponse:
                if method == "POST":
                    with self.lock:
                        self.auth_calls += 1
                    return FakeResponse(201)
                with self.lock:
                    self.get_calls += 1
                    call_number = self.get_calls
                if call_number <= 2:
                    self.barrier.wait(timeout=2)
                    return FakeResponse(401)
                return FakeResponse(200)

        session = ConcurrentSession()
        client = self.auto_auth_client(session)
        prepared = client.prepare(
            client.registry.get("/simulations/{simulation_id}"),
            "GET",
            path_vars={"simulation_id": "demo"},
        )
        results: list[dict[str, Any]] = []

        threads = [threading.Thread(target=lambda: results.append(client.call_once(prepared))) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=3)

        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(session.auth_calls, 1)
        self.assertEqual([result["response"]["status_code"] for result in results], [200, 200])
        refreshes = [result["response"]["authentication"]["events"][0]["refresh"] for result in results]
        self.assertEqual(sum(1 for refresh in refreshes if refresh["shared"]), 1)


if __name__ == "__main__":
    unittest.main()
