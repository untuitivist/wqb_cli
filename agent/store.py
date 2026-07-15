from __future__ import annotations

import json
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator

from .types import RunConfig, RunState, WorkflowNode


class InvalidTransition(ValueError):
    pass


class RunAlreadyExists(ValueError):
    pass


class RunNotFound(KeyError):
    pass


class InvalidNodeAttempt(ValueError):
    pass


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    state: RunState
    config: RunConfig
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class NodeAttemptRecord:
    id: int
    run_id: str
    node: WorkflowNode
    attempt_number: int
    status: str
    started_at: str | None = None
    finished_at: str | None = None


_ALLOWED_TRANSITIONS: dict[RunState, frozenset[RunState]] = {
    RunState.CREATED: frozenset({RunState.RUNNING, RunState.FAILED}),
    RunState.RUNNING: frozenset(
        {
            RunState.NEEDS_AUTH,
            RunState.PAUSED_MODEL,
            RunState.AWAITING_APPROVAL,
            RunState.BUDGET_EXHAUSTED,
            RunState.NO_PROGRESS,
            RunState.FAILED,
        }
    ),
    RunState.NEEDS_AUTH: frozenset({RunState.RUNNING, RunState.FAILED}),
    RunState.PAUSED_MODEL: frozenset({RunState.RUNNING, RunState.FAILED}),
    RunState.AWAITING_APPROVAL: frozenset(
        {RunState.RUNNING, RunState.REJECTED, RunState.FAILED}
    ),
    RunState.SUBMITTED: frozenset(),
    RunState.REJECTED: frozenset(),
    RunState.BUDGET_EXHAUSTED: frozenset(),
    RunState.NO_PROGRESS: frozenset(),
    RunState.FAILED: frozenset(),
}

_FINISHED_ATTEMPT_STATUSES = frozenset({"COMPLETED", "FAILED", "INTERRUPTED"})
_NOW_SQL = "strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
_SCHEMA_V1 = (
    f"""
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL DEFAULT ({_NOW_SQL})
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        state TEXT NOT NULL,
        config_json TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT ({_NOW_SQL}),
        updated_at TEXT NOT NULL DEFAULT ({_NOW_SQL})
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS state_transitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        from_state TEXT NOT NULL,
        to_state TEXT NOT NULL,
        reason TEXT NOT NULL,
        transitioned_at TEXT NOT NULL DEFAULT ({_NOW_SQL}),
        FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS node_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        node TEXT NOT NULL,
        attempt_number INTEGER NOT NULL,
        status TEXT NOT NULL,
        summary_json TEXT,
        started_at TEXT NOT NULL DEFAULT ({_NOW_SQL}),
        finished_at TEXT,
        FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
        UNIQUE (run_id, node, attempt_number)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_state_transitions_run_latest
    ON state_transitions(run_id, id DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_node_attempts_run_completed
    ON node_attempts(run_id, status, finished_at DESC, id DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_node_attempts_run_node_latest
    ON node_attempts(run_id, node, attempt_number DESC)
    """,
    "INSERT OR IGNORE INTO schema_version(version) VALUES (1)",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _run_from_row(row: sqlite3.Row) -> RunRecord:
    return RunRecord(
        run_id=row["run_id"],
        state=RunState(row["state"]),
        config=RunConfig.from_dict(json.loads(row["config_json"])),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _attempt_from_row(row: sqlite3.Row) -> NodeAttemptRecord:
    return NodeAttemptRecord(
        id=row["id"],
        run_id=row["run_id"],
        node=WorkflowNode(row["node"]),
        attempt_number=row["attempt_number"],
        status=row["status"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
    )


class AgentStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with closing(self.connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                connection.rollback()
                raise
            else:
                connection.commit()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("BEGIN IMMEDIATE")
            try:
                for statement in _SCHEMA_V1:
                    connection.execute(statement)
                versions = connection.execute(
                    "SELECT version FROM schema_version ORDER BY version"
                ).fetchall()
                if [row["version"] for row in versions] != [1]:
                    raise RuntimeError("unsupported agent store schema version")
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def create_run(self, run_id: str, config: RunConfig) -> RunRecord:
        config_json = _canonical_json(asdict(config))
        with self._transaction() as connection:
            try:
                connection.execute(
                    "INSERT INTO runs(run_id, state, config_json) VALUES (?, ?, ?)",
                    (run_id, RunState.CREATED.value, config_json),
                )
            except sqlite3.IntegrityError as error:
                if connection.execute(
                    "SELECT 1 FROM runs WHERE run_id = ?", (run_id,)
                ).fetchone():
                    raise RunAlreadyExists(f"run already exists: {run_id}") from error
                raise
            row = connection.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            return _run_from_row(row)

    def get_run(self, run_id: str) -> RunRecord:
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        if row is None:
            raise RunNotFound(run_id)
        return _run_from_row(row)

    def transition(self, run_id: str, target: RunState, reason: str) -> RunRecord:
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if row is None:
                raise RunNotFound(run_id)
            source = RunState(row["state"])
            if target not in _ALLOWED_TRANSITIONS[source]:
                raise InvalidTransition(f"cannot transition {source.value} to {target.value}")

            connection.execute(
                f"UPDATE runs SET state = ?, updated_at = ({_NOW_SQL}) "
                "WHERE run_id = ? AND state = ?",
                (target.value, run_id, source.value),
            )
            connection.execute(
                "INSERT INTO state_transitions(run_id, from_state, to_state, reason) "
                "VALUES (?, ?, ?, ?)",
                (run_id, source.value, target.value, reason),
            )
            updated = connection.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            return _run_from_row(updated)

    def start_node_attempt(
        self, run_id: str, node: WorkflowNode
    ) -> NodeAttemptRecord:
        with self._transaction() as connection:
            if connection.execute(
                "SELECT 1 FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone() is None:
                raise RunNotFound(run_id)
            next_attempt = connection.execute(
                "SELECT COALESCE(MAX(attempt_number), 0) + 1 "
                "FROM node_attempts WHERE run_id = ? AND node = ?",
                (run_id, node.value),
            ).fetchone()[0]
            cursor = connection.execute(
                "INSERT INTO node_attempts(run_id, node, attempt_number, status) "
                "VALUES (?, ?, ?, 'RUNNING')",
                (run_id, node.value, next_attempt),
            )
            row = connection.execute(
                "SELECT * FROM node_attempts WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return _attempt_from_row(row)

    def finish_node_attempt(
        self,
        attempt: NodeAttemptRecord,
        status: str,
        summary: dict[str, Any],
    ) -> None:
        if status not in _FINISHED_ATTEMPT_STATUSES:
            raise InvalidNodeAttempt(f"invalid finished attempt status: {status}")
        summary_json = _canonical_json(summary)
        with self._transaction() as connection:
            cursor = connection.execute(
                f"UPDATE node_attempts SET status = ?, summary_json = ?, "
                f"finished_at = ({_NOW_SQL}) "
                "WHERE id = ? AND run_id = ? AND node = ? "
                "AND attempt_number = ? AND status = 'RUNNING'",
                (
                    status,
                    summary_json,
                    attempt.id,
                    attempt.run_id,
                    attempt.node.value,
                    attempt.attempt_number,
                ),
            )
            if cursor.rowcount != 1:
                raise InvalidNodeAttempt(
                    f"attempt does not exist or is already finished: {attempt.id}"
                )

    def latest_completed_node(self, run_id: str) -> WorkflowNode | None:
        with closing(self.connect()) as connection:
            if connection.execute(
                "SELECT 1 FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone() is None:
                raise RunNotFound(run_id)
            row = connection.execute(
                "SELECT node FROM node_attempts "
                "WHERE run_id = ? AND status = 'COMPLETED' "
                "ORDER BY finished_at DESC, id DESC LIMIT 1",
                (run_id,),
            ).fetchone()
        return None if row is None else WorkflowNode(row["node"])
