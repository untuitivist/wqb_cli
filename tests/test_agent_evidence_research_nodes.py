from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from wqb_cli.agent.nodes.evidence import (
    DATA_SOURCE_MISSING,
    EvidenceNodes,
    evidence_coverage,
    screen_fields,
)
from wqb_cli.agent.nodes.research import ResearchNodes, validate_mechanism_fields
from wqb_cli.agent.store import AgentStore
from wqb_cli.agent.types import RunConfig, WorkflowNode


def envelope(body: object, *, status: int = 200, ok: bool = True) -> dict[str, object]:
    return {"ok": ok, "response": {"status_code": status, "body": body}}


def local_payload(**body: object) -> dict[str, object]:
    return {"ok": True, **body}


def model_value(payload_name: str, payload: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(
        value={
            "decision": "bounded decision",
            "reasoning_summary": "Uses only supplied artifacts.",
            "evidence_refs": ["artifact:1"],
            "confidence": 0.8,
            payload_name: payload,
        }
    )


class EvidenceResearchNodeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = AgentStore(Path(self.temp.name) / "agent.sqlite3")
        self.store.initialize()
        self.store.create_run(
            "run-1",
            RunConfig.from_dict(
                {
                    "scope_mode": "manual", "region": "USA", "delay": 1,
                    "universe": "TOP3000", "neutralization": "SUBINDUSTRY",
                }
            ),
        )
        self.scope = {
            "region": "USA", "delay": 1, "universe": "TOP3000",
            "neutralization": "SUBINDUSTRY", "category": "PV",
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_f_bans_fields_already_used_in_target_tower(self) -> None:
        result = screen_fields(
            platform_fields=[
                {"id": "volume", "dataset": {"id": "pv1"}},
                {"id": "vwap", "dataset": {"id": "pv1"}},
            ],
            used_fields={"volume"}, poor_os_fields=set(), used_datasets=set(),
        )

        self.assertIn("volume", result.banned_fields)
        self.assertEqual([field["id"] for field in result.candidate_fields], ["vwap"])

    def test_g_requires_four_evidence_classes(self) -> None:
        result = evidence_coverage([
            {"source_class": "community", "source_id": "artifact:1"},
            {"source_class": "official_docs", "source_id": "artifact:2"},
            {"source_class": "platform", "source_id": "artifact:3"},
        ])

        self.assertFalse(result.complete)
        self.assertEqual(result.missing_sources, ("paper",))

    def test_h_cannot_add_field_outside_f_pool(self) -> None:
        with self.assertRaisesRegex(ValueError, "outside F candidate pool"):
            validate_mechanism_fields(
                {"mechanisms": [{"mechanism_id": "m1", "field_ids": ["secret_field"], "evidence_refs": ["artifact:1"]}]},
                candidate_fields={"vwap"}, resolvable_evidence={"artifact:1"}, current_tower="tower-1",
            )

    def test_h_requires_resolvable_evidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "evidence"):
            validate_mechanism_fields(
                {"mechanisms": [{"mechanism_id": "m1", "field_ids": ["vwap"], "evidence_refs": ["artifact:missing"]}]},
                candidate_fields={"vwap"}, resolvable_evidence={"artifact:1"}, current_tower="tower-1",
            )

    def test_f_missing_local_data_returns_typed_failure_without_model(self) -> None:
        runner = Mock()
        router = Mock()
        result = EvidenceNodes(runner=runner, router=router, store=self.store).run_f(
            "run-1", self.scope, {"alpha_id": "tower-1", "code": "rank(volume)"},
            local_data_root=Path(self.temp.name) / "missing",
        )

        self.assertEqual(result.summary["failure_class"], DATA_SOURCE_MISSING)
        self.assertTrue(result.summary["setup_paths"])
        runner.run.assert_not_called()
        router.invoke.assert_not_called()

    def test_f_collects_authoritative_field_pool_before_models(self) -> None:
        runner = Mock()
        runner.run.side_effect = [
            SimpleNamespace(payload=local_payload(info_data={"exists": True}, all_data={"exists": True}), artifact=SimpleNamespace(id=1)),
            SimpleNamespace(payload=local_payload(scopes=["USA_1"]), artifact=SimpleNamespace(id=2)),
            SimpleNamespace(payload=local_payload(scope="USA_1", summary={}), artifact=SimpleNamespace(id=3)),
            SimpleNamespace(payload=local_payload(scope="USA_1", results=[]), artifact=SimpleNamespace(id=4)),
            SimpleNamespace(payload=envelope({"count": 2, "results": [{"id": "volume", "dataset": {"id": "pv"}}, {"id": "vwap", "dataset": {"id": "pv"}}]}), artifact=SimpleNamespace(id=5)),
            SimpleNamespace(payload=envelope({"count": 1, "results": [{"id": "pv"}]}), artifact=SimpleNamespace(id=6)),
            SimpleNamespace(payload=envelope({"results": []}), artifact=SimpleNamespace(id=7)),
            SimpleNamespace(payload=envelope({"results": []}), artifact=SimpleNamespace(id=8)),
        ]
        router = Mock()
        router.invoke.side_effect = [
            model_value("task_result", {"status": "COMPLETED", "payload": {}}),
            model_value("evidence_requirements", {"keywords": ["liquidity"]}),
        ]

        result = EvidenceNodes(runner=runner, router=router, store=self.store).run_f(
            "run-1", self.scope, {"alpha_id": "tower-1", "code": "rank(volume)"},
        )

        self.assertEqual(result.next_node, WorkflowNode.G)
        self.assertEqual(result.payload["candidate_fields"], ["vwap"])
        self.assertIn("volume", result.payload["banned_fields"])
        self.assertEqual(router.invoke.call_args_list[0].args[0].role.value, "operator")
        self.assertEqual(router.invoke.call_args_list[1].args[0].role.value, "planner")
        self.assertEqual(runner.run.call_args_list[2].args[2], ("scope", "show", "USA_1"))
        self.assertEqual(
            runner.run.call_args_list[3].args[2],
            ("scope", "top", "USA_1", "--group", "datafield", "--metric", "fitness_ratio", "--ascending"),
        )

    def test_f_scope_without_data_all_returns_typed_failure_before_model(self) -> None:
        runner = Mock()
        runner.run.side_effect = [
            SimpleNamespace(payload=local_payload(info_data={"exists": False}, all_data={"exists": False}), artifact=SimpleNamespace(id=1)),
            SimpleNamespace(payload=local_payload(scopes=[]), artifact=SimpleNamespace(id=2)),
            SimpleNamespace(payload=local_payload(scope="USA_1", summary={}), artifact=SimpleNamespace(id=3)),
            SimpleNamespace(payload=local_payload(scope="USA_1", results=[]), artifact=SimpleNamespace(id=4)),
        ]
        router = Mock()

        result = EvidenceNodes(runner=runner, router=router, store=self.store).run_f(
            "run-1", self.scope, {"alpha_id": "tower-1", "code": "rank(volume)"},
        )

        self.assertEqual(result.summary["failure_class"], DATA_SOURCE_MISSING)
        self.assertIn("local/data_all", result.summary["setup_paths"])
        self.assertEqual(runner.run.call_count, 4)
        router.invoke.assert_not_called()

    def test_f_uses_paginated_scope_fallback_only_after_empty_tag_search(self) -> None:
        runner = Mock()
        runner.run.side_effect = [
            SimpleNamespace(payload=local_payload(info_data={"exists": True}, all_data={"exists": True}), artifact=SimpleNamespace(id=1)),
            SimpleNamespace(payload=local_payload(scopes=["USA_1"]), artifact=SimpleNamespace(id=2)),
            SimpleNamespace(payload=local_payload(scope="USA_1", summary={}), artifact=SimpleNamespace(id=3)),
            SimpleNamespace(payload=local_payload(scope="USA_1", results=[]), artifact=SimpleNamespace(id=4)),
            SimpleNamespace(payload=envelope({"results": [{"id": "vwap", "dataset": {"id": "pv"}}]}), artifact=SimpleNamespace(id=5)),
            SimpleNamespace(payload=envelope({"results": [{"id": "pv"}]}), artifact=SimpleNamespace(id=6)),
            SimpleNamespace(payload=envelope({"results": []}), artifact=SimpleNamespace(id=7)),
            SimpleNamespace(payload=envelope({"results": [{"id": f"A{index}"} for index in range(100)]}), artifact=SimpleNamespace(id=8)),
            SimpleNamespace(payload=envelope({"results": [{"id": "A100"}]}), artifact=SimpleNamespace(id=9)),
        ]
        router = Mock()
        router.invoke.side_effect = [
            model_value("task_result", {"status": "COMPLETED", "payload": {}}),
            model_value("evidence_requirements", {"keywords": ["liquidity"]}),
        ]

        EvidenceNodes(runner=runner, router=router, store=self.store).run_f(
            "run-1", self.scope, {"alpha_id": "tower-1", "code": "rank(volume)"},
        )

        fallback_calls = [
            call.args[2] for call in runner.run.call_args_list
            if call.args[2][:2] == ("alpha", "list") and "--settings-region" in call.args[2]
        ]
        self.assertEqual([argv[argv.index("--offset") + 1] for argv in fallback_calls], ["0", "100"])

    def test_g_records_gap_when_paper_source_is_unavailable(self) -> None:
        runner = Mock()
        runner.run.side_effect = [
            SimpleNamespace(payload=local_payload(forum_topics=[{"title": "community lesson"}], forum_comments=[], docs_articles=[]), artifact=SimpleNamespace(id=10)),
            SimpleNamespace(payload=local_payload(nodes=[{"node": "data", "readme": "data/README.md", "examples": []}]), artifact=SimpleNamespace(id=11)),
            SimpleNamespace(payload=local_payload(path="data/README.md", text="official lesson"), artifact=SimpleNamespace(id=12)),
            SimpleNamespace(payload=envelope({"results": [{"text": "platform lesson"}]}), artifact=SimpleNamespace(id=13)),
        ]
        result = EvidenceNodes(runner=runner, router=Mock(), store=self.store).run_g(
            "run-1", ["liquidity"], arxiv_available=False,
        )

        self.assertEqual(result.next_node, WorkflowNode.G)
        self.assertIn("paper", result.summary["missing_sources"])
        self.assertEqual(result.summary["paper_source_unavailable"], True)
        self.assertEqual(runner.run.call_args_list[1].args[2], ("docs", "list"))
        self.assertEqual(runner.run.call_args_list[2].args[2], ("docs", "show", "data/README.md"))

    def test_g_auto_uses_configured_arxiv_without_fabricating_papers(self) -> None:
        runner = Mock()
        runner.run.side_effect = [
            SimpleNamespace(payload=local_payload(forum_topics=[{"title": "community lesson"}], forum_comments=[], docs_articles=[]), artifact=SimpleNamespace(id=10)),
            SimpleNamespace(payload=local_payload(nodes=[{"node": "data", "readme": "data/README.md", "examples": []}]), artifact=SimpleNamespace(id=11)),
            SimpleNamespace(payload=local_payload(text="official lesson"), artifact=SimpleNamespace(id=12)),
            SimpleNamespace(payload=envelope({"results": [{"text": "platform lesson"}]}), artifact=SimpleNamespace(id=13)),
        ]
        runner.run_external.return_value = SimpleNamespace(
            payload=local_payload(papers=[{"title": "Liquidity and returns"}]),
            artifact=SimpleNamespace(id=14),
        )

        result = EvidenceNodes(runner=runner, router=Mock(), store=self.store).run_g(
            "run-1", ["liquidity"]
        )

        self.assertEqual(result.next_node, WorkflowNode.H)
        self.assertFalse(result.summary["paper_source_unavailable"])
        runner.run_external.assert_called_once()

    def test_h_stores_canonical_plan_with_validated_tower_and_evidence(self) -> None:
        router = Mock()
        runner = Mock()
        runner.run.return_value = SimpleNamespace(
            payload=envelope({"id": "vwap", "description": "Volume-weighted price."}),
            artifact=SimpleNamespace(id=20),
        )
        router.invoke.return_value = model_value(
            "research_plan",
            {"mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"]}]},
        )
        lessons = [
            {"source_class": source_class, "source_id": f"artifact:{index}", "extracted_statement": "test", "applicability": "PV"}
            for index, source_class in enumerate(("community", "official_docs", "platform", "paper"), start=1)
        ]
        result = ResearchNodes(runner=runner, router=router, store=self.store).run_h(
            "run-1", self.scope, "tower-1", [{"id": "vwap"}], lessons,
        )

        record = self.store.get_latest_research_plan("run-1")
        self.assertEqual(result.next_node, WorkflowNode.I)
        self.assertEqual(record.plan_version, 1)
        self.assertEqual(result.payload["plan_hash"], record.plan_hash)
        runner.run.assert_called_once_with(
            "run-1", WorkflowNode.H, ("data", "field", "vwap"), "field_vwap.json"
        )

    def test_h_bounds_untrusted_metadata_before_planner(self) -> None:
        router = Mock()
        router.invoke.return_value = model_value(
            "research_plan",
            {"mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"]}]},
        )
        fields = [{"id": "vwap", "description": "x" * 100_000}]
        runner = Mock()
        runner.run.return_value = SimpleNamespace(
            payload=envelope({"id": "vwap", "description": "x" * 100_000}),
            artifact=SimpleNamespace(id=20),
        )
        lessons = [
            {"source_class": source_class, "source_id": f"artifact:{index}", "extracted_statement": "y" * 100_000, "applicability": "PV"}
            for index, source_class in enumerate(("community", "official_docs", "platform", "paper"), start=1)
        ]

        ResearchNodes(runner=runner, router=router, store=self.store).run_h(
            "run-1", self.scope, "tower-1", fields, lessons,
        )

        context = router.invoke.call_args.args[0].context
        self.assertLessEqual(len(json.dumps(context, sort_keys=True, separators=(",", ":"))), 20_000)

    def test_i_rejects_duplicate_fingerprint_unless_revalidation_allowed(self) -> None:
        plan = {"mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"]}]}
        self.store.record_research_plan("run-1", 1, "plan-hash", plan)
        router = Mock()
        router.invoke.side_effect = [
            model_value("candidate_plan", {"plan_version": 1, "plan_hash": "plan-hash", "tasks": [{"task_id": "t1", "mechanism_id": "m1", "permitted_fields": ["vwap"], "transform_families": ["rank"], "count": 1}]}),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": [{"expression": "rank(vwap)", "field_id": "vwap", "single_mechanism": True}]}}),
        ]
        nodes = ResearchNodes(runner=Mock(), router=router, store=self.store)
        first = nodes.run_i("run-1", self.scope, {"rank": {"arity": 1}}, allow_revalidation=False)
        self.assertEqual(first.payload["new_fingerprints"], [first.payload["accepted"][0]["fingerprint"]])
        router.invoke.side_effect = [
            model_value("candidate_plan", {"plan_version": 1, "plan_hash": "plan-hash", "tasks": [{"task_id": "t2", "mechanism_id": "m1", "permitted_fields": ["vwap"], "transform_families": ["rank"], "count": 1}]}),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": [{"expression": "rank(vwap)", "field_id": "vwap", "single_mechanism": True}]}}),
        ]
        second = nodes.run_i("run-1", self.scope, {"rank": {"arity": 1}}, allow_revalidation=False)

        self.assertEqual(second.payload["new_fingerprints"], [])
        self.assertEqual(second.payload["rejected"][0]["reason"], "duplicate_fingerprint")

    def test_i_accepts_operator_from_permitted_transform_family(self) -> None:
        plan = {"mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"]}]}
        self.store.record_research_plan("run-1", 1, "plan-hash", plan)
        router = Mock()
        router.invoke.side_effect = [
            model_value("candidate_plan", {"plan_version": 1, "plan_hash": "plan-hash", "tasks": [{"task_id": "ts-1", "mechanism_id": "m1", "permitted_fields": ["vwap"], "transform_families": ["time_series"], "count": 1}]}),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": [{"expression": "ts_mean(vwap,20)", "field_id": "vwap", "single_mechanism": True}]}}),
        ]

        result = ResearchNodes(runner=Mock(), router=router, store=self.store).run_i(
            "run-1", self.scope, {"ts_mean": {"arity": 2}},
        )

        self.assertEqual(len(result.payload["accepted"]), 1)


if __name__ == "__main__":
    unittest.main()
