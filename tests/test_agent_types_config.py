from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from wqb_cli.agent.config import load_agent_config, with_model_overrides
from wqb_cli.agent.types import (
    Budget,
    ModelRole,
    NodeResult,
    RunConfig,
    RunState,
    ScopeMode,
    WorkflowNode,
)
from wqb_cli.core.config_store import DEFAULT_CONFIG


class RunConfigTests(unittest.TestCase):
    def test_direct_manual_scope_requires_all_market_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "manual scope requires"):
            RunConfig(scope_mode=ScopeMode.MANUAL)

    def test_direct_auto_scope_rejects_pinned_market_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "auto scope must not pin"):
            RunConfig(scope_mode=ScopeMode.AUTO, region="USA")

    def test_manual_scope_requires_all_market_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "manual scope requires"):
            RunConfig.from_dict({"scope_mode": "manual", "region": "USA"})

    def test_auto_scope_rejects_partial_pinned_market_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "auto scope must not pin"):
            RunConfig.from_dict({"scope_mode": "auto", "region": "USA"})

    def test_run_config_round_trips_through_asdict(self) -> None:
        original = RunConfig.from_dict(
            {
                "scope_mode": "manual",
                "region": "USA",
                "delay": 1,
                "universe": "TOP3000",
                "neutralization": "INDUSTRY",
                "budget": {"rounds": 3, "max_model_cost_usd": 1.25},
            }
        )

        restored = RunConfig.from_dict(asdict(original))

        self.assertEqual(restored, original)
        self.assertIs(restored.scope_mode, ScopeMode.MANUAL)
        self.assertIsInstance(restored.budget, Budget)

    def test_domain_enums_and_node_result_defaults(self) -> None:
        self.assertEqual(ModelRole.PLANNER.value, "planner")
        self.assertEqual(ScopeMode.AUTO.value, "auto")
        self.assertEqual(RunState.CREATED.value, "CREATED")
        self.assertEqual(WorkflowNode.M.value, "M")
        result = NodeResult(node=WorkflowNode.A, summary={"count": 1})
        self.assertEqual(result.artifact_ids, ())
        self.assertIsNone(result.next_node)
        self.assertIsNone(result.run_state)
        self.assertEqual(result.payload, {})


class BudgetTests(unittest.TestCase):
    def test_count_and_time_limits_must_be_positive(self) -> None:
        fields = (
            "candidates_per_round",
            "rounds",
            "total_simulations",
            "max_runtime_minutes",
            "planner_calls",
            "operator_calls",
        )
        for field in fields:
            for value in (0, -1):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        Budget(**{field: value})

    def test_model_cost_must_be_none_or_non_negative(self) -> None:
        self.assertIsNone(Budget(max_model_cost_usd=None).max_model_cost_usd)
        self.assertEqual(Budget(max_model_cost_usd=0).max_model_cost_usd, 0)
        with self.assertRaises(ValueError):
            Budget(max_model_cost_usd=-0.01)


class AgentConfigTests(unittest.TestCase):
    def test_default_config_has_complete_agent_section(self) -> None:
        self.assertEqual(
            DEFAULT_CONFIG["agent"],
            {
                "database_path": "",
                "run_root": "",
                "models": {
                    "planner": {
                        "provider": "openai",
                        "api_style": "responses",
                        "model": "",
                        "base_url": "https://api.openai.com/v1",
                        "reasoning": "high",
                        "secret_name": "agent-planner-api-key",
                        "structured_outputs": True,
                        "fallback_model": "",
                        "input_cost_per_million": None,
                        "output_cost_per_million": None,
                    },
                    "operator": {
                        "provider": "openai-compatible",
                        "api_style": "chat_completions",
                        "model": "",
                        "base_url": "",
                        "reasoning": "",
                        "secret_name": "agent-operator-api-key",
                        "structured_outputs": True,
                        "fallback_model": "",
                        "input_cost_per_million": None,
                        "output_cost_per_million": None,
                    },
                },
                "budget": {
                    "candidates_per_round": 8,
                    "rounds": 5,
                    "total_simulations": 40,
                    "max_runtime_minutes": 180,
                    "planner_calls": 20,
                    "operator_calls": 100,
                    "max_model_cost_usd": None,
                },
            },
        )

    def test_defaults_are_role_specific_and_use_default_paths(self) -> None:
        config = load_agent_config(None)

        self.assertEqual(config.models[ModelRole.PLANNER].api_style, "responses")
        self.assertEqual(config.models[ModelRole.OPERATOR].api_style, "chat_completions")
        self.assertEqual(config.budget.total_simulations, 40)
        self.assertEqual(config.run_root.name, "research_runs")
        self.assertEqual(config.database_path.name, "agent.sqlite3")

    def test_model_overrides_change_only_model_ids(self) -> None:
        original = load_agent_config(None)

        updated = with_model_overrides(
            original,
            planner_model="planner-x",
            operator_model="operator-y",
        )

        self.assertEqual(updated.models[ModelRole.PLANNER].model, "planner-x")
        self.assertEqual(updated.models[ModelRole.OPERATOR].model, "operator-y")
        for role in ModelRole:
            before = asdict(original.models[role])
            after = asdict(updated.models[role])
            before.pop("model")
            after.pop("model")
            self.assertEqual(after, before)
        self.assertEqual(updated.database_path, original.database_path)
        self.assertEqual(updated.run_root, original.run_root)
        self.assertEqual(updated.budget, original.budget)

    def test_required_models_names_each_missing_role(self) -> None:
        with self.assertRaisesRegex(ValueError, "planner.*operator"):
            load_agent_config(None, require_models=True)

    def test_invalid_route_and_pricing_values_are_rejected(self) -> None:
        cases = (
            ("agent.models.planner.provider", "other"),
            ("agent.models.operator.api_style", "legacy"),
            ("agent.models.planner.input_cost_per_million", -1),
            ("agent.models.operator.output_cost_per_million", -1),
            ("agent.models.planner.fallback_model", "planner-fallback"),
        )
        for dotted_key, value in cases:
            with self.subTest(dotted_key=dotted_key):
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "config.json"
                    root: dict[str, object] = {}
                    current = root
                    parts = dotted_key.split(".")
                    for part in parts[:-1]:
                        child: dict[str, object] = {}
                        current[part] = child
                        current = child
                    current[parts[-1]] = value
                    path.write_text(json.dumps(root), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_agent_config(str(path))

    def test_operator_allows_same_role_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(
                json.dumps({"agent": {"models": {"operator": {"fallback_model": "operator-lite"}}}}),
                encoding="utf-8",
            )

            config = load_agent_config(str(path))

        self.assertEqual(config.models[ModelRole.OPERATOR].fallback_model, "operator-lite")


if __name__ == "__main__":
    unittest.main()
