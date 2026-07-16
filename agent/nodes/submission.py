from __future__ import annotations

import json
from typing import Any, Mapping

from ..reporting import canonical_report_hash
from ..store import StoreConflict
from ..types import NodeResult, RunState, WorkflowNode


class ApprovalMismatch(ValueError):
    """Raised before submission when the human decision does not match the report."""


class SubmissionFailed(RuntimeError):
    """Raised when the platform returns a definite submission failure."""


class SubmissionUncertain(RuntimeError):
    """Raised when a submission may have reached the platform."""


def _recommended_alpha_id(report: Mapping[str, object]) -> str:
    recommendation = report.get("terminal_recommendation")
    alpha_id = (
        recommendation.get("alpha_id")
        if isinstance(recommendation, Mapping)
        else None
    )
    if type(alpha_id) is not str or not alpha_id.strip():
        raise ApprovalMismatch("final report has no recommended alpha")
    return alpha_id


class SubmissionNode:
    def __init__(self, *, runner: Any, store: Any) -> None:
        if runner is None:
            raise TypeError("runner must not be None")
        if store is None:
            raise TypeError("store must not be None")
        self._runner = runner
        self._store = store

    def submit(
        self, run_id: str, alpha_id: str, report: Mapping[str, object]
    ) -> NodeResult:
        if type(run_id) is not str or not run_id.strip():
            raise ValueError("run_id must be a nonblank string")
        if type(alpha_id) is not str or not alpha_id.strip():
            raise ValueError("alpha_id must be a nonblank string")
        if not isinstance(report, Mapping):
            raise TypeError("report must be a mapping")
        report_hash = canonical_report_hash(report)
        if report.get("run_id") != run_id:
            raise ApprovalMismatch("final report belongs to a different run")
        if _recommended_alpha_id(report) != alpha_id:
            raise ApprovalMismatch("recommended alpha changed after the report")

        approval = self._store.find_unconsumed_approval(
            run_id, alpha_id, report_hash
        )
        if approval is None:
            raise ApprovalMismatch("no unconsumed approval matches the final report")
        if (
            approval.run_id != run_id
            or approval.alpha_id != alpha_id
            or approval.report_hash != report_hash
            or approval.consumed_at is not None
        ):
            raise ApprovalMismatch("approval subject does not exactly match the report")
        try:
            self._store.begin_approved_submission(
                run_id, approval.id, alpha_id, report_hash
            )
        except StoreConflict as error:
            raise ApprovalMismatch(str(error)) from error

        try:
            runner_result = self._runner.run(
                run_id,
                WorkflowNode.M,
                ("alpha", "submit", alpha_id),
                "alpha_submit.json",
            )
        except BaseException as error:
            raise SubmissionUncertain(
                "submission status is uncertain; inspect platform status before resuming"
            ) from error

        payload = runner_result.payload
        submit_code = payload.get("submit_code") if isinstance(payload, Mapping) else None
        if submit_code != 200:
            detail = {
                "event": "submission_failed",
                "alpha_id": alpha_id,
                "report_hash": report_hash,
                "submit_result": dict(payload) if isinstance(payload, Mapping) else {},
            }
            self._store.transition(
                run_id,
                RunState.FAILED,
                json.dumps(detail, sort_keys=True, separators=(",", ":")),
            )
            raise SubmissionFailed("platform returned a definite submission failure")

        finished = self._store.consume_approval_and_finish_submission(
            run_id, approval.id, alpha_id, report_hash, dict(payload)
        )
        artifact = getattr(runner_result, "artifact", None)
        artifact_id = getattr(artifact, "id", None)
        return NodeResult(
            node=WorkflowNode.M,
            summary={
                "status": "submitted",
                "alpha_id": alpha_id,
                "report_hash": report_hash,
            },
            artifact_ids=() if artifact_id is None else (str(artifact_id),),
            run_state=finished.state,
            payload=dict(payload),
        )

    def reject(self, run_id: str, reason: str) -> NodeResult:
        rejected = self._store.record_rejection(run_id, reason)
        return NodeResult(
            node=WorkflowNode.M,
            summary={"status": "rejected", "reason": reason},
            run_state=rejected.state,
        )

    def record_only(
        self, run_id: str, terminal_state: RunState, reason: str
    ) -> NodeResult:
        if terminal_state not in {RunState.BUDGET_EXHAUSTED, RunState.NO_PROGRESS}:
            raise ValueError("record-only state must be a bounded research terminal")
        finished = self._store.transition(run_id, terminal_state, reason)
        return NodeResult(
            node=WorkflowNode.M,
            summary={"status": "record_only", "reason": reason},
            run_state=finished.state,
        )
