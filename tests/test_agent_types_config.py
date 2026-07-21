from __future__ import annotations

import json
import re
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path

import wqb_cli.agent.config as agent_config
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
    def test_direct_scope_mode_must_be_enum(self) -> None:
        for value in ("manual", "invalid"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "scope_mode"):
                    RunConfig(scope_mode=value)  # type: ignore[arg-type]

    def test_direct_budget_must_be_budget(self) -> None:
        with self.assertRaisesRegex(ValueError, "budget"):
            RunConfig(scope_mode=ScopeMode.AUTO, budget={})  # type: ignore[arg-type]

    def test_manual_scope_requires_nonblank_text_fields(self) -> None:
        defaults: dict[str, object] = {
            "scope_mode": ScopeMode.MANUAL,
            "region": "USA",
            "delay": 1,
            "universe": "TOP3000",
            "neutralization": "INDUSTRY",
        }
        for field in ("region", "universe", "neutralization"):
            for value in ("", " ", 1):
                with self.subTest(field=field, value=value):
                    values = {**defaults, field: value}
                    with self.assertRaisesRegex(ValueError, "manual scope requires"):
                        RunConfig(**values)  # type: ignore[arg-type]

    def test_manual_delay_must_be_platform_integer(self) -> None:
        defaults: dict[str, object] = {
            "scope_mode": ScopeMode.MANUAL,
            "region": "USA",
            "universe": "TOP3000",
            "neutralization": "INDUSTRY",
        }
        for value in (True, 1.0, "1", 2):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "manual scope requires"):
                    RunConfig(**defaults, delay=value)  # type: ignore[arg-type]
        for value in (0, 1):
            with self.subTest(valid=value):
                self.assertEqual(RunConfig(**defaults, delay=value).delay, value)  # type: ignore[arg-type]

    def test_direct_manual_scope_requires_all_market_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "manual scope requires"):
            RunConfig(scope_mode=ScopeMode.MANUAL)

    def test_direct_auto_scope_allows_a_region_constraint(self) -> None:
        config = RunConfig(scope_mode=ScopeMode.AUTO, region="USA")
        self.assertEqual(config.region, "USA")

    def test_direct_auto_scope_rejects_other_pinned_market_fields(self) -> None:
        for field, value in (("delay", 1), ("universe", "TOP3000"), ("neutralization", "FAST")):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "auto scope must not pin"):
                    RunConfig(scope_mode=ScopeMode.AUTO, **{field: value})  # type: ignore[arg-type]

    def test_manual_scope_requires_all_market_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "manual scope requires"):
            RunConfig.from_dict({"scope_mode": "manual", "region": "USA"})

    def test_auto_scope_accepts_region_but_rejects_blank_region(self) -> None:
        self.assertEqual(
            RunConfig.from_dict({"scope_mode": "auto", "region": "USA"}).region,
            "USA",
        )
        with self.assertRaisesRegex(ValueError, "auto scope region"):
            RunConfig.from_dict({"scope_mode": "auto", "region": " "})

    def test_run_config_round_trips_through_asdict(self) -> None:
        original = RunConfig.from_dict(
            {
                "scope_mode": "manual",
                "region": "USA",
                "delay": 1,
                "universe": "TOP3000",
                "neutralization": "INDUSTRY",
                "budget": {"rounds": 3, "total_simulations": 24},
            }
        )

        restored = RunConfig.from_dict(asdict(original))

        self.assertEqual(restored, original)
        self.assertIs(restored.scope_mode, ScopeMode.MANUAL)
        self.assertIsInstance(restored.budget, Budget)

    def test_domain_enums_and_node_result_defaults(self) -> None:
        self.assertEqual(ModelRole.PLANNER.value, "planner")
        self.assertEqual(ScopeMode.AUTO.value, "auto")
        self.assertEqual(RunState.STOPPED.value, "STOPPED")
        self.assertEqual(RunState.CREATED.value, "CREATED")
        self.assertEqual(WorkflowNode.M.value, "M")
        result = NodeResult(node=WorkflowNode.A, summary={"count": 1})
        self.assertEqual(result.artifact_ids, ())
        self.assertIsNone(result.next_node)
        self.assertIsNone(result.run_state)
        self.assertEqual(result.payload, {})


class BudgetTests(unittest.TestCase):
    def test_budget_limits_must_be_positive(self) -> None:
        fields = (
            "candidates_per_round",
            "rounds",
            "total_simulations",
        )
        for field in fields:
            for value in (0, -1):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        Budget(**{field: value})

    def test_budget_limits_require_exact_integer_types(self) -> None:
        fields = (
            "candidates_per_round",
            "rounds",
            "total_simulations",
        )
        for field in fields:
            for value in (True, 1.5):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        Budget(**{field: value})

class AgentConfigTests(unittest.TestCase):
    def assert_config_error(
        self,
        payload: object,
        dotted_path: str,
        *,
        require_models: bool = False,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, re.escape(dotted_path)):
                load_agent_config(str(path), require_models=require_models)

    def load_payload(self, payload: object):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return load_agent_config(str(path))

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
                        "connect_timeout_seconds": 10,
                        "read_timeout_seconds": 300,
                        "proxy_mode": "system",
                        "proxy_url": "",
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
                        "connect_timeout_seconds": 10,
                        "read_timeout_seconds": 300,
                        "proxy_mode": "system",
                        "proxy_url": "",
                        "input_cost_per_million": None,
                        "output_cost_per_million": None,
                    },
                },
                "budget": {
                    "candidates_per_round": 8,
                    "rounds": 5,
                    "total_simulations": 40,
                },
            },
        )

    def test_defaults_are_role_specific_and_use_default_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = load_agent_config(str(Path(tmp) / "missing-config.json"))

        self.assertEqual(config.models[ModelRole.PLANNER].api_style, "responses")
        self.assertEqual(config.models[ModelRole.OPERATOR].api_style, "chat_completions")
        self.assertEqual(config.budget.total_simulations, 40)
        self.assertEqual(config.run_root.name, "research_runs")
        self.assertEqual(config.database_path.name, "agent.sqlite3")

    def test_model_overrides_change_only_model_ids(self) -> None:
        original = self.load_payload(
            {"agent": {"models": {"operator": {"base_url": "https://models.example/v1"}}}}
        )

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

    def test_model_overrides_validate_resulting_routes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original = load_agent_config(str(Path(tmp) / "missing-config.json"))

        with self.assertRaisesRegex(ValueError, re.escape("agent.models.operator.base_url")):
            with_model_overrides(original, operator_model="operator-x")

    def test_both_model_overrides_can_satisfy_required_models(self) -> None:
        original = self.load_payload(
            {"agent": {"models": {"operator": {"base_url": "https://models.example/v1"}}}}
        )

        updated = with_model_overrides(
            original,
            planner_model="planner-x",
            operator_model="operator-x",
            require_models=True,
        )

        self.assertIs(agent_config.validate_agent_config(updated, require_models=True), updated)

    def test_partial_model_override_names_missing_role_when_required(self) -> None:
        original = self.load_payload(
            {"agent": {"models": {"operator": {"base_url": "https://models.example/v1"}}}}
        )

        with self.assertRaisesRegex(ValueError, "operator"):
            with_model_overrides(original, planner_model="planner-x", require_models=True)

    def test_required_models_names_each_missing_role(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "planner.*operator"):
                load_agent_config(
                    str(Path(tmp) / "missing-config.json"), require_models=True
                )

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

    def test_config_objects_have_deliberate_shape_errors(self) -> None:
        cases = (
            ({"agent": None}, "agent"),
            ({"agent": {"models": None}}, "agent.models"),
            ({"agent": {"models": {"planner": None}}}, "agent.models.planner"),
            ({"agent": {"budget": None}}, "agent.budget"),
        )
        for payload, dotted_path in cases:
            with self.subTest(dotted_path=dotted_path):
                self.assert_config_error(payload, dotted_path)

    def test_unknown_config_keys_are_rejected_with_paths(self) -> None:
        cases = (
            ({"agent": {"models": {"reviewer": {}}}}, "agent.models.reviewer"),
            ({"agent": {"models": {"planner": {"temperature": 1}}}}, "agent.models.planner.temperature"),
            ({"agent": {"budget": {"spare_calls": 1}}}, "agent.budget.spare_calls"),
        )
        for payload, dotted_path in cases:
            with self.subTest(dotted_path=dotted_path):
                self.assert_config_error(payload, dotted_path)

    def test_unknown_agent_root_keys_are_rejected_with_paths(self) -> None:
        cases = ("databse_path", "model")
        for field in cases:
            dotted_path = f"agent.{field}"
            with self.subTest(dotted_path=dotted_path):
                self.assert_config_error({"agent": {field: "value"}}, dotted_path)

    def test_typed_config_requires_exact_model_role_keys_before_overrides(self) -> None:
        base = load_agent_config(None)
        planner = base.models[ModelRole.PLANNER]
        operator = base.models[ModelRole.OPERATOR]
        cases = (
            (
                "plain strings",
                {"planner": planner, "operator": operator},
                "agent.models.planner",
            ),
            ("unrelated", {"reviewer": planner}, "agent.models.reviewer"),
            ("missing", {ModelRole.PLANNER: planner}, "agent.models.operator"),
            (
                "extra",
                {**base.models, "reviewer": planner},
                "agent.models.reviewer",
            ),
        )
        for label, models, dotted_path in cases:
            invalid = replace(base, models=models)  # type: ignore[arg-type]
            for operation in (
                lambda: agent_config.validate_agent_config(invalid, require_models=False),
                lambda: with_model_overrides(invalid),
            ):
                with self.subTest(label=label, operation=operation.__code__.co_firstlineno):
                    with self.assertRaisesRegex(ValueError, re.escape(dotted_path)):
                        operation()

    def test_configured_model_base_url_must_be_absolute_http_url(self) -> None:
        invalid_urls = (
            "models.example/v1",
            "/v1",
            "ftp://models.example/v1",
            "https:///v1",
            "https://",
        )
        for value in invalid_urls:
            with self.subTest(value=value):
                self.assert_config_error(
                    {
                        "agent": {
                            "models": {
                                "planner": {"model": "planner-x", "base_url": value}
                            }
                        }
                    },
                    "agent.models.planner.base_url",
                )

    def test_configured_model_accepts_absolute_http_urls(self) -> None:
        for value in ("https://models.example/v1", "http://localhost:8000/v1"):
            with self.subTest(value=value):
                config = self.load_payload(
                    {
                        "agent": {
                            "models": {
                                "planner": {"model": "planner-x", "base_url": value}
                            }
                        }
                    }
                )
                self.assertEqual(config.models[ModelRole.PLANNER].base_url, value)

    def test_model_fields_require_deliberate_types(self) -> None:
        cases = (
            ("provider", 1),
            ("api_style", 1),
            ("model", 1),
            ("base_url", 1),
            ("reasoning", 1),
            ("secret_name", 1),
            ("fallback_model", 1),
            ("structured_outputs", "true"),
            ("input_cost_per_million", True),
            ("output_cost_per_million", float("nan")),
        )
        for field, value in cases:
            dotted_path = f"agent.models.planner.{field}"
            with self.subTest(dotted_path=dotted_path):
                self.assert_config_error(
                    {"agent": {"models": {"planner": {field: value}}}},
                    dotted_path,
                )

    def test_configured_paths_reject_non_path_values(self) -> None:
        cases = (
            ("database_path", []),
            ("run_root", {}),
            ("run_root", True),
        )
        for field, value in cases:
            dotted_path = f"agent.{field}"
            with self.subTest(dotted_path=dotted_path, value=value):
                self.assert_config_error({"agent": {field: value}}, dotted_path)

    def test_budget_values_report_dotted_paths(self) -> None:
        cases = (
            ("rounds", True),
            ("total_simulations", 1.5),
        )
        for field, value in cases:
            dotted_path = f"agent.budget.{field}"
            with self.subTest(dotted_path=dotted_path):
                self.assert_config_error({"agent": {"budget": {field: value}}}, dotted_path)

    def test_legacy_budget_termination_fields_are_ignored(self) -> None:
        config = self.load_payload({"agent": {"budget": {
            "max_runtime_minutes": 1,
            "planner_calls": 1,
            "operator_calls": 1,
            "max_model_cost_usd": 0,
        }}})
        self.assertEqual(
            asdict(config.budget),
            {"candidates_per_round": 8, "rounds": 5, "total_simulations": 40},
        )

    def test_whitespace_model_is_missing_when_required(self) -> None:
        self.assert_config_error(
            {
                "agent": {
                    "models": {
                        "planner": {"model": "   "},
                        "operator": {"model": "operator-x", "base_url": "https://models.example/v1"},
                    }
                }
            },
            "planner",
            require_models=True,
        )

    def test_configured_models_require_route_and_secret(self) -> None:
        cases = (
            (
                {"agent": {"models": {"operator": {"model": "operator-x"}}}},
                "agent.models.operator.base_url",
            ),
            (
                {"agent": {"models": {"planner": {"model": "planner-x", "secret_name": " "}}}},
                "agent.models.planner.secret_name",
            ),
        )
        for payload, dotted_path in cases:
            with self.subTest(dotted_path=dotted_path):
                self.assert_config_error(payload, dotted_path)

    def test_legacy_config_without_agent_section_uses_agent_defaults(self) -> None:
        config = self.load_payload({"defaults": {"region": "CHN"}})

        self.assertEqual(config.models[ModelRole.PLANNER].provider, "openai")
        self.assertEqual(config.budget, Budget())


if __name__ == "__main__":
    unittest.main()
