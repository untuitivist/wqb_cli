from __future__ import annotations

from argparse import Namespace
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from wqb_cli.cli import build_parser
from wqb_cli.commands.agent import handle_agent


class AgentCliTests(unittest.TestCase):
    def test_quant_agent_skill_is_present_and_forbids_direct_submit(self) -> None:
        skill = Path(__file__).resolve().parents[1] / "skills" / "wqb-quant-agent" / "SKILL.md"
        self.assertTrue(skill.exists())
        text = skill.read_text(encoding="utf-8")
        self.assertIn("wqb agent approve", text)
        self.assertIn("Never call `wqb alpha submit` directly", text)
        self.assertIn("planner", text.lower())
        self.assertIn("operator", text.lower())

    def test_manual_run_parser_keeps_handler_validation(self) -> None:
        args = build_parser().parse_args(["agent", "run", "--scope-mode", "manual", "--region", "USA"])
        self.assertEqual(args.agent_command, "run")
        self.assertEqual(args.scope_mode, "manual")

    def test_per_run_model_overrides_parse_independently(self) -> None:
        args = build_parser().parse_args(["agent", "run", "--scope-mode", "auto", "--planner-model", "large", "--operator-model", "small"])
        self.assertEqual(args.planner_model, "large")
        self.assertEqual(args.operator_model, "small")

    @patch("wqb_cli.commands.agent.write_json")
    @patch("wqb_cli.commands.agent.build_service")
    def test_approve_delegates_to_service(self, build_service: Mock, write_json: Mock) -> None:
        build_service.return_value.approve.return_value = {"ok": True, "state": "SUBMITTED"}
        args = build_parser().parse_args(["agent", "approve", "run-1"])
        self.assertEqual(handle_agent(args), 0)
        build_service.return_value.approve.assert_called_once_with("run-1")

    @patch("wqb_cli.commands.agent.write_json")
    @patch("wqb_cli.commands.agent.getpass.getpass", return_value="secret-value")
    @patch("wqb_cli.commands.agent.set_named_secret")
    @patch("wqb_cli.commands.agent.load_agent_config")
    def test_model_set_key_has_no_secret_argument(self, load_config: Mock, set_secret: Mock, getpass: Mock, write_json: Mock) -> None:
        load_config.return_value.models = {
            __import__("wqb_cli.agent.types", fromlist=["ModelRole"]).ModelRole.PLANNER: Mock(secret_name="planner-key")
        }
        set_secret.return_value = {"ok": True}
        args = build_parser().parse_args(["agent", "models", "set-key", "planner"])
        self.assertEqual(handle_agent(args), 0)
        set_secret.assert_called_once_with("planner-key", "secret-value")
        self.assertNotIn("secret-value", repr(args))

    def test_models_set_key_help_exposes_no_api_key_option(self) -> None:
        with self.assertRaises(SystemExit) as error:
            build_parser().parse_args(["agent", "models", "set-key", "--help"])
        self.assertEqual(error.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
