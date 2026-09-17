from __future__ import annotations

import json
import unittest
from pathlib import Path

from wqb_cli.evidence import (
    BudgetPolicy,
    CostObservation,
    CostProfile,
    EvidenceRecord,
    ResearchFreezeError,
    build_evidence_record,
    build_research_freeze_manifest,
    canonical_json,
    estimate_plan_p95,
    load_research_freeze,
    sha256_json,
    verify_evidence_record,
)


def _make_research_freeze(
    root: Path,
    *,
    run_id: str,
    mechanism_id: str = "quality-1",
    field_id: str = "field-quality",
):
    main_tower = root / "main_tower.json"
    candidates = root / "candidate_datafields.json"
    mechanisms = root / "mechanism_contracts.json"
    constraints = root / "run_constraints.json"
    field_meta = root / "field_meta.json"
    manifest_path = root / "research_freeze.json"

    main_tower.write_text(
        json.dumps({
            "decision_status": "frozen_d",
            "region": "CHN",
            "delay": 1,
            "universe": "TOP2000U",
            "category": {"id": "fundamental", "name": "Fundamental"},
        }),
        encoding="utf-8",
    )
    candidates.write_text(
        json.dumps({
            "freeze_status": "FROZEN",
            "complete": True,
            "scope_pending": False,
            "fields": [{"id": field_id}],
        }),
        encoding="utf-8",
    )
    mechanisms.write_text(
        json.dumps([{
            "mechanism_id": mechanism_id,
            "field_ids": [field_id],
            "reality_evidence_refs": [],
        }]),
        encoding="utf-8",
    )
    constraints.write_text(json.dumps({"language": "FASTEXPR"}), encoding="utf-8")
    field_meta.write_text(
        json.dumps({
            "ok": True,
            "endpoint": "/data-fields/{field_id}",
            "response": {
                "status_code": 200,
                "body": {"id": field_id, "type": "MATRIX"},
            },
        }),
        encoding="utf-8",
    )
    manifest = build_research_freeze_manifest(
        run_id=run_id,
        main_tower_path=main_tower,
        candidate_datafields_path=candidates,
        mechanisms_path=mechanisms,
        run_constraints_path=constraints,
        brain_field_snapshots=[field_meta],
    )
    manifest_path.write_text(canonical_json(manifest) + "\n", encoding="utf-8")
    return manifest_path, load_research_freeze(manifest_path)


from wqb_cli.evidence.providers.wind import (
    WindResponseError,
    decide_wind_access,
    normalize_wind_evidence,
    require_wind_access,
)


class ResearchFreezeTests(unittest.TestCase):
    def test_provisional_scope_pending_candidates_cannot_be_frozen(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            main_tower = root / "main_tower.json"
            candidates = root / "candidate_datafields.json"
            mechanisms = root / "mechanism_contracts.json"
            constraints = root / "run_constraints.json"
            field_meta = root / "field_meta.json"
            main_tower.write_text(
                json.dumps({"decision_status": "frozen_d"}), encoding="utf-8"
            )
            candidates.write_text(
                json.dumps({
                    "freeze_status": "NOT_FROZEN",
                    "complete": False,
                    "scope_pending": True,
                    "fields": [{"id": "f1"}],
                }),
                encoding="utf-8",
            )
            mechanisms.write_text(
                json.dumps([{"mechanism_id": "m1", "field_ids": ["f1"]}]),
                encoding="utf-8",
            )
            constraints.write_text("{}", encoding="utf-8")
            field_meta.write_text(json.dumps({"id": "f1"}), encoding="utf-8")
            with self.assertRaisesRegex(ResearchFreezeError, "not frozen"):
                build_research_freeze_manifest(
                    run_id="pilot",
                    main_tower_path=main_tower,
                    candidate_datafields_path=candidates,
                    mechanisms_path=mechanisms,
                    run_constraints_path=constraints,
                    brain_field_snapshots=[field_meta],
                )

    def test_bare_candidate_collection_cannot_be_frozen(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            main_tower = root / "main_tower.json"
            candidates = root / "candidate_datafields.json"
            mechanisms = root / "mechanism_families.json"
            constraints = root / "run_constraints.json"
            field_meta = root / "field_meta.json"
            main_tower.write_text(json.dumps({"decision_status": "frozen_d"}), encoding="utf-8")
            candidates.write_text(json.dumps([{"id": "f1"}]), encoding="utf-8")
            mechanisms.write_text(json.dumps([{"mechanism_id": "m1", "field_ids": ["f1"]}]), encoding="utf-8")
            constraints.write_text("{}", encoding="utf-8")
            field_meta.write_text(json.dumps({"id": "f1"}), encoding="utf-8")
            with self.assertRaisesRegex(ResearchFreezeError, "frozen JSON object"):
                build_research_freeze_manifest(
                    run_id="pilot",
                    main_tower_path=main_tower,
                    candidate_datafields_path=candidates,
                    mechanisms_path=mechanisms,
                    run_constraints_path=constraints,
                    brain_field_snapshots=[field_meta],
                )

    def test_all_frozen_candidates_require_brain_metadata_snapshots(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            main_tower = root / "main_tower.json"
            candidates = root / "candidate_datafields.json"
            mechanisms = root / "mechanism_families.json"
            constraints = root / "run_constraints.json"
            field_meta = root / "field_meta.json"
            main_tower.write_text(json.dumps({"decision_status": "frozen_d"}), encoding="utf-8")
            candidates.write_text(json.dumps({
                "freeze_status": "FROZEN",
                "complete": True,
                "scope_pending": False,
                "fields": [{"id": "f1"}, {"id": "f2"}],
            }), encoding="utf-8")
            mechanisms.write_text(json.dumps([
                {"mechanism_id": "m1", "field_ids": ["f1"]},
                {"mechanism_id": "m2", "field_ids": ["f2"]},
            ]), encoding="utf-8")
            constraints.write_text("{}", encoding="utf-8")
            field_meta.write_text(json.dumps({"id": "f1"}), encoding="utf-8")
            with self.assertRaisesRegex(ResearchFreezeError, "do not cover frozen candidates"):
                build_research_freeze_manifest(
                    run_id="pilot",
                    main_tower_path=main_tower,
                    candidate_datafields_path=candidates,
                    mechanisms_path=mechanisms,
                    run_constraints_path=constraints,
                    brain_field_snapshots=[field_meta],
                )

    def test_freeze_verification_detects_post_split_artifact_tampering(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path, _ = _make_research_freeze(root, run_id="tamper")
            candidates = root / "candidate_datafields.json"
            payload = json.loads(candidates.read_text(encoding="utf-8"))
            payload["fields"].append({"id": "late-field"})
            candidates.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ResearchFreezeError, "hash mismatch"):
                load_research_freeze(manifest_path)

    def test_plan_check_rejects_mechanism_absent_from_frozen_baseline(self) -> None:
        import argparse
        import tempfile
        from wqb_cli.evidence.plugin import EvidencePlugin

        class Context:
            last = None
            def write_json(self, payload, output=None):
                self.last = payload

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            freeze_path, _ = _make_research_freeze(
                root, run_id="mechanism-gate", mechanism_id="quality-1"
            )
            plan = root / "plan.json"
            plan.write_text(json.dumps({
                "run_id": "mechanism-gate",
                "freeze_manifest": str(freeze_path),
                "available_points": 1000,
                "checks": [{
                    "mechanism_id": "quality-2",
                    "node": "G",
                    "purpose": "research",
                    "server_type": "stock_data",
                    "tool_name": "get_stock_fundamentals",
                }],
            }), encoding="utf-8")
            parser = argparse.ArgumentParser()
            sub = parser.add_subparsers(dest="command", required=True)
            plugin = EvidencePlugin()
            plugin.register(sub).set_defaults(_wqb_plugin=plugin)
            args = parser.parse_args([
                "evidence", "--store-root", str(root / "store"),
                "wind", "plan-check", "--input", str(plan),
            ])
            context = Context()
            self.assertEqual(plugin.handle(args, context), 1)
            self.assertEqual(context.last["reason"], "mechanism_not_frozen")

    def test_research_plan_identity_is_bound_to_freeze_hash(self) -> None:
        from wqb_cli.evidence.execution import ExecutableRealityCheck, plan_identity

        checks = [ExecutableRealityCheck(
            check_id="a",
            mechanism_id="m1",
            node="G",
            purpose="research",
            server_type="stock_data",
            tool_name="get_stock_fundamentals",
            params={"question": "x"},
        )]
        first = plan_identity(checks, freeze_manifest_sha256="a" * 64)
        second = plan_identity(checks, freeze_manifest_sha256="b" * 64)
        self.assertNotEqual(first, second)


class EvidenceProvenanceTests(unittest.TestCase):
    def test_build_record_is_canonical_and_verifiable(self) -> None:
        raw_a = {"b": 2, "a": 1}
        raw_b = {"a": 1, "b": 2}
        self.assertEqual(sha256_json(raw_a), sha256_json(raw_b))

        record = build_evidence_record(
            provider="wind",
            query_type="economic_data.query_economic_indicator_data",
            request={"question": "M0001", "observation": "10"},
            raw_response=raw_a,
            normalized_response={"value": [1, 2]},
            retrieved_at="2026-09-07T00:00:00Z",
            provider_contract_version="wind-skill@abc123",
            entity_ids={"edb_code": "M0001"},
            supports=("mechanism:macro-demand",),
        )

        ok, problems = verify_evidence_record(record)
        self.assertTrue(ok)
        self.assertEqual(problems, ())
        payload = record.to_dict()
        self.assertEqual(payload["request"]["question"], "M0001")
        self.assertEqual(payload["raw_response"], raw_a)
        self.assertEqual(payload["entity_ids"], {"edb_code": "M0001"})

    def test_tampered_record_fails_hash_verification(self) -> None:
        record = build_evidence_record(
            provider="wind",
            query_type="stock_data.get_stock_fundamentals",
            request={"question": "600519.SH ROE"},
            raw_response={"content": [{"text": "ok"}]},
            retrieved_at="2026-09-07T00:00:00Z",
            provider_contract_version="wind-skill@abc123",
        )
        payload = record.to_dict()
        payload["raw_response"] = {"content": [{"text": "tampered"}]}
        tampered = EvidenceRecord.from_dict(payload)

        ok, problems = verify_evidence_record(tampered)
        self.assertFalse(ok)
        self.assertIn("raw_sha256_mismatch", problems)

    def test_normalized_response_tampering_changes_evidence_identity(self) -> None:
        record = build_evidence_record(
            provider="wind",
            query_type="stock_data.get_stock_fundamentals",
            request={"question": "600519.SH ROE"},
            raw_response={"content": [{"text": "raw"}]},
            normalized_response={"roe": 0.31},
            retrieved_at="2026-09-07T00:00:00Z",
            provider_contract_version="wind-skill@abc123",
        )
        payload = record.to_dict()
        payload["normalized_response"] = {"roe": 0.99}
        tampered = EvidenceRecord.from_dict(payload)
        ok, problems = verify_evidence_record(tampered)
        self.assertFalse(ok)
        self.assertIn("evidence_id_mismatch", problems)


class WindEvidenceTests(unittest.TestCase):
    def test_edb_response_preserves_metadata_and_cli_warnings(self) -> None:
        backend_payload = {
            "metrics": [
                {
                    "meta": {
                        "code": "M5567876",
                        "name": "中国GDP现价当季值",
                        "unit": "亿元",
                        "magnitude": 100000000,
                        "source": "国家统计局",
                        "updateDate": "2026-08-15",
                        "freq": "Q",
                    },
                    "date": ["2026-06-30"],
                    "value": [123.4],
                }
            ]
        }
        raw = {
            "content": [{"text": json.dumps(backend_payload, ensure_ascii=False)}],
            "cli_meta": {
                "schema_version": "1.0",
                "server_type": "economic_data",
                "tool_name": "query_economic_indicator_data",
                "completeness": "not_asserted",
                "warnings": [{"code": "EXAMPLE_WARNING", "path": "$.metrics"}],
            },
        }

        record = normalize_wind_evidence(
            server_type="economic_data",
            tool_name="query_economic_indicator_data",
            request={"question": "M5567876", "observation": "1"},
            raw_response=raw,
            provider_contract_version="wind-skill@d2b0015",
            retrieved_at="2026-09-07T00:00:00Z",
            entity_ids={"edb_code": "M5567876"},
            supports=("mechanism:gdp-regime",),
        )

        payload = record.to_dict()
        self.assertEqual(record.provider, "wind")
        self.assertEqual(
            record.query_type, "economic_data.query_economic_indicator_data"
        )
        self.assertEqual(record.provider_sources, ("国家统计局",))
        self.assertEqual(record.update_dates, ("2026-08-15",))
        self.assertEqual(payload["normalized_response"], backend_payload)
        self.assertEqual(payload["warnings"][0]["code"], "EXAMPLE_WARNING")
        self.assertTrue(any("not_asserted" in item for item in record.limitations))

    def test_error_envelope_is_not_admitted_as_evidence(self) -> None:
        with self.assertRaises(WindResponseError) as raised:
            normalize_wind_evidence(
                server_type="stock_data",
                tool_name="get_stock_fundamentals",
                request={"question": "600519.SH ROE"},
                raw_response={"ok": False, "code": "AUTH_ERROR", "message": "missing key"},
                provider_contract_version="wind-skill@d2b0015",
            )
        self.assertEqual(raised.exception.code, "AUTH_ERROR")

    def test_route_mismatch_is_rejected(self) -> None:
        with self.assertRaises(WindResponseError) as raised:
            normalize_wind_evidence(
                server_type="stock_data",
                tool_name="get_stock_fundamentals",
                request={"question": "600519.SH ROE"},
                raw_response={
                    "content": [{"text": "{}"}],
                    "cli_meta": {
                        "server_type": "analytics_data",
                        "tool_name": "get_financial_data",
                    },
                },
                provider_contract_version="wind-skill@d2b0015",
            )
        self.assertEqual(raised.exception.code, "ROUTE_MISMATCH")

    def test_workflow_standing_is_enforced(self) -> None:
        self.assertTrue(decide_wind_access("G", "research").allowed)
        self.assertTrue(decide_wind_access("H", "clarification").allowed)
        self.assertTrue(decide_wind_access("K", "diagnosis").allowed)
        self.assertFalse(decide_wind_access("F", "research").allowed)
        self.assertFalse(decide_wind_access("J", "research").allowed)
        with self.assertRaises(PermissionError):
            require_wind_access("I", "research")


class BudgetTests(unittest.TestCase):
    def test_profile_plan_and_gate_use_p95(self) -> None:
        query_type = "economic_data.query_economic_indicator_data"
        observations = [
            CostObservation(query_type, 1000, 990, True, "t1"),
            CostObservation(query_type, 990, 970, True, "t2"),
            CostObservation(query_type, 970, 940, True, "t3"),
            CostObservation(query_type, 940, 900, True, "t4"),
            CostObservation(query_type, 900, 850, True, "t5"),
            CostObservation(query_type, 850, 850, False, "refunded-failure"),
        ]
        profile = CostProfile.from_observations(query_type, observations)
        self.assertEqual(profile.p50, 30)
        self.assertEqual(profile.p95, 50)
        estimate = estimate_plan_p95({query_type: 4}, {query_type: profile})
        self.assertEqual(estimate, 200)

        policy = BudgetPolicy()
        allowed = policy.decide(
            available_points=1000, estimated_p95=estimate, purpose="research"
        )
        rejected = policy.decide(
            available_points=1000, estimated_p95=700, purpose="research"
        )
        self.assertTrue(allowed.allowed)
        self.assertEqual(allowed.allocation_points, 600)
        self.assertFalse(rejected.allowed)

    def test_calibration_rejects_grant_or_recharge_boundary(self) -> None:
        with self.assertRaisesRegex(ValueError, "grant/recharge"):
            CostObservation(
                "stock_data.get_stock_price_indicators",
                points_before=100,
                points_after=110,
                success=True,
                timestamp="t",
            )


if __name__ == "__main__":
    unittest.main()

class EvidenceStoreTests(unittest.TestCase):
    def test_store_is_immutable_and_provider_lock_detects_drift(self) -> None:
        import tempfile
        from pathlib import Path
        from wqb_cli.evidence import EvidenceStore, EvidenceStoreError

        with tempfile.TemporaryDirectory() as tmp:
            store = EvidenceStore(tmp)
            record = build_evidence_record(
                provider="wind",
                query_type="stock_data.get_stock_fundamentals",
                request={"question": "600519.SH ROE"},
                raw_response={"content": [{"text": "{}"}]},
                retrieved_at="2026-09-07T00:00:00Z",
                provider_contract_version="wind-skill:sha256:abc",
            )
            first = store.save_record(record)
            second = store.save_record(record)
            self.assertEqual(first, second)
            loaded = store.load_record("wind", record.evidence_id)
            self.assertEqual(loaded.evidence_id, record.evidence_id)

            store.lock_provider_contract(
                run_id="run-1", provider="wind", contract_version="v1"
            )
            self.assertEqual(
                store.read_provider_lock(run_id="run-1", provider="wind"), "v1"
            )
            with self.assertRaises(EvidenceStoreError):
                store.lock_provider_contract(
                    run_id="run-1", provider="wind", contract_version="v2"
                )

    def test_cost_ledger_roundtrip(self) -> None:
        import tempfile
        from wqb_cli.evidence import EvidenceStore

        with tempfile.TemporaryDirectory() as tmp:
            store = EvidenceStore(tmp)
            observation = CostObservation(
                "stock_data.get_stock_fundamentals", 1000, 975, True, "t"
            )
            store.append_cost("wind", observation)
            loaded = store.load_costs("wind")
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].cost, 25)


class RealityPlanTests(unittest.TestCase):
    def test_research_plan_caps_mechanisms_and_calls(self) -> None:
        from wqb_cli.evidence import RealityCheckSpec, RealityPlanError, assess_wind_reality_plan

        query = "stock_data.get_stock_fundamentals"
        profile = CostProfile(query_type=query, sample_count=3, p50=10, p95=20, maximum=20)
        specs = [
            RealityCheckSpec("m1", "G", "research", "stock_data", "get_stock_fundamentals"),
            RealityCheckSpec("m1", "G", "research", "stock_data", "get_stock_fundamentals"),
            RealityCheckSpec("m2", "G", "reality_check", "stock_data", "get_stock_fundamentals"),
        ]
        assessment = assess_wind_reality_plan(
            specs, profiles={query: profile}, available_points=1000
        )
        self.assertTrue(assessment.budget.allowed)
        self.assertEqual(assessment.call_count, 3)
        self.assertEqual(assessment.estimated_p95, 60)

        too_many = [
            RealityCheckSpec("m1", "G", "research", "stock_data", "get_stock_fundamentals")
            for _ in range(4)
        ]
        with self.assertRaises(RealityPlanError):
            assess_wind_reality_plan(
                too_many, profiles={query: profile}, available_points=1000
            )

    def test_diagnosis_plan_is_separately_bounded(self) -> None:
        from wqb_cli.evidence import RealityCheckSpec, RealityPlanError, assess_wind_reality_plan

        query = "economic_data.query_economic_indicator_data"
        profile = CostProfile(query_type=query, sample_count=3, p50=10, p95=10, maximum=10)
        specs = [
            RealityCheckSpec(f"m{i}", "K", "diagnosis", "economic_data", "query_economic_indicator_data")
            for i in range(4)
        ]
        with self.assertRaises(RealityPlanError):
            assess_wind_reality_plan(specs, profiles={query: profile}, available_points=1000)


class WindRuntimeTests(unittest.TestCase):
    def _fake_skill(self, root):
        from pathlib import Path
        skill = Path(root) / "wind-mcp-skill"
        (skill / "scripts").mkdir(parents=True)
        (skill / "references").mkdir()
        (skill / "SKILL.md").write_text("# fake skill\n", encoding="utf-8")
        (skill / "scripts" / "tool-manifest.json").write_text(
            '{"stock_data":["get_stock_fundamentals"]}', encoding="utf-8"
        )
        (skill / "references" / "stock.md").write_text("# stock contract\n", encoding="utf-8")
        (skill / "scripts" / "cli.mjs").write_text(
            """import fs from 'node:fs';
const [verb, serverType, toolName, paramsArg] = process.argv.slice(2);
if (verb !== 'call') process.exit(2);
const p = paramsArg.startsWith('@') ? paramsArg.slice(1) : null;
const params = JSON.parse(fs.readFileSync(p, 'utf8'));
const body = {echo: params, data: {unit: '元'}};
const out = {content:[{text:JSON.stringify(body)}], cli_meta:{schema_version:'1.0',server_type:serverType,tool_name:toolName,completeness:'not_asserted',warnings:[]}};
process.stdout.write(JSON.stringify(out));
""",
            encoding="utf-8",
        )
        return skill

    def test_runtime_executes_official_cli_shape_and_cleans_request_file(self) -> None:
        import tempfile
        from wqb_cli.evidence.providers.wind import WindRuntime

        with tempfile.TemporaryDirectory() as tmp:
            skill = self._fake_skill(tmp)
            runtime = WindRuntime(skill_dir=skill)
            status = runtime.status()
            self.assertTrue(status.available)
            result = runtime.call(
                node="G",
                purpose="research",
                server_type="stock_data",
                tool_name="get_stock_fundamentals",
                params={"question": "600519.SH ROE"},
                entity_ids={"windcode": "600519.SH"},
                supports=("mechanism:quality",),
            )
            self.assertEqual(result.record.provider, "wind")
            self.assertEqual(result.record.entity_ids, (("windcode", "600519.SH"),))
            leftovers = list((skill / "scripts").glob("request-wqb-*.json"))
            self.assertEqual(leftovers, [])

    def test_runtime_rejects_contract_drift_before_call(self) -> None:
        import tempfile
        from wqb_cli.evidence.providers.wind import WindRuntime

        with tempfile.TemporaryDirectory() as tmp:
            skill = self._fake_skill(tmp)
            initial = WindRuntime(skill_dir=skill).status().provider_contract_version
            self.assertIsNotNone(initial)
            (skill / "references" / "stock.md").write_text("# changed\n", encoding="utf-8")
            runtime = WindRuntime(skill_dir=skill, expected_contract_version=initial)
            self.assertEqual(runtime.status().reason, "provider_contract_drift")
            with self.assertRaisesRegex(Exception, "provider_contract_drift"):
                runtime.call(
                    node="G",
                    purpose="research",
                    server_type="stock_data",
                    tool_name="get_stock_fundamentals",
                    params={"question": "x"},
                )

    def test_runtime_rejects_mid_call_contract_drift(self) -> None:
        import tempfile
        from wqb_cli.evidence.providers.wind import WindRuntime, WindRuntimeError

        with tempfile.TemporaryDirectory() as tmp:
            skill = self._fake_skill(tmp)
            cli = skill / "scripts" / "cli.mjs"
            cli.write_text(
                """import fs from 'node:fs';
const [verb, serverType, toolName, paramsArg] = process.argv.slice(2);
const p = paramsArg.slice(1);
const params = JSON.parse(fs.readFileSync(p, 'utf8'));
fs.writeFileSync('references/stock.md', '# changed during call\\n');
const out = {content:[{text:JSON.stringify({echo:params})}], cli_meta:{server_type:serverType,tool_name:toolName,warnings:[],completeness:'not_asserted'}};
process.stdout.write(JSON.stringify(out));
""",
                encoding="utf-8",
            )
            runtime = WindRuntime(skill_dir=skill)
            with self.assertRaisesRegex(WindRuntimeError, "changed during the call"):
                runtime.call(
                    node="G",
                    purpose="research",
                    server_type="stock_data",
                    tool_name="get_stock_fundamentals",
                    params={"question": "x"},
                )


class EvidencePluginTests(unittest.TestCase):
    def test_plugin_registers_status_cost_gate_and_plan_commands(self) -> None:
        import argparse
        from wqb_cli.evidence.plugin import EvidencePlugin

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command", required=True)
        plugin = EvidencePlugin()
        root = plugin.register(sub)
        root.set_defaults(_wqb_plugin=plugin)

        status = parser.parse_args(["evidence", "wind", "status"])
        add = parser.parse_args(
            [
                "evidence",
                "cost",
                "add",
                "stock_data.get_stock_fundamentals",
                "--before",
                "1000",
                "--after",
                "980",
                "--success",
            ]
        )
        plan = parser.parse_args(["evidence", "wind", "plan-check", "--input", "plan.json"])
        compare = parser.parse_args([
            "evidence", "experiment", "compare",
            "--baseline-contracts", "a.json",
            "--wind-contracts", "b.json",
        ])
        self.assertEqual(status.wind_command, "status")
        self.assertEqual(add.cost_command, "add")
        self.assertTrue(add.success)
        self.assertEqual(plan.wind_command, "plan-check")
        self.assertEqual(compare.experiment_command, "compare")

class EvidenceExperimentTests(unittest.TestCase):
    def test_compare_mechanism_arms_detects_elimination_direction_and_falsification(self) -> None:
        from wqb_cli.evidence import compare_mechanism_arms

        baseline = [
            {
                "mechanism_id": "m1",
                "direction_status": "uncertain",
                "falsification_conditions": ["a"],
                "reality_evidence_refs": [],
            },
            {
                "mechanism_id": "m2",
                "direction_status": "supported",
                "falsification_conditions": ["x"],
                "reality_evidence_refs": [],
            },
        ]
        wind = [
            {
                "mechanism_id": "m1",
                "direction_status": "supported",
                "falsification_conditions": ["a", "b"],
                "reality_evidence_refs": ["wind:e1"],
            }
        ]
        report = compare_mechanism_arms(
            baseline,
            wind,
            baseline_candidates=[{"id": 1}, {"id": 2}, {"id": 3}],
            wind_candidates=[{"id": 1}],
        )
        payload = report.to_dict()
        self.assertEqual(report.eliminated_before_i, ("m2",))
        self.assertEqual(report.added_in_wind_arm, ())
        self.assertEqual(report.direction_changes, (("m1", "uncertain", "supported"),))
        self.assertEqual(report.falsification_strengthened, ("m1",))
        self.assertEqual(report.reality_evidence_mechanisms, ("m1",))
        self.assertEqual(payload["candidate_reduction"], 2)
        self.assertFalse(payload["new_mechanism_violation"])

    def test_compare_flags_wind_arm_new_mechanism_as_protocol_violation(self) -> None:
        from wqb_cli.evidence import compare_mechanism_arms

        report = compare_mechanism_arms(
            [{"mechanism_id": "m1"}],
            [{"mechanism_id": "m1"}, {"mechanism_id": "m-new", "reality_evidence_refs": ["e"]}],
        )
        self.assertEqual(report.added_in_wind_arm, ("m-new",))
        self.assertTrue(report.to_dict()["new_mechanism_violation"])

class WindSemanticInferenceTests(unittest.TestCase):
    def test_structured_windcode_and_period_are_inferred_without_nlp_guessing(self) -> None:
        from wqb_cli.evidence.providers.wind import normalize_wind_evidence

        raw = {
            "content": [{"text": "{}"}],
            "cli_meta": {
                "server_type": "stock_data",
                "tool_name": "get_stock_kline",
                "completeness": "not_asserted",
                "warnings": [],
            },
        }
        record = normalize_wind_evidence(
            server_type="stock_data",
            tool_name="get_stock_kline",
            request={
                "windcode": "600519.SH",
                "begin_date": "2025-01-01",
                "end_date": "2025-12-31",
                "period": "1d",
            },
            raw_response=raw,
            provider_contract_version="wind-skill:sha256:x",
        )
        self.assertEqual(dict(record.entity_ids), {"windcode": "600519.SH"})
        self.assertEqual(
            dict(record.period),
            {"aggregation": "1d", "begin": "2025-01-01", "end": "2025-12-31"},
        )

    def test_edb_codes_and_observation_are_inferred(self) -> None:
        from wqb_cli.evidence.providers.wind import normalize_wind_evidence

        raw = {
            "content": [{"text": '{"metrics":[]}'}],
            "cli_meta": {
                "server_type": "economic_data",
                "tool_name": "query_economic_indicator_data",
                "completeness": "not_asserted",
                "warnings": [],
            },
        }
        record = normalize_wind_evidence(
            server_type="economic_data",
            tool_name="query_economic_indicator_data",
            request={"question": "M5567876, M0000001", "observation": "10"},
            raw_response=raw,
            provider_contract_version="wind-skill:sha256:x",
        )
        self.assertEqual(dict(record.entity_ids)["edb_codes"], "M5567876,M0000001")
        self.assertEqual(dict(record.period)["observation"], "10")

    def test_financial_docs_without_locator_is_downgraded(self) -> None:
        from wqb_cli.evidence.providers.wind import normalize_wind_evidence

        raw = {
            "content": [{"text": '{"documents":[{"title":"公告","text":"片段"}]}'}],
            "cli_meta": {
                "server_type": "financial_docs",
                "tool_name": "get_company_announcements",
                "completeness": "not_asserted",
                "warnings": [],
            },
        }
        record = normalize_wind_evidence(
            server_type="financial_docs",
            tool_name="get_company_announcements",
            request={"query": "贵州茅台 2024 年报"},
            raw_response=raw,
            provider_contract_version="wind-skill:sha256:x",
        )
        self.assertTrue(any("stable document URL/id locator" in item for item in record.limitations))

class EvidencePluginEndToEndTests(unittest.TestCase):
    class _Context:
        def __init__(self) -> None:
            self.outputs = []

        def write_json(self, payload, output=None) -> None:
            import json
            from pathlib import Path
            self.outputs.append(payload)
            if output:
                target = Path(output)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _fake_skill(self, root):
        from pathlib import Path
        skill = Path(root) / "wind-mcp-skill"
        (skill / "scripts").mkdir(parents=True)
        (skill / "references").mkdir()
        (skill / "SKILL.md").write_text("# fake skill\n", encoding="utf-8")
        (skill / "scripts" / "tool-manifest.json").write_text(
            '{"stock_data":["get_stock_fundamentals"]}', encoding="utf-8"
        )
        (skill / "references" / "stock.md").write_text("# stock\n", encoding="utf-8")
        (skill / "scripts" / "cli.mjs").write_text(
            """import fs from 'node:fs';
const [verb, serverType, toolName, paramsArg] = process.argv.slice(2);
const params = JSON.parse(fs.readFileSync(paramsArg.slice(1), 'utf8'));
const backend = {company:'贵州茅台', requested:params.question, meta:{source:'WindTest',unit:'%'}};
const out = {content:[{text:JSON.stringify(backend)}],cli_meta:{schema_version:'1.0',server_type:serverType,tool_name:toolName,completeness:'not_asserted',warnings:[]}};
process.stdout.write(JSON.stringify(out));
""",
            encoding="utf-8",
        )
        return skill

    def test_execute_plan_persists_verifiable_record_and_run_lock(self) -> None:
        import argparse
        import json
        import tempfile
        from pathlib import Path
        from wqb_cli.evidence import EvidenceStore, verify_evidence_record
        from wqb_cli.evidence.plugin import EvidencePlugin

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = self._fake_skill(root)
            store_root = root / "store"
            freeze_path, _ = _make_research_freeze(
                root, run_id="run-e2e", mechanism_id="quality"
            )
            plan_path = root / "node" / "wind-plan.json"
            plan_path.parent.mkdir(parents=True)
            plan_path.write_text(
                json.dumps(
                    {
                        "run_id": "run-e2e",
                        "freeze_manifest": str(freeze_path),
                        "available_points": 1000,
                        "checks": [
                            {
                                "check_id": "quality-roe",
                                "mechanism_id": "quality",
                                "node": "G",
                                "purpose": "research",
                                "server_type": "stock_data",
                                "tool_name": "get_stock_fundamentals",
                                "cost_profile_key": "stock_data.get_stock_fundamentals:single",
                                "params": {"question": "600519.SH ROE"},
                                "entity_ids": {"windcode": "600519.SH"},
                                "supports": ["mechanism:quality"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            parser = argparse.ArgumentParser()
            sub = parser.add_subparsers(dest="command", required=True)
            plugin = EvidencePlugin()
            plugin.register(sub).set_defaults(_wqb_plugin=plugin)
            context = self._Context()

            key = "stock_data.get_stock_fundamentals:single"
            for before, after in ((1000, 990), (990, 980), (980, 970)):
                args = parser.parse_args(
                    [
                        "evidence",
                        "--store-root",
                        str(store_root),
                        "cost",
                        "add",
                        key,
                        "--before",
                        str(before),
                        "--after",
                        str(after),
                        "--success",
                    ]
                )
                self.assertEqual(plugin.handle(args, context), 0)

            args = parser.parse_args(
                [
                    "evidence",
                    "--store-root",
                    str(store_root),
                    "balance",
                    "add",
                    "wind",
                    "--available-points",
                    "970",
                    "--source",
                    "alice_market_account",
                ]
            )
            self.assertEqual(plugin.handle(args, context), 0)

            args = parser.parse_args(
                [
                    "evidence",
                    "--store-root",
                    str(store_root),
                    "wind",
                    "plan-check",
                    "--input",
                    str(plan_path),
                ]
            )
            self.assertEqual(plugin.handle(args, context), 0)
            self.assertTrue(context.outputs[-1]["ok"])

            args = parser.parse_args(
                [
                    "evidence",
                    "--store-root",
                    str(store_root),
                    "wind",
                    "execute-plan",
                    "--input",
                    str(plan_path),
                    "--skill-dir",
                    str(skill),
                ]
            )
            self.assertEqual(plugin.handle(args, context), 0)
            report = context.outputs[-1]
            self.assertEqual(report["status"], "completed")
            self.assertEqual(len(report["completed"]), 1)
            evidence_id = report["completed"][0]["evidence_id"]
            stored_path = Path(report["completed"][0]["stored_path"])
            self.assertTrue(stored_path.is_file())

            store = EvidenceStore(store_root)
            self.assertEqual(
                stored_path,
                store.records_root / "wind" / f"{evidence_id}.json",
            )
            self.assertEqual(Path(report["evidence_store_root"]), store.root)
            record = store.load_record("wind", evidence_id)
            self.assertTrue(verify_evidence_record(record)[0])
            self.assertEqual(
                store.read_provider_lock(run_id="run-e2e", provider="wind"),
                record.provider_contract_version,
            )
            self.assertEqual(dict(record.entity_ids)["windcode"], "600519.SH")
            self.assertEqual(record.provider_sources, ("WindTest",))

class WindRuntimeErrorSemanticsTests(unittest.TestCase):
    def test_auth_error_is_preserved_even_if_skill_changes_during_failed_call(self) -> None:
        import tempfile
        from pathlib import Path
        from wqb_cli.evidence.providers.wind import WindResponseError, WindRuntime

        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "wind-mcp-skill"
            (skill / "scripts").mkdir(parents=True)
            (skill / "references").mkdir()
            (skill / "SKILL.md").write_text("# fake\n", encoding="utf-8")
            (skill / "scripts" / "tool-manifest.json").write_text("{}", encoding="utf-8")
            (skill / "references" / "stock.md").write_text("# before\n", encoding="utf-8")
            (skill / "scripts" / "cli.mjs").write_text(
                """import fs from 'node:fs';
fs.writeFileSync('references/stock.md', '# after\\n');
process.stdout.write(JSON.stringify({ok:false,code:'AUTH_ERROR',message:'missing key'}));
process.exitCode = 1;
""",
                encoding="utf-8",
            )
            runtime = WindRuntime(skill_dir=skill)
            with self.assertRaises(WindResponseError) as raised:
                runtime.call(
                    node="G",
                    purpose="research",
                    server_type="stock_data",
                    tool_name="get_stock_fundamentals",
                    params={"question": "x"},
                )
            self.assertEqual(raised.exception.code, "AUTH_ERROR")

class EvidencePluginFailureTests(unittest.TestCase):
    class _Context:
        def __init__(self):
            self.last = None
        def write_json(self, payload, output=None):
            self.last = payload

    def test_plan_check_reports_missing_cost_profile(self) -> None:
        import argparse
        import json
        import tempfile
        from pathlib import Path
        from wqb_cli.evidence.plugin import EvidencePlugin

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            freeze_path, _ = _make_research_freeze(
                root, run_id="run-missing-cost", mechanism_id="m1"
            )
            plan = root / "plan.json"
            plan.write_text(
                json.dumps({
                    "run_id": "run-missing-cost",
                    "freeze_manifest": str(freeze_path),
                    "available_points": 1000,
                    "checks": [{
                        "mechanism_id": "m1",
                        "node": "G",
                        "purpose": "research",
                        "server_type": "stock_data",
                        "tool_name": "get_stock_fundamentals",
                    }],
                }),
                encoding="utf-8",
            )
            parser = argparse.ArgumentParser()
            sub = parser.add_subparsers(dest="command", required=True)
            plugin = EvidencePlugin()
            plugin.register(sub).set_defaults(_wqb_plugin=plugin)
            args = parser.parse_args([
                "evidence", "--store-root", str(root / "store"),
                "wind", "plan-check", "--input", str(plan),
            ])
            context = self._Context()
            code = plugin.handle(args, context)
            self.assertEqual(code, 1)
            self.assertEqual(context.last["reason"], "missing_cost_profile")

    def test_unplanned_raw_call_is_blocked_before_provider_execution(self) -> None:
        import argparse
        import tempfile
        from pathlib import Path
        from wqb_cli.evidence.plugin import EvidencePlugin

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "wind-mcp-skill"
            (skill / "scripts").mkdir(parents=True)
            (skill / "references").mkdir()
            (skill / "SKILL.md").write_text("# fake\n", encoding="utf-8")
            (skill / "scripts" / "tool-manifest.json").write_text("{}", encoding="utf-8")
            (skill / "references" / "stock.md").write_text("# stock\n", encoding="utf-8")
            (skill / "scripts" / "cli.mjs").write_text(
                "process.stdout.write(JSON.stringify({ok:false,code:'AUTH_ERROR',message:'missing key'})); process.exitCode=1;\n",
                encoding="utf-8",
            )
            parser = argparse.ArgumentParser()
            sub = parser.add_subparsers(dest="command", required=True)
            plugin = EvidencePlugin()
            plugin.register(sub).set_defaults(_wqb_plugin=plugin)
            args = parser.parse_args([
                "evidence", "--store-root", str(root / "store"),
                "wind", "call", "G", "research", "stock_data", "get_stock_fundamentals",
                "--params", '{"question":"x"}', "--skill-dir", str(skill),
            ])
            context = self._Context()
            code = plugin.handle(args, context)
            self.assertEqual(code, 2)
            self.assertEqual(context.last["reason"], "unplanned_wind_call_forbidden")
            self.assertFalse(context.last["admitted_evidence"])
            self.assertFalse((root / "store" / "records").exists())


class CalibrationRobustnessTests(unittest.TestCase):
    def test_reality_plan_rejects_thin_profile(self) -> None:
        from wqb_cli.evidence import RealityCheckSpec, RealityPlanError, assess_wind_reality_plan

        query = "stock_data.get_stock_fundamentals"
        thin = CostProfile(query_type=query, sample_count=2, p50=10, p95=20, maximum=20)
        spec = RealityCheckSpec("m1", "G", "research", "stock_data", "get_stock_fundamentals")
        with self.assertRaisesRegex(RealityPlanError, "insufficient calibration"):
            assess_wind_reality_plan([spec], profiles={query: thin}, available_points=1000)

    def test_cost_profile_key_can_separate_request_width_classes(self) -> None:
        from wqb_cli.evidence import RealityCheckSpec, assess_wind_reality_plan

        key = "stock_data.get_stock_price_indicators:batch10x5"
        profile = CostProfile(query_type=key, sample_count=3, p50=30, p95=40, maximum=40)
        specs = [
            RealityCheckSpec(
                "m1",
                "G",
                "research",
                "stock_data",
                "get_stock_price_indicators",
                cost_profile_key=key,
            )
        ]
        assessment = assess_wind_reality_plan(
            specs, profiles={key: profile}, available_points=1000
        )
        self.assertEqual(dict(assessment.query_counts), {key: 1})
        self.assertEqual(assessment.estimated_p95, 40)

class EvidenceDryPilotFlowTests(unittest.TestCase):
    class _Context:
        def __init__(self) -> None:
            self.outputs = []

        def write_json(self, payload, output=None) -> None:
            import json
            from pathlib import Path
            self.outputs.append(payload)
            if output:
                target = Path(output)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def test_calibrate_gate_call_and_compare_dry_pilot(self) -> None:
        import argparse
        import json
        import tempfile
        from pathlib import Path

        from wqb_cli.evidence.plugin import EvidencePlugin

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_root = root / "store"
            plugin = EvidencePlugin()
            parser = argparse.ArgumentParser()
            sub = parser.add_subparsers(dest="command", required=True)
            plugin.register(sub).set_defaults(_wqb_plugin=plugin)
            context = self._Context()

            cost_key = "stock_data.get_stock_fundamentals:single"
            for before, after in ((1000, 990), (990, 978), (978, 967)):
                args = parser.parse_args([
                    "evidence", "--store-root", str(store_root),
                    "cost", "add", cost_key,
                    "--before", str(before), "--after", str(after), "--success",
                ])
                self.assertEqual(plugin.handle(args, context), 0)

            args = parser.parse_args([
                "evidence", "--store-root", str(store_root),
                "balance", "add", "wind", "--available-points", "967",
                "--source", "alice_market_account",
            ])
            self.assertEqual(plugin.handle(args, context), 0)

            freeze_path, _ = _make_research_freeze(root, run_id="dry-pilot")
            plan_path = root / "plan.json"
            plan_path.write_text(json.dumps({
                "run_id": "dry-pilot",
                "freeze_manifest": str(freeze_path),
                "available_points": 967,
                "checks": [{
                    "check_id": "quality-a",
                    "mechanism_id": "quality-1",
                    "node": "G",
                    "purpose": "research",
                    "server_type": "stock_data",
                    "tool_name": "get_stock_fundamentals",
                    "cost_profile_key": cost_key,
                    "params": {"question": "600519.SH 2024 ROE"},
                    "entity_ids": {"windcode": "600519.SH"},
                    "supports": ["mechanism:quality-1"],
                }],
            }), encoding="utf-8")
            args = parser.parse_args([
                "evidence", "--store-root", str(store_root),
                "wind", "plan-check", "--input", str(plan_path),
            ])
            self.assertEqual(plugin.handle(args, context), 0)
            self.assertTrue(context.outputs[-1]["ok"])

            skill = root / "wind-mcp-skill"
            (skill / "scripts").mkdir(parents=True)
            (skill / "references").mkdir()
            (skill / "SKILL.md").write_text("# fake skill\n", encoding="utf-8")
            (skill / "scripts" / "tool-manifest.json").write_text(
                '{"stock_data":["get_stock_fundamentals"]}', encoding="utf-8"
            )
            (skill / "references" / "stock.md").write_text("# stock\n", encoding="utf-8")
            (skill / "scripts" / "cli.mjs").write_text(
                """import fs from 'node:fs';
const [verb, serverType, toolName, paramsArg] = process.argv.slice(2);
const params = JSON.parse(fs.readFileSync(paramsArg.slice(1), 'utf8'));
const body = {company:'贵州茅台', roe:31.2, meta:{source:'WindTest',unit:'%'}};
process.stdout.write(JSON.stringify({content:[{text:JSON.stringify(body)}],cli_meta:{schema_version:'1.0',server_type:serverType,tool_name:toolName,completeness:'not_asserted',warnings:[]}}));
""",
                encoding="utf-8",
            )
            args = parser.parse_args([
                "evidence", "--store-root", str(store_root),
                "wind", "execute-plan", "--input", str(plan_path),
                "--skill-dir", str(skill),
            ])
            self.assertEqual(plugin.handle(args, context), 0)
            evidence_id = context.outputs[-1]["completed"][0]["evidence_id"]
            from wqb_cli.evidence import EvidenceStore
            evidence_payload = EvidenceStore(store_root).load_record("wind", evidence_id).to_dict()
            self.assertEqual(evidence_payload["provider"], "wind")

            baseline_path = root / "baseline.json"
            wind_path = root / "wind.json"
            baseline_path.write_text(json.dumps([{
                "mechanism_id": "quality-1",
                "direction_status": "uncertain",
                "falsification_conditions": ["ROE does not persist"],
                "reality_evidence_refs": [],
            }]), encoding="utf-8")
            wind_path.write_text(json.dumps([{
                "mechanism_id": "quality-1",
                "direction_status": "supported",
                "falsification_conditions": ["ROE does not persist", "cash conversion breaks"],
                "reality_evidence_refs": [evidence_payload["evidence_id"]],
            }]), encoding="utf-8")
            args = parser.parse_args([
                "evidence", "--store-root", str(store_root),
                "experiment", "compare",
                "--baseline-contracts", str(baseline_path),
                "--wind-contracts", str(wind_path),
            ])
            self.assertEqual(plugin.handle(args, context), 0)
            impact = context.outputs[-1]["impact"]
            self.assertEqual(impact["direction_changes"], [{"mechanism_id": "quality-1", "baseline": "uncertain", "wind": "supported"}])
            self.assertEqual(impact["falsification_strengthened"], ["quality-1"])
            self.assertEqual(impact["reality_evidence_mechanisms"], ["quality-1"])

class EvidenceExecutePlanTests(unittest.TestCase):
    class _Context:
        def __init__(self) -> None:
            self.outputs = []

        def write_json(self, payload, output=None) -> None:
            import json
            from pathlib import Path
            self.outputs.append(payload)
            if output:
                target = Path(output)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _skill(root, *, invalid_json=False):
        from pathlib import Path
        skill = Path(root) / "wind-mcp-skill"
        (skill / "scripts").mkdir(parents=True)
        (skill / "references").mkdir()
        (skill / "SKILL.md").write_text("# fake skill\n", encoding="utf-8")
        (skill / "scripts" / "tool-manifest.json").write_text(
            '{"stock_data":["get_stock_fundamentals"]}', encoding="utf-8"
        )
        (skill / "references" / "stock.md").write_text("# stock\n", encoding="utf-8")
        if invalid_json:
            body = """import fs from 'node:fs';
const counter = new URL('./counter.txt', import.meta.url);
let value = 0; try { value = Number(fs.readFileSync(counter, 'utf8')); } catch {}
fs.writeFileSync(counter, String(value + 1));
process.stdout.write('not-json');
"""
        else:
            body = """import fs from 'node:fs';
const [verb, serverType, toolName, paramsArg] = process.argv.slice(2);
const counter = new URL('./counter.txt', import.meta.url);
let value = 0; try { value = Number(fs.readFileSync(counter, 'utf8')); } catch {}
fs.writeFileSync(counter, String(value + 1));
const params = JSON.parse(fs.readFileSync(paramsArg.slice(1), 'utf8'));
const data = {question:params.question, roe:31.2, meta:{source:'WindTest',unit:'%'}};
process.stdout.write(JSON.stringify({content:[{text:JSON.stringify(data)}],cli_meta:{schema_version:'1.0',server_type:serverType,tool_name:toolName,completeness:'not_asserted',warnings:[]}}));
"""
        (skill / "scripts" / "cli.mjs").write_text(body, encoding="utf-8")
        return skill

    @staticmethod
    def _add_costs(plugin, parser, context, store_root, key):
        for before, after in ((1000, 990), (990, 980), (980, 970)):
            args = parser.parse_args([
                "evidence", "--store-root", str(store_root),
                "cost", "add", key,
                "--before", str(before), "--after", str(after), "--success",
            ])
            assert plugin.handle(args, context) == 0

    @staticmethod
    def _add_balance(plugin, parser, context, store_root, points=970):
        args = parser.parse_args([
            "evidence", "--store-root", str(store_root),
            "balance", "add", "wind", "--available-points", str(points),
            "--source", "alice_market_account",
        ])
        assert plugin.handle(args, context) == 0

    def test_execute_plan_is_resumable_and_does_not_replay_completed_checks(self) -> None:
        import argparse
        import json
        import tempfile
        from pathlib import Path
        from wqb_cli.evidence.plugin import EvidencePlugin

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_root = root / "store"
            skill = self._skill(root)
            plugin = EvidencePlugin()
            parser = argparse.ArgumentParser()
            sub = parser.add_subparsers(dest="command", required=True)
            plugin.register(sub).set_defaults(_wqb_plugin=plugin)
            context = self._Context()
            key = "stock_data.get_stock_fundamentals:single"
            self._add_costs(plugin, parser, context, store_root, key)
            self._add_balance(plugin, parser, context, store_root)

            freeze_path, _ = _make_research_freeze(root, run_id="run-resume")
            plan = root / "plan.json"
            plan.write_text(json.dumps({
                "run_id": "run-resume",
                "freeze_manifest": str(freeze_path),
                "available_points": 970,
                "checks": [
                    {
                        "check_id": "quality-a",
                        "mechanism_id": "quality-1",
                        "node": "G",
                        "purpose": "research",
                        "server_type": "stock_data",
                        "tool_name": "get_stock_fundamentals",
                        "cost_profile_key": key,
                        "params": {"question": "600519.SH ROE"},
                        "entity_ids": {"windcode": "600519.SH"},
                    },
                    {
                        "check_id": "quality-b",
                        "mechanism_id": "quality-1",
                        "node": "G",
                        "purpose": "research",
                        "server_type": "stock_data",
                        "tool_name": "get_stock_fundamentals",
                        "cost_profile_key": key,
                        "params": {"question": "000858.SZ ROE"},
                        "entity_ids": {"windcode": "000858.SZ"},
                    },
                ],
            }), encoding="utf-8")

            argv = [
                "evidence", "--store-root", str(store_root),
                "wind", "execute-plan", "--input", str(plan), "--skill-dir", str(skill),
            ]
            args = parser.parse_args(argv)
            self.assertEqual(plugin.handle(args, context), 0)
            self.assertEqual(context.outputs[-1]["status"], "completed")
            self.assertEqual(len(context.outputs[-1]["completed"]), 2)
            counter = skill / "scripts" / "counter.txt"
            self.assertEqual(counter.read_text(encoding="utf-8"), "2")

            args = parser.parse_args(argv)
            self.assertEqual(plugin.handle(args, context), 0)
            self.assertEqual(context.outputs[-1]["status"], "completed")
            self.assertEqual(context.outputs[-1]["skipped"], ["quality-a", "quality-b"])
            self.assertEqual(counter.read_text(encoding="utf-8"), "2")

            status_args = parser.parse_args([
                "evidence", "--store-root", str(store_root),
                "wind", "plan-status", "--input", str(plan),
            ])
            self.assertEqual(plugin.handle(status_args, context), 0)
            self.assertTrue(context.outputs[-1]["is_complete"])
            self.assertFalse(context.outputs[-1]["pending"])
            self.assertEqual(len(context.outputs[-1]["completed"]), 2)
            for item in context.outputs[-1]["completed"]:
                self.assertTrue(Path(item["stored_path"]).is_file())

    def test_execute_plan_outcome_unknown_stops_and_never_blind_replays(self) -> None:
        import argparse
        import json
        import tempfile
        from pathlib import Path
        from wqb_cli.evidence.plugin import EvidencePlugin

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_root = root / "store"
            skill = self._skill(root, invalid_json=True)
            plugin = EvidencePlugin()
            parser = argparse.ArgumentParser()
            sub = parser.add_subparsers(dest="command", required=True)
            plugin.register(sub).set_defaults(_wqb_plugin=plugin)
            context = self._Context()
            key = "stock_data.get_stock_fundamentals:single"
            self._add_costs(plugin, parser, context, store_root, key)
            self._add_balance(plugin, parser, context, store_root)

            freeze_path, _ = _make_research_freeze(root, run_id="run-unknown")
            plan = root / "plan.json"
            plan.write_text(json.dumps({
                "run_id": "run-unknown",
                "freeze_manifest": str(freeze_path),
                "available_points": 970,
                "checks": [{
                    "check_id": "quality-a",
                    "mechanism_id": "quality-1",
                    "node": "G",
                    "purpose": "research",
                    "server_type": "stock_data",
                    "tool_name": "get_stock_fundamentals",
                    "cost_profile_key": key,
                    "params": {"question": "600519.SH ROE"},
                }],
            }), encoding="utf-8")
            argv = [
                "evidence", "--store-root", str(store_root),
                "wind", "execute-plan", "--input", str(plan), "--skill-dir", str(skill),
            ]
            args = parser.parse_args(argv)
            self.assertEqual(plugin.handle(args, context), 2)
            self.assertEqual(context.outputs[-1]["status"], "outcome_unknown")
            counter = skill / "scripts" / "counter.txt"
            self.assertEqual(counter.read_text(encoding="utf-8"), "1")

            args = parser.parse_args(argv)
            self.assertEqual(plugin.handle(args, context), 2)
            self.assertEqual(context.outputs[-1]["reason"], "outcome_unknown_requires_authoritative_readback")
            self.assertEqual(counter.read_text(encoding="utf-8"), "1")


            status_args = parser.parse_args([
                "evidence", "--store-root", str(store_root),
                "wind", "plan-status", "--input", str(plan),
            ])
            self.assertEqual(plugin.handle(status_args, context), 2)
            self.assertEqual(context.outputs[-1]["blocked"][0]["state"], "outcome_unknown")
            self.assertFalse(context.outputs[-1]["can_resume"])

class EvidenceBalanceObservationTests(unittest.TestCase):
    class _Context:
        def __init__(self) -> None:
            self.last = None
        def write_json(self, payload, output=None) -> None:
            self.last = payload

    def test_plan_check_can_use_fresh_recorded_balance(self) -> None:
        import argparse
        import json
        import tempfile
        from pathlib import Path
        from wqb_cli.evidence.plugin import EvidencePlugin

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugin = EvidencePlugin()
            parser = argparse.ArgumentParser()
            sub = parser.add_subparsers(dest="command", required=True)
            plugin.register(sub).set_defaults(_wqb_plugin=plugin)
            context = self._Context()
            store_root = root / "store"
            key = "stock_data.get_stock_fundamentals:single"
            for before, after in ((1000, 990), (990, 980), (980, 970)):
                args = parser.parse_args([
                    "evidence", "--store-root", str(store_root),
                    "cost", "add", key, "--before", str(before), "--after", str(after), "--success",
                ])
                self.assertEqual(plugin.handle(args, context), 0)
            args = parser.parse_args([
                "evidence", "--store-root", str(store_root),
                "balance", "add", "wind", "--available-points", "970",
                "--source", "alice_market_account",
            ])
            self.assertEqual(plugin.handle(args, context), 0)

            freeze_path, _ = _make_research_freeze(root, run_id="balance-fresh")
            plan = root / "plan.json"
            plan.write_text(json.dumps({
                "run_id": "balance-fresh",
                "freeze_manifest": str(freeze_path),
                "checks": [{
                    "mechanism_id": "quality-1",
                    "node": "G",
                    "purpose": "research",
                    "server_type": "stock_data",
                    "tool_name": "get_stock_fundamentals",
                    "cost_profile_key": key,
                }]
            }), encoding="utf-8")
            args = parser.parse_args([
                "evidence", "--store-root", str(store_root),
                "wind", "plan-check", "--input", str(plan),
            ])
            self.assertEqual(plugin.handle(args, context), 0)
            self.assertEqual(context.last["balance"]["source"], "alice_market_account")
            self.assertEqual(context.last["balance"]["available_points"], 970)

    def test_execute_plan_ignores_inline_balance_and_requires_recorded_balance(self) -> None:
        import argparse
        import json
        import tempfile
        from wqb_cli.evidence.plugin import EvidencePlugin

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugin = EvidencePlugin()
            parser = argparse.ArgumentParser()
            sub = parser.add_subparsers(dest="command", required=True)
            plugin.register(sub).set_defaults(_wqb_plugin=plugin)
            context = self._Context()
            store_root = root / "store"
            key = "stock_data.get_stock_fundamentals:single"
            for before, after in ((1000, 990), (990, 980), (980, 970)):
                args = parser.parse_args([
                    "evidence", "--store-root", str(store_root),
                    "cost", "add", key, "--before", str(before), "--after", str(after), "--success",
                ])
                self.assertEqual(plugin.handle(args, context), 0)
            freeze_path, _ = _make_research_freeze(root, run_id="inline-only")
            plan = root / "plan.json"
            plan.write_text(json.dumps({
                "run_id": "inline-only",
                "freeze_manifest": str(freeze_path),
                "available_points": 970,
                "checks": [{
                    "mechanism_id": "quality-1",
                    "node": "G",
                    "purpose": "research",
                    "server_type": "stock_data",
                    "tool_name": "get_stock_fundamentals",
                    "cost_profile_key": key,
                    "params": {"question": "x"},
                }],
            }), encoding="utf-8")
            args = parser.parse_args([
                "evidence", "--store-root", str(store_root),
                "wind", "execute-plan", "--input", str(plan),
            ])
            self.assertEqual(plugin.handle(args, context), 1)
            self.assertEqual(context.last["reason"], "missing_balance_observation")

    def test_stale_recorded_balance_is_rejected(self) -> None:
        import argparse
        import json
        import tempfile
        from pathlib import Path
        from wqb_cli.evidence.plugin import EvidencePlugin

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugin = EvidencePlugin()
            parser = argparse.ArgumentParser()
            sub = parser.add_subparsers(dest="command", required=True)
            plugin.register(sub).set_defaults(_wqb_plugin=plugin)
            context = self._Context()
            store_root = root / "store"
            key = "stock_data.get_stock_fundamentals:single"
            for before, after in ((1000, 990), (990, 980), (980, 970)):
                args = parser.parse_args([
                    "evidence", "--store-root", str(store_root),
                    "cost", "add", key, "--before", str(before), "--after", str(after), "--success",
                ])
                self.assertEqual(plugin.handle(args, context), 0)
            args = parser.parse_args([
                "evidence", "--store-root", str(store_root),
                "balance", "add", "wind", "--available-points", "970",
                "--observed-at", "2000-01-01T00:00:00Z",
            ])
            self.assertEqual(plugin.handle(args, context), 0)
            freeze_path, _ = _make_research_freeze(root, run_id="balance-stale")
            plan = root / "plan.json"
            plan.write_text(json.dumps({
                "run_id": "balance-stale",
                "freeze_manifest": str(freeze_path),
                "balance_max_age_seconds": 60,
                "checks": [{
                    "mechanism_id": "quality-1",
                    "node": "G",
                    "purpose": "research",
                    "server_type": "stock_data",
                    "tool_name": "get_stock_fundamentals",
                    "cost_profile_key": key,
                }]
            }), encoding="utf-8")
            args = parser.parse_args([
                "evidence", "--store-root", str(store_root),
                "wind", "plan-check", "--input", str(plan),
            ])
            self.assertEqual(plugin.handle(args, context), 1)
            self.assertEqual(context.last["reason"], "stale_balance_observation")

class WindPlanResumeBudgetTests(unittest.TestCase):
    def test_resume_budgets_only_pending_checks(self) -> None:
        import tempfile
        from pathlib import Path
        from wqb_cli.evidence import CostProfile, EvidenceStore, build_evidence_record
        from wqb_cli.evidence.execution import ExecutableRealityCheck, execute_wind_plan, plan_identity
        from wqb_cli.evidence.providers.wind import WindRuntime, wind_contract_fingerprint

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "wind-mcp-skill"
            (skill / "scripts").mkdir(parents=True)
            (skill / "references").mkdir()
            (skill / "SKILL.md").write_text("# fake\n", encoding="utf-8")
            (skill / "scripts" / "tool-manifest.json").write_text(
                '{"stock_data":["get_stock_fundamentals"]}', encoding="utf-8"
            )
            (skill / "references" / "stock.md").write_text("# stock\n", encoding="utf-8")
            (skill / "scripts" / "cli.mjs").write_text(
                """import fs from 'node:fs';
const [verb, serverType, toolName, paramsArg] = process.argv.slice(2);
const params = JSON.parse(fs.readFileSync(paramsArg.slice(1), 'utf8'));
const counter = new URL('./counter.txt', import.meta.url);
let n = 0; try { n = Number(fs.readFileSync(counter, 'utf8')); } catch {}
fs.writeFileSync(counter, String(n + 1));
const body={q:params.question,meta:{source:'WindTest',unit:'%'}};
process.stdout.write(JSON.stringify({content:[{text:JSON.stringify(body)}],cli_meta:{schema_version:'1.0',server_type:serverType,tool_name:toolName,completeness:'not_asserted',warnings:[]}}));
""",
                encoding="utf-8",
            )
            key = "stock_data.get_stock_fundamentals:single"
            checks = [
                ExecutableRealityCheck(
                    check_id="a", mechanism_id="m1", node="G", purpose="research",
                    server_type="stock_data", tool_name="get_stock_fundamentals",
                    cost_profile_key=key, params={"question":"a"},
                ),
                ExecutableRealityCheck(
                    check_id="b", mechanism_id="m1", node="G", purpose="research",
                    server_type="stock_data", tool_name="get_stock_fundamentals",
                    cost_profile_key=key, params={"question":"b"},
                ),
            ]
            store = EvidenceStore(root / "store")
            _, freeze = _make_research_freeze(
                root, run_id="resume-budget", mechanism_id="m1"
            )
            pid = plan_identity(
                checks, freeze_manifest_sha256=freeze.manifest_sha256
            )
            store.save_run_plan(
                run_id="resume-budget",
                plan_id=pid,
                payload={
                    "run_id": "resume-budget",
                    "plan_id": pid,
                    "checks": [c.identity_payload() for c in checks],
                    "freeze_manifest_sha256": freeze.manifest_sha256,
                    "freeze_manifest_path": str(freeze.manifest_path),
                },
            )
            version = wind_contract_fingerprint(skill)
            record = build_evidence_record(
                provider="wind", query_type="stock_data.get_stock_fundamentals",
                request={"question":"a"}, raw_response={"content":[]},
                provider_contract_version=version,
            )
            store.save_record(record)
            store.append_run_event(
                run_id="resume-budget", plan_id=pid,
                event={"event":"completed","check_id":"a","evidence_id":record.evidence_id},
            )
            profile = CostProfile(query_type=key, sample_count=3, p50=10, p95=10, maximum=10)
            report = execute_wind_plan(
                store=store, run_id="resume-budget", checks=checks,
                available_points=20, profiles={key: profile}, runtime=WindRuntime(skill_dir=skill),
                research_freeze=freeze,
            )
            self.assertTrue(report.ok)
            self.assertEqual(report.assessment.call_count, 1)
            self.assertEqual(report.assessment.estimated_p95, 10)
            self.assertEqual(report.skipped, ("a",))
            self.assertEqual((skill / "scripts" / "counter.txt").read_text(encoding="utf-8"), "1")

class AnalyticsFallbackGateTests(unittest.TestCase):
    def test_analytics_data_requires_explicit_expensive_fallback_reason(self) -> None:
        from wqb_cli.evidence import CostProfile, RealityCheckSpec, RealityPlanError, assess_wind_reality_plan
        key = "analytics_data.get_financial_data:wide"
        profile = CostProfile(query_type=key, sample_count=3, p50=100, p95=120, maximum=120)
        denied = RealityCheckSpec(
            mechanism_id="m1", node="G", purpose="research",
            server_type="analytics_data", tool_name="get_financial_data",
            cost_profile_key=key,
        )
        with self.assertRaisesRegex(RealityPlanError, "analytics_data requires"):
            assess_wind_reality_plan([denied], profiles={key: profile}, available_points=1000)

        allowed = RealityCheckSpec(
            mechanism_id="m1", node="G", purpose="research",
            server_type="analytics_data", tool_name="get_financial_data",
            cost_profile_key=key, allow_expensive_fallback=True,
            fallback_reason="stock_data specialist cannot express the required cross-asset aggregate",
        )
        assessment = assess_wind_reality_plan([allowed], profiles={key: profile}, available_points=1000)
        self.assertTrue(assessment.budget.allowed)

class CostProfileFreshnessTests(unittest.TestCase):
    class _Context:
        def __init__(self) -> None:
            self.last = None
        def write_json(self, payload, output=None) -> None:
            self.last = payload

    def test_plan_rejects_historical_only_cost_profile_as_stale(self) -> None:
        import argparse
        import json
        import tempfile
        from pathlib import Path
        from wqb_cli.evidence.plugin import EvidencePlugin

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_root = root / "store"
            plugin = EvidencePlugin()
            parser = argparse.ArgumentParser()
            sub = parser.add_subparsers(dest="command", required=True)
            plugin.register(sub).set_defaults(_wqb_plugin=plugin)
            context = self._Context()
            key = "stock_data.get_stock_fundamentals:single"
            for before, after in ((1000, 990), (990, 980), (980, 970)):
                args = parser.parse_args([
                    "evidence", "--store-root", str(store_root),
                    "cost", "add", key,
                    "--before", str(before), "--after", str(after), "--success",
                    "--timestamp", "2000-01-01T00:00:00Z",
                ])
                self.assertEqual(plugin.handle(args, context), 0)
            freeze_path, _ = _make_research_freeze(root, run_id="stale-cost")
            plan = root / "plan.json"
            plan.write_text(json.dumps({
                "run_id": "stale-cost",
                "freeze_manifest": str(freeze_path),
                "available_points": 1000,
                "checks": [{
                    "mechanism_id": "quality-1",
                    "node": "G",
                    "purpose": "research",
                    "server_type": "stock_data",
                    "tool_name": "get_stock_fundamentals",
                    "cost_profile_key": key,
                }]
            }), encoding="utf-8")
            args = parser.parse_args([
                "evidence", "--store-root", str(store_root),
                "wind", "plan-check", "--input", str(plan),
            ])
            self.assertEqual(plugin.handle(args, context), 1)
            self.assertEqual(context.last["reason"], "stale_cost_profile")
            self.assertEqual(context.last["query_type"], key)

class PilotOutcomeComparisonTests(unittest.TestCase):
    def test_pilot_outcomes_compare_information_efficiency_metrics(self) -> None:
        from wqb_cli.evidence import compare_pilot_outcomes
        report = compare_pilot_outcomes(
            {
                "simulation_attempts": 20,
                "valid_simulations": 14,
                "reached_l": 3,
                "failure_count": 8,
                "wall_clock_seconds": 1000,
                "wind_points_consumed": 0,
            },
            {
                "simulation_attempts": 12,
                "valid_simulations": 10,
                "reached_l": 4,
                "failure_count": 3,
                "wall_clock_seconds": 760,
                "wind_points_consumed": 86,
            },
        ).to_dict()
        self.assertEqual(report["delta"]["simulation_attempts"], -8)
        self.assertEqual(report["delta"]["reached_l"], 1)
        self.assertLess(report["delta"]["failure_density"], 0)
        self.assertEqual(report["delta"]["wind_points_consumed"], 86)



class DecimalPointAccountingTests(unittest.TestCase):
    def test_decimal_cost_profile_and_budget(self) -> None:
        observations = [
            CostObservation(
                "stock_data.get_stock_fundamentals:single",
                1000.0,
                999.6,
                True,
                "t1",
            ),
            CostObservation(
                "stock_data.get_stock_fundamentals:single",
                999.6,
                999.2,
                True,
                "t2",
            ),
            CostObservation(
                "stock_data.get_stock_fundamentals:single",
                999.2,
                998.8,
                True,
                "t3",
            ),
        ]

        profile = CostProfile.from_observations(
            "stock_data.get_stock_fundamentals:single",
            observations,
        )

        self.assertEqual(profile.sample_count, 3)
        self.assertAlmostEqual(profile.p50, 0.4)
        self.assertAlmostEqual(profile.p95, 0.4)
        self.assertAlmostEqual(profile.maximum, 0.4)

        decision = BudgetPolicy().decide(
            available_points=999.6,
            estimated_p95=0.4,
            purpose="research",
        )

        self.assertAlmostEqual(
            decision.allocation_points,
            599.76,
        )
        self.assertAlmostEqual(
            decision.headroom,
            599.36,
        )
        self.assertTrue(decision.allowed)

    def test_decimal_balance_cost_cli_and_store_roundtrip(self) -> None:
        import argparse
        import tempfile
        from pathlib import Path

        from wqb_cli.evidence import (
            BalanceObservation,
            EvidenceStore,
        )
        from wqb_cli.evidence.plugin import EvidencePlugin

        plugin = EvidencePlugin()
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(
            dest="command",
            required=True,
        )
        plugin.register(sub).set_defaults(
            _wqb_plugin=plugin
        )

        balance_args = parser.parse_args([
            "evidence",
            "balance",
            "add",
            "wind",
            "--available-points",
            "999.6",
        ])

        self.assertAlmostEqual(
            balance_args.available_points,
            999.6,
        )

        cost_args = parser.parse_args([
            "evidence",
            "cost",
            "add",
            "stock_data.get_stock_fundamentals:single",
            "--before",
            "999.6",
            "--after",
            "999.2",
            "--success",
        ])

        self.assertAlmostEqual(cost_args.before, 999.6)
        self.assertAlmostEqual(cost_args.after, 999.2)

        with tempfile.TemporaryDirectory() as tmp:
            store = EvidenceStore(Path(tmp))

            store.append_balance(
                BalanceObservation(
                    provider="wind",
                    available_points=999.6,
                    observed_at="2026-09-08T00:00:00Z",
                    source="alice_market_account",
                )
            )

            store.append_cost(
                "wind",
                CostObservation(
                    "stock_data.get_stock_fundamentals:single",
                    999.6,
                    999.2,
                    True,
                    "2026-09-08T00:00:01Z",
                ),
            )

            balance = store.latest_balance("wind")
            self.assertIsNotNone(balance)
            self.assertAlmostEqual(
                balance.available_points,
                999.6,
            )

            costs = store.load_costs("wind")
            self.assertEqual(len(costs), 1)
            self.assertAlmostEqual(
                costs[0].points_before,
                999.6,
            )
            self.assertAlmostEqual(
                costs[0].points_after,
                999.2,
            )
            self.assertAlmostEqual(costs[0].cost, 0.4)

        with self.assertRaisesRegex(
            ValueError,
            "finite",
        ):
            CostObservation(
                "x",
                float("nan"),
                0.0,
                True,
                "t",
            )



class FractionalPilotMetricsTests(unittest.TestCase):
    def test_pilot_metrics_preserve_fractional_wind_points(self) -> None:
        from wqb_cli.evidence.experiment import (
            PilotArmMetrics,
            compare_pilot_outcomes,
        )

        metric = PilotArmMetrics.from_mapping({
            "simulation_attempts": 1,
            "valid_simulations": 1,
            "reached_l": 0,
            "failure_count": 0,
            "wall_clock_seconds": 1.0,
            "wind_points_consumed": 0.4,
        })

        self.assertAlmostEqual(
            metric.wind_points_consumed,
            0.4,
        )

        report = compare_pilot_outcomes(
            {
                "simulation_attempts": 1,
                "valid_simulations": 1,
                "reached_l": 0,
                "failure_count": 0,
                "wall_clock_seconds": 1.0,
                "wind_points_consumed": 0.0,
            },
            {
                "simulation_attempts": 1,
                "valid_simulations": 1,
                "reached_l": 0,
                "failure_count": 0,
                "wall_clock_seconds": 1.0,
                "wind_points_consumed": 0.4,
            },
        ).to_dict()

        self.assertAlmostEqual(
            report["delta"]["wind_points_consumed"],
            0.4,
        )

        with self.assertRaisesRegex(ValueError, "finite"):
            PilotArmMetrics(
                simulation_attempts=1,
                valid_simulations=1,
                reached_l=0,
                failure_count=0,
                wall_clock_seconds=1.0,
                wind_points_consumed=float("nan"),
            )
