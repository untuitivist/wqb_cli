from __future__ import annotations

from argparse import Namespace
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from wqb_cli.cli import build_parser
from wqb_cli.commands.agent import handle_agent
from wqb_cli.commands.agent_runtime import RuntimeBundle, _Dispatcher


class AgentCliTests(unittest.TestCase):
    def test_runtime_approve_records_exact_report_subject_before_submit(self) -> None:
        bundle = object.__new__(RuntimeBundle)
        bundle.run_id = "run-1"
        bundle.store = Mock()
        bundle.artifacts = Mock()
        bundle.submission = Mock()
        report = {"run_id": "run-1", "terminal_recommendation": {"alpha_id": "ALPHA1"}}
        bundle._final_report_artifact = Mock(return_value=Mock())
        bundle.artifacts.read_json.return_value = report
        bundle.submission.submit.return_value = Mock(run_state=__import__("wqb_cli.agent.types", fromlist=["RunState"]).RunState.SUBMITTED)
        result = bundle.approve("run-1")
        from wqb_cli.agent.reporting import canonical_report_hash
        bundle.store.record_approval.assert_called_once_with("run-1", "ALPHA1", canonical_report_hash(report))
        bundle.submission.submit.assert_called_once_with("run-1", "ALPHA1", report)
        self.assertEqual(result["state"], "SUBMITTED")

    def test_runtime_manual_d_supplies_locked_scope_as_quarter_tower(self) -> None:
        from wqb_cli.agent.types import RunConfig
        dispatcher = object.__new__(_Dispatcher)
        dispatcher.runner = Mock()
        dispatcher.runner.run.side_effect = [Mock(payload={"ok": True}), Mock(payload={"ok": True})]
        dispatcher.artifacts = Mock()
        dispatcher.artifacts.write_json.side_effect = [Mock(id=1), Mock(id=2)]
        dispatcher.store = Mock()
        config = RunConfig.from_dict({"scope_mode": "manual", "region": "USA", "delay": 1, "universe": "TOP3000", "neutralization": "SUBINDUSTRY"})
        dispatcher.store.get_run.return_value = Mock(config=config)
        dispatcher.discovery = Mock()
        dispatcher.discovery.run_d.return_value = Mock()
        dispatcher._user_id = Mock(return_value="user-1")
        dispatcher._run_d("run-1", {})
        candidates = dispatcher.discovery.run_d.call_args.args[2]
        self.assertEqual(candidates["quarter_towers"][0]["region"], "USA")
        self.assertNotIn("candidates", candidates)

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
