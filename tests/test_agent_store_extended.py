from __future__ import annotations

import sqlite3
import tempfile
import threading
import unittest
from collections import OrderedDict
from contextlib import closing
from pathlib import Path

import wqb_cli.agent.store as store_module
from wqb_cli.agent.store import AgentStore
from wqb_cli.agent.types import Budget, ModelRole, RunConfig, ScopeMode, WorkflowNode


def auto_config() -> RunConfig:
    return RunConfig(scope_mode=ScopeMode.AUTO, budget=Budget(rounds=3))


class AgentStoreExtendedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "agent.sqlite3"
        self.store = AgentStore(self.db_path)
        self.store.initialize()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def create_run(self, run_id: str = "run") -> None:
        self.store.create_run(run_id, auto_config())

    def test_v3_migration_creates_domain_tables_and_upgrades_exact_v2(self) -> None:
        expected_tables = {
            "research_plans",
            "operator_tasks",
            "model_calls",
            "artifacts",
            "command_ledger",
            "candidates",
            "simulations",
            "diagnoses",
            "approvals",
            "experiences",
            "experience_fields",
        }
        with closing(self.store.connect()) as connection:
            versions = [
                row["version"]
                for row in connection.execute(
                    "SELECT version FROM schema_version ORDER BY version"
                )
            ]
            tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            ledger_index_sql = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'index' "
                "AND name = 'idx_command_ledger_run_status'"
            ).fetchone()
        self.assertEqual(versions, [1, 2, 3])
        self.assertTrue(expected_tables <= tables)
        self.assertIsNotNone(ledger_index_sql)
        self.assertIn("command_ledger(run_id, status)", ledger_index_sql[0])

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "v2.sqlite3"
            v2_store = AgentStore(path, _migrations=store_module._MIGRATIONS[:2])
            v2_store.initialize()
            with closing(v2_store.connect()) as connection:
                before = connection.execute(
                    "SELECT sql FROM sqlite_master "
                    "WHERE name IN ('runs', 'node_attempts') ORDER BY name"
                ).fetchall()
                self.assertIsNone(
                    connection.execute(
                        "SELECT 1 FROM sqlite_master WHERE type = 'index' "
                        "AND name = 'idx_command_ledger_run_status'"
                    ).fetchone()
                )

            upgraded = AgentStore(path)
            upgraded.initialize()
            upgraded.initialize()
            reopened = AgentStore(path)
            reopened.initialize()
            with closing(reopened.connect()) as connection:
                after = connection.execute(
                    "SELECT sql FROM sqlite_master "
                    "WHERE name IN ('runs', 'node_attempts') ORDER BY name"
                ).fetchall()
                upgraded_versions = [
                    row["version"]
                    for row in connection.execute(
                        "SELECT version FROM schema_version ORDER BY version"
                    )
                ]
                upgraded_ledger_index = connection.execute(
                    "SELECT sql FROM sqlite_master WHERE type = 'index' "
                    "AND name = 'idx_command_ledger_run_status'"
                ).fetchone()
            self.assertEqual(after, before)
            self.assertEqual(upgraded_versions, [1, 2, 3])
            self.assertIsNotNone(upgraded_ledger_index)
            self.assertIn(
                "command_ledger(run_id, status)", upgraded_ledger_index[0]
            )

    def test_research_plans_and_operator_tasks_are_versioned_and_terminal(self) -> None:
        self.create_run()
        plan = self.store.record_research_plan(
            "run", 1, "plan-hash-1", {"z": 1, "a": {"task": True}}
        )
        latest = self.store.record_research_plan(
            "run", 2, "plan-hash-2", {"next": [2, 1]}
        )
        self.assertEqual(plan.plan_version, 1)
        self.assertEqual(plan.plan, {"a": {"task": True}, "z": 1})
        self.assertEqual(self.store.get_latest_research_plan("run"), latest)
        with self.assertRaises(store_module.StoreConflict):
            self.store.record_research_plan("run", 2, "other", {})
        with self.assertRaises(store_module.StoreConflict):
            self.store.record_research_plan("run", 3, "plan-hash-1", {})

        task = self.store.record_operator_task(
            "run", "task-1", 2, {"z": "last", "a": "first"}
        )
        self.assertEqual(task.status, "PENDING")
        self.assertEqual(task.task, {"a": "first", "z": "last"})
        with self.assertRaises(ValueError):
            self.store.complete_operator_task("run", "task-1", "PENDING", {})
        self.assertEqual(self.store.get_operator_task("run", "task-1"), task)
        completed = self.store.complete_operator_task(
            "run", "task-1", "COMPLETED", {"answer": 42}
        )
        self.assertEqual(completed.result, {"answer": 42})
        self.assertEqual(self.store.get_operator_task("run", "task-1"), completed)
        with self.assertRaises(store_module.StoreConflict):
            self.store.complete_operator_task("run", "task-1", "FAILED", {})

        with closing(self.store.connect()) as connection:
            stored_plan = connection.execute(
                "SELECT plan_json FROM research_plans WHERE id = ?", (plan.id,)
            ).fetchone()[0]
            stored_task = connection.execute(
                "SELECT task_json, result_json FROM operator_tasks WHERE id = ?",
                (task.id,),
            ).fetchone()
        self.assertEqual(stored_plan, '{"a":{"task":true},"z":1}')
        self.assertEqual(tuple(stored_task), ('{"a":"first","z":"last"}', '{"answer":42}'))

    def test_json_objects_reject_lossy_or_non_native_values(self) -> None:
        self.create_run()
        valid = {
            "none": None,
            "bool": True,
            "int": 2,
            "float": 1.5,
            "str": "value",
            "list": [{"nested": False}, 3],
        }
        recorded = self.store.record_research_plan("run", 1, "valid-json", valid)
        self.assertEqual(recorded.plan, valid)

        invalid_values = (
            {"tuple": (1, 2)},
            {1: "non-string-key"},
            {"nested": {1: "non-string-key"}},
            {"mapping": OrderedDict((("key", "value"),))},
            {"set": {1, 2}},
            {"nan": float("nan")},
            {"infinity": float("inf")},
        )
        for version, value in enumerate(invalid_values, start=2):
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    self.store.record_research_plan(
                        "run", version, f"invalid-json-{version}", value
                    )
        with closing(self.store.connect()) as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM research_plans WHERE run_id = 'run'"
            ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_model_calls_validate_usage_and_summarize_by_exact_role(self) -> None:
        self.create_run()
        recorded = self.store.record_model_call(
            "run",
            ModelRole.PLANNER,
            WorkflowNode.A,
            "openai",
            "planner-model",
            "draft plan",
            "COMPLETED",
            input_tokens=10,
            cost_usd=0.25,
            latency_ms=100,
        )
        self.assertEqual(recorded.role, ModelRole.PLANNER)
        self.store.record_model_call(
            "run",
            ModelRole.PLANNER,
            WorkflowNode.F,
            "backup",
            "fallback-model",
            "repair plan",
            "FAILED",
            latency_ms=50.5,
            fallback_used=True,
            error="timeout",
        )
        self.store.record_model_call(
            "run",
            ModelRole.OPERATOR,
            WorkflowNode.G,
            "openai",
            "operator-model",
            "execute task",
            "COMPLETED",
            input_tokens=3,
            output_tokens=4,
            cost_usd=0.5,
        )
        self.assertEqual(
            self.store.usage_summary("run"),
            {
                "planner": {
                    "calls": 2,
                    "input_tokens": 10,
                    "output_tokens": 0,
                    "cost_usd": 0.25,
                    "latency_ms": 150.5,
                    "failures": 1,
                    "fallbacks": 1,
                },
                "operator": {
                    "calls": 1,
                    "input_tokens": 3,
                    "output_tokens": 4,
                    "cost_usd": 0.5,
                    "latency_ms": 0.0,
                    "failures": 0,
                    "fallbacks": 0,
                },
            },
        )

        with tempfile.TemporaryDirectory() as tmp:
            absent = Path(tmp) / "absent.sqlite3"
            unopened = AgentStore(absent)
            common = ("run", ModelRole.PLANNER, WorkflowNode.A, "p", "m", "x", "OK")
            invalid = (
                lambda: unopened.record_model_call("run", "planner", *common[2:]),
                lambda: unopened.record_model_call("run", ModelRole.PLANNER, "A", *common[3:]),
                lambda: unopened.record_model_call(*common, input_tokens=True),
                lambda: unopened.record_model_call(*common, output_tokens=-1),
                lambda: unopened.record_model_call(*common, cost_usd=float("nan")),
                lambda: unopened.record_model_call(*common, latency_ms=float("inf")),
                lambda: unopened.record_model_call(*common, fallback_used=1),
                lambda: unopened.record_model_call(
                    "run", ModelRole.PLANNER, WorkflowNode.A, " ", "m", "x", "OK"
                ),
            )
            for operation in invalid:
                with self.assertRaises((TypeError, ValueError)):
                    operation()
                self.assertFalse(absent.exists())

    def test_artifacts_are_metadata_only_unique_and_upsertable(self) -> None:
        self.create_run()
        missing_path = Path(self.tmp.name) / "does-not-exist" / "result.json"
        artifact = self.store.add_artifact(
            "run", WorkflowNode.G, "simulation-result", missing_path, "abc123"
        )
        self.assertFalse(missing_path.exists())
        self.assertEqual(artifact.path, str(missing_path))
        self.assertEqual(artifact.kind, "json")
        self.assertEqual(self.store.get_artifact(artifact.id), artifact)
        with self.assertRaises(store_module.StoreConflict):
            self.store.add_artifact(
                "run", WorkflowNode.G, "simulation-result", "other", "different"
            )

        updated = self.store.add_or_update_artifact(
            "run",
            WorkflowNode.G,
            "simulation-result",
            Path("new/location.bin"),
            "def456",
            kind="binary",
        )
        self.assertEqual(updated.id, artifact.id)
        self.assertEqual(updated.path, str(Path("new/location.bin")))
        self.assertEqual(updated.sha256, "def456")
        self.assertEqual(updated.kind, "binary")
        self.assertEqual(self.store.get_artifact(artifact.id), updated)
        with self.assertRaises(store_module.StoreRecordNotFound):
            self.store.get_artifact(artifact.id + 1000)

    def test_command_ledger_is_atomic_idempotent_and_recovery_aware(self) -> None:
        self.create_run()
        artifact = self.store.add_artifact(
            "run", WorkflowNode.G, "result", "result.json", "sha"
        )
        barrier = threading.Barrier(3)
        records = []
        errors = []
        lock = threading.Lock()

        def reserve() -> None:
            local = AgentStore(self.db_path)
            barrier.wait(timeout=5)
            try:
                value = local.reserve_command(
                    "run", WorkflowNode.G, "fingerprint", ("simulate", "--id", "1")
                )
                with lock:
                    records.append(value)
            except BaseException as error:
                with lock:
                    errors.append(error)

        threads = [threading.Thread(target=reserve) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait(timeout=5)
        for thread in threads:
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual({record.id for record in records}, {records[0].id})
        self.assertEqual(
            {record.status for record in records}, {"STARTED", "RECOVERY_REQUIRED"}
        )
        command = self.store.get_command(records[0].id)
        self.assertEqual(command.status, "STARTED")
        self.assertEqual(command.argv, ("simulate", "--id", "1"))
        recovery = self.store.reserve_command(
            "run", WorkflowNode.G, "fingerprint", ["ignored", "on", "replay"]
        )
        self.assertEqual(recovery.status, "RECOVERY_REQUIRED")
        self.assertEqual(recovery.argv, command.argv)

        resource = self.store.mark_command_resource(command.id, "simulation-123")
        self.assertEqual(resource.resource_id, "simulation-123")
        self.assertEqual(
            self.store.mark_command_resource(command.id, "simulation-123").resource_id,
            "simulation-123",
        )
        with self.assertRaises(store_module.StoreConflict):
            self.store.mark_command_resource(command.id, "different-simulation")
        persisted = AgentStore(self.db_path).get_command(command.id)
        self.assertEqual(persisted.resource_id, "simulation-123")
        with self.assertRaises(store_module.StoreConflict):
            self.store.complete_command(command.id, 0, resource_id="replacement")
        self.assertEqual(
            self.store.get_command(command.id).resource_id, "simulation-123"
        )
        completed = self.store.complete_command(command.id, 0, artifact_id=artifact.id)
        self.assertEqual(completed.status, "COMPLETED")
        self.assertEqual(completed.resource_id, "simulation-123")
        self.assertEqual(completed.artifact_id, artifact.id)
        self.assertEqual(
            self.store.reserve_command(
                "run", WorkflowNode.G, "fingerprint", ["different"]
            ),
            completed,
        )
        for operation in (
            lambda: self.store.complete_command(command.id, 0),
            lambda: self.store.fail_command(command.id, "late failure"),
            lambda: self.store.mark_command_resource(command.id, "changed"),
        ):
            with self.assertRaises(store_module.StoreConflict):
                operation()

        failed = self.store.reserve_command(
            "run", WorkflowNode.F, "failed-fingerprint", ["simulate"]
        )
        self.store.mark_command_resource(failed.id, "sim-failed")
        with self.assertRaises(store_module.StoreConflict):
            self.store.fail_command(
                failed.id, "provider failed", resource_id="replacement"
            )
        failed = self.store.fail_command(
            failed.id,
            "provider failed",
            exit_code=9,
            resource_id="sim-failed",
            artifact_id=artifact.id,
        )
        self.assertEqual(failed.status, "FAILED")
        projected = self.store.reserve_command(
            "run", WorkflowNode.F, "failed-fingerprint", ["ignored"]
        )
        self.assertEqual(projected.status, "FAILED")
        self.assertEqual(projected.error, "provider failed")
        self.assertEqual(projected.resource_id, "sim-failed")
        self.assertEqual(projected.artifact_id, artifact.id)
        with closing(self.store.connect()) as connection:
            stored = connection.execute(
                "SELECT status, error FROM command_ledger WHERE id = ?", (failed.id,)
            ).fetchone()
            count = connection.execute(
                "SELECT COUNT(*) FROM command_ledger "
                "WHERE run_id = 'run' AND command_fingerprint = 'fingerprint'"
            ).fetchone()[0]
        self.assertEqual(tuple(stored), ("FAILED", "provider failed"))
        self.assertEqual(count, 1)

    def test_candidates_simulations_and_diagnoses_preserve_domain_identity(self) -> None:
        self.create_run()
        candidate = self.store.add_candidate(
            "run",
            "expression-hash",
            {"expression": "rank(close)", "settings": {"z": 1}},
            status=" ACCEPTED ",
            reason=" initial screen ",
        )
        same = self.store.add_candidate(
            "run",
            "expression-hash",
            {"settings": {"z": 1}, "expression": "rank(close)"},
            status="ACCEPTED",
            reason="initial screen",
        )
        self.assertEqual(same, candidate)
        self.assertEqual(candidate.status, "ACCEPTED")
        self.assertEqual(candidate.reason, "initial screen")
        self.assertEqual(
            self.store.get_candidate_by_fingerprint("run", "expression-hash"),
            candidate,
        )
        with self.assertRaises(store_module.StoreConflict):
            self.store.add_candidate(
                "run",
                "expression-hash",
                {"expression": "rank(volume)"},
                status="ACCEPTED",
                reason="initial screen",
            )
        with self.assertRaises(store_module.StoreConflict):
            self.store.add_candidate(
                "run",
                "expression-hash",
                {"settings": {"z": 1}, "expression": "rank(close)"},
                status="REJECTED",
                reason="initial screen",
            )
        with self.assertRaises(store_module.StoreConflict):
            self.store.add_candidate(
                "run",
                "expression-hash",
                {"settings": {"z": 1}, "expression": "rank(close)"},
                status="ACCEPTED",
                reason="different reason",
            )

        artifact = self.store.add_artifact(
            "run", WorkflowNode.G, "sim-result", "sim.json", "sha"
        )
        other_artifact = self.store.add_artifact(
            "run", WorkflowNode.G, "other-result", "other.json", "other-sha"
        )
        simulation = self.store.record_simulation(
            "run", "simulation-1", "CREATED", candidate_id=candidate.id
        )
        self.assertEqual(simulation.candidate_id, candidate.id)
        pending = self.store.update_simulation("run", "simulation-1", "PENDING")
        self.assertEqual(pending.status, "PENDING")
        queued = self.store.update_simulation("run", "simulation-1", "QUEUED")
        self.assertEqual(queued.status, "QUEUED")
        running = self.store.update_simulation("run", "simulation-1", "RUNNING")
        self.assertEqual(running.status, "RUNNING")
        completed = self.store.update_simulation(
            "run",
            "simulation-1",
            "COMPLETE",
            alpha_id="alpha-1",
            result_artifact_id=artifact.id,
        )
        self.assertEqual(completed.id, simulation.id)
        self.assertEqual(completed.status, "COMPLETE")
        self.assertEqual(completed.alpha_id, "alpha-1")
        self.assertEqual(completed.result_artifact_id, artifact.id)
        repeated = self.store.update_simulation(
            "run",
            "simulation-1",
            "COMPLETE",
            alpha_id="alpha-1",
            result_artifact_id=artifact.id,
        )
        self.assertEqual(repeated, completed)
        for operation in (
            lambda: self.store.update_simulation("run", "simulation-1", "RUNNING"),
            lambda: self.store.update_simulation("run", "simulation-1", "FAILED"),
            lambda: self.store.update_simulation(
                "run", "simulation-1", "COMPLETE", alpha_id="alpha-2"
            ),
            lambda: self.store.update_simulation(
                "run",
                "simulation-1",
                "COMPLETE",
                result_artifact_id=other_artifact.id,
            ),
        ):
            with self.assertRaises(store_module.StoreConflict):
                operation()
        self.assertEqual(self.store.get_simulation("run", "simulation-1"), completed)
        with self.assertRaises(store_module.StoreConflict):
            self.store.record_simulation("run", "simulation-1", "CREATED")
        for invalid_status in ("COMPLETED", "complete", "UNKNOWN", " COMPLETE "):
            with self.assertRaises(ValueError):
                self.store.record_simulation(
                    "run", f"invalid-{invalid_status}", invalid_status
                )
        for terminal_status in ("WARNING", "ERROR", "FAIL", "FAILED", "TIMED_OUT"):
            terminal = self.store.record_simulation(
                "run", f"terminal-{terminal_status}", terminal_status
            )
            self.assertEqual(terminal.status, terminal_status)

        attempt = self.store.start_node_attempt("run", WorkflowNode.F)
        diagnosis = self.store.record_diagnosis(
            "run",
            "LOW_SHARPE",
            WorkflowNode.F,
            {"z": "retry", "a": ["adjust"]},
            node_attempt_id=attempt.id,
        )
        self.assertEqual(diagnosis.failure_class, "LOW_SHARPE")
        self.assertEqual(diagnosis.next_node, WorkflowNode.F)
        self.assertEqual(diagnosis.diagnosis, {"a": ["adjust"], "z": "retry"})
        with closing(self.store.connect()) as connection:
            stored = connection.execute(
                "SELECT candidate_json FROM candidates WHERE id = ?", (candidate.id,)
            ).fetchone()[0]
            diagnosis_json = connection.execute(
                "SELECT diagnosis_json FROM diagnoses WHERE id = ?", (diagnosis.id,)
            ).fetchone()[0]
        self.assertEqual(
            stored, '{"expression":"rank(close)","settings":{"z":1}}'
        )
        self.assertEqual(diagnosis_json, '{"a":["adjust"],"z":"retry"}')

    def test_approval_records_match_exact_tuple_without_submission_behavior(self) -> None:
        self.create_run()
        before = self.store.get_run("run")
        approval = self.store.record_approval("run", "alpha-1", "report-hash")
        self.assertEqual(approval.decision, "APPROVED")
        self.assertIsNone(approval.consumed_at)
        self.assertTrue(
            self.store.approval_matches(
                approval.id, "run", "alpha-1", "report-hash"
            )
        )
        self.assertFalse(
            self.store.approval_matches(
                approval.id, "run", "alpha-1", "changed-report"
            )
        )
        self.assertFalse(
            self.store.approval_matches(
                approval.id + 1000, "run", "alpha-1", "report-hash"
            )
        )
        self.assertEqual(
            self.store.find_unconsumed_approval(
                "run", "alpha-1", "report-hash"
            ),
            approval,
        )
        self.assertIsNone(
            self.store.find_unconsumed_approval(
                "run", "alpha-1", "changed-report"
            )
        )
        with self.assertRaises(store_module.StoreConflict):
            self.store.record_approval("run", "alpha-1", "report-hash")
        self.assertEqual(self.store.get_run("run"), before)
        self.assertFalse(hasattr(self.store, "consume_approval"))
        self.assertFalse(hasattr(self.store, "begin_submission"))
        self.assertFalse(hasattr(self.store, "submit"))

    def test_experience_search_uses_exact_scope_fields_failures_and_limits(self) -> None:
        self.create_run()
        base = {
            "region": " CHN ",
            "delay": 1,
            "category": " price-volume ",
            "expression_fingerprint": " expr-1 ",
            "field_ids": [" volume ", "close", "volume"],
            "failure_class": " LOW_SHARPE ",
            "hypothesis": {"z": 1, "a": "idea"},
            "record": {"round": 1},
            "metrics": {"sharpe": 0.4},
            "final_decision": "RETRY",
        }
        first = self.store.add_experience("run", base)
        self.assertEqual(first.field_ids, ("close", "volume"))
        self.assertEqual(first.region, "CHN")
        self.assertEqual(first.category, "price-volume")
        self.assertEqual(first.expression_fingerprint, "expr-1")
        self.assertEqual(first.failure_class, "LOW_SHARPE")
        self.assertEqual(first.hypothesis, {"a": "idea", "z": 1})
        second = self.store.add_experience(
            "run",
            {
                **base,
                "expression_fingerprint": "expr-2",
                "field_ids": ["volume_alt"],
                "failure_class": "TURNOVER",
            },
        )
        third = self.store.add_experience(
            "run",
            {
                **base,
                "expression_fingerprint": "expr-3",
                "failure_class": "LOW_SHARPE",
            },
        )
        self.assertEqual(
            [record.id for record in self.store.search_experience(
                "CHN", 1, "price-volume"
            )],
            [third.id, second.id, first.id],
        )
        self.assertEqual(
            [record.id for record in self.store.search_experience(
                " CHN ", 1, " price-volume "
            )],
            [third.id, second.id, first.id],
        )
        self.assertEqual(
            [record.id for record in self.store.search_experience(
                "CHN", 1, "price-volume", field_id="volume"
            )],
            [third.id, first.id],
        )
        self.assertEqual(
            [record.id for record in self.store.search_experience(
                "CHN", 1, "price-volume", field_id=" volume "
            )],
            [third.id, first.id],
        )
        self.assertEqual(
            [record.id for record in self.store.search_experience(
                "CHN", 1, "price-volume", field_id="volume_alt"
            )],
            [second.id],
        )
        self.assertEqual(
            [record.id for record in self.store.search_experience(
                "CHN",
                1,
                "price-volume",
                failure_class=" LOW_SHARPE ",
                limit=1,
            )],
            [third.id],
        )
        self.assertEqual(self.store.search_experience("USA", 1, "price-volume"), [])

        with closing(self.store.connect()) as connection:
            before = (
                connection.execute("SELECT COUNT(*) FROM experiences").fetchone()[0],
                connection.execute("SELECT COUNT(*) FROM experience_fields").fetchone()[0],
            )
        for malformed in (
            {**base, "field_ids": ["volume", " "]},
            {**base, "field_ids": ["volume", 1]},
            {**base, "field_ids": "volume"},
        ):
            with self.assertRaises((TypeError, ValueError)):
                self.store.add_experience("run", malformed)
        with closing(self.store.connect()) as connection:
            after = (
                connection.execute("SELECT COUNT(*) FROM experiences").fetchone()[0],
                connection.execute("SELECT COUNT(*) FROM experience_fields").fetchone()[0],
            )
        self.assertEqual(after, before)
        with self.assertRaises((TypeError, ValueError)):
            self.store.search_experience("CHN", 1, "price-volume", limit=True)
        with self.assertRaises((TypeError, ValueError)):
            self.store.search_experience("CHN", 1, "price-volume", limit=0)
        for invalid_delay in (True, -1, 2):
            with self.assertRaises((TypeError, ValueError)):
                self.store.add_experience(
                    "run",
                    {
                        **base,
                        "delay": invalid_delay,
                        "expression_fingerprint": f"invalid-{invalid_delay}",
                    },
                )
            with self.assertRaises((TypeError, ValueError)):
                self.store.search_experience(
                    "CHN", invalid_delay, "price-volume"
                )

    def test_add_experience_rolls_back_parent_when_field_insert_aborts(self) -> None:
        self.create_run()
        payload = {
            "region": "CHN",
            "delay": 1,
            "category": "price-volume",
            "expression_fingerprint": "rollback-expression",
            "field_ids": ["close", "volume"],
            "hypothesis": {"idea": "rollback"},
            "metrics": {"sharpe": 0.5},
        }
        with closing(self.store.connect()) as connection:
            before = (
                connection.execute("SELECT COUNT(*) FROM experiences").fetchone()[0],
                connection.execute("SELECT COUNT(*) FROM experience_fields").fetchone()[0],
            )
            connection.execute(
                "CREATE TRIGGER fail_experience_field "
                "BEFORE INSERT ON experience_fields BEGIN "
                "SELECT RAISE(ABORT, 'forced field failure'); END"
            )
            connection.commit()
        try:
            with self.assertRaisesRegex(sqlite3.IntegrityError, "forced field failure"):
                self.store.add_experience("run", payload)
        finally:
            with closing(self.store.connect()) as connection:
                connection.execute("DROP TRIGGER fail_experience_field")
                connection.commit()

        with closing(self.store.connect()) as connection:
            after = (
                connection.execute("SELECT COUNT(*) FROM experiences").fetchone()[0],
                connection.execute("SELECT COUNT(*) FROM experience_fields").fetchone()[0],
            )
        self.assertEqual(after, before)

    def test_extended_apis_validate_before_db_and_enforce_foreign_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            absent = Path(tmp) / "absent.sqlite3"
            unopened = AgentStore(absent)
            invalid = (
                lambda: unopened.record_research_plan("run", True, "hash", {}),
                lambda: unopened.record_research_plan("run", 1, " ", {}),
                lambda: unopened.record_research_plan(
                    "run", 1, "hash", {"bad": float("nan")}
                ),
                lambda: unopened.get_latest_research_plan(None),
                lambda: unopened.record_operator_task("run", " ", 1, {}),
                lambda: unopened.complete_operator_task("run", "task", "OK", []),
                lambda: unopened.get_operator_task("run", 1),
                lambda: unopened.usage_summary(" "),
                lambda: unopened.record_model_call(
                    "run",
                    ModelRole.PLANNER,
                    WorkflowNode.A,
                    "provider",
                    "model",
                    "purpose",
                    "OK",
                    provider_request_id=" ",
                ),
                lambda: unopened.add_artifact("run", "A", "n", "p", "s"),
                lambda: unopened.add_artifact(
                    "run", WorkflowNode.A, "n", 1, "s"
                ),
                lambda: unopened.add_or_update_artifact(
                    "run", WorkflowNode.A, "n", "", "s"
                ),
                lambda: unopened.get_artifact(True),
                lambda: unopened.reserve_command(
                    "run", WorkflowNode.A, "fingerprint", ["ok", 1]
                ),
                lambda: unopened.mark_command_resource(0, "resource"),
                lambda: unopened.complete_command(1, True),
                lambda: unopened.fail_command(1, " "),
                lambda: unopened.get_command(False),
                lambda: unopened.add_candidate("run", "hash", []),
                lambda: unopened.add_candidate("run", "hash", {}, reason=" "),
                lambda: unopened.get_candidate_by_fingerprint("run", " "),
                lambda: unopened.record_simulation(
                    "run", "sim", "CREATED", candidate_id=True
                ),
                lambda: unopened.update_simulation("run", " ", "OK"),
                lambda: unopened.get_simulation(None, "sim"),
                lambda: unopened.record_diagnosis("run", "failure", "F", {}),
                lambda: unopened.record_approval("run", "alpha", " "),
                lambda: unopened.approval_matches(True, "run", "alpha", "hash"),
                lambda: unopened.find_unconsumed_approval("run", 1, "hash"),
                lambda: unopened.add_experience("run", {"region": "CHN"}),
                lambda: unopened.search_experience("CHN", True, "cat"),
            )
            for operation in invalid:
                with self.subTest(operation=operation):
                    with self.assertRaises((TypeError, ValueError)):
                        operation()
                    self.assertFalse(absent.exists())

        self.create_run("run-a")
        self.create_run("run-b")
        candidate = self.store.add_candidate("run-a", "hash", {"value": 1})
        artifact = self.store.add_artifact(
            "run-a", WorkflowNode.G, "result", "result.json", "sha"
        )
        attempt = self.store.start_node_attempt("run-a", WorkflowNode.F)
        with self.assertRaises(store_module.StoreRecordNotFound):
            self.store.record_simulation(
                "run-b", "cross-candidate", "QUEUED", candidate_id=candidate.id
            )
        with self.assertRaises(store_module.StoreRecordNotFound):
            self.store.record_simulation(
                "run-b", "cross-artifact", "COMPLETE", result_artifact_id=artifact.id
            )
        command = self.store.reserve_command(
            "run-b", WorkflowNode.G, "cross-artifact-command", ["simulate"]
        )
        with self.assertRaises(store_module.StoreRecordNotFound):
            self.store.complete_command(command.id, 0, artifact_id=artifact.id)
        self.assertEqual(self.store.get_command(command.id).status, "STARTED")
        with self.assertRaises(store_module.StoreRecordNotFound):
            self.store.record_operator_task("run-a", "task", 99, {})
        with closing(self.store.connect()) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO approvals(run_id, alpha_id, report_hash) "
                    "VALUES ('missing', 'alpha', 'hash')"
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO command_ledger"
                    "(run_id, node, command_fingerprint, argv_json, status, artifact_id) "
                    "VALUES ('run-a', 'A', 'orphan', '[]', 'STARTED', 999999)"
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO command_ledger"
                    "(run_id, node, command_fingerprint, argv_json, status, artifact_id) "
                    "VALUES ('run-b', 'A', 'cross-run', '[]', 'STARTED', ?)",
                    (artifact.id,),
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO simulations"
                    "(run_id, simulation_id, status, candidate_id) "
                    "VALUES ('run-b', 'cross-candidate-sql', 'QUEUED', ?)",
                    (candidate.id,),
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO simulations"
                    "(run_id, simulation_id, status, result_artifact_id) "
                    "VALUES ('run-b', 'cross-artifact-sql', 'COMPLETE', ?)",
                    (artifact.id,),
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO diagnoses"
                    "(run_id, node_attempt_id, failure_class, next_node, diagnosis_json) "
                    "VALUES ('run-b', ?, 'FAILURE', 'F', '{}')",
                    (attempt.id,),
                )


if __name__ == "__main__":
    unittest.main()
