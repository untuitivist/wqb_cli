from __future__ import annotations

import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from wqb_cli.agent.artifacts import redact_json
from wqb_cli.agent.nodes.evaluation import (
    EvaluationError,
    EvaluationNodes,
    build_simulation_batches,
    classify_final_checks,
    classify_hard_metrics,
    extract_alpha_ids,
    select_passing_candidate,
    template_density_report,
    validate_diagnosis,
)
from wqb_cli.agent.store import AgentStore
from wqb_cli.agent.types import Budget, RunConfig, ScopeMode, WorkflowNode


FIXTURES = Path(__file__).parent / "fixtures" / "agent"


def fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeRunner:
    def __init__(self, responses: dict[tuple[str, ...], dict[str, object]]) -> None:
        self.responses = responses
        self.calls: list[tuple[WorkflowNode, tuple[str, ...], str]] = []
        self.policy = SimpleNamespace(budget=Budget(candidates_per_round=8))

    def run(self, run_id, node, argv, artifact_name):
        self.calls.append((node, argv, artifact_name))
        key = argv if argv in self.responses else argv[:2]
        payload = self.responses[key]
        return SimpleNamespace(payload=payload, artifact=SimpleNamespace(id=len(self.calls)))


class FakeStore:
    def __init__(self) -> None:
        self.simulations: dict[str, dict[str, object]] = {}
        self.candidates: dict[str, object] = {}
        self.diagnoses: list[tuple[str, WorkflowNode, dict[str, object]]] = []

    def record_simulation(self, run_id, simulation_id, status, candidate_id=None, alpha_id=None, result_artifact_id=None):
        if simulation_id in self.simulations:
            raise AssertionError("duplicate simulation record")
        self.simulations[simulation_id] = {
            "status": status,
            "candidate_id": candidate_id,
            "alpha_id": alpha_id,
            "result_artifact_id": result_artifact_id,
        }

    def update_simulation(self, run_id, simulation_id, status, alpha_id=None, result_artifact_id=None):
        simulation = self.simulations[simulation_id]
        simulation.update(status=status)
        if alpha_id is not None:
            simulation["alpha_id"] = alpha_id
        if result_artifact_id is not None:
            if simulation["result_artifact_id"] not in {None, result_artifact_id}:
                raise AssertionError("result artifact changed")
            simulation["result_artifact_id"] = result_artifact_id

    def get_simulation(self, run_id, simulation_id):
        value = self.simulations[simulation_id]
        return SimpleNamespace(simulation_id=simulation_id, **value)

    def get_candidate_by_fingerprint(self, run_id, fingerprint):
        return self.candidates[fingerprint]

    def record_diagnosis(self, run_id, failure_class, next_node, diagnosis, node_attempt_id=None):
        self.diagnoses.append((failure_class, next_node, diagnosis))


class FakeArtifacts:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.values: dict[str, object] = {}

    def write_json(self, run_id, node, name, value):
        self.values[name] = value
        path = self.root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return SimpleNamespace(id=len(self.values), path=str(path))

    def stage_input(self, run_id, node, content, sha256, *, require_utf8_text=False):
        assert hashlib.sha256(content).hexdigest() == sha256
        path = self.root / "staged_simulation_input.json"
        path.write_bytes(content)
        return path


class FakeRouter:
    def __init__(self, values: list[dict[str, object]]) -> None:
        self.values = values
        self.requests = []

    def invoke(self, request):
        self.requests.append(request)
        return SimpleNamespace(value=self.values.pop(0))


def envelope(body: object) -> dict[str, object]:
    return {"ok": True, "response": {"status_code": 200, "body": body}}


def passing(**changes: object) -> dict[str, object]:
    value = fixture("alpha_pass.json")
    value.update(changes)
    return value


@pytest.mark.parametrize(
    ("field", "boundary"),
    [("sharpe", 1.58), ("fitness", 1.0), ("turnover", 0.01), ("turnover", 0.70), ("margin", 0.001)],
)
def test_hard_metric_thresholds_are_strict(field: str, boundary: float) -> None:
    assert not classify_hard_metrics(passing(**{field: boundary})).passed


def test_hard_metrics_reject_fail_check_and_missing_required_visualization() -> None:
    assert not classify_hard_metrics(passing(checks=[{"result": "FAIL"}])).passed
    nested = passing(
        checks={"is": {"checks": [{"name": "LOW_SHARPE", "result": "FAIL"}]}}
    )
    assert "check:LOW_SHARPE" in classify_hard_metrics(nested).failures
    result = classify_hard_metrics(passing(visualizations={}), required_visualizations=("pnl",))
    assert not result.passed
    assert "visualization:pnl" in result.failures


def test_extract_alpha_ids_uses_only_completed_child_response_bodies() -> None:
    payload = fixture("simulation_complete.json")
    payload["children"].append({
        "simulation_id": "SIM-CHILD-2",
        "result": envelope({"status": "RUNNING", "alpha": "NOT-DONE"}),
    })
    assert extract_alpha_ids(payload) == ("ALPHA123",)
    assert "SIM-CHILD-1" not in extract_alpha_ids(payload)


def test_select_passing_candidate_uses_complete_deterministic_ranking() -> None:
    candidates = [
        passing(id="A1", sharpe=1.9, fitness=1.2, margin=0.0013, turnover=0.3),
        passing(id="A2", sharpe=1.9, fitness=1.2, margin=0.0013, turnover=0.2),
    ]
    assert select_passing_candidate(candidates)["id"] == "A2"


def test_template_density_groups_research_profiles() -> None:
    candidates = [
        passing(
            id="A1",
            template_id="binary:ts_corr",
            template_type="binary",
            strategy_family="relational",
            pnl=4_000_000,
            longCount=60,
            shortCount=60,
        ),
        passing(
            id="A2",
            template_id="binary:ts_corr",
            template_type="binary",
            strategy_family="relational",
            sharpe=0.2,
            fitness=0.1,
            pnl=100,
            longCount=60,
            shortCount=60,
        ),
    ]
    report = template_density_report(candidates)["binary:ts_corr"]
    assert report["tested"] == 2
    assert report["promising"] == 1
    assert report["factor_density"] == 0.5


def test_glb_batches_are_capped_at_four_and_lock_regular_fastexpr() -> None:
    candidates = [{"expression": f"rank(field_{index})"} for index in range(9)]
    batches = build_simulation_batches(
        candidates,
        {"region": "GLB", "delay": 1, "universe": "TOP3000", "neutralization": "INDUSTRY"},
        candidates_per_round=8,
    )
    assert [len(batch) for batch in batches] == [4, 4, 1]
    assert all(item["type"] == "REGULAR" and item["settings"]["instrumentType"] == "EQUITY" for batch in batches for item in batch)
    flattened = [item for batch in batches for item in batch]
    assert [item["regular"] for item in flattened] == [candidate["expression"] for candidate in candidates]
    assert all(
        item["settings"].items() >= {
            "decay": 0,
            "nanHandling": "ON",
            "pasteurization": "ON",
            "truncation": 0.08,
            "unitHandling": "VERIFY",
            "visualization": False,
        }.items()
        for item in flattened
    )


def test_j_stages_single_simulation_as_object_and_multiple_as_array(tmp_path: Path) -> None:
    nodes = EvaluationNodes(
        runner=FakeRunner({}),
        router=FakeRouter([]),
        store=FakeStore(),
        artifacts=FakeArtifacts(tmp_path),
    )
    first = {"type": "REGULAR", "regular": "ts_delta(vwap,22)"}
    second = {"type": "REGULAR", "regular": "ts_delta(vwap,63)"}

    single = nodes._stage_simulation_input("run1", [first])
    assert json.loads(single.read_text(encoding="utf-8")) == first
    multiple = nodes._stage_simulation_input("run1", [first, second])
    assert json.loads(multiple.read_text(encoding="utf-8")) == [first, second]


def test_j_resume_with_recorded_simulation_id_does_not_create(tmp_path: Path) -> None:
    runner = FakeRunner({
        ("sim", "get", "SIM-PARENT-1", "--max-wait-seconds", "900"): fixture("simulation_complete.json"),
        ("alpha", "get", "ALPHA123"): envelope(fixture("alpha_pass.json")),
        ("alpha", "check", "ALPHA123", "--max-wait-seconds", "900"): envelope({"checks": [{"result": "PASS"}]}),
        ("alpha", "recordsets", "ALPHA123", "--max-wait-seconds", "900"): envelope({"results": []}),
    })
    store = FakeStore()
    store.simulations["SIM-PARENT-1"] = {
        "status": "TIMED_OUT",
        "alpha_id": None,
        "result_artifact_id": None,
    }
    nodes = EvaluationNodes(runner=runner, router=FakeRouter([]), store=store, artifacts=FakeArtifacts(tmp_path))
    result = nodes.run_j("run1", {}, [], resume_simulation_ids=("SIM-PARENT-1",))
    assert result.simulation_ids == ("SIM-PARENT-1", "SIM-CHILD-1")
    assert not any(argv[:2] == ("sim", "create") for _, argv, _ in runner.calls)
    assert result.alpha_results[0]["alpha_id"] == "ALPHA123"


def test_j_recovers_parent_child_ids_before_collecting_alphas(tmp_path: Path) -> None:
    first_expression = "ts_delta(vwap,22)"
    second_expression = "ts_delta(vwap,63)"
    first_alpha = {
        **fixture("alpha_pass.json"),
        "id": "ALPHA1",
        "regular": {"code": first_expression},
    }
    second_alpha = {
        **fixture("alpha_pass.json"),
        "id": "ALPHA2",
        "regular": {"code": second_expression},
    }
    runner = FakeRunner(
        {
            ("sim", "create"): envelope(
                {"status": "COMPLETE", "children": ["CHILD1", "CHILD2"]}
            ),
            ("sim", "get", "CHILD1", "--max-wait-seconds", "900"): envelope(
                {
                    "id": "CHILD1",
                    "parent": "PARENT1",
                    "status": "COMPLETE",
                    "alpha": "ALPHA1",
                }
            ),
            ("sim", "get", "CHILD2", "--max-wait-seconds", "900"): envelope(
                {
                    "id": "CHILD2",
                    "parent": "PARENT1",
                    "status": "COMPLETE",
                    "alpha": "ALPHA2",
                }
            ),
            ("alpha", "get", "ALPHA1"): envelope(first_alpha),
            ("alpha", "check", "ALPHA1", "--max-wait-seconds", "900"): envelope(
                {"checks": [{"result": "PASS"}]}
            ),
            ("alpha", "recordsets", "ALPHA1", "--max-wait-seconds", "900"): envelope(
                {"results": []}
            ),
            ("alpha", "get", "ALPHA2"): envelope(second_alpha),
            ("alpha", "check", "ALPHA2", "--max-wait-seconds", "900"): envelope(
                {"checks": [{"result": "PASS"}]}
            ),
            ("alpha", "recordsets", "ALPHA2", "--max-wait-seconds", "900"): envelope(
                {"results": []}
            ),
        }
    )
    store = FakeStore()
    store.candidates["fp1"] = SimpleNamespace(id=11)
    store.candidates["fp2"] = SimpleNamespace(id=12)
    candidates = [
        {"fingerprint": "fp1", "candidate": {"expression": first_expression}},
        {"fingerprint": "fp2", "candidate": {"expression": second_expression}},
    ]
    nodes = EvaluationNodes(
        runner=runner,
        router=FakeRouter([]),
        store=store,
        artifacts=FakeArtifacts(tmp_path),
    )

    result = nodes.run_j(
        "run1",
        {
            "region": "USA",
            "delay": 1,
            "universe": "TOP3000",
            "neutralization": "INDUSTRY",
        },
        candidates,
        idea_id="p2:m1",
        create_candidates=candidates,
    )

    assert result.simulation_ids == ("CHILD1", "CHILD2")
    assert [item["alpha_id"] for item in result.alpha_results] == ["ALPHA1", "ALPHA2"]
    assert store.simulations["CHILD1"]["candidate_id"] == 11
    assert store.simulations["CHILD2"]["candidate_id"] == 12
    assert store.simulations["CHILD1"]["alpha_id"] == "ALPHA1"
    assert store.simulations["CHILD2"]["alpha_id"] == "ALPHA2"
    assert not result.platform_failures


def test_j_resume_keeps_first_result_artifact_on_repeated_poll(tmp_path: Path) -> None:
    runner = FakeRunner({
        ("sim", "get", "SIM-PARENT-1", "--max-wait-seconds", "900"): fixture("simulation_complete.json"),
        ("alpha", "get", "ALPHA123"): envelope(fixture("alpha_pass.json")),
        ("alpha", "check", "ALPHA123", "--max-wait-seconds", "900"): envelope({"checks": [{"result": "PASS"}]}),
        ("alpha", "recordsets", "ALPHA123", "--max-wait-seconds", "900"): envelope({"results": []}),
    })
    store = FakeStore()
    nodes = EvaluationNodes(runner=runner, router=FakeRouter([]), store=store, artifacts=FakeArtifacts(tmp_path))
    nodes.run_j("run1", {}, [], resume_simulation_ids=("SIM-PARENT-1",))
    first_artifact_id = store.simulations["SIM-PARENT-1"]["result_artifact_id"]
    nodes.run_j("run1", {}, [], resume_simulation_ids=("SIM-PARENT-1",))
    assert store.simulations["SIM-PARENT-1"]["result_artifact_id"] == first_artifact_id


def test_j_flattens_is_metrics_and_attaches_candidate_profile(tmp_path: Path) -> None:
    alpha = {
        "id": "ALPHA123",
        "is": {"sharpe": 1.7, "fitness": 1.1, "turnover": 0.2, "margin": 0.0012},
        "regular": {"code": "ts_delta(vwap,22)"},
    }
    runner = FakeRunner({
        ("sim", "get", "SIM-PARENT-1", "--max-wait-seconds", "900"): fixture("simulation_complete.json"),
        ("alpha", "get", "ALPHA123"): envelope(alpha),
        ("alpha", "check", "ALPHA123", "--max-wait-seconds", "900"): envelope({"checks": [{"result": "PASS"}]}),
        ("alpha", "recordsets", "ALPHA123", "--max-wait-seconds", "900"): envelope({"results": []}),
    })
    store = FakeStore()
    nodes = EvaluationNodes(runner=runner, router=FakeRouter([]), store=store, artifacts=FakeArtifacts(tmp_path))
    result = nodes.run_j(
        "run1",
        {},
        [{"candidate": {
            "expression": "ts_delta(vwap,22)",
            "template_id": "unary:ts_delta",
            "template_type": "unary",
            "strategy_family": "change",
        }}],
        resume_simulation_ids=("SIM-PARENT-1",),
    )
    evaluated = result.alpha_results[0]
    assert evaluated["sharpe"] == 1.7
    assert evaluated["template_id"] == "unary:ts_delta"


def test_j_preserves_platform_error_envelope(tmp_path: Path) -> None:
    failed = {"ok": False, "response": {"status_code": 400, "body": {"detail": "bad expression"}}}
    runner = FakeRunner({("sim", "create"): failed})
    nodes = EvaluationNodes(runner=runner, router=FakeRouter([]), store=FakeStore(), artifacts=FakeArtifacts(tmp_path))
    result = nodes.run_j(
        "run1",
        {"region": "USA", "delay": 1, "universe": "TOP3000", "neutralization": "INDUSTRY"},
        [{"fingerprint": "fp1", "expression": "rank(close)"}],
    )
    assert result.platform_failures == ({"stage": "simulation", "raw": failed},)


def test_j_expands_failed_parent_children_for_expression_diagnostics(
    tmp_path: Path,
) -> None:
    parent = {
        "ok": False,
        "response": {
            "status_code": 200,
            "body": {"status": "ERROR", "children": ["CHILD-ERROR"]},
        },
        "classification": {"ok": False, "status": "ERROR"},
    }
    child = {
        "ok": False,
        "response": {
            "status_code": 200,
            "body": {
                "id": "CHILD-ERROR",
                "parent": "PARENT-ERROR",
                "status": "ERROR",
                "message": "Operator ts_delta does not support event inputs.",
            },
        },
        "classification": {"ok": False, "status": "ERROR"},
    }
    runner = FakeRunner(
        {
            ("sim", "create"): parent,
            ("sim", "get", "CHILD-ERROR", "--max-wait-seconds", "900"): child,
        }
    )
    store = FakeStore()

    result = EvaluationNodes(
        runner=runner,
        router=FakeRouter([]),
        store=store,
        artifacts=FakeArtifacts(tmp_path),
    ).run_j(
        "run1",
        {"region": "USA", "delay": 1, "universe": "TOP3000", "neutralization": "INDUSTRY"},
        [{"fingerprint": "fp1", "expression": "ts_delta(event_signal,22)"}],
    )

    assert any(
        "does not support event inputs" in str(item)
        for item in result.platform_failures
    )
    assert store.simulations["CHILD-ERROR"]["status"] == "ERROR"


def test_j_links_child_simulation_to_candidate_for_actual_counting(tmp_path: Path) -> None:
    runner = FakeRunner({
        ("sim", "create"): fixture("simulation_complete.json"),
        ("alpha", "get", "ALPHA123"): envelope(fixture("alpha_pass.json")),
        ("alpha", "check", "ALPHA123", "--max-wait-seconds", "900"): envelope({"checks": [{"result": "PASS"}]}),
        ("alpha", "recordsets", "ALPHA123", "--max-wait-seconds", "900"): envelope({"results": []}),
    })
    store = FakeStore()
    store.candidates["fp1"] = SimpleNamespace(id=17)
    nodes = EvaluationNodes(runner=runner, router=FakeRouter([]), store=store, artifacts=FakeArtifacts(tmp_path))
    nodes.run_j(
        "run1",
        {"region": "USA", "delay": 1, "universe": "TOP3000", "neutralization": "INDUSTRY"},
        [{"fingerprint": "fp1", "candidate": {"expression": "ts_delta(vwap,22)"}}],
    )

    assert store.simulations["SIM-PARENT-1"]["candidate_id"] is None
    assert store.simulations["SIM-CHILD-1"]["candidate_id"] == 17


def test_j_remaining_capacity_uses_actual_child_backtests(tmp_path: Path) -> None:
    store = AgentStore(tmp_path / "agent.sqlite3")
    store.initialize()
    store.create_run("run1", RunConfig(scope_mode=ScopeMode.AUTO))
    first = store.add_candidate("run1", "fp1", {"expression": "ts_delta(vwap,22)"})
    second = store.add_candidate("run1", "fp2", {"expression": "ts_delta(vwap,63)"})
    store.record_simulation("run1", "PARENT", "COMPLETE")
    store.record_simulation("run1", "CHILD1", "COMPLETE", candidate_id=first.id)
    store.record_simulation("run1", "CHILD2", "COMPLETE", candidate_id=second.id)
    nodes = EvaluationNodes(
        runner=FakeRunner({}),
        router=FakeRouter([]),
        store=store,
        artifacts=FakeArtifacts(tmp_path),
    )

    assert nodes._remaining_simulation_capacity(
        "run1", SimpleNamespace(total_simulations=3)
    ) == 1


def test_k_failed_metrics_use_json_native_failures_and_route_to_i(tmp_path: Path) -> None:
    operator = {
        "decision": "organized",
        "reasoning_summary": "The deterministic metrics failed.",
        "evidence_refs": ["metric:A1"],
        "confidence": 1.0,
        "task_result": {"status": "COMPLETED", "payload": {}},
    }
    planner = {
        "decision": "revise expression",
        "reasoning_summary": "The candidate failed hard performance metrics.",
        "evidence_refs": ["metric:A1"],
        "confidence": 1.0,
        "diagnosis": {"failure_class": "EXPRESSION", "next_node": "I"},
    }
    router = FakeRouter([operator, planner])
    nodes = EvaluationNodes(
        runner=FakeRunner({}),
        router=router,
        store=FakeStore(),
        artifacts=FakeArtifacts(tmp_path),
    )

    result = nodes.run_k(
        "run1",
        [passing(id="A1", sharpe=0.1, fitness=0.1, margin=0.0001)],
        node_attempt_id=7,
    )

    assert result.next_node is WorkflowNode.I
    assert isinstance(router.requests[0].context["metrics"][0]["failures"], list)
    assert result.payload["diagnosis"]["failure_class"] == "EXPRESSION"


def test_k_large_raw_results_write_bounded_candidate_summaries(tmp_path: Path) -> None:
    operator = {
        "decision": "organized",
        "reasoning_summary": "The deterministic metrics failed.",
        "evidence_refs": ["metric:A0"],
        "confidence": 1.0,
        "task_result": {"status": "COMPLETED", "payload": {}},
    }
    planner = {
        "decision": "revise expression",
        "reasoning_summary": "The candidates failed hard performance metrics.",
        "evidence_refs": ["metric:A0"],
        "confidence": 1.0,
        "diagnosis": {"failure_class": "EXPRESSION", "next_node": "I"},
    }
    artifacts = FakeArtifacts(tmp_path)
    router = FakeRouter([operator, planner])
    nodes = EvaluationNodes(
        runner=FakeRunner({}),
        router=router,
        store=FakeStore(),
        artifacts=artifacts,
    )
    candidates = [
        passing(
            id=f"A{index}",
            alpha_id=f"A{index}",
            sharpe=0.1,
            fitness=0.1,
            margin=0.0001,
            raw={"response": "x" * 20_000},
        )
        for index in range(40)
    ]

    result = nodes.run_k("run1", candidates, node_attempt_id=7)

    assert result.next_node is WorkflowNode.I
    written = artifacts.values["best_alpha_candidates.json"]
    summaries = written["candidates"]
    assert len(summaries) == 40
    assert all("raw" not in item for item in summaries)
    assert redact_json(written) == written
    metric_context = router.requests[0].context
    assert len(json.dumps(metric_context)) < 50_000
    assert "raw" not in json.dumps(metric_context)


@pytest.mark.parametrize(
    "diagnosis",
    [
        {"failure_class": "DATA_FIELD", "next_node": "I"},
        {"failure_class": "EXPRESSION", "next_node": "I", "evidence_ids": ["unknown"]},
    ],
)
def test_diagnosis_rejects_invalid_route_or_evidence(diagnosis: dict[str, object]) -> None:
    with pytest.raises(EvaluationError):
        validate_diagnosis(diagnosis, evidence_ids={"metric:A1"})


def test_l_correlation_failure_routes_back_to_k_and_preserves_raw(tmp_path: Path) -> None:
    report = fixture("alpha_report_pass.json")
    report["prod_correlation"] = {"max": 0.71, "limit": 0.7}
    responses = {
        ("alpha", "get", "ALPHA123"): envelope(report["alpha"]),
        ("alpha", "check", "ALPHA123", "--max-wait-seconds", "900"): envelope(report["checks"]),
        ("alpha", "correlation", "self", "ALPHA123", "--max-wait-seconds", "900"): envelope(report["self_correlation"]),
        ("alpha", "correlation", "prod", "ALPHA123", "--max-wait-seconds", "900"): envelope(report["prod_correlation"]),
        ("alpha", "performance-comparison", "ALPHA123", "--max-wait-seconds", "900"): envelope(report["performance_comparison"]),
    }
    operator = {"decision": "organized", "reasoning_summary": "raw checks", "evidence_refs": ["alpha:ALPHA123"], "confidence": 1.0, "task_result": {"status": "COMPLETED", "payload": {}}}
    planner = {"decision": "reject", "reasoning_summary": "correlation risk", "evidence_refs": ["alpha:ALPHA123"], "confidence": 1.0, "final_recommendation": {"recommend": False, "risk_summary": "prod correlation"}}
    nodes = EvaluationNodes(runner=FakeRunner(responses), router=FakeRouter([operator, planner]), store=FakeStore(), artifacts=FakeArtifacts(tmp_path))
    result = nodes.run_l("run1", "ALPHA123")
    assert result.next_node is WorkflowNode.K
    assert result.payload["failure_record"]["failures"] == ("prod_correlation",)
    assert result.payload["report"]["prod_correlation"] == report["prod_correlation"]


def test_classify_final_checks_accepts_fixture_and_rejects_correlation() -> None:
    report = fixture("alpha_report_pass.json")
    assert classify_final_checks(report).passed
    report["prod_correlation"]["max"] = report["prod_correlation"]["limit"]
    assert not classify_final_checks(report).passed
