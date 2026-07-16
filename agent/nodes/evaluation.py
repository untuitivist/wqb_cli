from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from math import isfinite
from typing import Any

from ..models.base import ModelRequest
from ..schemas import DIAGNOSIS_ROUTES, validate_model_output
from ..store import StoreConflict, StoreRecordNotFound
from ..types import ModelRole, NodeResult, WorkflowNode


class EvaluationError(ValueError):
    """Raised when evaluation data cannot support a deterministic decision."""


@dataclass(frozen=True)
class CheckClassification:
    passed: bool
    failures: tuple[str, ...]
    degraded: bool = False


@dataclass(frozen=True)
class SimulationBatchResult:
    simulation_ids: tuple[str, ...]
    alpha_results: tuple[dict[str, object], ...]
    new_fingerprints: tuple[str, ...]
    platform_failures: tuple[dict[str, object], ...]


def classify_hard_metrics(
    alpha: Mapping[str, object],
    *,
    required_visualizations: Iterable[str] = (),
) -> CheckClassification:
    if not isinstance(alpha, Mapping):
        raise TypeError("alpha must be a mapping")
    failures: list[str] = []
    limits = {
        "sharpe": lambda value: value > 1.58,
        "fitness": lambda value: value > 1.0,
        "turnover": lambda value: 0.01 < value < 0.70,
        "margin": lambda value: value > 0.001,
    }
    for name, predicate in limits.items():
        value = alpha.get(name)
        if not _finite_number(value) or not predicate(float(value)):
            failures.append(name)
    for check in _checks(alpha.get("checks")):
        if _check_result(check) == "FAIL":
            failures.append(_check_name(check))

    visualizations = alpha.get("visualizations")
    for name in _required_names(required_visualizations):
        if not _has_visualization(visualizations, name):
            failures.append(f"visualization:{name}")
    unique = tuple(dict.fromkeys(failures))
    return CheckClassification(not unique, unique, any(item.startswith("visualization:") for item in unique))


def extract_alpha_ids(payload: Mapping[str, object]) -> tuple[str, ...]:
    """Extract Alpha IDs only from terminal child response bodies."""
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    children = payload.get("children")
    if not isinstance(children, list):
        return ()
    identifiers: list[str] = []
    for child in children:
        if not isinstance(child, Mapping):
            continue
        result = child.get("result")
        if not isinstance(result, Mapping):
            continue
        response = result.get("response")
        if not isinstance(response, Mapping):
            continue
        status_code = response.get("status_code")
        body = response.get("body")
        if (
            type(status_code) is not int
            or not 200 <= status_code <= 299
            or not isinstance(body, Mapping)
            or str(body.get("status", "")).upper() not in {"COMPLETE", "WARNING"}
        ):
            continue
        alpha_id = body.get("alpha")
        if isinstance(alpha_id, Mapping):
            alpha_id = alpha_id.get("id")
        if type(alpha_id) is str and alpha_id.strip() and alpha_id not in identifiers:
            identifiers.append(alpha_id.strip())
    return tuple(identifiers)


def select_passing_candidate(
    candidates: Sequence[Mapping[str, object]],
    *,
    required_visualizations: Iterable[str] = (),
) -> dict[str, object] | None:
    passing = [
        candidate
        for candidate in candidates
        if classify_hard_metrics(
            candidate, required_visualizations=required_visualizations
        ).passed
    ]
    if not passing:
        return None
    selected = max(
        passing,
        key=lambda candidate: (
            float(candidate["sharpe"]),
            float(candidate["fitness"]),
            float(candidate["margin"]),
            -abs(float(candidate["turnover"]) - 0.2),
            _alpha_id(candidate),
        ),
    )
    return dict(selected)


def classify_final_checks(report: Mapping[str, object]) -> CheckClassification:
    if not isinstance(report, Mapping):
        raise TypeError("report must be a mapping")
    failures: list[str] = []
    checks_value = report.get("checks")
    if isinstance(checks_value, Mapping):
        checks_value = checks_value.get("checks", checks_value.get("results"))
    for check in _checks(checks_value):
        if _check_result(check) == "FAIL":
            failures.append(_check_name(check))
    if not _successful_component(report.get("checks")):
        failures.append("platform_checks")

    for name in ("self_correlation", "prod_correlation"):
        if not _correlation_passed(report.get(name)):
            failures.append(name)
    if not _comparison_passed(report.get("performance_comparison")):
        failures.append("performance_comparison")
    unique = tuple(dict.fromkeys(failures))
    return CheckClassification(not unique, unique)


def validate_diagnosis(
    diagnosis: Mapping[str, object], *, evidence_ids: Iterable[str]
) -> dict[str, object]:
    if not isinstance(diagnosis, Mapping):
        raise EvaluationError("diagnosis must be an object")
    failure_class = diagnosis.get("failure_class")
    next_node = diagnosis.get("next_node")
    if type(failure_class) is not str or failure_class not in DIAGNOSIS_ROUTES:
        raise EvaluationError("diagnosis failure class is invalid")
    if failure_class == "PASS":
        raise EvaluationError("failed candidates cannot produce PASS diagnosis")
    if next_node != DIAGNOSIS_ROUTES[failure_class]:
        raise EvaluationError("diagnosis route does not match failure class")
    allowed = set(_required_names(evidence_ids))
    references = diagnosis.get("evidence_ids", ())
    if not isinstance(references, (list, tuple)):
        raise EvaluationError("diagnosis evidence_ids are invalid")
    if any(type(item) is not str or item not in allowed for item in references):
        raise EvaluationError("diagnosis references unknown evidence")
    return dict(diagnosis)


def build_simulation_batches(
    candidates: Sequence[Mapping[str, object]],
    scope: Mapping[str, object],
    *,
    candidates_per_round: int,
) -> tuple[list[dict[str, object]], ...]:
    if type(candidates_per_round) is not int or candidates_per_round <= 0:
        raise ValueError("candidates_per_round must be a positive integer")
    normalized_scope = _simulation_scope(scope)
    cap = min(candidates_per_round, 4 if normalized_scope["region"] == "GLB" else 8)
    simulations: list[dict[str, object]] = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise EvaluationError("candidate must be an object")
        expression = candidate.get("expression")
        if type(expression) is not str or not expression.strip():
            nested = candidate.get("candidate")
            expression = nested.get("expression") if isinstance(nested, Mapping) else None
        if type(expression) is not str or not expression.strip():
            raise EvaluationError("candidate expression is invalid")
        simulations.append(
            {
                "type": "REGULAR",
                "settings": {
                    "instrumentType": "EQUITY",
                    "region": normalized_scope["region"],
                    "universe": normalized_scope["universe"],
                    "delay": normalized_scope["delay"],
                    "neutralization": normalized_scope["neutralization"],
                    "language": "FASTEXPR",
                },
                "regular": expression.strip(),
            }
        )
    return tuple(simulations[index : index + cap] for index in range(0, len(simulations), cap))


class EvaluationNodes:
    """Nodes J-L: simulations, deterministic evaluation, and final checks."""

    def __init__(self, *, runner: Any, router: Any, store: Any, artifacts: Any | None = None) -> None:
        if not callable(getattr(runner, "run", None)):
            raise TypeError("runner must provide run")
        if not callable(getattr(router, "invoke", None)):
            raise TypeError("router must provide invoke")
        self._runner = runner
        self._router = router
        self._store = store
        self._artifacts = artifacts if artifacts is not None else getattr(runner, "artifacts", None)

    def run_j(
        self,
        run_id: str,
        scope: Mapping[str, object],
        candidates: Sequence[Mapping[str, object]],
        *,
        resume_simulation_ids: Sequence[str] = (),
    ) -> SimulationBatchResult:
        simulation_ids: list[str] = []
        alpha_results: list[dict[str, object]] = []
        failures: list[dict[str, object]] = []
        new_fingerprints: list[str] = []
        payloads: list[dict[str, object]] = []

        for simulation_id in _required_names(resume_simulation_ids):
            result = self._run(
                run_id,
                WorkflowNode.J,
                ("sim", "get", simulation_id, "--max-wait-seconds", "900"),
                f"resume_{simulation_id}.json",
            )
            payload = _result_payload(result)
            simulation_ids.append(simulation_id)
            payloads.append(payload)
            self._persist_simulation_payload(run_id, payload, simulation_id, result)

        if candidates:
            budget = getattr(getattr(self._runner, "policy", None), "budget", None)
            per_round = getattr(budget, "candidates_per_round", 8)
            batches = build_simulation_batches(
                candidates, scope, candidates_per_round=per_round
            )
            offset = 0
            for index, batch in enumerate(batches, start=1):
                input_path = self._stage_simulation_input(run_id, batch)
                result = self._run(
                    run_id,
                    WorkflowNode.J,
                    ("sim", "create", "--input", str(input_path)),
                    f"simulation_batch_{index}_result.json",
                )
                payload = _result_payload(result)
                payloads.append(payload)
                parent = _simulation_id(payload)
                if parent:
                    simulation_ids.append(parent)
                self._persist_simulation_payload(run_id, payload, parent, result)
                if payload.get("ok") is not True:
                    failures.append({"stage": "simulation", "raw": deepcopy(payload)})
                else:
                    for candidate in candidates[offset : offset + len(batch)]:
                        fingerprint = candidate.get("fingerprint")
                        if type(fingerprint) is str and fingerprint not in new_fingerprints:
                            new_fingerprints.append(fingerprint)
                offset += len(batch)

        alpha_ids: list[str] = []
        for payload in payloads:
            for child_id in _child_simulation_ids(payload):
                if child_id not in simulation_ids:
                    simulation_ids.append(child_id)
            for alpha_id in extract_alpha_ids(payload):
                if alpha_id not in alpha_ids:
                    alpha_ids.append(alpha_id)
        for alpha_id in alpha_ids:
            records: dict[str, object] = {}
            commands = (
                ("alpha", "get", alpha_id),
                ("alpha", "check", alpha_id, "--max-wait-seconds", "900"),
                ("alpha", "recordsets", alpha_id, "--max-wait-seconds", "900"),
            )
            labels = ("alpha", "checks", "recordsets")
            for label, argv in zip(labels, commands, strict=True):
                result = self._run(run_id, WorkflowNode.J, argv, f"{alpha_id}_{label}.json")
                raw = _result_payload(result)
                records[label] = deepcopy(raw)
                if raw.get("ok") is not True:
                    failures.append({"stage": label, "alpha_id": alpha_id, "raw": deepcopy(raw)})
            alpha_body = _successful_body(records["alpha"])
            check_body = _successful_body(records["checks"])
            merged = dict(alpha_body or {})
            merged["alpha_id"] = alpha_id
            if check_body is not None:
                merged["checks"] = check_body.get("checks", check_body.get("results", check_body))
            merged["raw"] = records
            alpha_results.append(merged)
            for simulation_id in _child_simulation_ids_for_alpha(payloads, alpha_id):
                self._update_simulation(run_id, simulation_id, "COMPLETE", alpha_id=alpha_id)
        return SimulationBatchResult(
            tuple(simulation_ids), tuple(alpha_results), tuple(new_fingerprints), tuple(failures)
        )

    def run_k(
        self,
        run_id: str,
        alpha_results: Sequence[Mapping[str, object]],
        *,
        evidence_ids: Iterable[str] = (),
        required_visualizations: Iterable[str] = (),
        node_attempt_id: int | None = None,
    ) -> NodeResult:
        ranked = sorted(
            (dict(item) for item in alpha_results),
            key=lambda item: (
                float(item.get("sharpe", float("-inf"))),
                float(item.get("fitness", float("-inf"))),
                float(item.get("margin", float("-inf"))),
                -abs(float(item.get("turnover", float("inf"))) - 0.2),
                _alpha_id(item),
            ),
            reverse=True,
        )
        artifact_ids = self._write_json(
            run_id, WorkflowNode.K, "best_alpha_candidates.json", {"candidates": ranked}
        )
        selected = select_passing_candidate(
            ranked, required_visualizations=required_visualizations
        )
        if selected is not None:
            return NodeResult(
                WorkflowNode.K,
                {"decision": "PASS", "alpha_id": _alpha_id(selected)},
                artifact_ids,
                next_node=WorkflowNode.L,
                payload={"selected_alpha": selected},
            )

        metrics = [
            {
                "evidence_id": f"metric:{_alpha_id(item)}",
                "alpha_id": _alpha_id(item),
                "metrics": {key: item.get(key) for key in ("sharpe", "fitness", "turnover", "margin", "checks")},
                "failures": classify_hard_metrics(
                    item, required_visualizations=required_visualizations
                ).failures,
            }
            for item in ranked
        ]
        operator = self._invoke(
            ModelRole.OPERATOR,
            WorkflowNode.K,
            "Organize supplied deterministic metric failures only; do not choose a route.",
            {"metrics": metrics},
        )
        planner = self._invoke(
            ModelRole.PLANNER,
            WorkflowNode.K,
            "Diagnose one failure class using supplied evidence IDs and return its exact schema route.",
            {"metrics": metrics, "operator": operator},
        )
        allowed = set(_required_names(evidence_ids)) | {item["evidence_id"] for item in metrics}
        diagnosis_value = dict(planner["diagnosis"])
        diagnosis_value["evidence_ids"] = list(planner.get("evidence_refs", ()))
        diagnosis = validate_diagnosis(diagnosis_value, evidence_ids=allowed)
        next_node = WorkflowNode(str(diagnosis["next_node"]))
        self._store.record_diagnosis(
            run_id,
            str(diagnosis["failure_class"]),
            next_node,
            {"diagnosis": diagnosis, "operator": operator, "planner": planner, "metrics": metrics},
            node_attempt_id=node_attempt_id,
        )
        artifact_ids += self._write_json(
            run_id, WorkflowNode.K, "diagnosis.json", {"diagnosis": diagnosis, "operator": operator, "planner": planner}
        )
        return NodeResult(
            WorkflowNode.K,
            {"decision": diagnosis["failure_class"]},
            artifact_ids,
            next_node=next_node,
            payload={"diagnosis": diagnosis, "metrics": metrics},
        )

    def run_l(self, run_id: str, alpha_id: str) -> NodeResult:
        if type(alpha_id) is not str or not alpha_id.strip():
            raise EvaluationError("alpha_id is invalid")
        alpha_id = alpha_id.strip()
        command_specs = (
            ("alpha", ("alpha", "get", alpha_id)),
            ("checks", ("alpha", "check", alpha_id, "--max-wait-seconds", "900")),
            ("self_correlation", ("alpha", "correlation", "self", alpha_id, "--max-wait-seconds", "900")),
            ("prod_correlation", ("alpha", "correlation", "prod", alpha_id, "--max-wait-seconds", "900")),
            ("performance_comparison", ("alpha", "performance-comparison", alpha_id, "--max-wait-seconds", "900")),
        )
        report: dict[str, object] = {}
        for label, argv in command_specs:
            raw = _result_payload(self._run(run_id, WorkflowNode.L, argv, f"{alpha_id}_{label}.json"))
            report[label] = deepcopy(_successful_body(raw) if raw.get("ok") is True else raw)
        classification = classify_final_checks(report)
        operator = self._invoke(
            ModelRole.OPERATOR,
            WorkflowNode.L,
            "Organize the complete raw final-check records without changing pass/fail controls.",
            {"alpha_id": alpha_id, "report": report, "deterministic_failures": list(classification.failures)},
        )
        planner = self._invoke(
            ModelRole.PLANNER,
            WorkflowNode.L,
            "Provide a recommendation and risk summary grounded in the deterministic final checks.",
            {"alpha_id": alpha_id, "operator": operator, "deterministic_passed": classification.passed, "failures": list(classification.failures)},
        )
        artifact_ids = self._write_json(
            run_id, WorkflowNode.L, "final_alpha_report.json", {"alpha_id": alpha_id, "report": report, "classification": {"passed": classification.passed, "failures": list(classification.failures)}, "operator": operator, "planner": planner}
        )
        payload: dict[str, object] = {"alpha_id": alpha_id, "report": report, "operator": operator, "planner": planner}
        if not classification.passed:
            failure_record = {"alpha_id": alpha_id, "failures": classification.failures, "raw": report}
            payload["failure_record"] = failure_record
            artifact_ids += self._write_json(
                run_id,
                WorkflowNode.L,
                "final_check_failure.json",
                {**failure_record, "failures": list(classification.failures)},
            )
        return NodeResult(
            WorkflowNode.L,
            {"passed": classification.passed, "failures": classification.failures},
            artifact_ids,
            next_node=WorkflowNode.M if classification.passed else WorkflowNode.K,
            payload=payload,
        )

    def _persist_simulation_payload(self, run_id: str, payload: Mapping[str, object], parent_id: str | None, result: Any) -> None:
        artifact_id = getattr(getattr(result, "artifact", None), "id", None)
        if parent_id:
            status = _simulation_status(payload)
            self._record_or_update_simulation(run_id, parent_id, status, result_artifact_id=artifact_id)
        for child in payload.get("children", ()) if isinstance(payload.get("children"), list) else ():
            if not isinstance(child, Mapping):
                continue
            child_id = child.get("simulation_id")
            if type(child_id) is not str or not child_id.strip():
                continue
            status = _child_status(child)
            alpha_ids = extract_alpha_ids({"children": [child]})
            self._record_or_update_simulation(
                run_id, child_id, status, alpha_id=alpha_ids[0] if alpha_ids else None, result_artifact_id=artifact_id
            )

    def _record_or_update_simulation(self, run_id: str, simulation_id: str, status: str, *, alpha_id: str | None = None, result_artifact_id: int | None = None) -> None:
        try:
            self._store.get_simulation(run_id, simulation_id)
        except (StoreRecordNotFound, KeyError):
            self._store.record_simulation(run_id, simulation_id, status, alpha_id=alpha_id, result_artifact_id=result_artifact_id)
        else:
            self._update_simulation(run_id, simulation_id, status, alpha_id=alpha_id, result_artifact_id=result_artifact_id)

    def _update_simulation(self, run_id: str, simulation_id: str, status: str, *, alpha_id: str | None = None, result_artifact_id: int | None = None) -> None:
        try:
            self._store.update_simulation(run_id, simulation_id, status, alpha_id=alpha_id, result_artifact_id=result_artifact_id)
        except StoreConflict:
            raise EvaluationError("simulation persistence conflicts with recorded identity") from None

    def _run(self, run_id: str, node: WorkflowNode, argv: tuple[str, ...], artifact_name: str) -> Any:
        return self._runner.run(run_id, node, argv, artifact_name)

    def _invoke(self, role: ModelRole, node: WorkflowNode, instructions: str, context: dict[str, object]) -> dict[str, Any]:
        value = getattr(self._router.invoke(ModelRequest(role=role, node=node, instructions=instructions, context=context)), "value", None)
        return validate_model_output(role, node, value)

    def _write_json(self, run_id: str, node: WorkflowNode, name: str, value: object) -> Any:
        if not callable(getattr(self._artifacts, "write_json", None)):
            raise EvaluationError("artifact writer is required")
        artifact = self._artifacts.write_json(run_id, node, name, value)
        return (f"artifact:{artifact.id}",) if type(getattr(artifact, "id", None)) is int else ()

    def _stage_simulation_input(
        self, run_id: str, batch: list[dict[str, object]]
    ) -> Any:
        stage = getattr(self._artifacts, "stage_input", None)
        if not callable(stage):
            raise EvaluationError("artifact writer must provide stage_input")
        content = json.dumps(
            batch,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return stage(
            run_id,
            WorkflowNode.J,
            content,
            hashlib.sha256(content).hexdigest(),
            require_utf8_text=True,
        )


def _finite_number(value: object) -> bool:
    return type(value) in {int, float} and isfinite(float(value))


def _required_names(values: Iterable[str]) -> tuple[str, ...]:
    try:
        copied = tuple(values)
    except TypeError:
        raise TypeError("values must be iterable") from None
    if any(type(item) is not str or not item.strip() for item in copied):
        raise EvaluationError("values contain an invalid identifier")
    return tuple(item.strip() for item in copied)


def _checks(value: object) -> tuple[Mapping[str, object], ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _check_result(check: Mapping[str, object]) -> str:
    return str(check.get("result", check.get("status", ""))).upper()


def _check_name(check: Mapping[str, object]) -> str:
    name = check.get("name")
    return f"check:{name}" if type(name) is str and name.strip() else "platform_check"


def _has_visualization(value: object, name: str) -> bool:
    if isinstance(value, Mapping):
        return name in value and value[name] is not None and value[name] != "" and value[name] != []
    if isinstance(value, list):
        return any(item == name or isinstance(item, Mapping) and item.get("name") == name for item in value)
    return False


def _successful_component(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    checks = value.get("checks", value.get("results"))
    if checks is None:
        return value.get("passed") is True or value.get("ok") is True
    return isinstance(checks, list) and bool(checks) and not any(_check_result(item) == "FAIL" for item in checks if isinstance(item, Mapping))


def _correlation_passed(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    if value.get("passed") is False or value.get("ok") is False:
        return False
    maximum = value.get("max", value.get("value", value.get("correlation")))
    limit = value.get("limit", value.get("threshold"))
    return _finite_number(maximum) and _finite_number(limit) and float(maximum) < float(limit)


def _comparison_passed(value: object) -> bool:
    if not isinstance(value, Mapping) or value.get("passed") is not True:
        return False
    checks = value.get("checks")
    return checks is None or isinstance(checks, list) and not any(_check_result(item) == "FAIL" for item in checks if isinstance(item, Mapping))


def _alpha_id(candidate: Mapping[str, object]) -> str:
    value = candidate.get("alpha_id", candidate.get("id", ""))
    return value if type(value) is str else ""


def _simulation_scope(scope: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(scope, Mapping):
        raise TypeError("scope must be a mapping")
    result: dict[str, object] = {}
    for name in ("region", "universe", "neutralization"):
        value = scope.get(name)
        if type(value) is not str or not value.strip():
            raise EvaluationError(f"scope {name} is invalid")
        result[name] = value.strip().upper()
    delay = scope.get("delay")
    if type(delay) is not int or delay not in {0, 1}:
        raise EvaluationError("scope delay is invalid")
    result["delay"] = delay
    return result


def _result_payload(result: Any) -> dict[str, object]:
    payload = getattr(result, "payload", None)
    if not isinstance(payload, Mapping):
        raise EvaluationError("runner returned an invalid payload")
    return dict(payload)


def _successful_body(payload: object) -> dict[str, object] | None:
    if not isinstance(payload, Mapping) or payload.get("ok") is not True:
        return None
    response = payload.get("response")
    if not isinstance(response, Mapping):
        return None
    status = response.get("status_code")
    body = response.get("body")
    if type(status) is int and 200 <= status <= 299 and isinstance(body, Mapping):
        return dict(body)
    return None


def _simulation_id(payload: Mapping[str, object]) -> str | None:
    value = payload.get("simulation_id", payload.get("id"))
    return value.strip() if type(value) is str and value.strip() else None


def _child_simulation_ids(payload: Mapping[str, object]) -> tuple[str, ...]:
    children = payload.get("children")
    if not isinstance(children, list):
        return ()
    values: list[str] = []
    for child in children:
        if not isinstance(child, Mapping):
            continue
        value = child.get("simulation_id", child.get("id"))
        if type(value) is str and value.strip() and value not in values:
            values.append(value.strip())
    return tuple(values)


def _simulation_status(payload: Mapping[str, object]) -> str:
    classification = payload.get("classification")
    if isinstance(classification, Mapping) and type(classification.get("status")) is str:
        return str(classification["status"]).upper()
    return "COMPLETE" if payload.get("ok") is True else "FAILED"


def _child_status(child: Mapping[str, object]) -> str:
    classification = child.get("classification")
    if isinstance(classification, Mapping) and type(classification.get("status")) is str:
        return str(classification["status"]).upper()
    result = child.get("result")
    body = _successful_body(result)
    status = body.get("status") if body else None
    return str(status).upper() if type(status) is str else "FAILED"


def _child_simulation_ids_for_alpha(payloads: Sequence[Mapping[str, object]], alpha_id: str) -> tuple[str, ...]:
    values: list[str] = []
    for payload in payloads:
        children = payload.get("children")
        if not isinstance(children, list):
            continue
        for child in children:
            if isinstance(child, Mapping) and extract_alpha_ids({"children": [child]}) == (alpha_id,):
                value = child.get("simulation_id")
                if type(value) is str:
                    values.append(value)
    return tuple(values)
