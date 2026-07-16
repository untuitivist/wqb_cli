from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import closing
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
from wqb_cli.agent.expressions import fingerprint_expression
from wqb_cli.agent.artifacts import ArtifactWriter
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
        self.artifacts = ArtifactWriter(Path(self.temp.name) / "artifacts", self.store)
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

    def trusted_evidence_bundle(self) -> dict[str, str]:
        sources = {
            "community": (("community", "search", "liquidity"), "liquidity_community_search.json"),
            "official_docs": (("docs", "show", "data/README.md"), "liquidity_docs_show.json"),
            "platform": (("search", "liquidity"), "liquidity_platform_search.json"),
            "paper": (("arxiv", "search", "query", "liquidity"), "liquidity_papers.json"),
        }
        lessons = []
        for source_class, (argv, name) in sources.items():
            command = self.store.reserve_command("run-1", WorkflowNode.G, f"{source_class}-command", argv)
            artifact = self.artifacts.write_json("run-1", WorkflowNode.G, name, {"source": source_class})
            self.store.complete_command(command.id, 0, artifact_id=artifact.id)
            lessons.append({"source_class": source_class, "source_id": f"artifact:{artifact.id}", "extracted_statement": f"{source_class} fact", "applicability": "PV"})
        bundle = self.artifacts.write_json(
            "run-1", WorkflowNode.G, "evidence_lessons.json",
            {"lessons": lessons, "coverage": []},
        )
        return {"artifact_id": f"artifact:{bundle.id}", "sha256": bundle.sha256}

    def bundle_source_ref(self, bundle: dict[str, str]) -> str:
        artifact = self.store.get_artifact(int(bundle["artifact_id"].split(":")[1]))
        return self.artifacts.read_json(artifact)["lessons"][0]["source_id"]

    def tearDown(self) -> None:
        self.temp.cleanup()

    def register_evidence(self, *, run_id: str = "run-1", node: WorkflowNode = WorkflowNode.G) -> None:
        for index in range(1, 5):
            self.store.add_artifact(
                run_id, node, f"evidence-{index}.json",
                Path(self.temp.name) / f"evidence-{index}.json", f"{index:064x}",
            )

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

    def test_h_requires_store_bound_canonical_evidence_bundle_before_planner(self) -> None:
        bundle = self.trusted_evidence_bundle()
        router = Mock()
        router.invoke.return_value = model_value(
            "research_plan",
            {"mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"]}]},
        )
        runner = Mock()
        runner.run.return_value = SimpleNamespace(payload=envelope({"id": "vwap"}), artifact=SimpleNamespace(id=20))

        ResearchNodes(runner=runner, router=router, store=self.store, artifacts=self.artifacts).run_h(
            "run-1", self.scope, "tower-1", [{"id": "vwap"}], bundle,
        )

        self.assertEqual(router.invoke.call_count, 1)

    def test_h_rejects_tampered_bundle_hash_and_cross_class_source_reuse_before_planner(self) -> None:
        bundle = self.trusted_evidence_bundle()
        router = Mock()
        runner = Mock()
        runner.run.return_value = SimpleNamespace(payload=envelope({"id": "vwap"}), artifact=SimpleNamespace(id=20))
        nodes = ResearchNodes(runner=runner, router=router, store=self.store, artifacts=self.artifacts)
        with self.assertRaisesRegex(ValueError, "bundle"):
            nodes.run_h("run-1", self.scope, "tower-1", [{"id": "vwap"}], {**bundle, "sha256": "0" * 64})

        record = self.store.get_artifact(int(bundle["artifact_id"].split(":")[1]))
        payload = self.artifacts.read_json(record)
        tampered = {**payload, "lessons": [dict(item) for item in payload["lessons"]]}
        tampered["lessons"][0]["extracted_statement"] = "tampered statement"
        Path(record.path).write_text(
            json.dumps(tampered, sort_keys=True, separators=(",", ":")), encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "bundle"):
            nodes.run_h("run-1", self.scope, "tower-1", [{"id": "vwap"}], bundle)

        payload["lessons"] = [
            {"source_class": source, "source_id": payload["lessons"][0]["source_id"], "extracted_statement": "forged", "applicability": "PV"}
            for source in ("community", "official_docs", "platform", "paper")
        ]
        forged = self.artifacts.write_json("run-1", WorkflowNode.G, "evidence_lessons.json", payload)
        with self.assertRaisesRegex(ValueError, "source"):
            nodes.run_h("run-1", self.scope, "tower-1", [{"id": "vwap"}], {"artifact_id": f"artifact:{forged.id}", "sha256": forged.sha256})
        router.invoke.assert_not_called()

    def test_h_rejects_foreign_source_inside_current_bundle(self) -> None:
        bundle = self.trusted_evidence_bundle()
        self.store.create_run("foreign", RunConfig.from_dict({"scope_mode": "auto"}))
        command = self.store.reserve_command(
            "foreign", WorkflowNode.G, "foreign-community",
            ("community", "search", "liquidity"),
        )
        foreign = self.artifacts.write_json(
            "foreign", WorkflowNode.G, "liquidity_community_search.json",
            {"foreign": True},
        )
        self.store.complete_command(command.id, 0, artifact_id=foreign.id)
        record = self.store.get_artifact(int(bundle["artifact_id"].split(":")[1]))
        payload = self.artifacts.read_json(record)
        payload["lessons"][0]["source_id"] = f"artifact:{foreign.id}"
        rewritten = self.artifacts.write_json(
            "run-1", WorkflowNode.G, "evidence_lessons.json", payload
        )
        router = Mock()
        with self.assertRaisesRegex(ValueError, "source"):
            ResearchNodes(
                runner=Mock(), router=router, store=self.store,
                artifacts=self.artifacts,
            ).run_h(
                "run-1", self.scope, "tower-1", [{"id": "vwap"}],
                {"artifact_id": f"artifact:{rewritten.id}", "sha256": rewritten.sha256},
            )
        router.invoke.assert_not_called()

    def test_f_missing_local_data_returns_typed_failure_without_model(self) -> None:
        runner = Mock()
        runner.run.return_value = SimpleNamespace(
            payload=local_payload(info_data={"exists": False}, all_data={"exists": False}),
            artifact=SimpleNamespace(id=1),
        )
        router = Mock()
        result = EvidenceNodes(runner=runner, router=router, store=self.store).run_f(
            "run-1", self.scope, {"alpha_id": "tower-1", "code": "rank(volume)"},
            local_data_root=Path(self.temp.name) / "missing",
        )

        self.assertEqual(result.summary["failure_class"], DATA_SOURCE_MISSING)
        self.assertTrue(result.summary["setup_paths"])
        runner.run.assert_called_once_with(
            "run-1", WorkflowNode.F, ("scope", "files"), "scope_files.json"
        )
        router.invoke.assert_not_called()

    def test_f_collects_authoritative_field_pool_before_models(self) -> None:
        runner = Mock()
        runner.run.side_effect = [
            SimpleNamespace(payload=local_payload(info_data={"exists": True}, all_data={"exists": True}), artifact=SimpleNamespace(id=1)),
            SimpleNamespace(payload=local_payload(scopes=[{"scope": "USA_1", "region": "USA", "delay": 1}]), artifact=SimpleNamespace(id=2)),
            SimpleNamespace(payload=local_payload(scope="USA_1", summary={}), artifact=SimpleNamespace(id=3)),
            SimpleNamespace(payload=local_payload(scope="USA_1", results=[]), artifact=SimpleNamespace(id=4)),
            SimpleNamespace(payload=envelope({"count": 2, "results": [{"id": "volume", "dataset": {"id": "base-price"}}, {"id": "vwap", "dataset": {"id": "pv"}}]}), artifact=SimpleNamespace(id=5)),
            SimpleNamespace(payload=envelope({"count": 2, "results": [{"id": "base-price"}, {"id": "pv"}]}), artifact=SimpleNamespace(id=6)),
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
        self.assertEqual(result.payload["base_price_volume_fields"], ["volume"])
        self.assertEqual(result.payload["used_dataset_ids"], ["base-price"])
        self.assertEqual(router.invoke.call_args_list[0].args[0].role.value, "operator")
        self.assertEqual(router.invoke.call_args_list[1].args[0].role.value, "planner")
        self.assertEqual(runner.run.call_args_list[2].args[2], ("scope", "show", "USA_1"))
        self.assertEqual(
            runner.run.call_args_list[3].args[2],
            ("scope", "top", "USA_1", "--group", "datafield", "--min-count", "5", "--limit", "100"),
        )

    def test_f_scope_without_data_all_returns_typed_failure_before_model(self) -> None:
        runner = Mock()
        runner.run.side_effect = [
            SimpleNamespace(payload=local_payload(info_data={"exists": False}, all_data={"exists": False}), artifact=SimpleNamespace(id=1)),
        ]
        router = Mock()

        result = EvidenceNodes(runner=runner, router=router, store=self.store).run_f(
            "run-1", self.scope, {"alpha_id": "tower-1", "code": "rank(volume)"},
        )

        self.assertEqual(result.summary["failure_class"], DATA_SOURCE_MISSING)
        self.assertIn("local/data_all/info_data.bin", result.summary["setup_paths"])
        self.assertEqual(runner.run.call_count, 1)
        router.invoke.assert_not_called()

    def test_f_file_not_found_payload_returns_typed_failure_immediately(self) -> None:
        runner = Mock()
        runner.run.return_value = SimpleNamespace(
            payload={"ok": False, "reason": "scope_info_file_not_found", "path": "local/data_all/info_data.bin"},
            artifact=SimpleNamespace(id=1),
        )
        router = Mock()

        result = EvidenceNodes(runner=runner, router=router, store=self.store).run_f(
            "run-1", self.scope, {"alpha_id": "tower-1", "regular": {"code": "rank(volume)"}},
        )

        self.assertEqual(result.summary["failure_class"], DATA_SOURCE_MISSING)
        runner.run.assert_called_once()
        router.invoke.assert_not_called()

    def test_f_uses_paginated_scope_fallback_only_after_empty_tag_search(self) -> None:
        runner = Mock()
        runner.run.side_effect = [
            SimpleNamespace(payload=local_payload(info_data={"exists": True}, all_data={"exists": True}), artifact=SimpleNamespace(id=1)),
            SimpleNamespace(payload=local_payload(scopes=[{"scope": "USA_1", "region": "USA", "delay": 1}]), artifact=SimpleNamespace(id=2)),
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
            if call.args[2][:2] == ("alpha", "list")
            and "--settings-region" in call.args[2]
            and "--tag" not in call.args[2]
        ]
        self.assertEqual([argv[argv.index("--offset") + 1] for argv in fallback_calls], ["0", "100"])

    def test_f_uses_real_alpha_rows_to_ban_poor_os_fields(self) -> None:
        runner = Mock()
        runner.run.side_effect = [
            SimpleNamespace(payload=local_payload(info_data={"exists": True}, all_data={"exists": True}), artifact=SimpleNamespace(id=1)),
            SimpleNamespace(payload=local_payload(scopes=[{"scope": "USA_1", "region": "USA", "delay": 1}]), artifact=SimpleNamespace(id=2)),
            SimpleNamespace(payload=local_payload(scope="USA_1", dimensions={"datafield": 2}), artifact=SimpleNamespace(id=3)),
            SimpleNamespace(payload=local_payload(scope="USA_1", group="datafield", metric="fitness_ratio", results=[{"name": "weak_field", "count": 5, "fitness_ratio": 0.1}]), artifact=SimpleNamespace(id=4)),
            SimpleNamespace(payload=envelope({"results": [{"id": "weak_field", "dataset": {"id": "weak-ds"}}, {"id": "vwap", "dataset": {"id": "pv"}}]}), artifact=SimpleNamespace(id=5)),
            SimpleNamespace(payload=envelope({"results": [{"id": "weak-ds"}, {"id": "pv"}]}), artifact=SimpleNamespace(id=6)),
            SimpleNamespace(payload=envelope({"results": [{"id": "A1"}]}), artifact=SimpleNamespace(id=7)),
            SimpleNamespace(payload=local_payload(scope="USA_1", table="os", total=1, offset=0, limit=20, filters={"datafield": "weak_field", "dataset": None}, columns=["id", "sharpe", "fitness", "turnover", "margin"], rows=[{"id": "A1", "sharpe": 0.2, "fitness": 0.1, "turnover": 0.2, "margin": 0.0001}]), artifact=SimpleNamespace(id=8)),
        ]
        router = Mock()
        router.invoke.side_effect = [
            model_value("task_result", {"status": "COMPLETED", "payload": {}}),
            model_value("evidence_requirements", {"keywords": ["liquidity"]}),
        ]

        result = EvidenceNodes(runner=runner, router=router, store=self.store).run_f(
            "run-1", self.scope, {"alpha_id": "tower-1", "regular": {"code": "rank(volume)"}},
        )

        self.assertIn("weak_field", result.payload["banned_fields"])
        alpha_rows_call = runner.run.call_args_list[-1].args[2]
        self.assertEqual(alpha_rows_call[:5], ("scope", "alpha-rows", "USA_1", "--table", "os"))

    def test_f_paginates_all_os_rows_before_deterministic_field_decision(self) -> None:
        failing_rows = [
            {"id": f"A{index}", "sharpe": 0.2, "fitness": 0.1, "turnover": 0.2, "margin": 0.0001}
            for index in range(20)
        ]
        runner = Mock()
        runner.run.side_effect = [
            SimpleNamespace(payload=local_payload(info_data={"exists": True}, all_data={"exists": True}), artifact=SimpleNamespace(id=1)),
            SimpleNamespace(payload=local_payload(scopes=[{"scope": "USA_1", "region": "USA", "delay": 1}]), artifact=SimpleNamespace(id=2)),
            SimpleNamespace(payload=local_payload(scope="USA_1", dimensions={"datafield": 1}), artifact=SimpleNamespace(id=3)),
            SimpleNamespace(payload=local_payload(scope="USA_1", group="datafield", metric="sharpe_ratio", results=[{"name": "late_weak", "count": 21, "sharpe_ratio": 1.5}]), artifact=SimpleNamespace(id=4)),
            SimpleNamespace(payload=envelope({"results": [{"id": "late_weak", "dataset": {"id": "ds"}}]}), artifact=SimpleNamespace(id=5)),
            SimpleNamespace(payload=envelope({"results": [{"id": "ds"}]}), artifact=SimpleNamespace(id=6)),
            SimpleNamespace(payload=envelope({"results": [{"id": "A1"}]}), artifact=SimpleNamespace(id=7)),
            SimpleNamespace(payload=local_payload(scope="USA_1", table="os", total=21, offset=0, limit=20, filters={"datafield": "late_weak", "dataset": None}, columns=["id", "sharpe", "fitness", "turnover", "margin"], rows=failing_rows), artifact=SimpleNamespace(id=8)),
            SimpleNamespace(payload=local_payload(scope="USA_1", table="os", total=21, offset=20, limit=20, filters={"datafield": "late_weak", "dataset": None}, columns=["id", "sharpe", "fitness", "turnover", "margin"], rows=[{"id": "A20", "sharpe": 2.0, "fitness": 1.2, "turnover": 0.2, "margin": 0.002}]), artifact=SimpleNamespace(id=9)),
        ]
        router = Mock()
        router.invoke.side_effect = [
            model_value("task_result", {"status": "COMPLETED", "payload": {}}),
            model_value("evidence_requirements", {"keywords": ["liquidity"]}),
        ]

        result = EvidenceNodes(runner=runner, router=router, store=self.store).run_f(
            "run-1", self.scope, {"alpha_id": "tower-1", "regular": {"code": "rank(volume)"}},
        )

        self.assertNotIn("late_weak", result.payload["poor_os_fields"])
        os_calls = [call.args[2] for call in runner.run.call_args_list if call.args[2][:2] == ("scope", "alpha-rows")]
        self.assertEqual([argv[argv.index("--offset") + 1] for argv in os_calls], ["0", "20"])

    def test_g_records_gap_when_paper_source_is_unavailable(self) -> None:
        runner = Mock()
        runner.run.side_effect = [
            SimpleNamespace(payload=local_payload(forum_topics=[{"title": "community lesson"}], forum_comments=[], docs_articles=[]), artifact=SimpleNamespace(id=10)),
            SimpleNamespace(payload=local_payload(nodes=[{"node": "data", "readme": "data/README.md", "examples": []}]), artifact=SimpleNamespace(id=11)),
            SimpleNamespace(payload=local_payload(path="data/README.md", text="official lesson"), artifact=SimpleNamespace(id=12)),
            SimpleNamespace(payload=envelope({"query": ["platform lesson"]}), artifact=SimpleNamespace(id=13)),
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
            SimpleNamespace(payload=envelope({"query": ["platform lesson"]}), artifact=SimpleNamespace(id=13)),
        ]
        runner.run_external.return_value = SimpleNamespace(
            payload=local_payload(papers=[{"title": "Liquidity and returns"}]),
            artifact=SimpleNamespace(id=14),
        )

        result = EvidenceNodes(
            runner=runner, router=Mock(), store=self.store,
            artifacts=self.artifacts,
        ).run_g("run-1", ["liquidity"])

        self.assertEqual(result.next_node, WorkflowNode.H)
        self.assertFalse(result.summary["paper_source_unavailable"])
        runner.run_external.assert_called_once()

    def test_g_returns_canonical_evidence_bundle_artifact_binding(self) -> None:
        runner = Mock()
        runner.run.side_effect = [
            SimpleNamespace(payload=local_payload(forum_topics=[{"title": "community lesson"}], forum_comments=[], docs_articles=[]), artifact=SimpleNamespace(id=10)),
            SimpleNamespace(payload=local_payload(nodes=[{"node": "data", "readme": "data/README.md", "examples": []}]), artifact=SimpleNamespace(id=11)),
            SimpleNamespace(payload=local_payload(text="official lesson"), artifact=SimpleNamespace(id=12)),
            SimpleNamespace(payload=envelope({"query": ["platform lesson"]}), artifact=SimpleNamespace(id=13)),
        ]
        runner.run_external.return_value = SimpleNamespace(
            payload=local_payload(papers=[{"title": "Liquidity and returns"}]),
            artifact=SimpleNamespace(id=14),
        )
        result = EvidenceNodes(
            runner=runner, router=Mock(), store=self.store,
            artifacts=self.artifacts,
        ).run_g("run-1", ["liquidity"])

        binding = result.payload["evidence_bundle"]
        artifact = self.store.get_artifact(int(binding["artifact_id"].split(":")[1]))
        self.assertEqual(artifact.name, "evidence_lessons.json")
        self.assertEqual(artifact.sha256, binding["sha256"])
        self.assertEqual(self.artifacts.read_json(artifact)["coverage"], [])

    def test_g_extracts_real_platform_search_inventory_strings(self) -> None:
        coverage = evidence_coverage([
            {"source_class": "community", "source_id": "artifact:1"},
            {"source_class": "official_docs", "source_id": "artifact:2"},
            {"source_class": "platform", "source_id": "artifact:3"},
            {"source_class": "paper", "source_id": "artifact:4"},
        ])
        self.assertTrue(coverage.complete)
        from wqb_cli.agent.nodes.evidence import platform_search_lesson
        lesson = platform_search_lesson(
            {"query": ["Liquidity inventory statement"]}, "artifact:3", "liquidity"
        )
        self.assertEqual(lesson["extracted_statement"], "Liquidity inventory statement")

    def test_h_stores_canonical_plan_with_validated_tower_and_evidence(self) -> None:
        bundle = self.trusted_evidence_bundle()
        source_ref = self.bundle_source_ref(bundle)
        router = Mock()
        runner = Mock()
        runner.run.return_value = SimpleNamespace(
            payload=envelope({"id": "vwap", "description": "Volume-weighted price."}),
            artifact=SimpleNamespace(id=20),
        )
        router.invoke.return_value = model_value(
            "research_plan",
            {"mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": [source_ref]}]},
        )
        result = ResearchNodes(runner=runner, router=router, store=self.store, artifacts=self.artifacts).run_h(
            "run-1", self.scope, "tower-1", [{"id": "vwap"}], bundle,
        )

        record = self.store.get_latest_research_plan("run-1")
        self.assertEqual(result.next_node, WorkflowNode.I)
        self.assertEqual(record.plan_version, 1)
        self.assertEqual(result.payload["plan_hash"], record.plan_hash)
        runner.run.assert_called_once_with(
            "run-1", WorkflowNode.H, ("data", "field", "vwap"), "field_vwap.json"
        )

    def test_h_bounds_untrusted_metadata_before_planner(self) -> None:
        bundle = self.trusted_evidence_bundle()
        bundle_record = self.store.get_artifact(int(bundle["artifact_id"].split(":")[1]))
        bundle_payload = self.artifacts.read_json(bundle_record)
        for lesson in bundle_payload["lessons"]:
            lesson["extracted_statement"] = "y" * 10_000
        rewritten = self.artifacts.write_json("run-1", WorkflowNode.G, "evidence_lessons.json", bundle_payload)
        bundle = {"artifact_id": f"artifact:{rewritten.id}", "sha256": rewritten.sha256}
        source_ref = bundle_payload["lessons"][0]["source_id"]
        router = Mock()
        router.invoke.return_value = model_value(
            "research_plan",
            {"mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": [source_ref]}]},
        )
        fields = [{"id": "vwap", "description": "x" * 100_000}]
        runner = Mock()
        runner.run.return_value = SimpleNamespace(
            payload=envelope({"id": "vwap", "description": "x" * 100_000}),
            artifact=SimpleNamespace(id=20),
        )
        ResearchNodes(runner=runner, router=router, store=self.store, artifacts=self.artifacts).run_h(
            "run-1", self.scope, "tower-1", fields, bundle,
        )

        context = router.invoke.call_args.args[0].context
        self.assertLessEqual(len(json.dumps(context, sort_keys=True, separators=(",", ":"))), 20_000)

    def test_h_rejects_missing_foreign_or_wrong_node_evidence_before_planner(self) -> None:
        router = Mock()
        runner = Mock()
        runner.run.return_value = SimpleNamespace(payload=envelope({"id": "vwap"}), artifact=SimpleNamespace(id=20))
        self.store.create_run("foreign", RunConfig.from_dict({"scope_mode": "auto"}))
        wrong = self.artifacts.write_json("run-1", WorkflowNode.F, "evidence_lessons.json", {"lessons": [], "coverage": []})
        foreign = self.artifacts.write_json("foreign", WorkflowNode.G, "evidence_lessons.json", {"lessons": [], "coverage": []})

        for binding in (
            {"artifact_id": "artifact:999", "sha256": "a" * 64},
            {"artifact_id": f"artifact:{foreign.id}", "sha256": foreign.sha256},
            {"artifact_id": f"artifact:{wrong.id}", "sha256": wrong.sha256},
        ):
            with self.subTest(binding=binding), self.assertRaisesRegex(ValueError, "evidence bundle"):
                ResearchNodes(runner=runner, router=router, store=self.store, artifacts=self.artifacts).run_h(
                    "run-1", self.scope, "tower-1", [{"id": "vwap"}], binding,
                )
        router.invoke.assert_not_called()
        self.assertIsNone(self.store.get_latest_research_plan("run-1"))

    def test_h_requires_explicit_current_tower_on_every_mechanism(self) -> None:
        with self.assertRaisesRegex(ValueError, "tower"):
            validate_mechanism_fields(
                {"mechanisms": [{"mechanism_id": "m1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"]}]},
                candidate_fields={"vwap"}, resolvable_evidence={"artifact:1"}, current_tower="tower-1",
            )

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

    def test_i_persists_equivalent_rejections_by_raw_candidate_and_reason(self) -> None:
        fingerprint = fingerprint_expression("rank(vwap)")
        self.store.add_candidate("run-1", fingerprint, {"expression": "rank(vwap)"})
        self.store.record_research_plan("run-1", 1, "plan-hash", {
            "mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"]}],
        })
        router = Mock()
        router.invoke.side_effect = [
            model_value("candidate_plan", {"plan_version": 1, "plan_hash": "plan-hash", "tasks": [{"task_id": "t1", "mechanism_id": "m1", "permitted_fields": ["vwap"], "transform_families": ["rank"], "count": 3}]}),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": [
                {"expression": "rank( vwap )", "field_id": "vwap", "single_mechanism": True},
                {"expression": " rank(vwap)", "field_id": "vwap", "single_mechanism": True},
                {"expression": "rank(vwap )", "field_id": "vwap", "single_mechanism": True},
            ]}}),
        ]

        result = ResearchNodes(runner=Mock(), router=router, store=self.store).run_i(
            "run-1", self.scope, {"rank": {"arity": 1}},
        )

        self.assertEqual(len(result.payload["rejected"]), 3)
        self.assertTrue(all(item["fingerprint"] == fingerprint for item in result.payload["rejected"]))
        self.assertEqual(self.store.get_operator_task("run-1", "t1").status, "COMPLETED")
        with closing(self.store.connect()) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM candidates WHERE status='REJECTED'").fetchone()[0], 3)

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

    def test_i_processes_every_task_with_one_operator_call_each(self) -> None:
        plan = {"mechanisms": [
            {"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"]},
            {"mechanism_id": "m2", "tower_id": "tower-1", "field_ids": ["close"], "evidence_refs": ["artifact:2"]},
        ]}
        self.store.record_research_plan("run-1", 1, "plan-hash", plan)
        router = Mock()
        router.invoke.side_effect = [
            model_value("candidate_plan", {"plan_version": 1, "plan_hash": "plan-hash", "tasks": [
                {"task_id": "t1", "mechanism_id": "m1", "permitted_fields": ["vwap"], "transform_families": ["rank"], "count": 1},
                {"task_id": "t2", "mechanism_id": "m2", "permitted_fields": ["close"], "transform_families": ["rank"], "count": 1},
            ]}),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": [{"expression": "rank(vwap)", "field_id": "vwap", "single_mechanism": True}]}}),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": [{"expression": "rank(close)", "field_id": "close", "single_mechanism": True}]}}),
        ]

        result = ResearchNodes(runner=Mock(), router=router, store=self.store).run_i(
            "run-1", self.scope, {"rank": {"arity": 1}},
        )

        self.assertEqual(len(result.payload["accepted"]), 2)
        self.assertEqual(self.store.get_operator_task("run-1", "t1").status, "COMPLETED")
        self.assertEqual(self.store.get_operator_task("run-1", "t2").status, "COMPLETED")
        self.assertEqual([call.args[0].role.value for call in router.invoke.call_args_list], ["planner", "operator", "operator"])

    def test_i_experience_revalidation_persists_current_run_candidate(self) -> None:
        fingerprint = fingerprint_expression("rank(vwap)")
        self.store.add_experience("run-1", {
            "region": "USA", "delay": 1, "category": "PV",
            "expression_fingerprint": fingerprint, "field_ids": ["vwap"],
            "failure_class": "LOW_SHARPE", "hypothesis": {"idea": "liquidity"},
            "record": {"round": 1}, "metrics": {"sharpe": 0.2},
            "final_decision": "RETRY",
        })
        plan = {"mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"]}]}
        self.store.record_research_plan("run-1", 1, "plan-hash", plan)
        router = Mock()
        router.invoke.side_effect = [
            model_value("candidate_plan", {"plan_version": 1, "plan_hash": "plan-hash", "tasks": [{"task_id": "t1", "mechanism_id": "m1", "permitted_fields": ["vwap"], "transform_families": ["rank"], "count": 1}]}),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": [{"expression": "rank(vwap)", "field_id": "vwap", "single_mechanism": True}]}}),
        ]

        result = ResearchNodes(runner=Mock(), router=router, store=self.store).run_i(
            "run-1", self.scope, {"rank": {"arity": 1}}, allow_revalidation=True,
        )

        self.assertEqual(result.payload["new_fingerprints"], [fingerprint])
        self.assertEqual(self.store.get_candidate_by_fingerprint("run-1", fingerprint).status, "REVALIDATED")

    def test_i_blocked_operator_task_is_terminal_and_does_not_route_to_j(self) -> None:
        plan = {"mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"]}]}
        self.store.record_research_plan("run-1", 1, "plan-hash", plan)
        router = Mock()
        router.invoke.side_effect = [
            model_value("candidate_plan", {"plan_version": 1, "plan_hash": "plan-hash", "tasks": [
                {"task_id": "blocked", "mechanism_id": "m1", "permitted_fields": ["vwap"], "transform_families": ["rank"], "count": 1},
                {"task_id": "later", "mechanism_id": "m1", "permitted_fields": ["vwap"], "transform_families": ["rank"], "count": 1},
            ]}),
            model_value("task_result", {"status": "BLOCKED", "payload": {"reason": "insufficient evidence"}}),
        ]

        result = ResearchNodes(runner=Mock(), router=router, store=self.store).run_i(
            "run-1", self.scope, {"rank": {"arity": 1}},
        )

        self.assertEqual(result.next_node, WorkflowNode.I)
        self.assertEqual(result.payload["status"], "BLOCKED")
        self.assertEqual(self.store.get_operator_task("run-1", "blocked").status, "BLOCKED")
        with self.assertRaisesRegex(KeyError, "operator task not found"):
            self.store.get_operator_task("run-1", "later")
        self.assertEqual(router.invoke.call_count, 2)
        with closing(self.store.connect()) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM candidates WHERE run_id='run-1'").fetchone()[0], 0)

    def test_i_later_blocked_task_preserves_prior_durable_candidates(self) -> None:
        plan = {"mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"]}]}
        self.store.record_research_plan("run-1", 1, "plan-hash", plan)
        router = Mock()
        router.invoke.side_effect = [
            model_value("candidate_plan", {"plan_version": 1, "plan_hash": "plan-hash", "tasks": [
                {"task_id": "accepted", "mechanism_id": "m1", "permitted_fields": ["vwap"], "transform_families": ["rank"], "count": 1},
                {"task_id": "blocked", "mechanism_id": "m1", "permitted_fields": ["vwap"], "transform_families": ["rank"], "count": 1},
            ]}),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": [{"expression": "rank(vwap)", "field_id": "vwap", "single_mechanism": True}]}}),
            model_value("task_result", {"status": "BLOCKED", "payload": {"reason": "needs replan"}}),
        ]

        result = ResearchNodes(runner=Mock(), router=router, store=self.store).run_i(
            "run-1", self.scope, {"rank": {"arity": 1}},
        )

        fingerprint = fingerprint_expression("rank(vwap)")
        self.assertEqual(result.next_node, WorkflowNode.I)
        self.assertEqual(result.payload["new_fingerprints"], [fingerprint])
        self.assertEqual(result.payload["accepted"][0]["fingerprint"], fingerprint)
        self.assertEqual(self.store.get_candidate_by_fingerprint("run-1", fingerprint).status, "ACCEPTED")

    def test_i_exact_experience_dedupe_finds_record_older_than_recent_window(self) -> None:
        target = fingerprint_expression("rank(vwap)")
        for index in range(102):
            self.store.add_experience("run-1", {
                "region": "USA", "delay": 1, "category": "PV",
                "expression_fingerprint": target if index == 0 else f"other-{index}",
                "field_ids": ["vwap"],
            })
        self.assertTrue(self.store.has_experience_fingerprint("USA", 1, "PV", target))

        plan = {"mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"]}]}
        self.store.record_research_plan("run-1", 1, "plan-hash", plan)
        router = Mock()
        router.invoke.side_effect = [
            model_value("candidate_plan", {"plan_version": 1, "plan_hash": "plan-hash", "tasks": [{"task_id": "t1", "mechanism_id": "m1", "permitted_fields": ["vwap"], "transform_families": ["rank"], "count": 1}]}),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": [{"expression": "rank(vwap)", "field_id": "vwap", "single_mechanism": True}]}}),
        ]
        result = ResearchNodes(runner=Mock(), router=router, store=self.store).run_i(
            "run-1", self.scope, {"rank": {"arity": 1}}, allow_revalidation=False,
        )
        self.assertEqual(result.payload["accepted"], [])
        self.assertEqual(result.payload["rejected"][0]["reason"], "duplicate_fingerprint")


if __name__ == "__main__":
    unittest.main()
