from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from wqb_cli.cli import build_parser
from wqb_cli.commands.sim import _create_and_wait_simulation
from wqb_cli.core.client import WqbClient
from wqb_cli.core.registry import EndpointRegistry
from wqb_cli.core.simulation import validate_region_agnostic_payload
from wqb_cli.sqlitesimu.db import SCHEMA_VERSION, SqliteStore
from wqb_cli.sqlitesimu.gateway import ApiTransportError
from wqb_cli.sqlitesimu.manifest import parse_manifest
from wqb_cli.sqlitesimu.models import RuntimePolicy
from wqb_cli.sqlitesimu.runtime import SqliteSimuRuntime


SETTINGS = {"region": "ALL", "universe": "LARGE", "delay": 1, "language": "FASTEXPR", "instrumentType": "EQUITY"}


def candidate(expression="rank(close)"):
    return {"type": "REGION_AGNOSTIC", "settings": dict(SETTINGS), "regular": expression}


def envelope(status=200, body=None, **response):
    return {"ok": 200 <= status < 300, "response": {"status_code": status, "body": body, **response}}


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class Gateway:
    def __init__(self):
        self.calls = []
        self.simulations = {}
        self.parent_ids = set()
        self.throttle_child = None

    def call(self, method, path, *, path_vars=None, json_body=None, **kwargs):
        identifier = next(iter((path_vars or {}).values()), None)
        self.calls.append((method, path, identifier, json_body))
        if method == "POST":
            simulation_id = f"simulation-{len(self.simulations)}"
            self.simulations[simulation_id] = json_body
            return envelope(201, location=f"https://api.worldquantbrain.com/simulations/{simulation_id}")
        if path == "/simulations/{simulation_id}":
            payload = self.simulations[identifier]
            if isinstance(payload, list):
                child_ids = [f"{identifier}-{index}" for index in range(len(payload))]
                self.simulations.update(zip(child_ids, payload))
                return envelope(body={"status": "COMPLETE", "children": child_ids})
            if payload["regular"] == "invalid()":
                return envelope(body={"status": "ERROR", "message": "Unknown operator invalid"})
            alpha_id = "alpha-" + identifier
            if payload["type"] == "REGION_AGNOSTIC":
                self.parent_ids.add(alpha_id)
            return envelope(body={"status": "WARNING", "alpha": alpha_id})
        if path == "/alphas/{alpha_id}":
            if identifier in self.parent_ids:
                return envelope(body={"id": identifier, "type": "RA_PARENT", "settings": SETTINGS,
                                      "children": [identifier + "-USA", identifier + "-EUR"]})
            region = identifier.rsplit("-", 1)[-1]
            return envelope(body={"id": identifier, "type": "RA_CHILD" if region in {"USA", "EUR"} else "REGULAR",
                                  "settings": {"region": region}, "is": {"sharpe": 1.2, "checks": []}})
        if path.endswith("/recordsets/pnl"):
            assert identifier not in self.parent_ids, "RA parents do not have PnL"
            if self.throttle_child == identifier:
                self.throttle_child = None
                return envelope(429, retry_after="2")
            return envelope(body={"records": [["2026-01-01", 10.0], ["2026-01-02", 12.0]]})
        raise AssertionError((method, path, identifier))


class RegionAgnosticTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = SqliteStore(Path(self.directory.name) / "runs.sqlite3")
        self.store.initialize()
        self.clock = Clock()
        self.gateway = Gateway()
        self.policy = RuntimePolicy(concurrent=False, default_retry_seconds=1, resend_interval_seconds=None)

    def enqueue(self, candidates):
        return self.store.enqueue(parse_manifest({"candidates": candidates}), now=self.clock()).run_id

    def runtime(self):
        return SqliteSimuRuntime(self.store, self.gateway, policy=self.policy, clock=self.clock, sleeper=self.clock.sleep)

    def test_all_validation_and_raw_client_batch_rejection(self):
        validate_region_agnostic_payload(candidate())
        for payload in ([candidate()], {**candidate(), "type": "REGULAR"},
                        {**candidate(), "settings": {**SETTINGS, "delay": 0}},
                        {**candidate(), "settings": {**SETTINGS, "universe": "TOP3000"}}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                validate_region_agnostic_payload(payload)
        registry = EndpointRegistry.load()
        client = WqbClient(registry, None)
        with self.assertRaisesRegex(ValueError, "batch"):
            client.prepare(registry.get("/simulations"), "POST", json_body=[candidate()])
        self.assertEqual(build_parser().parse_args(["simu", "options"]).sim_command, "options")

    def test_mixed_queue_keeps_all_single_and_enriches_every_region(self):
        regular = {"type": "REGULAR", "settings": {**SETTINGS, "region": "USA", "universe": "TOP3000"}}
        run_id = self.enqueue([candidate(), candidate("rank(volume)"),
                               {**regular, "regular": "rank(close)"}, {**regular, "regular": "rank(volume)"}])
        summary = self.runtime().run(run_id)
        self.assertEqual(summary["counts"], {"READY": 4})
        posts = [call[3] for call in self.gateway.calls if call[0] == "POST"]
        self.assertEqual(len(posts), 3)
        self.assertEqual(len(self.store.pnl_paths(run_id)["paths"]), 2)
        self.assertEqual(sum(isinstance(payload, dict) and payload["type"] == "REGION_AGNOSTIC" for payload in posts), 2)
        results = self.store.region_agnostic_results(run_id)
        self.assertEqual(len(results), 4)
        self.assertTrue(all(row["state"] == "READY" and len(row["pnl"]) == 2 for row in results))
        with self.store.connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM alpha_pnl").fetchone()[0], 4)
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_child_backpressure_and_restart_preserve_completed_children(self):
        run_id = self.enqueue([candidate()])
        runtime = self.runtime()
        for _ in range(30):
            runtime._step(run_id, now=self.clock())
            self.clock.sleep(1)
            with self.store.connect() as connection:
                ready = connection.execute("SELECT COUNT(*) FROM region_agnostic_children WHERE state='READY'").fetchone()[0]
            if ready == 1:
                break
        self.assertEqual(ready, 1)
        parent_id = next(iter(self.gateway.parent_ids))
        self.gateway.throttle_child = parent_id + "-USA"
        self.store = SqliteStore(self.store.path)
        self.store.initialize()
        summary = self.runtime().run(run_id)
        self.assertEqual(summary["state"], "COMPLETED")
        self.assertEqual(sum(call[0] == "POST" for call in self.gateway.calls), 1)
        euro_pnl = [call for call in self.gateway.calls if call[1].endswith("/pnl") and call[2].endswith("EUR")]
        usa_pnl = [call for call in self.gateway.calls if call[1].endswith("/pnl") and call[2].endswith("USA")]
        self.assertEqual(len(euro_pnl), 1)
        self.assertEqual(len(usa_pnl), 2)

    def test_concurrent_all_children_complete_without_duplicate_pnl(self):
        run_id = self.enqueue([candidate(), candidate("rank(volume)")])
        runtime = SqliteSimuRuntime(self.store, self.gateway, policy=RuntimePolicy(
            concurrent=True, result_workers=2, enrichment_workers=2,
            default_retry_seconds=0.01, idle_sleep_seconds=0.01, resend_interval_seconds=None,
        ))
        summary = runtime.run(run_id, max_runtime_seconds=10)
        self.assertEqual(summary["counts"], {"READY": 2})
        self.assertEqual(sum(call[0] == "POST" for call in self.gateway.calls), 2)
        self.assertEqual(len(self.store.region_agnostic_results(run_id)), 4)

    def test_pending_pnl_200_retry_after_does_not_consume_failure_budget(self):
        run_id = self.enqueue([candidate()])
        original = self.gateway.call
        pending = {"remaining": 2}

        def call(method, path, **kwargs):
            if path.endswith("/recordsets/pnl") and pending["remaining"]:
                pending["remaining"] -= 1
                return envelope(body={"progress": 0.5}, retry_after="2")
            return original(method, path, **kwargs)

        self.gateway.call = call
        self.policy = RuntimePolicy(concurrent=False, max_attempts=1, resend_interval_seconds=None)
        self.assertEqual(self.runtime().run(run_id)["state"], "COMPLETED")

    def test_failed_and_unknown_all_do_not_block_other_candidates_or_repeat(self):
        run_id = self.enqueue([candidate("invalid()"), candidate("unknown()"), candidate()])
        original = self.gateway.call

        def call(method, path, **kwargs):
            if method == "POST" and kwargs["json_body"]["regular"] == "unknown()":
                self.gateway.calls.append((method, path, None, kwargs["json_body"]))
                raise ApiTransportError("connection interrupted after POST")
            return original(method, path, **kwargs)

        self.gateway.call = call
        summary = self.runtime().run(run_id)
        self.assertEqual(summary["state"], "BLOCKED")
        self.assertEqual(summary["counts"], {"PERMANENT_FAILURE": 1, "READY": 1, "SIMULATE_UNKNOWN": 1})
        self.assertEqual(sum(call[0] == "POST" for call in self.gateway.calls), 3)

    def test_no_resend_preserves_remote_poll_and_retries_explicit_rejection(self):
        run_id = self.enqueue([candidate()])
        batch = self.store.create_next_batch(run_id, now=self.clock(), resend_interval_seconds=None)
        self.runtime()._simulate(batch, now=self.clock())
        self.assertIsNone(self.store.create_next_batch(run_id, now=self.clock() + 10000, resend_interval_seconds=None))
        other_id = self.enqueue([candidate("rank(volume)")])
        other = self.store.create_next_batch(other_id, now=self.clock(), resend_interval_seconds=None)
        self.store.mark_simulate_started(other.id, now=self.clock())
        self.store.retry_simulate(other.id, response=envelope(429), not_before=self.clock()+2, error="capacity", now=self.clock())
        self.assertIsNone(self.store.next_simulate_batch(other_id, now=self.clock()))
        self.assertEqual(self.store.next_simulate_batch(other_id, now=self.clock()+3).id, other.id)

    def test_v6_extension_migration_preserves_partial_child_results(self):
        run_id = self.enqueue([candidate()])
        self.runtime().run(run_id)
        before = self.store.region_agnostic_results(run_id)
        with self.store.connect() as connection:
            connection.execute("PRAGMA user_version=6")
            connection.execute("UPDATE candidates SET batch_limit=10")
        self.store.initialize()
        self.assertEqual(self.store.region_agnostic_results(run_id), before)
        with self.store.connect() as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], SCHEMA_VERSION)
            self.assertEqual(connection.execute("SELECT batch_limit FROM candidates").fetchone()[0], 1)

    def test_sim_create_collects_ra_children_without_simulation_child_polls(self):
        registry = EndpointRegistry.load()
        gateway = self.gateway

        class Client:
            def prepare(self, endpoint, method, *, path_vars=None):
                return SimpleNamespace(endpoint=endpoint.path, method=method, path_vars=path_vars, json_body=None)

            def call(self, prepared, **kwargs):
                return gateway.call(prepared.method, prepared.endpoint, path_vars=prepared.path_vars, json_body=prepared.json_body)

        result = _create_and_wait_simulation(Client(), registry,
            SimpleNamespace(endpoint="/simulations", method="POST", path_vars=None, json_body=candidate()), 60)
        self.assertTrue(result["ok"])
        self.assertEqual({child["region"] for child in result["region_agnostic"]["children"]}, {"USA", "EUR"})
        self.assertEqual(sum(call[1] == "/simulations/{simulation_id}" for call in gateway.calls), 1)


if __name__ == "__main__":
    unittest.main()
