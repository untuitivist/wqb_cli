from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from agent.artifacts import ArtifactWriter
from agent.nodes.submission import (
    ApprovalMismatch,
    SubmissionFailed,
    SubmissionNode,
    SubmissionUncertain,
)
from agent.reporting import (
    build_final_report,
    canonical_report_hash,
    write_final_report,
)
from agent.store import AgentStore, InvalidTransition, StoreConflict
from agent.types import Budget, RunConfig, RunState, ScopeMode, WorkflowNode


def manual_config() -> RunConfig:
    return RunConfig(
        scope_mode=ScopeMode.MANUAL,
        region="USA",
        delay=1,
        universe="TOP3000",
        neutralization="INDUSTRY",
        budget=Budget(planner_calls=7, operator_calls=11),
    )


def final_report(
    alpha_id: str = "ALPHA1", run_id: str = "run-1"
) -> dict[str, object]:
    return build_final_report(
        run_id=run_id,
        run_config={"scope_mode": "manual", "budget": {"rounds": 5}},
        scope={"region": "USA", "delay": 1, "universe": "TOP3000"},
        plan_version=3,
        plan_hash="plan-sha",
        candidate={"alpha_id": alpha_id, "metrics": {"sharpe": 1.9}},
        checks=[{"name": "LOW_SHARPE", "result": "PASS"}],
        evidence_refs=["artifact-4", "artifact-8"],
        route_history=["J", "K", "L", "M"],
        budgets={"simulations": {"used": 9, "limit": 40}},
        role_usage={"planner": {"calls": 4}, "operator": {"calls": 8}},
        terminal_recommendation={"decision": "SUBMIT", "alpha_id": alpha_id},
    )


class AgentSubmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.store = AgentStore(root / "agent.sqlite3")
        self.store.initialize()
        self.artifacts = ArtifactWriter(root / "artifacts", self.store)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def awaiting_run(self, run_id: str = "run-1") -> None:
        self.store.create_run(run_id, manual_config())
        self.store.transition(run_id, RunState.RUNNING, "start")
        self.store.transition(run_id, RunState.AWAITING_APPROVAL, "report ready")

    def test_report_hash_is_canonical_utf8_json_sha256(self) -> None:
        report = {"unicode": "\u4e2d\u6587", "b": 2, "a": [1, True]}
        encoded = json.dumps(
            report,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(canonical_report_hash(report), hashlib.sha256(encoded).hexdigest())
        self.assertEqual(
            canonical_report_hash(report),
            canonical_report_hash({"a": [1, True], "b": 2, "unicode": "\u4e2d\u6587"}),
        )

    def test_build_and_write_final_report_contains_submission_subject(self) -> None:
        self.store.create_run("run-1", manual_config())
        report = final_report()
        written = write_final_report(self.artifacts, "run-1", report)

        self.assertEqual(report["plan"], {"version": 3, "hash": "plan-sha"})
        self.assertEqual(
            written.approval_subject,
            {
                "run_id": "run-1",
                "recommended_alpha_id": "ALPHA1",
                "report_hash": canonical_report_hash(report),
            },
        )
        self.assertEqual(Path(written.json_artifact.path).name, "final_report.json")
        self.assertEqual(Path(written.markdown_artifact.path).name, "final_report.md")
        self.assertIn("ALPHA1", Path(written.markdown_artifact.path).read_text("utf-8"))

    def test_begin_requires_exact_unconsumed_approval_and_consumes_on_success(self) -> None:
        self.awaiting_run()
        report_hash = canonical_report_hash(final_report())
        approval = self.store.record_approval("run-1", "ALPHA1", report_hash)

        begun = self.store.begin_approved_submission(
            "run-1", approval.id, "ALPHA1", report_hash
        )
        self.assertEqual(begun.state, RunState.RUNNING)
        with self.assertRaises(StoreConflict):
            self.store.begin_approved_submission(
                "run-1", approval.id, "ALPHA1", report_hash
            )

        finished = self.store.consume_approval_and_finish_submission(
            "run-1", approval.id, "ALPHA1", report_hash, {"submit_code": 200}
        )
        self.assertEqual(finished.state, RunState.SUBMITTED)
        self.assertIsNone(
            self.store.find_unconsumed_approval("run-1", "ALPHA1", report_hash)
        )
        with self.assertRaises(StoreConflict):
            self.store.consume_approval_and_finish_submission(
                "run-1", approval.id, "ALPHA1", report_hash, {"submit_code": 200}
            )

    def test_record_rejection_is_terminal_without_creating_approval(self) -> None:
        self.awaiting_run()
        rejected = self.store.record_rejection("run-1", "operator rejected")
        self.assertEqual(rejected.state, RunState.REJECTED)
        self.assertIsNone(
            self.store.find_unconsumed_approval("run-1", "ALPHA1", "report-hash")
        )

    def test_consume_cannot_bypass_begin_transaction(self) -> None:
        self.store.create_run("run-1", manual_config())
        self.store.transition("run-1", RunState.RUNNING, "ordinary research")
        report_hash = canonical_report_hash(final_report())
        approval = self.store.record_approval("run-1", "ALPHA1", report_hash)

        with self.assertRaises(StoreConflict):
            self.store.consume_approval_and_finish_submission(
                "run-1", approval.id, "ALPHA1", report_hash, {"submit_code": 200}
            )
        self.assertEqual(self.store.get_run("run-1").state, RunState.RUNNING)
        self.assertIsNotNone(
            self.store.find_unconsumed_approval("run-1", "ALPHA1", report_hash)
        )

    def test_mismatch_conditions_never_call_runner(self) -> None:
        cases = ("missing", "report", "alpha", "wrong_state", "consumed")
        for case in cases:
            with self.subTest(case=case):
                run_id = f"run-{case}"
                self.awaiting_run(run_id)
                report = final_report(run_id=run_id)
                report_hash = canonical_report_hash(report)
                approval = None
                if case != "missing":
                    approved_alpha = "OTHER" if case == "alpha" else "ALPHA1"
                    approved_hash = "old-report" if case == "report" else report_hash
                    approval = self.store.record_approval(
                        run_id, approved_alpha, approved_hash
                    )
                if case == "wrong_state":
                    self.store.transition(run_id, RunState.FAILED, "stop")
                if case == "consumed":
                    self.store.begin_approved_submission(
                        run_id, approval.id, "ALPHA1", report_hash
                    )
                    self.store.consume_approval_and_finish_submission(
                        run_id,
                        approval.id,
                        "ALPHA1",
                        report_hash,
                        {"submit_code": 200},
                    )
                runner = Mock()
                node = SubmissionNode(runner=runner, store=self.store)
                with self.assertRaises((ApprovalMismatch, StoreConflict, InvalidTransition)):
                    node.submit(run_id, "ALPHA1", report)
                runner.run.assert_not_called()

    def test_matching_approval_permits_exactly_one_submit(self) -> None:
        self.awaiting_run()
        report = final_report()
        report_hash = canonical_report_hash(report)
        self.store.record_approval("run-1", "ALPHA1", report_hash)
        runner = Mock()
        runner.run.return_value = SimpleNamespace(
            payload={"ok": True, "submit_code": 200}
        )

        result = SubmissionNode(runner=runner, store=self.store).submit(
            "run-1", "ALPHA1", report
        )

        runner.run.assert_called_once_with(
            "run-1",
            WorkflowNode.M,
            ("alpha", "submit", "ALPHA1"),
            "alpha_submit.json",
        )
        self.assertEqual(result.run_state, RunState.SUBMITTED)
        self.assertEqual(self.store.get_run("run-1").state, RunState.SUBMITTED)

    def test_uncertain_submission_stays_running_and_never_reposts(self) -> None:
        self.awaiting_run()
        report = final_report()
        self.store.record_approval(
            "run-1", "ALPHA1", canonical_report_hash(report)
        )
        runner = Mock()
        runner.run.side_effect = RuntimeError("connection dropped after POST")
        node = SubmissionNode(runner=runner, store=self.store)

        with self.assertRaises(SubmissionUncertain):
            node.submit("run-1", "ALPHA1", report)
        self.assertEqual(self.store.get_run("run-1").state, RunState.RUNNING)
        with self.assertRaises(ApprovalMismatch):
            node.submit("run-1", "ALPHA1", report)
        self.assertEqual(runner.run.call_count, 1)

    def test_definite_failure_is_terminal_and_never_reposts(self) -> None:
        self.awaiting_run()
        report = final_report()
        self.store.record_approval(
            "run-1", "ALPHA1", canonical_report_hash(report)
        )
        runner = Mock()
        runner.run.return_value = SimpleNamespace(
            payload={"ok": False, "submit_code": 460}
        )
        node = SubmissionNode(runner=runner, store=self.store)

        with self.assertRaises(SubmissionFailed):
            node.submit("run-1", "ALPHA1", report)
        self.assertEqual(self.store.get_run("run-1").state, RunState.FAILED)
        with self.assertRaises(ApprovalMismatch):
            node.submit("run-1", "ALPHA1", report)
        self.assertEqual(runner.run.call_count, 1)

    def test_reject_and_record_only_never_call_runner_or_create_approval(self) -> None:
        for state in (RunState.REJECTED, RunState.BUDGET_EXHAUSTED, RunState.NO_PROGRESS):
            with self.subTest(state=state):
                run_id = f"run-{state.value.lower()}"
                self.awaiting_run(run_id)
                runner = Mock()
                node = SubmissionNode(runner=runner, store=self.store)
                if state is RunState.REJECTED:
                    result = node.reject(run_id, "operator rejected")
                else:
                    self.store.transition(run_id, RunState.RUNNING, "resume")
                    result = node.record_only(run_id, state, "research terminal")
                self.assertEqual(result.run_state, state)
                runner.run.assert_not_called()
                with closing(self.store.connect()) as connection:
                    count = connection.execute(
                        "SELECT COUNT(*) FROM approvals WHERE run_id = ?", (run_id,)
                    ).fetchone()[0]
                self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
