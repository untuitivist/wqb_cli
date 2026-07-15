from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from dataclasses import FrozenInstanceError
from pathlib import Path

from wqb_cli.agent.store import (
    AgentStore,
    InvalidNodeAttempt,
    InvalidTransition,
    RunAlreadyExists,
    RunNotFound,
)
from wqb_cli.agent.types import Budget, RunConfig, RunState, ScopeMode, WorkflowNode


ALLOWED_TRANSITIONS = {
    RunState.CREATED: {RunState.RUNNING, RunState.FAILED},
    RunState.RUNNING: {
        RunState.NEEDS_AUTH,
        RunState.PAUSED_MODEL,
        RunState.AWAITING_APPROVAL,
        RunState.BUDGET_EXHAUSTED,
        RunState.NO_PROGRESS,
        RunState.FAILED,
    },
    RunState.NEEDS_AUTH: {RunState.RUNNING, RunState.FAILED},
    RunState.PAUSED_MODEL: {RunState.RUNNING, RunState.FAILED},
    RunState.AWAITING_APPROVAL: {
        RunState.RUNNING,
        RunState.REJECTED,
        RunState.FAILED,
    },
    RunState.SUBMITTED: set(),
    RunState.REJECTED: set(),
    RunState.BUDGET_EXHAUSTED: set(),
    RunState.NO_PROGRESS: set(),
    RunState.FAILED: set(),
}

PATH_TO_STATE = {
    RunState.CREATED: (),
    RunState.RUNNING: (RunState.RUNNING,),
    RunState.NEEDS_AUTH: (RunState.RUNNING, RunState.NEEDS_AUTH),
    RunState.PAUSED_MODEL: (RunState.RUNNING, RunState.PAUSED_MODEL),
    RunState.AWAITING_APPROVAL: (RunState.RUNNING, RunState.AWAITING_APPROVAL),
    RunState.REJECTED: (
        RunState.RUNNING,
        RunState.AWAITING_APPROVAL,
        RunState.REJECTED,
    ),
    RunState.BUDGET_EXHAUSTED: (RunState.RUNNING, RunState.BUDGET_EXHAUSTED),
    RunState.NO_PROGRESS: (RunState.RUNNING, RunState.NO_PROGRESS),
    RunState.FAILED: (RunState.FAILED,),
}


def auto_config() -> RunConfig:
    return RunConfig(scope_mode=ScopeMode.AUTO, budget=Budget(rounds=3))


def manual_config() -> RunConfig:
    return RunConfig(
        scope_mode=ScopeMode.MANUAL,
        region="CHN",
        delay=1,
        universe="TOP2000",
        neutralization="INDUSTRY",
        budget=Budget(candidates_per_round=4, max_model_cost_usd=2.5),
    )


class AgentStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "nested" / "agent.sqlite3"
        self.store = AgentStore(self.db_path)
        self.store.initialize()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def create_at_state(self, run_id: str, state: RunState) -> None:
        self.store.create_run(run_id, auto_config())
        for target in PATH_TO_STATE[state]:
            self.store.transition(run_id, target, f"reach {target.value}")

    def history(self, run_id: str) -> list[sqlite3.Row]:
        with closing(self.store.connect()) as connection:
            return connection.execute(
                "SELECT from_state, to_state, reason FROM state_transitions "
                "WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()

    def test_create_persists_exact_immutable_auto_and_manual_configs(self) -> None:
        cases = (("auto", auto_config()), ("manual", manual_config()))
        for run_id, config in cases:
            with self.subTest(run_id=run_id):
                created = self.store.create_run(run_id, config)
                loaded = self.store.get_run(run_id)
                self.assertEqual(created, loaded)
                self.assertEqual(loaded.state, RunState.CREATED)
                self.assertEqual(loaded.config, config)
                with self.assertRaises(FrozenInstanceError):
                    loaded.state = RunState.RUNNING  # type: ignore[misc]

        expected = (
            '{"budget":{"candidates_per_round":8,"max_model_cost_usd":null,'
            '"max_runtime_minutes":180,"operator_calls":100,"planner_calls":20,'
            '"rounds":3,"total_simulations":40},"delay":null,"neutralization":null,'
            '"region":null,"scope_mode":"auto","universe":null}'
        )
        with closing(self.store.connect()) as connection:
            stored = connection.execute(
                "SELECT config_json FROM runs WHERE run_id = 'auto'"
            ).fetchone()[0]
        self.assertEqual(stored, expected)

    def test_duplicate_and_missing_runs_raise_deliberate_errors(self) -> None:
        self.store.create_run("duplicate", auto_config())
        with self.assertRaises(RunAlreadyExists):
            self.store.create_run("duplicate", manual_config())
        with self.assertRaises(RunNotFound):
            self.store.get_run("missing")
        with self.assertRaises(RunNotFound):
            self.store.transition("missing", RunState.RUNNING, "no run")
        with self.assertRaises(RunNotFound):
            self.store.start_node_attempt("missing", WorkflowNode.A)

    def test_every_allowed_transition_updates_run_and_writes_history(self) -> None:
        for source, targets in ALLOWED_TRANSITIONS.items():
            if source is RunState.SUBMITTED:
                continue
            for target in targets:
                run_id = f"allowed-{source.value}-{target.value}"
                with self.subTest(source=source, target=target):
                    self.create_at_state(run_id, source)
                    before = len(self.history(run_id))
                    updated = self.store.transition(run_id, target, "expected reason")
                    self.assertEqual(updated.state, target)
                    rows = self.history(run_id)
                    self.assertEqual(len(rows), before + 1)
                    self.assertEqual(
                        tuple(rows[-1]),
                        (source.value, target.value, "expected reason"),
                    )

    def test_every_invalid_transition_preserves_state_and_history(self) -> None:
        sources = tuple(PATH_TO_STATE)
        for index, source in enumerate(sources):
            invalid_targets = set(RunState) - ALLOWED_TRANSITIONS[source]
            for target in invalid_targets:
                run_id = f"invalid-{index}-{target.value}"
                with self.subTest(source=source, target=target):
                    self.create_at_state(run_id, source)
                    before = self.history(run_id)
                    with self.assertRaises(InvalidTransition):
                        self.store.transition(run_id, target, "not allowed")
                    self.assertEqual(self.store.get_run(run_id).state, source)
                    self.assertEqual(self.history(run_id), before)

    def test_generic_transition_always_rejects_submitted(self) -> None:
        for source in (
            RunState.CREATED,
            RunState.RUNNING,
            RunState.AWAITING_APPROVAL,
        ):
            run_id = f"submitted-{source.value}"
            with self.subTest(source=source):
                self.create_at_state(run_id, source)
                before = self.history(run_id)
                with self.assertRaises(InvalidTransition):
                    self.store.transition(run_id, RunState.SUBMITTED, "bypass")
                self.assertEqual(self.store.get_run(run_id).state, source)
                self.assertEqual(self.history(run_id), before)

    def test_attempt_numbers_are_scoped_and_completed_summary_is_canonical(self) -> None:
        for run_id in ("run-a", "run-b"):
            self.store.create_run(run_id, auto_config())

        first = self.store.start_node_attempt("run-a", WorkflowNode.F)
        second = self.store.start_node_attempt("run-a", WorkflowNode.F)
        other_node = self.store.start_node_attempt("run-a", WorkflowNode.G)
        other_run = self.store.start_node_attempt("run-b", WorkflowNode.F)
        self.assertEqual(first.attempt_number, 1)
        self.assertEqual(second.attempt_number, 2)
        self.assertEqual(other_node.attempt_number, 1)
        self.assertEqual(other_run.attempt_number, 1)
        self.assertEqual(first.status, "RUNNING")

        self.store.finish_node_attempt(first, "COMPLETED", {"z": 1, "a": "中文"})
        with closing(self.store.connect()) as connection:
            row = connection.execute(
                "SELECT status, summary_json, finished_at FROM node_attempts WHERE id = ?",
                (first.id,),
            ).fetchone()
        self.assertEqual(row["status"], "COMPLETED")
        self.assertEqual(row["summary_json"], '{"a":"中文","z":1}')
        self.assertIsNotNone(row["finished_at"])

    def test_latest_completed_node_uses_latest_completed_attempt(self) -> None:
        self.store.create_run("feedback", auto_config())
        self.assertIsNone(self.store.latest_completed_node("feedback"))

        first = self.store.start_node_attempt("feedback", WorkflowNode.F)
        self.store.finish_node_attempt(first, "COMPLETED", {"round": 1})
        failed = self.store.start_node_attempt("feedback", WorkflowNode.G)
        self.store.finish_node_attempt(failed, "FAILED", {"error": "retry"})
        repeated = self.store.start_node_attempt("feedback", WorkflowNode.F)
        self.store.finish_node_attempt(repeated, "COMPLETED", {"round": 2})
        latest = self.store.start_node_attempt("feedback", WorkflowNode.H)
        self.store.finish_node_attempt(latest, "COMPLETED", {"round": 3})

        self.assertEqual(self.store.latest_completed_node("feedback"), WorkflowNode.H)
        with self.assertRaises(RunNotFound):
            self.store.latest_completed_node("missing")

    def test_attempts_cannot_be_finished_twice_or_with_invalid_status(self) -> None:
        self.store.create_run("run", auto_config())
        attempt = self.store.start_node_attempt("run", WorkflowNode.A)
        with self.assertRaises(InvalidNodeAttempt):
            self.store.finish_node_attempt(attempt, "RUNNING", {})
        self.assertEqual(attempt.status, "RUNNING")

        self.store.finish_node_attempt(attempt, "INTERRUPTED", {"why": "pause"})
        with self.assertRaises(InvalidNodeAttempt):
            self.store.finish_node_attempt(attempt, "FAILED", {"why": "again"})

        unknown = type(attempt)(
            id=attempt.id + 1000,
            run_id=attempt.run_id,
            node=attempt.node,
            attempt_number=attempt.attempt_number,
            status="RUNNING",
        )
        with self.assertRaises(InvalidNodeAttempt):
            self.store.finish_node_attempt(unknown, "COMPLETED", {})

    def test_initialize_is_idempotent_reopen_preserves_data_and_pragmas(self) -> None:
        self.assertTrue(self.db_path.parent.is_dir())
        self.store.create_run("persisted", manual_config())
        self.store.initialize()
        reopened = AgentStore(self.db_path)
        reopened.initialize()

        self.assertEqual(reopened.get_run("persisted").config, manual_config())
        with closing(reopened.connect()) as connection:
            self.assertEqual(connection.row_factory, sqlite3.Row)
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(connection.execute("PRAGMA journal_mode").fetchone()[0], "wal")
            self.assertEqual(
                [
                    row["version"]
                    for row in connection.execute(
                        "SELECT version FROM schema_version"
                    ).fetchall()
                ],
                [1],
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO node_attempts "
                    "(run_id, node, attempt_number, status) VALUES (?, ?, ?, ?)",
                    ("missing", WorkflowNode.A.value, 1, "RUNNING"),
                )

    def test_separate_store_instances_allocate_unique_attempt_numbers(self) -> None:
        self.store.create_run("concurrent", auto_config())
        barrier = threading.Barrier(3)
        records = []
        errors = []
        lock = threading.Lock()

        def allocate() -> None:
            local_store = AgentStore(self.db_path)
            barrier.wait(timeout=5)
            try:
                record = local_store.start_node_attempt("concurrent", WorkflowNode.M)
                with lock:
                    records.append(record)
            except BaseException as error:
                with lock:
                    errors.append(error)

        threads = [threading.Thread(target=allocate) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait(timeout=5)
        for thread in threads:
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())

        self.assertEqual(errors, [])
        self.assertEqual(sorted(record.attempt_number for record in records), [1, 2])


if __name__ == "__main__":
    unittest.main()
