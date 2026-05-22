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


if __name__ == "__main__":
    unittest.main()
