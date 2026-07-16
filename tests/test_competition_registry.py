from __future__ import annotations

import unittest

import requests

from wqb_cli.core.client import WqbClient
from wqb_cli.core.registry import EndpointRegistry


class CompetitionRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = EndpointRegistry.load()
        self.client = WqbClient(self.registry, requests.Session())

    def test_generic_and_spc_endpoints_are_registered(self) -> None:
        expected = {
            "/competitions/{competition_id}/boards/{board_type}": ("GET",),
            "/competitions/spc/submissions": ("GET", "POST"),
            "/competitions/spc/submissions/{submission_id}": ("GET", "PUT", "PATCH"),
            "/consultant/boards/{board_type}": ("GET",),
            "/consultant/boards/spc": ("GET",),
        }
        for path, methods in expected.items():
            self.assertEqual(self.registry.get(path).methods, methods)

        self.assertNotIn("DELETE", self.registry.get("/competitions/spc/submissions/{submission_id}").methods)

    def test_generic_leaderboard_paths_prepare_without_path_injection(self) -> None:
        competition = self.client.prepare(
            self.registry.get("/competitions/{competition_id}/boards/{board_type}"),
            "GET",
            path_vars={"competition_id": "PAC2026", "board_type": "leader"},
        )
        self.assertEqual(
            competition.url,
            "https://api.worldquantbrain.com/competitions/PAC2026/boards/leader",
        )

        consultant = self.client.prepare(
            self.registry.get("/consultant/boards/{board_type}"),
            "GET",
            path_vars={"board_type": "spc"},
        )
        self.assertEqual(consultant.url, "https://api.worldquantbrain.com/consultant/boards/spc")

    def test_spc_submission_item_prepares_canonical_url(self) -> None:
        prepared = self.client.prepare(
            self.registry.get("/competitions/spc/submissions/{submission_id}"),
            "PATCH",
            path_vars={"submission_id": "submission-id"},
            json_body={"weight": 0.5},
        )
        self.assertEqual(
            prepared.url,
            "https://api.worldquantbrain.com/competitions/spc/submissions/submission-id",
        )
        self.assertTrue(prepared.mutating)


if __name__ == "__main__":
    unittest.main()
