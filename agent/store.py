from __future__ import annotations

import json
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass
from math import isfinite
from pathlib import Path
from typing import Any, Iterator

from .types import ModelRole, RunConfig, RunState, WorkflowNode


class InvalidTransition(ValueError):
    pass


class RunAlreadyExists(ValueError):
    pass


class RunNotFound(KeyError):
    pass


class InvalidNodeAttempt(ValueError):
    pass


class StoreConflict(ValueError):
    pass


class StoreRecordNotFound(KeyError):
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


@dataclass(frozen=True)
class ResearchPlanRecord:
    id: int
    run_id: str
    plan_version: int
    plan_hash: str
    plan: dict[str, Any]
    created_at: str


@dataclass(frozen=True)
class OperatorTaskRecord:
    id: int
    run_id: str
    task_id: str
    plan_version: int
    status: str
    task: dict[str, Any]
    result: dict[str, Any] | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ModelCallRecord:
    id: int
    run_id: str
    role: ModelRole
    node: WorkflowNode
    provider: str
    model: str
    purpose: str
    status: str
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    latency_ms: float | None
    fallback_used: bool
    provider_request_id: str | None
    error: str | None
    created_at: str


@dataclass(frozen=True)
class ArtifactRecord:
    id: int
    run_id: str
    node: WorkflowNode
    name: str
    path: str
    sha256: str
    kind: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class CommandLedgerRecord:
    id: int
    run_id: str
    node: WorkflowNode
    command_fingerprint: str
    argv: tuple[str, ...]
    status: str
    exit_code: int | None
    resource_id: str | None
    artifact_id: int | None
    error: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class CandidateRecord:
    id: int
    run_id: str
    expression_fingerprint: str
    candidate: dict[str, Any]
    status: str
    reason: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class SimulationRecord:
    id: int
    run_id: str
    simulation_id: str
    status: str
    candidate_id: int | None
    alpha_id: str | None
    result_artifact_id: int | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class DiagnosisRecord:
    id: int
    run_id: str
    failure_class: str
    next_node: WorkflowNode
    diagnosis: dict[str, Any]
    node_attempt_id: int | None
    created_at: str


@dataclass(frozen=True)
class ApprovalRecord:
    id: int
    run_id: str
    alpha_id: str
    report_hash: str
    decision: str
    reason: str | None
    consumed_at: str | None
    created_at: str


@dataclass(frozen=True)
class ExperienceRecord:
    id: int
    run_id: str
    region: str
    delay: int
    category: str
    field_ids: tuple[str, ...]
    expression_fingerprint: str
    failure_class: str | None
    hypothesis: dict[str, Any] | None
    record: dict[str, Any] | None
    metrics: dict[str, Any] | None
    final_decision: str | None
    created_at: str
    updated_at: str


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
_TERMINAL_TASK_STATUSES = frozenset({"COMPLETED", "FAILED", "BLOCKED"})
_TERMINAL_SIMULATION_STATUSES = frozenset(
    {"COMPLETE", "WARNING", "ERROR", "FAIL", "FAILED"}
)
_SIMULATION_STATUSES = frozenset(
    {"CREATED", "PENDING", "QUEUED", "RUNNING", "TIMED_OUT"}
) | _TERMINAL_SIMULATION_STATUSES
_SIMULATION_TRANSITIONS: dict[str, frozenset[str]] = {
    "CREATED": frozenset(
        {"CREATED", "PENDING", "QUEUED", "RUNNING", "TIMED_OUT"}
        | _TERMINAL_SIMULATION_STATUSES
    ),
    "PENDING": frozenset(
        {"PENDING", "QUEUED", "RUNNING", "TIMED_OUT"}
        | _TERMINAL_SIMULATION_STATUSES
    ),
    "QUEUED": frozenset(
        {"PENDING", "QUEUED", "RUNNING", "TIMED_OUT"}
        | _TERMINAL_SIMULATION_STATUSES
    ),
    "RUNNING": frozenset({"RUNNING", "TIMED_OUT"})
    | _TERMINAL_SIMULATION_STATUSES,
    "TIMED_OUT": frozenset({"TIMED_OUT", "RUNNING"})
    | _TERMINAL_SIMULATION_STATUSES,
}
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
        ),
    ),
    _Migration(
        version=2,
        statements=(
            "ALTER TABLE node_attempts ADD COLUMN completion_sequence INTEGER",
            """
            UPDATE node_attempts
            SET completion_sequence = 1 + (
                SELECT COUNT(*)
                FROM node_attempts AS earlier
                WHERE earlier.run_id = node_attempts.run_id
                  AND earlier.status IN ('COMPLETED', 'FAILED', 'INTERRUPTED')
                  AND (
                      (
                          earlier.finished_at IS NULL
                          AND node_attempts.finished_at IS NOT NULL
                      )
                      OR earlier.finished_at < node_attempts.finished_at
                      OR (
                          (
                              earlier.finished_at = node_attempts.finished_at
                              OR (
                                  earlier.finished_at IS NULL
                                  AND node_attempts.finished_at IS NULL
                              )
                          )
                          AND earlier.id < node_attempts.id
                      )
                  )
            )
            WHERE status IN ('COMPLETED', 'FAILED', 'INTERRUPTED')
            """,
            "DROP INDEX idx_node_attempts_run_completed",
            """
            CREATE INDEX idx_node_attempts_run_completed
            ON node_attempts(run_id, status, completion_sequence DESC, id DESC)
            """,
            """
            CREATE UNIQUE INDEX idx_node_attempts_run_completion_sequence
            ON node_attempts(run_id, completion_sequence)
            WHERE completion_sequence IS NOT NULL
            """,
        ),
    ),
    _Migration(
        version=3,
        statements=(
            f"""
            CREATE TABLE research_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                plan_version INTEGER NOT NULL CHECK (plan_version > 0),
                plan_hash TEXT NOT NULL CHECK (length(trim(plan_hash)) > 0),
                plan_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT ({_NOW_SQL}),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
                UNIQUE (run_id, plan_version),
                UNIQUE (run_id, plan_hash)
            )
            """,
            f"""
            CREATE TABLE operator_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                task_id TEXT NOT NULL CHECK (length(trim(task_id)) > 0),
                plan_version INTEGER NOT NULL CHECK (plan_version > 0),
                status TEXT NOT NULL,
                task_json TEXT NOT NULL,
                result_json TEXT,
                created_at TEXT NOT NULL DEFAULT ({_NOW_SQL}),
                updated_at TEXT NOT NULL DEFAULT ({_NOW_SQL}),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
                FOREIGN KEY (run_id, plan_version)
                    REFERENCES research_plans(run_id, plan_version) ON DELETE CASCADE,
                UNIQUE (run_id, task_id)
            )
            """,
            f"""
            CREATE TABLE model_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('planner', 'operator')),
                node TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                purpose TEXT NOT NULL,
                status TEXT NOT NULL,
                input_tokens INTEGER CHECK (input_tokens IS NULL OR input_tokens >= 0),
                output_tokens INTEGER CHECK (output_tokens IS NULL OR output_tokens >= 0),
                cost_usd REAL CHECK (cost_usd IS NULL OR cost_usd >= 0),
                latency_ms REAL CHECK (latency_ms IS NULL OR latency_ms >= 0),
                fallback_used INTEGER NOT NULL CHECK (fallback_used IN (0, 1)),
                provider_request_id TEXT,
                error TEXT,
                created_at TEXT NOT NULL DEFAULT ({_NOW_SQL}),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            )
            """,
            "CREATE INDEX idx_model_calls_run_role ON model_calls(run_id, role, id)",
            f"""
            CREATE TABLE artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                node TEXT NOT NULL,
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                kind TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT ({_NOW_SQL}),
                updated_at TEXT NOT NULL DEFAULT ({_NOW_SQL}),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
                UNIQUE (id, run_id),
                UNIQUE (run_id, node, name)
            )
            """,
            f"""
            CREATE TABLE command_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                node TEXT NOT NULL,
                command_fingerprint TEXT NOT NULL,
                argv_json TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('STARTED', 'COMPLETED', 'FAILED')),
                exit_code INTEGER,
                resource_id TEXT,
                artifact_id INTEGER,
                error TEXT,
                created_at TEXT NOT NULL DEFAULT ({_NOW_SQL}),
                updated_at TEXT NOT NULL DEFAULT ({_NOW_SQL}),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
                FOREIGN KEY (artifact_id, run_id) REFERENCES artifacts(id, run_id),
                UNIQUE (run_id, command_fingerprint)
            )
            """,
            """
            CREATE INDEX idx_command_ledger_run_status
            ON command_ledger(run_id, status)
            """,
            f"""
            CREATE TABLE candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                expression_fingerprint TEXT NOT NULL,
                candidate_json TEXT NOT NULL,
                status TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL DEFAULT ({_NOW_SQL}),
                updated_at TEXT NOT NULL DEFAULT ({_NOW_SQL}),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
                UNIQUE (id, run_id),
                UNIQUE (run_id, expression_fingerprint)
            )
            """,
            f"""
            CREATE TABLE simulations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                candidate_id INTEGER,
                simulation_id TEXT NOT NULL CHECK (length(trim(simulation_id)) > 0),
                alpha_id TEXT,
                status TEXT NOT NULL,
                result_artifact_id INTEGER,
                created_at TEXT NOT NULL DEFAULT ({_NOW_SQL}),
                updated_at TEXT NOT NULL DEFAULT ({_NOW_SQL}),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
                FOREIGN KEY (candidate_id, run_id) REFERENCES candidates(id, run_id),
                FOREIGN KEY (result_artifact_id, run_id)
                    REFERENCES artifacts(id, run_id),
                UNIQUE (run_id, simulation_id)
            )
            """,
            """
            CREATE UNIQUE INDEX idx_node_attempts_id_run
            ON node_attempts(id, run_id)
            """,
            f"""
            CREATE TABLE diagnoses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                node_attempt_id INTEGER,
                failure_class TEXT NOT NULL,
                next_node TEXT NOT NULL,
                diagnosis_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT ({_NOW_SQL}),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
                FOREIGN KEY (node_attempt_id, run_id)
                    REFERENCES node_attempts(id, run_id)
            )
            """,
            f"""
            CREATE TABLE approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                alpha_id TEXT NOT NULL,
                report_hash TEXT NOT NULL,
                decision TEXT NOT NULL DEFAULT 'APPROVED' CHECK (decision = 'APPROVED'),
                reason TEXT,
                consumed_at TEXT,
                created_at TEXT NOT NULL DEFAULT ({_NOW_SQL}),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
                UNIQUE (run_id, alpha_id, report_hash)
            )
            """,
            f"""
            CREATE TABLE experiences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                region TEXT NOT NULL,
                delay INTEGER NOT NULL,
                category TEXT NOT NULL,
                failure_class TEXT,
                expression_fingerprint TEXT NOT NULL,
                hypothesis_json TEXT,
                record_json TEXT,
                metrics_json TEXT,
                final_decision TEXT,
                created_at TEXT NOT NULL DEFAULT ({_NOW_SQL}),
                updated_at TEXT NOT NULL DEFAULT ({_NOW_SQL}),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            )
            """,
            """
            CREATE INDEX idx_experiences_scope_failure_created
            ON experiences(region, delay, category, failure_class, created_at DESC, id DESC)
            """,
            """
            CREATE TABLE experience_fields (
                experience_id INTEGER NOT NULL,
                field_id TEXT NOT NULL,
                FOREIGN KEY (experience_id) REFERENCES experiences(id) ON DELETE CASCADE,
                PRIMARY KEY (experience_id, field_id)
            )
            """,
            "CREATE INDEX idx_experience_fields_field ON experience_fields(field_id)",
        ),
    ),
    _Migration(
        version=4,
        statements=(
            "CREATE INDEX idx_experiences_scope_fingerprint "
            "ON experiences(region, delay, category, expression_fingerprint)",
            "CREATE INDEX idx_command_ledger_artifact "
            "ON command_ledger(artifact_id)",
        ),
    ),
)
LATEST_SCHEMA_VERSION = _MIGRATIONS[-1].version


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
    if not isinstance(summary, dict):
        raise TypeError("summary must be a dictionary")


def _validate_nonblank_string(value: object, name: str) -> None:
    if type(value) is not str:
        raise TypeError(f"{name} must be a string")
    if not value.strip():
        raise ValueError(f"{name} must not be empty")


def _validated_json_object(value: object, name: str) -> str:
    if type(value) is not dict:
        raise TypeError(f"{name} must be a dictionary")
    _validate_json_native(value, name, set())
    return _canonical_json(value)


def _validate_json_native(value: object, name: str, active: set[int]) -> None:
    if value is None or type(value) in {bool, int, str}:
        return
    if type(value) is float:
        if not isfinite(value):
            raise ValueError(f"{name} must be finite")
        return
    if type(value) not in {list, dict}:
        raise TypeError(f"{name} must contain only JSON-native values")

    identity = id(value)
    if identity in active:
        raise ValueError(f"{name} must not contain circular references")
    active.add(identity)
    try:
        if type(value) is list:
            for index, item in enumerate(value):
                _validate_json_native(item, f"{name}[{index}]", active)
            return
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError(f"{name} keys must be strings")
            _validate_json_native(item, f"{name}.{key}", active)
    finally:
        active.remove(identity)


def _validate_optional_nonnegative_integer(value: object, name: str) -> None:
    if value is None:
        return
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer or None")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _validate_optional_nonnegative_number(value: object, name: str) -> None:
    if value is None:
        return
    if type(value) not in {int, float}:
        raise TypeError(f"{name} must be a number or None")
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and non-negative")


def _validate_optional_string(value: object, name: str) -> None:
    if value is None:
        return
    if type(value) is not str:
        raise TypeError(f"{name} must be a string or None")
    if not value.strip():
        raise ValueError(f"{name} must not be empty")


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


def _research_plan_from_row(row: sqlite3.Row) -> ResearchPlanRecord:
    return ResearchPlanRecord(
        id=row["id"],
        run_id=row["run_id"],
        plan_version=row["plan_version"],
        plan_hash=row["plan_hash"],
        plan=json.loads(row["plan_json"]),
        created_at=row["created_at"],
    )


def _operator_task_from_row(row: sqlite3.Row) -> OperatorTaskRecord:
    return OperatorTaskRecord(
        id=row["id"],
        run_id=row["run_id"],
        task_id=row["task_id"],
        plan_version=row["plan_version"],
        status=row["status"],
        task=json.loads(row["task_json"]),
        result=None if row["result_json"] is None else json.loads(row["result_json"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _model_call_from_row(row: sqlite3.Row) -> ModelCallRecord:
    return ModelCallRecord(
        id=row["id"],
        run_id=row["run_id"],
        role=ModelRole(row["role"]),
        node=WorkflowNode(row["node"]),
        provider=row["provider"],
        model=row["model"],
        purpose=row["purpose"],
        status=row["status"],
        input_tokens=row["input_tokens"],
        output_tokens=row["output_tokens"],
        cost_usd=row["cost_usd"],
        latency_ms=row["latency_ms"],
        fallback_used=bool(row["fallback_used"]),
        provider_request_id=row["provider_request_id"],
        error=row["error"],
        created_at=row["created_at"],
    )


def _artifact_from_row(row: sqlite3.Row) -> ArtifactRecord:
    return ArtifactRecord(
        id=row["id"],
        run_id=row["run_id"],
        node=WorkflowNode(row["node"]),
        name=row["name"],
        path=row["path"],
        sha256=row["sha256"],
        kind=row["kind"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _command_from_row(
    row: sqlite3.Row, *, status: str | None = None
) -> CommandLedgerRecord:
    return CommandLedgerRecord(
        id=row["id"],
        run_id=row["run_id"],
        node=WorkflowNode(row["node"]),
        command_fingerprint=row["command_fingerprint"],
        argv=tuple(json.loads(row["argv_json"])),
        status=row["status"] if status is None else status,
        exit_code=row["exit_code"],
        resource_id=row["resource_id"],
        artifact_id=row["artifact_id"],
        error=row["error"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _candidate_from_row(row: sqlite3.Row) -> CandidateRecord:
    return CandidateRecord(
        id=row["id"],
        run_id=row["run_id"],
        expression_fingerprint=row["expression_fingerprint"],
        candidate=json.loads(row["candidate_json"]),
        status=row["status"],
        reason=row["reason"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _simulation_from_row(row: sqlite3.Row) -> SimulationRecord:
    return SimulationRecord(
        id=row["id"],
        run_id=row["run_id"],
        simulation_id=row["simulation_id"],
        status=row["status"],
        candidate_id=row["candidate_id"],
        alpha_id=row["alpha_id"],
        result_artifact_id=row["result_artifact_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _diagnosis_from_row(row: sqlite3.Row) -> DiagnosisRecord:
    return DiagnosisRecord(
        id=row["id"],
        run_id=row["run_id"],
        failure_class=row["failure_class"],
        next_node=WorkflowNode(row["next_node"]),
        diagnosis=json.loads(row["diagnosis_json"]),
        node_attempt_id=row["node_attempt_id"],
        created_at=row["created_at"],
    )


def _approval_from_row(row: sqlite3.Row) -> ApprovalRecord:
    return ApprovalRecord(
        id=row["id"],
        run_id=row["run_id"],
        alpha_id=row["alpha_id"],
        report_hash=row["report_hash"],
        decision=row["decision"],
        reason=row["reason"],
        consumed_at=row["consumed_at"],
        created_at=row["created_at"],
    )


def _experience_from_row(
    row: sqlite3.Row, field_ids: tuple[str, ...]
) -> ExperienceRecord:
    def load_optional(column: str) -> dict[str, Any] | None:
        return None if row[column] is None else json.loads(row[column])

    return ExperienceRecord(
        id=row["id"],
        run_id=row["run_id"],
        region=row["region"],
        delay=row["delay"],
        category=row["category"],
        field_ids=field_ids,
        expression_fingerprint=row["expression_fingerprint"],
        failure_class=row["failure_class"],
        hypothesis=load_optional("hypothesis_json"),
        record=load_optional("record_json"),
        metrics=load_optional("metrics_json"),
        final_decision=row["final_decision"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
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
        self._latest_schema_version = self._migrations[-1].version

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
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(_SCHEMA_VERSION_BOOTSTRAP)
                versions = connection.execute(
                    "SELECT version FROM schema_version ORDER BY version"
                ).fetchall()
                applied = [row["version"] for row in versions]
                if applied and applied[-1] > self._latest_schema_version:
                    raise RuntimeError(
                        "database has a future schema version "
                        f"above {self._latest_schema_version}"
                    )
                expected_prefix = list(range(1, len(applied) + 1))
                if applied != expected_prefix:
                    raise RuntimeError(
                        "applied schema versions must be a contiguous prefix"
                    )
                for migration in self._migrations[len(applied) :]:
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
            connection.execute("PRAGMA journal_mode = WAL")

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

    def record_research_plan(
        self,
        run_id: str,
        plan_version: int,
        plan_hash: str,
        plan: dict[str, Any],
    ) -> ResearchPlanRecord:
        _validate_run_id(run_id)
        _validate_positive_integer(plan_version, "plan_version")
        _validate_nonblank_string(plan_hash, "plan_hash")
        plan_json = _validated_json_object(plan, "plan")
        with self._transaction() as connection:
            try:
                cursor = connection.execute(
                    "INSERT INTO research_plans"
                    "(run_id, plan_version, plan_hash, plan_json) VALUES (?, ?, ?, ?)",
                    (run_id, plan_version, plan_hash, plan_json),
                )
            except sqlite3.IntegrityError as error:
                if connection.execute(
                    "SELECT 1 FROM research_plans "
                    "WHERE run_id = ? AND (plan_version = ? OR plan_hash = ?)",
                    (run_id, plan_version, plan_hash),
                ).fetchone():
                    raise StoreConflict(
                        f"research plan version or hash already exists for run: {run_id}"
                    ) from error
                if connection.execute(
                    "SELECT 1 FROM runs WHERE run_id = ?", (run_id,)
                ).fetchone() is None:
                    raise RunNotFound(run_id) from error
                raise
            row = connection.execute(
                "SELECT * FROM research_plans WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return _research_plan_from_row(row)

    def get_latest_research_plan(self, run_id: str) -> ResearchPlanRecord | None:
        _validate_run_id(run_id)
        with closing(self.connect()) as connection:
            if connection.execute(
                "SELECT 1 FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone() is None:
                raise RunNotFound(run_id)
            row = connection.execute(
                "SELECT * FROM research_plans WHERE run_id = ? "
                "ORDER BY plan_version DESC LIMIT 1",
                (run_id,),
            ).fetchone()
        return None if row is None else _research_plan_from_row(row)

    def record_operator_task(
        self,
        run_id: str,
        task_id: str,
        plan_version: int,
        task: dict[str, Any],
    ) -> OperatorTaskRecord:
        _validate_run_id(run_id)
        _validate_nonblank_string(task_id, "task_id")
        _validate_positive_integer(plan_version, "plan_version")
        task_json = _validated_json_object(task, "task")
        with self._transaction() as connection:
            try:
                cursor = connection.execute(
                    "INSERT INTO operator_tasks"
                    "(run_id, task_id, plan_version, status, task_json) "
                    "VALUES (?, ?, ?, 'PENDING', ?)",
                    (run_id, task_id, plan_version, task_json),
                )
            except sqlite3.IntegrityError as error:
                if connection.execute(
                    "SELECT 1 FROM operator_tasks WHERE run_id = ? AND task_id = ?",
                    (run_id, task_id),
                ).fetchone():
                    raise StoreConflict(
                        f"operator task already exists: {run_id}.{task_id}"
                    ) from error
                if connection.execute(
                    "SELECT 1 FROM runs WHERE run_id = ?", (run_id,)
                ).fetchone() is None:
                    raise RunNotFound(run_id) from error
                raise StoreRecordNotFound(
                    f"research plan does not exist: {run_id}.{plan_version}"
                ) from error
            row = connection.execute(
                "SELECT * FROM operator_tasks WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return _operator_task_from_row(row)

    def complete_operator_task(
        self,
        run_id: str,
        task_id: str,
        status: str,
        result: dict[str, Any],
    ) -> OperatorTaskRecord:
        _validate_run_id(run_id)
        _validate_nonblank_string(task_id, "task_id")
        _validate_nonblank_string(status, "status")
        if status not in _TERMINAL_TASK_STATUSES:
            raise ValueError(f"invalid terminal operator task status: {status}")
        result_json = _validated_json_object(result, "result")
        with self._transaction() as connection:
            cursor = connection.execute(
                f"UPDATE operator_tasks SET status = ?, result_json = ?, "
                f"updated_at = ({_NOW_SQL}) "
                "WHERE run_id = ? AND task_id = ? AND result_json IS NULL",
                (status, result_json, run_id, task_id),
            )
            if cursor.rowcount != 1:
                existing = connection.execute(
                    "SELECT 1 FROM operator_tasks WHERE run_id = ? AND task_id = ?",
                    (run_id, task_id),
                ).fetchone()
                if existing is None:
                    raise StoreRecordNotFound(f"operator task not found: {run_id}.{task_id}")
                raise StoreConflict(f"operator task is already complete: {run_id}.{task_id}")
            row = connection.execute(
                "SELECT * FROM operator_tasks WHERE run_id = ? AND task_id = ?",
                (run_id, task_id),
            ).fetchone()
            return _operator_task_from_row(row)

    def get_operator_task(self, run_id: str, task_id: str) -> OperatorTaskRecord:
        _validate_run_id(run_id)
        _validate_nonblank_string(task_id, "task_id")
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT * FROM operator_tasks WHERE run_id = ? AND task_id = ?",
                (run_id, task_id),
            ).fetchone()
        if row is None:
            raise StoreRecordNotFound(f"operator task not found: {run_id}.{task_id}")
        return _operator_task_from_row(row)

    def record_model_call(
        self,
        run_id: str,
        role: ModelRole,
        node: WorkflowNode,
        provider: str,
        model: str,
        purpose: str,
        status: str,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_usd: float | None = None,
        latency_ms: float | None = None,
        fallback_used: bool = False,
        provider_request_id: str | None = None,
        error: str | None = None,
    ) -> ModelCallRecord:
        _validate_run_id(run_id)
        if type(role) is not ModelRole:
            raise TypeError("role must be a ModelRole")
        _validate_workflow_node(node)
        for value, name in (
            (provider, "provider"),
            (model, "model"),
            (purpose, "purpose"),
            (status, "status"),
        ):
            _validate_nonblank_string(value, name)
        _validate_optional_nonnegative_integer(input_tokens, "input_tokens")
        _validate_optional_nonnegative_integer(output_tokens, "output_tokens")
        _validate_optional_nonnegative_number(cost_usd, "cost_usd")
        _validate_optional_nonnegative_number(latency_ms, "latency_ms")
        if type(fallback_used) is not bool:
            raise TypeError("fallback_used must be a boolean")
        _validate_optional_string(provider_request_id, "provider_request_id")
        _validate_optional_string(error, "error")
        with self._transaction() as connection:
            try:
                cursor = connection.execute(
                    "INSERT INTO model_calls"
                    "(run_id, role, node, provider, model, purpose, status, "
                    "input_tokens, output_tokens, cost_usd, latency_ms, fallback_used, "
                    "provider_request_id, error) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        run_id,
                        role.value,
                        node.value,
                        provider,
                        model,
                        purpose,
                        status,
                        input_tokens,
                        output_tokens,
                        cost_usd,
                        latency_ms,
                        int(fallback_used),
                        provider_request_id,
                        error,
                    ),
                )
            except sqlite3.IntegrityError as insert_error:
                if connection.execute(
                    "SELECT 1 FROM runs WHERE run_id = ?", (run_id,)
                ).fetchone() is None:
                    raise RunNotFound(run_id) from insert_error
                raise
            row = connection.execute(
                "SELECT * FROM model_calls WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return _model_call_from_row(row)

    def usage_summary(self, run_id: str) -> dict[str, dict[str, int | float]]:
        _validate_run_id(run_id)
        with closing(self.connect()) as connection:
            if connection.execute(
                "SELECT 1 FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone() is None:
                raise RunNotFound(run_id)
            rows = connection.execute(
                "SELECT role, COUNT(*) AS calls, "
                "COALESCE(SUM(input_tokens), 0) AS input_tokens, "
                "COALESCE(SUM(output_tokens), 0) AS output_tokens, "
                "COALESCE(SUM(cost_usd), 0.0) AS cost_usd, "
                "COALESCE(SUM(latency_ms), 0.0) AS latency_ms, "
                "SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failures, "
                "SUM(fallback_used) AS fallbacks "
                "FROM model_calls WHERE run_id = ? GROUP BY role",
                (run_id,),
            ).fetchall()
        summary: dict[str, dict[str, int | float]] = {
            role.value: {
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "latency_ms": 0.0,
                "failures": 0,
                "fallbacks": 0,
            }
            for role in ModelRole
        }
        for row in rows:
            summary[row["role"]] = {
                "calls": row["calls"],
                "input_tokens": row["input_tokens"],
                "output_tokens": row["output_tokens"],
                "cost_usd": row["cost_usd"],
                "latency_ms": row["latency_ms"],
                "failures": row["failures"],
                "fallbacks": row["fallbacks"],
            }
        return summary

    def add_artifact(
        self,
        run_id: str,
        node: WorkflowNode,
        name: str,
        path: str | Path,
        sha256: str,
        kind: str = "json",
    ) -> ArtifactRecord:
        path = self._validate_artifact_values(
            run_id, node, name, path, sha256, kind
        )
        with self._transaction() as connection:
            try:
                cursor = connection.execute(
                    "INSERT INTO artifacts(run_id, node, name, path, sha256, kind) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (run_id, node.value, name, path, sha256, kind),
                )
            except sqlite3.IntegrityError as error:
                if connection.execute(
                    "SELECT 1 FROM artifacts WHERE run_id = ? AND node = ? AND name = ?",
                    (run_id, node.value, name),
                ).fetchone():
                    raise StoreConflict(
                        f"artifact already exists: {run_id}.{node.value}.{name}"
                    ) from error
                if connection.execute(
                    "SELECT 1 FROM runs WHERE run_id = ?", (run_id,)
                ).fetchone() is None:
                    raise RunNotFound(run_id) from error
                raise
            row = connection.execute(
                "SELECT * FROM artifacts WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return _artifact_from_row(row)

    def add_or_update_artifact(
        self,
        run_id: str,
        node: WorkflowNode,
        name: str,
        path: str | Path,
        sha256: str,
        kind: str = "json",
    ) -> ArtifactRecord:
        path = self._validate_artifact_values(
            run_id, node, name, path, sha256, kind
        )
        with self._transaction() as connection:
            try:
                connection.execute(
                    f"INSERT INTO artifacts(run_id, node, name, path, sha256, kind) "
                    f"VALUES (?, ?, ?, ?, ?, ?) "
                    f"ON CONFLICT(run_id, node, name) DO UPDATE SET "
                    f"path = excluded.path, sha256 = excluded.sha256, kind = excluded.kind, "
                    f"updated_at = ({_NOW_SQL})",
                    (run_id, node.value, name, path, sha256, kind),
                )
            except sqlite3.IntegrityError as error:
                if connection.execute(
                    "SELECT 1 FROM runs WHERE run_id = ?", (run_id,)
                ).fetchone() is None:
                    raise RunNotFound(run_id) from error
                raise
            row = connection.execute(
                "SELECT * FROM artifacts WHERE run_id = ? AND node = ? AND name = ?",
                (run_id, node.value, name),
            ).fetchone()
            return _artifact_from_row(row)

    def get_artifact(self, artifact_id: int) -> ArtifactRecord:
        _validate_positive_integer(artifact_id, "artifact_id")
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone()
        if row is None:
            raise StoreRecordNotFound(f"artifact not found: {artifact_id}")
        return _artifact_from_row(row)

    def reserve_command(
        self,
        run_id: str,
        node: WorkflowNode,
        fingerprint: str,
        argv: tuple[str, ...] | list[str],
    ) -> CommandLedgerRecord:
        _validate_run_id(run_id)
        _validate_workflow_node(node)
        _validate_nonblank_string(fingerprint, "fingerprint")
        argv_json = self._validated_argv(argv)
        with self._transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM command_ledger "
                "WHERE run_id = ? AND command_fingerprint = ?",
                (run_id, fingerprint),
            ).fetchone()
            if existing is not None:
                projection = (
                    "RECOVERY_REQUIRED"
                    if existing["status"] == "STARTED"
                    else existing["status"]
                )
                return _command_from_row(existing, status=projection)
            try:
                cursor = connection.execute(
                    "INSERT INTO command_ledger"
                    "(run_id, node, command_fingerprint, argv_json, status) "
                    "VALUES (?, ?, ?, ?, 'STARTED')",
                    (run_id, node.value, fingerprint, argv_json),
                )
            except sqlite3.IntegrityError as error:
                if connection.execute(
                    "SELECT 1 FROM runs WHERE run_id = ?", (run_id,)
                ).fetchone() is None:
                    raise RunNotFound(run_id) from error
                raise
            row = connection.execute(
                "SELECT * FROM command_ledger WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return _command_from_row(row)

    def mark_command_resource(
        self, command_id: int, resource_id: str
    ) -> CommandLedgerRecord:
        _validate_positive_integer(command_id, "command_id")
        _validate_nonblank_string(resource_id, "resource_id")
        with self._transaction() as connection:
            cursor = connection.execute(
                f"UPDATE command_ledger SET resource_id = COALESCE(resource_id, ?), "
                f"updated_at = ({_NOW_SQL}) WHERE id = ? AND status = 'STARTED' "
                "AND (resource_id IS NULL OR resource_id = ?)",
                (resource_id, command_id, resource_id),
            )
            row = connection.execute(
                "SELECT * FROM command_ledger WHERE id = ?", (command_id,)
            ).fetchone()
            if row is None:
                raise StoreRecordNotFound(f"command not found: {command_id}")
            if cursor.rowcount != 1:
                if row["status"] != "STARTED":
                    raise StoreConflict(f"command is already terminal: {command_id}")
                raise StoreConflict(
                    f"command resource is already assigned: {command_id}"
                )
            return _command_from_row(row)

    def complete_command(
        self,
        command_id: int,
        exit_code: int,
        resource_id: str | None = None,
        artifact_id: int | None = None,
    ) -> CommandLedgerRecord:
        _validate_positive_integer(command_id, "command_id")
        self._validate_exit_code(exit_code, "exit_code", optional=False)
        if resource_id is not None:
            _validate_nonblank_string(resource_id, "resource_id")
        if artifact_id is not None:
            _validate_positive_integer(artifact_id, "artifact_id")
        with self._transaction() as connection:
            self._validate_command_resource_link(connection, command_id, resource_id)
            self._validate_command_artifact_link(connection, command_id, artifact_id)
            try:
                cursor = connection.execute(
                    f"UPDATE command_ledger SET status = 'COMPLETED', exit_code = ?, "
                    f"resource_id = COALESCE(resource_id, ?), "
                    f"artifact_id = COALESCE(?, artifact_id), updated_at = ({_NOW_SQL}) "
                    "WHERE id = ? AND status = 'STARTED'",
                    (exit_code, resource_id, artifact_id, command_id),
                )
            except sqlite3.IntegrityError as error:
                raise StoreRecordNotFound(
                    f"artifact does not exist: {artifact_id}"
                ) from error
            return self._command_after_terminal_update(connection, command_id, cursor)

    def fail_command(
        self,
        command_id: int,
        error: str,
        exit_code: int | None = None,
        resource_id: str | None = None,
        artifact_id: int | None = None,
    ) -> CommandLedgerRecord:
        _validate_positive_integer(command_id, "command_id")
        _validate_nonblank_string(error, "error")
        self._validate_exit_code(exit_code, "exit_code", optional=True)
        if resource_id is not None:
            _validate_nonblank_string(resource_id, "resource_id")
        if artifact_id is not None:
            _validate_positive_integer(artifact_id, "artifact_id")
        with self._transaction() as connection:
            self._validate_command_resource_link(connection, command_id, resource_id)
            self._validate_command_artifact_link(connection, command_id, artifact_id)
            try:
                cursor = connection.execute(
                    f"UPDATE command_ledger SET status = 'FAILED', error = ?, "
                    f"exit_code = ?, resource_id = COALESCE(resource_id, ?), "
                    f"artifact_id = COALESCE(?, artifact_id), updated_at = ({_NOW_SQL}) "
                    "WHERE id = ? AND status = 'STARTED'",
                    (error, exit_code, resource_id, artifact_id, command_id),
                )
            except sqlite3.IntegrityError as db_error:
                raise StoreRecordNotFound(
                    f"artifact does not exist: {artifact_id}"
                ) from db_error
            return self._command_after_terminal_update(connection, command_id, cursor)

    def get_command(self, command_id: int) -> CommandLedgerRecord:
        _validate_positive_integer(command_id, "command_id")
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT * FROM command_ledger WHERE id = ?", (command_id,)
            ).fetchone()
        if row is None:
            raise StoreRecordNotFound(f"command not found: {command_id}")
        return _command_from_row(row)

    def get_command_for_artifact(self, artifact_id: int) -> CommandLedgerRecord:
        """Return the completed command that produced one registered artifact."""
        _validate_positive_integer(artifact_id, "artifact_id")
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT * FROM command_ledger WHERE artifact_id = ? "
                "AND status = 'COMPLETED' ORDER BY id DESC LIMIT 1",
                (artifact_id,),
            ).fetchone()
        if row is None:
            raise StoreRecordNotFound(
                f"completed command not found for artifact: {artifact_id}"
            )
        return _command_from_row(row)

    def list_completed_commands(
        self, run_id: str, node: WorkflowNode
    ) -> list[CommandLedgerRecord]:
        """Return completed commands for one run/node in ledger order."""
        _validate_run_id(run_id)
        _validate_workflow_node(node)
        with closing(self.connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM command_ledger WHERE run_id = ? AND node = ? "
                "AND status = 'COMPLETED' ORDER BY id",
                (run_id, node.value),
            ).fetchall()
        return [_command_from_row(row) for row in rows]

    def add_candidate(
        self,
        run_id: str,
        fingerprint: str,
        candidate: dict[str, Any],
        status: str = "ACCEPTED",
        reason: str | None = None,
    ) -> CandidateRecord:
        _validate_run_id(run_id)
        _validate_nonblank_string(fingerprint, "fingerprint")
        candidate_json = _validated_json_object(candidate, "candidate")
        _validate_nonblank_string(status, "status")
        _validate_optional_string(reason, "reason")
        status = status.strip()
        reason = None if reason is None else reason.strip()
        with self._transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM candidates "
                "WHERE run_id = ? AND expression_fingerprint = ?",
                (run_id, fingerprint),
            ).fetchone()
            if existing is not None:
                if (
                    existing["candidate_json"] != candidate_json
                    or existing["status"] != status
                    or existing["reason"] != reason
                ):
                    raise StoreConflict(
                        f"candidate fingerprint has conflicting record: {run_id}.{fingerprint}"
                    )
                return _candidate_from_row(existing)
            try:
                cursor = connection.execute(
                    "INSERT INTO candidates"
                    "(run_id, expression_fingerprint, candidate_json, status, reason) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (run_id, fingerprint, candidate_json, status, reason),
                )
            except sqlite3.IntegrityError as error:
                raise RunNotFound(run_id) from error
            row = connection.execute(
                "SELECT * FROM candidates WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return _candidate_from_row(row)

    def get_candidate_by_fingerprint(
        self, run_id: str, fingerprint: str
    ) -> CandidateRecord:
        _validate_run_id(run_id)
        _validate_nonblank_string(fingerprint, "fingerprint")
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT * FROM candidates "
                "WHERE run_id = ? AND expression_fingerprint = ?",
                (run_id, fingerprint),
            ).fetchone()
        if row is None:
            raise StoreRecordNotFound(f"candidate not found: {run_id}.{fingerprint}")
        return _candidate_from_row(row)

    def record_simulation(
        self,
        run_id: str,
        simulation_id: str,
        status: str,
        candidate_id: int | None = None,
        alpha_id: str | None = None,
        result_artifact_id: int | None = None,
    ) -> SimulationRecord:
        self._validate_simulation_values(
            run_id, simulation_id, status, candidate_id, alpha_id, result_artifact_id
        )
        with self._transaction() as connection:
            self._validate_run_scoped_links(
                connection, run_id, candidate_id, result_artifact_id
            )
            try:
                cursor = connection.execute(
                    "INSERT INTO simulations"
                    "(run_id, simulation_id, status, candidate_id, alpha_id, "
                    "result_artifact_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        run_id,
                        simulation_id,
                        status,
                        candidate_id,
                        alpha_id,
                        result_artifact_id,
                    ),
                )
            except sqlite3.IntegrityError as error:
                if connection.execute(
                    "SELECT 1 FROM simulations WHERE run_id = ? AND simulation_id = ?",
                    (run_id, simulation_id),
                ).fetchone():
                    raise StoreConflict(
                        f"simulation already exists: {run_id}.{simulation_id}"
                    ) from error
                raise RunNotFound(run_id) from error
            row = connection.execute(
                "SELECT * FROM simulations WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return _simulation_from_row(row)

    def update_simulation(
        self,
        run_id: str,
        simulation_id: str,
        status: str,
        alpha_id: str | None = None,
        result_artifact_id: int | None = None,
    ) -> SimulationRecord:
        self._validate_simulation_values(
            run_id, simulation_id, status, None, alpha_id, result_artifact_id
        )
        with self._transaction() as connection:
            self._validate_run_scoped_links(connection, run_id, None, result_artifact_id)
            existing = connection.execute(
                "SELECT * FROM simulations WHERE run_id = ? AND simulation_id = ?",
                (run_id, simulation_id),
            ).fetchone()
            if existing is None:
                raise StoreRecordNotFound(
                    f"simulation not found: {run_id}.{simulation_id}"
                )
            source_status = existing["status"]
            if source_status in _TERMINAL_SIMULATION_STATUSES:
                if status != source_status:
                    raise StoreConflict(
                        f"simulation is terminal: {run_id}.{simulation_id}.{source_status}"
                    )
            elif status not in _SIMULATION_TRANSITIONS.get(
                source_status, frozenset()
            ):
                raise StoreConflict(
                    f"invalid simulation transition: {source_status} to {status}"
                )
            if alpha_id is not None and existing["alpha_id"] not in {None, alpha_id}:
                raise StoreConflict(
                    f"simulation alpha_id is already assigned: {run_id}.{simulation_id}"
                )
            if (
                result_artifact_id is not None
                and existing["result_artifact_id"] not in {None, result_artifact_id}
            ):
                raise StoreConflict(
                    "simulation result_artifact_id is already assigned: "
                    f"{run_id}.{simulation_id}"
                )
            if (
                source_status == status
                and (alpha_id is None or alpha_id == existing["alpha_id"])
                and (
                    result_artifact_id is None
                    or result_artifact_id == existing["result_artifact_id"]
                )
            ):
                return _simulation_from_row(existing)
            cursor = connection.execute(
                f"UPDATE simulations SET status = ?, "
                f"alpha_id = COALESCE(alpha_id, ?), "
                f"result_artifact_id = COALESCE(result_artifact_id, ?), "
                f"updated_at = ({_NOW_SQL}) "
                "WHERE run_id = ? AND simulation_id = ?",
                (status, alpha_id, result_artifact_id, run_id, simulation_id),
            )
            if cursor.rowcount != 1:
                raise StoreRecordNotFound(
                    f"simulation not found: {run_id}.{simulation_id}"
                )
            row = connection.execute(
                "SELECT * FROM simulations WHERE run_id = ? AND simulation_id = ?",
                (run_id, simulation_id),
            ).fetchone()
            return _simulation_from_row(row)

    def get_simulation(self, run_id: str, simulation_id: str) -> SimulationRecord:
        _validate_run_id(run_id)
        _validate_nonblank_string(simulation_id, "simulation_id")
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT * FROM simulations WHERE run_id = ? AND simulation_id = ?",
                (run_id, simulation_id),
            ).fetchone()
        if row is None:
            raise StoreRecordNotFound(f"simulation not found: {run_id}.{simulation_id}")
        return _simulation_from_row(row)

    def record_diagnosis(
        self,
        run_id: str,
        failure_class: str,
        next_node: WorkflowNode,
        diagnosis: dict[str, Any],
        node_attempt_id: int | None = None,
    ) -> DiagnosisRecord:
        _validate_run_id(run_id)
        _validate_nonblank_string(failure_class, "failure_class")
        _validate_workflow_node(next_node)
        diagnosis_json = _validated_json_object(diagnosis, "diagnosis")
        if node_attempt_id is not None:
            _validate_positive_integer(node_attempt_id, "node_attempt_id")
        with self._transaction() as connection:
            if connection.execute(
                "SELECT 1 FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone() is None:
                raise RunNotFound(run_id)
            if node_attempt_id is not None and connection.execute(
                "SELECT 1 FROM node_attempts WHERE id = ? AND run_id = ?",
                (node_attempt_id, run_id),
            ).fetchone() is None:
                raise StoreRecordNotFound(
                    f"node attempt not found for run: {run_id}.{node_attempt_id}"
                )
            cursor = connection.execute(
                "INSERT INTO diagnoses"
                "(run_id, node_attempt_id, failure_class, next_node, diagnosis_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    run_id,
                    node_attempt_id,
                    failure_class,
                    next_node.value,
                    diagnosis_json,
                ),
            )
            row = connection.execute(
                "SELECT * FROM diagnoses WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return _diagnosis_from_row(row)

    def record_approval(
        self, run_id: str, alpha_id: str, report_hash: str
    ) -> ApprovalRecord:
        _validate_run_id(run_id)
        _validate_nonblank_string(alpha_id, "alpha_id")
        _validate_nonblank_string(report_hash, "report_hash")
        with self._transaction() as connection:
            try:
                cursor = connection.execute(
                    "INSERT INTO approvals(run_id, alpha_id, report_hash) "
                    "VALUES (?, ?, ?)",
                    (run_id, alpha_id, report_hash),
                )
            except sqlite3.IntegrityError as error:
                if connection.execute(
                    "SELECT 1 FROM approvals "
                    "WHERE run_id = ? AND alpha_id = ? AND report_hash = ?",
                    (run_id, alpha_id, report_hash),
                ).fetchone():
                    raise StoreConflict(
                        f"approval already exists: {run_id}.{alpha_id}.{report_hash}"
                    ) from error
                raise RunNotFound(run_id) from error
            row = connection.execute(
                "SELECT * FROM approvals WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return _approval_from_row(row)

    def approval_matches(
        self,
        approval_id: int,
        run_id: str,
        alpha_id: str,
        report_hash: str,
    ) -> bool:
        _validate_positive_integer(approval_id, "approval_id")
        _validate_run_id(run_id)
        _validate_nonblank_string(alpha_id, "alpha_id")
        _validate_nonblank_string(report_hash, "report_hash")
        with closing(self.connect()) as connection:
            return (
                connection.execute(
                    "SELECT 1 FROM approvals WHERE id = ? AND run_id = ? "
                    "AND alpha_id = ? AND report_hash = ? AND decision = 'APPROVED'",
                    (approval_id, run_id, alpha_id, report_hash),
                ).fetchone()
                is not None
            )

    def find_unconsumed_approval(
        self, run_id: str, alpha_id: str, report_hash: str
    ) -> ApprovalRecord | None:
        _validate_run_id(run_id)
        _validate_nonblank_string(alpha_id, "alpha_id")
        _validate_nonblank_string(report_hash, "report_hash")
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT * FROM approvals WHERE run_id = ? AND alpha_id = ? "
                "AND report_hash = ? AND decision = 'APPROVED' "
                "AND consumed_at IS NULL ORDER BY id DESC LIMIT 1",
                (run_id, alpha_id, report_hash),
            ).fetchone()
        return None if row is None else _approval_from_row(row)

    def record_rejection(self, run_id: str, reason: str) -> RunRecord:
        _validate_run_id(run_id)
        _validate_reason(reason)
        with self._transaction() as connection:
            cursor = connection.execute(
                f"UPDATE runs SET state = ?, updated_at = ({_NOW_SQL}) "
                "WHERE run_id = ? AND state = ?",
                (RunState.REJECTED.value, run_id, RunState.AWAITING_APPROVAL.value),
            )
            if cursor.rowcount != 1:
                if connection.execute(
                    "SELECT 1 FROM runs WHERE run_id = ?", (run_id,)
                ).fetchone() is None:
                    raise RunNotFound(run_id)
                raise StoreConflict(
                    f"run is not awaiting a rejection decision: {run_id}"
                )
            connection.execute(
                "INSERT INTO state_transitions(run_id, from_state, to_state, reason) "
                "VALUES (?, ?, ?, ?)",
                (
                    run_id,
                    RunState.AWAITING_APPROVAL.value,
                    RunState.REJECTED.value,
                    reason,
                ),
            )
            row = connection.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            return _run_from_row(row)

    def begin_approved_submission(
        self,
        run_id: str,
        approval_id: int,
        alpha_id: str,
        report_hash: str,
    ) -> RunRecord:
        _validate_run_id(run_id)
        _validate_positive_integer(approval_id, "approval_id")
        _validate_nonblank_string(alpha_id, "alpha_id")
        _validate_nonblank_string(report_hash, "report_hash")
        with self._transaction() as connection:
            approval = connection.execute(
                "SELECT 1 FROM approvals WHERE id = ? AND run_id = ? "
                "AND alpha_id = ? AND report_hash = ? AND decision = 'APPROVED' "
                "AND consumed_at IS NULL",
                (approval_id, run_id, alpha_id, report_hash),
            ).fetchone()
            if approval is None:
                raise StoreConflict("approval subject is missing, changed, or consumed")
            cursor = connection.execute(
                f"UPDATE runs SET state = ?, updated_at = ({_NOW_SQL}) "
                "WHERE run_id = ? AND state = ?",
                (RunState.RUNNING.value, run_id, RunState.AWAITING_APPROVAL.value),
            )
            if cursor.rowcount != 1:
                if connection.execute(
                    "SELECT 1 FROM runs WHERE run_id = ?", (run_id,)
                ).fetchone() is None:
                    raise RunNotFound(run_id)
                raise StoreConflict(f"run is not awaiting approval: {run_id}")
            connection.execute(
                "INSERT INTO state_transitions(run_id, from_state, to_state, reason) "
                "VALUES (?, ?, ?, ?)",
                (
                    run_id,
                    RunState.AWAITING_APPROVAL.value,
                    RunState.RUNNING.value,
                    _canonical_json(
                        {
                            "event": "approved_submission_started",
                            "approval_id": approval_id,
                            "alpha_id": alpha_id,
                            "report_hash": report_hash,
                        }
                    ),
                ),
            )
            row = connection.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            return _run_from_row(row)

    def consume_approval_and_finish_submission(
        self,
        run_id: str,
        approval_id: int,
        alpha_id: str,
        report_hash: str,
        submit_result: dict[str, Any],
    ) -> RunRecord:
        _validate_run_id(run_id)
        _validate_positive_integer(approval_id, "approval_id")
        _validate_nonblank_string(alpha_id, "alpha_id")
        _validate_nonblank_string(report_hash, "report_hash")
        result_json = _validated_json_object(submit_result, "submit_result")
        begin_reason = _canonical_json(
            {
                "event": "approved_submission_started",
                "approval_id": approval_id,
                "alpha_id": alpha_id,
                "report_hash": report_hash,
            }
        )
        with self._transaction() as connection:
            approval_cursor = connection.execute(
                f"UPDATE approvals SET consumed_at = ({_NOW_SQL}) "
                "WHERE id = ? AND run_id = ? AND alpha_id = ? AND report_hash = ? "
                "AND decision = 'APPROVED' AND consumed_at IS NULL "
                "AND EXISTS (SELECT 1 FROM runs WHERE run_id = ? AND state = ?) "
                "AND EXISTS (SELECT 1 FROM state_transitions "
                "WHERE run_id = ? AND from_state = ? AND to_state = ? AND reason = ?)",
                (
                    approval_id,
                    run_id,
                    alpha_id,
                    report_hash,
                    run_id,
                    RunState.RUNNING.value,
                    run_id,
                    RunState.AWAITING_APPROVAL.value,
                    RunState.RUNNING.value,
                    begin_reason,
                ),
            )
            if approval_cursor.rowcount != 1:
                raise StoreConflict(
                    "submission is not running or approval subject was already consumed"
                )
            run_cursor = connection.execute(
                f"UPDATE runs SET state = ?, updated_at = ({_NOW_SQL}) "
                "WHERE run_id = ? AND state = ?",
                (RunState.SUBMITTED.value, run_id, RunState.RUNNING.value),
            )
            if run_cursor.rowcount != 1:
                raise StoreConflict(f"submission run state changed concurrently: {run_id}")
            connection.execute(
                "INSERT INTO state_transitions(run_id, from_state, to_state, reason) "
                "VALUES (?, ?, ?, ?)",
                (
                    run_id,
                    RunState.RUNNING.value,
                    RunState.SUBMITTED.value,
                    _canonical_json(
                        {
                            "event": "submission_finished",
                            "approval_id": approval_id,
                            "alpha_id": alpha_id,
                            "report_hash": report_hash,
                            "submit_result": json.loads(result_json),
                        }
                    ),
                ),
            )
            row = connection.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            return _run_from_row(row)

    def add_experience(
        self, run_id: str, payload: dict[str, Any]
    ) -> ExperienceRecord:
        _validate_run_id(run_id)
        values = self._validated_experience_payload(payload)
        with self._transaction() as connection:
            try:
                cursor = connection.execute(
                    "INSERT INTO experiences"
                    "(run_id, region, delay, category, failure_class, "
                    "expression_fingerprint, hypothesis_json, record_json, metrics_json, "
                    "final_decision) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        run_id,
                        values["region"],
                        values["delay"],
                        values["category"],
                        values["failure_class"],
                        values["expression_fingerprint"],
                        values["hypothesis_json"],
                        values["record_json"],
                        values["metrics_json"],
                        values["final_decision"],
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise RunNotFound(run_id) from error
            experience_id = cursor.lastrowid
            connection.executemany(
                "INSERT INTO experience_fields(experience_id, field_id) VALUES (?, ?)",
                ((experience_id, field_id) for field_id in values["field_ids"]),
            )
            row = connection.execute(
                "SELECT * FROM experiences WHERE id = ?", (experience_id,)
            ).fetchone()
            return _experience_from_row(row, values["field_ids"])

    def finalize_run_experiences(
        self,
        run_id: str,
        *,
        final_decision: str,
        approval_outcome: str,
        terminal_artifact_ids: list[str],
    ) -> int:
        """Attach one terminal decision snapshot to every experience in a run."""
        _validate_run_id(run_id)
        _validate_nonblank_string(final_decision, "final_decision")
        _validate_nonblank_string(approval_outcome, "approval_outcome")
        if type(terminal_artifact_ids) is not list:
            raise TypeError("terminal_artifact_ids must be a list")
        for index, artifact_id in enumerate(terminal_artifact_ids):
            _validate_nonblank_string(
                artifact_id, f"terminal_artifact_ids[{index}]"
            )
        normalized_ids = list(dict.fromkeys(terminal_artifact_ids))
        with self._transaction() as connection:
            if connection.execute(
                "SELECT 1 FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone() is None:
                raise RunNotFound(run_id)
            rows = connection.execute(
                "SELECT id, record_json FROM experiences WHERE run_id = ?",
                (run_id,),
            ).fetchall()
            for row in rows:
                record = json.loads(row["record_json"]) if row["record_json"] else {}
                record["terminal_artifact_ids"] = normalized_ids
                record["approval_outcome"] = approval_outcome
                connection.execute(
                    f"UPDATE experiences SET final_decision = ?, record_json = ?, "
                    f"updated_at = ({_NOW_SQL}) WHERE id = ?",
                    (
                        final_decision.strip(),
                        _validated_json_object(record, "experience record"),
                        row["id"],
                    ),
                )
            return len(rows)

    def search_experience(
        self,
        region: str,
        delay: int,
        category: str,
        field_id: str | None = None,
        failure_class: str | None = None,
        limit: int = 20,
    ) -> list[ExperienceRecord]:
        _validate_nonblank_string(region, "region")
        if type(delay) is not int:
            raise TypeError("delay must be an integer")
        if delay not in {0, 1}:
            raise ValueError("delay must be 0 or 1")
        _validate_nonblank_string(category, "category")
        if field_id is not None:
            _validate_nonblank_string(field_id, "field_id")
        if failure_class is not None:
            _validate_nonblank_string(failure_class, "failure_class")
        _validate_positive_integer(limit, "limit")
        region = region.strip()
        category = category.strip()
        field_id = None if field_id is None else field_id.strip()
        failure_class = (
            None if failure_class is None else failure_class.strip()
        )
        join = (
            " JOIN experience_fields AS filtered_fields "
            "ON filtered_fields.experience_id = e.id "
            if field_id is not None
            else " "
        )
        conditions = ["e.region = ?", "e.delay = ?", "e.category = ?"]
        parameters: list[object] = [region, delay, category]
        if field_id is not None:
            conditions.append("filtered_fields.field_id = ?")
            parameters.append(field_id)
        if failure_class is not None:
            conditions.append("e.failure_class = ?")
            parameters.append(failure_class)
        parameters.append(limit)
        query = (
            "SELECT e.* FROM experiences AS e"
            + join
            + "WHERE "
            + " AND ".join(conditions)
            + " ORDER BY e.created_at DESC, e.id DESC LIMIT ?"
        )
        with closing(self.connect()) as connection:
            rows = connection.execute(query, parameters).fetchall()
            return [
                self._experience_with_fields(connection, row) for row in rows
            ]

    def has_experience_fingerprint(
        self, region: str, delay: int, category: str, fingerprint: str
    ) -> bool:
        _validate_nonblank_string(region, "region")
        if type(delay) is not int:
            raise TypeError("delay must be an integer")
        if delay not in {0, 1}:
            raise ValueError("delay must be 0 or 1")
        _validate_nonblank_string(category, "category")
        _validate_nonblank_string(fingerprint, "fingerprint")
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT EXISTS(SELECT 1 FROM experiences WHERE region = ? "
                "AND delay = ? AND category = ? AND expression_fingerprint = ?)",
                (region.strip(), delay, category.strip(), fingerprint.strip()),
            ).fetchone()
        return bool(row[0])

    @staticmethod
    def _experience_with_fields(
        connection: sqlite3.Connection, row: sqlite3.Row
    ) -> ExperienceRecord:
        field_ids = tuple(
            field_row["field_id"]
            for field_row in connection.execute(
                "SELECT field_id FROM experience_fields "
                "WHERE experience_id = ? ORDER BY field_id",
                (row["id"],),
            ).fetchall()
        )
        return _experience_from_row(row, field_ids)

    @staticmethod
    def _validated_experience_payload(payload: object) -> dict[str, Any]:
        if type(payload) is not dict:
            raise TypeError("payload must be a dictionary")
        required = {
            "region",
            "delay",
            "category",
            "field_ids",
            "expression_fingerprint",
        }
        allowed = required | {
            "failure_class",
            "hypothesis",
            "record",
            "metrics",
            "final_decision",
        }
        missing = sorted(required - payload.keys())
        if missing:
            raise ValueError(f"payload missing required field: {missing[0]}")
        unexpected = sorted(payload.keys() - allowed)
        if unexpected:
            raise ValueError(f"payload has unexpected field: {unexpected[0]}")
        _validate_nonblank_string(payload["region"], "payload.region")
        if type(payload["delay"]) is not int:
            raise TypeError("payload.delay must be an integer")
        if payload["delay"] not in {0, 1}:
            raise ValueError("payload.delay must be 0 or 1")
        _validate_nonblank_string(payload["category"], "payload.category")
        _validate_nonblank_string(
            payload["expression_fingerprint"], "payload.expression_fingerprint"
        )
        raw_fields = payload["field_ids"]
        if type(raw_fields) is not list:
            raise TypeError("payload.field_ids must be a list")
        if not raw_fields:
            raise ValueError("payload.field_ids must not be empty")
        normalized_fields: set[str] = set()
        for index, raw_field in enumerate(raw_fields):
            _validate_nonblank_string(raw_field, f"payload.field_ids[{index}]")
            normalized_fields.add(raw_field.strip())
        failure_class = payload.get("failure_class")
        if failure_class is not None:
            _validate_nonblank_string(failure_class, "payload.failure_class")
            failure_class = failure_class.strip()
        final_decision = payload.get("final_decision")
        if final_decision is not None:
            _validate_nonblank_string(final_decision, "payload.final_decision")

        json_values: dict[str, str | None] = {}
        for name in ("hypothesis", "record", "metrics"):
            value = payload.get(name)
            json_values[f"{name}_json"] = (
                None
                if value is None
                else _validated_json_object(value, f"payload.{name}")
            )
        return {
            "region": payload["region"].strip(),
            "delay": payload["delay"],
            "category": payload["category"].strip(),
            "field_ids": tuple(sorted(normalized_fields)),
            "expression_fingerprint": payload["expression_fingerprint"].strip(),
            "failure_class": failure_class,
            "final_decision": final_decision,
            **json_values,
        }

    @staticmethod
    def _command_after_terminal_update(
        connection: sqlite3.Connection,
        command_id: int,
        cursor: sqlite3.Cursor,
    ) -> CommandLedgerRecord:
        row = connection.execute(
            "SELECT * FROM command_ledger WHERE id = ?", (command_id,)
        ).fetchone()
        if row is None:
            raise StoreRecordNotFound(f"command not found: {command_id}")
        if cursor.rowcount != 1:
            raise StoreConflict(f"command is already terminal: {command_id}")
        return _command_from_row(row)

    @staticmethod
    def _validate_command_artifact_link(
        connection: sqlite3.Connection,
        command_id: int,
        artifact_id: int | None,
    ) -> None:
        if artifact_id is None:
            return
        command = connection.execute(
            "SELECT run_id, status FROM command_ledger WHERE id = ?", (command_id,)
        ).fetchone()
        if command is None or command["status"] != "STARTED":
            return
        if connection.execute(
            "SELECT 1 FROM artifacts WHERE id = ? AND run_id = ?",
            (artifact_id, command["run_id"]),
        ).fetchone() is None:
            raise StoreRecordNotFound(
                f"artifact not found for command run: {command['run_id']}.{artifact_id}"
            )

    @staticmethod
    def _validate_command_resource_link(
        connection: sqlite3.Connection,
        command_id: int,
        resource_id: str | None,
    ) -> None:
        if resource_id is None:
            return
        command = connection.execute(
            "SELECT status, resource_id FROM command_ledger WHERE id = ?", (command_id,)
        ).fetchone()
        if command is None or command["status"] != "STARTED":
            return
        if command["resource_id"] not in {None, resource_id}:
            raise StoreConflict(f"command resource is already assigned: {command_id}")

    @staticmethod
    def _validated_argv(argv: object) -> str:
        if type(argv) not in {tuple, list}:
            raise TypeError("argv must be a tuple or list")
        if not argv:
            raise ValueError("argv must not be empty")
        for index, value in enumerate(argv):
            if type(value) is not str:
                raise TypeError(f"argv[{index}] must be a string")
        return _canonical_json(list(argv))

    @staticmethod
    def _validate_exit_code(value: object, name: str, *, optional: bool) -> None:
        if optional and value is None:
            return
        if type(value) is not int:
            suffix = " or None" if optional else ""
            raise TypeError(f"{name} must be an integer{suffix}")

    @staticmethod
    def _validate_simulation_values(
        run_id: object,
        simulation_id: object,
        status: object,
        candidate_id: object,
        alpha_id: object,
        result_artifact_id: object,
    ) -> None:
        _validate_run_id(run_id)
        _validate_nonblank_string(simulation_id, "simulation_id")
        _validate_nonblank_string(status, "status")
        if status not in _SIMULATION_STATUSES:
            raise ValueError(f"invalid simulation status: {status}")
        if candidate_id is not None:
            _validate_positive_integer(candidate_id, "candidate_id")
        if alpha_id is not None:
            _validate_nonblank_string(alpha_id, "alpha_id")
        if result_artifact_id is not None:
            _validate_positive_integer(result_artifact_id, "result_artifact_id")

    @staticmethod
    def _validate_run_scoped_links(
        connection: sqlite3.Connection,
        run_id: str,
        candidate_id: int | None,
        artifact_id: int | None,
    ) -> None:
        if candidate_id is not None and connection.execute(
            "SELECT 1 FROM candidates WHERE id = ? AND run_id = ?",
            (candidate_id, run_id),
        ).fetchone() is None:
            raise StoreRecordNotFound(
                f"candidate not found for run: {run_id}.{candidate_id}"
            )
        if artifact_id is not None and connection.execute(
            "SELECT 1 FROM artifacts WHERE id = ? AND run_id = ?",
            (artifact_id, run_id),
        ).fetchone() is None:
            raise StoreRecordNotFound(
                f"artifact not found for run: {run_id}.{artifact_id}"
            )

    @staticmethod
    def _validate_artifact_values(
        run_id: object,
        node: object,
        name: object,
        path: object,
        sha256: object,
        kind: object,
    ) -> str:
        _validate_run_id(run_id)
        _validate_workflow_node(node)
        for value, value_name in (
            (name, "name"),
            (sha256, "sha256"),
            (kind, "kind"),
        ):
            _validate_nonblank_string(value, value_name)
        if type(path) is str:
            _validate_nonblank_string(path, "path")
            return path
        if isinstance(path, Path):
            normalized = str(path)
            _validate_nonblank_string(normalized, "path")
            return normalized
        raise TypeError("path must be a string or Path")

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
        summary_json = _validated_json_object(summary, "summary")
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
