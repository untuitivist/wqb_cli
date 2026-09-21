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

from ..core.simulation import region_agnostic_child_ids
from .models import (
    EXPERIMENT_TERMINAL_STATES,
    BatchItemRecord,
    BatchRecord,
    EnqueueResult,
    ExperimentRecord,
    SimulationManifest,
)


SCHEMA_VERSION = 8
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
    enqueued_at REAL NOT NULL,
    last_attempt_at REAL NOT NULL DEFAULT 0,
    attempt_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS enrichment_queue (
    experiment_id TEXT PRIMARY KEY REFERENCES experiments(id) ON DELETE CASCADE,
    run_id TEXT NOT NULL REFERENCES runs(id),
    alpha_id TEXT NOT NULL,
    enqueued_at REAL NOT NULL,
    claim_owner TEXT
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
    claim_owner TEXT,
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
    claim_owner TEXT,
    PRIMARY KEY(batch_id, ordinal)
);

CREATE TABLE IF NOT EXISTS simulation_failures (
    batch_id TEXT NOT NULL REFERENCES simulation_batches(id),
    experiment_id TEXT NOT NULL REFERENCES experiments(id),
    run_id TEXT NOT NULL REFERENCES runs(id),
    error TEXT NOT NULL,
    response_json TEXT,
    created_at REAL NOT NULL,
    PRIMARY KEY(batch_id, experiment_id)
);
CREATE INDEX IF NOT EXISTS idx_simulation_failures_experiment
    ON simulation_failures(experiment_id);

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
    ordinal INTEGER NOT NULL,
    name TEXT NOT NULL,
    result TEXT,
    value_json TEXT,
    raw_json TEXT NOT NULL,
    PRIMARY KEY(alpha_id, ordinal)
);

CREATE TABLE IF NOT EXISTS alpha_pnl (
    alpha_id TEXT NOT NULL REFERENCES alphas(alpha_id),
    ordinal INTEGER NOT NULL,
    date_value TEXT,
    cumulative REAL,
    pnl_delta REAL,
    PRIMARY KEY(alpha_id, ordinal)
);

CREATE TABLE IF NOT EXISTS region_agnostic_children (
    parent_alpha_id TEXT NOT NULL REFERENCES alphas(alpha_id),
    child_alpha_id TEXT NOT NULL,
    region TEXT,
    state TEXT NOT NULL DEFAULT 'SIM_DONE',
    detail_json TEXT,
    pnl_response_json TEXT,
    pnl_records INTEGER NOT NULL DEFAULT 0,
    updated_at REAL NOT NULL,
    PRIMARY KEY(parent_alpha_id, child_alpha_id)
);

CREATE TABLE IF NOT EXISTS region_agnostic_child_pnl (
    parent_alpha_id TEXT NOT NULL,
    child_alpha_id TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    date_value TEXT,
    cumulative REAL,
    pnl_delta REAL,
    PRIMARY KEY(parent_alpha_id, child_alpha_id, ordinal),
    FOREIGN KEY(parent_alpha_id, child_alpha_id)
        REFERENCES region_agnostic_children(parent_alpha_id, child_alpha_id)
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
                        'QUEUED', 'RETRY_WAIT', 'BATCHED', 'SUBMITTING', 'SIMULATING',
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
            if current < 3:
                # v3 reserves "submit" for Alpha submission; these literals only migrate v2 data.
                for table in ("experiments", "simulation_batches", "simulation_items"):
                    conn.execute(
                        f"""
                        UPDATE {table}
                        SET state = CASE state
                            WHEN 'SUBMITTING' THEN 'SIMULATING'
                            WHEN 'SUBMIT_UNKNOWN' THEN 'SIMULATE_UNKNOWN'
                            ELSE state
                        END
                        WHERE state IN ('SUBMITTING', 'SUBMIT_UNKNOWN')
                        """
                    )
                for table in ("experiments", "simulation_batches", "simulation_items"):
                    conn.execute(
                        f"""
                        UPDATE {table}
                        SET last_error = REPLACE(
                            REPLACE(
                                REPLACE(last_error,
                                    'worker_interrupted_during_submit',
                                    'worker_interrupted_during_simulate'
                                ),
                                'cancelled_during_submit',
                                'cancelled_during_simulate'
                            ),
                            'unexpected_submit_status_',
                            'unexpected_simulate_status_'
                        )
                        WHERE last_error IS NOT NULL
                        """
                    )
                conn.execute(
                    """
                    UPDATE api_events
                    SET event_type = CASE event_type
                        WHEN 'SUBMIT_BECAME_AMBIGUOUS' THEN 'SIMULATE_BECAME_AMBIGUOUS'
                        WHEN 'SIMULATION_SUBMITTED' THEN 'SIMULATION_ACCEPTED'
                        WHEN 'SIMULATION_SUBMIT_RETRY' THEN 'SIMULATE_RETRY'
                        ELSE event_type
                    END,
                    payload_json = REPLACE(
                        REPLACE(payload_json, 'SUBMIT_UNKNOWN', 'SIMULATE_UNKNOWN'),
                        'SUBMITTING', 'SIMULATING'
                    )
                    """
                )
                conn.execute(
                    """
                    UPDATE outbox_events
                    SET payload_json = REPLACE(
                        REPLACE(payload_json, 'SUBMIT_UNKNOWN', 'SIMULATE_UNKNOWN'),
                        'SUBMITTING', 'SIMULATING'
                    )
                    """
                )
                old_backpressure = conn.execute(
                    """
                    SELECT value, updated_at FROM runtime_state
                    WHERE key = 'simulation_submit_not_before'
                    """
                ).fetchone()
                if old_backpressure:
                    current_backpressure = conn.execute(
                        """
                        SELECT updated_at FROM runtime_state
                        WHERE key = 'simulation_request_not_before'
                        """
                    ).fetchone()
                    if (
                        current_backpressure is None
                        or float(old_backpressure["updated_at"])
                        >= float(current_backpressure["updated_at"])
                    ):
                        conn.execute(
                            """
                            INSERT INTO runtime_state(key, value, updated_at)
                            VALUES ('simulation_request_not_before', ?, ?)
                            ON CONFLICT(key) DO UPDATE SET
                                value = excluded.value,
                                updated_at = excluded.updated_at
                            """,
                            (old_backpressure["value"], old_backpressure["updated_at"]),
                        )
                    conn.execute(
                        "DELETE FROM runtime_state WHERE key = 'simulation_submit_not_before'"
                    )
            if current < 4:
                _add_column_if_missing(conn, "simulation_batches", "claim_owner TEXT")
                _add_column_if_missing(conn, "simulation_items", "claim_owner TEXT")
                _add_column_if_missing(conn, "enrichment_queue", "claim_owner TEXT")
            if current < 5:
                _add_column_if_missing(
                    conn,
                    "simulation_queue",
                    "last_attempt_at REAL NOT NULL DEFAULT 0",
                )
                _add_column_if_missing(
                    conn,
                    "simulation_queue",
                    "attempt_count INTEGER NOT NULL DEFAULT 0",
                )
            if current < 6:
                _migrate_alpha_checks_v6(conn)
            if current < 7:
                for candidate in conn.execute(
                    "SELECT id, payload_json FROM candidates WHERE simulation_type = 'REGION_AGNOSTIC'"
                ).fetchall():
                    compatibility_key, batch_limit = scheduling_profile(json.loads(candidate["payload_json"]))
                    conn.execute(
                        "UPDATE candidates SET compatibility_key = ?, batch_limit = ? WHERE id = ?",
                        (compatibility_key, batch_limit, candidate["id"]),
                    )
            if current < 8:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO simulation_failures(
                        batch_id, experiment_id, run_id, error, response_json, created_at
                    )
                    SELECT item.batch_id, item.experiment_id, batch.run_id,
                           COALESCE(item.last_error, 'legacy_simulation_failure'),
                           item.last_response_json, batch.updated_at
                    FROM simulation_items item
                    JOIN simulation_batches batch ON batch.id = item.batch_id
                    WHERE item.state = 'RETRIED'
                    """
                )
                for candidate in conn.execute(
                    "SELECT id, payload_json FROM candidates WHERE simulation_type = 'REGULAR'"
                ).fetchall():
                    compatibility_key, batch_limit = scheduling_profile(json.loads(candidate["payload_json"]))
                    conn.execute(
                        "UPDATE candidates SET compatibility_key = ?, batch_limit = ? WHERE id = ?",
                        (compatibility_key, batch_limit, candidate["id"]),
                    )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_batches_claimable "
                "ON simulation_batches(run_id, state, claim_owner, not_before, created_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_items_claimable "
                "ON simulation_items(state, claim_owner, not_before, batch_id, ordinal)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_enrichment_claimable "
                "ON enrichment_queue(run_id, claim_owner, enqueued_at, experiment_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_simulation_queue_attempt "
                "ON simulation_queue(run_id, last_attempt_at, enqueued_at, experiment_id)"
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
            conn.execute(
                "UPDATE simulation_batches SET claim_owner = NULL WHERE run_id = ?",
                (run_id,),
            )
            conn.execute(
                """
                UPDATE simulation_items SET claim_owner = NULL
                WHERE batch_id IN (SELECT id FROM simulation_batches WHERE run_id = ?)
                """,
                (run_id,),
            )
            conn.execute(
                "UPDATE enrichment_queue SET claim_owner = NULL WHERE run_id = ?",
                (run_id,),
            )
            ambiguous = conn.execute(
                """
                SELECT id FROM simulation_batches
                WHERE run_id = ? AND state = 'SIMULATING'
                """,
                (run_id,),
            ).fetchall()
            for row in ambiguous:
                batch_id = str(row["id"])
                items = conn.execute(
                    "SELECT experiment_id, ordinal FROM simulation_items WHERE batch_id = ?",
                    (batch_id,),
                ).fetchall()
                claimed = 0
                for item in items:
                    owner = conn.execute(
                        """
                        UPDATE experiments
                        SET state = 'SIMULATE_UNKNOWN', last_error = ?, updated_at = ?
                        WHERE id = ? AND batch_id = ? AND state = 'SIMULATING'
                          AND EXISTS (
                              SELECT 1 FROM simulation_queue q
                              WHERE q.experiment_id = experiments.id
                          )
                        """,
                        (
                            "worker_interrupted_during_simulate",
                            now,
                            item["experiment_id"],
                            batch_id,
                        ),
                    )
                    item_state = "SIMULATE_UNKNOWN" if owner.rowcount else "SUPERSEDED"
                    claimed += int(bool(owner.rowcount))
                    conn.execute(
                        """
                        UPDATE simulation_items
                        SET state = ?, last_error = ?, claim_owner = NULL
                        WHERE batch_id = ? AND ordinal = ?
                        """,
                        (
                            item_state,
                            "worker_interrupted_during_simulate",
                            batch_id,
                            item["ordinal"],
                        ),
                    )
                conn.execute(
                    """
                    UPDATE simulation_batches
                    SET state = ?, last_error = ?, claim_owner = NULL, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        "SIMULATE_UNKNOWN" if claimed else "SUPERSEDED",
                        "worker_interrupted_during_simulate",
                        now,
                        batch_id,
                    ),
                )
                self._event(
                    conn,
                    run_id,
                    "SIMULATE_BECAME_AMBIGUOUS",
                    batch_id=batch_id,
                    payload={
                        "reason": "worker_interrupted_during_simulate",
                        "claimed_experiments": claimed,
                    },
                    now=now,
                )

    def cancel_run(
        self,
        run_id: str,
        *,
        reason: str,
        allow_active_lease: bool = False,
        now: float | None = None,
    ) -> dict[str, Any]:
        timestamp = time.time() if now is None else now
        detail = reason.strip()
        if not detail:
            raise ValueError("Cancellation reason must not be empty")
        with self.connect() as conn:
            run = conn.execute("SELECT state FROM runs WHERE id = ?", (run_id,)).fetchone()
            if not run:
                raise KeyError(f"Unknown run id: {run_id}")
            if str(run["state"]) in {"COMPLETED", "COMPLETED_WITH_ERRORS", "BLOCKED", "CANCELLED"}:
                return self.run_summary(run_id)
            lease = conn.execute(
                "SELECT owner, lease_until FROM run_leases WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if lease and float(lease["lease_until"]) > timestamp and not allow_active_lease:
                raise RuntimeError(
                    "Run has an active worker lease; stop and verify the worker first, "
                    "then retry with allow_active_lease"
                )

            conn.execute(
                """
                UPDATE simulation_items
                SET state = 'SIMULATE_UNKNOWN', last_error = ?
                WHERE batch_id IN (
                    SELECT id FROM simulation_batches
                    WHERE run_id = ? AND state = 'SIMULATING'
                )
                """,
                (f"cancelled_during_simulate: {detail}", run_id),
            )
            conn.execute(
                """
                UPDATE simulation_items
                SET state = 'CANCELLED', last_error = ?
                WHERE batch_id IN (
                    SELECT id FROM simulation_batches
                    WHERE run_id = ? AND state IN (
                        'CREATED', 'RETRY_WAIT', 'POLLING', 'CHILD_POLLING'
                    )
                ) AND state IN ('BATCHED', 'POLLING')
                """,
                (f"cancelled: {detail}", run_id),
            )
            conn.execute(
                """
                UPDATE simulation_batches
                SET state = CASE
                        WHEN state = 'SIMULATING' THEN 'SIMULATE_UNKNOWN'
                        ELSE 'CANCELLED'
                    END,
                    last_error = ?, updated_at = ?
                WHERE run_id = ? AND state IN (
                    'CREATED', 'RETRY_WAIT', 'SIMULATING', 'POLLING', 'CHILD_POLLING'
                )
                """,
                (f"cancelled: {detail}", timestamp, run_id),
            )
            conn.execute(
                """
                UPDATE experiments
                SET state = 'SIMULATE_UNKNOWN', last_error = ?, updated_at = ?
                WHERE run_id = ? AND state = 'SIMULATING'
                """,
                (f"cancelled_during_simulate: {detail}", timestamp, run_id),
            )
            conn.execute(
                """
                UPDATE experiments
                SET state = 'CANCELLED', last_error = ?, updated_at = ?
                WHERE run_id = ? AND state NOT IN (
                    'READY', 'PERMANENT_FAILURE', 'SIMULATE_UNKNOWN', 'CANCELLED'
                )
                """,
                (f"cancelled: {detail}", timestamp, run_id),
            )
            conn.execute(
                """
                DELETE FROM simulation_queue
                WHERE run_id = ? AND experiment_id IN (
                    SELECT id FROM experiments WHERE run_id = ? AND state = 'CANCELLED'
                )
                """,
                (run_id, run_id),
            )
            conn.execute(
                """
                DELETE FROM enrichment_queue
                WHERE run_id = ? AND experiment_id IN (
                    SELECT id FROM experiments WHERE run_id = ? AND state = 'CANCELLED'
                )
                """,
                (run_id, run_id),
            )
            conn.execute(
                """
                UPDATE runs
                SET state = 'CANCELLED', updated_at = ?, finished_at = ?
                WHERE id = ?
                """,
                (timestamp, timestamp, run_id),
            )
            conn.execute("DELETE FROM run_leases WHERE run_id = ?", (run_id,))
            counts = {
                str(row["state"]): int(row["count"])
                for row in conn.execute(
                    "SELECT state, COUNT(*) AS count FROM experiments WHERE run_id = ? GROUP BY state",
                    (run_id,),
                )
            }
            queues = self._queue_counts(conn, run_id)
            payload = {
                "run_id": run_id,
                "state": "CANCELLED",
                "reason": detail,
                "counts": counts,
                "queues": queues,
                "total": sum(counts.values()),
            }
            self._event(
                conn,
                run_id,
                "RUN_CANCELLED",
                payload=payload,
                now=timestamp,
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO outbox_events(run_id, event_type, payload_json, created_at)
                VALUES (?, 'RUN_TERMINAL', ?, ?)
                """,
                (run_id, _json(payload), timestamp),
            )
        return self.run_summary(run_id)

    def next_simulate_batch(self, run_id: str, *, now: float) -> BatchRecord | None:
        global_not_before = self.simulation_not_before()
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

    def create_next_batch(
        self,
        run_id: str,
        *,
        now: float,
        resend_interval_seconds: float | None = 0.0,
    ) -> BatchRecord | None:
        global_not_before = self.simulation_not_before()
        if global_not_before is not None and now < global_not_before:
            return None
        resend_cutoff = (
            now - max(0.0, resend_interval_seconds)
            if resend_interval_seconds is not None else None
        )
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            selected_head = conn.execute(
                """
                SELECT e.id AS experiment_id, c.*
                FROM simulation_queue q
                JOIN experiments e ON e.id = q.experiment_id
                JOIN candidates c ON c.id = e.candidate_id
                WHERE q.run_id = ?
                  AND e.state IN ('QUEUED', 'RETRY_WAIT', 'POLLING')
                  AND e.not_before <= ?
                  AND (e.state <> 'POLLING' OR (? IS NOT NULL AND q.last_attempt_at <= ?))
                ORDER BY q.last_attempt_at, e.priority DESC, q.enqueued_at, e.id
                LIMIT 1
                """,
                (run_id, now, resend_cutoff, resend_cutoff),
            ).fetchone()
            if selected_head is None:
                return None
            compatible = conn.execute(
                """
                SELECT e.id AS experiment_id, c.payload_json
                FROM simulation_queue q
                JOIN experiments e ON e.id = q.experiment_id
                JOIN candidates c ON c.id = e.candidate_id
                WHERE q.run_id = ?
                  AND e.state IN ('QUEUED', 'RETRY_WAIT', 'POLLING')
                  AND e.not_before <= ?
                  AND (e.state <> 'POLLING' OR (? IS NOT NULL AND q.last_attempt_at <= ?))
                  AND c.compatibility_key = ?
                ORDER BY q.last_attempt_at, e.priority DESC, q.enqueued_at, e.id
                LIMIT ?
                """,
                (
                    run_id,
                    now,
                    resend_cutoff,
                    resend_cutoff,
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
                conn.execute(
                    """
                    UPDATE simulation_queue
                    SET last_attempt_at = ?, attempt_count = attempt_count + 1
                    WHERE experiment_id = ?
                    """,
                    (now, experiment_id),
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

    def mark_simulate_started(self, batch_id: str, *, now: float) -> None:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE simulation_batches
                SET state = 'SIMULATING', attempts = attempts + 1, updated_at = ?
                WHERE id = ? AND state IN ('CREATED', 'RETRY_WAIT')
                """,
                (now, batch_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError(f"Batch {batch_id} is no longer ready to simulate")
            conn.execute(
                "UPDATE experiments SET state = 'SIMULATING', attempts = attempts + 1, updated_at = ? WHERE batch_id = ?",
                (now, batch_id),
            )

    def accept_simulation(
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
                "SIMULATION_ACCEPTED",
                batch_id=batch_id,
                status_code=_status_code(response),
                payload=response,
                now=now,
            )

    def retry_simulate(
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
                "SIMULATE_RETRY",
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
        if state not in {"PERMANENT_FAILURE", "SIMULATE_UNKNOWN"}:
            raise ValueError(f"Unsupported batch failure state: {state}")
        batch_state = "FAILED" if state == "PERMANENT_FAILURE" else "SIMULATE_UNKNOWN"
        with self.connect() as conn:
            row = conn.execute("SELECT run_id FROM simulation_batches WHERE id = ?", (batch_id,)).fetchone()
            items = conn.execute(
                "SELECT experiment_id, ordinal FROM simulation_items WHERE batch_id = ?",
                (batch_id,),
            ).fetchall()
            claimed = 0
            for item in items:
                owner = conn.execute(
                    """
                    UPDATE experiments
                    SET state = ?, last_error = ?, updated_at = ?
                    WHERE id = ? AND batch_id = ?
                      AND state IN (
                          'QUEUED', 'RETRY_WAIT', 'BATCHED', 'SIMULATING',
                          'POLLING', 'SIMULATE_UNKNOWN'
                      )
                      AND EXISTS (
                          SELECT 1 FROM simulation_queue q
                          WHERE q.experiment_id = experiments.id
                      )
                    """,
                    (state, error, now, item["experiment_id"], batch_id),
                )
                item_state = state if owner.rowcount else "SUPERSEDED"
                claimed += int(bool(owner.rowcount))
                conn.execute(
                    """
                    UPDATE simulation_items
                    SET state = ?, last_error = ?, last_response_json = ?, claim_owner = NULL
                    WHERE batch_id = ? AND ordinal = ?
                    """,
                    (
                        item_state,
                        error,
                        _json(response) if response else None,
                        batch_id,
                        item["ordinal"],
                    ),
                )
                if owner.rowcount and state == "PERMANENT_FAILURE":
                    conn.execute(
                        "DELETE FROM simulation_queue WHERE experiment_id = ?",
                        (item["experiment_id"],),
                    )
            conn.execute(
                """
                UPDATE simulation_batches
                SET state = ?, last_error = ?, last_response_json = ?,
                    claim_owner = NULL, updated_at = ?
                WHERE id = ?
                """,
                (
                    batch_state if claimed else "SUPERSEDED",
                    error,
                    _json(response) if response else None,
                    now,
                    batch_id,
                ),
            )
            self._event(
                conn,
                str(row["run_id"]),
                "SIMULATION_BATCH_FAILED",
                batch_id=batch_id,
                status_code=_status_code(response),
                payload={
                    "state": state,
                    "error": error,
                    "response": response,
                    "claimed_experiments": claimed,
                },
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
        max_retries: int = 1,
    ) -> None:
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            batch = conn.execute(
                "SELECT run_id FROM simulation_batches WHERE id = ?", (batch_id,)
            ).fetchone()
            items = conn.execute(
                "SELECT experiment_id, ordinal FROM simulation_items WHERE batch_id = ?",
                (batch_id,),
            ).fetchall()
            outcomes: list[str] = []
            for item in items:
                outcome = self._retry_simulation_item(
                    conn, batch_id=batch_id, experiment_id=item["experiment_id"],
                    ordinal=item["ordinal"], run_id=batch["run_id"], child_id=None,
                    error=error, response=response, not_before=not_before,
                    now=now, max_retries=max_retries,
                )
                if outcome is not None:
                    outcomes.append(outcome)
            if not outcomes:
                return
            conn.execute(
                """
                UPDATE simulation_batches
                SET last_error = ?, last_response_json = ?,
                    claim_owner = NULL, updated_at = ?
                WHERE id = ?
                """,
                (error, _json(response), now, batch_id),
            )
            self._refresh_batch_from_items(conn, batch_id, now=now)
            self._event(
                conn,
                str(batch["run_id"]),
                "SIMULATION_BATCH_REQUEUED" if "RETRIED" in outcomes else "SIMULATION_BATCH_FAILED",
                batch_id=batch_id,
                status_code=_status_code(response),
                payload={
                    "error": error,
                    "response": response,
                    "claimed_experiments": sum(outcome != "SUPERSEDED" for outcome in outcomes),
                    "exhausted_experiments": outcomes.count("PERMANENT_FAILURE"),
                },
                now=now,
            )

    def next_poll_batch(self, run_id: str, *, now: float) -> BatchRecord | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM simulation_batches
                WHERE run_id = ? AND state = 'POLLING'
                  AND claim_owner IS NULL AND not_before <= ?
                ORDER BY not_before, created_at
                LIMIT 1
                """,
                (run_id, now),
            ).fetchone()
        return _batch_from_row(row) if row else None

    def claim_poll_batch(
        self,
        run_id: str,
        *,
        owner: str,
        now: float,
    ) -> BatchRecord | None:
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT * FROM simulation_batches
                WHERE run_id = ? AND state = 'POLLING'
                  AND claim_owner IS NULL AND not_before <= ?
                ORDER BY not_before, created_at
                LIMIT 1
                """,
                (run_id, now),
            ).fetchone()
            if row is not None:
                conn.execute(
                    "UPDATE simulation_batches SET claim_owner = ? WHERE id = ?",
                    (owner, row["id"]),
                )
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
                    poll_attempts = poll_attempts + ?, claim_owner = NULL, updated_at = ?
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
                claimed = 0
                for item, child_id in zip(items, child_ids):
                    owner = conn.execute(
                        """
                        UPDATE experiments
                        SET state = 'CHILD_POLLING', batch_id = ?, child_simulation_id = ?,
                            last_error = NULL, updated_at = ?
                        WHERE id = ?
                          AND state IN (
                              'QUEUED', 'RETRY_WAIT', 'BATCHED', 'SIMULATING',
                              'POLLING', 'SIMULATE_UNKNOWN'
                          )
                          AND EXISTS (
                              SELECT 1 FROM simulation_queue q
                              WHERE q.experiment_id = experiments.id
                          )
                        """,
                        (batch_id, child_id, now, item["experiment_id"]),
                    )
                    if owner.rowcount:
                        claimed += 1
                        item_state = "POLLING"
                    else:
                        item_state = "SUPERSEDED"
                    conn.execute(
                        """
                        UPDATE simulation_items
                        SET state = ?, child_simulation_id = ?, not_before = ?,
                            last_response_json = ?, claim_owner = NULL
                        WHERE batch_id = ? AND ordinal = ?
                        """,
                        (
                            item_state,
                            child_id,
                            now,
                            _json(response),
                            batch_id,
                            item["ordinal"],
                        ),
                    )
                batch_state = "CHILD_POLLING" if claimed else "SUPERSEDED"
            else:
                if len(items) != 1 or not alpha_id:
                    raise ValueError("Single simulation completed without an alpha id")
                item = items[0]
                owner = conn.execute(
                    """
                    UPDATE experiments
                    SET state = 'SIM_DONE', batch_id = ?, alpha_id = ?,
                        last_error = NULL, updated_at = ?
                    WHERE id = ?
                      AND state IN (
                          'QUEUED', 'RETRY_WAIT', 'BATCHED', 'SIMULATING',
                          'POLLING', 'SIMULATE_UNKNOWN'
                      )
                      AND EXISTS (
                          SELECT 1 FROM simulation_queue q
                          WHERE q.experiment_id = experiments.id
                      )
                    """,
                    (batch_id, alpha_id, now, item["experiment_id"]),
                )
                item_state = "SIM_DONE" if owner.rowcount else "SUPERSEDED"
                conn.execute(
                    """
                    UPDATE simulation_items
                    SET state = ?, alpha_id = ?, last_response_json = ?, claim_owner = NULL
                    WHERE batch_id = ? AND ordinal = 0
                    """,
                    (item_state, alpha_id, _json(response), batch_id),
                )
                if owner.rowcount:
                    self._advance_to_enrichment(
                        conn,
                        experiment_id=str(item["experiment_id"]),
                        run_id=str(batch["run_id"]),
                        alpha_id=alpha_id,
                        now=now,
                    )
                    batch_state = "COMPLETE"
                else:
                    batch_state = "SUPERSEDED"
            conn.execute(
                """
                UPDATE simulation_batches
                SET state = ?, last_status = ?, last_response_json = ?,
                    claim_owner = NULL, updated_at = ?
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
                  AND i.state = 'POLLING' AND i.claim_owner IS NULL AND i.not_before <= ?
                ORDER BY i.not_before, b.created_at, i.ordinal
                LIMIT 1
                """,
                (run_id, now),
            ).fetchone()
        return _item_from_row(row) if row else None

    def claim_child_item(
        self,
        run_id: str,
        *,
        owner: str,
        now: float,
    ) -> BatchItemRecord | None:
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT i.*
                FROM simulation_items i
                JOIN simulation_batches b ON b.id = i.batch_id
                WHERE b.run_id = ? AND b.state = 'CHILD_POLLING'
                  AND i.state = 'POLLING' AND i.claim_owner IS NULL
                  AND i.not_before <= ?
                ORDER BY i.not_before, b.created_at, i.ordinal
                LIMIT 1
                """,
                (run_id, now),
            ).fetchone()
            if row is not None:
                conn.execute(
                    """
                    UPDATE simulation_items SET claim_owner = ?
                    WHERE batch_id = ? AND ordinal = ?
                    """,
                    (owner, row["batch_id"], row["ordinal"]),
                )
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
                SET not_before = ?, attempts = attempts + ?, last_response_json = ?,
                    claim_owner = NULL
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
            owner = conn.execute(
                """
                UPDATE experiments
                SET state = 'SIM_DONE', alpha_id = ?, last_error = NULL, updated_at = ?
                WHERE id = ? AND state = 'CHILD_POLLING' AND batch_id = ?
                  AND child_simulation_id = ?
                  AND EXISTS (
                      SELECT 1 FROM simulation_queue q
                      WHERE q.experiment_id = experiments.id
                  )
                """,
                (
                    alpha_id,
                    now,
                    item.experiment_id,
                    item.batch_id,
                    item.child_simulation_id,
                ),
            )
            item_state = "SIM_DONE" if owner.rowcount else "SUPERSEDED"
            conn.execute(
                """
                UPDATE simulation_items
                SET state = ?, alpha_id = ?, last_response_json = ?,
                    claim_owner = NULL
                WHERE batch_id = ? AND ordinal = ?
                """,
                (item_state, alpha_id, _json(response), item.batch_id, item.ordinal),
            )
            if owner.rowcount:
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
                "SIMULATION_CHILD_COMPLETE" if owner.rowcount else "SIMULATION_CHILD_SUPERSEDED",
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
            owner = conn.execute(
                """
                UPDATE experiments
                SET state = 'PERMANENT_FAILURE', last_error = ?, updated_at = ?
                WHERE id = ? AND state = 'CHILD_POLLING' AND batch_id = ?
                  AND child_simulation_id = ?
                  AND EXISTS (
                      SELECT 1 FROM simulation_queue q
                      WHERE q.experiment_id = experiments.id
                  )
                """,
                (
                    error,
                    now,
                    item.experiment_id,
                    item.batch_id,
                    item.child_simulation_id,
                ),
            )
            item_state = "PERMANENT_FAILURE" if owner.rowcount else "SUPERSEDED"
            conn.execute(
                """
                UPDATE simulation_items
                SET state = ?, last_error = ?, last_response_json = ?,
                    claim_owner = NULL
                WHERE batch_id = ? AND ordinal = ?
                """,
                (
                    item_state,
                    error,
                    _json(response) if response else None,
                    item.batch_id,
                    item.ordinal,
                ),
            )
            if owner.rowcount:
                conn.execute(
                    "DELETE FROM simulation_queue WHERE experiment_id = ?",
                    (item.experiment_id,),
                )
            self._event(
                conn,
                str(batch["run_id"]),
                "SIMULATION_CHILD_FAILED" if owner.rowcount else "SIMULATION_CHILD_SUPERSEDED",
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
        max_retries: int = 1,
    ) -> None:
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            batch = conn.execute(
                "SELECT run_id FROM simulation_batches WHERE id = ?", (item.batch_id,)
            ).fetchone()
            outcome = self._retry_simulation_item(
                conn, batch_id=item.batch_id, experiment_id=item.experiment_id,
                ordinal=item.ordinal, run_id=batch["run_id"], child_id=item.child_simulation_id,
                error=error, response=response, not_before=not_before,
                now=now, max_retries=max_retries,
            )
            if outcome is None:
                return
            event_type = {
                "RETRIED": "SIMULATION_CHILD_REQUEUED",
                "PERMANENT_FAILURE": "SIMULATION_CHILD_FAILED",
                "SUPERSEDED": "SIMULATION_CHILD_SUPERSEDED",
            }[outcome]
            self._event(
                conn,
                str(batch["run_id"]),
                event_type,
                experiment_id=item.experiment_id,
                batch_id=item.batch_id,
                status_code=_status_code(response),
                payload={"error": error, "response": response},
                now=now,
            )
            self._refresh_batch_from_items(conn, item.batch_id, now=now)

    def _retry_simulation_item(
        self,
        conn: sqlite3.Connection,
        *,
        batch_id: str,
        experiment_id: str,
        ordinal: int,
        run_id: str,
        child_id: str | None,
        error: str,
        response: dict[str, Any],
        not_before: float,
        now: float,
        max_retries: int,
    ) -> str | None:
        if conn.execute(
            "SELECT 1 FROM simulation_failures WHERE batch_id = ? AND experiment_id = ?",
            (batch_id, experiment_id),
        ).fetchone():
            return None
        experiment = conn.execute(
            """
            SELECT * FROM experiments
            WHERE id = ? AND batch_id = ?
              AND ((? IS NULL AND state IN (
                  'QUEUED', 'RETRY_WAIT', 'BATCHED', 'SIMULATING',
                  'POLLING', 'SIMULATE_UNKNOWN', 'PERMANENT_FAILURE'
              )) OR (state = 'CHILD_POLLING' AND child_simulation_id = ?))
              AND (state = 'PERMANENT_FAILURE' OR EXISTS (
                  SELECT 1 FROM simulation_queue WHERE experiment_id = experiments.id
              ))
            """,
            (experiment_id, batch_id, child_id, child_id),
        ).fetchone()
        outcome = "SUPERSEDED"
        if experiment is not None:
            conn.execute(
                """
                INSERT INTO simulation_failures(batch_id, experiment_id, run_id, error, response_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (batch_id, experiment_id, run_id, error, _json(response), now),
            )
            failures = conn.execute(
                "SELECT COUNT(*) FROM simulation_failures WHERE experiment_id = ?", (experiment_id,)
            ).fetchone()[0]
            retry = failures <= max_retries
            outcome = "RETRIED" if retry else "PERMANENT_FAILURE"
            conn.execute(
                """
                UPDATE experiments
                SET state = ?, batch_id = ?, child_simulation_id = ?,
                    not_before = ?, last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    "RETRY_WAIT" if retry else "PERMANENT_FAILURE",
                    None if retry else batch_id, None if retry else child_id,
                    not_before if retry else 0, error, now, experiment_id,
                ),
            )
            if retry:
                conn.execute(
                    "INSERT OR IGNORE INTO simulation_queue(experiment_id, run_id, enqueued_at) VALUES (?, ?, ?)",
                    (experiment_id, run_id, now),
                )
            else:
                conn.execute("DELETE FROM simulation_queue WHERE experiment_id = ?", (experiment_id,))
                self._event(
                    conn, run_id, "SIMULATION_RETRIES_EXHAUSTED", experiment_id=experiment_id,
                    batch_id=batch_id, status_code=_status_code(response),
                    payload={"error": error, "failures": failures, "max_retries": max_retries}, now=now,
                )
        conn.execute(
            """
            UPDATE simulation_items
            SET state = ?, last_error = ?, last_response_json = ?, claim_owner = NULL
            WHERE batch_id = ? AND ordinal = ?
              AND state NOT IN ('COMPLETE', 'RETRIED', 'SUPERSEDED')
            """,
            (outcome, error, _json(response), batch_id, ordinal),
        )
        return outcome

    def exhaust_simulation_retries(self, run_id: str, *, max_retries: int, now: float) -> None:
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            exhausted = conn.execute(
                """
                SELECT experiment.id, experiment.last_error, COUNT(*) AS failures
                FROM experiments experiment
                JOIN simulation_failures failure ON failure.experiment_id = experiment.id
                WHERE experiment.run_id = ? AND experiment.state = 'RETRY_WAIT'
                GROUP BY experiment.id HAVING COUNT(*) > ?
                """,
                (run_id, max_retries),
            ).fetchall()
            for experiment in exhausted:
                conn.execute(
                    "UPDATE experiments SET state = 'PERMANENT_FAILURE', updated_at = ? WHERE id = ?",
                    (now, experiment["id"]),
                )
                conn.execute("DELETE FROM simulation_queue WHERE experiment_id = ?", (experiment["id"],))
                self._event(
                    conn, run_id, "SIMULATION_RETRIES_EXHAUSTED", experiment_id=experiment["id"],
                    payload={"error": experiment["last_error"], "failures": experiment["failures"],
                             "max_retries": max_retries}, now=now,
                )

    def next_enrichment(self, run_id: str, *, now: float) -> ExperimentRecord | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT e.*, c.simulation_type
                FROM enrichment_queue q
                JOIN experiments e ON e.id = q.experiment_id
                JOIN candidates c ON c.id = e.candidate_id
                WHERE q.run_id = ? AND e.state IN ('SIM_DONE', 'ENRICH_PNL')
                  AND q.claim_owner IS NULL AND e.not_before <= ?
                ORDER BY CASE e.state WHEN 'ENRICH_PNL' THEN 0 ELSE 1 END,
                         e.updated_at, e.id
                LIMIT 1
                """,
                (run_id, now),
            ).fetchone()
        return _experiment_from_row(row) if row else None

    def claim_enrichment(
        self,
        run_id: str,
        *,
        owner: str,
        now: float,
    ) -> ExperimentRecord | None:
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT e.*, c.simulation_type
                FROM enrichment_queue q
                JOIN experiments e ON e.id = q.experiment_id
                JOIN candidates c ON c.id = e.candidate_id
                WHERE q.run_id = ? AND e.state IN ('SIM_DONE', 'ENRICH_PNL')
                  AND q.claim_owner IS NULL AND e.not_before <= ?
                ORDER BY CASE e.state WHEN 'ENRICH_PNL' THEN 0 ELSE 1 END,
                         e.updated_at, e.id
                LIMIT 1
                """,
                (run_id, now),
            ).fetchone()
            if row is not None:
                conn.execute(
                    "UPDATE enrichment_queue SET claim_owner = ? WHERE experiment_id = ?",
                    (owner, row["id"]),
                )
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
        if experiment.simulation_type == "REGION_AGNOSTIC":
            region_agnostic_child_ids(detail, alpha_id)
        metrics = _extract_metrics(detail)
        checks = detail.get("is", {}).get("checks", []) if isinstance(detail.get("is"), dict) else []
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO alphas(alpha_id, experiment_id, run_id, candidate_id, detail_json, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(alpha_id) DO UPDATE SET
                    detail_json = excluded.detail_json, fetched_at = excluded.fetched_at
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
            for ordinal, check in enumerate(checks if isinstance(checks, list) else []):
                if not isinstance(check, dict) or not check.get("name"):
                    continue
                conn.execute(
                    """
                    INSERT INTO alpha_checks(
                        alpha_id, ordinal, name, result, value_json, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        alpha_id,
                        ordinal,
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
            conn.execute(
                "UPDATE enrichment_queue SET claim_owner = NULL WHERE experiment_id = ?",
                (experiment.id,),
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

    def region_agnostic_children(
        self, experiment: ExperimentRecord, *, now: float
    ) -> list[dict[str, Any]]:
        with self.connect() as conn:
            parent = conn.execute(
                "SELECT detail_json FROM alphas WHERE alpha_id = ? AND experiment_id = ?",
                (experiment.alpha_id, experiment.id),
            ).fetchone()
            if parent is None:
                raise ValueError("Region-agnostic parent detail is missing")
            child_ids = region_agnostic_child_ids(json.loads(parent["detail_json"]), experiment.alpha_id)
            conn.executemany(
                "INSERT OR IGNORE INTO region_agnostic_children(parent_alpha_id, child_alpha_id, updated_at) "
                "VALUES (?, ?, ?)",
                [(experiment.alpha_id, child_id, now) for child_id in child_ids],
            )
            rows = conn.execute(
                "SELECT * FROM region_agnostic_children WHERE parent_alpha_id = ? ORDER BY child_alpha_id",
                (experiment.alpha_id,),
            ).fetchall()
            if {row["child_alpha_id"] for row in rows} != set(child_ids):
                raise ValueError("Region-agnostic parent child identities changed")
        return [dict(row) for row in rows]

    def save_region_agnostic_child_detail(
        self, experiment: ExperimentRecord, child_id: str, detail: dict[str, Any], *, now: float
    ) -> None:
        settings = detail.get("settings")
        region = settings.get("region") if isinstance(settings, dict) else None
        if (
            detail.get("id") != child_id or detail.get("type") != "RA_CHILD"
            or region not in {"USA", "EUR", "ASI", "GLB"}
        ):
            raise ValueError("Unexpected region-agnostic child identity, type or region")
        with self.connect() as conn:
            cursor = conn.execute(
                "UPDATE region_agnostic_children SET detail_json = ?, region = ?, state = 'ENRICH_PNL', "
                "updated_at = ? WHERE parent_alpha_id = ? AND child_alpha_id = ? AND state = 'SIM_DONE'",
                (_json(detail), region, now, experiment.alpha_id, child_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Region-agnostic child is not awaiting detail")
            self._release_region_agnostic_enrichment(conn, experiment, now=now)
            self._event(
                conn, experiment.run_id, "RA_CHILD_DETAIL_SAVED", experiment_id=experiment.id,
                status_code=200, payload={"parent": experiment.alpha_id, "child": child_id, "region": region},
                now=now,
            )

    def save_region_agnostic_child_pnl(
        self, experiment: ExperimentRecord, child_id: str,
        points: Iterable[tuple[str | None, float | None, float | None]],
        *, response: dict[str, Any], now: float,
    ) -> None:
        points = list(points)
        if not points or any(date_value is None for date_value, _, _ in points):
            raise ValueError("Region-agnostic child PnL must contain dated observations")
        if len({point[0] for point in points}) != len(points):
            raise ValueError("Region-agnostic child PnL contains duplicate dates")
        with self.connect() as conn:
            cursor = conn.execute(
                "UPDATE region_agnostic_children SET state = 'READY', pnl_response_json = ?, "
                "pnl_records = ?, updated_at = ? WHERE parent_alpha_id = ? AND child_alpha_id = ? "
                "AND state = 'ENRICH_PNL'",
                (_json(response), len(points), now, experiment.alpha_id, child_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Region-agnostic child is not awaiting PnL")
            conn.executemany(
                "INSERT INTO region_agnostic_child_pnl "
                "(parent_alpha_id, child_alpha_id, ordinal, date_value, cumulative, pnl_delta) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [(experiment.alpha_id, child_id, ordinal, *point) for ordinal, point in enumerate(points)],
            )
            self._release_region_agnostic_enrichment(conn, experiment, now=now)
            self._event(
                conn, experiment.run_id, "RA_CHILD_READY", experiment_id=experiment.id,
                status_code=200, payload={"parent": experiment.alpha_id, "child": child_id, "pnl_records": len(points)},
                now=now,
            )

    @staticmethod
    def _release_region_agnostic_enrichment(
        conn: sqlite3.Connection, experiment: ExperimentRecord, *, now: float
    ) -> None:
        conn.execute(
            "UPDATE experiments SET enrich_attempts = 0, not_before = ?, updated_at = ? WHERE id = ?",
            (now, now, experiment.id),
        )
        conn.execute("UPDATE enrichment_queue SET claim_owner = NULL WHERE experiment_id = ?", (experiment.id,))

    def finish_region_agnostic_parent(self, experiment: ExperimentRecord, *, now: float) -> None:
        children = self.region_agnostic_children(experiment, now=now)
        if any(child["state"] != "READY" or child["pnl_records"] <= 0 for child in children):
            raise ValueError("Cannot complete a region-agnostic parent before every child has PnL")
        if len({child["region"] for child in children}) != len(children):
            raise ValueError("Region-agnostic children must have distinct regions")
        with self.connect() as conn:
            conn.execute(
                "UPDATE experiments SET state = 'READY', enrich_attempts = 0, not_before = 0, updated_at = ? "
                "WHERE id = ?", (now, experiment.id),
            )
            conn.execute("DELETE FROM enrichment_queue WHERE experiment_id = ?", (experiment.id,))
            self._event(
                conn, experiment.run_id, "RA_PARENT_READY", experiment_id=experiment.id, status_code=200,
                payload={"parent": experiment.alpha_id, "children": [child["child_alpha_id"] for child in children],
                         "regions": [child["region"] for child in children], "parent_pnl": "NOT_APPLICABLE"},
                now=now,
            )

    def region_agnostic_results(self, run_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT children.*, alphas.experiment_id FROM region_agnostic_children children "
                "JOIN alphas ON alphas.alpha_id = children.parent_alpha_id WHERE alphas.run_id = ? "
                "ORDER BY alphas.experiment_id, children.region, children.child_alpha_id", (run_id,),
            ).fetchall()
            results = []
            for row in rows:
                result = dict(row)
                detail = result.pop("detail_json")
                result["detail"] = json.loads(detail) if detail else None
                response = result.pop("pnl_response_json")
                result["pnl_response"] = json.loads(response) if response else None
                result["pnl"] = [dict(point) for point in conn.execute(
                    "SELECT ordinal, date_value, cumulative, pnl_delta FROM region_agnostic_child_pnl "
                    "WHERE parent_alpha_id = ? AND child_alpha_id = ? ORDER BY ordinal",
                    (result["parent_alpha_id"], result["child_alpha_id"]),
                )]
                results.append(result)
        return results

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
            else:
                conn.execute(
                    "UPDATE enrichment_queue SET claim_owner = NULL WHERE experiment_id = ?",
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

    def simulation_not_before(self) -> float | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT MAX(CAST(value AS REAL)) FROM runtime_state "
                "WHERE key IN ('simulation_request_not_before', 'simulation_daily_not_before')"
            ).fetchone()
        return float(row[0]) if row[0] is not None else None

    def refresh_run_state(self, run_id: str, *, now: float) -> dict[str, Any]:
        with self.connect() as conn:
            run = conn.execute("SELECT state FROM runs WHERE id = ?", (run_id,)).fetchone()
            if not run:
                raise KeyError(f"Unknown run id: {run_id}")
            self._supersede_resolved_poll_attempts(conn, run_id, now=now)
            counts = {
                str(row["state"]): int(row["count"])
                for row in conn.execute(
                    "SELECT state, COUNT(*) AS count FROM experiments WHERE run_id = ? GROUP BY state",
                    (run_id,),
                )
            }
            queues = self._queue_counts(conn, run_id)
            active_attempts = int(
                conn.execute(
                    """
                    SELECT COUNT(*) FROM simulation_batches
                    WHERE run_id = ? AND state IN (
                        'CREATED', 'RETRY_WAIT', 'SIMULATING', 'POLLING', 'CHILD_POLLING'
                    )
                    """,
                    (run_id,),
                ).fetchone()[0]
            )
            total = sum(counts.values())
            terminal_count = sum(counts.get(state, 0) for state in EXPERIMENT_TERMINAL_STATES)
            if str(run["state"]) == "CANCELLED":
                state = "CANCELLED"
            elif total == terminal_count and active_attempts == 0:
                if counts.get("SIMULATE_UNKNOWN", 0):
                    state = "BLOCKED"
                elif counts.get("PERMANENT_FAILURE", 0):
                    state = "COMPLETED_WITH_ERRORS"
                else:
                    state = "COMPLETED"
            else:
                state = "RUNNING"
            terminal = state in {"COMPLETED", "COMPLETED_WITH_ERRORS", "BLOCKED", "CANCELLED"}
            conn.execute(
                """
                UPDATE runs
                SET state = ?, updated_at = ?,
                    finished_at = CASE WHEN ? THEN COALESCE(finished_at, ?) ELSE NULL END
                WHERE id = ?
                """,
                (state, now, 1 if terminal else 0, now, run_id),
            )
            if terminal:
                payload = {
                    "run_id": run_id,
                    "state": state,
                    "counts": counts,
                    "queues": queues,
                    "active_attempts": active_attempts,
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
            "simulation_not_before": self.simulation_not_before(),
            "daily_limit_not_before": self.runtime_float("simulation_daily_not_before"),
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

    def check_results(self, run_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    e.id AS experiment_id,
                    e.metadata_json,
                    a.alpha_id,
                    checks.ordinal,
                    checks.name,
                    checks.result,
                    checks.value_json,
                    checks.raw_json
                FROM alpha_checks checks
                JOIN alphas a ON a.alpha_id = checks.alpha_id
                JOIN experiments e ON e.id = a.experiment_id
                WHERE e.run_id = ? AND e.state = 'READY'
                ORDER BY e.id, checks.ordinal
                """,
                (run_id,),
            ).fetchall()
        results = []
        for row in rows:
            result = dict(row)
            result["metadata"] = json.loads(result.pop("metadata_json"))
            result["value"] = json.loads(result.pop("value_json"))
            result["raw"] = json.loads(result.pop("raw_json"))
            result["limit"] = (
                result["raw"].get("limit") if isinstance(result["raw"], dict) else None
            )
            results.append(result)
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
                    (SELECT COUNT(*) FROM simulation_failures failure
                     WHERE failure.experiment_id = e.id) AS simulation_failures,
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

    def pnl_paths(self, run_id: str) -> dict[str, Any]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    e.id AS experiment_id,
                    a.alpha_id,
                    p.ordinal,
                    p.date_value,
                    p.pnl_delta
                FROM experiments e
                JOIN alphas a ON a.experiment_id = e.id
                JOIN candidates c ON c.id = e.candidate_id
                LEFT JOIN alpha_pnl p ON p.alpha_id = a.alpha_id
                WHERE e.run_id = ? AND e.state = 'READY' AND c.simulation_type <> 'REGION_AGNOSTIC'
                ORDER BY e.id, p.ordinal
                """,
                (run_id,),
            )

            paths: list[dict[str, Any]] = []
            date_grids: dict[str, list[str | None]] = {}
            current: dict[str, Any] | None = None
            ordinals: list[int] = []
            dates: list[str | None] = []
            deltas: list[float | None] = []

            def finish_path() -> None:
                nonlocal current, ordinals, dates, deltas
                if current is None:
                    return
                grid_payload = _json(dates)
                grid_id = hashlib.sha256(grid_payload.encode("utf-8")).hexdigest()
                date_grids.setdefault(grid_id, dates)
                current["date_grid_id"] = grid_id
                current["pnl_deltas"] = deltas
                if ordinals and ordinals == list(range(ordinals[0], ordinals[0] + len(ordinals))):
                    current["ordinal_start"] = ordinals[0]
                    current["ordinal_step"] = 1
                elif ordinals:
                    current["ordinals"] = ordinals
                paths.append(current)
                current = None
                ordinals = []
                dates = []
                deltas = []

            for row in rows:
                alpha_id = str(row["alpha_id"])
                if current is None or current["alpha_id"] != alpha_id:
                    finish_path()
                    current = {
                        "experiment_id": str(row["experiment_id"]),
                        "alpha_id": alpha_id,
                        "source": "alpha_pnl",
                    }
                if row["ordinal"] is not None:
                    ordinals.append(int(row["ordinal"]))
                    dates.append(row["date_value"])
                    deltas.append(row["pnl_delta"])
            finish_path()

        return {
            "format_version": 1,
            "date_grids": date_grids,
            "paths": paths,
        }

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

    def _supersede_resolved_poll_attempts(
        self,
        conn: sqlite3.Connection,
        run_id: str,
        *,
        now: float,
    ) -> None:
        reason = "source_experiment_resolved_by_another_attempt"
        item_update = conn.execute(
            """
            UPDATE simulation_items
            SET state = 'SUPERSEDED',
                last_error = COALESCE(last_error, ?),
                claim_owner = NULL
            WHERE state IN ('BATCHED', 'POLLING')
              AND claim_owner IS NULL
              AND batch_id IN (
                  SELECT id
                  FROM simulation_batches
                  WHERE run_id = ?
                    AND state IN ('POLLING', 'CHILD_POLLING')
                    AND claim_owner IS NULL
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM simulation_queue q
                  WHERE q.experiment_id = simulation_items.experiment_id
              )
            """,
            (reason, run_id),
        )
        superseded_items = int(item_update.rowcount)
        if superseded_items == 0:
            return

        batch_update = conn.execute(
            """
            UPDATE simulation_batches
            SET state = CASE
                    WHEN NOT EXISTS (
                        SELECT 1 FROM simulation_items i
                        WHERE i.batch_id = simulation_batches.id
                          AND i.state <> 'SUPERSEDED'
                    ) THEN 'SUPERSEDED'
                    WHEN EXISTS (
                        SELECT 1 FROM simulation_items i
                        WHERE i.batch_id = simulation_batches.id
                          AND i.state = 'PERMANENT_FAILURE'
                    ) THEN 'PARTIAL_FAILURE'
                    WHEN EXISTS (
                        SELECT 1 FROM simulation_items i
                        WHERE i.batch_id = simulation_batches.id
                          AND i.state = 'RETRIED'
                    ) THEN 'RETRIED'
                    ELSE 'COMPLETE'
                END,
                last_error = COALESCE(last_error, ?),
                claim_owner = NULL,
                updated_at = ?
            WHERE run_id = ?
              AND state IN ('POLLING', 'CHILD_POLLING')
              AND claim_owner IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM simulation_items i
                  WHERE i.batch_id = simulation_batches.id
                    AND i.state IN ('BATCHED', 'POLLING')
              )
            """,
            (reason, now, run_id),
        )
        self._event(
            conn,
            run_id,
            "SIMULATION_ATTEMPTS_SUPERSEDED",
            payload={
                "reason": reason,
                "items": superseded_items,
                "batches": int(batch_update.rowcount),
            },
            now=now,
        )

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
        resolved = sum(counts.values()) - counts.get("SUPERSEDED", 0)
        if resolved == 0:
            state = "SUPERSEDED"
        elif counts.get("PERMANENT_FAILURE", 0):
            state = "PARTIAL_FAILURE"
        elif counts.get("RETRIED", 0):
            state = "RETRIED"
        else:
            state = "COMPLETE"
        conn.execute(
            """
            UPDATE simulation_batches
            SET state = ?, claim_owner = NULL, updated_at = ?
            WHERE id = ?
            """,
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


def _add_column_if_missing(
    conn: sqlite3.Connection,
    table: str,
    definition: str,
) -> None:
    column = definition.split(None, 1)[0]
    columns = {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def _migrate_alpha_checks_v6(conn: sqlite3.Connection) -> None:
    columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(alpha_checks)")
    }
    if "ordinal" in columns:
        return
    conn.execute("ALTER TABLE alpha_checks RENAME TO alpha_checks_v5")
    conn.execute(
        """
        CREATE TABLE alpha_checks (
            alpha_id TEXT NOT NULL REFERENCES alphas(alpha_id),
            ordinal INTEGER NOT NULL,
            name TEXT NOT NULL,
            result TEXT,
            value_json TEXT,
            raw_json TEXT NOT NULL,
            PRIMARY KEY(alpha_id, ordinal)
        )
        """
    )
    conn.execute(
        """
        INSERT INTO alpha_checks(
            alpha_id, ordinal, name, result, value_json, raw_json
        )
        SELECT
            alpha_id,
            ROW_NUMBER() OVER (PARTITION BY alpha_id ORDER BY name) - 1,
            name,
            result,
            value_json,
            raw_json
        FROM alpha_checks_v5
        """
    )
    conn.execute("DROP TABLE alpha_checks_v5")


def scheduling_profile(payload: dict[str, Any]) -> tuple[str, int]:
    simulation_type = str(payload["type"]).upper()
    settings = payload["settings"]
    language = str(settings.get("language") or "FASTEXPR").upper()
    region = str(settings.get("region") or "").upper()
    instrument_type = str(settings.get("instrumentType") or "").upper()
    if simulation_type in {"SUPER", "REGION_AGNOSTIC"}:
        batch_limit = 1
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
        simulation_type=str(row["simulation_type"]),
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
