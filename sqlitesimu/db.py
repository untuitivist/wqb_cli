from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .models import (
    EXPERIMENT_TERMINAL_STATES,
    BatchItemRecord,
    BatchRecord,
    EnqueueResult,
    ExperimentRecord,
    SimulationManifest,
)


SCHEMA_VERSION = 2
# Kept only for non-destructive compatibility with schema v1 columns; never used for scheduling.
LEGACY_SLOT_CLASS = "SERVER_MANAGED"


class RunLeaseError(RuntimeError):
    pass


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    state TEXT NOT NULL,
    enrichment_profile TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    started_at REAL,
    finished_at REAL
);

CREATE TABLE IF NOT EXISTS candidates (
    id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL UNIQUE,
    simulation_type TEXT NOT NULL,
    language TEXT NOT NULL,
    settings_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    compatibility_key TEXT NOT NULL,
    slot_class TEXT NOT NULL,
    batch_limit INTEGER NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    candidate_id TEXT NOT NULL REFERENCES candidates(id),
    state TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    enrich_attempts INTEGER NOT NULL DEFAULT 0,
    not_before REAL NOT NULL DEFAULT 0,
    batch_id TEXT,
    child_simulation_id TEXT,
    alpha_id TEXT,
    last_error TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    UNIQUE(run_id, candidate_id)
);

CREATE TABLE IF NOT EXISTS simulation_queue (
    experiment_id TEXT PRIMARY KEY REFERENCES experiments(id) ON DELETE CASCADE,
    run_id TEXT NOT NULL REFERENCES runs(id),
    enqueued_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS enrichment_queue (
    experiment_id TEXT PRIMARY KEY REFERENCES experiments(id) ON DELETE CASCADE,
    run_id TEXT NOT NULL REFERENCES runs(id),
    alpha_id TEXT NOT NULL,
    enqueued_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS simulation_batches (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    state TEXT NOT NULL,
    compatibility_key TEXT NOT NULL,
    slot_class TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    parent_simulation_id TEXT,
    location TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    poll_attempts INTEGER NOT NULL DEFAULT 0,
    not_before REAL NOT NULL DEFAULT 0,
    last_status TEXT,
    last_response_json TEXT,
    last_error TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS simulation_items (
    batch_id TEXT NOT NULL REFERENCES simulation_batches(id),
    experiment_id TEXT NOT NULL REFERENCES experiments(id),
    ordinal INTEGER NOT NULL,
    state TEXT NOT NULL,
    child_simulation_id TEXT,
    alpha_id TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    not_before REAL NOT NULL DEFAULT 0,
    last_response_json TEXT,
    last_error TEXT,
    PRIMARY KEY(batch_id, ordinal)
);

CREATE TABLE IF NOT EXISTS alphas (
    alpha_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL UNIQUE REFERENCES experiments(id),
    run_id TEXT NOT NULL REFERENCES runs(id),
    candidate_id TEXT NOT NULL REFERENCES candidates(id),
    detail_json TEXT NOT NULL,
    fetched_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS alpha_metrics (
    alpha_id TEXT PRIMARY KEY REFERENCES alphas(alpha_id),
    author TEXT,
    alpha_type TEXT,
    date_created TEXT,
    region TEXT,
    universe_name TEXT,
    delay INTEGER,
    decay REAL,
    neutralization TEXT,
    truncation REAL,
    max_trade TEXT,
    regular_code TEXT,
    operator_count INTEGER,
    pnl REAL,
    long_count INTEGER,
    short_count INTEGER,
    turnover REAL,
    returns_value REAL,
    drawdown REAL,
    margin REAL,
    sharpe REAL,
    fitness REAL,
    pyramids TEXT
);

CREATE TABLE IF NOT EXISTS alpha_checks (
    alpha_id TEXT NOT NULL REFERENCES alphas(alpha_id),
    name TEXT NOT NULL,
    result TEXT,
    value_json TEXT,
    raw_json TEXT NOT NULL,
    PRIMARY KEY(alpha_id, name)
);

CREATE TABLE IF NOT EXISTS alpha_pnl (
    alpha_id TEXT NOT NULL REFERENCES alphas(alpha_id),
    ordinal INTEGER NOT NULL,
    date_value TEXT,
    cumulative REAL,
    pnl_delta REAL,
    PRIMARY KEY(alpha_id, ordinal)
);

CREATE TABLE IF NOT EXISTS api_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    experiment_id TEXT,
    batch_id TEXT,
    event_type TEXT NOT NULL,
    status_code INTEGER,
    payload_json TEXT,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS outbox_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    consumed_at REAL,
    UNIQUE(run_id, event_type)
);

CREATE TABLE IF NOT EXISTS runtime_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS run_leases (
    run_id TEXT PRIMARY KEY REFERENCES runs(id),
    owner TEXT NOT NULL,
    lease_until REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_experiments_runnable
    ON experiments(run_id, state, not_before, priority, created_at);
CREATE INDEX IF NOT EXISTS idx_simulation_queue_run
    ON simulation_queue(run_id, enqueued_at, experiment_id);
CREATE INDEX IF NOT EXISTS idx_enrichment_queue_run
    ON enrichment_queue(run_id, enqueued_at, experiment_id);
CREATE INDEX IF NOT EXISTS idx_batches_runnable
    ON simulation_batches(run_id, state, not_before, created_at);
CREATE INDEX IF NOT EXISTS idx_items_runnable
    ON simulation_items(state, not_before, batch_id, ordinal);

CREATE VIEW IF NOT EXISTS analysis_alpha_ready AS
SELECT
    e.run_id,
    e.id AS experiment_id,
    c.id AS candidate_id,
    c.fingerprint,
    e.metadata_json,
    a.alpha_id,
    m.author,
    m.alpha_type,
    m.date_created,
    m.region,
    m.universe_name,
    m.delay,
    m.decay,
    m.neutralization,
    m.truncation,
    m.max_trade,
    m.regular_code,
    m.operator_count,
    m.pnl,
    m.long_count,
    m.short_count,
    m.turnover,
    m.returns_value,
    m.drawdown,
    m.margin,
    m.sharpe,
    m.fitness,
    m.pyramids
FROM experiments e
JOIN candidates c ON c.id = e.candidate_id
JOIN alphas a ON a.experiment_id = e.id
JOIN alpha_metrics m ON m.alpha_id = a.alpha_id
WHERE e.state = 'READY';

CREATE VIEW IF NOT EXISTS simued_alpha_is_pnl AS
SELECT
    m.alpha_id AS id,
    COALESCE(m.author, '') AS author,
    COALESCE(m.alpha_type, '') AS type,
    COALESCE(m.region, '') AS settings_region,
    COALESCE(m.universe_name, '') AS settings_universe,
    COALESCE(m.delay, '') AS settings_delay,
    COALESCE(m.decay, '') AS settings_decay,
    COALESCE(m.neutralization, '') AS settings_neutralization,
    COALESCE(m.truncation, '') AS settings_truncation,
    COALESCE(m.max_trade, '') AS settings_maxTrade,
    COALESCE(m.regular_code, '') AS regular_code,
    COALESCE(m.operator_count, '') AS regular_operatorCount,
    COALESCE(m.date_created, '') AS dateCreated,
    COALESCE(m.pnl, '') AS is_pnl,
    COALESCE(m.long_count, '') AS is_longCount,
    COALESCE(m.short_count, '') AS is_shortCount,
    COALESCE(m.turnover, '') AS is_turnover,
    COALESCE(m.returns_value, '') AS is_returns,
    COALESCE(m.drawdown, '') AS is_drawdown,
    COALESCE(m.margin, '') AS is_margin,
    COALESCE(m.sharpe, '') AS is_sharpe,
    COALESCE(m.fitness, '') AS is_fitness,
    COALESCE(m.pyramids, '') AS pyramids,
    COALESCE((
        SELECT group_concat(
            CASE
                WHEN pnl_delta IS NULL THEN 'nan'
                ELSE CAST(pnl_delta AS TEXT)
            END,
            ', '
        )
        FROM (
            SELECT pnl_delta
            FROM alpha_pnl p
            WHERE p.alpha_id = m.alpha_id
            ORDER BY ordinal
        )
    ), '') AS PnL
FROM alpha_metrics m
JOIN alphas a ON a.alpha_id = m.alpha_id
JOIN experiments e ON e.id = a.experiment_id
WHERE e.state = 'READY';
"""


class SqliteStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=30.0)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 30000")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            current = int(conn.execute("PRAGMA user_version").fetchone()[0])
            if current > SCHEMA_VERSION:
                raise RuntimeError(
                    f"Database schema {current} is newer than supported version {SCHEMA_VERSION}"
                )
            conn.executescript(SCHEMA_SQL)
            if current < 2:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO simulation_queue(experiment_id, run_id, enqueued_at)
                    SELECT id, run_id, created_at
                    FROM experiments
                    WHERE state IN (
                        'QUEUED', 'RETRY_WAIT', 'BATCHED', 'SUBMITTING',
                        'POLLING', 'CHILD_POLLING'
                    )
                    """
                )
                conn.execute(
                    """
                    INSERT OR IGNORE INTO enrichment_queue(
                        experiment_id, run_id, alpha_id, enqueued_at
                    )
                    SELECT id, run_id, alpha_id, updated_at
                    FROM experiments
                    WHERE state IN ('SIM_DONE', 'ENRICH_PNL') AND alpha_id IS NOT NULL
                    """
                )
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    def enqueue(self, manifest: SimulationManifest, *, now: float | None = None) -> EnqueueResult:
        timestamp = time.time() if now is None else now
        run_id = manifest.requested_run_id or _new_id("run")
        accepted = 0
        reused = 0
        duplicates = 0
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO runs(id, name, state, enrichment_profile, metadata_json, created_at, updated_at)
                VALUES (?, ?, 'QUEUED', ?, ?, ?, ?)
                """,
                (
                    run_id,
                    manifest.name,
                    manifest.enrichment_profile,
                    _json(manifest.metadata),
                    timestamp,
                    timestamp,
                ),
            )
            for spec in manifest.candidates:
                fingerprint = candidate_fingerprint(spec.payload)
                existing = conn.execute(
                    "SELECT id FROM candidates WHERE fingerprint = ?", (fingerprint,)
                ).fetchone()
                if existing:
                    candidate_id = str(existing["id"])
                    reused += 1
                else:
                    candidate_id = f"cand_{fingerprint[:24]}"
                    settings = spec.payload["settings"]
                    language = str(settings.get("language") or "FASTEXPR").upper()
                    compatibility_key, batch_limit = scheduling_profile(spec.payload)
                    conn.execute(
                        """
                        INSERT INTO candidates(
                            id, fingerprint, simulation_type, language, settings_json, payload_json,
                            compatibility_key, slot_class, batch_limit, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            candidate_id,
                            fingerprint,
                            spec.payload["type"],
                            language,
                            _json(settings),
                            _json(spec.payload),
                            compatibility_key,
                            LEGACY_SLOT_CLASS,
                            batch_limit,
                            timestamp,
                        ),
                    )
                experiment_id = _new_id("exp")
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO experiments(
                        id, run_id, candidate_id, state, priority, metadata_json, created_at, updated_at
                    ) VALUES (?, ?, ?, 'QUEUED', ?, ?, ?, ?)
                    """,
                    (
                        experiment_id,
                        run_id,
                        candidate_id,
                        spec.priority,
                        _json(spec.metadata),
                        timestamp,
                        timestamp,
                    ),
                )
                if cursor.rowcount:
                    accepted += 1
                    conn.execute(
                        """
                        INSERT INTO simulation_queue(experiment_id, run_id, enqueued_at)
                        VALUES (?, ?, ?)
                        """,
                        (experiment_id, run_id, timestamp),
                    )
                else:
                    duplicates += 1
            self._event(
                conn,
                run_id,
                "RUN_ENQUEUED",
                payload={"accepted": accepted, "reused_candidates": reused, "duplicates": duplicates},
                now=timestamp,
            )
        return EnqueueResult(run_id, accepted, reused, duplicates)

    def mark_run_running(self, run_id: str, *, now: float) -> None:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE runs
                SET state = 'RUNNING', started_at = COALESCE(started_at, ?), updated_at = ?
                WHERE id = ? AND state NOT IN ('COMPLETED', 'COMPLETED_WITH_ERRORS', 'BLOCKED', 'CANCELLED')
                """,
                (now, now, run_id),
            )
            if not cursor.rowcount and not self._run_exists(conn, run_id):
                raise KeyError(f"Unknown run id: {run_id}")

    def acquire_run_lease(
        self,
        run_id: str,
        *,
        owner: str,
        now: float,
        lease_seconds: float,
    ) -> None:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO run_leases(run_id, owner, lease_until, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    owner = excluded.owner,
                    lease_until = excluded.lease_until,
                    updated_at = excluded.updated_at
                WHERE run_leases.owner = excluded.owner OR run_leases.lease_until <= ?
                """,
                (run_id, owner, now + lease_seconds, now, now),
            )
            if not cursor.rowcount:
                lease = conn.execute(
                    "SELECT owner, lease_until FROM run_leases WHERE run_id = ?", (run_id,)
                ).fetchone()
                raise RunLeaseError(
                    f"Run {run_id} is already leased by {lease['owner']} until {lease['lease_until']}"
                )

    def renew_run_lease(
        self,
        run_id: str,
        *,
        owner: str,
        now: float,
        lease_seconds: float,
    ) -> None:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE run_leases SET lease_until = ?, updated_at = ?
                WHERE run_id = ? AND owner = ?
                """,
                (now + lease_seconds, now, run_id, owner),
            )
            if not cursor.rowcount:
                raise RunLeaseError(f"Run lease was lost for {run_id}")

    def release_run_lease(self, run_id: str, *, owner: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM run_leases WHERE run_id = ? AND owner = ?", (run_id, owner))

    def recover_interrupted(self, run_id: str, *, now: float) -> None:
        with self.connect() as conn:
            ambiguous = conn.execute(
                """
                SELECT id FROM simulation_batches
                WHERE run_id = ? AND state = 'SUBMITTING'
                """,
                (run_id,),
            ).fetchall()
            for row in ambiguous:
                batch_id = str(row["id"])
                conn.execute(
                    "UPDATE simulation_batches SET state = 'SUBMIT_UNKNOWN', updated_at = ? WHERE id = ?",
                    (now, batch_id),
                )
                conn.execute(
                    "UPDATE experiments SET state = 'SUBMIT_UNKNOWN', last_error = ?, updated_at = ? WHERE batch_id = ?",
                    ("worker_interrupted_during_submit", now, batch_id),
                )
                self._event(
                    conn,
                    run_id,
                    "SUBMIT_BECAME_AMBIGUOUS",
                    batch_id=batch_id,
                    payload={"reason": "worker_interrupted_during_submit"},
                    now=now,
                )

    def next_submit_batch(self, run_id: str, *, now: float) -> BatchRecord | None:
        global_not_before = self.runtime_float("simulation_submit_not_before")
        if global_not_before is not None and now < global_not_before:
            return None
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM simulation_batches
                WHERE run_id = ? AND state IN ('CREATED', 'RETRY_WAIT') AND not_before <= ?
                ORDER BY created_at, id
                LIMIT 1
                """,
                (run_id, now),
            ).fetchone()
        return _batch_from_row(row) if row else None

    def create_next_batch(self, run_id: str, *, now: float) -> BatchRecord | None:
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            selected_head = conn.execute(
                """
                SELECT e.id AS experiment_id, c.*
                FROM simulation_queue q
                JOIN experiments e ON e.id = q.experiment_id
                JOIN candidates c ON c.id = e.candidate_id
                WHERE q.run_id = ?
                  AND e.state IN ('QUEUED', 'RETRY_WAIT') AND e.not_before <= ?
                ORDER BY e.priority DESC, e.created_at, e.id
                LIMIT 1
                """,
                (run_id, now),
            ).fetchone()
            if selected_head is None:
                return None
            compatible = conn.execute(
                """
                SELECT e.id AS experiment_id, c.payload_json
                FROM simulation_queue q
                JOIN experiments e ON e.id = q.experiment_id
                JOIN candidates c ON c.id = e.candidate_id
                WHERE q.run_id = ? AND e.state IN ('QUEUED', 'RETRY_WAIT')
                  AND e.not_before <= ? AND c.compatibility_key = ?
                ORDER BY e.priority DESC, e.created_at, e.id
                LIMIT ?
                """,
                (
                    run_id,
                    now,
                    selected_head["compatibility_key"],
                    int(selected_head["batch_limit"]),
                ),
            ).fetchall()
            batch_id = _new_id("batch")
            payloads = [json.loads(row["payload_json"]) for row in compatible]
            request_payload: Any = payloads[0] if len(payloads) == 1 else payloads
            conn.execute(
                """
                INSERT INTO simulation_batches(
                    id, run_id, state, compatibility_key, slot_class, payload_json,
                    created_at, updated_at
                ) VALUES (?, ?, 'CREATED', ?, ?, ?, ?, ?)
                """,
                (
                    batch_id,
                    run_id,
                    selected_head["compatibility_key"],
                    LEGACY_SLOT_CLASS,
                    _json(request_payload),
                    now,
                    now,
                ),
            )
            for ordinal, row in enumerate(compatible):
                experiment_id = str(row["experiment_id"])
                conn.execute(
                    """
                    INSERT INTO simulation_items(batch_id, experiment_id, ordinal, state)
                    VALUES (?, ?, ?, 'BATCHED')
                    """,
                    (batch_id, experiment_id, ordinal),
                )
                conn.execute(
                    """
                    UPDATE experiments SET state = 'BATCHED', batch_id = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (batch_id, now, experiment_id),
                )
            self._event(
                conn,
                run_id,
                "BATCH_CREATED",
                batch_id=batch_id,
                payload={"size": len(compatible)},
                now=now,
            )
            row = conn.execute("SELECT * FROM simulation_batches WHERE id = ?", (batch_id,)).fetchone()
        return _batch_from_row(row)

    def mark_submit_started(self, batch_id: str, *, now: float) -> None:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE simulation_batches
                SET state = 'SUBMITTING', attempts = attempts + 1, updated_at = ?
                WHERE id = ? AND state IN ('CREATED', 'RETRY_WAIT')
                """,
                (now, batch_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError(f"Batch {batch_id} is no longer ready for submission")
            conn.execute(
                "UPDATE experiments SET state = 'SUBMITTING', attempts = attempts + 1, updated_at = ? WHERE batch_id = ?",
                (now, batch_id),
            )

    def accept_submission(
        self,
        batch_id: str,
        *,
        location: str,
        parent_simulation_id: str,
        response: dict[str, Any],
        not_before: float,
        now: float,
    ) -> None:
        with self.connect() as conn:
            row = conn.execute("SELECT run_id FROM simulation_batches WHERE id = ?", (batch_id,)).fetchone()
            conn.execute(
                """
                UPDATE simulation_batches
                SET state = 'POLLING', location = ?, parent_simulation_id = ?, not_before = ?,
                    last_status = 'CREATED', last_response_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (location, parent_simulation_id, not_before, _json(response), now, batch_id),
            )
            conn.execute(
                "UPDATE experiments SET state = 'POLLING', updated_at = ? WHERE batch_id = ?",
                (now, batch_id),
            )
            self._event(
                conn,
                str(row["run_id"]),
                "SIMULATION_SUBMITTED",
                batch_id=batch_id,
                status_code=_status_code(response),
                payload=response,
                now=now,
            )

    def retry_submission(
        self,
        batch_id: str,
        *,
        response: dict[str, Any],
        not_before: float,
        error: str,
        now: float,
    ) -> None:
        with self.connect() as conn:
            row = conn.execute("SELECT run_id FROM simulation_batches WHERE id = ?", (batch_id,)).fetchone()
            conn.execute(
                """
                UPDATE simulation_batches
                SET state = 'RETRY_WAIT', not_before = ?, last_response_json = ?, last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (not_before, _json(response), error, now, batch_id),
            )
            conn.execute(
                "UPDATE experiments SET state = 'BATCHED', last_error = ?, updated_at = ? WHERE batch_id = ?",
                (error, now, batch_id),
            )
            self._event(
                conn,
                str(row["run_id"]),
                "SIMULATION_SUBMIT_RETRY",
                batch_id=batch_id,
                status_code=_status_code(response),
                payload=response,
                now=now,
            )

    def fail_batch(
        self,
        batch_id: str,
        *,
        state: str,
        error: str,
        response: dict[str, Any] | None,
        now: float,
    ) -> None:
        if state not in {"PERMANENT_FAILURE", "SUBMIT_UNKNOWN"}:
            raise ValueError(f"Unsupported batch failure state: {state}")
        batch_state = "FAILED" if state == "PERMANENT_FAILURE" else "SUBMIT_UNKNOWN"
        with self.connect() as conn:
            row = conn.execute("SELECT run_id FROM simulation_batches WHERE id = ?", (batch_id,)).fetchone()
            conn.execute(
                """
                UPDATE simulation_batches
                SET state = ?, last_error = ?, last_response_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (batch_state, error, _json(response) if response else None, now, batch_id),
            )
            conn.execute(
                "UPDATE experiments SET state = ?, last_error = ?, updated_at = ? WHERE batch_id = ?",
                (state, error, now, batch_id),
            )
            conn.execute(
                "UPDATE simulation_items SET state = ?, last_error = ? WHERE batch_id = ?",
                (state, error, batch_id),
            )
            if state == "PERMANENT_FAILURE":
                conn.execute(
                    """
                    DELETE FROM simulation_queue
                    WHERE experiment_id IN (
                        SELECT experiment_id FROM simulation_items WHERE batch_id = ?
                    )
                    """,
                    (batch_id,),
                )
            self._event(
                conn,
                str(row["run_id"]),
                "SIMULATION_BATCH_FAILED",
                batch_id=batch_id,
                status_code=_status_code(response),
                payload={"state": state, "error": error, "response": response},
                now=now,
            )

    def retry_completed_batch(
        self,
        batch_id: str,
        *,
        error: str,
        response: dict[str, Any],
        not_before: float,
        now: float,
    ) -> None:
        with self.connect() as conn:
            batch = conn.execute(
                "SELECT run_id FROM simulation_batches WHERE id = ?", (batch_id,)
            ).fetchone()
            conn.execute(
                """
                UPDATE simulation_batches
                SET state = 'RETRIED', last_error = ?, last_response_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (error, _json(response), now, batch_id),
            )
            conn.execute(
                "UPDATE simulation_items SET state = 'RETRIED', last_error = ? WHERE batch_id = ?",
                (error, batch_id),
            )
            conn.execute(
                """
                UPDATE experiments
                SET state = 'RETRY_WAIT', batch_id = NULL, child_simulation_id = NULL,
                    alpha_id = NULL, not_before = ?, last_error = ?, updated_at = ?
                WHERE batch_id = ?
                """,
                (not_before, error, now, batch_id),
            )
            self._event(
                conn,
                str(batch["run_id"]),
                "SIMULATION_BATCH_REQUEUED",
                batch_id=batch_id,
                status_code=_status_code(response),
                payload={"error": error, "response": response},
                now=now,
            )

    def next_poll_batch(self, run_id: str, *, now: float) -> BatchRecord | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM simulation_batches
                WHERE run_id = ? AND state = 'POLLING' AND not_before <= ?
                ORDER BY not_before, created_at
                LIMIT 1
                """,
                (run_id, now),
            ).fetchone()
        return _batch_from_row(row) if row else None

    def defer_parent_poll(
        self,
        batch_id: str,
        *,
        response: dict[str, Any],
        not_before: float,
        status: str | None,
        increment_attempt: bool,
        now: float,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE simulation_batches
                SET not_before = ?, last_status = ?, last_response_json = ?,
                    poll_attempts = poll_attempts + ?, updated_at = ?
                WHERE id = ?
                """,
                (not_before, status, _json(response), 1 if increment_attempt else 0, now, batch_id),
            )

    def complete_parent(
        self,
        batch_id: str,
        *,
        alpha_id: str | None,
        child_ids: list[str],
        parent_status: str,
        response: dict[str, Any],
        now: float,
    ) -> None:
        with self.connect() as conn:
            batch = conn.execute(
                "SELECT run_id FROM simulation_batches WHERE id = ?", (batch_id,)
            ).fetchone()
            items = conn.execute(
                "SELECT * FROM simulation_items WHERE batch_id = ? ORDER BY ordinal", (batch_id,)
            ).fetchall()
            if child_ids:
                if len(child_ids) != len(items):
                    raise ValueError(
                        f"Parent returned {len(child_ids)} children for {len(items)} batch items"
                    )
                for item, child_id in zip(items, child_ids):
                    conn.execute(
                        """
                        UPDATE simulation_items
                        SET state = 'POLLING', child_simulation_id = ?, not_before = ?, last_response_json = ?
                        WHERE batch_id = ? AND ordinal = ?
                        """,
                        (child_id, now, _json(response), batch_id, item["ordinal"]),
                    )
                    conn.execute(
                        """
                        UPDATE experiments
                        SET state = 'CHILD_POLLING', child_simulation_id = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (child_id, now, item["experiment_id"]),
                    )
                batch_state = "CHILD_POLLING"
            else:
                if len(items) != 1 or not alpha_id:
                    raise ValueError("Single simulation completed without an alpha id")
                item = items[0]
                conn.execute(
                    """
                    UPDATE simulation_items
                    SET state = 'SIM_DONE', alpha_id = ?, last_response_json = ?
                    WHERE batch_id = ? AND ordinal = 0
                    """,
                    (alpha_id, _json(response), batch_id),
                )
                conn.execute(
                    """
                    UPDATE experiments SET state = 'SIM_DONE', alpha_id = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (alpha_id, now, item["experiment_id"]),
                )
                self._advance_to_enrichment(
                    conn,
                    experiment_id=str(item["experiment_id"]),
                    run_id=str(batch["run_id"]),
                    alpha_id=alpha_id,
                    now=now,
                )
                batch_state = "COMPLETE"
            conn.execute(
                """
                UPDATE simulation_batches
                SET state = ?, last_status = ?, last_response_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (batch_state, parent_status, _json(response), now, batch_id),
            )
            self._event(
                conn,
                str(batch["run_id"]),
                "SIMULATION_PARENT_COMPLETE",
                batch_id=batch_id,
                status_code=_status_code(response),
                payload=response,
                now=now,
            )

    def next_child_item(self, run_id: str, *, now: float) -> BatchItemRecord | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT i.*
                FROM simulation_items i
                JOIN simulation_batches b ON b.id = i.batch_id
                WHERE b.run_id = ? AND b.state = 'CHILD_POLLING'
                  AND i.state = 'POLLING' AND i.not_before <= ?
                ORDER BY i.not_before, b.created_at, i.ordinal
                LIMIT 1
                """,
                (run_id, now),
            ).fetchone()
        return _item_from_row(row) if row else None

    def defer_child_poll(
        self,
        item: BatchItemRecord,
        *,
        response: dict[str, Any],
        not_before: float,
        increment_attempt: bool,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE simulation_items
                SET not_before = ?, attempts = attempts + ?, last_response_json = ?
                WHERE batch_id = ? AND ordinal = ?
                """,
                (
                    not_before,
                    1 if increment_attempt else 0,
                    _json(response),
                    item.batch_id,
                    item.ordinal,
                ),
            )

    def complete_child(
        self,
        item: BatchItemRecord,
        *,
        alpha_id: str,
        response: dict[str, Any],
        now: float,
    ) -> None:
        with self.connect() as conn:
            batch = conn.execute(
                "SELECT run_id FROM simulation_batches WHERE id = ?", (item.batch_id,)
            ).fetchone()
            conn.execute(
                """
                UPDATE simulation_items
                SET state = 'SIM_DONE', alpha_id = ?, last_response_json = ?
                WHERE batch_id = ? AND ordinal = ?
                """,
                (alpha_id, _json(response), item.batch_id, item.ordinal),
            )
            conn.execute(
                """
                UPDATE experiments SET state = 'SIM_DONE', alpha_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (alpha_id, now, item.experiment_id),
            )
            self._advance_to_enrichment(
                conn,
                experiment_id=item.experiment_id,
                run_id=str(batch["run_id"]),
                alpha_id=alpha_id,
                now=now,
            )
            self._event(
                conn,
                str(batch["run_id"]),
                "SIMULATION_CHILD_COMPLETE",
                experiment_id=item.experiment_id,
                batch_id=item.batch_id,
                status_code=_status_code(response),
                payload=response,
                now=now,
            )
            self._refresh_batch_from_items(conn, item.batch_id, now=now)

    def fail_child(
        self,
        item: BatchItemRecord,
        *,
        error: str,
        response: dict[str, Any] | None,
        now: float,
    ) -> None:
        with self.connect() as conn:
            batch = conn.execute(
                "SELECT run_id FROM simulation_batches WHERE id = ?", (item.batch_id,)
            ).fetchone()
            conn.execute(
                """
                UPDATE simulation_items
                SET state = 'PERMANENT_FAILURE', last_error = ?, last_response_json = ?
                WHERE batch_id = ? AND ordinal = ?
                """,
                (error, _json(response) if response else None, item.batch_id, item.ordinal),
            )
            conn.execute(
                """
                UPDATE experiments SET state = 'PERMANENT_FAILURE', last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (error, now, item.experiment_id),
            )
            conn.execute(
                "DELETE FROM simulation_queue WHERE experiment_id = ?",
                (item.experiment_id,),
            )
            self._event(
                conn,
                str(batch["run_id"]),
                "SIMULATION_CHILD_FAILED",
                experiment_id=item.experiment_id,
                batch_id=item.batch_id,
                status_code=_status_code(response),
                payload={"error": error, "response": response},
                now=now,
            )
            self._refresh_batch_from_items(conn, item.batch_id, now=now)

    def retry_child(
        self,
        item: BatchItemRecord,
        *,
        error: str,
        response: dict[str, Any],
        not_before: float,
        now: float,
    ) -> None:
        with self.connect() as conn:
            batch = conn.execute(
                "SELECT run_id FROM simulation_batches WHERE id = ?", (item.batch_id,)
            ).fetchone()
            conn.execute(
                """
                UPDATE simulation_items
                SET state = 'RETRIED', last_error = ?, last_response_json = ?
                WHERE batch_id = ? AND ordinal = ?
                """,
                (error, _json(response), item.batch_id, item.ordinal),
            )
            conn.execute(
                """
                UPDATE experiments
                SET state = 'RETRY_WAIT', batch_id = NULL, child_simulation_id = NULL,
                    alpha_id = NULL, not_before = ?, last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (not_before, error, now, item.experiment_id),
            )
            self._event(
                conn,
                str(batch["run_id"]),
                "SIMULATION_CHILD_REQUEUED",
                experiment_id=item.experiment_id,
                batch_id=item.batch_id,
                status_code=_status_code(response),
                payload={"error": error, "response": response},
                now=now,
            )
            self._refresh_batch_from_items(conn, item.batch_id, now=now)

    def next_enrichment(self, run_id: str, *, now: float) -> ExperimentRecord | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT e.*
                FROM enrichment_queue q
                JOIN experiments e ON e.id = q.experiment_id
                WHERE q.run_id = ? AND e.state IN ('SIM_DONE', 'ENRICH_PNL')
                  AND e.not_before <= ?
                ORDER BY CASE e.state WHEN 'ENRICH_PNL' THEN 0 ELSE 1 END,
                         e.updated_at, e.id
                LIMIT 1
                """,
                (run_id, now),
            ).fetchone()
        return _experiment_from_row(row) if row else None

    def save_alpha_detail(
        self,
        experiment: ExperimentRecord,
        detail: dict[str, Any],
        *,
        response: dict[str, Any],
        now: float,
    ) -> None:
        alpha_id = experiment.alpha_id
        if not alpha_id:
            raise ValueError("Cannot enrich an experiment without alpha_id")
        metrics = _extract_metrics(detail)
        checks = detail.get("is", {}).get("checks", []) if isinstance(detail.get("is"), dict) else []
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO alphas(alpha_id, experiment_id, run_id, candidate_id, detail_json, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    alpha_id,
                    experiment.id,
                    experiment.run_id,
                    experiment.candidate_id,
                    _json(detail),
                    now,
                ),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO alpha_metrics(
                    alpha_id, author, alpha_type, date_created, region, universe_name, delay,
                    decay, neutralization, truncation, max_trade, regular_code, operator_count, pnl,
                    long_count, short_count, turnover, returns_value, drawdown, margin,
                    sharpe, fitness, pyramids
                ) VALUES (
                    :alpha_id, :author, :alpha_type, :date_created, :region, :universe_name,
                    :delay, :decay, :neutralization, :truncation, :max_trade, :regular_code,
                    :operator_count, :pnl, :long_count, :short_count, :turnover,
                    :returns_value, :drawdown, :margin, :sharpe, :fitness, :pyramids
                )
                """,
                {"alpha_id": alpha_id, **metrics},
            )
            conn.execute("DELETE FROM alpha_checks WHERE alpha_id = ?", (alpha_id,))
            for check in checks if isinstance(checks, list) else []:
                if not isinstance(check, dict) or not check.get("name"):
                    continue
                conn.execute(
                    """
                    INSERT INTO alpha_checks(alpha_id, name, result, value_json, raw_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        alpha_id,
                        str(check["name"]),
                        check.get("result"),
                        _json(check.get("value")),
                        _json(check),
                    ),
                )
            conn.execute(
                """
                UPDATE experiments
                SET state = 'ENRICH_PNL', enrich_attempts = 0, not_before = ?, updated_at = ?
                WHERE id = ?
                """,
                (now, now, experiment.id),
            )
            self._event(
                conn,
                experiment.run_id,
                "ALPHA_DETAIL_SAVED",
                experiment_id=experiment.id,
                status_code=_status_code(response),
                payload={"alpha_id": alpha_id},
                now=now,
            )

    def save_pnl(
        self,
        experiment: ExperimentRecord,
        points: Iterable[tuple[str | None, float | None, float | None]],
        *,
        response: dict[str, Any],
        now: float,
    ) -> None:
        alpha_id = experiment.alpha_id
        if not alpha_id:
            raise ValueError("Cannot save PnL without alpha_id")
        point_rows = [
            (alpha_id, ordinal, date_value, cumulative, pnl_delta)
            for ordinal, (date_value, cumulative, pnl_delta) in enumerate(points)
        ]
        with self.connect() as conn:
            conn.execute("DELETE FROM alpha_pnl WHERE alpha_id = ?", (alpha_id,))
            conn.executemany(
                """
                INSERT INTO alpha_pnl(alpha_id, ordinal, date_value, cumulative, pnl_delta)
                VALUES (?, ?, ?, ?, ?)
                """,
                point_rows,
            )
            conn.execute(
                """
                UPDATE experiments
                SET state = 'READY', enrich_attempts = 0, not_before = 0, updated_at = ?
                WHERE id = ?
                """,
                (now, experiment.id),
            )
            conn.execute(
                "DELETE FROM enrichment_queue WHERE experiment_id = ?",
                (experiment.id,),
            )
            self._event(
                conn,
                experiment.run_id,
                "ALPHA_READY",
                experiment_id=experiment.id,
                status_code=_status_code(response),
                payload={"alpha_id": alpha_id, "record_count": len(point_rows)},
                now=now,
            )

    def defer_enrichment(
        self,
        experiment: ExperimentRecord,
        *,
        not_before: float,
        error: str,
        terminal: bool,
        increment_attempt: bool = True,
        now: float,
    ) -> None:
        state = "PERMANENT_FAILURE" if terminal else experiment.state
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE experiments
                SET state = ?, enrich_attempts = enrich_attempts + ?,
                    not_before = ?, last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (state, 1 if increment_attempt else 0, not_before, error, now, experiment.id),
            )
            if terminal:
                conn.execute(
                    "DELETE FROM enrichment_queue WHERE experiment_id = ?",
                    (experiment.id,),
                )

    def set_runtime_float(self, key: str, value: float, *, now: float) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO runtime_state(key, value, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, str(value), now),
            )

    def runtime_float(self, key: str) -> float | None:
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM runtime_state WHERE key = ?", (key,)).fetchone()
        return float(row["value"]) if row else None

    def refresh_run_state(self, run_id: str, *, now: float) -> dict[str, Any]:
        with self.connect() as conn:
            if not self._run_exists(conn, run_id):
                raise KeyError(f"Unknown run id: {run_id}")
            counts = {
                str(row["state"]): int(row["count"])
                for row in conn.execute(
                    "SELECT state, COUNT(*) AS count FROM experiments WHERE run_id = ? GROUP BY state",
                    (run_id,),
                )
            }
            queues = self._queue_counts(conn, run_id)
            total = sum(counts.values())
            terminal_count = sum(counts.get(state, 0) for state in EXPERIMENT_TERMINAL_STATES)
            if total == terminal_count:
                if counts.get("SUBMIT_UNKNOWN", 0):
                    state = "BLOCKED"
                elif counts.get("PERMANENT_FAILURE", 0):
                    state = "COMPLETED_WITH_ERRORS"
                else:
                    state = "COMPLETED"
            else:
                state = "RUNNING"
            terminal = state in {"COMPLETED", "COMPLETED_WITH_ERRORS", "BLOCKED", "CANCELLED"}
            conn.execute(
                "UPDATE runs SET state = ?, updated_at = ?, finished_at = CASE WHEN ? THEN ? ELSE finished_at END WHERE id = ?",
                (state, now, 1 if terminal else 0, now, run_id),
            )
            if terminal:
                payload = {
                    "run_id": run_id,
                    "state": state,
                    "counts": counts,
                    "queues": queues,
                    "total": total,
                }
                conn.execute(
                    """
                    INSERT OR IGNORE INTO outbox_events(run_id, event_type, payload_json, created_at)
                    VALUES (?, 'RUN_TERMINAL', ?, ?)
                    """,
                    (run_id, _json(payload), now),
                )
        return self.run_summary(run_id)

    def run_summary(self, run_id: str) -> dict[str, Any]:
        with self.connect() as conn:
            run = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if not run:
                raise KeyError(f"Unknown run id: {run_id}")
            counts = {
                str(row["state"]): int(row["count"])
                for row in conn.execute(
                    "SELECT state, COUNT(*) AS count FROM experiments WHERE run_id = ? GROUP BY state",
                    (run_id,),
                )
            }
            queues = self._queue_counts(conn, run_id)
        return {
            "run_id": run_id,
            "name": run["name"],
            "state": run["state"],
            "enrichment_profile": run["enrichment_profile"],
            "metadata": json.loads(run["metadata_json"]),
            "counts": counts,
            "queues": queues,
            "total": sum(counts.values()),
            "created_at": run["created_at"],
            "updated_at": run["updated_at"],
            "started_at": run["started_at"],
            "finished_at": run["finished_at"],
        }

    def list_runs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as conn:
            ids = [
                str(row["id"])
                for row in conn.execute(
                    "SELECT id FROM runs ORDER BY created_at DESC LIMIT ?", (max(1, limit),)
                )
            ]
        return [self.run_summary(run_id) for run_id in ids]

    def analysis_results(self, run_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM analysis_alpha_ready
                WHERE run_id = ?
                ORDER BY experiment_id
                """,
                (run_id,),
            ).fetchall()
        results = [dict(row) for row in rows]
        for result in results:
            result["metadata"] = json.loads(result.pop("metadata_json"))
        return results

    def experiment_results(self, run_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    e.id AS experiment_id,
                    e.state,
                    e.priority,
                    e.attempts,
                    e.enrich_attempts,
                    e.alpha_id,
                    e.last_error,
                    e.metadata_json,
                    c.id AS candidate_id,
                    c.fingerprint,
                    c.payload_json
                FROM experiments e
                JOIN candidates c ON c.id = e.candidate_id
                WHERE e.run_id = ?
                ORDER BY e.created_at, e.id
                """,
                (run_id,),
            ).fetchall()
        results = [dict(row) for row in rows]
        for result in results:
            result["metadata"] = json.loads(result.pop("metadata_json"))
            result["payload"] = json.loads(result.pop("payload_json"))
        return results

    def compatibility_results(self, run_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT legacy.*
                FROM simued_alpha_is_pnl legacy
                JOIN alphas a ON a.alpha_id = legacy.id
                WHERE a.run_id = ?
                ORDER BY legacy.id
                """,
                (run_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def next_due_time(self, run_id: str) -> float | None:
        with self.connect() as conn:
            values = [
                row[0]
                for row in conn.execute(
                    """
                    SELECT MIN(not_before) FROM simulation_batches
                    WHERE run_id = ? AND state IN ('RETRY_WAIT', 'POLLING')
                    UNION ALL
                    SELECT MIN(i.not_before) FROM simulation_items i
                    JOIN simulation_batches b ON b.id = i.batch_id
                    WHERE b.run_id = ? AND i.state = 'POLLING'
                    UNION ALL
                    SELECT MIN(not_before) FROM experiments
                    WHERE run_id = ? AND state IN ('QUEUED', 'RETRY_WAIT', 'SIM_DONE', 'ENRICH_PNL')
                    """,
                    (run_id, run_id, run_id),
                ).fetchall()
                if row[0] is not None
            ]
        return min(float(value) for value in values) if values else None

    @staticmethod
    def _advance_to_enrichment(
        conn: sqlite3.Connection,
        *,
        experiment_id: str,
        run_id: str,
        alpha_id: str,
        now: float,
    ) -> None:
        conn.execute(
            "DELETE FROM simulation_queue WHERE experiment_id = ?",
            (experiment_id,),
        )
        conn.execute(
            """
            INSERT INTO enrichment_queue(experiment_id, run_id, alpha_id, enqueued_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(experiment_id) DO UPDATE SET
                run_id = excluded.run_id,
                alpha_id = excluded.alpha_id,
                enqueued_at = excluded.enqueued_at
            """,
            (experiment_id, run_id, alpha_id, now),
        )

    @staticmethod
    def _queue_counts(conn: sqlite3.Connection, run_id: str) -> dict[str, int]:
        simulation = conn.execute(
            "SELECT COUNT(*) FROM simulation_queue WHERE run_id = ?",
            (run_id,),
        ).fetchone()[0]
        enrichment = conn.execute(
            "SELECT COUNT(*) FROM enrichment_queue WHERE run_id = ?",
            (run_id,),
        ).fetchone()[0]
        return {"simulation": int(simulation), "enrichment": int(enrichment)}

    def _refresh_batch_from_items(self, conn: sqlite3.Connection, batch_id: str, *, now: float) -> None:
        counts = {
            str(row["state"]): int(row["count"])
            for row in conn.execute(
                "SELECT state, COUNT(*) AS count FROM simulation_items WHERE batch_id = ? GROUP BY state",
                (batch_id,),
            )
        }
        pending = counts.get("POLLING", 0) + counts.get("BATCHED", 0)
        if pending:
            return
        if counts.get("PERMANENT_FAILURE", 0):
            state = "PARTIAL_FAILURE"
        elif counts.get("RETRIED", 0):
            state = "RETRIED"
        else:
            state = "COMPLETE"
        conn.execute(
            "UPDATE simulation_batches SET state = ?, updated_at = ? WHERE id = ?",
            (state, now, batch_id),
        )

    @staticmethod
    def _run_exists(conn: sqlite3.Connection, run_id: str) -> bool:
        return conn.execute("SELECT 1 FROM runs WHERE id = ?", (run_id,)).fetchone() is not None

    @staticmethod
    def _event(
        conn: sqlite3.Connection,
        run_id: str,
        event_type: str,
        *,
        experiment_id: str | None = None,
        batch_id: str | None = None,
        status_code: int | None = None,
        payload: Any = None,
        now: float,
    ) -> None:
        conn.execute(
            """
            INSERT INTO api_events(
                run_id, experiment_id, batch_id, event_type, status_code, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                experiment_id,
                batch_id,
                event_type,
                status_code,
                _json(payload) if payload is not None else None,
                now,
            ),
        )


def candidate_fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()


def scheduling_profile(payload: dict[str, Any]) -> tuple[str, int]:
    simulation_type = str(payload["type"]).upper()
    settings = payload["settings"]
    language = str(settings.get("language") or "FASTEXPR").upper()
    region = str(settings.get("region") or "").upper()
    instrument_type = str(settings.get("instrumentType") or "").upper()
    if simulation_type == "SUPER":
        batch_limit = 1
    elif region == "GLB":
        batch_limit = 5 if language == "FASTEXPR" else 1
    else:
        batch_limit = 10 if language == "FASTEXPR" else 1
    compatibility = {
        "type": simulation_type,
        "language": language,
        "instrument_type": instrument_type,
        "region": region,
        "delay": settings.get("delay"),
        "batch_limit": batch_limit,
    }
    return candidate_fingerprint(compatibility), batch_limit


def _extract_metrics(detail: dict[str, Any]) -> dict[str, Any]:
    settings = detail.get("settings") if isinstance(detail.get("settings"), dict) else {}
    metrics = detail.get("is") if isinstance(detail.get("is"), dict) else {}
    regular = detail.get("regular")
    if isinstance(regular, dict):
        regular_code = regular.get("code")
        operator_count = regular.get("operatorCount")
    else:
        regular_code = regular
        operator_count = None
    author = detail.get("author")
    if isinstance(author, dict):
        author = author.get("id") or author.get("name") or _json(author)
    pyramid_names: list[str] = []
    for pyramid in detail.get("pyramids") or []:
        if isinstance(pyramid, dict) and pyramid.get("name"):
            pyramid_names.append(str(pyramid["name"]))
        elif isinstance(pyramid, str):
            pyramid_names.append(pyramid)
    for check in metrics.get("checks") or []:
        if not isinstance(check, dict) or check.get("name") != "MATCHES_PYRAMID":
            continue
        for pyramid in check.get("pyramids") or []:
            if isinstance(pyramid, dict) and pyramid.get("name"):
                pyramid_names.append(str(pyramid["name"]))
    for classification in detail.get("classifications") or []:
        if (
            isinstance(classification, dict)
            and classification.get("id") == "DATA_USAGE:SINGLE_DATA_SET"
        ):
            pyramid_names.append("ATOM")
            break
    pyramid_names = list(dict.fromkeys(pyramid_names))
    return {
        "author": author,
        "alpha_type": detail.get("type"),
        "date_created": detail.get("dateCreated"),
        "region": settings.get("region"),
        "universe_name": settings.get("universe"),
        "delay": settings.get("delay"),
        "decay": settings.get("decay"),
        "neutralization": settings.get("neutralization"),
        "truncation": settings.get("truncation"),
        "max_trade": settings.get("maxTrade"),
        "regular_code": regular_code,
        "operator_count": operator_count,
        "pnl": metrics.get("pnl"),
        "long_count": metrics.get("longCount"),
        "short_count": metrics.get("shortCount"),
        "turnover": metrics.get("turnover"),
        "returns_value": metrics.get("returns"),
        "drawdown": metrics.get("drawdown"),
        "margin": metrics.get("margin"),
        "sharpe": metrics.get("sharpe"),
        "fitness": metrics.get("fitness"),
        "pyramids": ", ".join(pyramid_names),
    }


def _batch_from_row(row: sqlite3.Row) -> BatchRecord:
    return BatchRecord(
        id=str(row["id"]),
        run_id=str(row["run_id"]),
        state=str(row["state"]),
        payload=json.loads(row["payload_json"]),
        attempts=int(row["attempts"]),
        poll_attempts=int(row["poll_attempts"]),
        parent_simulation_id=row["parent_simulation_id"],
        location=row["location"],
    )


def _item_from_row(row: sqlite3.Row) -> BatchItemRecord:
    return BatchItemRecord(
        batch_id=str(row["batch_id"]),
        experiment_id=str(row["experiment_id"]),
        ordinal=int(row["ordinal"]),
        child_simulation_id=row["child_simulation_id"],
        alpha_id=row["alpha_id"],
        state=str(row["state"]),
        attempts=int(row["attempts"]),
    )


def _experiment_from_row(row: sqlite3.Row) -> ExperimentRecord:
    return ExperimentRecord(
        id=str(row["id"]),
        run_id=str(row["run_id"]),
        candidate_id=str(row["candidate_id"]),
        state=str(row["state"]),
        alpha_id=row["alpha_id"],
        attempts=int(row["enrich_attempts"]),
    )


def _status_code(response: dict[str, Any] | None) -> int | None:
    if not response:
        return None
    value = (response.get("response") or {}).get("status_code")
    return int(value) if isinstance(value, int) else None


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"
