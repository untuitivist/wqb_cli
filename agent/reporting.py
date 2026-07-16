from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

from .types import WorkflowNode


class ReportingError(ValueError):
    """Raised when a final report cannot define one immutable approval subject."""


@dataclass(frozen=True)
class WrittenFinalReport:
    json_artifact: Any
    markdown_artifact: Any
    approval_subject: dict[str, str]


def _canonical_json(report: Mapping[str, object]) -> str:
    if not isinstance(report, Mapping):
        raise TypeError("report must be a mapping")
    try:
        return json.dumps(
            dict(report),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError):
        raise ReportingError("report must contain only finite JSON values") from None


def canonical_report_hash(report: Mapping[str, object]) -> str:
    return hashlib.sha256(_canonical_json(report).encode("utf-8")).hexdigest()


def _snapshot(value: object, name: str) -> Any:
    try:
        return json.loads(
            json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    except (TypeError, ValueError):
        raise ReportingError(f"{name} must contain only finite JSON values") from None


def build_final_report(
    *,
    run_id: str,
    run_config: Mapping[str, object],
    scope: Mapping[str, object],
    plan_version: int,
    plan_hash: str,
    candidate: Mapping[str, object],
    checks: Sequence[object],
    evidence_refs: Sequence[str],
    route_history: Sequence[object],
    budgets: Mapping[str, object],
    role_usage: Mapping[str, object],
    terminal_recommendation: Mapping[str, object],
) -> dict[str, object]:
    if type(run_id) is not str or not run_id.strip():
        raise ReportingError("run_id must be a nonblank string")
    if type(plan_version) is not int or plan_version <= 0:
        raise ReportingError("plan_version must be a positive integer")
    if type(plan_hash) is not str or not plan_hash.strip():
        raise ReportingError("plan_hash must be a nonblank string")
    if any(type(ref) is not str or not ref.strip() for ref in evidence_refs):
        raise ReportingError("evidence_refs must contain nonblank strings")
    return {
        "run_id": run_id,
        "run_config": _snapshot(run_config, "run_config"),
        "scope": _snapshot(scope, "scope"),
        "plan": {"version": plan_version, "hash": plan_hash},
        "candidate": _snapshot(candidate, "candidate"),
        "checks": _snapshot(list(checks), "checks"),
        "evidence_refs": _snapshot(list(evidence_refs), "evidence_refs"),
        "route_history": _snapshot(list(route_history), "route_history"),
        "budgets": _snapshot(budgets, "budgets"),
        "role_usage": _snapshot(role_usage, "role_usage"),
        "terminal_recommendation": _snapshot(
            terminal_recommendation, "terminal_recommendation"
        ),
    }


def _recommended_alpha_id(report: Mapping[str, object]) -> str:
    recommendation = report.get("terminal_recommendation")
    alpha_id = (
        recommendation.get("alpha_id")
        if isinstance(recommendation, Mapping)
        else None
    )
    if type(alpha_id) is not str or not alpha_id.strip():
        raise ReportingError("terminal recommendation must identify one alpha_id")
    return alpha_id


def _render_markdown(report: Mapping[str, object], report_hash: str) -> str:
    recommendation = report["terminal_recommendation"]
    decision = recommendation.get("decision", "UNKNOWN")
    alpha_id = _recommended_alpha_id(report)
    plan = report["plan"]
    return (
        "# Final Report\n\n"
        f"- Run: `{report['run_id']}`\n"
        f"- Recommendation: `{decision}`\n"
        f"- Alpha: `{alpha_id}`\n"
        f"- Plan: version `{plan['version']}`, hash `{plan['hash']}`\n"
        f"- Report hash: `{report_hash}`\n\n"
        "## Report Data\n\n"
        "```json\n"
        f"{json.dumps(dict(report), ensure_ascii=False, sort_keys=True, indent=2)}\n"
        "```\n"
    )


def write_final_report(
    artifact_writer: Any, run_id: str, report: Mapping[str, object]
) -> WrittenFinalReport:
    if report.get("run_id") != run_id:
        raise ReportingError("report run_id does not match artifact run_id")
    snapshot = json.loads(_canonical_json(report))
    report_hash = canonical_report_hash(snapshot)
    alpha_id = _recommended_alpha_id(snapshot)
    json_artifact = artifact_writer.write_json(
        run_id, WorkflowNode.M, "final_report.json", snapshot
    )
    markdown_artifact = artifact_writer.write_markdown(
        run_id,
        WorkflowNode.M,
        "final_report.md",
        _render_markdown(snapshot, report_hash),
    )
    return WrittenFinalReport(
        json_artifact=json_artifact,
        markdown_artifact=markdown_artifact,
        approval_subject={
            "run_id": run_id,
            "recommended_alpha_id": alpha_id,
            "report_hash": report_hash,
        },
    )
