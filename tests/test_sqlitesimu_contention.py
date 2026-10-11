from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wqb_cli.sqlitesimu.db import SqliteStore, retry_database_lock
from wqb_cli.sqlitesimu.manifest import parse_manifest
from wqb_cli.sqlitesimu.runtime import SqliteSimuRuntime
from wqb_cli.tests.test_sqlitesimu import SETTINGS, SuccessfulGateway


class ContentionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = SqliteStore(Path(self.temp.name) / "queue.sqlite3")
        self.store.initialize()
        self.run = self.store.enqueue(parse_manifest([
            {"expression": "rank(close)", "settings": SETTINGS},
        ]), now=1000)

    def test_real_writer_lock_retries_after_release(self):
        blocker = sqlite3.connect(self.store.path)
        self.addCleanup(blocker.close)
        blocker.execute("BEGIN IMMEDIATE")
        native_connect = sqlite3.connect

        class FastConnection(sqlite3.Connection):
            def execute(self, sql, parameters=()):
                if sql == "PRAGMA busy_timeout = 30000":
                    sql = "PRAGMA busy_timeout = 1"
                return super().execute(sql, parameters)

        def connect(*args, **kwargs):
            return native_connect(*args, **kwargs, factory=FastConnection)

        with patch("wqb_cli.sqlitesimu.db.sqlite3.connect", side_effect=connect), patch(
            "wqb_cli.sqlitesimu.db.time.sleep", side_effect=lambda delay: blocker.rollback()
        ) as sleeper:
            self.store.mark_run_running(self.run.run_id, now=1001)
        self.assertEqual(sleeper.call_count, 1)
        self.assertEqual(self.store.run_summary(self.run.run_id)["state"], "RUNNING")

    def test_accepted_post_is_not_repeated_when_transaction_rolls_back(self):
        batch = self.store.create_next_batch(self.run.run_id, now=1001)
        gateway = SuccessfulGateway()
        original_event = self.store._event
        failed = False

        def event(*args, **kwargs):
            nonlocal failed
            original_event(*args, **kwargs)
            if args[2] == "SIMULATION_ACCEPTED" and not failed:
                failed = True
                raise sqlite3.OperationalError("database is locked")

        with patch.object(self.store, "_event", side_effect=event), patch(
            "wqb_cli.sqlitesimu.db.time.sleep"
        ):
            SqliteSimuRuntime(self.store, gateway, clock=lambda: 1002)._simulate(batch, now=1001)
        self.assertTrue(failed)
        self.assertEqual(len(gateway.calls), 1)
        with self.store.connect() as conn:
            row = conn.execute("SELECT state, parent_simulation_id FROM simulation_batches").fetchone()
            self.assertEqual(tuple(row), ("POLLING", "parent-1"))
            self.assertEqual(conn.execute(
                "SELECT COUNT(*) FROM api_events WHERE event_type='SIMULATION_ACCEPTED'"
            ).fetchone()[0], 1)

    def test_retries_are_bounded_and_other_errors_propagate(self):
        for message, attempts in [("database is locked", 4), ("no such table: missing", 1)]:
            calls = []

            @retry_database_lock
            def operation():
                calls.append(1)
                raise sqlite3.OperationalError(message)

            with patch("wqb_cli.sqlitesimu.db.time.sleep"), self.assertRaises(sqlite3.OperationalError):
                operation()
            self.assertEqual(len(calls), attempts)

    def test_existing_database_receives_lookup_index(self):
        with self.store.connect() as conn:
            conn.execute("DROP INDEX idx_items_experiment_id")
        self.store.initialize()
        with self.store.connect() as conn:
            plan = conn.execute(
                "EXPLAIN QUERY PLAN SELECT 1 FROM simulation_items WHERE experiment_id=? LIMIT 1",
                ("example",),
            ).fetchall()
        self.assertIn("idx_items_experiment_id", str([tuple(row) for row in plan]))
