from __future__ import annotations

from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from math import isfinite
from typing import Any

from ..expressions import ExpressionViolation, validate_candidate
from ..models.base import ModelError, ModelRequest
from ..schemas import (
    MAX_RESEARCH_IDEAS,
    ModelRefusal,
    SchemaViolation,
    validate_model_output,
)
from ..store import StoreConflict, StoreRecordNotFound
from ..strategies import (
    materialize_strategy_templates,
    profile_research_strategy,
    strategy_catalog,
    validate_research_strategy,
)
from ..types import ModelRole, NodeResult, RunState, WorkflowNode
from .evidence import (
    REQUIRED_EVIDENCE_CLASSES,
    EvidenceError,
    keyword_evidence_coverage,
)


MAX_GENERATED_RESEARCH_IDEAS = 4
MAX_H_CANDIDATE_FIELDS = 12


class ResearchError(ValueError):
    """Raised for a plan or candidate that cannot enter the durable workflow."""


_FIELD_ROLES = frozenset(
    {
        "primary_signal",
        "confirmation",
        "condition",
        "grouping",
        "weighting",
        "normalization",
        "risk_control",
        "benchmark",
    }
)
MAX_EXPRESSIONS_PER_PLAN = 200
MAX_PLANNER_EXPRESSIONS_PER_PLAN = 20
MAX_CANDIDATES_PER_OPERATOR_TASK = 10
MAX_OPERATOR_GENERATION_ATTEMPTS = 3
MIN_EXPRESSIONS_PER_IDEA = 4
UNDERFILLED_IDEA_ERROR = "idea has fewer than"


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
    require_specific_hypothesis: bool = False,
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
    if len(mechanisms) > MAX_RESEARCH_IDEAS:
        raise ResearchError(
            f"research plan exceeds the {MAX_RESEARCH_IDEAS}-idea limit"
        )
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
        hypothesis = item.get("hypothesis")
        if require_specific_hypothesis and not _specific_hypothesis(hypothesis, fields):
            raise ResearchError("mechanism hypothesis is generic or does not explain its fields")
        bindings = _validated_field_bindings(
            item.get("field_bindings"),
            fields=fields,
            mechanism_evidence=references,
            resolvable_evidence=evidence,
        )
        record = dict(item)
        record["mechanism_id"] = mechanism_id
        record["field_ids"] = sorted(fields)
        record["field_bindings"] = bindings
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
        evidence_bundle: Mapping[str, Any],
        *,
        refinement_context: Mapping[str, Any] | None = None,
    ) -> NodeResult:
        if refinement_context is not None and not isinstance(
            refinement_context, Mapping
        ):
            raise TypeError("refinement_context must be a mapping or None")
        normalized_scope = _scope(scope)
        lessons, evidence_refs = self._verified_evidence_bundle(
            run_id, evidence_bundle
        )
        selected_fields = candidate_fields[:MAX_H_CANDIDATE_FIELDS]
        field_records, field_artifacts = self._field_metadata(run_id, selected_fields)
        field_ids = {record["id"] for record in field_records}
        field_types = {
            record["id"]: str(record.get("type", "MATRIX")).strip().upper()
            for record in field_records
        }
        semantic_error: str | None = None
        for repair_attempt in range(3):
            context = {
                "scope": normalized_scope,
                "current_tower": current_tower,
                "required_tower_id": current_tower,
                "field_metadata": field_records,
                "allowed_field_ids": sorted(field_ids),
                "evidence": lessons,
                "allowed_evidence_refs": sorted(evidence_refs),
                "idea_constraints": {
                    "generation_goal": "generate a concise set of the strongest evidence-supported ideas",
                    "max_ideas": MAX_GENERATED_RESEARCH_IDEAS,
                    "padding_forbidden": True,
                },
            }
            if semantic_error is not None:
                context["semantic_repair_error"] = semantic_error
            if refinement_context:
                context["refinement_evidence"] = _compact_refinement_evidence(
                    refinement_context, None
                )
            planner = self._invoke(
                ModelRole.PLANNER,
                WorkflowNode.H,
                f"Create an evidence-specific research plan only. Generate between 1 and {MAX_GENERATED_RESEARCH_IDEAS} genuinely distinct, high-confidence mechanisms supported by the supplied fields and evidence; prefer fewer mechanisms when evidence is narrow, and do not pad the plan with weak or duplicate ideas. When refinement_evidence is present, revise the economic mechanism to address its measured failure class, metric failure counts, weak template families, and anti-pattern actions instead of merely restating the previous mechanism. Refinement metric IDs are diagnostic feedback, not citable source evidence: every mechanism must still cite only allowed_evidence_refs. Every mechanism may bind any number of economically related allowed_field_ids. For every field_id, provide exactly one field_binding with the same field_id, one allowed role (primary_signal, confirmation, condition, grouping, weighting, normalization, risk_control, or benchmark), a field-specific rationale, and evidence_refs that are also present in the mechanism evidence_refs. Explain the expected direction or relationship in the hypothesis, use required_tower_id exactly, and cite only allowed_evidence_refs. Keep reasoning_summary concise. Do not add fields merely to increase breadth. Never produce expressions or simulation settings, and never use generic claims that a field may contain stable information.",
                context,
            )
            try:
                plan = validate_mechanism_fields(
                    planner.get("research_plan"),
                    candidate_fields=field_ids,
                    resolvable_evidence=evidence_refs,
                    current_tower=current_tower,
                    require_specific_hypothesis=True,
                )
                for mechanism in plan["mechanisms"]:
                    mechanism["field_types"] = {
                        field_id: field_types[field_id]
                        for field_id in mechanism["field_ids"]
                    }
                break
            except (ResearchError, TypeError, ValueError) as error:
                if repair_attempt == 2:
                    artifacts = field_artifacts + self._write_json(
                        run_id,
                        WorkflowNode.H,
                        "research_plan_blocked.json",
                        {
                            "status": "BLOCKED",
                            "reason": "planner could not produce an evidence-specific research plan",
                            "semantic_error": str(error),
                        },
                    )
                    return NodeResult(
                        WorkflowNode.H,
                        {
                            "status": "BLOCKED",
                            "reason": "planner could not produce an evidence-specific research plan",
                        },
                        artifacts,
                        run_state=RunState.PAUSED_MODEL,
                        payload={},
                    )
                semantic_error = str(error)
        latest = self._store.get_latest_research_plan(run_id)
        version = 1 if latest is None else latest.plan_version + 1
        canonical = _canonical(plan)
        plan_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        self._store.record_research_plan(run_id, version, plan_hash, plan)
        self._store.sync_research_ideas(
            run_id, version, plan_hash, [dict(item) for item in plan["mechanisms"]]
        )
        artifacts = field_artifacts + self._write_json(run_id, WorkflowNode.H, "research_plan.json", {"plan_version": version, "plan_hash": plan_hash, "plan": plan})
        return NodeResult(WorkflowNode.H, {"plan_version": version, "plan_hash": plan_hash, "mechanisms": len(plan["mechanisms"])}, artifacts, next_node=WorkflowNode.I, payload={"plan_version": version, "plan_hash": plan_hash, "research_plan": plan})

    def run_i(
        self,
        run_id: str,
        scope: Mapping[str, Any],
        operators: Mapping[str, Mapping[str, object]],
        *,
        allow_revalidation: bool = False,
        refinement_context: Mapping[str, Any] | None = None,
    ) -> NodeResult:
        normalized_scope = _scope(scope)
        if type(allow_revalidation) is not bool:
            raise TypeError("allow_revalidation must be a bool")
        if refinement_context is not None and not isinstance(
            refinement_context, Mapping
        ):
            raise TypeError("refinement_context must be a mapping or None")
        plan_record = self._store.get_latest_research_plan(run_id)
        if plan_record is None:
            raise ResearchError("candidate materialization requires a locked research plan")
        mechanisms = {
            item["mechanism_id"]: dict(item)
            for item in plan_record.plan.get("mechanisms", [])
            if isinstance(item, Mapping) and type(item.get("mechanism_id")) is str
        }
        if not mechanisms:
            raise ResearchError("locked research plan has no valid ideas")
        ideas = self._store.sync_research_ideas(
            run_id,
            plan_record.plan_version,
            plan_record.plan_hash,
            list(mechanisms.values()),
        )
        accepted_before = self._accepted_plan_candidates(
            run_id, plan_record.plan_version, plan_record.plan_hash
        )
        known_fingerprints = {item["fingerprint"] for item in accepted_before}
        covered_counts: dict[str, int] = {}
        for item in accepted_before:
            candidate = item.get("candidate")
            mechanism_id = (
                candidate.get("mechanism_id")
                if isinstance(candidate, Mapping)
                else None
            )
            if type(mechanism_id) is str:
                covered_counts[mechanism_id] = (
                    covered_counts.get(mechanism_id, 0) + 1
                )
        for idea in ideas:
            mechanism_id = idea.idea.get("mechanism_id")
            if (
                type(mechanism_id) is str
                and covered_counts.get(mechanism_id, 0)
                >= MIN_EXPRESSIONS_PER_IDEA
                and idea.stage == "INSPECT"
                and idea.status not in {
                    "READY",
                    "SIMULATING",
                    "COMPLETED",
                    "ABORTED",
                }
            ):
                self._store.set_research_idea_status(
                    run_id, idea.idea_id, "READY", stage="SIMULATE"
                )
        ideas = self._store.list_research_ideas(
            run_id, plan_version=plan_record.plan_version
        )
        pending = [
            idea
            for idea in ideas
            if not idea.abort_requested
            and idea.stage == "INSPECT"
            and idea.status in {"PENDING_INSPECT", "ERROR"}
        ]
        eligible = [idea for idea in pending if _retry_due(idea.next_retry_at)]
        if not eligible:
            accepted = self._accepted_plan_candidates(
                run_id, plan_record.plan_version, plan_record.plan_hash
            )
            if pending:
                wait_seconds = _retry_wait_seconds(pending)
                return NodeResult(
                    WorkflowNode.I,
                    {
                        "status": "RETRY_WAIT",
                        "accepted": len(accepted),
                        "pending_idea_ids": [item.idea_id for item in pending],
                        "retry_after_seconds": wait_seconds,
                    },
                    next_node=WorkflowNode.I,
                    payload={
                        "accepted": accepted,
                        "new_fingerprints": [],
                        "plan_version": plan_record.plan_version,
                        "plan_hash": plan_record.plan_hash,
                        "retry_after_seconds": wait_seconds,
                    },
                )
            return NodeResult(
                WorkflowNode.I,
                {"accepted": len(accepted), "pending_idea_ids": []},
                next_node=WorkflowNode.J,
                payload={
                    "accepted": accepted,
                    "rejected": [],
                    "new_fingerprints": [],
                    "plan_version": plan_record.plan_version,
                    "plan_hash": plan_record.plan_hash,
                },
            )

        idea = eligible[0]
        mechanism_id = idea.idea.get("mechanism_id")
        if type(mechanism_id) is not str or mechanism_id not in mechanisms:
            raise ResearchError("persisted idea is not present in the locked plan")
        mechanism = mechanisms[mechanism_id]
        attempt = self._store.begin_idea_attempt(run_id, idea.idea_id, "INSPECT")
        accepted: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        task_ids: list[str] = []
        operator_blocked = False
        try:
            existing_count = covered_counts.get(mechanism_id, 0)
            retry_error = idea.last_error
            if 0 < existing_count < MIN_EXPRESSIONS_PER_IDEA:
                retry_error = (
                    f"{UNDERFILLED_IDEA_ERROR} "
                    f"{MIN_EXPRESSIONS_PER_IDEA} validated expressions"
                )
            tasks = self._plan_one_idea(
                plan_record.plan_version,
                plan_record.plan_hash,
                mechanism,
                operators,
                retry_error=retry_error,
                refinement_context=refinement_context,
            )
            for task in tasks:
                durable_count = sum(
                    item["candidate"].get("mechanism_id") == mechanism_id
                    for item in self._accepted_plan_candidates(
                        run_id,
                        plan_record.plan_version,
                        plan_record.plan_hash,
                    )
                )
                remaining_capacity = (
                    MAX_CANDIDATES_PER_OPERATOR_TASK - durable_count
                )
                if remaining_capacity <= 0:
                    break
                task = {
                    **task,
                    "count": min(task["count"], remaining_capacity),
                }
                task_id = self._available_task_id(run_id, task["task_id"])
                task = {**task, "task_id": task_id}
                task_ids.append(task_id)
                self._store.record_operator_task(
                    run_id, task_id, plan_record.plan_version, task
                )
                outcome = self._run_operator_task(
                    run_id,
                    normalized_scope,
                    plan_record.plan_version,
                    plan_record.plan_hash,
                    task,
                    operators,
                    allow_revalidation,
                )
                if outcome.status == "BLOCKED":
                    operator_blocked = True
                    blocked = outcome.result or {
                        "status": "BLOCKED",
                        "reason": "operator task blocked",
                    }
                    self._store.complete_operator_task(
                        run_id, task_id, "BLOCKED", blocked
                    )
                    raise ResearchError(str(blocked["reason"]))
                task_accepted = list(outcome.accepted)
                task_rejected = list(outcome.rejected)
                accepted.extend(task_accepted)
                rejected.extend(task_rejected)
                self._store.complete_operator_task(
                    run_id,
                    task_id,
                    "COMPLETED",
                    outcome.result
                    or {"accepted": task_accepted, "rejected": task_rejected},
                )
            durable = self._accepted_plan_candidates(
                run_id, plan_record.plan_version, plan_record.plan_hash
            )
            idea_candidates = [
                item
                for item in durable
                if item["candidate"].get("mechanism_id") == mechanism_id
            ]
            if not idea_candidates:
                failures = "; ".join(
                    dict.fromkeys(
                        str(item.get("reason", "invalid candidate"))[:200]
                        for item in rejected[-30:]
                    )
                )
                detail = f": {failures}" if failures else ""
                raise ResearchError(
                    f"no research-quality candidate was produced{detail}"
                )
        except Exception as error:
            for task_id in task_ids:
                try:
                    task_record = self._store.get_operator_task(run_id, task_id)
                    if task_record.status == "PENDING":
                        self._store.complete_operator_task(
                            run_id,
                            task_id,
                            "FAILED",
                            {"error": type(error).__name__},
                        )
                except (StoreConflict, StoreRecordNotFound):
                    pass
            current = self._store.get_research_idea(run_id, idea.idea_id)
            error_text = " ".join(str(error).split())[:1000] or type(error).__name__
            if current.abort_requested:
                self._finish_attempt_if_running(
                    attempt,
                    "ABORTED",
                    "ABORTED",
                    detail={"error_type": type(error).__name__},
                    error="aborted by user",
                )
                state = "ABORTED"
                retry_seconds = 0
            else:
                retry_seconds = min(60, 5 * (2 ** min(current.retry_count, 4)))
                self._finish_attempt_if_running(
                    attempt,
                    "FAILED",
                    "ERROR",
                    detail={
                        "error_type": type(error).__name__,
                        "task_ids": task_ids,
                        "accepted": len(accepted),
                        "rejected": len(rejected),
                    },
                    error=error_text,
                    retry_after_seconds=retry_seconds,
                )
                state = "ERROR"
            artifacts = self._write_json(
                run_id,
                WorkflowNode.I,
                f"idea_{_artifact_token(idea.idea_id)}_inspect_{attempt.attempt_number}.json",
                {
                    "idea_id": idea.idea_id,
                    "status": state,
                    "error": error_text,
                    "retry_after_seconds": retry_seconds,
                    "task_ids": task_ids,
                    "accepted": accepted,
                    "rejected": rejected,
                },
            )
            all_accepted = self._accepted_plan_candidates(
                run_id, plan_record.plan_version, plan_record.plan_hash
            )
            other_ready = any(
                item.idea_id != idea.idea_id
                and not item.abort_requested
                and item.stage == "INSPECT"
                and item.status in {"PENDING_INSPECT", "ERROR"}
                and _retry_due(item.next_retry_at)
                for item in self._store.list_research_ideas(
                    run_id, plan_version=plan_record.plan_version
                )
            )
            loop_delay = 0 if other_ready else retry_seconds
            partial_new = [
                item["fingerprint"]
                for item in all_accepted
                if item["fingerprint"] not in known_fingerprints
                and not item.get("current_run_existing")
            ]
            return NodeResult(
                WorkflowNode.I,
                {
                    "idea_id": idea.idea_id,
                    "idea_status": state,
                    "reason": error_text,
                    "accepted": len(all_accepted),
                    "task_ids": task_ids,
                    "pending_mechanism_ids": [mechanism_id]
                    if state != "ABORTED"
                    else [],
                    "retry_after_seconds": loop_delay,
                },
                artifacts,
                next_node=WorkflowNode.I,
                payload={
                    "status": "BLOCKED" if operator_blocked else state,
                    "task_id": task_ids[-1] if task_ids else None,
                    "reason": error_text,
                    "accepted": all_accepted,
                    "rejected": rejected,
                    "new_fingerprints": partial_new,
                    "plan_version": plan_record.plan_version,
                    "plan_hash": plan_record.plan_hash,
                    "retry_after_seconds": loop_delay,
                },
            )

        current = self._store.get_research_idea(run_id, idea.idea_id)
        if current.abort_requested:
            self._finish_attempt_if_running(
                attempt,
                "ABORTED",
                "ABORTED",
                detail={"task_ids": task_ids},
                error="aborted by user",
            )
            all_accepted = self._accepted_plan_candidates(
                run_id, plan_record.plan_version, plan_record.plan_hash
            )
            return NodeResult(
                WorkflowNode.I,
                {"idea_id": idea.idea_id, "idea_status": "ABORTED"},
                next_node=WorkflowNode.I,
                payload={
                    "accepted": all_accepted,
                    "rejected": rejected,
                    "new_fingerprints": [],
                    "plan_version": plan_record.plan_version,
                    "plan_hash": plan_record.plan_hash,
                },
            )
        self._store.finish_idea_attempt(
            attempt,
            "COMPLETED",
            "READY",
            detail={
                "task_ids": task_ids,
                "accepted": len(idea_candidates),
                "rejected": len(rejected),
            },
        )
        accepted = self._accepted_plan_candidates(
            run_id, plan_record.plan_version, plan_record.plan_hash
        )
        new_fingerprints = [
            item["fingerprint"] for item in accepted
            if item["fingerprint"] not in known_fingerprints
            and not item.get("current_run_existing")
        ]
        remaining = [
            item.idea_id
            for item in self._store.list_research_ideas(
                run_id, plan_version=plan_record.plan_version
            )
            if not item.abort_requested
            and item.stage == "INSPECT"
            and item.status in {"PENDING_INSPECT", "ERROR"}
        ]
        artifacts = self._write_json(
            run_id,
            WorkflowNode.I,
            f"idea_{_artifact_token(idea.idea_id)}_inspect_{attempt.attempt_number}.json",
            {
                "plan_version": plan_record.plan_version,
                "plan_hash": plan_record.plan_hash,
                "idea_id": idea.idea_id,
                "status": "READY",
                "task_ids": task_ids,
                "accepted": idea_candidates,
                "rejected": rejected,
            },
        )
        return NodeResult(
            WorkflowNode.I,
            {
                "idea_id": idea.idea_id,
                "idea_status": "READY",
                "accepted": len(accepted),
                "rejected": len(rejected),
                "task_ids": task_ids,
                "pending_idea_ids": remaining,
            },
            artifacts,
            next_node=WorkflowNode.I if remaining else WorkflowNode.J,
            payload={
                "accepted": accepted,
                "rejected": rejected,
                "new_fingerprints": new_fingerprints,
                "plan_version": plan_record.plan_version,
                "plan_hash": plan_record.plan_hash,
            },
        )

    def _plan_one_idea(
        self,
        plan_version: int,
        plan_hash: str,
        mechanism: Mapping[str, Any],
        operators: Mapping[str, Mapping[str, object]],
        *,
        retry_error: str | None,
        refinement_context: Mapping[str, Any] | None,
    ) -> list[dict[str, Any]]:
        mechanism_id = mechanism["mechanism_id"]
        mechanisms = {mechanism_id: mechanism}
        fields = _names(mechanism.get("field_ids"), "mechanism field_ids")
        field_types = _mechanism_field_types(mechanism, fields)
        if retry_error and (
            retry_error.startswith(UNDERFILLED_IDEA_ERROR)
            or retry_error == "process interrupted"
        ):
            return self._fallback_tasks(
                plan_version, plan_hash, mechanisms, operators
            )
        context: dict[str, Any] = {
            "plan_version": plan_version,
            "plan_hash": plan_hash,
            "idea": dict(mechanism),
            "operator_names": sorted(operators),
            "strategy_catalog": strategy_catalog(
                operators, field_count=len(fields), field_types=field_types
            ),
            "field_types": field_types,
            "task_constraints": {
                "mechanism_id": mechanism_id,
                "permitted_fields": sorted(fields),
                "count_per_task_max": MAX_CANDIDATES_PER_OPERATOR_TASK,
                "count_min": 1,
                "count_max": MAX_CANDIDATES_PER_OPERATOR_TASK,
                "total_count_max": MAX_EXPRESSIONS_PER_PLAN,
                "expression_target_min": 4,
                "expression_target_max": MAX_CANDIDATES_PER_OPERATOR_TASK,
                "generation_target": MAX_CANDIDATES_PER_OPERATOR_TASK,
                "strategy_selection": "Every task should select strategy_ids from strategy_catalog; local code expands those abstract templates into concrete expressions.",
                "quality": "temporal, change, relational, group-relative, or conditional",
                "forbidden": "raw fields, rank(field), log(field), and cosmetic-only transforms",
            },
        }
        if retry_error:
            context["validation_failure"] = retry_error
        if refinement_context:
            context["refinement_evidence"] = _compact_refinement_evidence(
                refinement_context, mechanism_id
            )
        try:
            planner = self._invoke(
                ModelRole.PLANNER,
                WorkflowNode.I,
                "Plan expression generation for exactly one research idea. Return tasks only, all bound to the supplied mechanism_id. Every task should include strategy_ids selected from strategy_catalog so local deterministic code can expand abstract templates into concrete expressions. Cover every permitted field across the tasks and target 4 to 10 genuinely distinct expressions. VECTOR fields must be reduced to scalar values with the strategy_catalog vector_reducer before any time-series, cross-sectional, arithmetic, logical, or relational operator. Keep each task small and use only available transform families. Use validation_failure and refinement_evidence, when present, to select materially different templates that address measured backtest weaknesses. Do not include other ideas, unrelated prior run history, concrete FASTEXPR expressions, simulation settings, or workflow routes.",
                context,
            )
            return self._validated_tasks(
                planner.get("candidate_plan"),
                plan_version,
                plan_hash,
                mechanisms,
                operators,
            )
        except (
            ModelError,
            ModelRefusal,
            SchemaViolation,
            ResearchError,
            TypeError,
            ValueError,
        ):
            return self._fallback_tasks(
                plan_version, plan_hash, mechanisms, operators
            )

    def _finish_attempt_if_running(
        self,
        attempt: Any,
        status: str,
        idea_status: str,
        **kwargs: Any,
    ) -> None:
        try:
            self._store.finish_idea_attempt(
                attempt, status, idea_status, **kwargs
            )
        except StoreConflict:
            current = self._store.get_research_idea(attempt.run_id, attempt.idea_id)
            if not current.abort_requested:
                raise

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
        accepted: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        target = task["count"]
        attempts = 0
        operator_status = "COMPLETED"
        strategy_ids = task.get("strategy_ids", [])
        if strategy_ids:
            local_candidates = materialize_strategy_templates(
                operators,
                task["permitted_fields"],
                strategy_ids=strategy_ids,
                limit=target,
                field_types=task.get("field_types", {}),
            )
            for raw in local_candidates:
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
        while (
            len(accepted) < target
            and len(accepted) < MIN_EXPRESSIONS_PER_IDEA
            and attempts < MAX_OPERATOR_GENERATION_ATTEMPTS
        ):
            attempts += 1
            remaining = target - len(accepted)
            excluded = [
                item["candidate"]["expression"]
                for item in accepted
                if isinstance(item.get("candidate"), Mapping)
                and type(item["candidate"].get("expression")) is str
            ]
            request_task = {
                **task,
                "count": remaining,
                "generation_attempt": attempts,
                "excluded_expressions": excluded,
                "validation_failures": rejected[-30:],
            }
            operator = self._invoke(
                ModelRole.OPERATOR,
                WorkflowNode.I,
                "Materialize research-quality FASTEXPR candidates for exactly this one task. Set task_result.status to COMPLETED and return at least one candidate whenever task.permitted_fields and task.transform_families are non-empty; use BLOCKED with a reason only when generation is genuinely impossible. Return exactly task.count distinct candidates whenever the strict field and research-quality rules allow it. Each candidate must include a non-empty expression string, field_id from task.permitted_fields, and single_mechanism set to true. Every expression must test a temporal, change, relational, group-relative, or conditional mechanism. Every VECTOR field declared in task.field_types must appear only as the direct argument of an available vec_* reducer before any other operator. Raw fields, rank(field), log(field), cosmetic-only transforms, and stacked rank/zscore/normalize transforms are forbidden. Multi-field expressions must use only economically justified fields from task.permitted_fields; never introduce an unbound field. Do not repeat task.excluded_expressions. Expressions may use only task.permitted_fields and task.transform_families. If strict validation makes the requested count impossible, return fewer candidates rather than weakening field selection. Return no plan, scope, settings, commands, or additional task.",
                {
                    "plan_version": plan_version,
                    "plan_hash": plan_hash,
                    "task": request_task,
                    "strategy_catalog": strategy_catalog(
                        operators, field_count=len(task["permitted_fields"])
                    ),
                },
            )
            payload = operator.get("task_result")
            if not isinstance(payload, Mapping) or not isinstance(payload.get("payload"), Mapping):
                raise ResearchError("operator candidate task is invalid")
            status = payload.get("status")
            if type(status) is not str:
                raise ResearchError("operator candidate task did not complete")
            status = status.strip().upper()
            if status in {"SUCCESS", "SUCCEEDED"}:
                status = "COMPLETED"
            operator_status = status
            if status == "BLOCKED":
                reason = payload["payload"].get("reason", "operator task blocked")
                if type(reason) is not str or not reason.strip():
                    raise ResearchError("blocked operator task has invalid reason")
                if not accepted:
                    return _OperatorTaskOutcome(
                        "BLOCKED",
                        result={"status": "BLOCKED", "reason": reason.strip()[:512]},
                    )
                break
            if status != "COMPLETED":
                break
            content = payload["payload"]
            if any(key in content for key in ("plan_version", "plan_hash", "scope", "settings", "commands")):
                raise ResearchError("operator cannot modify the locked plan or scope")
            raw_candidates = content.get("candidates")
            if not isinstance(raw_candidates, list) or len(raw_candidates) > remaining:
                raise ResearchError("operator candidate count is invalid")
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
            # A one-candidate task still needs another attempt when the model
            # returns an empty list; otherwise the configured retry budget is
            # silently bypassed for the most reliable fallback task shape.
            if target == 1 and raw_candidates:
                break
        return _OperatorTaskOutcome(
            "COMPLETED",
            tuple(accepted),
            tuple(rejected),
            {
                "status": "COMPLETED",
                "operator_status": operator_status,
                "requested": target,
                "accepted": len(accepted),
                "rejected": len(rejected),
                "locally_materialized": sum(
                    item.get("candidate", {}).get("materialization")
                    == "local_template_expansion"
                    for item in accepted
                    if isinstance(item.get("candidate"), Mapping)
                ),
                "attempts": attempts,
                "shortfall": target - len(accepted),
            },
        )

    def _planner_was_interrupted(self, run_id: str, node: WorkflowNode) -> bool:
        connect = getattr(self._store, "connect", None)
        if not callable(connect):
            return False
        with closing(connect()) as connection:
            rows = connection.execute(
                "SELECT summary_json FROM node_attempts "
                "WHERE run_id=? AND node=? AND status='INTERRUPTED' ORDER BY id DESC",
                (run_id, node.value),
            ).fetchall()
        for row in rows:
            try:
                summary = json.loads(row["summary_json"] or "{}")
            except (json.JSONDecodeError, TypeError):
                continue
            if summary.get("failure") == "planner_unavailable":
                return True
        return False

    def _accepted_plan_candidates(
        self, run_id: str, plan_version: int, plan_hash: str
    ) -> list[dict[str, Any]]:
        records = getattr(self._store, "list_candidates", lambda _run_id: [])(run_id)
        result: list[dict[str, Any]] = []
        for record in records:
            candidate = getattr(record, "candidate", None)
            if (
                getattr(record, "status", None) not in {"ACCEPTED", "REVALIDATED"}
                or not isinstance(candidate, Mapping)
                or candidate.get("plan_version") != plan_version
                or candidate.get("plan_hash") != plan_hash
            ):
                continue
            result.append(
                {
                    "fingerprint": getattr(record, "expression_fingerprint"),
                    "candidate": dict(candidate),
                    "revalidated": getattr(record, "status") == "REVALIDATED",
                }
            )
        return result

    def _covered_mechanism_ids(
        self, run_id: str, plan_version: int, plan_hash: str
    ) -> set[str]:
        return {
            item["candidate"]["mechanism_id"]
            for item in self._accepted_plan_candidates(run_id, plan_version, plan_hash)
            if type(item["candidate"].get("mechanism_id")) is str
        }

    def _available_task_id(self, run_id: str, task_id: str) -> str:
        for suffix in range(1, 10_001):
            candidate = task_id if suffix == 1 else f"{task_id}-{suffix}"
            try:
                self._store.get_operator_task(run_id, candidate)
            except StoreRecordNotFound:
                return candidate
        raise ResearchError("operator task identifier space is exhausted")

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

    def _verified_evidence_bundle(
        self, run_id: str, binding: Mapping[str, Any]
    ) -> tuple[list[dict[str, Any]], set[str]]:
        if not isinstance(binding, Mapping) or set(binding) != {"artifact_id", "sha256"}:
            raise ResearchError("evidence bundle binding is invalid")
        artifact_ref = binding.get("artifact_id")
        bound_hash = binding.get("sha256")
        artifact_id = _artifact_id(artifact_ref, "evidence bundle")
        if (
            type(bound_hash) is not str
            or len(bound_hash) != 64
            or any(character not in "0123456789abcdef" for character in bound_hash)
        ):
            raise ResearchError("evidence bundle hash is invalid")
        try:
            bundle_artifact = self._store.get_artifact(artifact_id)
        except StoreRecordNotFound:
            raise ResearchError("evidence bundle artifact is missing") from None
        if (
            bundle_artifact.run_id != run_id
            or bundle_artifact.node is not WorkflowNode.G
            or bundle_artifact.name != "evidence_lessons.json"
            or bundle_artifact.kind != "json"
            or bundle_artifact.sha256 != bound_hash
        ):
            raise ResearchError("evidence bundle binding does not match its artifact")
        if not callable(getattr(self._artifacts, "read_json", None)):
            raise ResearchError("evidence bundle reader is unavailable")
        try:
            bundle = self._artifacts.read_json(bundle_artifact)
        except Exception:
            raise ResearchError("evidence bundle content is invalid") from None
        if hashlib.sha256(_canonical(bundle).encode("utf-8")).hexdigest() != bound_hash:
            raise ResearchError("evidence bundle is not canonical")
        if type(bundle) is not dict or set(bundle) != {
            "mechanism_keywords", "lessons", "coverage", "missing_sources",
            "per_keyword",
        }:
            raise ResearchError("evidence bundle content is invalid")
        mechanism_keywords = _mechanism_keywords(bundle["mechanism_keywords"])
        trusted_keywords = self._completed_evidence_keywords(run_id)
        if set(mechanism_keywords) != trusted_keywords:
            raise ResearchError(
                "mechanism keywords do not match command provenance"
            )
        raw_lessons = bundle.get("lessons")
        if type(raw_lessons) is not list:
            raise ResearchError("evidence bundle lessons are invalid")
        declared_per_keyword = bundle.get("per_keyword")
        if not isinstance(declared_per_keyword, Mapping):
            raise ResearchError("evidence bundle coverage is invalid")
        if set(declared_per_keyword) != set(mechanism_keywords):
            raise ResearchError("evidence bundle mechanism keywords do not match coverage")
        lessons: list[dict[str, Any]] = []
        references: set[str] = set()
        for lesson in raw_lessons:
            if not isinstance(lesson, Mapping):
                raise ResearchError("evidence lesson is invalid")
            source_class = lesson.get("source_class")
            if source_class not in {
                "community", "official_docs", "platform", "paper"
            }:
                raise ResearchError("evidence lesson has invalid source class")
            for key in ("source_id", "extracted_statement", "applicability"):
                if type(lesson.get(key)) is not str or not lesson[key].strip():
                    raise ResearchError(f"evidence lesson has invalid {key}")
            source_id = lesson["source_id"]
            source_artifact_id = _artifact_id(source_id, "evidence source")
            if source_id in references:
                raise ResearchError("evidence source cannot be reused across lessons")
            try:
                artifact = self._store.get_artifact(source_artifact_id)
            except StoreRecordNotFound:
                raise ResearchError("evidence source artifact is missing") from None
            if (
                artifact.run_id != run_id
                or artifact.node is not WorkflowNode.G
                or artifact.kind != "json"
            ):
                raise ResearchError("evidence source belongs to another run or node")
            self._verify_source_provenance(source_class, artifact, lesson)
            references.add(source_id)
            lessons.append(dict(lesson))
        try:
            per_keyword = keyword_evidence_coverage(
                lessons, mechanism_keywords
            )
        except (EvidenceError, TypeError):
            raise ResearchError("evidence bundle coverage is invalid") from None
        missing_sources = [
            source
            for source in ("community", "official_docs", "platform", "paper")
            if any(source in item["missing_sources"] for item in per_keyword.values())
        ]
        if (
            declared_per_keyword != per_keyword
            or bundle["coverage"] != missing_sources
            or bundle["missing_sources"] != missing_sources
        ):
            raise ResearchError("evidence bundle coverage does not match its lessons")
        required_missing = [
            source for source in REQUIRED_EVIDENCE_CLASSES
            if source in missing_sources
        ]
        if required_missing:
            raise ResearchError(
                "research plan requires evidence coverage: "
                + ", ".join(required_missing)
            )
        return lessons, references

    def _completed_evidence_keywords(self, run_id: str) -> set[str]:
        list_commands = getattr(self._store, "list_completed_commands", None)
        if not callable(list_commands):
            raise ResearchError("evidence command ledger is unavailable")
        keywords: set[str] = set()
        for command in list_commands(run_id, WorkflowNode.G):
            argv = command.argv
            if len(argv) == 3 and argv[:2] == ("community", "search"):
                keywords.add(argv[2])
            elif len(argv) == 2 and argv[:1] == ("search",):
                keywords.add(argv[1])
            elif len(argv) == 4 and argv[:3] == (
                "arxiv", "search", "query"
            ):
                keywords.add(argv[3])
        return keywords

    def _verify_source_provenance(
        self, source_class: str, artifact: Any, lesson: Mapping[str, Any]
    ) -> None:
        expected: dict[str, tuple[str, tuple[str, ...]]] = {
            "community": ("_community_search.json", ("community", "search")),
            "official_docs": ("_docs_show.json", ("docs", "show")),
            "platform": ("_platform_search.json", ("search",)),
            "paper": ("_papers.json", ("arxiv", "search", "query")),
        }
        suffix, prefix = expected[source_class]
        if not artifact.name.endswith(suffix):
            raise ResearchError("evidence source name does not match its source class")
        try:
            command = self._store.get_command_for_artifact(artifact.id)
        except StoreRecordNotFound:
            raise ResearchError("evidence source has no completed command provenance") from None
        if command.run_id != artifact.run_id or command.node is not WorkflowNode.G:
            raise ResearchError("evidence source command belongs to another run or node")
        if command.argv[: len(prefix)] != prefix:
            raise ResearchError("evidence source command does not match its source class")
        applicability = lesson["applicability"]
        expected_name = {
            "community": f"{applicability}_community_search.json",
            "official_docs": f"{applicability}_docs_show.json",
            "platform": f"{applicability}_platform_search.json",
            "paper": f"{applicability}_papers.json",
        }[source_class]
        if artifact.name != expected_name:
            raise ResearchError("evidence source does not match lesson applicability")
        query_index = {"community": 2, "platform": 1, "paper": 3}.get(
            source_class
        )
        if query_index is not None:
            if (
                len(command.argv) <= query_index
                or command.argv[query_index] != applicability
            ):
                raise ResearchError(
                    "evidence applicability does not match source command"
                )
            return
        try:
            source_payload = self._artifacts.read_json(artifact)
            statement = _official_docs_statement(source_payload)
        except Exception:
            raise ResearchError("official docs evidence content is invalid") from None
        if statement != lesson["extracted_statement"]:
            raise ResearchError("official docs lesson does not match source artifact")

    def _validated_tasks(self, value: object, version: int, plan_hash: str, mechanisms: dict[str, Mapping[str, Any]], operators: Mapping[str, Mapping[str, object]]) -> list[dict[str, Any]]:
        if not isinstance(value, Mapping):
            raise ResearchError("candidate plan is invalid")
        raw_tasks = value.get("tasks")
        if not isinstance(raw_tasks, list) or not raw_tasks:
            return self._fallback_tasks(version, plan_hash, mechanisms, operators)
        tasks: list[dict[str, Any]] = []
        total_count = 0
        seen: set[str] = set()
        covered_fields: dict[str, set[str]] = {}
        for task_index, raw in enumerate(raw_tasks, start=1):
            if not isinstance(raw, Mapping):
                raise ResearchError("candidate task is invalid")
            task_id = raw.get("task_id")
            mechanism_id = raw.get("mechanism_id")
            count = raw.get("count")
            if type(task_id) is not str or not task_id.strip():
                task_id = f"task-{task_index}"
            else:
                task_id = task_id.strip()
            if task_id in seen:
                raise ResearchError(f"duplicate task id: {task_id}")
            if type(mechanism_id) is not str or mechanism_id not in mechanisms:
                raise ResearchError("candidate task mechanism is invalid")
            if type(count) is not int or not 1 <= count <= MAX_CANDIDATES_PER_OPERATOR_TASK:
                raise ResearchError(
                    f"candidate task count must be an integer between 1 and {MAX_CANDIDATES_PER_OPERATOR_TASK}"
                )
            total_count += count
            if total_count > MAX_EXPRESSIONS_PER_PLAN:
                raise ResearchError(
                    f"candidate plan total count must not exceed {MAX_EXPRESSIONS_PER_PLAN}"
                )
            permitted = _names(raw.get("permitted_fields"), "permitted_fields")
            allowed = _names(mechanisms[mechanism_id].get("field_ids"), "mechanism field_ids")
            if not permitted or not permitted <= allowed:
                raise ResearchError("candidate task fields exceed mechanism fields")
            families = _names(raw.get("transform_families"), "transform_families")
            task_catalog = strategy_catalog(
                operators,
                field_count=len(permitted),
                field_types=_mechanism_field_types(
                    mechanisms[mechanism_id], permitted
                ),
            )
            available_families = {
                _operator_family(name) for name in operators
            } | {name.lower() for name in operators} | {
                str(item["strategy_family"]) for item in task_catalog
            }
            if not families <= available_families:
                raise ResearchError("candidate task transform family is unavailable")
            raw_strategy_ids = raw.get("strategy_ids", [])
            if not isinstance(raw_strategy_ids, list) or any(
                type(item) is not str or not item.strip()
                for item in raw_strategy_ids
            ):
                raise ResearchError("candidate task strategy ids are invalid")
            strategy_ids = list(dict.fromkeys(item.strip() for item in raw_strategy_ids))
            catalog = {
                item["strategy_id"]: item
                for item in task_catalog
            }
            if any(item not in catalog for item in strategy_ids):
                raise ResearchError("candidate task strategy is unavailable")
            for strategy_id in strategy_ids:
                if any(
                    operator not in families
                    and _operator_family(operator) not in families
                    and catalog[strategy_id]["strategy_family"] not in families
                    for operator in catalog[strategy_id]["required_operators"]
                ):
                    raise ResearchError(
                        "candidate task strategy exceeds transform families"
                    )
                families.update(catalog[strategy_id]["required_operators"])
            task = {"task_id": task_id, "mechanism_id": mechanism_id, "permitted_fields": sorted(permitted), "field_types": _mechanism_field_types(mechanisms[mechanism_id], permitted), "transform_families": sorted(families), "strategy_ids": strategy_ids, "count": count, "plan_version": version, "plan_hash": plan_hash, "quality_gate": _specific_hypothesis(mechanisms[mechanism_id].get("hypothesis"), allowed)}
            tasks.append(task)
            seen.add(task_id)
            covered_fields.setdefault(mechanism_id, set()).update(permitted)
        if set(covered_fields) != set(mechanisms):
            raise ResearchError("candidate plan must cover every mechanism")
        for mechanism_id, mechanism in mechanisms.items():
            required = _names(mechanism.get("field_ids"), "mechanism field_ids")
            if covered_fields[mechanism_id] != required:
                raise ResearchError(
                    f"candidate plan does not cover all fields for mechanism: {mechanism_id}"
                )
        return tasks

    @staticmethod
    def _fallback_tasks(
        version: int,
        plan_hash: str,
        mechanisms: Mapping[str, Mapping[str, Any]],
        operators: Mapping[str, Mapping[str, object]],
    ) -> list[dict[str, Any]]:
        available_families = {
            _operator_family(name) for name in operators
        } | {name.lower() for name in operators}
        preferred_families = (
            "time_series",
            "change",
            "cross_sectional",
            "group",
            "logical",
            "arithmetic",
            "vector",
        )
        family = next(
            (name for name in preferred_families if name in available_families),
            next(iter(sorted(available_families)), None),
        )
        if family is None:
            raise ResearchError("candidate tasks require available operator families")

        selected = list(mechanisms.items())[:MAX_RESEARCH_IDEAS]
        if not selected:
            raise ResearchError("candidate plan requires mechanisms")
        tasks: list[dict[str, Any]] = []
        for mechanism_index, (mechanism_id, mechanism) in enumerate(selected, start=1):
            fields = sorted(_names(mechanism.get("field_ids"), "mechanism field_ids"))
            field_types = _mechanism_field_types(mechanism, set(fields))
            catalog = strategy_catalog(
                operators, field_count=len(fields), field_types=field_types
            )
            if catalog:
                strategy_ids = [str(item["strategy_id"]) for item in catalog]
                required_operators = sorted(
                    {
                        str(operator)
                        for item in catalog
                        for operator in item["required_operators"]
                    }
                )
                tasks.append(
                    {
                        "task_id": f"fallback-{mechanism_index}-templates",
                        "mechanism_id": mechanism_id,
                        "permitted_fields": fields,
                        "field_types": field_types,
                        "transform_families": required_operators,
                        "strategy_ids": strategy_ids,
                        "count": MAX_CANDIDATES_PER_OPERATOR_TASK,
                        "plan_version": version,
                        "plan_hash": plan_hash,
                        "quality_gate": _specific_hypothesis(
                            mechanism.get("hypothesis"), set(fields)
                        ),
                    }
                )
                continue
            for field_index, field in enumerate(fields, start=1):
                tasks.append(
                    {
                        "task_id": f"fallback-{mechanism_index}-{field_index}",
                        "mechanism_id": mechanism_id,
                        "permitted_fields": [field],
                        "field_types": {field: field_types[field]},
                        "transform_families": [family],
                        "strategy_ids": [],
                        "count": 1,
                        "plan_version": version,
                        "plan_hash": plan_hash,
                        "quality_gate": _specific_hypothesis(
                            mechanism.get("hypothesis"), set(fields)
                        ),
                    }
                )
        if not tasks:
            raise ResearchError("candidate plan requires mechanisms")
        return tasks

    def _materialize_candidate(self, run_id: str, scope: dict[str, Any], task: dict[str, Any], raw: object, operators: Mapping[str, Mapping[str, object]], allow_revalidation: bool, accepted: list[dict[str, Any]], rejected: list[dict[str, Any]]) -> None:
        if not isinstance(raw, Mapping):
            self._reject(run_id, raw, "invalid_candidate", rejected)
            return
        try:
            validated = validate_candidate(raw, allowed_fields=task["permitted_fields"], banned_fields=set(), operators=operators, field_types=task.get("field_types", {}))
            strategy = (
                validate_research_strategy(validated)
                if task.get("quality_gate") is True
                else profile_research_strategy(validated)
            )
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
        record = {
            "expression": validated.canonical_expression,
            "field_id": raw["field_id"],
            "single_mechanism": True,
            "plan_version": task["plan_version"],
            "plan_hash": task["plan_hash"],
            "mechanism_id": task["mechanism_id"],
            **strategy.as_dict(),
        }
        for key in (
            "strategy_id",
            "expression_template",
            "field_bindings",
            "materialization",
        ):
            if key in raw:
                record[key] = raw[key]
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
        return self._store.has_experience_fingerprint(
            scope["region"], scope["delay"], scope["category"], fingerprint
        )

    def _reject(self, run_id: str, raw: object, reason: str, rejected: list[dict[str, Any]], *, fingerprint: str | None = None) -> None:
        raw_candidate = dict(raw) if isinstance(raw, Mapping) else {"raw": repr(raw)}
        rendered = _canonical(raw_candidate)
        diagnostic_fingerprint = fingerprint or hashlib.sha256(
            rendered.encode("utf-8")
        ).hexdigest()
        normalized_reason = reason[:512]
        rejection_identity = hashlib.sha256(
            _canonical(
                {"raw_candidate": raw_candidate, "reason": normalized_reason}
            ).encode("utf-8")
        ).hexdigest()
        persistence_key = f"rejected:{rejection_identity}"
        record = {
            "raw_candidate": raw_candidate,
            "expression_fingerprint": diagnostic_fingerprint,
            "rejection_identity": rejection_identity,
        }
        self._store.add_candidate(
            run_id,
            persistence_key,
            record,
            status="REJECTED",
            reason=normalized_reason,
        )
        rejected.append(
            {
                "fingerprint": diagnostic_fingerprint,
                "reason": normalized_reason,
                "expression": (
                    raw.get("expression")
                    if isinstance(raw, Mapping)
                    and type(raw.get("expression")) is str
                    else None
                ),
            }
        )

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


def _mechanism_field_types(
    mechanism: Mapping[str, Any], fields: set[str]
) -> dict[str, str]:
    raw = mechanism.get("field_types", {})
    if raw is None:
        raw = {}
    if not isinstance(raw, Mapping):
        raise ResearchError("mechanism field_types must be an object")
    result: dict[str, str] = {}
    for field in sorted(fields):
        value = raw.get(field, "MATRIX")
        if type(value) is not str or not value.strip():
            raise ResearchError(f"mechanism field type is invalid: {field}")
        result[field] = value.strip().upper()
    return result


def _validated_field_bindings(
    value: object,
    *,
    fields: set[str],
    mechanism_evidence: set[str],
    resolvable_evidence: set[str],
) -> list[dict[str, object]]:
    if not isinstance(value, list) or not value:
        raise ResearchError("mechanism requires field_bindings")
    bindings: list[dict[str, object]] = []
    bound_fields: set[str] = set()
    expected_keys = {"field_id", "role", "rationale", "evidence_refs"}
    for binding in value:
        if not isinstance(binding, Mapping) or set(binding) != expected_keys:
            raise ResearchError("field binding shape is invalid")
        field_id = binding.get("field_id")
        if type(field_id) is not str or not field_id.strip():
            raise ResearchError("field binding id is invalid")
        field_id = field_id.strip().lower()
        if field_id not in fields:
            raise ResearchError(f"field binding is not declared by mechanism: {field_id}")
        if field_id in bound_fields:
            raise ResearchError(f"duplicate field binding: {field_id}")
        role = binding.get("role")
        if type(role) is not str or role.strip().lower() not in _FIELD_ROLES:
            raise ResearchError(f"field binding role is invalid: {field_id}")
        rationale = binding.get("rationale")
        if type(rationale) is not str or len(rationale.strip()) < 20:
            raise ResearchError(f"field binding rationale is insufficient: {field_id}")
        references = _evidence_refs(binding.get("evidence_refs"))
        if not references <= mechanism_evidence:
            raise ResearchError(
                f"field binding evidence is not declared by mechanism: {field_id}"
            )
        if not references <= resolvable_evidence:
            raise ResearchError(f"field binding evidence is not resolvable: {field_id}")
        bindings.append(
            {
                "field_id": field_id,
                "role": role.strip().lower(),
                "rationale": rationale.strip(),
                "evidence_refs": sorted(references),
            }
        )
        bound_fields.add(field_id)
    if bound_fields != fields:
        missing = sorted(fields - bound_fields)
        extra = sorted(bound_fields - fields)
        detail = missing[0] if missing else extra[0]
        raise ResearchError(f"field bindings do not exactly cover mechanism fields: {detail}")
    return sorted(bindings, key=lambda item: str(item["field_id"]))


def _evidence_refs(values: object) -> set[str]:
    names = _names(values, "evidence_refs")
    if any(not value.startswith("artifact:") for value in names):
        raise ResearchError("evidence_refs must be artifact references")
    return names


def _artifact_id(value: object, label: str) -> int:
    if type(value) is not str or not value.startswith("artifact:"):
        raise ResearchError(f"{label} artifact reference is invalid")
    raw_id = value.removeprefix("artifact:")
    if not raw_id.isdigit() or int(raw_id) <= 0:
        raise ResearchError(f"{label} artifact reference is invalid")
    return int(raw_id)


def _mechanism_keywords(value: object) -> tuple[str, ...]:
    if type(value) is not list or not value or len(value) > 8:
        raise ResearchError("evidence bundle mechanism keywords are invalid")
    keywords: list[str] = []
    for keyword in value:
        if type(keyword) is not str or keyword != keyword.strip().lower():
            raise ResearchError("evidence bundle mechanism keywords are invalid")
        if not keyword or keyword in keywords:
            raise ResearchError("evidence bundle mechanism keywords are invalid")
        keywords.append(keyword)
    return tuple(keywords)


def _specific_hypothesis(value: object, fields: set[str]) -> bool:
    if type(value) is not str or len(value.strip()) < 40 or not fields:
        return False
    normalized = " ".join(value.lower().split())
    generic_fragments = (
        "may provide stable cross-sectional information",
        "may contain useful information",
        "evaluate each locked candidate field",
        "test whether the field works",
    )
    return not any(fragment in normalized for fragment in generic_fragments)


def _official_docs_statement(payload: object) -> str:
    if not isinstance(payload, Mapping) or payload.get("ok") is not True:
        raise ResearchError("official docs evidence content is invalid")
    body = {key: value for key, value in payload.items() if key != "ok"}
    rows: list[Mapping[str, Any]] = []
    for key in ("results", "items", "alphas", "fields", "files", "documents"):
        value = body.get(key)
        if isinstance(value, list) and all(isinstance(item, Mapping) for item in value):
            rows = list(value)
            break
    row = rows[0] if rows else body
    statement = row.get(
        "extracted_statement",
        row.get("text", row.get("summary", row.get("title"))),
    )
    if type(statement) is not str or not statement.strip():
        raise ResearchError("official docs evidence content is invalid")
    return statement.strip()[:2_000]


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


def _compact_refinement_evidence(
    value: Mapping[str, Any], mechanism_id: str | None
) -> dict[str, object]:
    result: dict[str, object] = {}
    if mechanism_id is not None:
        result["mechanism_id"] = mechanism_id
    diagnosis = value.get("diagnosis")
    if isinstance(diagnosis, Mapping):
        compact_diagnosis = {
            key: diagnosis[key]
            for key in ("failure_class", "next_node")
            if type(diagnosis.get(key)) is str
            and 0 < len(str(diagnosis[key])) <= 128
        }
        evidence_ids = diagnosis.get("evidence_ids")
        if isinstance(evidence_ids, list):
            compact_diagnosis["evidence_ids"] = [
                item
                for item in evidence_ids[:8]
                if type(item) is str and 0 < len(item) <= 128
            ]
        if compact_diagnosis:
            result["diagnosis"] = compact_diagnosis

    density = value.get("template_density")
    if isinstance(density, Mapping):
        compact_density: dict[str, dict[str, object]] = {}
        for template_id, item in sorted(density.items(), key=lambda pair: str(pair[0]))[:16]:
            if type(template_id) is not str or not isinstance(item, Mapping):
                continue
            compact_density[template_id[:128]] = {
                key: item[key]
                for key in (
                    "template_id",
                    "template_type",
                    "strategy_family",
                    "tested",
                    "promising",
                    "passed",
                    "factor_density",
                    "pass_rate",
                )
                if _compact_scalar(item.get(key))
            }
        if compact_density:
            result["template_density"] = compact_density

    anti_patterns = value.get("anti_patterns")
    if isinstance(anti_patterns, list):
        compact_patterns = [
            {
                key: item[key]
                for key in ("code", "template_id", "tested", "action")
                if _compact_scalar(item.get(key))
            }
            for item in anti_patterns[:16]
            if isinstance(item, Mapping)
        ]
        if compact_patterns:
            result["anti_patterns"] = compact_patterns

    metrics = value.get("metrics")
    if isinstance(metrics, list):
        failure_counts: dict[str, int] = {}
        representatives: list[dict[str, object]] = []
        for item in metrics:
            if not isinstance(item, Mapping):
                continue
            failures = item.get("failures")
            compact_failures = [
                failure[:128]
                for failure in failures[:16]
                if type(failure) is str and failure
            ] if isinstance(failures, list) else []
            for failure in compact_failures:
                failure_counts[failure] = failure_counts.get(failure, 0) + 1
            raw_metrics = item.get("metrics")
            raw_metrics = raw_metrics if isinstance(raw_metrics, Mapping) else {}
            representative = {
                key: item[key]
                for key in (
                    "alpha_id",
                    "template_id",
                    "template_type",
                    "strategy_family",
                )
                if _compact_scalar(item.get(key))
            }
            representative.update(
                {
                    key: raw_metrics[key]
                    for key in ("sharpe", "fitness", "turnover", "margin")
                    if _compact_number(raw_metrics.get(key))
                }
            )
            representative["failures"] = compact_failures
            representatives.append(representative)
        representatives.sort(
            key=lambda item: float(item.get("sharpe", float("-inf"))),
            reverse=True,
        )
        result["metric_summary"] = {
            "tested": len(representatives),
            "failure_counts": dict(sorted(failure_counts.items())),
            "representative_metrics": representatives[:3],
        }
    return result


def _compact_scalar(value: object) -> bool:
    if type(value) is str:
        return 0 < len(value) <= 128
    if type(value) is int:
        return True
    return type(value) is float and isfinite(value)


def _compact_number(value: object) -> bool:
    return type(value) in {int, float} and isfinite(float(value))


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _retry_due(value: str | None) -> bool:
    if value is None:
        return True
    try:
        due = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return True
    return due <= datetime.now(timezone.utc)


def _retry_wait_seconds(ideas: list[Any]) -> int:
    waits: list[float] = []
    now = datetime.now(timezone.utc)
    for idea in ideas:
        value = getattr(idea, "next_retry_at", None)
        if type(value) is not str:
            return 1
        try:
            due = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return 1
        waits.append(max(0.0, (due - now).total_seconds()))
    return max(1, min(60, int(min(waits, default=0.0)) + 1))


def _artifact_token(value: str) -> str:
    token = "".join(character if character.isalnum() else "_" for character in value)
    token = token.strip("_")[:48]
    return token or hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


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
