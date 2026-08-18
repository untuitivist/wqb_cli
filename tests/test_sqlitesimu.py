from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from wqb_cli.sqlitesimu.db import RunLeaseError, SqliteStore
from wqb_cli.sqlitesimu.gateway import WqbApiGateway
from wqb_cli.sqlitesimu.manifest import parse_manifest
from wqb_cli.sqlitesimu.models import RuntimePolicy
from wqb_cli.sqlitesimu.runtime import SqliteSimuRuntime, _retry_seconds, pnl_points


SETTINGS = {
    "instrumentType": "EQUITY",
    "region": "USA",
    "universe": "TOP3000",
    "delay": 1,
    "decay": 5,
    "neutralization": "SUBINDUSTRY",
    "truncation": 0.08,
    "pasteurization": "ON",
    "unitHandling": "VERIFY",
    "nanHandling": "OFF",
    "language": "FASTEXPR",
    "visualization": False,
}


class FakeClock:
    def __init__(self) -> None:
        self.value = 1000.0

    def __call__(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += seconds


class SuccessfulGateway:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def call(
        self,
        method: str,
        path: str,
        *,
        path_vars: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "method": method,
                "path": path,
                "path_vars": path_vars,
                "params": params,
                "json_body": json_body,
            }
        )
        if method == "POST":
            return envelope(201, location="https://api.worldquantbrain.com/simulations/parent-1")
        identifier = (path_vars or {}).get("simulation_id")
        if path == "/simulations/{simulation_id}" and identifier == "parent-1":
            return envelope(200, {"status": "COMPLETE", "children": ["child-1", "child-2"]})
        if path == "/simulations/{simulation_id}" and identifier in {"child-1", "child-2"}:
            suffix = "1" if identifier == "child-1" else "2"
            return envelope(200, {"status": "COMPLETE", "alpha": f"alpha-{suffix}"})
        alpha_id = (path_vars or {}).get("alpha_id")
        if path == "/alphas/{alpha_id}":
            return envelope(200, alpha_detail(str(alpha_id)))
        if path == "/alphas/{alpha_id}/recordsets/pnl":
            return envelope(
                200,
                {
                    "records": [
                        ["2024-01-01", 10.0],
                        ["2024-01-02", None],
                        ["2024-01-03", 13.5],
                    ]
                },
            )
        raise AssertionError((method, path, path_vars))


class NoCallGateway:
    def __init__(self) -> None:
        self.calls = 0

    def call(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls += 1
        raise AssertionError("ambiguous simulations must never be posted again automatically")


class PendingParentGateway:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def call(
        self,
        method: str,
        path: str,
        *,
        path_vars: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "method": method,
                "path": path,
                "path_vars": path_vars,
                "params": params,
                "json_body": json_body,
            }
        )
        return envelope(200, {"status": "PENDING"}, retry_after="5")


class FixedResponseGateway:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.calls = 0

    def call(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls += 1
        return self.response


class ThrottledGateway(SuccessfulGateway):
    def __init__(self) -> None:
        super().__init__()
        self.throttled = False

    def call(
        self,
        method: str,
        path: str,
        *,
        path_vars: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> dict[str, Any]:
        if method == "POST" and not self.throttled:
            self.throttled = True
            self.calls.append(
                {
                    "method": method,
                    "path": path,
                    "path_vars": path_vars,
                    "params": params,
                    "json_body": json_body,
                }
            )
            return envelope(429, {"detail": "CONCURRENT_SIMULATION_LIMIT_EXCEEDED"}, retry_after="2")
        return super().call(
            method,
            path,
            path_vars=path_vars,
            params=params,
            json_body=json_body,
        )


class RetryableSimulationGateway(SuccessfulGateway):
    def __init__(self) -> None:
        super().__init__()
        self.simulate_calls = 0

    def call(
        self,
        method: str,
        path: str,
        *,
        path_vars: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> dict[str, Any]:
        if method == "POST":
            self.simulate_calls += 1
            if self.simulate_calls == 1:
                self.calls.append(
                    {
                        "method": method,
                        "path": path,
                        "path_vars": path_vars,
                        "params": params,
                        "json_body": json_body,
                    }
                )
                return envelope(
                    201,
                    location="https://api.worldquantbrain.com/simulations/failed-parent",
                )
        if (
            path == "/simulations/{simulation_id}"
            and (path_vars or {}).get("simulation_id") == "failed-parent"
        ):
            self.calls.append(
                {
                    "method": method,
                    "path": path,
                    "path_vars": path_vars,
                    "params": params,
                    "json_body": json_body,
                }
            )
            return envelope(200, {"status": "ERROR"})
        return super().call(
            method,
            path,
            path_vars=path_vars,
            params=params,
            json_body=json_body,
        )


class RecoveringSessionGateway(SuccessfulGateway):
    def __init__(self, trigger_status: int) -> None:
        super().__init__()
        self.trigger_status = trigger_status
        self.triggered: set[tuple[str, str, str | None]] = set()

    def call(
        self,
        method: str,
        path: str,
        *,
        path_vars: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> dict[str, Any]:
        identifier = next(iter((path_vars or {}).values()), None)
        key = (method, path, identifier)
        if key not in self.triggered:
            self.triggered.add(key)
            self.calls.append(
                {
                    "method": method,
                    "path": path,
                    "path_vars": path_vars,
                    "params": params,
                    "json_body": json_body,
                }
            )
            return envelope(
                self.trigger_status,
                retry_after="1" if self.trigger_status == 429 else None,
            )
        return super().call(
            method,
            path,
            path_vars=path_vars,
            params=params,
            json_body=json_body,
        )


class ReauthGateway(WqbApiGateway):
    def __init__(
        self,
        responses: list[dict[str, Any]],
        *,
        authentication_results: list[bool] | None = None,
    ) -> None:
        self.responses = list(responses)
        self.authentication_results = (
            list(authentication_results)
            if authentication_results is not None
            else None
        )
        self.auth_calls = 0
        self.call_auto_auth: list[bool] = []
        self.reauth_attempts = 5
        self.reauth_delay_seconds = 0
        self.sleeper = lambda _seconds: None
        self._reauth_lock = threading.Lock()
        self._reauth_generation = 0

    def _call_once(
        self,
        method: str,
        path: str,
        *,
        path_vars: dict[str, str] | None,
        params: dict[str, Any] | None,
        json_body: Any,
        auto_auth: bool = True,
    ) -> dict[str, Any]:
        self.call_auto_auth.append(auto_auth)
        return self.responses.pop(0)

    def _reauthenticate(self) -> dict[str, Any]:
        self.auth_calls += 1
        succeeded = (
            self.authentication_results.pop(0)
            if self.authentication_results is not None
            else True
        )
        return {
            "ok": succeeded,
            "reason": "authenticated" if succeeded else "authentication_rejected",
            "status_code": 201 if succeeded else 401,
        }


class ConcurrentReauthGateway(WqbApiGateway):
    def __init__(self) -> None:
        self.reauth_attempts = 5
        self.reauth_delay_seconds = 0
        self.sleeper = lambda _seconds: None
        self._reauth_lock = threading.Lock()
        self._reauth_generation = 0
        self.initial_calls = threading.Barrier(2)
        self.auth_calls = 0
        self.auth_calls_lock = threading.Lock()

    def _call_once(
        self,
        method: str,
        path: str,
        *,
        path_vars: dict[str, str] | None,
        params: dict[str, Any] | None,
        json_body: Any,
        auto_auth: bool = True,
    ) -> dict[str, Any]:
        if auto_auth:
            self.initial_calls.wait(timeout=1.0)
            return envelope(401)
        return envelope(200, {"status": "PENDING"})

    def _reauthenticate(self) -> dict[str, Any]:
        with self.auth_calls_lock:
            self.auth_calls += 1
        time.sleep(0.02)
        return {"ok": True, "reason": "authenticated", "status_code": 201}


class ConcurrentPipelineGateway:
    def __init__(self) -> None:
        self.poll_started = threading.Event()
        self.simulate_started = threading.Event()

    def call(
        self,
        method: str,
        path: str,
        *,
        path_vars: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> dict[str, Any]:
        if method == "POST":
            self.simulate_started.set()
            if not self.poll_started.wait(timeout=1.0):
                raise AssertionError("simulation sender did not overlap result polling")
            return envelope(429, retry_after="60")
        self.poll_started.set()
        if not self.simulate_started.wait(timeout=1.0):
            raise AssertionError("result polling did not overlap simulation sender")
        return envelope(200, {"status": "PENDING"}, retry_after="60")


def sequential_policy(**kwargs: Any) -> RuntimePolicy:
    return RuntimePolicy(concurrent=False, **kwargs)


class SqliteSimuTests(unittest.TestCase):
    def test_each_401_call_gets_reauthentication_and_replay(self) -> None:
        gateway = ReauthGateway(
            [
                envelope(401),
                envelope(200, {"status": "PENDING"}),
                envelope(401),
                envelope(200, {"status": "PENDING"}),
            ]
        )

        first = gateway.call("GET", "/simulations/{simulation_id}")
        second = gateway.call("GET", "/simulations/{simulation_id}")

        self.assertEqual(first["response"]["status_code"], 200)
        self.assertEqual(second["response"]["status_code"], 200)
        self.assertEqual(gateway.auth_calls, 2)

    def test_concurrent_sqlitesimu_calls_share_one_explicit_reauthentication(self) -> None:
        gateway = ConcurrentReauthGateway()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    lambda _: gateway.call("GET", "/simulations/{simulation_id}"),
                    range(2),
                )
            )

        self.assertEqual([result["response"]["status_code"] for result in results], [200, 200])
        self.assertEqual(gateway.auth_calls, 1)
        self.assertEqual(sum(bool(result["reauthentication"]["shared"]) for result in results), 1)

    def test_gateway_reauthenticates_on_all_wqb_session_statuses(self) -> None:
        for trigger in (204, 401, 429):
            with self.subTest(trigger=trigger):
                gateway = ReauthGateway([envelope(trigger), envelope(200)])

                result = gateway.call("GET", "/simulations/{simulation_id}")

                self.assertEqual(result["response"]["status_code"], 200)
                self.assertEqual(result["reauthentication"]["trigger_status"], trigger)
                self.assertFalse(result["reauthentication"]["exhausted"])
                self.assertEqual(gateway.call_auto_auth, [True, False])

    def test_gateway_replays_mutating_204_like_wqb_session(self) -> None:
        gateway = ReauthGateway([envelope(204), envelope(201)])

        result = gateway.call("POST", "/simulations", json_body={"type": "REGULAR"})

        self.assertEqual(result["response"]["status_code"], 201)
        self.assertEqual(gateway.auth_calls, 1)

    def test_gateway_can_recover_on_fifth_login(self) -> None:
        gateway = ReauthGateway(
            [envelope(401), envelope(200)],
            authentication_results=[False, False, False, False, True],
        )

        result = gateway.call("GET", "/simulations/{simulation_id}")

        self.assertEqual(result["response"]["status_code"], 200)
        self.assertEqual(gateway.auth_calls, 5)
        self.assertEqual(len(result["reauthentication"]["attempts"]), 5)

    def test_gateway_exhausts_five_logins_for_each_wqb_session_status(self) -> None:
        for trigger in (204, 401, 429):
            with self.subTest(trigger=trigger):
                gateway = ReauthGateway([envelope(trigger) for _ in range(6)])

                result = gateway.call("GET", "/simulations/{simulation_id}")

                self.assertFalse(result["ok"])
                self.assertEqual(result["response"]["status_code"], trigger)
                self.assertTrue(result["reauthentication"]["exhausted"])
                self.assertEqual(gateway.auth_calls, 5)
                self.assertEqual(gateway.call_auto_auth, [True, False, False, False, False, False])

    def test_gateway_does_not_recursively_authenticate_authentication_endpoint(self) -> None:
        gateway = ReauthGateway([envelope(401)])

        result = gateway.call("POST", "/authentication")

        self.assertEqual(result["response"]["status_code"], 401)
        self.assertEqual(gateway.auth_calls, 0)

    def test_manifest_normalizes_expressions_and_rejects_unknown_profiles(self) -> None:
        manifest = parse_manifest(
            {
                "run": {"name": "demo"},
                "candidates": [{"expression": "rank(close)", "settings": SETTINGS}],
            }
        )

        self.assertEqual(manifest.name, "demo")
        self.assertEqual(manifest.candidates[0].payload["regular"], "rank(close)")
        self.assertEqual(manifest.candidates[0].payload["settings"]["language"], "FASTEXPR")
        with self.assertRaisesRegex(ValueError, "Unsupported enrichment profile"):
            parse_manifest(
                {
                    "run": {"enrichment_profile": "everything"},
                    "candidates": [{"expression": "close", "settings": SETTINGS}],
                }
            )
        with self.assertRaisesRegex(ValueError, "metadata must be an object"):
            parse_manifest(
                {
                    "metadata": "not-an-object",
                    "candidates": [{"expression": "close", "settings": SETTINGS}],
                }
            )

    def test_enqueue_deduplicates_candidates_within_a_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            manifest = parse_manifest(
                [
                    {"expression": "rank(close)", "settings": SETTINGS},
                    {"expression": "rank(close)", "settings": SETTINGS},
                ]
            )

            result = store.enqueue(manifest, now=10.0)

            self.assertEqual(result.accepted, 1)
            self.assertEqual(result.duplicates, 1)
            self.assertEqual(result.reused_candidates, 1)

    def test_reused_candidate_keeps_per_experiment_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            first = store.enqueue(
                parse_manifest(
                    [
                        {
                            "expression": "rank(close)",
                            "settings": SETTINGS,
                            "metadata": {"generation": 1},
                        }
                    ]
                ),
                now=10.0,
            )
            second = store.enqueue(
                parse_manifest(
                    [
                        {
                            "expression": "rank(close)",
                            "settings": SETTINGS,
                            "metadata": {"generation": 2},
                        }
                    ]
                ),
                now=20.0,
            )

            with store.connect() as conn:
                rows = conn.execute(
                    "SELECT run_id, metadata_json FROM experiments ORDER BY created_at"
                ).fetchall()

            self.assertEqual([row["run_id"] for row in rows], [first.run_id, second.run_id])
            self.assertEqual(
                [json.loads(row["metadata_json"])["generation"] for row in rows],
                [1, 2],
            )

    def test_runtime_batches_tracks_and_enriches_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            manifest = parse_manifest(
                {
                    "run": {"name": "batch-demo"},
                    "candidates": [
                        {"expression": "rank(close)", "settings": SETTINGS},
                        {
                            "expression": "rank(volume)",
                            "settings": {**SETTINGS, "decay": 9},
                        },
                    ],
                }
            )
            enqueued = store.enqueue(manifest, now=1000.0)
            gateway = SuccessfulGateway()
            clock = FakeClock()
            runtime = SqliteSimuRuntime(
                store,
                gateway,
                policy=sequential_policy(default_retry_seconds=1.0, idle_sleep_seconds=1.0),
                clock=clock,
                sleeper=clock.sleep,
            )

            summary = runtime.run(enqueued.run_id)

            self.assertEqual(summary["state"], "COMPLETED")
            self.assertEqual(summary["counts"], {"READY": 2})
            self.assertEqual(summary["queues"], {"simulation": 0, "enrichment": 0})
            post = next(call for call in gateway.calls if call["method"] == "POST")
            self.assertIsInstance(post["json_body"], list)
            self.assertEqual(len(post["json_body"]), 2)
            enrichment_paths = [
                call["path"] for call in gateway.calls if call["path"].startswith("/alphas/")
            ]
            self.assertEqual(
                enrichment_paths,
                [
                    "/alphas/{alpha_id}",
                    "/alphas/{alpha_id}/recordsets/pnl",
                    "/alphas/{alpha_id}",
                    "/alphas/{alpha_id}/recordsets/pnl",
                ],
            )
            normalized = store.analysis_results(enqueued.run_id)
            experiments = store.experiment_results(enqueued.run_id)
            legacy = store.compatibility_results(enqueued.run_id)
            self.assertEqual(len(normalized), 2)
            self.assertEqual(len(experiments), 2)
            self.assertEqual(experiments[0]["state"], "READY")
            self.assertIn("regular", experiments[0]["payload"])
            self.assertEqual(len(legacy), 2)
            self.assertEqual(
                list(legacy[0]),
                [
                    "id",
                    "author",
                    "type",
                    "settings_region",
                    "settings_universe",
                    "settings_delay",
                    "settings_decay",
                    "settings_neutralization",
                    "settings_truncation",
                    "settings_maxTrade",
                    "regular_code",
                    "regular_operatorCount",
                    "dateCreated",
                    "is_pnl",
                    "is_longCount",
                    "is_shortCount",
                    "is_turnover",
                    "is_returns",
                    "is_drawdown",
                    "is_margin",
                    "is_sharpe",
                    "is_fitness",
                    "pyramids",
                    "PnL",
                ],
            )
            self.assertEqual(legacy[0]["settings_maxTrade"], "OFF")
            self.assertEqual(legacy[0]["pyramids"], "USA/D1, ATOM")
            self.assertEqual(legacy[0]["PnL"], "nan, 0.0, 3.5")

    def test_server_backpressure_replaces_local_slot_limits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            manifest = parse_manifest(
                [
                    {
                        "expression": f"rank(ts_delay(close, {index + 1}))",
                        "settings": SETTINGS,
                    }
                    for index in range(90)
                ]
            )
            enqueued = store.enqueue(manifest, now=1000.0)

            for index in range(9):
                batch = store.create_next_batch(enqueued.run_id, now=1000.0 + index)
                self.assertIsNotNone(batch)
                assert batch is not None
                store.mark_simulate_started(batch.id, now=1000.0 + index)
                store.accept_simulation(
                    batch.id,
                    location=f"https://api.worldquantbrain.com/simulations/parent-{index}",
                    parent_simulation_id=f"parent-{index}",
                    response=envelope(201),
                    not_before=2000.0,
                    now=1000.0 + index,
                )

            with store.connect() as conn:
                active = conn.execute(
                    "SELECT COUNT(*) FROM simulation_batches WHERE state = 'POLLING'"
                ).fetchone()[0]
            self.assertEqual(active, 9)

    def test_due_result_polling_precedes_new_batch_simulation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            manifest = parse_manifest(
                {
                    "candidates": [
                        {
                            "expression": "rank(close)",
                            "settings": SETTINGS,
                            "priority": 10,
                        },
                        {
                            "expression": "rank(volume)",
                            "settings": {**SETTINGS, "region": "CHN", "universe": "TOP2000U"},
                        },
                    ]
                }
            )
            enqueued = store.enqueue(manifest, now=1000.0)
            batch = store.create_next_batch(enqueued.run_id, now=1000.0)
            assert batch is not None
            store.mark_simulate_started(batch.id, now=1000.0)
            store.accept_simulation(
                batch.id,
                location="https://api.worldquantbrain.com/simulations/parent-due",
                parent_simulation_id="parent-due",
                response=envelope(201),
                not_before=1000.0,
                now=1000.0,
            )
            gateway = PendingParentGateway()
            runtime = SqliteSimuRuntime(store, gateway, clock=FakeClock())

            self.assertTrue(runtime._step(enqueued.run_id, now=1001.0))

            self.assertEqual(gateway.calls[0]["method"], "GET")
            with store.connect() as conn:
                batch_count = conn.execute("SELECT COUNT(*) FROM simulation_batches").fetchone()[0]
            self.assertEqual(batch_count, 1)

    def test_concurrent_claims_are_unique_and_recovered_on_restart(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            enqueued = store.enqueue(
                parse_manifest(
                    [
                        {"expression": f"rank(close + {index})", "settings": SETTINGS}
                        for index in range(8)
                    ]
                ),
                now=1000.0,
            )
            batch = store.create_next_batch(enqueued.run_id, now=1000.0)
            assert batch is not None
            store.mark_simulate_started(batch.id, now=1000.0)
            store.complete_parent(
                batch.id,
                alpha_id=None,
                child_ids=[f"child-{index}" for index in range(8)],
                parent_status="COMPLETE",
                response=envelope(200, {"status": "COMPLETE"}),
                now=1001.0,
            )

            with ThreadPoolExecutor(max_workers=8) as executor:
                items = list(
                    executor.map(
                        lambda index: store.claim_child_item(
                            enqueued.run_id,
                            owner=f"result-{index}",
                            now=1001.0,
                        ),
                        range(8),
                    )
                )

            self.assertNotIn(None, items)
            claimed_items = [item for item in items if item is not None]
            self.assertEqual(
                len({(item.batch_id, item.ordinal) for item in claimed_items}),
                8,
            )
            for index, item in enumerate(claimed_items):
                store.complete_child(
                    item,
                    alpha_id=f"alpha-{index}",
                    response=envelope(200, {"status": "COMPLETE"}),
                    now=1002.0,
                )

            with ThreadPoolExecutor(max_workers=8) as executor:
                experiments = list(
                    executor.map(
                        lambda index: store.claim_enrichment(
                            enqueued.run_id,
                            owner=f"enrichment-{index}",
                            now=1002.0,
                        ),
                        range(8),
                    )
                )

            self.assertNotIn(None, experiments)
            claimed_experiments = [experiment for experiment in experiments if experiment is not None]
            self.assertEqual(len({experiment.id for experiment in claimed_experiments}), 8)

            store.recover_interrupted(enqueued.run_id, now=1003.0)
            with store.connect() as conn:
                remaining_claims = conn.execute(
                    "SELECT COUNT(*) FROM enrichment_queue WHERE claim_owner IS NOT NULL"
                ).fetchone()[0]
            self.assertEqual(remaining_claims, 0)

    def test_concurrent_runtime_overlaps_sender_and_result_polling(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            enqueued = store.enqueue(
                parse_manifest(
                    {
                        "candidates": [
                            {
                                "expression": "rank(close)",
                                "settings": SETTINGS,
                                "priority": 10,
                            },
                            {
                                "expression": "rank(volume)",
                                "settings": {
                                    **SETTINGS,
                                    "region": "CHN",
                                    "universe": "TOP2000U",
                                },
                            },
                        ]
                    }
                ),
                now=time.time(),
            )
            batch = store.create_next_batch(enqueued.run_id, now=time.time())
            assert batch is not None
            store.mark_simulate_started(batch.id, now=time.time())
            store.accept_simulation(
                batch.id,
                location="https://api.worldquantbrain.com/simulations/parent-due",
                parent_simulation_id="parent-due",
                response=envelope(201),
                not_before=time.time(),
                now=time.time(),
            )
            gateway = ConcurrentPipelineGateway()
            runtime = SqliteSimuRuntime(
                store,
                gateway,
                policy=RuntimePolicy(
                    default_retry_seconds=0.05,
                    idle_sleep_seconds=0.01,
                    lease_seconds=2.0,
                    result_workers=1,
                    enrichment_workers=1,
                ),
            )

            summary = runtime.run(enqueued.run_id, max_runtime_seconds=0.2)

            self.assertTrue(summary["timed_out"])
            self.assertTrue(gateway.poll_started.is_set())
            self.assertTrue(gateway.simulate_started.is_set())

    def test_queue_rows_are_consumed_only_after_stage_results_are_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            enqueued = store.enqueue(
                parse_manifest([{"expression": "rank(close)", "settings": SETTINGS}]),
                now=1000.0,
            )
            self.assertEqual(
                store.run_summary(enqueued.run_id)["queues"],
                {"simulation": 1, "enrichment": 0},
            )

            batch = store.create_next_batch(enqueued.run_id, now=1000.0)
            assert batch is not None
            store.mark_simulate_started(batch.id, now=1000.0)
            store.accept_simulation(
                batch.id,
                location="https://api.worldquantbrain.com/simulations/parent-1",
                parent_simulation_id="parent-1",
                response=envelope(201),
                not_before=1001.0,
                now=1000.0,
            )
            store.complete_parent(
                batch.id,
                alpha_id="alpha-1",
                child_ids=[],
                parent_status="COMPLETE",
                response=envelope(200, {"status": "COMPLETE", "alpha": "alpha-1"}),
                now=1001.0,
            )
            self.assertEqual(
                store.run_summary(enqueued.run_id)["queues"],
                {"simulation": 0, "enrichment": 1},
            )

            experiment = store.next_enrichment(enqueued.run_id, now=1001.0)
            assert experiment is not None
            store.save_alpha_detail(
                experiment,
                alpha_detail("alpha-1"),
                response=envelope(200),
                now=1002.0,
            )
            self.assertEqual(
                store.run_summary(enqueued.run_id)["queues"],
                {"simulation": 0, "enrichment": 1},
            )

            experiment = store.next_enrichment(enqueued.run_id, now=1002.0)
            assert experiment is not None
            store.save_pnl(
                experiment,
                [("2024-01-01", 1.0, None)],
                response=envelope(200),
                now=1003.0,
            )
            summary = store.refresh_run_state(enqueued.run_id, now=1003.0)
            self.assertEqual(summary["queues"], {"simulation": 0, "enrichment": 0})
            self.assertEqual(len(store.experiment_results(enqueued.run_id)), 1)
            checks = store.check_results(enqueued.run_id)
            self.assertEqual(len(checks), 1)
            self.assertEqual(checks[0]["name"], "MATCHES_PYRAMID")
            self.assertEqual(checks[0]["result"], "WARNING")
            self.assertEqual(checks[0]["raw"]["pyramids"], [{"name": "USA/D1"}])

    def test_cancel_preserves_simulate_ambiguity_and_consumes_other_queues(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            enqueued = store.enqueue(
                parse_manifest(
                    {
                        "candidates": [
                            {"expression": "rank(close)", "settings": SETTINGS},
                            {
                                "expression": "rank(volume)",
                                "settings": {
                                    **SETTINGS,
                                    "region": "CHN",
                                    "universe": "TOP2000U",
                                },
                            },
                        ]
                    }
                ),
                now=1000.0,
            )
            batch = store.create_next_batch(enqueued.run_id, now=1000.0)
            assert batch is not None
            store.mark_simulate_started(batch.id, now=1000.0)

            summary = store.cancel_run(
                enqueued.run_id,
                reason="obsolete_template_set",
                now=1001.0,
            )

            self.assertEqual(summary["state"], "CANCELLED")
            self.assertEqual(summary["counts"], {"CANCELLED": 1, "SIMULATE_UNKNOWN": 1})
            self.assertEqual(summary["queues"], {"simulation": 1, "enrichment": 0})
            self.assertEqual(
                store.refresh_run_state(enqueued.run_id, now=1002.0)["state"],
                "CANCELLED",
            )
            with store.connect() as conn:
                batch_state = conn.execute(
                    "SELECT state FROM simulation_batches WHERE id = ?", (batch.id,)
                ).fetchone()[0]
                event_count = conn.execute(
                    "SELECT COUNT(*) FROM api_events WHERE run_id = ? AND event_type = 'RUN_CANCELLED'",
                    (enqueued.run_id,),
                ).fetchone()[0]
            self.assertEqual(batch_state, "SIMULATE_UNKNOWN")
            self.assertEqual(event_count, 1)

    def test_cancel_rejects_active_lease_unless_worker_death_was_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            enqueued = store.enqueue(
                parse_manifest([{"expression": "rank(close)", "settings": SETTINGS}]),
                now=1000.0,
            )
            store.acquire_run_lease(
                enqueued.run_id,
                owner="worker-1",
                now=1000.0,
                lease_seconds=300.0,
            )

            with self.assertRaisesRegex(RuntimeError, "active worker lease"):
                store.cancel_run(enqueued.run_id, reason="stop", now=1001.0)

            summary = store.cancel_run(
                enqueued.run_id,
                reason="verified_worker_dead",
                allow_active_lease=True,
                now=1001.0,
            )
            self.assertEqual(summary["state"], "CANCELLED")

    def test_cancel_consumes_enrichment_queue_and_preserves_alpha_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            enqueued = store.enqueue(
                parse_manifest([{"expression": "rank(close)", "settings": SETTINGS}]),
                now=1000.0,
            )
            batch = store.create_next_batch(enqueued.run_id, now=1000.0)
            assert batch is not None
            store.mark_simulate_started(batch.id, now=1000.0)
            store.accept_simulation(
                batch.id,
                location="https://api.worldquantbrain.com/simulations/parent-1",
                parent_simulation_id="parent-1",
                response=envelope(201),
                not_before=1001.0,
                now=1000.0,
            )
            store.complete_parent(
                batch.id,
                alpha_id="alpha-1",
                child_ids=[],
                parent_status="COMPLETE",
                response=envelope(200, {"status": "COMPLETE", "alpha": "alpha-1"}),
                now=1001.0,
            )
            experiment = store.next_enrichment(enqueued.run_id, now=1001.0)
            assert experiment is not None
            store.save_alpha_detail(
                experiment,
                alpha_detail("alpha-1"),
                response=envelope(200),
                now=1001.5,
            )

            summary = store.cancel_run(enqueued.run_id, reason="stop", now=1002.0)

            self.assertEqual(summary["counts"], {"CANCELLED": 1})
            self.assertEqual(summary["queues"], {"simulation": 0, "enrichment": 0})
            with store.connect() as conn:
                alpha_count = conn.execute(
                    "SELECT COUNT(*) FROM alphas WHERE alpha_id = 'alpha-1'"
                ).fetchone()[0]
            self.assertEqual(alpha_count, 1)

    def test_permanent_failure_consumes_simulation_queue_but_unknown_simulate_does_not(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            failed = store.enqueue(
                parse_manifest([{"expression": "rank(close)", "settings": SETTINGS}]),
                now=1000.0,
            )
            failed_batch = store.create_next_batch(failed.run_id, now=1000.0)
            assert failed_batch is not None
            store.fail_batch(
                failed_batch.id,
                state="PERMANENT_FAILURE",
                error="invalid_expression",
                response=envelope(400),
                now=1001.0,
            )
            self.assertEqual(
                store.run_summary(failed.run_id)["queues"],
                {"simulation": 0, "enrichment": 0},
            )

            unknown = store.enqueue(
                parse_manifest([{"expression": "rank(volume)", "settings": SETTINGS}]),
                now=1002.0,
            )
            unknown_batch = store.create_next_batch(unknown.run_id, now=1002.0)
            assert unknown_batch is not None
            store.fail_batch(
                unknown_batch.id,
                state="SIMULATE_UNKNOWN",
                error="connection_lost_after_post",
                response=None,
                now=1003.0,
            )
            self.assertEqual(
                store.run_summary(unknown.run_id)["queues"],
                {"simulation": 1, "enrichment": 0},
            )

    def test_schema_v1_upgrade_backfills_pending_queues(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            enqueued = store.enqueue(
                parse_manifest([{"expression": "rank(close)", "settings": SETTINGS}]),
                now=1000.0,
            )
            with store.connect() as conn:
                conn.execute("DROP TABLE enrichment_queue")
                conn.execute("DROP TABLE simulation_queue")
                conn.execute("PRAGMA user_version = 1")

            store.initialize()

            self.assertEqual(
                store.run_summary(enqueued.run_id)["queues"],
                {"simulation": 1, "enrichment": 0},
            )

    def test_schema_v3_migrates_legacy_simulation_request_terms(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            enqueued = store.enqueue(
                parse_manifest([{"expression": "rank(close)", "settings": SETTINGS}]),
                now=1000.0,
            )
            batch = store.create_next_batch(enqueued.run_id, now=1000.0)
            assert batch is not None
            with store.connect() as conn:
                conn.execute(
                    "UPDATE simulation_batches SET state = 'SUBMITTING' WHERE id = ?",
                    (batch.id,),
                )
                conn.execute(
                    "UPDATE experiments SET state = 'SUBMITTING', last_error = "
                    "'worker_interrupted_during_submit' WHERE run_id = ?",
                    (enqueued.run_id,),
                )
                conn.execute(
                    "UPDATE simulation_items SET state = 'SUBMIT_UNKNOWN' WHERE batch_id = ?",
                    (batch.id,),
                )
                conn.execute(
                    """
                    INSERT INTO runtime_state(key, value, updated_at)
                    VALUES ('simulation_submit_not_before', '1010', 1000)
                    """
                )
                conn.execute(
                    """
                    INSERT INTO api_events(run_id, batch_id, event_type, payload_json, created_at)
                    VALUES (?, ?, 'SIMULATION_SUBMIT_RETRY',
                            '{"state":"SUBMIT_UNKNOWN"}', 1000)
                    """,
                    (enqueued.run_id, batch.id),
                )
                conn.execute("PRAGMA user_version = 2")

            store.initialize()

            with store.connect() as conn:
                experiment = conn.execute(
                    "SELECT state, last_error FROM experiments WHERE run_id = ?",
                    (enqueued.run_id,),
                ).fetchone()
                migrated_batch = conn.execute(
                    "SELECT state FROM simulation_batches WHERE id = ?",
                    (batch.id,),
                ).fetchone()
                item = conn.execute(
                    "SELECT state FROM simulation_items WHERE batch_id = ?",
                    (batch.id,),
                ).fetchone()
                runtime_keys = {
                    str(row["key"]): str(row["value"])
                    for row in conn.execute("SELECT key, value FROM runtime_state")
                }
                event = conn.execute(
                    """
                    SELECT event_type, payload_json FROM api_events
                    WHERE batch_id = ? AND event_type = 'SIMULATE_RETRY'
                    """,
                    (batch.id,),
                ).fetchone()
                schema_version = conn.execute("PRAGMA user_version").fetchone()[0]
            self.assertEqual(experiment["state"], "SIMULATING")
            self.assertEqual(
                experiment["last_error"],
                "worker_interrupted_during_simulate",
            )
            self.assertEqual(migrated_batch["state"], "SIMULATING")
            self.assertEqual(item["state"], "SIMULATE_UNKNOWN")
            self.assertEqual(runtime_keys, {"simulation_request_not_before": "1010"})
            self.assertEqual(event["event_type"], "SIMULATE_RETRY")
            self.assertIn("SIMULATE_UNKNOWN", event["payload_json"])
            self.assertEqual(schema_version, 4)

    def test_run_lease_rejects_a_second_worker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            enqueued = store.enqueue(
                parse_manifest([{"expression": "close", "settings": SETTINGS}]),
                now=1000.0,
            )
            store.acquire_run_lease(
                enqueued.run_id,
                owner="worker-1",
                now=1000.0,
                lease_seconds=300.0,
            )

            with self.assertRaisesRegex(RunLeaseError, "already leased"):
                store.acquire_run_lease(
                    enqueued.run_id,
                    owner="worker-2",
                    now=1001.0,
                    lease_seconds=300.0,
                )

            store.release_run_lease(enqueued.run_id, owner="worker-1")

    def test_interrupted_simulate_blocks_without_reposting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            manifest = parse_manifest([{"expression": "close", "settings": SETTINGS}])
            enqueued = store.enqueue(manifest, now=1000.0)
            batch = store.create_next_batch(enqueued.run_id, now=1000.0)
            assert batch is not None
            store.mark_simulate_started(batch.id, now=1000.0)
            gateway = NoCallGateway()
            clock = FakeClock()
            runtime = SqliteSimuRuntime(
                store,
                gateway,
                policy=sequential_policy(),
                clock=clock,
                sleeper=clock.sleep,
            )

            summary = runtime.run(enqueued.run_id)

            self.assertEqual(summary["state"], "BLOCKED")
            self.assertEqual(summary["counts"], {"SIMULATE_UNKNOWN": 1})
            self.assertEqual(gateway.calls, 0)

    def test_simulate_unknown_waits_for_other_experiments_before_blocking_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            manifest = parse_manifest(
                {
                    "candidates": [
                        {"expression": "rank(close)", "settings": SETTINGS},
                        {
                            "expression": "rank(volume)",
                            "settings": {**SETTINGS, "region": "CHN", "universe": "TOP2000U"},
                        },
                    ]
                }
            )
            enqueued = store.enqueue(manifest, now=1000.0)
            batch = store.create_next_batch(enqueued.run_id, now=1000.0)
            assert batch is not None
            store.mark_simulate_started(batch.id, now=1000.0)
            store.fail_batch(
                batch.id,
                state="SIMULATE_UNKNOWN",
                error="connection_lost",
                response=None,
                now=1001.0,
            )

            summary = store.refresh_run_state(enqueued.run_id, now=1001.0)

            self.assertEqual(summary["state"], "RUNNING")
            self.assertEqual(summary["counts"], {"QUEUED": 1, "SIMULATE_UNKNOWN": 1})

    def test_throttling_does_not_consume_the_failure_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            manifest = parse_manifest(
                {
                    "candidates": [
                        {"expression": "rank(close)", "settings": SETTINGS},
                        {"expression": "rank(volume)", "settings": SETTINGS},
                    ]
                }
            )
            enqueued = store.enqueue(manifest, now=1000.0)
            gateway = ThrottledGateway()
            clock = FakeClock()
            runtime = SqliteSimuRuntime(
                store,
                gateway,
                policy=sequential_policy(
                    max_attempts=1,
                    default_retry_seconds=1.0,
                    idle_sleep_seconds=1.0,
                ),
                clock=clock,
                sleeper=clock.sleep,
            )

            summary = runtime.run(enqueued.run_id)

            self.assertEqual(summary["state"], "COMPLETED")
            self.assertEqual(sum(call["method"] == "POST" for call in gateway.calls), 2)
            self.assertGreaterEqual(clock.value, 1002.0)

    def test_auth_statuses_never_consume_runtime_failure_budget(self) -> None:
        for trigger in (204, 401, 429):
            with self.subTest(trigger=trigger), tempfile.TemporaryDirectory() as temp_dir:
                store = initialized_store(temp_dir)
                manifest = parse_manifest(
                    {
                        "candidates": [
                            {"expression": "rank(close)", "settings": SETTINGS},
                            {"expression": "rank(volume)", "settings": SETTINGS},
                        ]
                    }
                )
                enqueued = store.enqueue(manifest, now=1000.0)
                gateway = RecoveringSessionGateway(trigger)
                clock = FakeClock()
                runtime = SqliteSimuRuntime(
                    store,
                    gateway,
                    policy=sequential_policy(
                        max_attempts=1,
                        default_retry_seconds=1.0,
                        idle_sleep_seconds=1.0,
                    ),
                    clock=clock,
                    sleeper=clock.sleep,
                )

                summary = runtime.run(enqueued.run_id)

                self.assertEqual(summary["state"], "COMPLETED")
                self.assertEqual(summary["counts"], {"READY": 2})

    def test_parent_error_without_children_requeues_like_the_legacy_worker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            manifest = parse_manifest(
                {
                    "candidates": [
                        {"expression": "rank(close)", "settings": SETTINGS},
                        {"expression": "rank(volume)", "settings": SETTINGS},
                    ]
                }
            )
            enqueued = store.enqueue(manifest, now=1000.0)
            gateway = RetryableSimulationGateway()
            clock = FakeClock()
            runtime = SqliteSimuRuntime(
                store,
                gateway,
                policy=sequential_policy(default_retry_seconds=1.0, idle_sleep_seconds=1.0),
                clock=clock,
                sleeper=clock.sleep,
            )

            summary = runtime.run(enqueued.run_id)

            self.assertEqual(summary["state"], "COMPLETED")
            self.assertEqual(gateway.simulate_calls, 2)
            with store.connect() as conn:
                retried = conn.execute(
                    "SELECT COUNT(*) FROM simulation_batches WHERE state = 'RETRIED'"
                ).fetchone()[0]
            self.assertEqual(retried, 1)

    def test_cancelled_parent_is_requeued_instead_of_polled_forever(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            enqueued = store.enqueue(
                parse_manifest([{"expression": "close", "settings": SETTINGS}]),
                now=1000.0,
            )
            batch = store.create_next_batch(enqueued.run_id, now=1000.0)
            assert batch is not None
            store.mark_simulate_started(batch.id, now=1000.0)
            store.accept_simulation(
                batch.id,
                location="https://api.worldquantbrain.com/simulations/parent-cancelled",
                parent_simulation_id="parent-cancelled",
                response=envelope(201),
                not_before=1001.0,
                now=1000.0,
            )
            polling = store.next_poll_batch(enqueued.run_id, now=1001.0)
            assert polling is not None
            runtime = SqliteSimuRuntime(
                store,
                FixedResponseGateway(envelope(200, {"status": "CANCELLED"})),
            )

            runtime._poll_parent(polling, now=1001.0)

            summary = store.run_summary(enqueued.run_id)
            self.assertEqual(summary["counts"], {"RETRY_WAIT": 1})
            with store.connect() as conn:
                state = conn.execute(
                    "SELECT state FROM simulation_batches WHERE id = ?", (batch.id,)
                ).fetchone()[0]
            self.assertEqual(state, "RETRIED")

    def test_cancelled_child_is_requeued_instead_of_polled_forever(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            enqueued = store.enqueue(
                parse_manifest(
                    [
                        {"expression": "close", "settings": SETTINGS},
                        {"expression": "volume", "settings": SETTINGS},
                    ]
                ),
                now=1000.0,
            )
            batch = store.create_next_batch(enqueued.run_id, now=1000.0)
            assert batch is not None
            store.mark_simulate_started(batch.id, now=1000.0)
            store.complete_parent(
                batch.id,
                alpha_id=None,
                child_ids=["child-cancelled", "child-pending"],
                parent_status="COMPLETE",
                response=envelope(200, {"status": "COMPLETE"}),
                now=1001.0,
            )
            item = store.next_child_item(enqueued.run_id, now=1001.0)
            assert item is not None
            runtime = SqliteSimuRuntime(
                store,
                FixedResponseGateway(envelope(200, {"status": "CANCELLED"})),
            )

            runtime._poll_child(item, now=1001.0)

            summary = store.run_summary(enqueued.run_id)
            self.assertEqual(summary["counts"], {"CHILD_POLLING": 1, "RETRY_WAIT": 1})
            with store.connect() as conn:
                state = conn.execute(
                    "SELECT state FROM simulation_items WHERE batch_id = ? AND ordinal = 0",
                    (batch.id,),
                ).fetchone()[0]
            self.assertEqual(state, "RETRIED")

    def test_step_rotates_ready_work_classes_to_prevent_starvation(self) -> None:
        class AlwaysReadyStore:
            def next_poll_batch(self, run_id: str, *, now: float) -> str:
                return "parent"

            def next_child_item(self, run_id: str, *, now: float) -> str:
                return "child"

            def next_enrichment(self, run_id: str, *, now: float) -> str:
                return "enrichment"

            def next_simulate_batch(self, run_id: str, *, now: float) -> str:
                return "simulation"

        observed: list[str] = []
        runtime = SqliteSimuRuntime(AlwaysReadyStore(), NoCallGateway())  # type: ignore[arg-type]
        runtime._poll_parent = lambda batch, *, now: observed.append(str(batch))  # type: ignore[method-assign]
        runtime._poll_child = lambda item, *, now: observed.append(str(item))  # type: ignore[method-assign]
        runtime._enrich = lambda experiment, *, now: observed.append(str(experiment))  # type: ignore[method-assign]
        runtime._simulate = lambda batch, *, now: observed.append(str(batch))  # type: ignore[method-assign]

        for _ in range(8):
            self.assertTrue(runtime._step("run", now=1000.0))

        self.assertEqual(
            observed,
            [
                "parent",
                "child",
                "enrichment",
                "simulation",
                "parent",
                "child",
                "enrichment",
                "simulation",
            ],
        )

    def test_pnl_points_forward_fills_before_differencing(self) -> None:
        self.assertEqual(
            pnl_points(
                {
                    "records": [
                        ["d1", 4],
                        ["d2", None],
                        {"date": "d3", "pnl": "7.5"},
                    ]
                }
            ),
            [("d1", 4.0, None), ("d2", 4.0, 0.0), ("d3", 7.5, 3.5)],
        )

    def test_parent_progress_035_scales_retry_by_legacy_batch_size_rule(self) -> None:
        result = envelope(200, {"progress": 0.35}, retry_after="4")

        self.assertEqual(_retry_seconds(result, 1.0, batch_size=10), 20.0)
        self.assertEqual(_retry_seconds(result, 1.0, batch_size=1), 4.0)


def initialized_store(temp_dir: str) -> SqliteStore:
    store = SqliteStore(Path(temp_dir) / "simulations.sqlite3")
    store.initialize()
    return store


def envelope(
    status_code: int,
    body: dict[str, Any] | None = None,
    *,
    location: str | None = None,
    retry_after: str | None = None,
) -> dict[str, Any]:
    return {
        "ok": 200 <= status_code < 400,
        "response": {
            "status_code": status_code,
            "body": body,
            "location": location,
            "retry_after": retry_after,
        },
    }


def alpha_detail(alpha_id: str) -> dict[str, Any]:
    return {
        "id": alpha_id,
        "type": "REGULAR",
        "author": "user-1",
        "settings": {**SETTINGS, "maxTrade": "OFF"},
        "regular": {"code": "rank(close)", "operatorCount": 1},
        "dateCreated": "2026-01-01T00:00:00Z",
        "classifications": [{"id": "DATA_USAGE:SINGLE_DATA_SET"}],
        "is": {
            "pnl": 100.0,
            "longCount": 100,
            "shortCount": 90,
            "turnover": 0.2,
            "returns": 0.03,
            "drawdown": 0.04,
            "margin": 0.001,
            "sharpe": 1.8,
            "fitness": 1.2,
            "checks": [
                {
                    "name": "MATCHES_PYRAMID",
                    "result": "WARNING",
                    "pyramids": [{"name": "USA/D1"}],
                }
            ],
        },
    }


if __name__ == "__main__":
    unittest.main()
