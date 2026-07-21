from __future__ import annotations

from argparse import Namespace
from dataclasses import replace
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from wqb_cli.agent.models.base import ModelResponseError, ModelResult
from wqb_cli.agent.types import ModelRole
from wqb_cli.cli import build_parser
from wqb_cli.commands.agent import AgentService, handle_agent, status_projection
from wqb_cli.commands.agent_runtime import RuntimeBundle, _Dispatcher, build_submission_runtime


class AgentCliTests(unittest.TestCase):
    @patch("wqb_cli.commands.agent_runtime.build_model_adapter")
    def test_model_healthcheck_invokes_selected_adapter(self, build_adapter: Mock) -> None:
        adapter = Mock()
        adapter.invoke.return_value = ModelResult({}, 11, 7, 23, "request-1")
        build_adapter.return_value = adapter
        config = Mock()
        config.models = {
            ModelRole.PLANNER: Mock(model="planner-model", api_style="responses")
        }
        service = AgentService(config, Mock(), Namespace())

        result = service.model_healthcheck(ModelRole.PLANNER)

        self.assertTrue(result["ok"])
        self.assertEqual(result["checks"][0]["latency_ms"], 23)
        adapter.invoke.assert_called_once()

    @patch("wqb_cli.commands.agent_runtime.build_model_adapter")
    def test_model_healthcheck_reports_safe_provider_failure(self, build_adapter: Mock) -> None:
        adapter = Mock()
        adapter.invoke.side_effect = ModelResponseError(
            "model provider HTTP 424 (type=api_error) retries exhausted"
        )
        build_adapter.return_value = adapter
        config = Mock()
        config.models = {
            ModelRole.PLANNER: Mock(model="planner-model", api_style="responses")
        }
        service = AgentService(config, Mock(), Namespace())

        result = service.model_healthcheck(ModelRole.PLANNER)

        self.assertFalse(result["ok"])
        self.assertEqual(result["checks"][0]["error_type"], "ModelResponseError")
        self.assertIn("HTTP 424", result["checks"][0]["detail"])

    def test_submission_runtime_does_not_require_model_configuration(self) -> None:
        from wqb_cli.agent.config import load_agent_config
        from wqb_cli.agent.store import AgentStore

        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(Path(tmp) / "agent.sqlite3")
            store.initialize()
            config = load_agent_config(str(Path(tmp) / "missing-config.json"), require_models=False)
            config = replace(config, run_root=Path(tmp) / "runs")

            runtime = build_submission_runtime(config, store, "run-1")

        self.assertIsNone(runtime.coordinator)
        self.assertIsNotNone(runtime.submission)

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
        dispatcher.runner.run.side_effect = [
            Mock(payload={"ok": True}),
            Mock(payload={"ok": True}),
            Mock(
                payload={
                    "ok": True,
                    "response": {
                        "body": {
                            "id": "fundamental6",
                            "category": {"id": "fundamental"},
                            "data": [
                                {
                                    "region": "USA",
                                    "delay": 1,
                                    "universe": "TOP3000",
                                }
                            ],
                        }
                    },
                },
                artifact=Mock(id=3),
            ),
        ]
        dispatcher.artifacts = Mock()
        dispatcher.artifacts.write_json.side_effect = [Mock(id=1), Mock(id=2)]
        dispatcher.store = Mock()
        config = RunConfig.from_dict({"scope_mode": "manual", "region": "USA", "delay": 1, "universe": "TOP3000", "neutralization": "SUBINDUSTRY", "dataset_id": "fundamental6"})
        dispatcher.store.get_run.return_value = Mock(config=config)
        dispatcher.discovery = Mock()
        dispatcher.discovery.run_d.return_value = Mock()
        dispatcher._user_id = Mock(return_value="user-1")
        dispatcher._run_d("run-1", {})
        candidates = dispatcher.discovery.run_d.call_args.args[2]
        self.assertEqual(candidates["quarter_towers"][0]["region"], "USA")
        self.assertEqual(candidates["quarter_towers"][0]["category"], "FUNDAMENTAL")
        self.assertEqual(
            dispatcher.discovery.run_d.call_args.kwargs["dataset_constraint"]
            ["dataset_id"],
            "fundamental6",
        )
        self.assertNotIn("candidates", candidates)

    def test_runtime_operator_loader_accepts_list_response_body(self) -> None:
        dispatcher = object.__new__(_Dispatcher)
        dispatcher.runner = Mock()
        dispatcher.runner.run.return_value = Mock(payload={
            "response": {"body": [
                {"name": "rank", "category": "Cross Sectional", "definition": "rank(x, rate=2)"},
                {"name": "ts_rank", "category": "Time Series", "definition": "ts_rank(x, d)"},
            ]}
        })

        operators = dispatcher._operators("run-1")

        self.assertEqual(set(operators), {"rank", "ts_rank"})
        self.assertEqual(operators["rank"]["arity"], 1)
        self.assertEqual(operators["ts_rank"]["arity"], 2)

    def test_runtime_h_forwards_k_feedback_to_research(self) -> None:
        from wqb_cli.agent.types import WorkflowNode

        dispatcher = object.__new__(_Dispatcher)
        dispatcher.research = Mock()
        dispatcher.research.run_h.return_value = Mock(node=WorkflowNode.H)
        context = {
            "scope": {},
            "current_tower": "REGULAR",
            "candidate_fields": [{"id": "vwap"}],
            "evidence_bundle": {"artifact_id": "artifact:1"},
            "diagnosis": {
                "failure_class": "ECONOMIC_MECHANISM",
                "next_node": "H",
            },
            "metrics": [{"alpha_id": "A1"}],
            "template_density": {"unary:ts_delta": {"tested": 1}},
            "anti_patterns": [{"code": "LOW_FACTOR_DENSITY"}],
        }

        dispatcher.run("run-1", WorkflowNode.H, context)

        self.assertEqual(
            dispatcher.research.run_h.call_args.kwargs["refinement_context"],
            {
                "diagnosis": context["diagnosis"],
                "metrics": context["metrics"],
                "template_density": context["template_density"],
                "anti_patterns": context["anti_patterns"],
            },
        )

    def test_runtime_j_processes_and_persists_one_idea_at_a_time(self) -> None:
        from wqb_cli.agent.nodes.evaluation import SimulationBatchResult
        from wqb_cli.agent.store import AgentStore
        from wqb_cli.agent.types import RunConfig, ScopeMode, WorkflowNode

        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(Path(tmp) / "agent.sqlite3")
            store.initialize()
            store.create_run("run-1", RunConfig(scope_mode=ScopeMode.AUTO))
            mechanisms = [
                {"mechanism_id": "m1", "field_ids": ["vwap"]},
                {"mechanism_id": "m2", "field_ids": ["close"]},
            ]
            store.record_research_plan(
                "run-1", 1, "plan-hash", {"mechanisms": mechanisms}
            )
            for idea in store.sync_research_ideas(
                "run-1", 1, "plan-hash", mechanisms
            ):
                store.set_research_idea_status(
                    "run-1", idea.idea_id, "READY", stage="SIMULATE"
                )
            for mechanism_id, field in (("m1", "vwap"), ("m2", "close")):
                for index, window in enumerate((22, 63, 126, 252), start=1):
                    store.add_candidate(
                        "run-1",
                        f"fp-{mechanism_id}-{index}",
                        {
                            "expression": f"ts_delta({field},{window})",
                            "mechanism_id": mechanism_id,
                            "plan_version": 1,
                            "plan_hash": "plan-hash",
                        },
                    )

            dispatcher = object.__new__(_Dispatcher)
            dispatcher.store = store
            dispatcher.evaluation = Mock()
            dispatcher.evaluation.run_j.side_effect = [
                SimulationBatchResult((), ({"alpha_id": "A1"},), ("fp-m1",), ()),
                SimulationBatchResult((), ({"alpha_id": "A2"},), ("fp-m2",), ()),
            ]

            first = dispatcher._run_j("run-1", {}, {})
            second = dispatcher._run_j("run-1", {}, first.payload)

            self.assertEqual(first.next_node, WorkflowNode.J)
            self.assertEqual(second.next_node, WorkflowNode.K)
            self.assertEqual(
                [item["alpha_id"] for item in second.payload["alpha_results"]],
                ["A1", "A2"],
            )
            self.assertEqual(
                [idea.status for idea in store.list_research_ideas("run-1")],
                ["COMPLETED", "COMPLETED"],
            )
            calls = dispatcher.evaluation.run_j.call_args_list
            self.assertEqual(calls[0].kwargs["idea_id"], "p1:m1")
            self.assertEqual(calls[1].kwargs["idea_id"], "p1:m2")

    def test_runtime_j_backfills_legacy_ideas_and_returns_to_i(self) -> None:
        from wqb_cli.agent.store import AgentStore
        from wqb_cli.agent.types import RunConfig, ScopeMode, WorkflowNode

        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(Path(tmp) / "agent.sqlite3")
            store.initialize()
            store.create_run("run-1", RunConfig(scope_mode=ScopeMode.AUTO))
            mechanisms = [
                {"mechanism_id": "m1", "field_ids": ["vwap"]},
                {"mechanism_id": "m2", "field_ids": ["close"]},
            ]
            store.record_research_plan(
                "run-1", 1, "plan-hash", {"mechanisms": mechanisms}
            )

            dispatcher = object.__new__(_Dispatcher)
            dispatcher.store = store
            dispatcher.evaluation = Mock()

            result = dispatcher._run_j("run-1", {}, {})

            self.assertEqual(result.next_node, WorkflowNode.I)
            self.assertEqual(result.summary["status"], "NEEDS_INSPECTION")
            self.assertEqual(
                [idea.idea_id for idea in store.list_research_ideas("run-1")],
                ["p1:m1", "p1:m2"],
            )
            dispatcher.evaluation.run_j.assert_not_called()

    def test_runtime_j_returns_underfilled_legacy_idea_to_i(self) -> None:
        from wqb_cli.agent.store import AgentStore
        from wqb_cli.agent.types import RunConfig, ScopeMode, WorkflowNode

        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(Path(tmp) / "agent.sqlite3")
            store.initialize()
            store.create_run("run-1", RunConfig(scope_mode=ScopeMode.AUTO))
            mechanisms = [{"mechanism_id": "m1", "field_ids": ["vwap"]}]
            store.record_research_plan(
                "run-1", 1, "plan-hash", {"mechanisms": mechanisms}
            )
            idea = store.sync_research_ideas(
                "run-1", 1, "plan-hash", mechanisms
            )[0]
            store.set_research_idea_status(
                "run-1", idea.idea_id, "READY", stage="SIMULATE"
            )
            for index, window in enumerate((22, 63), start=1):
                store.add_candidate(
                    "run-1",
                    f"fp-{index}",
                    {
                        "expression": f"ts_delta(vwap,{window})",
                        "mechanism_id": "m1",
                    },
                )
            dispatcher = object.__new__(_Dispatcher)
            dispatcher.store = store
            dispatcher.evaluation = Mock()

            result = dispatcher._run_j("run-1", {}, {})

            self.assertEqual(result.next_node, WorkflowNode.I)
            persisted = store.get_research_idea("run-1", "p1:m1")
            self.assertEqual(persisted.status, "PENDING_INSPECT")
            self.assertEqual(persisted.stage, "INSPECT")
            dispatcher.evaluation.run_j.assert_not_called()

    def test_runtime_j_failure_isolated_from_next_ready_idea(self) -> None:
        from wqb_cli.agent.nodes.evaluation import SimulationBatchResult
        from wqb_cli.agent.store import AgentStore
        from wqb_cli.agent.types import RunConfig, ScopeMode, WorkflowNode

        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(Path(tmp) / "agent.sqlite3")
            store.initialize()
            store.create_run("run-1", RunConfig(scope_mode=ScopeMode.AUTO))
            mechanisms = [
                {"mechanism_id": "m1", "field_ids": ["vwap"]},
                {"mechanism_id": "m2", "field_ids": ["close"]},
            ]
            store.record_research_plan(
                "run-1", 1, "plan-hash", {"mechanisms": mechanisms}
            )
            for idea in store.sync_research_ideas(
                "run-1", 1, "plan-hash", mechanisms
            ):
                store.set_research_idea_status(
                    "run-1", idea.idea_id, "READY", stage="SIMULATE"
                )
            for mechanism_id in ("m1", "m2"):
                for index in range(1, 5):
                    store.add_candidate(
                        "run-1",
                        f"fp-{mechanism_id}-{index}",
                        {
                            "expression": f"ts_delta({mechanism_id},{index})",
                            "mechanism_id": mechanism_id,
                        },
                    )

            dispatcher = object.__new__(_Dispatcher)
            dispatcher.store = store
            dispatcher.evaluation = Mock()
            dispatcher.evaluation.run_j.side_effect = [
                RuntimeError("temporary platform failure"),
                SimulationBatchResult((), ({"alpha_id": "A2"},), ("fp-m2",), ()),
            ]

            failed = dispatcher._run_j("run-1", {}, {})
            progressed = dispatcher._run_j("run-1", {}, failed.payload)

            self.assertEqual(failed.next_node, WorkflowNode.J)
            self.assertEqual(progressed.next_node, WorkflowNode.J)
            self.assertEqual(store.get_research_idea("run-1", "p1:m1").status, "ERROR")
            self.assertEqual(store.get_research_idea("run-1", "p1:m2").status, "COMPLETED")
            self.assertEqual(dispatcher.evaluation.run_j.call_args_list[1].kwargs["idea_id"], "p1:m2")

    def test_runtime_j_pauses_for_platform_authentication_failure(self) -> None:
        from wqb_cli.agent.nodes.evaluation import SimulationBatchResult
        from wqb_cli.agent.store import AgentStore
        from wqb_cli.agent.types import RunConfig, RunState, ScopeMode

        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(Path(tmp) / "agent.sqlite3")
            store.initialize()
            store.create_run("run-1", RunConfig(scope_mode=ScopeMode.AUTO))
            mechanisms = [{"mechanism_id": "m1", "field_ids": ["vwap"]}]
            store.record_research_plan(
                "run-1", 1, "plan-hash", {"mechanisms": mechanisms}
            )
            idea = store.sync_research_ideas(
                "run-1", 1, "plan-hash", mechanisms
            )[0]
            store.set_research_idea_status(
                "run-1", idea.idea_id, "READY", stage="SIMULATE"
            )
            for index, window in enumerate((22, 63, 126, 252), start=1):
                store.add_candidate(
                    "run-1",
                    f"fp-m1-{index}",
                    {
                        "expression": f"ts_delta(vwap,{window})",
                        "mechanism_id": "m1",
                    },
                )
            dispatcher = object.__new__(_Dispatcher)
            dispatcher.store = store
            dispatcher.evaluation = Mock()
            dispatcher.evaluation.run_j.return_value = SimulationBatchResult(
                (),
                (),
                (),
                ({"stage": "simulation", "raw": {"response": {"status_code": 401}}},),
            )

            result = dispatcher._run_j("run-1", {}, {})

            self.assertEqual(result.run_state, RunState.NEEDS_AUTH)
            self.assertIsNone(result.next_node)
            persisted = store.get_research_idea("run-1", "p1:m1")
            self.assertEqual(persisted.status, "ERROR")
            self.assertEqual(persisted.last_error, "WorldQuant authentication required")

    def test_runtime_j_returns_vector_platform_failure_to_h(self) -> None:
        from wqb_cli.agent.nodes.evaluation import SimulationBatchResult
        from wqb_cli.agent.store import AgentStore
        from wqb_cli.agent.types import RunConfig, ScopeMode, WorkflowNode

        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(Path(tmp) / "agent.sqlite3")
            store.initialize()
            store.create_run("run-1", RunConfig(scope_mode=ScopeMode.AUTO))
            mechanisms = [{"mechanism_id": "m1", "field_ids": ["event_signal"]}]
            store.record_research_plan(
                "run-1", 1, "plan-hash", {"mechanisms": mechanisms}
            )
            idea = store.sync_research_ideas(
                "run-1", 1, "plan-hash", mechanisms
            )[0]
            store.set_research_idea_status(
                "run-1", idea.idea_id, "READY", stage="SIMULATE"
            )
            for index, window in enumerate((22, 63, 126, 252), start=1):
                store.add_candidate(
                    "run-1",
                    f"fp-{index}",
                    {
                        "expression": f"ts_delta(event_signal,{window})",
                        "mechanism_id": "m1",
                    },
                )
            dispatcher = object.__new__(_Dispatcher)
            dispatcher.store = store
            dispatcher.evaluation = Mock()
            dispatcher.evaluation.run_j.return_value = SimulationBatchResult(
                (),
                (),
                (),
                (
                    {
                        "stage": "child_simulation",
                        "raw": {
                            "response": {
                                "body": {
                                    "message": "Operator ts_delta does not support event inputs."
                                }
                            }
                        },
                    },
                ),
            )

            result = dispatcher._run_j("run-1", {}, {})

            self.assertEqual(result.next_node, WorkflowNode.H)
            self.assertEqual(
                result.payload["expression_validation_failure"]["code"],
                "VECTOR_REDUCER_REQUIRED",
            )
            persisted = store.get_research_idea("run-1", "p1:m1")
            self.assertEqual(persisted.status, "ERROR")

    def test_runtime_j_resume_reuses_success_and_recreates_only_failed_candidate(self) -> None:
        from wqb_cli.agent.nodes.evaluation import SimulationBatchResult
        from wqb_cli.agent.store import AgentStore
        from wqb_cli.agent.types import RunConfig, ScopeMode

        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(Path(tmp) / "agent.sqlite3")
            store.initialize()
            store.create_run("run-1", RunConfig(scope_mode=ScopeMode.AUTO))
            mechanisms = [{"mechanism_id": "m1", "field_ids": ["vwap"]}]
            store.record_research_plan(
                "run-1", 1, "plan-hash", {"mechanisms": mechanisms}
            )
            idea = store.sync_research_ideas(
                "run-1", 1, "plan-hash", mechanisms
            )[0]
            store.set_research_idea_status(
                "run-1", idea.idea_id, "READY", stage="SIMULATE"
            )
            first = store.add_candidate(
                "run-1", "fp-1", {"expression": "ts_delta(vwap,22)", "mechanism_id": "m1"}
            )
            second = store.add_candidate(
                "run-1", "fp-2", {"expression": "ts_delta(vwap,63)", "mechanism_id": "m1"}
            )
            third = store.add_candidate(
                "run-1", "fp-3", {"expression": "ts_delta(vwap,126)", "mechanism_id": "m1"}
            )
            fourth = store.add_candidate(
                "run-1", "fp-4", {"expression": "ts_delta(vwap,252)", "mechanism_id": "m1"}
            )
            store.record_simulation(
                "run-1", "SIM-OK", "COMPLETE", candidate_id=first.id, alpha_id="A1"
            )
            store.record_simulation(
                "run-1", "SIM-FAIL", "FAILED", candidate_id=second.id
            )
            store.record_simulation(
                "run-1", "SIM-OK-3", "COMPLETE", candidate_id=third.id, alpha_id="A3"
            )
            store.record_simulation(
                "run-1", "SIM-OK-4", "COMPLETE", candidate_id=fourth.id, alpha_id="A4"
            )
            dispatcher = object.__new__(_Dispatcher)
            dispatcher.store = store
            dispatcher.evaluation = Mock()
            dispatcher.evaluation.run_j.return_value = SimulationBatchResult(
                ("SIM-OK", "SIM-NEW"),
                ({"alpha_id": "A1"}, {"alpha_id": "A2"}),
                ("fp-2",),
                (),
            )

            dispatcher._run_j("run-1", {}, {})

            kwargs = dispatcher.evaluation.run_j.call_args.kwargs
            self.assertEqual(
                kwargs["resume_simulation_ids"],
                ["SIM-OK", "SIM-OK-3", "SIM-OK-4"],
            )
            self.assertEqual(
                [item["fingerprint"] for item in kwargs["create_candidates"]],
                ["fp-2"],
            )

    def test_runtime_j_does_not_reuse_previous_plan_candidates(self) -> None:
        from wqb_cli.agent.store import AgentStore
        from wqb_cli.agent.types import RunConfig, ScopeMode

        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(Path(tmp) / "agent.sqlite3")
            store.initialize()
            store.create_run("run-1", RunConfig(scope_mode=ScopeMode.AUTO))
            mechanism = {"mechanism_id": "m1", "field_ids": ["vwap"]}
            store.record_research_plan(
                "run-1", 1, "plan-1", {"mechanisms": [mechanism]}
            )
            old = store.add_candidate(
                "run-1",
                "old-fp",
                {
                    "expression": "ts_delta(vwap,22)",
                    "mechanism_id": "m1",
                    "plan_version": 1,
                    "plan_hash": "plan-1",
                },
            )
            store.record_simulation(
                "run-1", "OLD-SIM", "COMPLETE", candidate_id=old.id, alpha_id="A1"
            )
            store.record_research_plan(
                "run-1", 2, "plan-2", {"mechanisms": [mechanism]}
            )
            store.add_candidate(
                "run-1",
                "new-fp",
                {
                    "expression": "days_from_last_change(vwap)",
                    "mechanism_id": "m1",
                    "plan_version": 2,
                    "plan_hash": "plan-2",
                },
            )
            dispatcher = object.__new__(_Dispatcher)
            dispatcher.store = store

            candidates = dispatcher._idea_candidates("run-1", "m1")
            resume, create = dispatcher._idea_simulation_work(
                "run-1", candidates
            )

            self.assertEqual([item["fingerprint"] for item in candidates], ["new-fp"])
            self.assertEqual(resume, [])
            self.assertEqual(
                [item["fingerprint"] for item in create], ["new-fp"]
            )

    def test_runtime_j_keeps_only_latest_plan_prior_results(self) -> None:
        from wqb_cli.agent.store import AgentStore
        from wqb_cli.agent.types import RunConfig, ScopeMode, WorkflowNode

        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(Path(tmp) / "agent.sqlite3")
            store.initialize()
            store.create_run("run-1", RunConfig(scope_mode=ScopeMode.AUTO))
            mechanism = {"mechanism_id": "m1", "field_ids": ["vwap"]}
            store.record_research_plan(
                "run-1", 1, "plan-1", {"mechanisms": [mechanism]}
            )
            store.record_research_plan(
                "run-1", 2, "plan-2", {"mechanisms": [mechanism]}
            )
            idea = store.sync_research_ideas(
                "run-1", 2, "plan-2", [mechanism]
            )[0]
            store.set_research_idea_status(
                "run-1", idea.idea_id, "COMPLETED", stage="SIMULATE"
            )
            dispatcher = object.__new__(_Dispatcher)
            dispatcher.store = store
            dispatcher.evaluation = Mock()
            context = {
                "alpha_results": [
                    {"alpha_id": "LEGACY"},
                    {"alpha_id": "P1", "plan_version": 1, "plan_hash": "plan-1"},
                    {"alpha_id": "P2", "plan_version": 2, "plan_hash": "plan-2"},
                    {"alpha_id": "WRONG", "plan_version": 2, "plan_hash": "other"},
                ]
            }

            result = dispatcher._run_j("run-1", {}, context)

            self.assertEqual(result.next_node, WorkflowNode.K)
            self.assertEqual(
                [item["alpha_id"] for item in result.payload["alpha_results"]],
                ["P2"],
            )

    def test_runtime_k_evaluates_only_latest_plan_results(self) -> None:
        from wqb_cli.agent.store import AgentStore
        from wqb_cli.agent.types import NodeResult, RunConfig, ScopeMode, WorkflowNode

        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(Path(tmp) / "agent.sqlite3")
            store.initialize()
            store.create_run("run-1", RunConfig(scope_mode=ScopeMode.AUTO))
            mechanism = {"mechanism_id": "m1", "field_ids": ["vwap"]}
            store.record_research_plan(
                "run-1", 1, "plan-1", {"mechanisms": [mechanism]}
            )
            store.record_research_plan(
                "run-1", 2, "plan-2", {"mechanisms": [mechanism]}
            )
            dispatcher = object.__new__(_Dispatcher)
            dispatcher.store = store
            dispatcher.evaluation = Mock()
            dispatcher.evaluation.run_k.return_value = NodeResult(WorkflowNode.K, {})
            context = {
                "scope": {},
                "alpha_results": [
                    {"alpha_id": "LEGACY"},
                    {"alpha_id": "P1", "plan_version": 1, "plan_hash": "plan-1"},
                    {"alpha_id": "P2-A", "plan_version": 2, "plan_hash": "plan-2"},
                    {"alpha_id": "P2-B", "plan_version": 2, "plan_hash": "plan-2"},
                ],
            }

            dispatcher.run("run-1", WorkflowNode.K, context)

            alpha_results = dispatcher.evaluation.run_k.call_args.args[1]
            self.assertEqual(
                [item["alpha_id"] for item in alpha_results],
                ["P2-A", "P2-B"],
            )

    def test_quant_agent_skill_is_present_and_forbids_direct_submit(self) -> None:
        skill = Path(__file__).resolve().parents[1] / "skills" / "wqb-quant-agent" / "SKILL.md"
        self.assertTrue(skill.exists())
        text = skill.read_text(encoding="utf-8")
        self.assertIn("wqb agent approve", text)
        self.assertIn("Never call `wqb alpha submit` directly", text)
        self.assertIn("planner", text.lower())
        self.assertIn("operator", text.lower())

    def test_manual_run_parser_keeps_handler_validation(self) -> None:
        args = build_parser().parse_args(["agent", "run", "--scope-mode", "manual", "--region", "USA", "--dataset-id", "pv"])
        self.assertEqual(args.agent_command, "run")
        self.assertEqual(args.dataset_id, "pv")
        self.assertEqual(args.scope_mode, "manual")

    def test_per_run_model_overrides_parse_independently(self) -> None:
        args = build_parser().parse_args(["agent", "run", "--scope-mode", "auto", "--dataset-id", "pv", "--planner-model", "large", "--operator-model", "small"])
        self.assertEqual(args.planner_model, "large")
        self.assertEqual(args.operator_model, "small")

    def test_run_exposes_only_round_and_backtest_termination_options(self) -> None:
        args = build_parser().parse_args([
            "agent", "run", "--scope-mode", "auto",
            "--dataset-id", "pv",
            "--max-rounds", "7", "--max-simulations", "64",
        ])
        self.assertEqual(args.max_rounds, 7)
        self.assertEqual(args.max_simulations, 64)
        for removed in (
            "--max-runtime-minutes",
            "--max-planner-calls",
            "--max-operator-calls",
            "--max-model-cost-usd",
        ):
            with self.subTest(option=removed), self.assertRaises(SystemExit):
                build_parser().parse_args([
                    "agent", "run", "--scope-mode", "auto", "--dataset-id", "pv", removed, "1"
                ])

    def test_run_requires_explicit_dataset(self) -> None:
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["agent", "run", "--scope-mode", "auto"])

    def test_status_reports_only_two_termination_counters(self) -> None:
        from wqb_cli.agent.store import AgentStore
        from wqb_cli.agent.types import Budget, RunConfig, ScopeMode, WorkflowNode

        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(Path(tmp) / "agent.sqlite3")
            store.initialize()
            store.create_run(
                "run-1",
                RunConfig(
                    scope_mode=ScopeMode.AUTO,
                    budget=Budget(rounds=7, total_simulations=64),
                ),
            )
            candidate = store.add_candidate(
                "run-1", "fingerprint", {"expression": "ts_delta(vwap,22)"}
            )
            store.record_simulation(
                "run-1", "CHILD", "COMPLETE", candidate_id=candidate.id
            )
            attempt = store.start_node_attempt("run-1", WorkflowNode.K)
            store.finish_node_attempt(attempt, "COMPLETED", {"decision": "retry"})

            projection = status_projection(store, "run-1")

        self.assertEqual(projection["termination"], {
            "actual_simulations": 1,
            "max_simulations": 64,
            "rounds": 1,
            "max_rounds": 7,
        })

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
