from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import unittest
from collections import UserDict
from contextlib import closing
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import wqb_cli.agent.store as store_module
from wqb_cli.agent.store import (
    AgentStore,
    InvalidNodeAttempt,
    InvalidTransition,
    NodeAttemptRecord,
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
        if state is RunState.SUBMITTED:
            self.seed_submitted_run(run_id)
            return
        self.store.create_run(run_id, auto_config())
        for target in PATH_TO_STATE[state]:
            self.store.transition(run_id, target, f"reach {target.value}")

    def seed_submitted_run(self, run_id: str) -> None:
        self.store.create_run(run_id, auto_config())
        with closing(self.store.connect()) as connection:
            connection.execute(
                "UPDATE runs SET state = ? WHERE run_id = ?",
                (RunState.SUBMITTED.value, run_id),
            )
            connection.commit()

    def history(self, run_id: str) -> list[sqlite3.Row]:
        with closing(self.store.connect()) as connection:
            return connection.execute(
                "SELECT from_state, to_state, reason FROM state_transitions "
                "WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()

    def table_counts(self) -> tuple[int, int, int]:
        with closing(self.store.connect()) as connection:
            return tuple(
                connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("runs", "state_transitions", "node_attempts")
            )

    def test_all_public_apis_validate_before_database_access(self) -> None:
        class RunConfigSubclass(RunConfig):
            pass

        class AttemptSubclass(NodeAttemptRecord):
            pass

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "absent" / "store.sqlite3"
            unopened = AgentStore(path)
            attempt = NodeAttemptRecord(1, "run", WorkflowNode.A, 1, "RUNNING")
            invalid_calls = (
                (TypeError, lambda: unopened.create_run(None, auto_config())),
                (ValueError, lambda: unopened.create_run(" ", auto_config())),
                (
                    TypeError,
                    lambda: unopened.create_run(
                        "run", RunConfigSubclass(scope_mode=ScopeMode.AUTO)
                    ),
                ),
                (TypeError, lambda: unopened.get_run(1)),
                (ValueError, lambda: unopened.get_run("")),
                (
                    TypeError,
                    lambda: unopened.transition("run", "RUNNING", "reason"),
                ),
                (
                    TypeError,
                    lambda: unopened.transition("run", RunState.RUNNING, None),
                ),
                (
                    ValueError,
                    lambda: unopened.transition("run", RunState.RUNNING, "  "),
                ),
                (TypeError, lambda: unopened.start_node_attempt("run", "A")),
                (TypeError, lambda: unopened.start_node_attempt(None, WorkflowNode.A)),
                (
                    TypeError,
                    lambda: unopened.finish_node_attempt(
                        AttemptSubclass(**attempt.__dict__), "COMPLETED", {}
                    ),
                ),
                (
                    TypeError,
                    lambda: unopened.finish_node_attempt(attempt, None, {}),
                ),
                (
                    InvalidNodeAttempt,
                    lambda: unopened.finish_node_attempt(attempt, "RUNNING", {}),
                ),
                (
                    TypeError,
                    lambda: unopened.finish_node_attempt(
                        attempt, "COMPLETED", UserDict()
                    ),
                ),
                (TypeError, lambda: unopened.latest_completed_node(None)),
            )
            for error_type, operation in invalid_calls:
                with self.subTest(error_type=error_type, operation=operation):
                    with self.assertRaises(error_type):
                        operation()
                    self.assertFalse(path.exists())

    def test_invalid_inputs_do_not_mutate_existing_rows_or_history(self) -> None:
        self.store.create_run("run", auto_config())
        attempt = self.store.start_node_attempt("run", WorkflowNode.A)
        circular: dict[str, object] = {}
        circular["self"] = circular
        malformed_attempts = (
            replace(attempt, id=True),
            replace(attempt, id=0),
            replace(attempt, attempt_number=True),
            replace(attempt, attempt_number=0),
            replace(attempt, run_id=" "),
            replace(attempt, node="A"),
            replace(attempt, status=1),
            replace(attempt, status="COMPLETED"),
        )
        invalid_calls = [
            lambda: self.store.create_run("new", None),
            lambda: self.store.create_run(" ", auto_config()),
            lambda: self.store.get_run(None),
            lambda: self.store.transition("run", "RUNNING", "reason"),
            lambda: self.store.transition("run", RunState.RUNNING, ""),
            lambda: self.store.start_node_attempt("run", "A"),
            lambda: self.store.finish_node_attempt(attempt, 1, {}),
            lambda: self.store.finish_node_attempt(attempt, "UNKNOWN", {}),
            lambda: self.store.finish_node_attempt(attempt, "COMPLETED", []),
            lambda: self.store.finish_node_attempt(attempt, "COMPLETED", circular),
            lambda: self.store.latest_completed_node(" "),
        ]
        invalid_calls.extend(
            lambda malformed=malformed: self.store.finish_node_attempt(
                malformed, "COMPLETED", {}
            )
            for malformed in malformed_attempts
        )
        before = self.table_counts()
        for operation in invalid_calls:
            with self.subTest(operation=operation):
                with self.assertRaises((TypeError, ValueError)):
                    operation()
                self.assertEqual(self.table_counts(), before)
                self.assertEqual(self.store.get_run("run").state, RunState.CREATED)
                self.assertEqual(self.history("run"), [])
        with closing(self.store.connect()) as connection:
            row = connection.execute(
                "SELECT status, summary_json, finished_at FROM node_attempts WHERE id = ?",
                (attempt.id,),
            ).fetchone()
        self.assertEqual(tuple(row), ("RUNNING", None, None))

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
        sources = (*PATH_TO_STATE, RunState.SUBMITTED)
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

    def test_transition_rejects_zero_row_update_before_writing_history(self) -> None:
        self.store.create_run("guarded", auto_config())
        with closing(self.store.connect()) as connection:
            connection.execute(
                "CREATE TRIGGER ignore_guarded_transition "
                "BEFORE UPDATE ON runs WHEN OLD.run_id = 'guarded' "
                "BEGIN SELECT RAISE(IGNORE); END"
            )
            connection.commit()

        with self.assertRaises(InvalidTransition):
            self.store.transition("guarded", RunState.RUNNING, "race guard")

        self.assertEqual(self.store.get_run("guarded").state, RunState.CREATED)
        self.assertEqual(self.history("guarded"), [])

    def test_concurrent_terminal_transitions_allow_exactly_one_winner(self) -> None:
        self.store.create_run("terminal-race", auto_config())
        self.store.transition("terminal-race", RunState.RUNNING, "start")
        barrier = threading.Barrier(3)
        successes = []
        errors = []
        lock = threading.Lock()

        def transition(target: RunState) -> None:
            local_store = AgentStore(self.db_path)
            barrier.wait(timeout=5)
            try:
                result = local_store.transition("terminal-race", target, target.value)
                with lock:
                    successes.append(result)
            except BaseException as error:
                with lock:
                    errors.append(error)

        threads = [
            threading.Thread(target=transition, args=(target,))
            for target in (RunState.FAILED, RunState.NO_PROGRESS)
        ]
        for thread in threads:
            thread.start()
        barrier.wait(timeout=5)
        for thread in threads:
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], InvalidTransition)
        with closing(self.store.connect()) as connection:
            rows = connection.execute(
                "SELECT id, from_state, to_state FROM state_transitions "
                "WHERE run_id = 'terminal-race' ORDER BY id"
            ).fetchall()
        self.assertEqual([row["id"] for row in rows], sorted(row["id"] for row in rows))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[-1]["from_state"], RunState.RUNNING.value)
        self.assertEqual(rows[-1]["to_state"], successes[0].state.value)

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

        self.store.finish_node_attempt(
            first,
            "COMPLETED",
            {"z": 1, "a": "中文"},
        )
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

    def test_latest_completed_node_uses_completion_sequence_not_timestamp_or_id(
        self,
    ) -> None:
        self.store.create_run("ordered", auto_config())
        lower_id = self.store.start_node_attempt("ordered", WorkflowNode.F)
        higher_id = self.store.start_node_attempt("ordered", WorkflowNode.H)

        self.store.finish_node_attempt(higher_id, "COMPLETED", {"finished": 1})
        self.store.finish_node_attempt(lower_id, "COMPLETED", {"finished": 2})
        with closing(self.store.connect()) as connection:
            connection.execute(
                "UPDATE node_attempts SET finished_at = 'same' WHERE run_id = 'ordered'"
            )
            rows = connection.execute(
                "SELECT id, completion_sequence FROM node_attempts "
                "WHERE run_id = 'ordered' ORDER BY id"
            ).fetchall()
            connection.commit()

        self.assertEqual(
            [(row["id"], row["completion_sequence"]) for row in rows],
            [(lower_id.id, 2), (higher_id.id, 1)],
        )
        self.assertEqual(self.store.latest_completed_node("ordered"), WorkflowNode.F)

    def test_completion_sequence_includes_every_terminal_status_and_is_per_run(
        self,
    ) -> None:
        for run_id in ("terminal-sequence", "other-sequence"):
            self.store.create_run(run_id, auto_config())
        attempts = [
            self.store.start_node_attempt("terminal-sequence", node)
            for node in (WorkflowNode.A, WorkflowNode.F, WorkflowNode.H)
        ]
        for attempt, status in zip(
            attempts,
            ("FAILED", "INTERRUPTED", "COMPLETED"),
            strict=True,
        ):
            self.store.finish_node_attempt(attempt, status, {"status": status})
        other = self.store.start_node_attempt("other-sequence", WorkflowNode.A)
        self.store.finish_node_attempt(other, "FAILED", {})

        with closing(self.store.connect()) as connection:
            rows = connection.execute(
                "SELECT status, completion_sequence FROM node_attempts "
                "WHERE run_id = 'terminal-sequence' ORDER BY id"
            ).fetchall()
            other_sequence = connection.execute(
                "SELECT completion_sequence FROM node_attempts WHERE id = ?",
                (other.id,),
            ).fetchone()[0]
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE node_attempts SET completion_sequence = 1 WHERE id = ?",
                    (attempts[-1].id,),
                )
        self.assertEqual(
            [(row["status"], row["completion_sequence"]) for row in rows],
            [("FAILED", 1), ("INTERRUPTED", 2), ("COMPLETED", 3)],
        )
        self.assertEqual(other_sequence, 1)
        self.assertEqual(
            self.store.latest_completed_node("terminal-sequence"), WorkflowNode.H
        )

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

    def test_attempt_summary_rejects_non_native_json_without_finishing(self) -> None:
        self.store.create_run("summary-json", auto_config())
        circular: dict[str, object] = {}
        circular["self"] = circular
        invalid_summaries = (
            {1: "non-string-key"},
            {"tuple": (1, 2)},
            {"infinity": float("inf")},
            circular,
        )
        for summary in invalid_summaries:
            attempt = self.store.start_node_attempt("summary-json", WorkflowNode.A)
            with self.subTest(summary=summary):
                with self.assertRaises((TypeError, ValueError)):
                    self.store.finish_node_attempt(attempt, "COMPLETED", summary)
                with closing(self.store.connect()) as connection:
                    row = connection.execute(
                        "SELECT status, summary_json, finished_at "
                        "FROM node_attempts WHERE id = ?",
                        (attempt.id,),
                    ).fetchone()
                self.assertEqual(tuple(row), ("RUNNING", None, None))

    def test_concurrent_double_finish_allows_exactly_one_winner(self) -> None:
        self.store.create_run("finish-race", auto_config())
        attempt = self.store.start_node_attempt("finish-race", WorkflowNode.A)
        barrier = threading.Barrier(3)
        successes = []
        errors = []
        lock = threading.Lock()

        def finish(status: str) -> None:
            local_store = AgentStore(self.db_path)
            barrier.wait(timeout=5)
            try:
                local_store.finish_node_attempt(attempt, status, {"status": status})
                with lock:
                    successes.append(status)
            except BaseException as error:
                with lock:
                    errors.append(error)

        threads = [
            threading.Thread(target=finish, args=(status,))
            for status in ("COMPLETED", "FAILED")
        ]
        for thread in threads:
            thread.start()
        barrier.wait(timeout=5)
        for thread in threads:
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], InvalidNodeAttempt)
        with closing(self.store.connect()) as connection:
            row = connection.execute(
                "SELECT status, completion_sequence FROM node_attempts WHERE id = ?",
                (attempt.id,),
            ).fetchone()
        self.assertEqual(row["status"], successes[0])
        self.assertEqual(row["completion_sequence"], 1)

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
                [1, 2, 3],
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO node_attempts "
                    "(run_id, node, attempt_number, status) VALUES (?, ?, ?, ?)",
                    ("missing", WorkflowNode.A.value, 1, "RUNNING"),
                )

    def test_exact_v1_database_upgrades_backfills_and_reopens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.sqlite3"
            legacy = AgentStore(path, _migrations=store_module._MIGRATIONS[:1])
            legacy.initialize()
            legacy.create_run("legacy", auto_config())
            legacy.create_run("other", auto_config())
            with closing(legacy.connect()) as connection:
                columns = [
                    row["name"]
                    for row in connection.execute(
                        "PRAGMA table_info(node_attempts)"
                    ).fetchall()
                ]
                completed_index_sql = connection.execute(
                    "SELECT sql FROM sqlite_master "
                    "WHERE type = 'index' AND name = 'idx_node_attempts_run_completed'"
                ).fetchone()[0]
                attempts = (
                    ("legacy", "B", 1, "COMPLETED", None),
                    ("legacy", "F", 1, "COMPLETED", "2026-01-01T00:00:00Z"),
                    ("legacy", "H", 1, "FAILED", "2026-01-01T00:00:00Z"),
                    ("legacy", "A", 1, "INTERRUPTED", "2026-01-02T00:00:00Z"),
                    ("legacy", "M", 1, "RUNNING", None),
                    ("other", "C", 1, "INTERRUPTED", None),
                    ("other", "G", 1, "FAILED", "2026-01-01T00:00:00Z"),
                    ("other", "J", 1, "COMPLETED", "2026-01-02T00:00:00Z"),
                )
                ids = []
                for run_id, node, attempt_number, status, finished_at in attempts:
                    cursor = connection.execute(
                        "INSERT INTO node_attempts "
                        "(run_id, node, attempt_number, status, finished_at) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (run_id, node, attempt_number, status, finished_at),
                    )
                    ids.append(cursor.lastrowid)
                connection.commit()

            self.assertEqual(
                columns,
                [
                    "id",
                    "run_id",
                    "node",
                    "attempt_number",
                    "status",
                    "summary_json",
                    "started_at",
                    "finished_at",
                ],
            )
            self.assertIn("finished_at DESC", completed_index_sql)
            self.assertNotIn("completion_sequence", completed_index_sql)

            upgraded = AgentStore(path)
            upgraded.initialize()
            with closing(upgraded.connect()) as connection:
                rows = connection.execute(
                    "SELECT run_id, node, status, completion_sequence "
                    "FROM node_attempts ORDER BY id"
                ).fetchall()
                versions = connection.execute(
                    "SELECT version FROM schema_version ORDER BY version"
                ).fetchall()
                index_sql = connection.execute(
                    "SELECT sql FROM sqlite_master "
                    "WHERE type = 'index' AND name = 'idx_node_attempts_run_completed'"
                ).fetchone()[0]
            self.assertEqual(
                [
                    (row["run_id"], row["node"], row["completion_sequence"])
                    for row in rows
                ],
                [
                    ("legacy", "B", 1),
                    ("legacy", "F", 2),
                    ("legacy", "H", 3),
                    ("legacy", "A", 4),
                    ("legacy", "M", None),
                    ("other", "C", 1),
                    ("other", "G", 2),
                    ("other", "J", 3),
                ],
            )
            self.assertEqual([row["version"] for row in versions], [1, 2, 3])
            self.assertIn("completion_sequence DESC", index_sql)
            self.assertEqual(upgraded.latest_completed_node("legacy"), WorkflowNode.F)

            running = NodeAttemptRecord(
                id=ids[4],
                run_id="legacy",
                node=WorkflowNode.M,
                attempt_number=1,
                status="RUNNING",
            )
            upgraded.finish_node_attempt(running, "COMPLETED", {"upgraded": True})
            self.assertEqual(upgraded.latest_completed_node("legacy"), WorkflowNode.M)
            with closing(upgraded.connect()) as connection:
                sequence = connection.execute(
                    "SELECT completion_sequence FROM node_attempts WHERE id = ?",
                    (running.id,),
                ).fetchone()[0]
            self.assertEqual(sequence, 5)
            reopened = AgentStore(path)
            reopened.initialize()
            self.assertEqual(reopened.latest_completed_node("legacy"), WorkflowNode.M)

    def test_v2_migration_uses_no_window_function_syntax(self) -> None:
        migration_sql = "\n".join(store_module._MIGRATIONS[1].statements).upper()
        self.assertNotIn("ROW_NUMBER", migration_sql)
        self.assertNotIn(" OVER ", migration_sql)
        self.assertIn("COUNT(", migration_sql)

    def test_unknown_future_schema_version_preserves_delete_journal_and_tables(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "future.sqlite3"
            with closing(sqlite3.connect(path)) as connection:
                connection.execute(
                    "CREATE TABLE schema_version (version INTEGER PRIMARY KEY)"
                )
                connection.execute("INSERT INTO schema_version(version) VALUES (4)")
                connection.execute("CREATE TABLE sentinel (value TEXT)")
                connection.commit()
                self.assertEqual(
                    connection.execute("PRAGMA journal_mode").fetchone()[0], "delete"
                )
                before = connection.execute(
                    "SELECT type, name, sql FROM sqlite_master "
                    "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
                ).fetchall()

            with self.assertRaisesRegex(RuntimeError, "future schema version"):
                AgentStore(path).initialize()

            with closing(sqlite3.connect(path)) as connection:
                self.assertEqual(
                    connection.execute("PRAGMA journal_mode").fetchone()[0], "delete"
                )
                after = connection.execute(
                    "SELECT type, name, sql FROM sqlite_master "
                    "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
                ).fetchall()
            self.assertEqual(after, before)

    def test_missing_schema_prefix_is_rejected_before_migrations_or_wal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gap.sqlite3"
            with closing(sqlite3.connect(path)) as connection:
                connection.execute(
                    "CREATE TABLE schema_version (version INTEGER PRIMARY KEY)"
                )
                connection.execute("INSERT INTO schema_version(version) VALUES (2)")
                connection.execute("CREATE TABLE sentinel (value TEXT)")
                connection.commit()

            with self.assertRaisesRegex(RuntimeError, "contiguous prefix"):
                AgentStore(path).initialize()

            with closing(sqlite3.connect(path)) as connection:
                tables = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
                ).fetchall()
                journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
            self.assertEqual([row[0] for row in tables], ["schema_version", "sentinel"])
            self.assertEqual(journal_mode, "delete")

    def test_failed_injected_migration_is_atomic_and_does_not_enable_wal(self) -> None:
        failing = store_module._Migration(
            version=4,
            statements=(
                "CREATE TABLE migration_probe (value INTEGER NOT NULL)",
                "INSERT INTO table_that_does_not_exist(value) VALUES (1)",
            ),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "failed.sqlite3"
            store = AgentStore(path, _migrations=(*store_module._MIGRATIONS, failing))
            with self.assertRaises(sqlite3.OperationalError):
                store.initialize()

            with closing(sqlite3.connect(path)) as connection:
                tables = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
                journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
            self.assertEqual(tables, [])
            self.assertEqual(journal_mode, "delete")

    def test_only_unapplied_ordered_migrations_execute(self) -> None:
        self.assertEqual(store_module.LATEST_SCHEMA_VERSION, 3)
        fourth = store_module._Migration(
            version=4,
            statements=(
                "CREATE TABLE migration_probe (value INTEGER NOT NULL)",
                "INSERT INTO migration_probe(value) VALUES (1)",
            ),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "migrations.sqlite3"
            store = AgentStore(
                path,
                _migrations=(*store_module._MIGRATIONS, fourth),
            )
            store.initialize()
            store.initialize()
            AgentStore(
                path,
                _migrations=(*store_module._MIGRATIONS, fourth),
            ).initialize()

            with closing(store.connect()) as connection:
                versions = connection.execute(
                    "SELECT version FROM schema_version ORDER BY version"
                ).fetchall()
                probe = connection.execute(
                    "SELECT value FROM migration_probe"
                ).fetchall()
        self.assertEqual([row["version"] for row in versions], [1, 2, 3, 4])
        self.assertEqual([row["value"] for row in probe], [1])

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
