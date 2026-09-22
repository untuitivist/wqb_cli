from __future__ import annotations

import argparse
import tempfile
import unittest
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import random
from typing import Any
from unittest.mock import patch
from zoneinfo import ZoneInfo

from wqb_cli.core.client import is_wqb_daily_simulation_limit
from wqb_cli.sqlitesimu.models import RuntimePolicy
from wqb_cli.sqlitesimu.plugin import _add_runtime_arguments, _run
from wqb_cli.sqlitesimu.db import SCHEMA_VERSION, SqliteStore
from wqb_cli.sqlitesimu.manifest import parse_manifest
from wqb_cli.sqlitesimu.runtime import SqliteSimuRuntime, _next_eastern_midnight
from wqb_cli.tests.test_sqlitesimu import (
    SETTINGS, FakeClock, FixedResponseGateway, SuccessfulGateway, envelope,
    initialized_store, sequential_policy,
)


class FailingCandidateGateway(SuccessfulGateway):
    def __init__(self) -> None:
        super().__init__()
        self.posts: list[dict[str, Any]] = []
        self.throttles = 3

    def call(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if method == "POST":
            if self.throttles:
                self.throttles -= 1
                return envelope(429, retry_after="2")
            self.posts.append(kwargs["json_body"])
            return envelope(201, location=f"https://example.test/simulations/{len(self.posts)}")
        if path == "/simulations/{simulation_id}":
            payload = self.posts[int(kwargs["path_vars"]["simulation_id"]) - 1]
            if payload["regular"] == "bad":
                return envelope(200, {"status": "ERROR", "message": "invalid dimension"})
            return envelope(200, {"status": "COMPLETE", "alpha": "good-alpha"})
        return super().call(method, path, **kwargs)


class SchedulingTests(unittest.TestCase):
    def test_cli_does_not_resend_accepted_work_without_an_explicit_opt_in(self) -> None:
        self.assertIsNone(RuntimePolicy().resend_interval_seconds)
        for arguments, interval in [([], None), (["--resend-seconds", "10"], 10),
                                    (["--resend-seconds", "10", "--no-resend"], None)]:
            with self.subTest(arguments=arguments):
                parser = argparse.ArgumentParser()
                _add_runtime_arguments(parser)
                with patch("wqb_cli.sqlitesimu.plugin.WqbApiGateway"), \
                     patch("wqb_cli.sqlitesimu.plugin.SqliteSimuRuntime") as runtime:
                    _run(None, None, "run-test", parser.parse_args(arguments))
                    self.assertEqual(runtime.call_args.kwargs["policy"].resend_interval_seconds, interval)
                    runtime.return_value.run.assert_called_once_with("run-test", max_runtime_seconds=None)

    def test_groups_are_sampled_independently_of_queue_size_and_priority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = initialized_store(directory)
            run = store.enqueue(parse_manifest([
                {"expression": f"close + {index}", "settings": SETTINGS, "priority": 1000 - index}
                for index in range(60)
            ] + [{"expression": "rare", "settings": {**SETTINGS, "region": "IND"}, "priority": -1000}]), now=1000)
            generator = random.Random(42)
            original_connect = store.connect

            @contextmanager
            def sampled_connection():
                with original_connect() as connection:
                    connection.create_function("random", 0, lambda: generator.randrange(-(2 ** 63), 2 ** 63))
                    try:
                        yield connection
                    finally:
                        connection.rollback()

            regions = Counter()
            expressions = set()
            with patch.object(store, "connect", sampled_connection):
                for _ in range(128):
                    batch = store.create_next_batch(run.run_id, now=1000, resend_interval_seconds=None)
                    assert batch is not None
                    payloads = batch.payload if isinstance(batch.payload, list) else [batch.payload]
                    region = payloads[0]["settings"]["region"]
                    regions[region] += 1
                    self.assertEqual(len(payloads), 10 if region == "USA" else 1)
                    expressions.update(payload["regular"] for payload in payloads)
            self.assertGreater(regions["IND"], 40)
            self.assertLess(regions["IND"], 88)
            self.assertEqual(len(expressions), 61)
            self.assertEqual(store.run_summary(run.run_id)["counts"], {"QUEUED": 61})

    def test_random_batches_fill_type_limits_without_mixing_groups_or_repeating_accepted_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = initialized_store(directory)
            candidates = []
            for region, delay, count in [("USA", 0, 23), ("USA", 1, 13), ("GLB", 1, 21)]:
                for index in range(count):
                    candidates.append({"type": "REGULAR", "regular": f"{region}_{delay}_{index}",
                                       "settings": {**SETTINGS, "region": region, "delay": delay,
                                                    "universe": "TOP3000" if index % 2 else "TOP1000",
                                                    "decay": index % 3}})
            candidates += [
                {"type": "SUPER", "selection": "(own)", "combo": f"combo_{index}", "settings": SETTINGS}
                for index in range(3)
            ]
            candidates += [
                {"type": "REGION_AGNOSTIC", "regular": f"all_{index}",
                 "settings": {**SETTINGS, "region": "ALL", "universe": "LARGE"}}
                for index in range(3)
            ]
            run = store.enqueue(parse_manifest(candidates), now=1000)
            remaining = Counter((item["type"], item["settings"]["region"], item["settings"]["delay"])
                                for item in candidates)
            seen = set()
            while batch := store.create_next_batch(run.run_id, now=1000):
                payloads = batch.payload if isinstance(batch.payload, list) else [batch.payload]
                group = (payloads[0]["type"], payloads[0]["settings"]["region"], payloads[0]["settings"]["delay"])
                limit = 10 if group[0] == "REGULAR" else 1
                self.assertEqual(len(payloads), min(limit, remaining[group]))
                self.assertEqual({(item["type"], item["settings"]["region"], item["settings"]["delay"])
                                  for item in payloads}, {group})
                for item in payloads:
                    expression = item.get("regular", item.get("combo"))
                    self.assertNotIn(expression, seen)
                    seen.add(expression)
                remaining[group] -= len(payloads)
                store.mark_simulate_started(batch.id, now=1000)
                store.accept_simulation(batch.id, location=f"https://example.test/simulations/{batch.id}",
                                        parent_simulation_id=batch.id, response=envelope(201),
                                        not_before=2000, now=1000)
            self.assertEqual(len(seen), len(candidates))
            self.assertFalse(any(remaining.values()))
            self.assertEqual(store.run_summary(run.run_id)["counts"], {"POLLING": len(candidates)})
            self.assertIsNone(store.create_next_batch(run.run_id, now=10000))
            with store.connect() as connection:
                self.assertEqual(connection.execute(
                    "SELECT COUNT(*) FROM api_events WHERE event_type='BATCH_CREATED' "
                    "AND json_extract(payload_json,'$.selection')='random_group'").fetchone()[0], 14)

    def test_due_failure_retry_is_not_starved_by_a_large_unsent_queue(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = initialized_store(directory)
            run = store.enqueue(parse_manifest([
                {"expression": "bad", "settings": SETTINGS, "priority": 10},
                *[{"expression": f"close + {index}", "settings": {**SETTINGS, "region": "GLB"}}
                  for index in range(40)],
            ]), now=1000)
            with store.connect() as connection:
                connection.execute("UPDATE experiments SET not_before=1010 WHERE candidate_id IN "
                                   "(SELECT id FROM candidates WHERE json_extract(settings_json,'$.region')='GLB')")
            original = store.create_next_batch(run.run_id, now=1000)
            assert original is not None
            self.assertEqual(original.payload["regular"], "bad")
            store.retry_completed_batch(original.id, error="failed", response=envelope(200),
                                        not_before=1010, now=1001)
            retry = store.create_next_batch(run.run_id, now=1010, resend_interval_seconds=None)
            assert retry is not None
            self.assertEqual(retry.payload["regular"], "bad")

    def test_daily_quota_waits_until_eastern_midnight_across_restart_without_blocking_results(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = initialized_store(directory)
            observed = datetime(2026, 9, 21, 22, 30, tzinfo=timezone.utc).timestamp()
            reset = datetime(2026, 9, 22, 4, 0, tzinfo=timezone.utc).timestamp()
            run = store.enqueue(parse_manifest([
                {"expression": "close", "settings": SETTINGS, "priority": 10},
                {"expression": "volume", "settings": {**SETTINGS, "region": "GLB"}},
            ]), now=observed)
            accepted = store.create_next_batch(run.run_id, now=observed)
            assert accepted is not None
            store.mark_simulate_started(accepted.id, now=observed)
            store.accept_simulation(accepted.id, location="https://example.test/simulations/accepted",
                                    parent_simulation_id="accepted", response=envelope(201),
                                    not_before=observed, now=observed)
            quota_batch = store.create_next_batch(run.run_id, now=observed, resend_interval_seconds=None)
            assert quota_batch is not None
            runtime = SqliteSimuRuntime(
                store, FixedResponseGateway(envelope(429, {"detail": "DAILY_SIMULATION_LIMIT_EXCEEDED"}, retry_after="10")),
                clock=lambda: observed,
            )
            with self.assertLogs("wqb_cli.sqlitesimu.runtime", level="WARNING"):
                runtime._simulate(quota_batch, now=observed)
            store = SqliteStore(store.path)
            store.initialize()
            store.set_runtime_float("simulation_request_not_before", observed + 10, now=observed)
            self.assertEqual(store.run_summary(run.run_id)["daily_limit_not_before"], reset)
            self.assertIsNone(store.next_simulate_batch(run.run_id, now=reset - 1))
            self.assertIsNone(store.create_next_batch(run.run_id, now=reset - 1))
            self.assertEqual(store.next_poll_batch(run.run_id, now=observed + 1).id, accepted.id)
            self.assertEqual(store.next_simulate_batch(run.run_id, now=reset).id, quota_batch.id)
            runtime = SqliteSimuRuntime(store, FixedResponseGateway(envelope(
                201, location="https://example.test/simulations/resumed")), clock=lambda: reset)
            self.assertTrue(runtime._step_simulation(run.run_id, now=reset))
            self.assertEqual(store.run_summary(run.run_id)["counts"], {"POLLING": 2})
            with store.connect() as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM simulation_failures").fetchone()[0], 0)

    def test_eastern_midnight_handles_summer_winter_and_both_dst_transitions(self) -> None:
        eastern = ZoneInfo("America/New_York")
        for month, day, expected_hours, expected_utc_hour in (
            (1, 15, 24, 5), (7, 15, 24, 4), (3, 8, 23, 4), (11, 1, 25, 5),
        ):
            with self.subTest(month=month, day=day):
                start = datetime(2026, month, day, tzinfo=eastern).timestamp()
                deadline = _next_eastern_midnight(start)
                self.assertEqual(deadline - start, expected_hours * 3600)
                self.assertEqual(datetime.fromtimestamp(deadline, timezone.utc).hour, expected_utc_hour)

    def test_concurrency_and_generic_rate_limits_are_not_daily_quotas(self) -> None:
        for detail in ("CONCURRENT_SIMULATION_LIMIT_EXCEEDED", "SIMULATION_LIMIT_EXCEEDED",
                       "API rate limit exceeded", "invalid expression"):
            self.assertFalse(is_wqb_daily_simulation_limit(429, {"detail": detail}))
        self.assertTrue(is_wqb_daily_simulation_limit(429, {"detail": "DAILY_SIMULATION_LIMIT_EXCEEDED"}))
        self.assertTrue(is_wqb_daily_simulation_limit(429, {"message": "Daily simulation limit reached. Please try tomorrow (EST time zone)."}))
        self.assertFalse(is_wqb_daily_simulation_limit(200, {"detail": "DAILY_SIMULATION_LIMIT_EXCEEDED"}))

    def test_failed_candidate_retries_once_and_later_work_finishes_despite_throttling(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = initialized_store(directory)
            run = store.enqueue(parse_manifest([
                {"expression": "bad", "settings": SETTINGS, "priority": 10},
                {"expression": "good", "settings": {**SETTINGS, "region": "GLB"}},
            ]), now=1000)
            gateway = FailingCandidateGateway()
            clock = FakeClock()
            runtime = SqliteSimuRuntime(store, gateway, clock=clock, sleeper=clock.sleep,
                                       policy=sequential_policy(resend_interval_seconds=31536000))
            summary = runtime.run(run.run_id, max_runtime_seconds=200)
            self.assertEqual(summary["state"], "COMPLETED_WITH_ERRORS")
            self.assertEqual(summary["counts"], {"PERMANENT_FAILURE": 1, "READY": 1})
            self.assertEqual(Counter(payload["regular"] for payload in gateway.posts), {"bad": 2, "good": 1})
            self.assertEqual(summary["queues"], {"simulation": 0, "enrichment": 0})
            failures = [record for record in store.experiment_results(run.run_id) if record["state"] == "PERMANENT_FAILURE"]
            self.assertEqual(failures[0]["simulation_failures"], 2)
            self.assertEqual(failures[0]["last_error"], "invalid dimension")

    def test_retry_budget_survives_restart_and_duplicate_failure_notifications(self) -> None:
        for resend in (None, 31536000):
            with self.subTest(resend=resend), tempfile.TemporaryDirectory() as directory:
                store = initialized_store(directory)
                run = store.enqueue(parse_manifest([{"expression": "bad", "settings": SETTINGS}]), now=1000)
                original = store.create_next_batch(run.run_id, now=1000)
                assert original is not None
                failure = envelope(200, {"status": "ERROR"})
                store.retry_completed_batch(original.id, error="first", response=failure, not_before=1010, now=1001)
                store.retry_completed_batch(original.id, error="duplicate", response=failure, not_before=9999, now=1002)
                store = SqliteStore(store.path)
                store.initialize()
                self.assertIsNone(store.create_next_batch(run.run_id, now=1009, resend_interval_seconds=resend))
                retry = store.create_next_batch(run.run_id, now=1010, resend_interval_seconds=resend)
                assert retry is not None
                store.retry_completed_batch(original.id, error="stale", response=failure, not_before=9999, now=1011)
                store.retry_completed_batch(retry.id, error="second", response=failure, not_before=1020, now=1012)
                store.retry_completed_batch(retry.id, error="duplicate", response=failure, not_before=9999, now=1013)
                self.assertIsNone(store.create_next_batch(run.run_id, now=2000))
                record = store.experiment_results(run.run_id)[0]
                self.assertEqual((record["state"], record["simulation_failures"], record["last_error"]),
                                 ("PERMANENT_FAILURE", 2, "second"))

    def test_child_and_parent_failures_share_one_retry_budget(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = initialized_store(directory)
            run = store.enqueue(parse_manifest([
                {"expression": "close", "settings": SETTINGS},
                {"expression": "volume", "settings": SETTINGS},
            ]), now=1000)
            batch = store.create_next_batch(run.run_id, now=1000)
            assert batch is not None
            store.complete_parent(batch.id, alpha_id=None, child_ids=["bad-child", "pending-child"],
                                  parent_status="COMPLETE", response=envelope(200), now=1001)
            child = store.next_child_item(run.run_id, now=1001)
            assert child is not None
            failure = envelope(200, {"status": "FAIL"})
            runtime = SqliteSimuRuntime(store, FixedResponseGateway(failure), clock=lambda: 1002)
            runtime._poll_child(child, now=1002)
            runtime._poll_child(child, now=1002)
            retry = store.create_next_batch(run.run_id, now=1012, resend_interval_seconds=None)
            assert retry is not None
            store.retry_completed_batch(retry.id, error="second", response=failure, not_before=1020, now=1013)
            self.assertEqual(store.run_summary(run.run_id)["counts"], {"CHILD_POLLING": 1, "PERMANENT_FAILURE": 1})
            with store.connect() as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM simulation_failures").fetchone()[0], 2)

    def test_glb_batches_continue_while_previous_results_are_pending_and_retry_429(self) -> None:
        class SenderGateway:
            def __init__(self) -> None:
                self.payloads: list[Any] = []

            def call(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
                self.assert_post(method)
                self.payloads.append(kwargs["json_body"])
                if len(self.payloads) == 2:
                    return envelope(429, retry_after="7")
                return envelope(201, location=f"https://example.test/simulations/{len(self.payloads)}")

            @staticmethod
            def assert_post(method: str) -> None:
                if method != "POST":
                    raise AssertionError("Sender must not wait for result collection")

        with tempfile.TemporaryDirectory() as directory:
            store = initialized_store(directory)
            run = store.enqueue(parse_manifest([
                {"expression": f"close + {index}", "settings": {**SETTINGS, "region": "GLB"}}
                for index in range(35)
            ]), now=1000)
            gateway = SenderGateway()
            clock = FakeClock()
            runtime = SqliteSimuRuntime(store, gateway, clock=clock,
                                       policy=sequential_policy(resend_interval_seconds=None))
            for index in range(4):
                self.assertTrue(runtime._step_simulation(run.run_id, now=clock()))
            self.assertFalse(runtime._step_simulation(run.run_id, now=clock()))
            clock.sleep(7)
            for index in range(5):
                self.assertTrue(runtime._step_simulation(run.run_id, now=clock()))
            self.assertEqual([len(payload) for payload in gateway.payloads], [10, 10, 10, 10, 5])
            self.assertEqual(gateway.payloads[1], gateway.payloads[2])
            self.assertEqual(store.run_summary(run.run_id)["counts"], {"POLLING": 35})
            with store.connect() as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM simulation_failures").fetchone()[0], 0)

    def test_schema_seven_migration_preserves_retry_history_and_refreshes_glb_batches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = initialized_store(directory)
            run = store.enqueue(parse_manifest([
                {"expression": "close", "settings": {**SETTINGS, "region": "GLB"}},
            ]), now=1000)
            for timestamp in (1000, 1010):
                batch = store.create_next_batch(run.run_id, now=timestamp)
                assert batch is not None
                store.retry_completed_batch(batch.id, error="legacy failure", response=envelope(200),
                                            not_before=timestamp + 1, now=timestamp, max_retries=10)
            with store.connect() as connection:
                connection.execute("DELETE FROM simulation_failures")
                connection.execute("UPDATE candidates SET batch_limit = 5, compatibility_key = 'old-glb'")
                connection.execute("PRAGMA user_version = 7")
            store.initialize()
            store.initialize()
            store.exhaust_simulation_retries(run.run_id, max_retries=1, now=1020)
            self.assertEqual(store.refresh_run_state(run.run_id, now=1020)["state"], "COMPLETED_WITH_ERRORS")
            with store.connect() as connection:
                self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], SCHEMA_VERSION)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM simulation_failures").fetchone()[0], 2)
                self.assertEqual(connection.execute("SELECT batch_limit FROM candidates").fetchone()[0], 10)

    def test_late_failure_cannot_overwrite_success_or_consume_its_budget(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = initialized_store(directory)
            run = store.enqueue(parse_manifest([{"expression": "close", "settings": SETTINGS}]), now=1000)
            batch = store.create_next_batch(run.run_id, now=1000)
            assert batch is not None
            store.complete_parent(batch.id, alpha_id="alpha", child_ids=[], parent_status="COMPLETE",
                                  response=envelope(200), now=1001)
            store.retry_completed_batch(batch.id, error="stale", response=envelope(200), not_before=1010, now=1002)
            self.assertEqual(store.run_summary(run.run_id)["counts"], {"SIM_DONE": 1})
            self.assertEqual(store.experiment_results(run.run_id)[0]["simulation_failures"], 0)


if __name__ == "__main__":
    unittest.main()
