from __future__ import annotations

import unittest

import requests

from wqb_cli.core.client import WqbClient
from wqb_cli.core.registry import EndpointRegistry


class ClientPrepareTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
