from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from typing import Any

from ..expressions import ExpressionViolation, validate_candidate
from ..models.base import ModelRequest
from ..schemas import validate_model_output
from ..store import StoreRecordNotFound
from ..types import ModelRole, NodeResult, WorkflowNode
from .evidence import EvidenceError, evidence_coverage


class ResearchError(ValueError):
    """Raised for a plan or candidate that cannot enter the durable workflow."""


@dataclass(frozen=True)
class _OperatorTaskOutcome:
    status: str
    accepted: tuple[dict[str, Any], ...] = ()
    rejected: tuple[dict[str, Any], ...] = ()
    result: dict[str, Any] | None = None


def validate_mechanism_fields(
    plan: object,
    *,
    candidate_fields: object,
    resolvable_evidence: object,
    current_tower: str,
) -> dict[str, Any]:
    if not isinstance(plan, Mapping):
        raise TypeError("research plan must be an object")
    if type(current_tower) is not str or not current_tower.strip():
        raise ValueError("current tower is invalid")
    candidates = _names(candidate_fields, "candidate_fields")
    evidence = _evidence_refs(resolvable_evidence)
    mechanisms = plan.get("mechanisms")
    if not isinstance(mechanisms, list) or not mechanisms:
        raise ResearchError("research plan requires mechanisms")
    _reject_expression_keys(plan)
    copied: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for item in mechanisms:
        if not isinstance(item, Mapping):
            raise ResearchError("mechanism must be an object")
        mechanism_id = item.get("mechanism_id")
        if type(mechanism_id) is not str or not mechanism_id.strip():
            raise ResearchError("mechanism_id is invalid")
        mechanism_id = mechanism_id.strip()
        if mechanism_id in identifiers:
            raise ResearchError(f"duplicate mechanism_id: {mechanism_id}")
        identifiers.add(mechanism_id)
        fields = _names(item.get("field_ids"), "mechanism field_ids")
        outside = sorted(fields - candidates)
        if outside:
            raise ResearchError(f"field outside F candidate pool: {outside[0]}")
        references = _evidence_refs(item.get("evidence_refs"))
        unresolved = sorted(references - evidence)
        if unresolved:
            raise ResearchError(f"mechanism evidence is not resolvable: {unresolved[0]}")
        tower_id = item.get("tower_id")
        if type(tower_id) is not str or not tower_id.strip():
            raise ResearchError("mechanism must explicitly reference the current tower")
        if tower_id != current_tower:
            raise ResearchError("mechanism references a different current tower")
        record = dict(item)
        record["mechanism_id"] = mechanism_id
        record["field_ids"] = sorted(fields)
        record["evidence_refs"] = sorted(references)
        record["tower_id"] = current_tower
        copied.append(record)
    result = dict(plan)
    result["mechanisms"] = copied
    return result


class ResearchNodes:
    """Nodes H and I: bind research ideas to evidence, then materialize one task."""

    def __init__(self, *, runner: Any, router: Any, store: Any, artifacts: Any | None = None) -> None:
        if not callable(getattr(router, "invoke", None)):
            raise TypeError("router must provide invoke")
        self._runner = runner
        self._router = router
        self._store = store
        self._artifacts = artifacts if artifacts is not None else getattr(runner, "artifacts", None)

    def run_h(
        self,
        run_id: str,
        scope: Mapping[str, Any],
        current_tower: str,
        candidate_fields: list[Mapping[str, Any]] | list[str],
        lessons: list[Mapping[str, Any]],
    ) -> NodeResult:
        normalized_scope = _scope(scope)
        coverage = evidence_coverage(lessons)
        if not coverage.complete:
            raise ResearchError(f"research plan requires evidence coverage: {', '.join(coverage.missing_sources)}")
        for lesson in lessons:
            for key in ("source_id", "extracted_statement", "applicability"):
                if type(lesson.get(key)) is not str or not lesson[key].strip():
                    raise ResearchError(f"evidence lesson has invalid {key}")
        evidence_refs = self._verified_evidence_refs(run_id, lessons)
        field_records, field_artifacts = self._field_metadata(run_id, candidate_fields)
        field_ids = {record["id"] for record in field_records}
        planner = self._invoke(
            ModelRole.PLANNER, WorkflowNode.H,
            "Create a research plan only. Each mechanism must use supplied field IDs, current tower ID, and artifact evidence. Never produce expressions or simulation settings.",
            {"scope": normalized_scope, "current_tower": current_tower, "field_metadata": field_records, "evidence": [dict(lesson) for lesson in lessons]},
        )
        raw_plan = planner.get("research_plan")
        plan = validate_mechanism_fields(raw_plan, candidate_fields=field_ids, resolvable_evidence=evidence_refs, current_tower=current_tower)
        latest = self._store.get_latest_research_plan(run_id)
        version = 1 if latest is None else latest.plan_version + 1
        canonical = _canonical(plan)
        plan_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        self._store.record_research_plan(run_id, version, plan_hash, plan)
        artifacts = field_artifacts + self._write_json(run_id, WorkflowNode.H, "research_plan.json", {"plan_version": version, "plan_hash": plan_hash, "plan": plan})
        return NodeResult(WorkflowNode.H, {"plan_version": version, "plan_hash": plan_hash, "mechanisms": len(plan["mechanisms"])}, artifacts, next_node=WorkflowNode.I, payload={"plan_version": version, "plan_hash": plan_hash, "research_plan": plan})

    def run_i(
        self,
        run_id: str,
        scope: Mapping[str, Any],
        operators: Mapping[str, Mapping[str, object]],
        *,
        allow_revalidation: bool = False,
    ) -> NodeResult:
        normalized_scope = _scope(scope)
        if type(allow_revalidation) is not bool:
            raise TypeError("allow_revalidation must be a bool")
        plan_record = self._store.get_latest_research_plan(run_id)
        if plan_record is None:
            raise ResearchError("candidate materialization requires a locked research plan")
        mechanisms = {item["mechanism_id"]: item for item in plan_record.plan.get("mechanisms", []) if isinstance(item, Mapping)}
        planner = self._invoke(
            ModelRole.PLANNER, WorkflowNode.I,
            "Create candidate tasks only. Bind every task to the provided plan version/hash and mechanism fields. Do not write FASTEXPR expressions.",
            {"plan_version": plan_record.plan_version, "plan_hash": plan_record.plan_hash, "mechanisms": list(mechanisms.values()), "operator_names": sorted(operators)},
        )
        candidate_plan = planner.get("candidate_plan")
        tasks = self._validated_tasks(candidate_plan, plan_record.plan_version, plan_record.plan_hash, mechanisms, operators)
        accepted: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        task_ids: list[str] = []
        for task in tasks:
            task_id = task["task_id"]
            task_ids.append(task_id)
            self._store.record_operator_task(
                run_id, task_id, plan_record.plan_version, task
            )
            try:
                outcome = self._run_operator_task(
                    run_id,
                    normalized_scope,
                    plan_record.plan_version,
                    plan_record.plan_hash,
                    task,
                    operators,
                    allow_revalidation,
                )
            except Exception as error:
                self._store.complete_operator_task(
                    run_id, task_id, "FAILED", {"error": type(error).__name__}
                )
                raise
            if outcome.status == "BLOCKED":
                blocked_result = outcome.result or {
                    "status": "BLOCKED",
                    "reason": "operator task blocked",
                }
                self._store.complete_operator_task(
                    run_id, task_id, "BLOCKED", blocked_result
                )
                artifacts = self._write_json(
                    run_id,
                    WorkflowNode.I,
                    "candidate_materialization_blocked.json",
                    {
                        "plan_version": plan_record.plan_version,
                        "plan_hash": plan_record.plan_hash,
                        "task_id": task_id,
                        "status": "BLOCKED",
                        "reason": blocked_result["reason"],
                    },
                )
                return NodeResult(
                    WorkflowNode.I,
                    {
                        "status": "BLOCKED",
                        "task_id": task_id,
                        "reason": blocked_result["reason"],
                    },
                    artifacts,
                    next_node=WorkflowNode.I,
                    payload={
                        "status": "BLOCKED",
                        "task_id": task_id,
                        "reason": blocked_result["reason"],
                        "accepted": accepted,
                        "rejected": rejected,
                        "new_fingerprints": [],
                        "plan_version": plan_record.plan_version,
                        "plan_hash": plan_record.plan_hash,
                    },
                )
            task_accepted = list(outcome.accepted)
            task_rejected = list(outcome.rejected)
            accepted.extend(task_accepted)
            rejected.extend(task_rejected)
            self._store.complete_operator_task(
                run_id,
                task_id,
                "COMPLETED",
                {"accepted": task_accepted, "rejected": task_rejected},
            )
        artifacts = self._write_json(run_id, WorkflowNode.I, "candidate_materialization.json", {"plan_version": plan_record.plan_version, "plan_hash": plan_record.plan_hash, "task_ids": task_ids, "accepted": accepted, "rejected": rejected})
        new_fingerprints = [
            item["fingerprint"]
            for item in accepted
            if not item.get("current_run_existing")
        ]
        return NodeResult(WorkflowNode.I, {"accepted": len(accepted), "rejected": len(rejected), "task_ids": task_ids}, artifacts, next_node=WorkflowNode.J, payload={"accepted": accepted, "rejected": rejected, "new_fingerprints": new_fingerprints, "plan_version": plan_record.plan_version, "plan_hash": plan_record.plan_hash})

    def _run_operator_task(
        self,
        run_id: str,
        scope: dict[str, Any],
        plan_version: int,
        plan_hash: str,
        task: dict[str, Any],
        operators: Mapping[str, Mapping[str, object]],
        allow_revalidation: bool,
    ) -> _OperatorTaskOutcome:
        operator = self._invoke(
            ModelRole.OPERATOR,
            WorkflowNode.I,
            "Materialize FASTEXPR candidates for exactly this one task. Return no plan, scope, settings, commands, or additional task.",
            {"plan_version": plan_version, "plan_hash": plan_hash, "task": task},
        )
        payload = operator.get("task_result")
        if not isinstance(payload, Mapping) or not isinstance(payload.get("payload"), Mapping):
            raise ResearchError("operator candidate task is invalid")
        status = payload.get("status")
        if status == "BLOCKED":
            reason = payload["payload"].get("reason", "operator task blocked")
            if type(reason) is not str or not reason.strip():
                raise ResearchError("blocked operator task has invalid reason")
            return _OperatorTaskOutcome(
                "BLOCKED",
                result={"status": "BLOCKED", "reason": reason.strip()[:512]},
            )
        if status != "COMPLETED":
            raise ResearchError("operator candidate task did not complete")
        content = payload["payload"]
        if any(key in content for key in ("plan_version", "plan_hash", "scope", "settings", "commands")):
            raise ResearchError("operator cannot modify the locked plan or scope")
        raw_candidates = content.get("candidates")
        if not isinstance(raw_candidates, list) or len(raw_candidates) > task["count"]:
            raise ResearchError("operator candidate count is invalid")
        accepted: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        for raw in raw_candidates:
            self._materialize_candidate(
                run_id,
                scope,
                task,
                raw,
                operators,
                allow_revalidation,
                accepted,
                rejected,
            )
        return _OperatorTaskOutcome(
            "COMPLETED", tuple(accepted), tuple(rejected), {"status": "COMPLETED"}
        )

    def _field_metadata(self, run_id: str, fields: list[Mapping[str, Any]] | list[str]) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
        result: list[dict[str, Any]] = []
        artifact_ids: list[str] = []
        for field in fields:
            if isinstance(field, Mapping):
                identifier = field.get("id")
                if type(identifier) is not str or not identifier.strip():
                    raise ResearchError("candidate field metadata has invalid id")
                field_id = identifier.strip()
            elif type(field) is str and field.strip():
                field_id = field.strip()
            else:
                raise ResearchError("candidate field metadata is unavailable")
            if not callable(getattr(self._runner, "run", None)):
                raise ResearchError("candidate field metadata is unavailable")
            response = self._runner.run(
                run_id,
                WorkflowNode.H,
                ("data", "field", field_id),
                f"field_{field_id}.json",
            )
            body = _successful_body(getattr(response, "payload", None), "field metadata")
            if body.get("id") != field_id:
                raise ResearchError("field metadata identity does not match F candidate")
            result.append(dict(body))
            artifact = getattr(response, "artifact", None)
            artifact_id = getattr(artifact, "id", None)
            if type(artifact_id) is int and artifact_id > 0:
                artifact_ids.append(f"artifact:{artifact_id}")
        if not result:
            raise ResearchError("candidate field metadata is empty")
        return result, tuple(artifact_ids)

    def _verified_evidence_refs(
        self, run_id: str, lessons: list[Mapping[str, Any]]
    ) -> set[str]:
        references: set[str] = set()
        for lesson in lessons:
            source_id = lesson["source_id"]
            if not source_id.startswith("artifact:"):
                raise ResearchError("evidence artifact reference is invalid")
            raw_id = source_id.removeprefix("artifact:")
            if not raw_id.isdigit() or int(raw_id) <= 0:
                raise ResearchError("evidence artifact reference is invalid")
            try:
                artifact = self._store.get_artifact(int(raw_id))
            except StoreRecordNotFound:
                raise ResearchError("evidence artifact is missing") from None
            if artifact.run_id != run_id or artifact.node is not WorkflowNode.G:
                raise ResearchError("evidence artifact belongs to another run or node")
            references.add(source_id)
        return references

    def _validated_tasks(self, value: object, version: int, plan_hash: str, mechanisms: dict[str, Mapping[str, Any]], operators: Mapping[str, Mapping[str, object]]) -> list[dict[str, Any]]:
        if not isinstance(value, Mapping) or value.get("plan_version") != version or value.get("plan_hash") != plan_hash:
            raise ResearchError("candidate plan does not match locked plan version/hash")
        raw_tasks = value.get("tasks")
        if not isinstance(raw_tasks, list) or not raw_tasks:
            raise ResearchError("candidate plan requires tasks")
        tasks: list[dict[str, Any]] = []
        total_count = 0
        seen: set[str] = set()
        for raw in raw_tasks:
            if not isinstance(raw, Mapping):
                raise ResearchError("candidate task is invalid")
            task_id = raw.get("task_id")
            mechanism_id = raw.get("mechanism_id")
            count = raw.get("count")
            if type(task_id) is not str or not task_id.strip() or task_id in seen:
                raise ResearchError("candidate task_id is invalid")
            task_id = task_id.strip()
            if type(mechanism_id) is not str or mechanism_id not in mechanisms:
                raise ResearchError("candidate task mechanism is invalid")
            if type(count) is not int or not 1 <= count <= 8:
                raise ResearchError("candidate task count is invalid")
            total_count += count
            if total_count > 8:
                raise ResearchError("candidate plan exceeds the per-round candidate budget")
            permitted = _names(raw.get("permitted_fields"), "permitted_fields")
            allowed = _names(mechanisms[mechanism_id].get("field_ids"), "mechanism field_ids")
            if not permitted or not permitted <= allowed:
                raise ResearchError("candidate task fields exceed mechanism fields")
            families = _names(raw.get("transform_families"), "transform_families")
            available_families = {
                _operator_family(name) for name in operators
            } | {name.lower() for name in operators}
            if not families <= available_families:
                raise ResearchError("candidate task transform family is unavailable")
            task = {"task_id": task_id, "mechanism_id": mechanism_id, "permitted_fields": sorted(permitted), "transform_families": sorted(families), "count": count, "plan_version": version, "plan_hash": plan_hash}
            tasks.append(task)
            seen.add(task_id)
        return tasks

    def _materialize_candidate(self, run_id: str, scope: dict[str, Any], task: dict[str, Any], raw: object, operators: Mapping[str, Mapping[str, object]], allow_revalidation: bool, accepted: list[dict[str, Any]], rejected: list[dict[str, Any]]) -> None:
        if not isinstance(raw, Mapping):
            self._reject(run_id, raw, "invalid_candidate", rejected)
            return
        try:
            validated = validate_candidate(raw, allowed_fields=task["permitted_fields"], banned_fields=set(), operators=operators)
            if any(
                operator not in task["transform_families"]
                and _operator_family(operator) not in task["transform_families"]
                for operator in validated.operators
            ):
                raise ExpressionViolation("candidate uses a transform outside task families")
        except (ExpressionViolation, TypeError, ValueError) as error:
            self._reject(run_id, raw, str(error), rejected)
            return
        fingerprint = validated.fingerprint
        current_duplicate = self._existing_fingerprint(run_id, fingerprint)
        experience_duplicate = self._experience_fingerprint(scope, fingerprint)
        if (current_duplicate or experience_duplicate) and not allow_revalidation:
            self._reject(run_id, raw, "duplicate_fingerprint", rejected, fingerprint=fingerprint)
            return
        if current_duplicate:
            accepted.append({"fingerprint": fingerprint, "candidate": dict(raw), "revalidated": True, "current_run_existing": True})
            return
        record = {"expression": validated.canonical_expression, "field_id": raw["field_id"], "single_mechanism": True, "plan_version": task["plan_version"], "plan_hash": task["plan_hash"], "mechanism_id": task["mechanism_id"]}
        status = "REVALIDATED" if experience_duplicate else "ACCEPTED"
        self._store.add_candidate(run_id, fingerprint, record, status=status)
        accepted.append({"fingerprint": fingerprint, "candidate": record, "revalidated": experience_duplicate})

    def _existing_fingerprint(self, run_id: str, fingerprint: str) -> bool:
        try:
            self._store.get_candidate_by_fingerprint(run_id, fingerprint)
        except StoreRecordNotFound:
            return False
        return True

    def _experience_fingerprint(self, scope: dict[str, Any], fingerprint: str) -> bool:
        records = self._store.search_experience(scope["region"], scope["delay"], scope["category"], limit=100)
        return any(getattr(record, "expression_fingerprint", None) == fingerprint for record in records)

    def _reject(self, run_id: str, raw: object, reason: str, rejected: list[dict[str, Any]], *, fingerprint: str | None = None) -> None:
        rendered = _canonical(raw if isinstance(raw, Mapping) else {"raw": repr(raw)})
        key = fingerprint or hashlib.sha256(rendered.encode("utf-8")).hexdigest()
        persistence_key = f"rejected:{key}"
        record = {"raw_candidate": dict(raw) if isinstance(raw, Mapping) else {"raw": repr(raw)}, "rejection_fingerprint": key}
        self._store.add_candidate(
            run_id,
            persistence_key,
            record,
            status="REJECTED",
            reason=reason[:512],
        )
        rejected.append({"fingerprint": key, "reason": reason[:512]})

    def _invoke(self, role: ModelRole, node: WorkflowNode, instructions: str, context: dict[str, Any]) -> dict[str, Any]:
        response = self._router.invoke(
            ModelRequest(
                role=role,
                node=node,
                instructions=instructions,
                context=_bounded_context(context),
            )
        )
        value = getattr(response, "value", None)
        if type(value) is not dict:
            raise ResearchError("model response has no valid value")
        return validate_model_output(role, node, value)

    def _write_json(self, run_id: str, node: WorkflowNode, name: str, value: dict[str, Any]) -> tuple[str, ...]:
        if not callable(getattr(self._artifacts, "write_json", None)):
            return ()
        artifact = self._artifacts.write_json(run_id, node, name, value)
        identifier = getattr(artifact, "id", None)
        return (f"artifact:{identifier}",) if type(identifier) is int and identifier > 0 else ()


def _successful_body(payload: object, label: str) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or payload.get("ok") is not True:
        raise ResearchError(f"{label} did not return a successful response")
    response = payload.get("response")
    if not isinstance(response, Mapping) or type(response.get("status_code")) is not int or not 200 <= response["status_code"] <= 299 or not isinstance(response.get("body"), Mapping):
        raise ResearchError(f"{label} did not return a successful response body")
    return dict(response["body"])


def _scope(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("scope must be a mapping")
    required = ("region", "delay", "universe", "neutralization", "category")
    result: dict[str, Any] = {}
    for key in required:
        item = value.get(key)
        if key == "delay":
            if type(item) is not int or item not in {0, 1}:
                raise ResearchError("scope delay is invalid")
        elif type(item) is not str or not item.strip():
            raise ResearchError(f"scope {key} is invalid")
        result[key] = item.strip() if type(item) is str else item
    return result


def _names(values: object, label: str) -> set[str]:
    if not isinstance(values, (list, tuple, set, frozenset)):
        raise ResearchError(f"{label} must be a collection")
    result: set[str] = set()
    for value in values:
        if type(value) is not str or not value.strip():
            raise ResearchError(f"{label} contains an invalid value")
        result.add(value.strip().lower())
    if not result:
        raise ResearchError(f"{label} must not be empty")
    return result


def _evidence_refs(values: object) -> set[str]:
    names = _names(values, "evidence_refs")
    if any(not value.startswith("artifact:") for value in names):
        raise ResearchError("evidence_refs must be artifact references")
    return names


def _reject_expression_keys(value: object) -> None:
    forbidden = {"expression", "expressions", "settings", "simulation_settings", "fast_expr"}
    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if any(type(key) is str and key.lower() in forbidden for key in current):
                raise ResearchError("research plan must not contain expressions or settings")
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _operator_family(name: str) -> str:
    normalized = name.lower()
    if normalized.startswith("ts_"):
        return "time_series"
    if normalized.startswith("group_"):
        return "group"
    if normalized.startswith("vec_"):
        return "vector"
    if normalized in {"rank", "zscore", "normalize", "scale", "quantile", "winsorize"}:
        return "cross_sectional"
    if normalized in {"add", "subtract", "multiply", "divide", "inverse", "log", "power", "signed_power", "abs", "sqrt"}:
        return "arithmetic"
    if normalized in {"and", "or", "not", "if_else", "equal", "less", "greater"}:
        return "logical"
    return normalized


def _bounded_context(value: dict[str, Any]) -> dict[str, Any]:
    def copy(item: object, depth: int, *, string_limit: int, item_limit: int) -> object:
        if item is None or type(item) in {bool, int, float}:
            return item
        if type(item) is str:
            return item[:string_limit]
        if depth >= 8:
            return "[truncated]"
        if isinstance(item, Mapping):
            return {
                str(key)[:128]: copy(child, depth + 1, string_limit=string_limit, item_limit=item_limit)
                for key, child in list(item.items())[:item_limit]
                if type(key) is str
            }
        if isinstance(item, (list, tuple)):
            return [copy(child, depth + 1, string_limit=string_limit, item_limit=item_limit) for child in list(item)[:item_limit]]
        return "[unsupported]"

    for string_limit, item_limit in ((1_000, 32), (256, 12), (96, 8)):
        bounded = copy(value, 0, string_limit=string_limit, item_limit=item_limit)
        if not isinstance(bounded, dict):
            raise ResearchError("model context is invalid")
        if len(_canonical(bounded)) <= 20_000:
            return bounded
    raise ResearchError("model context exceeds the bounded input limit")
