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
from wqb_cli.agent.nodes.research import (
    ResearchError,
    ResearchNodes,
    validate_mechanism_fields,
)
from wqb_cli.agent.models import ModelReadTimeoutError
from wqb_cli.agent.expressions import fingerprint_expression
from wqb_cli.agent.artifacts import ArtifactWriter
from wqb_cli.agent.runner import RunnerError
from wqb_cli.agent.store import AgentStore
from wqb_cli.agent.types import RunConfig, RunState, WorkflowNode


def envelope(body: object, *, status: int = 200, ok: bool = True) -> dict[str, object]:
    return {"ok": ok, "response": {"status_code": status, "body": body}}


def local_payload(**body: object) -> dict[str, object]:
    return {"ok": True, **body}


def model_value(payload_name: str, payload: dict[str, object]) -> SimpleNamespace:
    if payload_name == "research_plan":
        for mechanism in payload.get("mechanisms", []):
            if not isinstance(mechanism, dict) or "field_bindings" in mechanism:
                continue
            fields = mechanism.get("field_ids", [])
            references = mechanism.get("evidence_refs", [])
            if isinstance(fields, list) and isinstance(references, list) and references:
                mechanism["field_bindings"] = [
                    {
                        "field_id": field_id,
                        "role": "primary_signal" if index == 0 else "confirmation",
                        "rationale": f"{field_id} has a specific economic role in this mechanism.",
                        "evidence_refs": [references[0]],
                    }
                    for index, field_id in enumerate(fields)
                ]
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
    def test_remote_401_is_classified_as_authentication_required(self) -> None:
        payload = {
            "ok": False,
            "response": {
                "status_code": 401,
                "body": {"detail": "Incorrect authentication credentials."},
            },
        }

        with self.assertRaisesRegex(Exception, "authentication required") as raised:
            EvidenceNodes._body(payload, "data fields")

        self.assertIn("auth", type(raised.exception).__name__.lower())

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
            source_payload = (
                {"ok": True, "text": f"{source_class} fact"}
                if source_class == "official_docs"
                else {"source": source_class}
            )
            artifact = self.artifacts.write_json("run-1", WorkflowNode.G, name, source_payload)
            self.store.complete_command(command.id, 0, artifact_id=artifact.id)
            lessons.append({"source_class": source_class, "source_id": f"artifact:{artifact.id}", "extracted_statement": f"{source_class} fact", "applicability": "liquidity"})
        bundle = self.artifacts.write_json(
            "run-1", WorkflowNode.G, "evidence_lessons.json",
            {
                "mechanism_keywords": ["liquidity"],
                "lessons": lessons,
                "coverage": [],
                "missing_sources": [],
                "per_keyword": {
                    "liquidity": {
                        "coverage": ["community", "official_docs", "platform", "paper"],
                        "missing_sources": [],
                    },
                },
            },
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
            {"mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"], "hypothesis": "Persistent deviations in volume-weighted price may reveal gradual price discovery after liquidity shocks."}]},
        )
        runner = Mock()
        runner.run.return_value = SimpleNamespace(payload=envelope({"id": "vwap"}), artifact=SimpleNamespace(id=20))

        ResearchNodes(runner=runner, router=router, store=self.store, artifacts=self.artifacts).run_h(
            "run-1", self.scope, "tower-1", [{"id": "vwap"}], bundle,
        )

        self.assertEqual(router.invoke.call_count, 1)
        request = router.invoke.call_args.args[0]
        self.assertEqual(request.context["idea_constraints"]["max_ideas"], 4)
        self.assertIn("between 1 and 4", request.instructions)

    def test_h_limits_field_metadata_to_top_twelve_candidates(self) -> None:
        bundle = self.trusted_evidence_bundle()
        source_ref = self.bundle_source_ref(bundle)
        router = Mock()
        router.invoke.return_value = model_value(
            "research_plan",
            {
                "mechanisms": [
                    {
                        "mechanism_id": "m1",
                        "tower_id": "tower-1",
                        "field_ids": ["field-00"],
                        "evidence_refs": [source_ref],
                        "hypothesis": "Persistent changes in field-00 may reveal delayed price discovery after liquidity shocks.",
                    }
                ]
            },
        )
        runner = Mock()

        def field_response(
            run_id: str, node: WorkflowNode, argv: tuple[str, ...], name: str
        ) -> SimpleNamespace:
            return SimpleNamespace(
                payload=envelope({"id": argv[2]}), artifact=SimpleNamespace(id=20)
            )

        runner.run.side_effect = field_response
        fields = [{"id": f"field-{index:02d}"} for index in range(13)]

        ResearchNodes(
            runner=runner, router=router, store=self.store, artifacts=self.artifacts
        ).run_h("run-1", self.scope, "tower-1", fields, bundle)

        self.assertEqual(runner.run.call_count, 12)
        request = router.invoke.call_args.args[0]
        self.assertEqual(len(request.context["allowed_field_ids"]), 12)
        self.assertNotIn("field-12", request.context["allowed_field_ids"])

    def test_h_receives_compact_backtest_feedback_for_mechanism_refinement(self) -> None:
        bundle = self.trusted_evidence_bundle()
        source_ref = self.bundle_source_ref(bundle)
        router = Mock()
        router.invoke.return_value = model_value(
            "research_plan",
            {
                "mechanisms": [
                    {
                        "mechanism_id": "revised-liquidity",
                        "tower_id": "tower-1",
                        "field_ids": ["vwap"],
                        "evidence_refs": [source_ref],
                        "hypothesis": "Changes in volume-weighted price after liquidity shocks predict gradual next-period price discovery.",
                    }
                ]
            },
        )
        runner = Mock()
        runner.run.return_value = SimpleNamespace(
            payload=envelope({"id": "vwap", "description": "Volume-weighted price."}),
            artifact=SimpleNamespace(id=20),
        )
        refinement = {
            "diagnosis": {
                "failure_class": "ECONOMIC_MECHANISM",
                "next_node": "H",
                "evidence_ids": [f"metric:A{index}" for index in range(40)],
            },
            "metrics": [
                {
                    "alpha_id": f"A{index}",
                    "failures": ["sharpe", "fitness"],
                    "metrics": {
                        "sharpe": index / 100,
                        "fitness": 0.1,
                        "turnover": 0.2,
                        "margin": 0.0001,
                        "checks": {"raw": "x" * 20_000},
                    },
                    "template_id": "unary:ts_delta",
                    "raw": {"response": "x" * 20_000},
                }
                for index in range(40)
            ],
            "template_density": {
                "unary:ts_delta": {
                    "template_id": "unary:ts_delta",
                    "template_type": "unary",
                    "strategy_family": "change",
                    "tested": 40,
                    "promising": 0,
                    "passed": 0,
                    "factor_density": 0.0,
                    "pass_rate": 0.0,
                }
            },
            "anti_patterns": [
                {
                    "code": "LOW_FACTOR_DENSITY",
                    "template_id": "unary:ts_delta",
                    "tested": 40,
                    "action": "replace_template",
                }
            ],
        }

        ResearchNodes(
            runner=runner, router=router, store=self.store, artifacts=self.artifacts
        ).run_h(
            "run-1",
            self.scope,
            "tower-1",
            [{"id": "vwap"}],
            bundle,
            refinement_context=refinement,
        )

        request = router.invoke.call_args.args[0]
        feedback = request.context["refinement_evidence"]
        self.assertNotIn("mechanism_id", feedback)
        self.assertEqual(
            feedback["diagnosis"]["failure_class"], "ECONOMIC_MECHANISM"
        )
        self.assertEqual(feedback["metric_summary"]["tested"], 40)
        self.assertEqual(
            len(feedback["metric_summary"]["representative_metrics"]), 3
        )
        serialized = json.dumps(feedback)
        self.assertLess(len(serialized), 10_000)
        self.assertNotIn("raw", serialized)
        self.assertNotIn("checks", serialized)
        self.assertIn("refinement_evidence", request.instructions)

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
        self.assertEqual(result.run_state, RunState.NEEDS_DATA)
        self.assertIsNone(result.next_node)
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
            dataset_id="pv",
        )

        self.assertEqual(result.next_node, WorkflowNode.G)
        self.assertEqual(result.payload["candidate_fields"], ["vwap"])
        self.assertIn("volume", result.payload["banned_fields"])
        self.assertEqual(result.payload["base_price_volume_fields"], ["volume"])
        self.assertEqual(result.payload["used_dataset_ids"], [])
        self.assertEqual(router.invoke.call_args_list[0].args[0].role.value, "operator")
        self.assertEqual(router.invoke.call_args_list[1].args[0].role.value, "planner")
        for command_call in runner.run.call_args_list[4:6]:
            argv = command_call.args[2]
            self.assertEqual(argv[argv.index("--limit") + 1], "50")
            self.assertNotIn("--category", argv)
        self.assertEqual(
            runner.run.call_args_list[4].args[2][runner.run.call_args_list[4].args[2].index("--dataset") + 1],
            "pv",
        )
        self.assertEqual(runner.run.call_args_list[2].args[2], ("scope", "show", "USA_1"))
        self.assertEqual(
            runner.run.call_args_list[3].args[2],
            ("scope", "top", "USA_1", "--group", "datafield", "--min-count", "5", "--limit", "100"),
        )

    def test_f_scope_without_pickle_uses_aggregate_data_without_os_rows(self) -> None:
        runner = Mock()
        runner.run.side_effect = [
            SimpleNamespace(payload=local_payload(info_data={"exists": True}, all_data={"exists": False}), artifact=SimpleNamespace(id=1)),
            SimpleNamespace(payload=local_payload(scopes=[{"scope": "USA_1", "region": "USA", "delay": 1}]), artifact=SimpleNamespace(id=2)),
            SimpleNamespace(payload=local_payload(scope="USA_1", summary={}), artifact=SimpleNamespace(id=3)),
            SimpleNamespace(payload=local_payload(scope="USA_1", results=[{"name": "vwap", "count": 10}]), artifact=SimpleNamespace(id=4)),
            SimpleNamespace(payload=envelope({"results": [{"id": "vwap", "dataset": {"id": "pv"}}]}), artifact=SimpleNamespace(id=5)),
            SimpleNamespace(payload=envelope({"results": [{"id": "pv"}]}), artifact=SimpleNamespace(id=6)),
            SimpleNamespace(payload=envelope({"results": [{"id": "A1"}]}), artifact=SimpleNamespace(id=7)),
        ]
        router = Mock()
        router.invoke.side_effect = [
            model_value("task_result", {"status": "COMPLETED", "payload": {}}),
            model_value("evidence_requirements", {"keywords": ["liquidity"]}),
        ]

        result = EvidenceNodes(runner=runner, router=router, store=self.store).run_f(
            "run-1", self.scope, {"alpha_id": "tower-1", "code": "rank(volume)"}, dataset_id="pv",
        )

        self.assertEqual(result.next_node, WorkflowNode.G)
        self.assertIs(result.payload["os_detail_available"], False)
        self.assertFalse(
            any(call.args[2][0:2] == ("scope", "alpha-rows") for call in runner.run.call_args_list)
        )

    def test_f_paginates_datasets_until_the_selected_dataset_is_found(self) -> None:
        runner = Mock()
        runner.run.side_effect = [
            SimpleNamespace(payload=local_payload(info_data={"exists": True}, all_data={"exists": True}), artifact=SimpleNamespace(id=1)),
            SimpleNamespace(payload=local_payload(scopes=[{"scope": "USA_1", "region": "USA", "delay": 1}]), artifact=SimpleNamespace(id=2)),
            SimpleNamespace(payload=local_payload(scope="USA_1", summary={}), artifact=SimpleNamespace(id=3)),
            SimpleNamespace(payload=local_payload(scope="USA_1", results=[]), artifact=SimpleNamespace(id=4)),
            SimpleNamespace(payload=envelope({"results": [{"id": "chosen_field", "dataset": {"id": "late_dataset"}}]}), artifact=SimpleNamespace(id=5)),
            SimpleNamespace(payload=envelope({"count": 51, "results": [{"id": "first_page_dataset"}]}), artifact=SimpleNamespace(id=6)),
            SimpleNamespace(payload=envelope({"results": []}), artifact=SimpleNamespace(id=7)),
            SimpleNamespace(payload=envelope({"count": 51, "results": [{"id": "late_dataset"}]}), artifact=SimpleNamespace(id=8)),
            SimpleNamespace(payload=envelope({"count": 0, "results": []}), artifact=SimpleNamespace(id=9)),
        ]
        router = Mock()
        router.invoke.side_effect = [
            model_value("task_result", {"status": "COMPLETED", "payload": {}}),
            model_value("evidence_requirements", {"keywords": ["liquidity"]}),
        ]

        result = EvidenceNodes(runner=runner, router=router, store=self.store).run_f(
            "run-1", self.scope, {"alpha_id": "tower-1", "code": "rank(volume)"},
            dataset_id="late_dataset",
        )

        self.assertEqual(result.next_node, WorkflowNode.G)
        page_call = runner.run.call_args_list[7].args[2]
        self.assertEqual(page_call[0:2], ("data", "datasets"))
        self.assertEqual(page_call[page_call.index("--offset") + 1], "50")

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
            SimpleNamespace(payload=envelope({"count": 21, "results": [{"id": f"A{index}"} for index in range(20)]}), artifact=SimpleNamespace(id=8)),
            SimpleNamespace(payload=envelope({"count": 21, "results": [{"id": "A20"}]}), artifact=SimpleNamespace(id=9)),
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
        self.assertEqual([argv[argv.index("--offset") + 1] for argv in fallback_calls], ["0", "20"])
        self.assertTrue(all(argv[argv.index("--limit") + 1] == "20" for argv in fallback_calls))

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

    def test_g_allows_optional_community_and_paper_gaps(self) -> None:
        runner = Mock()
        runner.run.side_effect = [
            RunnerError("community database unavailable"),
            SimpleNamespace(payload=local_payload(nodes=[{"node": "data", "readme": "data/README.md", "examples": []}]), artifact=SimpleNamespace(id=11)),
            SimpleNamespace(payload=local_payload(path="data/README.md", text="official lesson"), artifact=SimpleNamespace(id=12)),
            SimpleNamespace(payload=envelope({"query": ["platform lesson"]}), artifact=SimpleNamespace(id=13)),
        ]
        result = EvidenceNodes(
            runner=runner,
            router=Mock(),
            store=self.store,
            artifacts=self.artifacts,
        ).run_g("run-1", ["liquidity"], arxiv_available=False)

        self.assertEqual(result.next_node, WorkflowNode.H)
        self.assertIn("community", result.summary["missing_sources"])
        self.assertIn("paper", result.summary["missing_sources"])
        self.assertEqual(result.summary["paper_source_unavailable"], True)
        self.assertEqual(runner.run.call_args_list[1].args[2], ("docs", "list"))
        self.assertEqual(runner.run.call_args_list[2].args[2], ("docs", "show", "data/README.md"))

    def test_g_allows_unsuccessful_optional_community_payload(self) -> None:
        runner = Mock()
        runner.run.side_effect = [
            SimpleNamespace(
                payload={
                    "ok": False,
                    "error_type": "FileNotFoundError",
                    "detail": "community sqlite dataset not found",
                },
                artifact=SimpleNamespace(id=10),
            ),
            SimpleNamespace(payload=local_payload(nodes=[{"node": "data", "readme": "data/README.md", "examples": []}]), artifact=SimpleNamespace(id=11)),
            SimpleNamespace(payload=local_payload(path="data/README.md", text="official lesson"), artifact=SimpleNamespace(id=12)),
            SimpleNamespace(payload=envelope({"query": ["platform lesson"]}), artifact=SimpleNamespace(id=13)),
        ]

        result = EvidenceNodes(
            runner=runner,
            router=Mock(),
            store=self.store,
            artifacts=self.artifacts,
        ).run_g("run-1", ["liquidity"], arxiv_available=False)

        self.assertEqual(result.next_node, WorkflowNode.H)
        self.assertIn("community", result.summary["missing_sources"])
        self.assertIn("artifact:10", result.artifact_ids)

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

    def test_g_records_optional_source_coverage_for_each_keyword(self) -> None:
        runner = Mock()
        runner.run.side_effect = [
            SimpleNamespace(payload=local_payload(forum_topics=[{"title": "liquidity community"}], forum_comments=[], docs_articles=[]), artifact=SimpleNamespace(id=10)),
            SimpleNamespace(payload=local_payload(nodes=[{"node": "data", "readme": "data/README.md", "examples": []}]), artifact=SimpleNamespace(id=11)),
            SimpleNamespace(payload=local_payload(text="liquidity docs"), artifact=SimpleNamespace(id=12)),
            SimpleNamespace(payload=envelope({"query": ["liquidity platform"]}), artifact=SimpleNamespace(id=13)),
            SimpleNamespace(payload=local_payload(forum_topics=[{"title": "momentum community"}], forum_comments=[], docs_articles=[]), artifact=SimpleNamespace(id=20)),
            SimpleNamespace(payload=local_payload(nodes=[{"node": "data", "readme": "data/README.md", "examples": []}]), artifact=SimpleNamespace(id=21)),
            SimpleNamespace(payload=local_payload(text="momentum docs"), artifact=SimpleNamespace(id=22)),
            SimpleNamespace(payload=envelope({"query": ["momentum platform"]}), artifact=SimpleNamespace(id=23)),
        ]
        runner.run_external.side_effect = [
            SimpleNamespace(
                payload=local_payload(papers=[{"title": "Liquidity and returns"}]),
                artifact=SimpleNamespace(id=14),
            ),
            SimpleNamespace(payload=local_payload(papers=[]), artifact=SimpleNamespace(id=24)),
        ]

        result = EvidenceNodes(
            runner=runner, router=Mock(), store=self.store,
            artifacts=self.artifacts,
        ).run_g("run-1", ["liquidity", "momentum"])

        expected_per_keyword = {
            "liquidity": {
                "coverage": ["community", "official_docs", "platform", "paper"],
                "missing_sources": [],
            },
            "momentum": {
                "coverage": ["community", "official_docs", "platform"],
                "missing_sources": ["paper"],
            },
        }
        self.assertEqual(result.next_node, WorkflowNode.H)
        self.assertEqual(result.summary["missing_sources"], ["paper"])
        self.assertEqual(result.summary["per_keyword"], expected_per_keyword)
        self.assertTrue(result.summary["paper_source_unavailable"])
        self.assertEqual(result.payload["missing_sources"], ["paper"])
        self.assertEqual(result.payload["per_keyword"], expected_per_keyword)
        binding = result.payload["evidence_bundle"]
        artifact = self.store.get_artifact(int(binding["artifact_id"].split(":")[1]))
        bundle = self.artifacts.read_json(artifact)
        self.assertEqual(bundle["coverage"], ["paper"])
        self.assertEqual(bundle["missing_sources"], ["paper"])
        self.assertEqual(bundle["per_keyword"], expected_per_keyword)
        self.assertEqual(bundle["mechanism_keywords"], ["liquidity", "momentum"])

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
        grouped = platform_search_lesson(
            {
                "faq": {
                    "count": 1,
                    "results": [
                        {
                            "question": "How does market neutralization affect Sharpe?",
                            "answer": "group-relative risk control",
                        }
                    ],
                }
            },
            "artifact:4",
            "market mechanism",
        )
        self.assertEqual(
            grouped["extracted_statement"],
            "How does market neutralization affect Sharpe?",
        )

    def test_h_rejects_bundle_with_only_global_source_coverage(self) -> None:
        sources = (
            ("community", "liquidity", ("community", "search", "liquidity"), "liquidity_community_search.json"),
            ("paper", "liquidity", ("arxiv", "search", "query", "liquidity"), "liquidity_papers.json"),
            ("official_docs", "momentum", ("docs", "show", "data/README.md"), "momentum_docs_show.json"),
            ("platform", "momentum", ("search", "momentum"), "momentum_platform_search.json"),
        )
        lessons = []
        for source_class, keyword, argv, name in sources:
            command = self.store.reserve_command(
                "run-1", WorkflowNode.G, f"{keyword}-{source_class}", argv,
            )
            artifact = self.artifacts.write_json(
                "run-1", WorkflowNode.G, name,
                (
                    {"ok": True, "text": f"{source_class} fact"}
                    if source_class == "official_docs"
                    else {"source": source_class}
                ),
            )
            self.store.complete_command(command.id, 0, artifact_id=artifact.id)
            lessons.append({
                "source_class": source_class,
                "source_id": f"artifact:{artifact.id}",
                "extracted_statement": f"{source_class} fact",
                "applicability": keyword,
            })
        bundle_artifact = self.artifacts.write_json(
            "run-1", WorkflowNode.G, "evidence_lessons.json", {
                "mechanism_keywords": ["liquidity", "momentum"],
                "lessons": lessons,
                "coverage": ["community", "official_docs", "platform", "paper"],
                "missing_sources": ["community", "official_docs", "platform", "paper"],
                "per_keyword": {
                    "liquidity": {
                        "coverage": ["community", "paper"],
                        "missing_sources": ["official_docs", "platform"],
                    },
                    "momentum": {
                        "coverage": ["official_docs", "platform"],
                        "missing_sources": ["community", "paper"],
                    },
                },
            },
        )
        router = Mock()

        with self.assertRaisesRegex(ResearchError, "research plan requires evidence coverage"):
            ResearchNodes(
                runner=Mock(), router=router, store=self.store,
                artifacts=self.artifacts,
            ).run_h(
                "run-1", self.scope, "tower-1", [{"id": "vwap"}],
                {"artifact_id": f"artifact:{bundle_artifact.id}", "sha256": bundle_artifact.sha256},
            )

        router.invoke.assert_not_called()

    def test_h_rejects_renamed_mechanism_keyword_before_planner(self) -> None:
        bundle = self.trusted_evidence_bundle()
        record = self.store.get_artifact(int(bundle["artifact_id"].split(":")[1]))
        payload = self.artifacts.read_json(record)
        payload["mechanism_keywords"] = ["momentum"]
        payload["per_keyword"] = {"momentum": payload["per_keyword"].pop("liquidity")}
        for lesson in payload["lessons"]:
            lesson["applicability"] = "momentum"
        rewritten = self.artifacts.write_json(
            "run-1", WorkflowNode.G, "evidence_lessons.json", payload,
        )
        router = Mock()

        with self.assertRaisesRegex(
            ResearchError, "mechanism keywords do not match command provenance",
        ):
            ResearchNodes(
                runner=Mock(), router=router, store=self.store,
                artifacts=self.artifacts,
            ).run_h(
                "run-1", self.scope, "tower-1", [{"id": "vwap"}],
                {"artifact_id": f"artifact:{rewritten.id}", "sha256": rewritten.sha256},
            )

        router.invoke.assert_not_called()

    def test_h_rejects_omitted_mechanism_keyword_before_planner(self) -> None:
        bundle = self.trusted_evidence_bundle()
        for source_class, argv, name in (
            ("community", ("community", "search", "momentum"), "momentum_community_search.json"),
            ("official_docs", ("docs", "show", "data/README.md"), "momentum_docs_show.json"),
            ("platform", ("search", "momentum"), "momentum_platform_search.json"),
            ("paper", ("arxiv", "search", "query", "momentum"), "momentum_papers.json"),
        ):
            command = self.store.reserve_command(
                "run-1", WorkflowNode.G, f"momentum-{source_class}", argv,
            )
            source_payload = (
                {"ok": True, "text": "official_docs momentum fact"}
                if source_class == "official_docs"
                else {"source": source_class}
            )
            artifact = self.artifacts.write_json(
                "run-1", WorkflowNode.G, name, source_payload,
            )
            self.store.complete_command(command.id, 0, artifact_id=artifact.id)
        router = Mock()

        with self.assertRaisesRegex(
            ResearchError, "mechanism keywords do not match command provenance",
        ):
            ResearchNodes(
                runner=Mock(), router=router, store=self.store,
                artifacts=self.artifacts,
            ).run_h(
                "run-1", self.scope, "tower-1", [{"id": "vwap"}], bundle,
            )

        router.invoke.assert_not_called()

    def test_h_rejects_cross_keyword_evidence_reuse_before_planner(self) -> None:
        bundle = self.trusted_evidence_bundle()
        record = self.store.get_artifact(int(bundle["artifact_id"].split(":")[1]))
        payload = self.artifacts.read_json(record)
        payload["mechanism_keywords"] = ["liquidity", "momentum"]
        payload["per_keyword"]["momentum"] = dict(payload["per_keyword"]["liquidity"])
        momentum_command = self.store.reserve_command(
            "run-1", WorkflowNode.G, "unused-momentum-query",
            ("search", "momentum"),
        )
        momentum_source = self.artifacts.write_json(
            "run-1", WorkflowNode.G, "unused_momentum_platform_search.json",
            {"query": ["unused momentum fact"]},
        )
        self.store.complete_command(
            momentum_command.id, 0, artifact_id=momentum_source.id,
        )
        copied_lessons = []
        for index, lesson in enumerate(payload["lessons"]):
            source = self.store.get_artifact(int(lesson["source_id"].split(":")[1]))
            copied_name = {
                "community": "momentum_community_search.json",
                "official_docs": "momentum_docs_show.json",
                "platform": "momentum_platform_search.json",
                "paper": "momentum_papers.json",
            }[lesson["source_class"]]
            copied = self.artifacts.write_json(
                "run-1", WorkflowNode.G, copied_name,
                self.artifacts.read_json(source),
            )
            command = self.store.reserve_command(
                "run-1", WorkflowNode.G, f"momentum-copy-{index}",
                self.store.get_command_for_artifact(source.id).argv,
            )
            self.store.complete_command(command.id, 0, artifact_id=copied.id)
            copied_lessons.append({
                **lesson,
                "source_id": f"artifact:{copied.id}",
                "applicability": "momentum",
            })
        payload["lessons"].extend(copied_lessons)
        rewritten = self.artifacts.write_json(
            "run-1", WorkflowNode.G, "evidence_lessons.json", payload,
        )
        router = Mock()

        with self.assertRaisesRegex(
            ResearchError, "applicability does not match source command",
        ):
            ResearchNodes(
                runner=Mock(), router=router, store=self.store,
                artifacts=self.artifacts,
            ).run_h(
                "run-1", self.scope, "tower-1", [{"id": "vwap"}],
                {"artifact_id": f"artifact:{rewritten.id}", "sha256": rewritten.sha256},
            )

        router.invoke.assert_not_called()

    def test_h_stores_canonical_plan_with_validated_tower_and_evidence(self) -> None:
        bundle = self.trusted_evidence_bundle()
        source_ref = self.bundle_source_ref(bundle)
        router = Mock()
        runner = Mock()
        runner.run.return_value = SimpleNamespace(
            payload=envelope(
                {
                    "id": "vwap",
                    "type": "VECTOR",
                    "description": "Volume-weighted price.",
                }
            ),
            artifact=SimpleNamespace(id=20),
        )
        router.invoke.return_value = model_value(
            "research_plan",
            {"mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": [source_ref], "hypothesis": "Persistent deviations in volume-weighted price may reveal gradual price discovery after liquidity shocks."}]},
        )
        result = ResearchNodes(runner=runner, router=router, store=self.store, artifacts=self.artifacts).run_h(
            "run-1", self.scope, "tower-1", [{"id": "vwap"}], bundle,
        )

        record = self.store.get_latest_research_plan("run-1")
        self.assertEqual(result.next_node, WorkflowNode.I)
        self.assertEqual(record.plan_version, 1)
        self.assertEqual(result.payload["plan_hash"], record.plan_hash)
        self.assertEqual(
            record.plan["mechanisms"][0]["field_types"], {"vwap": "VECTOR"}
        )
        runner.run.assert_called_once_with(
            "run-1", WorkflowNode.H, ("data", "field", "vwap"), "field_vwap.json"
        )

    def test_h_repairs_semantically_invalid_plan_before_persisting(self) -> None:
        bundle = self.trusted_evidence_bundle()
        source_ref = self.bundle_source_ref(bundle)
        router = Mock()
        router.invoke.side_effect = [
            model_value(
                "research_plan",
                {
                    "mechanisms": [
                        {
                            "mechanism_id": "m1",
                            "tower_id": "tower-1",
                            "field_ids": ["outside-field"],
                            "evidence_refs": [source_ref],
                            "hypothesis": "Persistent deviations in volume-weighted price may reveal gradual price discovery after liquidity shocks.",
                        }
                    ]
                },
            ),
            model_value(
                "research_plan",
                {
                    "mechanisms": [
                        {
                            "mechanism_id": "m1",
                            "tower_id": "tower-1",
                            "field_ids": ["vwap"],
                            "evidence_refs": [source_ref],
                            "hypothesis": "Persistent deviations in volume-weighted price may reveal gradual price discovery after liquidity shocks.",
                        }
                    ]
                },
            ),
        ]
        runner = Mock()
        runner.run.return_value = SimpleNamespace(
            payload=envelope({"id": "vwap", "description": "Volume-weighted price."}),
            artifact=SimpleNamespace(id=20),
        )

        ResearchNodes(
            runner=runner, router=router, store=self.store, artifacts=self.artifacts
        ).run_h("run-1", self.scope, "tower-1", [{"id": "vwap"}], bundle)

        self.assertEqual(router.invoke.call_count, 2)
        repair_request = router.invoke.call_args_list[1].args[0]
        self.assertIn("outside-field", repair_request.context["semantic_repair_error"])
        self.assertEqual(
            self.store.get_latest_research_plan("run-1").plan["mechanisms"][0]["field_ids"],
            ["vwap"],
        )

    def test_h_bounds_untrusted_metadata_before_planner(self) -> None:
        bundle = self.trusted_evidence_bundle()
        bundle_record = self.store.get_artifact(int(bundle["artifact_id"].split(":")[1]))
        bundle_payload = self.artifacts.read_json(bundle_record)
        for lesson in bundle_payload["lessons"]:
            if lesson["source_class"] != "official_docs":
                lesson["extracted_statement"] = "y" * 10_000
        rewritten = self.artifacts.write_json("run-1", WorkflowNode.G, "evidence_lessons.json", bundle_payload)
        bundle = {"artifact_id": f"artifact:{rewritten.id}", "sha256": rewritten.sha256}
        source_ref = bundle_payload["lessons"][0]["source_id"]
        router = Mock()
        router.invoke.return_value = model_value(
            "research_plan",
            {"mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": [source_ref], "hypothesis": "Persistent deviations in volume-weighted price may reveal gradual price discovery after liquidity shocks."}]},
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

    def test_h_allows_unbounded_fields_with_exact_evidence_bound_bindings(self) -> None:
        fields = {"price_signal", "volume_confirmation", "risk_regime"}
        plan = {
            "mechanisms": [
                {
                    "mechanism_id": "multi-field-mechanism",
                    "tower_id": "tower-1",
                    "field_ids": sorted(fields),
                    "field_bindings": [
                        {
                            "field_id": "price_signal",
                            "role": "primary_signal",
                            "rationale": "Price displacement supplies the mechanism's directional signal.",
                            "evidence_refs": ["artifact:1"],
                        },
                        {
                            "field_id": "volume_confirmation",
                            "role": "confirmation",
                            "rationale": "Trading participation confirms that the price move is broadly supported.",
                            "evidence_refs": ["artifact:1"],
                        },
                        {
                            "field_id": "risk_regime",
                            "role": "condition",
                            "rationale": "The risk regime limits the signal to economically comparable periods.",
                            "evidence_refs": ["artifact:1"],
                        },
                    ],
                    "evidence_refs": ["artifact:1"],
                    "hypothesis": "Price displacement confirmed by trading participation should be strongest in comparable risk regimes.",
                }
            ]
        }

        validated = validate_mechanism_fields(
            plan,
            candidate_fields=fields,
            resolvable_evidence={"artifact:1"},
            current_tower="tower-1",
            require_specific_hypothesis=True,
        )

        self.assertEqual(validated["mechanisms"][0]["field_ids"], sorted(fields))
        self.assertEqual(len(validated["mechanisms"][0]["field_bindings"]), 3)

    def test_h_rejects_more_than_twenty_ideas(self) -> None:
        mechanisms = [
            {
                "mechanism_id": f"m{index}",
                "tower_id": "tower-1",
                "field_ids": ["vwap"],
                "evidence_refs": ["artifact:1"],
                "hypothesis": "Persistent deviations in volume-weighted price may reveal gradual price discovery.",
            }
            for index in range(21)
        ]

        with self.assertRaisesRegex(ResearchError, "20-idea limit"):
            validate_mechanism_fields(
                {"mechanisms": mechanisms},
                candidate_fields={"vwap"},
                resolvable_evidence={"artifact:1"},
                current_tower="tower-1",
            )

    def test_h_rejects_missing_or_untrusted_field_bindings(self) -> None:
        base = {
            "mechanism_id": "m1",
            "tower_id": "tower-1",
            "field_ids": ["vwap"],
            "evidence_refs": ["artifact:1"],
            "hypothesis": "Persistent deviations in volume-weighted price may reveal gradual price discovery.",
        }
        invalid_bindings = (
            None,
            [
                {
                    "field_id": "vwap",
                    "role": "primary_signal",
                    "rationale": "Volume-weighted price measures persistent price discovery pressure.",
                    "evidence_refs": ["artifact:2"],
                }
            ],
        )
        for bindings in invalid_bindings:
            mechanism = dict(base)
            if bindings is not None:
                mechanism["field_bindings"] = bindings
            with self.subTest(bindings=bindings), self.assertRaisesRegex(
                ResearchError, "field.?binding"
            ):
                validate_mechanism_fields(
                    {"mechanisms": [mechanism]},
                    candidate_fields={"vwap"},
                    resolvable_evidence={"artifact:1", "artifact:2"},
                    current_tower="tower-1",
                    require_specific_hypothesis=True,
                )

    def test_h_rejects_generic_locked_field_hypothesis(self) -> None:
        with self.assertRaisesRegex(ResearchError, "generic"):
            validate_mechanism_fields(
                {"mechanisms": [{
                    "mechanism_id": "locked-field-1",
                    "tower_id": "tower-1",
                    "field_ids": ["vwap"],
                    "evidence_refs": ["artifact:1"],
                    "hypothesis": "The locked field may provide stable cross-sectional information within the selected scope.",
                }]},
                candidate_fields={"vwap", "volume"},
                resolvable_evidence={"artifact:1"},
                current_tower="tower-1",
                require_specific_hypothesis=True,
            )

    def test_h_pauses_after_generic_plan_repairs_are_exhausted(self) -> None:
        bundle = self.trusted_evidence_bundle()
        source_ref = self.bundle_source_ref(bundle)
        router = Mock()
        router.invoke.return_value = model_value("research_plan", {"mechanisms": [{
            "mechanism_id": "locked-field-1",
            "tower_id": "tower-1",
            "field_ids": ["vwap"],
            "evidence_refs": [source_ref],
            "hypothesis": "The locked field may provide stable cross-sectional information within the selected scope.",
        }]})
        runner = Mock()
        runner.run.return_value = SimpleNamespace(
            payload=envelope({"id": "vwap", "description": "Volume-weighted price."}),
            artifact=SimpleNamespace(id=20),
        )
        result = ResearchNodes(
            runner=runner,
            router=router,
            store=self.store,
            artifacts=self.artifacts,
        ).run_h("run-1", self.scope, "tower-1", [{"id": "vwap"}], bundle)

        self.assertEqual(result.run_state, RunState.PAUSED_MODEL)
        self.assertEqual(router.invoke.call_count, 3)
        self.assertIsNone(self.store.get_latest_research_plan("run-1"))

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
        self.assertEqual(second.payload["rejected"], [])

    def test_i_rejects_task_ids_that_duplicate_after_normalization_before_operator(self) -> None:
        plan = {"mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"]}]}
        self.store.record_research_plan("run-1", 1, "plan-hash", plan)
        router = Mock()
        router.invoke.return_value = model_value(
            "candidate_plan",
            {"plan_version": 1, "plan_hash": "plan-hash", "tasks": [
                {"task_id": "t1", "mechanism_id": "m1", "permitted_fields": ["vwap"], "transform_families": ["rank"], "count": 1},
                {"task_id": " t1", "mechanism_id": "m1", "permitted_fields": ["vwap"], "transform_families": ["rank"], "count": 1},
            ]},
        )

        nodes = ResearchNodes(runner=Mock(), router=router, store=self.store)
        with self.assertRaisesRegex(ResearchError, "duplicate task id"):
            nodes._validated_tasks(
                router.invoke().value["candidate_plan"],
                1,
                "plan-hash",
                {"m1": plan["mechanisms"][0]},
                {"rank": {"arity": 1}},
            )

    def test_i_falls_back_locally_after_invalid_mechanism(self) -> None:
        plan = {
            "mechanisms": [
                {
                    "mechanism_id": "m1",
                    "tower_id": "tower-1",
                    "field_ids": ["vwap"],
                    "evidence_refs": ["artifact:1"],
                }
            ]
        }
        self.store.record_research_plan("run-1", 1, "plan-hash", plan)
        router = Mock()
        router.invoke.return_value = model_value(
            "candidate_plan",
            {
                "plan_version": 1,
                "plan_hash": "plan-hash",
                "tasks": [{"task_id": "bad", "mechanism_id": "missing", "permitted_fields": ["vwap"], "transform_families": ["ts_delta"], "count": 1}],
            },
        )

        result = ResearchNodes(runner=Mock(), router=router, store=self.store).run_i(
            "run-1", self.scope, {"ts_delta": {"arity": 2}}
        )

        self.assertEqual(router.invoke.call_count, 1)
        self.assertGreaterEqual(len(result.payload["accepted"]), 4)
        self.assertTrue(
            all(
                item["candidate"]["materialization"]
                == "local_template_expansion"
                for item in result.payload["accepted"]
            )
        )

    def test_i_falls_back_locally_after_out_of_range_task_count(self) -> None:
        plan = {
            "mechanisms": [
                {
                    "mechanism_id": "m1",
                    "tower_id": "tower-1",
                    "field_ids": ["vwap"],
                    "evidence_refs": ["artifact:1"],
                }
            ]
        }
        self.store.record_research_plan("run-1", 1, "plan-hash", plan)
        router = Mock()
        router.invoke.return_value = model_value(
            "candidate_plan",
            {
                "plan_version": 1,
                "plan_hash": "plan-hash",
                "tasks": [{"task_id": "bad", "mechanism_id": "m1", "permitted_fields": ["vwap"], "transform_families": ["ts_delta"], "count": 21}],
            },
        )

        result = ResearchNodes(runner=Mock(), router=router, store=self.store).run_i(
            "run-1", self.scope, {"ts_delta": {"arity": 2}}
        )

        self.assertEqual(router.invoke.call_count, 1)
        self.assertGreaterEqual(len(result.payload["accepted"]), 4)
        self.assertTrue(
            all(
                item["candidate"]["materialization"]
                == "local_template_expansion"
                for item in result.payload["accepted"]
            )
        )

    def test_i_resume_after_planner_interruption_retries_only_current_idea(self) -> None:
        self.store.record_research_plan("run-1", 1, "plan-hash", {
            "mechanisms": [{
                "mechanism_id": "m1",
                "tower_id": "tower-1",
                "field_ids": ["vwap"],
                "evidence_refs": ["artifact:1"],
            }],
        })
        attempt = self.store.start_node_attempt("run-1", WorkflowNode.I)
        self.store.finish_node_attempt(
            attempt,
            "INTERRUPTED",
            {"failure": "planner_unavailable"},
        )
        router = Mock()
        router.invoke.side_effect = [
            model_value(
                "candidate_plan",
                {"tasks": [{
                    "task_id": "t1",
                    "mechanism_id": "m1",
                    "permitted_fields": ["vwap"],
                    "transform_families": ["rank"],
                    "count": 1,
                }]},
            ),
            *[
            model_value(
                "task_result",
                {"status": "COMPLETED", "payload": {"candidates": []}},
            )
            for _ in range(3)
            ],
        ]

        ResearchNodes(runner=Mock(), router=router, store=self.store).run_i(
            "run-1", self.scope, {"rank": {"arity": 1}}
        )

        self.assertEqual(router.invoke.call_count, 4)
        self.assertEqual(router.invoke.call_args_list[0].args[0].role.value, "planner")
        self.assertTrue(
            all(call.args[0].role.value == "operator" for call in router.invoke.call_args_list[1:])
        )
        self.assertEqual(self.store.get_research_idea("run-1", "p1:m1").status, "ERROR")

    def test_i_generates_stable_id_for_task_with_blank_id(self) -> None:
        self.store.record_research_plan("run-1", 1, "plan-hash", {
            "mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"]}],
        })
        router = Mock()
        router.invoke.side_effect = [
            model_value("candidate_plan", {
                "plan_version": 1,
                "plan_hash": "plan-hash",
                "tasks": [{"task_id": " ", "mechanism_id": "m1", "permitted_fields": ["vwap"], "transform_families": ["rank"], "count": 1}],
            }),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": []}}),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": []}}),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": []}}),
        ]

        nodes = ResearchNodes(runner=Mock(), router=router, store=self.store)
        result = nodes.run_i(
            "run-1", self.scope, {"rank": {"arity": 1}}
        )

        self.assertEqual(result.summary["task_ids"], ["task-1"])
        self.assertEqual(self.store.get_operator_task("run-1", "task-1").status, "COMPLETED")

    def test_i_accepts_lowercase_operator_completion_status(self) -> None:
        self.store.record_research_plan("run-1", 1, "plan-hash", {
            "mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"]}],
        })
        router = Mock()
        router.invoke.side_effect = [
            model_value("candidate_plan", {
                "plan_version": 1,
                "plan_hash": "plan-hash",
                "tasks": [{"task_id": "t1", "mechanism_id": "m1", "permitted_fields": ["vwap"], "transform_families": ["rank"], "count": 1}],
            }),
            model_value("task_result", {"status": "completed", "payload": {"candidates": []}}),
            model_value("task_result", {"status": "completed", "payload": {"candidates": []}}),
            model_value("task_result", {"status": "completed", "payload": {"candidates": []}}),
        ]

        ResearchNodes(runner=Mock(), router=router, store=self.store).run_i(
            "run-1", self.scope, {"rank": {"arity": 1}}
        )

        self.assertEqual(self.store.get_operator_task("run-1", "t1").status, "COMPLETED")

    def test_i_retries_pending_mechanism_instead_of_pausing_on_empty_candidates(self) -> None:
        self.store.record_research_plan("run-1", 1, "plan-hash", {
            "mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"]}],
        })
        router = Mock()
        router.invoke.side_effect = [
            model_value("candidate_plan", {"tasks": [{"task_id": "t1", "mechanism_id": "m1", "permitted_fields": ["vwap"], "transform_families": ["rank"], "count": 1}]}),
            *[model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": []}}) for _ in range(3)],
        ]

        nodes = ResearchNodes(runner=Mock(), router=router, store=self.store)
        result = nodes.run_i(
            "run-1", self.scope, {"rank": {"arity": 1}}
        )

        self.assertIsNone(result.run_state)
        self.assertEqual(result.next_node, WorkflowNode.I)
        self.assertEqual(result.summary["pending_mechanism_ids"], ["m1"])
        model_calls = router.invoke.call_count
        waiting = nodes.run_i("run-1", self.scope, {"rank": {"arity": 1}})
        self.assertEqual(waiting.summary["status"], "RETRY_WAIT")
        self.assertGreaterEqual(waiting.payload["retry_after_seconds"], 1)
        self.assertEqual(router.invoke.call_count, model_calls)

    def test_i_isolates_planner_timeout_to_current_idea_without_pausing_run(self) -> None:
        plan = {"mechanisms": [
            {"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"]},
            {"mechanism_id": "m2", "tower_id": "tower-1", "field_ids": ["close"], "evidence_refs": ["artifact:2"]},
        ]}
        self.store.record_research_plan("run-1", 1, "plan-hash", plan)
        router = Mock()
        router.invoke.side_effect = ModelReadTimeoutError("planner read timed out")

        result = ResearchNodes(runner=Mock(), router=router, store=self.store).run_i(
            "run-1", self.scope, {"ts_delta": {"arity": 2}}
        )

        self.assertIsNone(result.run_state)
        self.assertEqual(result.next_node, WorkflowNode.I)
        self.assertEqual(len(result.payload["accepted"]), 4)
        self.assertEqual(self.store.get_research_idea("run-1", "p1:m1").status, "READY")
        self.assertEqual(
            self.store.get_research_idea("run-1", "p1:m2").status,
            "PENDING_INSPECT",
        )
        self.assertEqual(router.invoke.call_count, 1)

    def test_i_accepts_success_operator_status_with_candidates(self) -> None:
        self.store.record_research_plan("run-1", 1, "plan-hash", {
            "mechanisms": [{
                "mechanism_id": "m1",
                "tower_id": "tower-1",
                "field_ids": ["vwap"],
                "evidence_refs": ["artifact:1"],
                "hypothesis": "Persistent volume-weighted price changes may reveal delayed price discovery.",
            }],
        })
        router = Mock()
        router.invoke.side_effect = [
            model_value("candidate_plan", {
                "tasks": [{
                    "task_id": "t1",
                    "mechanism_id": "m1",
                    "permitted_fields": ["vwap"],
                    "transform_families": ["time_series"],
                    "count": 1,
                }],
            }),
            model_value("task_result", {
                "status": "SUCCESS",
                "payload": {
                    "candidates": [{
                        "expression": "ts_delta(vwap, 20)",
                        "field_id": "vwap",
                        "single_mechanism": True,
                    }],
                },
            }),
        ]

        result = ResearchNodes(runner=Mock(), router=router, store=self.store).run_i(
            "run-1", self.scope, {"ts_delta": {"arity": 2}}
        )

        self.assertEqual(len(result.payload["accepted"]), 1)
        self.assertEqual(self.store.get_operator_task("run-1", "t1").result["accepted"], 1)

    def test_i_isolates_non_completed_operator_status_as_empty_result(self) -> None:
        self.store.record_research_plan("run-1", 1, "plan-hash", {
            "mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"]}],
        })
        router = Mock()
        router.invoke.side_effect = [
            model_value("candidate_plan", {
                "plan_version": 1,
                "plan_hash": "plan-hash",
                "tasks": [{"task_id": "t1", "mechanism_id": "m1", "permitted_fields": ["vwap"], "transform_families": ["rank"], "count": 1}],
            }),
            model_value("task_result", {"status": "failed", "payload": {"reason": "no expression"}}),
        ]

        result = ResearchNodes(runner=Mock(), router=router, store=self.store).run_i(
            "run-1", self.scope, {"rank": {"arity": 1}}
        )

        self.assertEqual(result.summary["accepted"], 0)
        task = self.store.get_operator_task("run-1", "t1")
        self.assertEqual(task.status, "COMPLETED")
        self.assertEqual(task.result["operator_status"], "FAILED")

    def test_i_binds_tasks_to_locked_plan_instead_of_model_metadata(self) -> None:
        self.store.record_research_plan("run-1", 1, "plan-hash", {
            "mechanisms": [{"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"]}],
        })
        router = Mock()
        router.invoke.side_effect = [
            model_value("candidate_plan", {
                "plan_version": 999,
                "plan_hash": "model-supplied-wrong-hash",
                "tasks": [{"task_id": "t1", "mechanism_id": "m1", "permitted_fields": ["vwap"], "transform_families": ["rank"], "count": 1}],
            }),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": []}}),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": []}}),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": []}}),
        ]

        ResearchNodes(runner=Mock(), router=router, store=self.store).run_i(
            "run-1", self.scope, {"rank": {"arity": 1}}
        )

        stored = self.store.get_operator_task("run-1", "t1")
        self.assertEqual(stored.plan_version, 1)
        self.assertEqual(stored.task["plan_hash"], "plan-hash")

    def test_i_falls_back_to_locked_mechanisms_when_planner_omits_tasks(self) -> None:
        tasks = ResearchNodes._fallback_tasks(
            1,
            "plan-hash",
            {
                "m1": {
                    "mechanism_id": "m1",
                    "tower_id": "tower-1",
                    "field_ids": ["vwap"],
                    "evidence_refs": ["artifact:1"],
                }
            },
            {"rank": {"arity": 1}},
        )

        self.assertEqual(len(tasks), 1)
        self.assertEqual(sum(task["count"] for task in tasks), 1)
        self.assertTrue(all(task["count"] == 1 for task in tasks))
        self.assertTrue(all(task["mechanism_id"] == "m1" for task in tasks))
        self.assertTrue(all(task["permitted_fields"] == ["vwap"] for task in tasks))
        self.assertTrue(all(task["transform_families"] == ["cross_sectional"] for task in tasks))

    def test_i_fallback_distributes_one_batch_across_ideas(self) -> None:
        mechanisms = {
            f"m{index}": {
                "mechanism_id": f"m{index}",
                "tower_id": "tower-1",
                "field_ids": [f"field_{index}"],
                "evidence_refs": ["artifact:1"],
            }
            for index in range(1, 4)
        }

        tasks = ResearchNodes._fallback_tasks(
            1, "plan-hash", mechanisms, {"ts_delta": {"arity": 2}}
        )

        totals = {
            mechanism_id: sum(
                task["count"]
                for task in tasks
                if task["mechanism_id"] == mechanism_id
            )
            for mechanism_id in mechanisms
        }
        self.assertEqual(sum(totals.values()), 30)
        self.assertEqual(sorted(totals.values()), [10, 10, 10])
        self.assertTrue(
            all(task["count"] == 10 for task in tasks)
        )
        self.assertTrue(
            all(task["transform_families"] == ["ts_delta"] for task in tasks)
        )
        self.assertTrue(
            all(task["strategy_ids"] == ["change_delta"] for task in tasks)
        )

    def test_i_expands_planner_strategy_templates_without_operator_call(self) -> None:
        plan = {
            "mechanisms": [
                {
                    "mechanism_id": "m1",
                    "tower_id": "tower-1",
                    "field_ids": ["vwap"],
                    "evidence_refs": ["artifact:1"],
                }
            ]
        }
        self.store.record_research_plan("run-1", 1, "plan-hash", plan)
        router = Mock()
        router.invoke.return_value = model_value(
            "candidate_plan",
            {
                "tasks": [
                    {
                        "task_id": "local-templates",
                        "mechanism_id": "m1",
                        "permitted_fields": ["vwap"],
                        "transform_families": ["ts_delta"],
                        "strategy_ids": ["change_delta"],
                        "count": 4,
                    }
                ]
            },
        )

        result = ResearchNodes(
            runner=Mock(), router=router, store=self.store
        ).run_i(
            "run-1",
            self.scope,
            {"ts_delta": {"arity": 2}},
            refinement_context={
                "diagnosis": {
                    "failure_class": "EXPRESSION",
                    "next_node": "I",
                    "evidence_ids": [f"metric:A{index}" for index in range(40)],
                },
                "metrics": [
                    {
                        "alpha_id": f"A{index}",
                        "failures": ["sharpe", "fitness"],
                        "metrics": {
                            "sharpe": index / 100,
                            "fitness": 0.1,
                            "turnover": 0.2,
                            "margin": 0.0001,
                            "checks": {"raw": "x" * 20_000},
                        },
                        "template_id": "unary:ts_delta",
                        "raw": {"response": "x" * 20_000},
                    }
                    for index in range(40)
                ],
                "template_density": {
                    "unary:ts_delta": {
                        "template_id": "unary:ts_delta",
                        "tested": 40,
                        "factor_density": 0.0,
                        "pass_rate": 0.0,
                    }
                },
                "anti_patterns": [
                    {
                        "code": "LOW_FACTOR_DENSITY",
                        "template_id": "unary:ts_delta",
                        "tested": 40,
                        "action": "replace_template",
                    }
                ],
            },
        )

        self.assertEqual(router.invoke.call_count, 1)
        refinement = router.invoke.call_args.args[0].context[
            "refinement_evidence"
        ]
        self.assertEqual(
            refinement["diagnosis"]["failure_class"],
            "EXPRESSION",
        )
        self.assertEqual(refinement["mechanism_id"], "m1")
        self.assertEqual(refinement["metric_summary"]["tested"], 40)
        self.assertEqual(
            len(refinement["metric_summary"]["representative_metrics"]), 3
        )
        self.assertLess(len(json.dumps(refinement)), 10_000)
        self.assertNotIn("raw", json.dumps(refinement))
        self.assertNotIn("checks", json.dumps(refinement))
        self.assertEqual(len(result.payload["accepted"]), 4)
        self.assertEqual(
            {
                item["candidate"]["expression"]
                for item in result.payload["accepted"]
            },
            {
                "ts_delta(vwap,22)",
                "ts_delta(vwap,63)",
                "ts_delta(vwap,126)",
                "ts_delta(vwap,252)",
            },
        )
        self.assertTrue(
            all(
                item["candidate"]["materialization"]
                == "local_template_expansion"
                for item in result.payload["accepted"]
            )
        )

    def test_i_does_not_mark_underfilled_legacy_idea_ready(self) -> None:
        plan = {
            "mechanisms": [
                {
                    "mechanism_id": "m1",
                    "tower_id": "tower-1",
                    "field_ids": ["vwap"],
                    "evidence_refs": ["artifact:1"],
                }
            ]
        }
        self.store.record_research_plan("run-1", 1, "plan-hash", plan)
        for index, window in enumerate((22, 63), start=1):
            self.store.add_candidate(
                "run-1",
                f"legacy-{index}",
                {
                    "expression": f"ts_zscore(vwap,{window})",
                    "mechanism_id": "m1",
                    "plan_version": 1,
                    "plan_hash": "plan-hash",
                },
            )
        idea = self.store.sync_research_ideas(
            "run-1", 1, "plan-hash", plan["mechanisms"]
        )[0]
        self.store.set_research_idea_status(
            "run-1",
            idea.idea_id,
            "PENDING_INSPECT",
            stage="INSPECT",
            error="process interrupted",
        )
        router = Mock()

        result = ResearchNodes(
            runner=Mock(), router=router, store=self.store
        ).run_i("run-1", self.scope, {"ts_delta": {"arity": 2}})

        self.assertEqual(router.invoke.call_count, 0)
        self.assertEqual(len(result.payload["accepted"]), 6)
        self.assertEqual(
            self.store.get_research_idea("run-1", "p1:m1").status,
            "READY",
        )

    def test_i_process_interruption_uses_local_fallback_without_planner(self) -> None:
        plan = {
            "mechanisms": [
                {
                    "mechanism_id": "m1",
                    "tower_id": "tower-1",
                    "field_ids": ["vwap"],
                    "evidence_refs": ["artifact:1"],
                }
            ]
        }
        self.store.record_research_plan("run-1", 1, "plan-hash", plan)
        idea = self.store.sync_research_ideas(
            "run-1", 1, "plan-hash", plan["mechanisms"]
        )[0]
        self.store.set_research_idea_status(
            "run-1",
            idea.idea_id,
            "ERROR",
            stage="INSPECT",
            error="process interrupted",
        )
        router = Mock()

        result = ResearchNodes(
            runner=Mock(), router=router, store=self.store
        ).run_i("run-1", self.scope, {"ts_delta": {"arity": 2}})

        self.assertEqual(router.invoke.call_count, 0)
        self.assertGreaterEqual(len(result.payload["accepted"]), 4)
        self.assertEqual(
            self.store.get_research_idea("run-1", "p1:m1").status,
            "READY",
        )

    def test_i_operator_backfills_only_the_strict_candidate_shortfall(self) -> None:
        self.store.record_research_plan(
            "run-1",
            1,
            "plan-hash",
            {
                "mechanisms": [
                    {
                        "mechanism_id": "m1",
                        "tower_id": "tower-1",
                        "field_ids": ["vwap"],
                        "evidence_refs": ["artifact:1"],
                    }
                ]
            },
        )
        router = Mock()
        router.invoke.side_effect = [
            model_value(
                "candidate_plan",
                {
                    "tasks": [
                        {
                            "task_id": "batch",
                            "mechanism_id": "m1",
                            "permitted_fields": ["vwap"],
                            "transform_families": ["time_series"],
                            "count": 3,
                        }
                    ]
                },
            ),
            model_value(
                "task_result",
                {
                    "status": "COMPLETED",
                    "payload": {
                        "candidates": [
                            {
                                "expression": "ts_delta(vwap,22)",
                                "field_id": "vwap",
                                "single_mechanism": True,
                            }
                        ]
                    },
                },
            ),
            model_value(
                "task_result",
                {
                    "status": "COMPLETED",
                    "payload": {
                        "candidates": [
                            {
                                "expression": "ts_delta(vwap,63)",
                                "field_id": "vwap",
                                "single_mechanism": True,
                            },
                            {
                                "expression": "ts_delta(vwap,126)",
                                "field_id": "vwap",
                                "single_mechanism": True,
                            },
                        ]
                    },
                },
            ),
        ]

        result = ResearchNodes(
            runner=Mock(), router=router, store=self.store
        ).run_i(
            "run-1", self.scope, {"ts_delta": {"arity": 2}}
        )

        self.assertEqual(len(result.payload["accepted"]), 3)
        second_operator_request = router.invoke.call_args_list[2].args[0]
        self.assertEqual(second_operator_request.context["task"]["count"], 2)
        self.assertEqual(
            second_operator_request.context["task"]["excluded_expressions"],
            ["ts_delta(vwap,22)"],
        )
        task = self.store.get_operator_task("run-1", "batch")
        self.assertEqual(task.result["accepted"], 3)
        self.assertEqual(task.result["shortfall"], 0)

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
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": []}}),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": []}}),
        ]

        result = ResearchNodes(runner=Mock(), router=router, store=self.store).run_i(
            "run-1", self.scope, {"rank": {"arity": 1}},
        )

        self.assertEqual(len(result.payload["rejected"]), 3)
        self.assertTrue(all(item["fingerprint"] == fingerprint for item in result.payload["rejected"]))
        repair_task = router.invoke.call_args_list[2].args[0].context["task"]
        self.assertEqual(len(repair_task["validation_failures"]), 3)
        self.assertEqual(repair_task["validation_failures"][0]["expression"], "rank( vwap )")
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

    def test_i_rejects_cosmetic_candidate_for_specific_research_mechanism(self) -> None:
        plan = {"mechanisms": [{
            "mechanism_id": "m1",
            "tower_id": "tower-1",
            "field_ids": ["vwap"],
            "evidence_refs": ["artifact:1"],
            "hypothesis": "Persistent changes in volume-weighted price may reveal gradual price discovery after liquidity shocks.",
        }]}
        self.store.record_research_plan("run-1", 1, "plan-hash", plan)
        router = Mock()
        router.invoke.side_effect = [
            model_value("candidate_plan", {"tasks": [{
                "task_id": "quality",
                "mechanism_id": "m1",
                "permitted_fields": ["vwap"],
                "transform_families": ["cross_sectional", "time_series"],
                "count": 2,
            }]}),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": [
                {"expression": "rank(vwap)", "field_id": "vwap", "single_mechanism": True},
                {"expression": "ts_delta(vwap,22)", "field_id": "vwap", "single_mechanism": True},
            ]}}),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": []}}),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": []}}),
        ]
        result = ResearchNodes(runner=Mock(), router=router, store=self.store).run_i(
            "run-1",
            self.scope,
            {"rank": {"arity": 1}, "ts_delta": {"arity": 2}},
        )

        self.assertEqual(len(result.payload["accepted"]), 1)
        self.assertEqual(result.payload["accepted"][0]["candidate"]["template_id"], "unary:ts_delta")
        self.assertIn("cosmetic-only", result.payload["rejected"][0]["reason"])

    def test_i_processes_one_idea_per_call_and_preserves_all_candidates(self) -> None:
        plan = {"mechanisms": [
            {"mechanism_id": "m1", "tower_id": "tower-1", "field_ids": ["vwap"], "evidence_refs": ["artifact:1"]},
            {"mechanism_id": "m2", "tower_id": "tower-1", "field_ids": ["close"], "evidence_refs": ["artifact:2"]},
        ]}
        self.store.record_research_plan("run-1", 1, "plan-hash", plan)
        router = Mock()
        router.invoke.side_effect = [
            model_value("candidate_plan", {"plan_version": 1, "plan_hash": "plan-hash", "tasks": [
                {"task_id": "t1", "mechanism_id": "m1", "permitted_fields": ["vwap"], "transform_families": ["rank"], "count": 1},
            ]}),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": [{"expression": "rank(vwap)", "field_id": "vwap", "single_mechanism": True}]}}),
            model_value("candidate_plan", {"plan_version": 1, "plan_hash": "plan-hash", "tasks": [
                {"task_id": "t2", "mechanism_id": "m2", "permitted_fields": ["close"], "transform_families": ["rank"], "count": 1},
            ]}),
            model_value("task_result", {"status": "COMPLETED", "payload": {"candidates": [{"expression": "rank(close)", "field_id": "close", "single_mechanism": True}]}}),
        ]

        nodes = ResearchNodes(runner=Mock(), router=router, store=self.store)
        first = nodes.run_i(
            "run-1", self.scope, {"rank": {"arity": 1}},
        )
        result = nodes.run_i("run-1", self.scope, {"rank": {"arity": 1}})

        self.assertEqual(first.next_node, WorkflowNode.I)
        self.assertEqual(len(result.payload["accepted"]), 2)
        self.assertEqual(result.next_node, WorkflowNode.J)
        self.assertEqual(self.store.get_operator_task("run-1", "t1").status, "COMPLETED")
        self.assertEqual(self.store.get_operator_task("run-1", "t2").status, "COMPLETED")
        self.assertEqual([call.args[0].role.value for call in router.invoke.call_args_list], ["planner", "operator", "planner", "operator"])
        first_planner_context = router.invoke.call_args_list[0].args[0].context
        self.assertEqual(first_planner_context["idea"]["mechanism_id"], "m1")
        self.assertNotIn("mechanisms", first_planner_context)

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
