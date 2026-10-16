from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from .freeze import ResearchFreeze, require_research_freeze
from .plan import RealityCheckSpec, RealityPlanAssessment, assess_wind_reality_plan
from .provenance import canonical_json, utc_now_iso
from .providers.wind import (
    WIND_PROVIDER_NAME,
    WindOutcomeUnknownError,
    WindResponseError,
    WindRuntime,
    WindRuntimeError,
)
from .store import EvidenceStore


class WindPlanExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExecutableRealityCheck:
    check_id: str
    mechanism_id: str
    node: str
    purpose: str
    server_type: str
    tool_name: str
    params: Mapping[str, Any]
    cost_profile_key: str | None = None
    allow_expensive_fallback: bool = False
    fallback_reason: str | None = None
    entity_ids: Mapping[str, str] | None = None
    as_of: str | None = None
    period: Mapping[str, str] | None = None
    supports: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.check_id.strip():
            raise ValueError("check_id must be non-empty")
        if not isinstance(self.params, Mapping):
            raise ValueError("params must be a JSON mapping")

    @property
    def spec(self) -> RealityCheckSpec:
        return RealityCheckSpec(
            mechanism_id=self.mechanism_id,
            node=self.node,
            purpose=self.purpose,
            server_type=self.server_type,
            tool_name=self.tool_name,
            cost_profile_key=self.cost_profile_key,
            allow_expensive_fallback=self.allow_expensive_fallback,
            fallback_reason=self.fallback_reason,
        )

    def identity_payload(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "mechanism_id": self.mechanism_id,
            "node": self.node,
            "purpose": self.purpose,
            "server_type": self.server_type,
            "tool_name": self.tool_name,
            "cost_profile_key": self.cost_profile_key,
            "allow_expensive_fallback": self.allow_expensive_fallback,
            "fallback_reason": self.fallback_reason,
            "params": dict(self.params),
            "entity_ids": dict(self.entity_ids or {}),
            "as_of": self.as_of,
            "period": dict(self.period or {}),
            "supports": list(self.supports),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class WindPlanExecutionReport:
    ok: bool
    run_id: str
    plan_id: str
    status: str
    assessment: RealityPlanAssessment | None
    completed: tuple[tuple[str, str], ...]
    skipped: tuple[str, ...]
    blocked_check_id: str | None = None
    reason: str | None = None
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "run_id": self.run_id,
            "plan_id": self.plan_id,
            "status": self.status,
            "assessment": (
                {
                    "call_count": self.assessment.call_count,
                    "mechanism_count": self.assessment.mechanism_count,
                    "estimated_p95": self.assessment.estimated_p95,
                    "query_counts": dict(self.assessment.query_counts),
                    "budget": self.assessment.budget.__dict__,
                }
                if self.assessment is not None
                else None
            ),
            "completed": [
                {"check_id": check_id, "evidence_id": evidence_id}
                for check_id, evidence_id in self.completed
            ],
            "skipped": list(self.skipped),
            "blocked_check_id": self.blocked_check_id,
            "reason": self.reason,
            "detail": self.detail,
        }


def load_executable_checks(payload: Mapping[str, Any]) -> list[ExecutableRealityCheck]:
    raw_checks = payload.get("checks") or ()
    if not isinstance(raw_checks, Sequence) or isinstance(raw_checks, (str, bytes)):
        raise ValueError("checks must be a JSON array")
    result: list[ExecutableRealityCheck] = []
    ids: set[str] = set()
    for index, item in enumerate(raw_checks, 1):
        if not isinstance(item, Mapping):
            raise ValueError(f"checks[{index}] must be a JSON object")
        check_id = str(item.get("check_id") or f"check-{index:02d}")
        if check_id in ids:
            raise ValueError(f"duplicate check_id: {check_id}")
        ids.add(check_id)
        params = item.get("params") or {}
        if not isinstance(params, Mapping):
            raise ValueError(f"checks[{index}].params must be a JSON object")
        entity_ids = item.get("entity_ids") or {}
        period = item.get("period") or {}
        if not isinstance(entity_ids, Mapping) or not isinstance(period, Mapping):
            raise ValueError(f"checks[{index}] entity_ids/period must be JSON objects")
        result.append(
            ExecutableRealityCheck(
                check_id=check_id,
                mechanism_id=str(item["mechanism_id"]),
                node=str(item["node"]),
                purpose=str(item["purpose"]),
                server_type=str(item["server_type"]),
                tool_name=str(item["tool_name"]),
                params=dict(params),
                cost_profile_key=(
                    str(item["cost_profile_key"])
                    if item.get("cost_profile_key") is not None
                    else None
                ),
                allow_expensive_fallback=bool(item.get("allow_expensive_fallback", False)),
                fallback_reason=(
                    str(item["fallback_reason"])
                    if item.get("fallback_reason") is not None
                    else None
                ),
                entity_ids={str(k): str(v) for k, v in entity_ids.items()},
                as_of=str(item["as_of"]) if item.get("as_of") is not None else None,
                period={str(k): str(v) for k, v in period.items()},
                supports=tuple(str(value) for value in item.get("supports") or ()),
                limitations=tuple(str(value) for value in item.get("limitations") or ()),
            )
        )
    if not result:
        raise ValueError("checks must contain at least one item")
    purposes = {item.purpose for item in result}
    if len(purposes) != 1:
        raise ValueError("one executable plan cannot mix research and diagnosis purposes")
    return result


def plan_identity(
    checks: Sequence[ExecutableRealityCheck],
    *,
    freeze_manifest_sha256: str | None = None,
) -> str:
    check_payload = [item.identity_payload() for item in checks]
    payload: Any
    if freeze_manifest_sha256 is None:
        # Preserve the historical identity for diagnosis plans, which do not
        # consume the paired-research freeze gate.
        payload = check_payload
    else:
        payload = {
            "checks": check_payload,
            "freeze_manifest_sha256": freeze_manifest_sha256,
        }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()[:20]


def _research_mechanism_ids(checks: Sequence[ExecutableRealityCheck]) -> tuple[str, ...]:
    return tuple(
        sorted({check.mechanism_id for check in checks if check.node.upper() in {"G", "H"}})
    )


def execute_wind_plan(
    *,
    store: EvidenceStore,
    run_id: str,
    checks: Sequence[ExecutableRealityCheck],
    available_points: float,
    profiles: Mapping[str, Any],
    runtime: WindRuntime,
    research_freeze: ResearchFreeze | None = None,
) -> WindPlanExecutionReport:
    if not run_id.strip():
        raise ValueError("run_id must be non-empty")
    research_mechanisms = _research_mechanism_ids(checks)
    if research_mechanisms:
        research_freeze = require_research_freeze(
            research_freeze,
            run_id=run_id,
            mechanism_ids=research_mechanisms,
        )
    pid = plan_identity(
        checks,
        freeze_manifest_sha256=(
            research_freeze.manifest_sha256 if research_freeze is not None else None
        ),
    )
    store.save_run_plan(
        run_id=run_id,
        plan_id=pid,
        payload={
            "run_id": run_id,
            "plan_id": pid,
            "checks": [item.identity_payload() for item in checks],
            "freeze_manifest_sha256": (
                research_freeze.manifest_sha256 if research_freeze is not None else None
            ),
            "freeze_manifest_path": (
                str(research_freeze.manifest_path) if research_freeze is not None else None
            ),
        },
    )

    completed: list[tuple[str, str]] = []
    skipped: list[str] = []
    pending: list[ExecutableRealityCheck] = []
    states = _journal_states(store.load_run_events(run_id=run_id, plan_id=pid))
    for check in checks:
        state = states.get(check.check_id)
        if state is None:
            pending.append(check)
            continue
        event = state["event"]
        if event == "completed":
            evidence_id = str(state["evidence_id"])
            store.load_record(WIND_PROVIDER_NAME, evidence_id)
            completed.append((check.check_id, evidence_id))
            skipped.append(check.check_id)
            continue
        if event in {"started", "outcome_unknown"}:
            return WindPlanExecutionReport(
                ok=False,
                run_id=run_id,
                plan_id=pid,
                status="outcome_unknown",
                assessment=None,
                completed=tuple(completed),
                skipped=tuple(skipped),
                blocked_check_id=check.check_id,
                reason="outcome_unknown_requires_authoritative_readback",
                detail=str(state.get("detail") or "previous call has no authoritative terminal result"),
            )
        if event in {"provider_error", "runtime_error"}:
            return WindPlanExecutionReport(
                ok=False,
                run_id=run_id,
                plan_id=pid,
                status="prior_failure",
                assessment=None,
                completed=tuple(completed),
                skipped=tuple(skipped),
                blocked_check_id=check.check_id,
                reason=event,
                detail=str(state.get("detail") or state.get("message") or "previous plan attempt failed"),
            )
        pending.append(check)

    if not pending:
        return WindPlanExecutionReport(
            ok=True,
            run_id=run_id,
            plan_id=pid,
            status="completed",
            assessment=None,
            completed=tuple(completed),
            skipped=tuple(skipped),
        )

    assessment = assess_wind_reality_plan(
        [item.spec for item in pending],
        profiles=profiles,
        available_points=available_points,
    )
    if not assessment.budget.allowed:
        return WindPlanExecutionReport(
            ok=False,
            run_id=run_id,
            plan_id=pid,
            status="budget_blocked",
            assessment=assessment,
            completed=tuple(completed),
            skipped=tuple(skipped),
            reason="budget_blocked",
        )

    status = runtime.status()
    if not status.available or status.provider_contract_version is None:
        return WindPlanExecutionReport(
            ok=False,
            run_id=run_id,
            plan_id=pid,
            status="runtime_blocked",
            assessment=assessment,
            completed=tuple(completed),
            skipped=tuple(skipped),
            reason=status.reason,
        )
    store.lock_provider_contract(
        run_id=run_id,
        provider=WIND_PROVIDER_NAME,
        contract_version=status.provider_contract_version,
    )
    locked = store.read_provider_lock(run_id=run_id, provider=WIND_PROVIDER_NAME)
    if locked != status.provider_contract_version:
        raise WindPlanExecutionError("provider lock readback mismatch")
    runtime.expected_contract_version = locked

    store.append_run_event(
        run_id=run_id,
        plan_id=pid,
        event={
            "event": "plan_admitted",
            "timestamp": utc_now_iso(),
            "available_points": available_points,
            "pending_check_ids": [item.check_id for item in pending],
            "estimated_p95": assessment.estimated_p95,
            "purpose": assessment.budget.purpose,
            "provider_contract_version": locked,
            "freeze_manifest_sha256": (
                research_freeze.manifest_sha256 if research_freeze is not None else None
            ),
        },
    )

    for check in pending:
        request_hash = hashlib.sha256(
            canonical_json(check.identity_payload()).encode("utf-8")
        ).hexdigest()
        store.append_run_event(
            run_id=run_id,
            plan_id=pid,
            event={
                "event": "started",
                "check_id": check.check_id,
                "request_hash": request_hash,
                "timestamp": utc_now_iso(),
                "provider_contract_version": locked,
            },
        )
        try:
            result = runtime.call(
                node=check.node,
                purpose=check.purpose,
                server_type=check.server_type,
                tool_name=check.tool_name,
                params=dict(check.params),
                entity_ids=dict(check.entity_ids or {}),
                as_of=check.as_of,
                period=dict(check.period or {}),
                supports=check.supports,
                limitations=check.limitations,
            )
        except WindResponseError as exc:
            store.append_run_event(
                run_id=run_id,
                plan_id=pid,
                event={
                    "event": "provider_error",
                    "check_id": check.check_id,
                    "code": exc.code,
                    "message": exc.message,
                    "timestamp": utc_now_iso(),
                },
            )
            return WindPlanExecutionReport(
                ok=False,
                run_id=run_id,
                plan_id=pid,
                status="provider_error",
                assessment=assessment,
                completed=tuple(completed),
                skipped=tuple(skipped),
                blocked_check_id=check.check_id,
                reason=exc.code,
                detail=exc.message,
            )
        except WindOutcomeUnknownError as exc:
            store.append_run_event(
                run_id=run_id,
                plan_id=pid,
                event={
                    "event": "outcome_unknown",
                    "check_id": check.check_id,
                    "detail": str(exc),
                    "timestamp": utc_now_iso(),
                },
            )
            return WindPlanExecutionReport(
                ok=False,
                run_id=run_id,
                plan_id=pid,
                status="outcome_unknown",
                assessment=assessment,
                completed=tuple(completed),
                skipped=tuple(skipped),
                blocked_check_id=check.check_id,
                reason="outcome_unknown_requires_authoritative_readback",
                detail=str(exc),
            )
        except WindRuntimeError as exc:
            store.append_run_event(
                run_id=run_id,
                plan_id=pid,
                event={
                    "event": "runtime_error",
                    "check_id": check.check_id,
                    "detail": str(exc),
                    "timestamp": utc_now_iso(),
                },
            )
            return WindPlanExecutionReport(
                ok=False,
                run_id=run_id,
                plan_id=pid,
                status="runtime_error",
                assessment=assessment,
                completed=tuple(completed),
                skipped=tuple(skipped),
                blocked_check_id=check.check_id,
                reason="runtime_error",
                detail=str(exc),
            )

        path = store.save_record(result.record)
        store.append_run_event(
            run_id=run_id,
            plan_id=pid,
            event={
                "event": "completed",
                "check_id": check.check_id,
                "evidence_id": result.record.evidence_id,
                "stored_path": str(path),
                "timestamp": utc_now_iso(),
            },
        )
        completed.append((check.check_id, result.record.evidence_id))

    if not any(event.get("event") == "plan_completed" for event in store.load_run_events(run_id=run_id, plan_id=pid)):
        store.append_run_event(
            run_id=run_id,
            plan_id=pid,
            event={
                "event": "plan_completed",
                "timestamp": utc_now_iso(),
                "evidence_ids": [evidence_id for _, evidence_id in completed],
            },
        )
    return WindPlanExecutionReport(
        ok=True,
        run_id=run_id,
        plan_id=pid,
        status="completed",
        assessment=assessment,
        completed=tuple(completed),
        skipped=tuple(skipped),
    )


def _journal_states(events: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    states: dict[str, Mapping[str, Any]] = {}
    for event in events:
        check_id = event.get("check_id")
        if check_id is None:
            continue
        states[str(check_id)] = event
    return states


def summarize_wind_plan(
    *,
    store: EvidenceStore,
    run_id: str,
    checks: Sequence[ExecutableRealityCheck],
    research_freeze: ResearchFreeze | None = None,
) -> dict[str, Any]:
    research_mechanisms = _research_mechanism_ids(checks)
    if research_mechanisms:
        research_freeze = require_research_freeze(
            research_freeze,
            run_id=run_id,
            mechanism_ids=research_mechanisms,
        )
    pid = plan_identity(
        checks,
        freeze_manifest_sha256=(
            research_freeze.manifest_sha256 if research_freeze is not None else None
        ),
    )
    events = store.load_run_events(run_id=run_id, plan_id=pid)
    states = _journal_states(events)
    completed: list[dict[str, str]] = []
    pending: list[str] = []
    blocked: list[dict[str, str]] = []
    for check in checks:
        state = states.get(check.check_id)
        if state is None:
            pending.append(check.check_id)
            continue
        event = str(state.get("event"))
        if event == "completed":
            evidence_id = str(state.get("evidence_id") or "")
            try:
                store.load_record(WIND_PROVIDER_NAME, evidence_id)
            except Exception as exc:
                blocked.append(
                    {
                        "check_id": check.check_id,
                        "state": "evidence_verification_failed",
                        "detail": str(exc),
                    }
                )
            else:
                completed.append(
                    {
                        "check_id": check.check_id,
                        "evidence_id": evidence_id,
                        "stored_path": str(
                            store.records_root
                            / WIND_PROVIDER_NAME
                            / f"{evidence_id}.json"
                        ),
                    }
                )
            continue
        if event in {"started", "outcome_unknown"}:
            blocked.append(
                {
                    "check_id": check.check_id,
                    "state": "outcome_unknown",
                    "detail": str(state.get("detail") or "request has no authoritative terminal result"),
                }
            )
            continue
        if event in {"provider_error", "runtime_error"}:
            blocked.append(
                {
                    "check_id": check.check_id,
                    "state": event,
                    "detail": str(state.get("detail") or state.get("message") or ""),
                }
            )
            continue
        pending.append(check.check_id)
    return {
        "ok": not blocked,
        "run_id": run_id,
        "plan_id": pid,
        "freeze_manifest_sha256": (
            research_freeze.manifest_sha256 if research_freeze is not None else None
        ),
        "provider_contract_version": store.read_provider_lock(
            run_id=run_id, provider=WIND_PROVIDER_NAME
        ),
        "completed": completed,
        "pending": pending,
        "blocked": blocked,
        "can_resume": not blocked and bool(pending),
        "is_complete": not blocked and not pending and len(completed) == len(checks),
        "event_count": len(events),
    }
