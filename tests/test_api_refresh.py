import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from wqb_cli.cli import build_parser, handle_api
from wqb_cli.commands.user import handle_user
from wqb_cli.core.registry import EndpointRegistry


class ApiRefreshTests(unittest.TestCase):
    def test_raw_mutating_preview_never_sends_http(self):
        arguments = build_parser().parse_args([
            "api", "call", "POST", "/users/{user_id}/osmosis/scale-points", "--var", "user_id=self", "--dry-run",
        ])
        with patch("wqb_cli.cli.session_from_cookies"), \
             patch("wqb_cli.cli.WqbClient.call") as send, \
             patch("wqb_cli.cli.write_json") as output:
            self.assertEqual(handle_api(arguments), 0)
        send.assert_not_called()
        preview = output.call_args.args[0]
        self.assertTrue(preview["dry_run"])
        self.assertTrue(preview["request"]["mutating"])
        self.assertTrue(preview["request"]["url"].endswith("/users/self/osmosis/scale-points"))

    def test_registry_copies_and_new_contracts_agree(self):
        directory = Path(__file__).resolve().parents[1] / "resources/api_inventory"
        base = json.loads((directory / "api_inventory.json").read_text(encoding="utf-8"))
        complete = json.loads((directory / "api_inventory_complete.json").read_text(encoding="utf-8"))
        self.assertEqual(base["endpoints"], complete["endpoints"])
        self.assertEqual(len(complete["endpoints"]), 127)
        registry = EndpointRegistry(complete)
        self.assertIn("POST", registry.get("/data-fields/{field_id}/visualize").methods)
        self.assertEqual(registry.get("/users/{user_id}/osmosis/scale-points/ALL").raw["success_statuses_by_method"], {"GET": [200, 204]})
        self.assertFalse(registry.get("/simulations").raw["region_agnostic"]["batch_supported"])
        for endpoint in registry.list():
            self.assertNotIn('"choices"', json.dumps(endpoint.raw.get("options_schema", {})))

    def test_named_activity_preserves_path_query_and_failure_exit(self):
        registry = EndpointRegistry.load()
        arguments = build_parser().parse_args([
            "user", "activity", "base-payment", "--user-id", "self", "--param", "date>=2026-09-01",
        ])
        client = Mock()
        client.call.return_value = {"ok": False, "response": {"status_code": 403}}
        with patch("wqb_cli.commands.user.WqbClient", return_value=client), \
             patch("wqb_cli.commands.user.session_from_cookies"), \
             patch("wqb_cli.commands.user.write_json"):
            self.assertEqual(handle_user(arguments, registry), 1)
        positional, keyword = client.prepare.call_args
        self.assertEqual(positional[0].path, "/users/{user_id}/activities/{activity_name}")
        self.assertEqual(positional[1], "GET")
        self.assertEqual(keyword["path_vars"], {"user_id": "self", "activity_name": "base-payment"})
        self.assertEqual(keyword["params"], {"date>": "2026-09-01"})


if __name__ == "__main__":
    unittest.main()
