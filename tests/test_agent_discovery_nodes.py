from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from wqb_cli.agent.nodes.discovery import DiscoveryNodes
from wqb_cli.agent.types import RunConfig, RunState, WorkflowNode


def planner_choice(candidate_id: str) -> dict[str, object]:
    return {
        "decision": "choose tower",
        "reasoning_summary": "Unlit candidate is the best current-quarter target.",
        "evidence_refs": ["artifact:quarter"],
        "confidence": 0.9,
        "scope_decision": {"candidate_id": candidate_id},
    }


class DiscoveryNodeTests(unittest.TestCase):
    def test_a_pauses_when_authentication_is_missing(self) -> None:
        runner = Mock()
        runner.run.return_value.payload = {
            "ok": False,
            "response": {"status_code": 401, "body": {}},
        }

        result = DiscoveryNodes(runner=runner, router=Mock(), store=Mock()).run_a("run-1")

        self.assertEqual(result.node, WorkflowNode.A)
        self.assertEqual(result.run_state, RunState.NEEDS_AUTH)
        runner.run.assert_called_once_with("run-1", WorkflowNode.A, ("auth", "status"), "auth_status.json")

    def test_manual_d_locks_market_scope_while_planner_selects_category(self) -> None:
        config = RunConfig.from_dict(
            {
                "scope_mode": "manual",
                "region": "USA",
                "delay": 1,
                "universe": "TOP3000",
                "neutralization": "SUBINDUSTRY",
            }
        )
        router = Mock()
        router.invoke.return_value.value = planner_choice("USA_D1_PV")
        candidates = {
            "quarter_towers": [
                {
                    "candidate_id": "USA_D1_PV",
                    "region": "USA",
                    "delay": 1,
                    "universe": "TOP3000",
                    "neutralization": "SUBINDUSTRY",
                    "category": "PV",
                    "alphaCount": 1,
                }
            ],
            "sim_options": {
                "regions": ["USA"],
                "delays": [1],
                "universes": ["TOP3000"],
                "neutralizations": ["SUBINDUSTRY"],
            },
        }

        result = DiscoveryNodes(runner=Mock(), router=router, store=Mock()).run_d(
            "run-1", config, candidates
        )

        self.assertEqual(
            result.summary["scope"],
            {
                "region": "USA",
                "delay": 1,
                "universe": "TOP3000",
                "neutralization": "SUBINDUSTRY",
                "category": "PV",
            },
        )
        router.invoke.assert_called_once()

    def test_auto_d_uses_planner_only_after_validating_candidates(self) -> None:
        router = Mock()
        router.invoke.return_value.value = planner_choice("USA_D1_PV")
        candidates = {
            "quarter_towers": [
                {
                    "candidate_id": "USA_D1_PV",
                    "region": "USA",
                    "delay": 1,
                    "universe": "TOP3000",
                    "neutralization": "SUBINDUSTRY",
                    "category": "PV",
                    "alphaCount": 0,
                }
            ],
            "sim_options": {
                "regions": ["USA"],
                "delays": [1],
                "universes": ["TOP3000"],
                "neutralizations": ["SUBINDUSTRY"],
            },
        }

        result = DiscoveryNodes(runner=Mock(), router=router, store=Mock()).run_d(
            "run-1", RunConfig.from_dict({"scope_mode": "auto"}), candidates
        )

        self.assertEqual(result.summary["scope"]["category"], "PV")
        router.invoke.assert_called_once()

    def test_d_rejects_planner_candidate_outside_validated_list(self) -> None:
        router = Mock()
        router.invoke.return_value.value = planner_choice("not-supplied")
        candidates = {
            "quarter_towers": [
                {
                    "candidate_id": "USA_D1_PV",
                    "region": "USA",
                    "delay": 1,
                    "universe": "TOP3000",
                    "neutralization": "SUBINDUSTRY",
                    "category": "PV",
                    "alphaCount": 0,
                }
            ],
            "sim_options": {"regions": ["USA"], "delays": [1], "universes": ["TOP3000"], "neutralizations": ["SUBINDUSTRY"]},
        }

        with self.assertRaisesRegex(ValueError, "supplied candidates"):
            DiscoveryNodes(runner=Mock(), router=router, store=Mock()).run_d(
                "run-1", RunConfig.from_dict({"scope_mode": "auto"}), candidates
            )

    def test_d_fails_closed_without_prevalidated_platform_scope_options(self) -> None:
        candidates = {
            "quarter_towers": [
                {
                    "candidate_id": "USA_D1_PV", "region": "USA", "delay": 1,
                    "universe": "TOP3000", "neutralization": "SUBINDUSTRY", "category": "PV",
                }
            ]
        }

        with self.assertRaisesRegex(ValueError, "validated platform options"):
            DiscoveryNodes(runner=Mock(), router=Mock(), store=Mock()).run_d(
                "run-1", RunConfig.from_dict({"scope_mode": "auto"}), candidates
            )

    def test_c_uses_exact_eastern_day_interval_and_remaining_regular_quota(self) -> None:
        runner = Mock()
        runner.run.side_effect = [
            Mock(payload={"ok": True, "response": {"status_code": 200, "body": {"results": [{"id": "alpha-a"}, {"id": "alpha-b"}]}}}),
            Mock(payload={"ok": True, "response": {"status_code": 200, "body": {"results": [{"id": "alpha-a"}]}}}),
            Mock(payload={"ok": True, "response": {"status_code": 200, "body": {"results": [{"id": "alpha-b"}]}}}),
            Mock(payload={"ok": True, "response": {"status_code": 200, "body": {}}}),
            Mock(payload={"ok": True, "response": {"status_code": 200, "body": {}}}),
            Mock(payload={"ok": True, "response": {"status_code": 200, "body": {}}}),
        ]

        result = DiscoveryNodes(runner=runner, router=Mock(), store=Mock(), regular_daily_quota=3).run_c(
            "run-1", now=lambda: datetime(2026, 7, 1, 4, 30, tzinfo=timezone.utc)
        )

        self.assertEqual(result.summary["regular_remaining"], 2)
        self.assertEqual(result.summary["submission_day"], "2026-07-01")
        self.assertIn("2026-07-01T00:00:00-04:00", runner.run.call_args_list[0].args[2])

    def test_b_collects_platform_data_then_uses_operator_before_planner(self) -> None:
        runner = Mock()
        runner.run.return_value.payload = {"ok": True, "response": {"status_code": 200, "body": {}}}
        router = Mock()
        router.invoke.side_effect = [
            Mock(value={"decision": "organized", "reasoning_summary": "No active themes.", "evidence_refs": ["artifact:1"], "confidence": 0.5, "task_result": {"status": "COMPLETED", "payload": {}}}),
            Mock(value={"decision": "ranked", "reasoning_summary": "Prioritize available regular capacity.", "evidence_refs": ["artifact:1"], "confidence": 0.5}),
        ]

        result = DiscoveryNodes(runner=runner, router=router, store=Mock()).run_b(
            "run-1", now=lambda: datetime(2026, 7, 1, tzinfo=timezone.utc)
        )

        self.assertEqual(result.node, WorkflowNode.B)
        self.assertEqual(result.next_node, WorkflowNode.C)
        self.assertEqual(router.invoke.call_args_list[0].args[0].role.value, "operator")
        self.assertEqual(router.invoke.call_args_list[1].args[0].role.value, "planner")
        self.assertEqual(runner.run.call_count, 6)


if __name__ == "__main__":
    unittest.main()
