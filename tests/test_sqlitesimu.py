from __future__ import annotations

import json
import tempfile
import unittest
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
        raise AssertionError("ambiguous submissions must never be posted again automatically")


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
        self.submissions = 0

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
            self.submissions += 1
            if self.submissions == 1:
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


class ReauthGateway(WqbApiGateway):
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = responses
        self.auth_calls = 0

    def _call_once(
        self,
        method: str,
        path: str,
        *,
        path_vars: dict[str, str] | None,
        params: dict[str, Any] | None,
        json_body: Any,
    ) -> dict[str, Any]:
        return self.responses.pop(0)

    def _reauthenticate(self) -> bool:
        self.auth_calls += 1
        return True


class SqliteSimuTests(unittest.TestCase):
    def test_each_401_call_gets_one_reauthentication_and_replay(self) -> None:
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
                policy=RuntimePolicy(default_retry_seconds=1.0, idle_sleep_seconds=1.0),
                clock=clock,
                sleeper=clock.sleep,
            )

            summary = runtime.run(enqueued.run_id)

            self.assertEqual(summary["state"], "COMPLETED")
            self.assertEqual(summary["counts"], {"READY": 2})
            post = next(call for call in gateway.calls if call["method"] == "POST")
            self.assertIsInstance(post["json_body"], list)
            self.assertEqual(len(post["json_body"]), 2)
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

    def test_interrupted_submission_blocks_without_reposting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = initialized_store(temp_dir)
            manifest = parse_manifest([{"expression": "close", "settings": SETTINGS}])
            enqueued = store.enqueue(manifest, now=1000.0)
            batch = store.create_next_batch(enqueued.run_id, now=1000.0)
            assert batch is not None
            store.mark_submit_started(batch.id, now=1000.0)
            gateway = NoCallGateway()
            clock = FakeClock()
            runtime = SqliteSimuRuntime(store, gateway, clock=clock, sleeper=clock.sleep)

            summary = runtime.run(enqueued.run_id)

            self.assertEqual(summary["state"], "BLOCKED")
            self.assertEqual(summary["counts"], {"SUBMIT_UNKNOWN": 1})
            self.assertEqual(gateway.calls, 0)

    def test_submit_unknown_waits_for_other_experiments_before_blocking_run(self) -> None:
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
            store.mark_submit_started(batch.id, now=1000.0)
            store.fail_batch(
                batch.id,
                state="SUBMIT_UNKNOWN",
                error="connection_lost",
                response=None,
                now=1001.0,
            )

            summary = store.refresh_run_state(enqueued.run_id, now=1001.0)

            self.assertEqual(summary["state"], "RUNNING")
            self.assertEqual(summary["counts"], {"QUEUED": 1, "SUBMIT_UNKNOWN": 1})

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
                policy=RuntimePolicy(
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
                policy=RuntimePolicy(default_retry_seconds=1.0, idle_sleep_seconds=1.0),
                clock=clock,
                sleeper=clock.sleep,
            )

            summary = runtime.run(enqueued.run_id)

            self.assertEqual(summary["state"], "COMPLETED")
            self.assertEqual(gateway.submissions, 2)
            with store.connect() as conn:
                retried = conn.execute(
                    "SELECT COUNT(*) FROM simulation_batches WHERE state = 'RETRIED'"
                ).fetchone()[0]
            self.assertEqual(retried, 1)

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
