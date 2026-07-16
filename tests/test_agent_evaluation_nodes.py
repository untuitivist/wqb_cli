from __future__ import annotations

import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from wqb_cli.agent.nodes.evaluation import (
    EvaluationError,
    EvaluationNodes,
    build_simulation_batches,
    classify_final_checks,
    classify_hard_metrics,
    extract_alpha_ids,
    select_passing_candidate,
    validate_diagnosis,
)
from wqb_cli.agent.types import Budget, WorkflowNode


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
        self.diagnoses: list[tuple[str, WorkflowNode, dict[str, object]]] = []

    def record_simulation(self, run_id, simulation_id, status, candidate_id=None, alpha_id=None, result_artifact_id=None):
        if simulation_id in self.simulations:
            raise AssertionError("duplicate simulation record")
        self.simulations[simulation_id] = {"status": status, "alpha_id": alpha_id}

    def update_simulation(self, run_id, simulation_id, status, alpha_id=None, result_artifact_id=None):
        self.simulations[simulation_id].update(status=status)
        if alpha_id is not None:
            self.simulations[simulation_id]["alpha_id"] = alpha_id

    def get_simulation(self, run_id, simulation_id):
        value = self.simulations[simulation_id]
        return SimpleNamespace(simulation_id=simulation_id, **value)

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

    def invoke(self, request):
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


def test_j_resume_with_recorded_simulation_id_does_not_create(tmp_path: Path) -> None:
    runner = FakeRunner({
        ("sim", "get", "SIM-PARENT-1", "--max-wait-seconds", "900"): fixture("simulation_complete.json"),
        ("alpha", "get", "ALPHA123"): envelope(fixture("alpha_pass.json")),
        ("alpha", "check", "ALPHA123", "--max-wait-seconds", "900"): envelope({"checks": [{"result": "PASS"}]}),
        ("alpha", "recordsets", "ALPHA123", "--max-wait-seconds", "900"): envelope({"results": []}),
    })
    store = FakeStore()
    store.simulations["SIM-PARENT-1"] = {"status": "TIMED_OUT", "alpha_id": None}
    nodes = EvaluationNodes(runner=runner, router=FakeRouter([]), store=store, artifacts=FakeArtifacts(tmp_path))
    result = nodes.run_j("run1", {}, [], resume_simulation_ids=("SIM-PARENT-1",))
    assert result.simulation_ids == ("SIM-PARENT-1", "SIM-CHILD-1")
    assert not any(argv[:2] == ("sim", "create") for _, argv, _ in runner.calls)
    assert result.alpha_results[0]["alpha_id"] == "ALPHA123"


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
