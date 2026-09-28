from __future__ import annotations

import tempfile
import unittest

from test_sqlitesimu import SETTINGS, FakeClock, ReauthGateway, envelope, initialized_store
from wqb_cli.sqlitesimu.manifest import parse_manifest
from wqb_cli.sqlitesimu.runtime import SqliteSimuRuntime


class RecoveryGateway:
    def __init__(self, response, cancellation=None):
        self.response = response
        self.cancellation = cancellation or envelope(204)
        self.methods = []

    def call(self, method, path, **kwargs):
        self.methods.append(method)
        return self.cancellation if method == "DELETE" else self.response


class SimulationRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = initialized_store(self.directory.name)
        self.clock = FakeClock()
        self.run = self.store.enqueue(parse_manifest([
            {"expression": "rank(close)", "settings": SETTINGS},
        ]), now=0)
        self.batch = self.accept_batch()

    def accept_batch(self):
        batch = self.store.create_next_batch(self.run.run_id, now=self.clock())
        self.store.mark_simulate_started(batch.id, now=self.clock())
        self.store.accept_simulation(
            batch.id, location="https://api.worldquantbrain.com/simulations/remote",
            parent_simulation_id="remote", response=envelope(201),
            not_before=self.clock(), now=self.clock(),
        )
        return self.store.next_poll_batch(self.run.run_id, now=self.clock())

    def poll(self, gateway):
        runtime = SqliteSimuRuntime(self.store, gateway, clock=self.clock, sleeper=self.clock.sleep)
        runtime._poll_parent(self.batch, now=self.clock())

    def experiment_state(self):
        with self.store.connect() as conn:
            return conn.execute("SELECT state FROM experiments").fetchone()[0]

    def test_timeout_counts_from_acceptance_and_cancels_then_retries(self):
        gateway = RecoveryGateway(envelope(200, {"status": "PENDING"}))
        self.clock.value = 2799
        self.poll(gateway)
        self.assertEqual(gateway.methods, ["GET"])
        self.clock.value = 2800
        self.poll(gateway)
        self.assertEqual(gateway.methods, ["GET", "GET", "DELETE"])
        self.assertEqual(self.experiment_state(), "RETRY_WAIT")

    def test_complete_result_wins_over_timeout(self):
        self.clock.value = 5000
        gateway = RecoveryGateway(envelope(200, {"status": "COMPLETE", "alpha": "alpha-1"}))
        self.poll(gateway)
        self.assertEqual(gateway.methods, ["GET"])
        self.assertEqual(self.experiment_state(), "SIM_DONE")

    def test_unconfirmed_cancel_never_requeues(self):
        self.clock.value = 5000
        for status in (202, 404, 429, 500):
            with self.subTest(status=status):
                self.poll(RecoveryGateway(envelope(200, {"status": "PENDING"}), envelope(status)))
                self.assertEqual(self.experiment_state(), "POLLING")

    def test_missing_retry_budget_persists_and_repeated_loss_is_terminal(self):
        gateway = RecoveryGateway(envelope(404))
        for attempt in range(3):
            self.poll(gateway)
            self.assertEqual(self.experiment_state(), "POLLING")
            self.store.initialize()
        self.poll(gateway)
        self.assertEqual(self.experiment_state(), "RETRY_WAIT")
        self.clock.sleep(11)
        self.batch = self.accept_batch()
        for attempt in range(4):
            self.poll(gateway)
        self.assertEqual(self.experiment_state(), "PERMANENT_FAILURE")
        self.assertNotIn("DELETE", gateway.methods)

    def test_valid_response_resets_missing_count(self):
        for attempt in range(3):
            self.poll(RecoveryGateway(envelope(404)))
        self.poll(RecoveryGateway(envelope(200, {"status": "PENDING"})))
        self.poll(RecoveryGateway(envelope(404)))
        self.assertEqual(self.experiment_state(), "POLLING")

    def test_child_timeout_uses_parent_acceptance(self):
        self.store.complete_parent(
            self.batch.id, alpha_id=None, child_ids=["child-1"], parent_status="COMPLETE",
            response=envelope(200), now=self.clock(),
        )
        child = self.store.next_child_item(self.run.run_id, now=self.clock())
        self.clock.value = 2800
        gateway = RecoveryGateway(envelope(200, {"status": "PENDING"}))
        runtime = SqliteSimuRuntime(self.store, gateway, clock=self.clock)
        runtime._poll_child(child, now=self.clock())
        self.assertEqual(gateway.methods, ["GET", "DELETE"])
        self.assertEqual(self.experiment_state(), "RETRY_WAIT")

    def test_migration_backfills_acceptance_from_event(self):
        with self.store.connect() as conn:
            conn.execute("UPDATE simulation_batches SET accepted_at = NULL")
            conn.execute("PRAGMA user_version = 8")
        self.store.initialize()
        with self.store.connect() as conn:
            self.assertEqual(conn.execute("SELECT accepted_at FROM simulation_batches").fetchone()[0], 1000)

    def test_delete_no_content_does_not_reauthenticate(self):
        gateway = ReauthGateway([envelope(204)])
        result = gateway.call("DELETE", "/simulations/{simulation_id}")
        self.assertEqual(result["response"]["status_code"], 204)
        self.assertEqual(gateway.auth_calls, 0)
