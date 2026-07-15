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
_SCHEMA_VERSION_BOOTSTRAP = f"""
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL DEFAULT ({_NOW_SQL})
    )
    """


@dataclass(frozen=True)
class _Migration:
    version: int
    statements: tuple[str, ...]


_MIGRATIONS = (
    _Migration(
        version=1,
        statements=(
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
                completion_sequence INTEGER,
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
                UNIQUE (run_id, node, attempt_number),
                UNIQUE (run_id, completion_sequence)
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_state_transitions_run_latest
            ON state_transitions(run_id, id DESC)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_node_attempts_run_completed
            ON node_attempts(run_id, status, completion_sequence DESC, id DESC)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_node_attempts_run_node_latest
            ON node_attempts(run_id, node, attempt_number DESC)
            """,
        ),
    ),
)
LATEST_SCHEMA_VERSION = 1


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _validate_run_id(run_id: object) -> None:
    if type(run_id) is not str:
        raise TypeError("run_id must be a string")
    if not run_id.strip():
        raise ValueError("run_id must not be empty")


def _validate_config(config: object) -> None:
    if type(config) is not RunConfig:
        raise TypeError("config must be a RunConfig")


def _validate_run_state(target: object) -> None:
    if type(target) is not RunState:
        raise TypeError("target must be a RunState")


def _validate_workflow_node(node: object) -> None:
    if type(node) is not WorkflowNode:
        raise TypeError("node must be a WorkflowNode")


def _validate_reason(reason: object) -> None:
    if type(reason) is not str:
        raise TypeError("reason must be a string")
    if not reason.strip():
        raise ValueError("reason must not be empty")


def _validate_positive_integer(value: object, name: str) -> None:
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")


def _validate_attempt(attempt: object) -> None:
    if type(attempt) is not NodeAttemptRecord:
        raise TypeError("attempt must be a NodeAttemptRecord")
    _validate_positive_integer(attempt.id, "attempt.id")
    _validate_run_id(attempt.run_id)
    _validate_workflow_node(attempt.node)
    _validate_positive_integer(attempt.attempt_number, "attempt.attempt_number")
    if type(attempt.status) is not str:
        raise TypeError("attempt.status must be a string")
    if attempt.status != "RUNNING":
        raise InvalidNodeAttempt("attempt status must be RUNNING")


def _validate_finished_status(status: object) -> None:
    if type(status) is not str:
        raise TypeError("status must be a string")
    if status not in _FINISHED_ATTEMPT_STATUSES:
        raise InvalidNodeAttempt(f"invalid finished attempt status: {status}")


def _validate_summary(summary: object) -> None:
    if type(summary) is not dict:
        raise TypeError("summary must be a dictionary")


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
    def __init__(
        self,
        path: Path,
        *,
        _migrations: tuple[_Migration, ...] | None = None,
    ) -> None:
        self.path = Path(path)
        self._migrations = _MIGRATIONS if _migrations is None else _migrations
        if not self._migrations:
            raise ValueError("migrations must not be empty")
        expected_versions = tuple(range(1, len(self._migrations) + 1))
        actual_versions = tuple(migration.version for migration in self._migrations)
        if actual_versions != expected_versions:
            raise ValueError("migrations must be ordered and contiguous from version 1")
        self._latest_schema_version = (
            LATEST_SCHEMA_VERSION
            if _migrations is None
            else self._migrations[-1].version
        )

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
                connection.execute(_SCHEMA_VERSION_BOOTSTRAP)
                versions = connection.execute(
                    "SELECT version FROM schema_version ORDER BY version"
                ).fetchall()
                applied = {row["version"] for row in versions}
                if any(
                    version > self._latest_schema_version for version in applied
                ):
                    raise RuntimeError(
                        "database has a future schema version "
                        f"above {self._latest_schema_version}"
                    )
                known = {migration.version for migration in self._migrations}
                if not applied <= known:
                    raise RuntimeError("database has an unsupported schema version")
                for migration in self._migrations:
                    if migration.version in applied:
                        continue
                    for statement in migration.statements:
                        connection.execute(statement)
                    connection.execute(
                        "INSERT INTO schema_version(version) VALUES (?)",
                        (migration.version,),
                    )
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def create_run(self, run_id: str, config: RunConfig) -> RunRecord:
        _validate_run_id(run_id)
        _validate_config(config)
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
        _validate_run_id(run_id)
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        if row is None:
            raise RunNotFound(run_id)
        return _run_from_row(row)

    def transition(self, run_id: str, target: RunState, reason: str) -> RunRecord:
        _validate_run_id(run_id)
        _validate_run_state(target)
        _validate_reason(reason)
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if row is None:
                raise RunNotFound(run_id)
            source = RunState(row["state"])
            if target not in _ALLOWED_TRANSITIONS[source]:
                raise InvalidTransition(f"cannot transition {source.value} to {target.value}")

            cursor = connection.execute(
                f"UPDATE runs SET state = ?, updated_at = ({_NOW_SQL}) "
                "WHERE run_id = ? AND state = ?",
                (target.value, run_id, source.value),
            )
            if cursor.rowcount != 1:
                raise InvalidTransition(f"run state changed concurrently: {run_id}")
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
        _validate_run_id(run_id)
        _validate_workflow_node(node)
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
        _validate_attempt(attempt)
        _validate_finished_status(status)
        _validate_summary(summary)
        summary_json = _canonical_json(summary)
        with self._transaction() as connection:
            completion_sequence = connection.execute(
                "SELECT COALESCE(MAX(completion_sequence), 0) + 1 "
                "FROM node_attempts WHERE run_id = ?",
                (attempt.run_id,),
            ).fetchone()[0]
            cursor = connection.execute(
                f"UPDATE node_attempts SET status = ?, summary_json = ?, "
                f"finished_at = ({_NOW_SQL}), completion_sequence = ? "
                "WHERE id = ? AND run_id = ? AND node = ? "
                "AND attempt_number = ? AND status = 'RUNNING'",
                (
                    status,
                    summary_json,
                    completion_sequence,
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
        _validate_run_id(run_id)
        with closing(self.connect()) as connection:
            if connection.execute(
                "SELECT 1 FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone() is None:
                raise RunNotFound(run_id)
            row = connection.execute(
                "SELECT node FROM node_attempts "
                "WHERE run_id = ? AND status = 'COMPLETED' "
                "ORDER BY completion_sequence DESC, id DESC LIMIT 1",
                (run_id,),
            ).fetchone()
        return None if row is None else WorkflowNode(row["node"])
