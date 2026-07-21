from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.request import Request, urlopen

from wqb_cli.agent.store import AgentStore
from wqb_cli.agent.types import Budget, RunConfig, RunState, ScopeMode, WorkflowNode
from wqb_cli.app_server import (
    AppState,
    ResearchDeskServer,
    _normalize_platform_options,
    _redact,
)
from wqb_cli.cli import build_parser
from wqb_cli.core.config_store import load_config


class AppServerTests(unittest.TestCase):
    @staticmethod
    def platform_options_payload() -> dict[str, object]:
        def choices(values: list[object]) -> list[dict[str, object]]:
            return [{"label": str(value), "value": value} for value in values]

        regions = ["USA", "EUR"]
        return {
            "ok": True,
            "response": {
                "status_code": 200,
                "body": {
                    "actions": {
                        "POST": {
                            "settings": {
                                "children": {
                                    "instrumentType": {"type": "choice", "choices": choices(["EQUITY"])},
                                    "region": {
                                        "type": "choice",
                                        "choices": {"instrumentType": {"EQUITY": choices(regions)}},
                                    },
                                    "delay": {
                                        "type": "choice",
                                        "choices": {"instrumentType": {"EQUITY": {"region": {
                                            "USA": choices([1, 0]), "EUR": choices([1, 0]),
                                        }}}},
                                    },
                                    "universe": {
                                        "type": "choice",
                                        "choices": {"instrumentType": {"EQUITY": {"region": {
                                            "USA": choices(["TOP3000", "TOP1000"]),
                                            "EUR": choices(["TOP2500", "TOP1200"]),
                                        }}}},
                                    },
                                    "neutralization": {
                                        "type": "choice",
                                        "choices": {"instrumentType": {"EQUITY": {"region": {
                                            "USA": choices(["NONE", "FAST"]),
                                            "EUR": choices(["NONE", "COUNTRY"]),
                                        }}}},
                                    },
                                    "decay": {
                                        "label": "Decay", "type": "integer", "required": True,
                                        "minValue": 0, "maxValue": 512,
                                    },
                                }
                            }
                        }
                    }
                },
            },
        }

    @patch("wqb_cli.app_server.WqbClient")
    @patch("wqb_cli.app_server.EndpointRegistry.load")
    def test_auth_status_treats_204_as_unauthenticated(
        self, load_registry: Mock, client_class: Mock
    ) -> None:
        load_registry.return_value = Mock()
        client = Mock()
        client.call.return_value = {
            "ok": True,
            "response": {"status_code": 204, "reason": "No Content"},
        }
        client_class.return_value = client

        with tempfile.TemporaryDirectory() as tmp:
            app = AppState(
                database_path=str(Path(tmp) / "agent" / "agent.sqlite3"),
                run_root=str(Path(tmp) / "runs"),
            )
            result = app.auth_status()

        self.assertTrue(result["ok"])
        self.assertFalse(result["authenticated"])

    def test_platform_options_parser_preserves_dependent_scope_choices(self) -> None:
        result = _normalize_platform_options(self.platform_options_payload())

        self.assertEqual([item["value"] for item in result["regions"]], ["USA", "EUR"])
        self.assertEqual([item["value"] for item in result["delays"]["USA"]], [1, 0])
        self.assertEqual(
            [item["value"] for item in result["universes"]["EUR"]],
            ["TOP2500", "TOP1200"],
        )
        self.assertEqual(
            [item["value"] for item in result["neutralizations"]["USA"]],
            ["NONE", "FAST"],
        )
        decay = next(item for item in result["settings_catalog"] if item["name"] == "decay")
        self.assertEqual((decay["min_value"], decay["max_value"]), (0, 512))

    @patch("wqb_cli.app_server.WqbClient")
    @patch("wqb_cli.app_server.EndpointRegistry.load")
    def test_platform_options_are_cached_after_live_fetch(
        self, load_registry: Mock, client_class: Mock
    ) -> None:
        registry = Mock()
        registry.get.return_value = Mock()
        load_registry.return_value = registry
        client = Mock()
        client.prepare.return_value = Mock()
        client.call.return_value = self.platform_options_payload()
        client_class.return_value = client

        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "agent" / "agent.sqlite3"
            app = AppState(database_path=str(database), run_root=tmp)
            result = app.simulation_options(refresh=True)
            cache = database.parent / "platform_simulation_options.json"
            cache_exists = cache.exists()

            restarted = AppState(database_path=str(database), run_root=tmp)
            cached = restarted.simulation_options()

        self.assertEqual(result["source"], "platform")
        self.assertTrue(cache_exists)
        self.assertEqual(cached["source"], "local_cache")
        self.assertEqual(cached["scope"]["universes"]["USA"][0]["value"], "TOP3000")
        client.call.assert_called_once()

    @patch("wqb_cli.app_server.WqbClient")
    @patch("wqb_cli.app_server.EndpointRegistry.load")
    def test_platform_auth_failure_uses_complete_bundled_scope_fallback(
        self, load_registry: Mock, client_class: Mock
    ) -> None:
        registry = Mock()
        registry.get.return_value = Mock()
        load_registry.return_value = registry
        client = Mock()
        client.prepare.return_value = Mock()
        client.call.return_value = {"ok": False, "response": {"status_code": 401}}
        client_class.return_value = client

        with tempfile.TemporaryDirectory() as tmp:
            app = AppState(
                database_path=str(Path(tmp) / "agent" / "agent.sqlite3"),
                run_root=str(Path(tmp) / "runs"),
            )
            result = app.simulation_options(refresh=True)

        self.assertEqual(result["source"], "bundled_fallback")
        self.assertEqual(result["refresh_status"], "authentication_required")
        self.assertEqual(len(result["scope"]["regions"]), 8)
        self.assertEqual(
            [item["value"] for item in result["scope"]["universes"]["CHN"]],
            ["TOP2000U"],
        )

    def test_app_cli_defaults_to_loopback(self) -> None:
        args = build_parser().parse_args(["app", "--no-open"])
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 8765)
        self.assertTrue(args.no_open)

    def test_app_rejects_non_loopback_bind(self) -> None:
        from wqb_cli.commands.app import handle_app

        args = build_parser().parse_args(["app", "--host", "0.0.0.0", "--no-open"])
        with self.assertRaisesRegex(ValueError, "host"):
            handle_app(args)

    @patch("wqb_cli.app_server.AppState._ensure_models_ready")
    @patch("wqb_cli.app_server.build_runtime")
    def test_create_run_waits_until_background_registration(
        self, build_runtime: Mock, ensure_models_ready: Mock
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "agent.sqlite3"
            app = AppState(database_path=str(database), run_root=tmp)

            def delayed_run(*, run_id: str, scope: RunConfig) -> None:
                time.sleep(0.08)
                store = app.store()
                store.create_run(run_id, scope)
                store.transition(run_id, RunState.RUNNING, "test registered")

            runtime = Mock()
            runtime.run_manual.side_effect = delayed_run
            build_runtime.return_value = runtime
            app.dataset_options = Mock(return_value={
                "ok": True,
                "datasets": [{"id": "price_volume", "label": "Price Volume"}],
            })

            result = app.create_run(
                {
                    "scope_mode": "manual",
                    "region": "USA",
                    "delay": 1,
                    "universe": "TOP1000",
                    "neutralization": "FAST",
                    "dataset_id": "price_volume",
                    "max_rounds": 3,
                    "max_simulations": 12,
                }
            )

            run = app.store().get_run(str(result["run_id"]))
            deadline = time.monotonic() + 2
            while app.job(str(result["run_id"]))["state"] != "COMPLETED" and time.monotonic() < deadline:
                time.sleep(0.01)
            finished_run = app.store().get_run(str(result["run_id"]))

        self.assertIn(run.state, {RunState.CREATED, RunState.RUNNING})
        self.assertEqual(finished_run.state, RunState.RUNNING)
        self.assertEqual(run.config.budget.rounds, 3)
        self.assertEqual(run.config.budget.total_simulations, 12)
        self.assertIn(result["job"]["state"], {"RUNNING", "COMPLETED"})
        app.dataset_options.assert_called_once_with(
            region="USA", delay=None, universe=None
        )

    @patch("wqb_cli.app_server.AppState._ensure_models_ready")
    @patch("wqb_cli.app_server.build_runtime")
    def test_create_auto_run_preserves_region_without_pinning_other_scope_fields(
        self, build_runtime: Mock, ensure_models_ready: Mock
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = AppState(database_path=str(Path(tmp) / "agent.sqlite3"), run_root=tmp)

            def register_auto(*, run_id: str, config: RunConfig) -> None:
                store = app.store()
                store.create_run(run_id, config)
                store.transition(run_id, RunState.RUNNING, "test registered")

            runtime = Mock()
            runtime.run_auto.side_effect = register_auto
            build_runtime.return_value = runtime
            result = app.create_run({
                "scope_mode": "auto", "region": "USA", "dataset_id": "analyst4",
                "max_rounds": 3, "max_simulations": 12,
            })
            run = app.store().get_run(str(result["run_id"]))
            deadline = time.monotonic() + 2
            while app.job(str(result["run_id"]))["state"] != "COMPLETED" and time.monotonic() < deadline:
                time.sleep(0.01)

        self.assertEqual(run.config.scope_mode, ScopeMode.AUTO)
        self.assertEqual(run.config.region, "USA")
        self.assertIsNone(run.config.delay)
        self.assertIsNone(run.config.universe)
        self.assertIsNone(run.config.neutralization)
        self.assertEqual(run.config.dataset_id, "analyst4")
        runtime.run_auto.assert_called_once()

    def test_dataset_rows_expose_platform_category_for_auto_filtering(self) -> None:
        rows = AppState._dataset_rows({
            "response": {"body": {"results": [
                {"id": "analyst4", "name": "Analyst 4", "category": {"id": "analyst", "name": "Analyst"}},
                {"id": "model7", "description": "Model 7", "category": "model"},
            ]}}
        })
        self.assertEqual(rows, [
            {"id": "analyst4", "label": "Analyst 4", "category": "analyst"},
            {"id": "model7", "label": "Model 7", "category": "model"},
        ])

    @patch("wqb_cli.app_server.WqbClient")
    @patch("wqb_cli.app_server.EndpointRegistry.load")
    def test_auto_dataset_options_uses_selected_region_catalog_scope(
        self, load_registry: Mock, client_class: Mock
    ) -> None:
        client = Mock()
        client_class.return_value = client
        response = lambda identifier, category: {"ok": True, "response": {"body": {"results": [
            {"id": identifier, "name": identifier, "category": {"id": category}},
        ]}}}
        client.call.return_value = response("analyst4", "analyst")
        with tempfile.TemporaryDirectory() as tmp:
            app = AppState(database_path=str(Path(tmp) / "agent.sqlite3"), run_root=tmp)
            app.simulation_options = Mock(return_value={"scope": {
                "delays": {"USA": [{"value": 0}, {"value": 1}]},
                "universes": {"USA": [{"value": "TOP1000"}, {"value": "TOP3000"}]},
            }})
            result = app.dataset_options(region="USA", delay=None, universe=None)

        self.assertEqual(
            [row["id"] for row in result["datasets"]], ["analyst4"],
        )
        self.assertEqual(client.prepare.call_count, 1)
        for call in client.prepare.call_args_list:
            params = call.kwargs["params"]
            self.assertEqual(params["region"], "USA")
            self.assertEqual(params["delay"], "0")
            self.assertEqual(params["universe"], "TOP1000")

    def test_dataset_scope_rows_fetches_every_platform_page(self) -> None:
        client, registry = Mock(), Mock()
        client.call.side_effect = [
            {"ok": True, "response": {"body": {"count": 51, "results": [
                {"id": "analyst4", "category": "analyst"},
            ]}}},
            {"ok": True, "response": {"body": {"count": 51, "results": [
                {"id": "model7", "category": "model"},
            ]}}},
        ]

        rows, complete = AppState._dataset_scope_rows(
            client, registry, "USA", 1, "TOP3000"
        )

        self.assertTrue(complete)
        self.assertEqual([row["id"] for row in rows], ["analyst4", "model7"])
        self.assertEqual(
            [call.kwargs["params"]["offset"] for call in client.prepare.call_args_list],
            ["0", "50"],
        )

    def test_redaction_keeps_usage_tokens_but_removes_secrets(self) -> None:
        value = _redact({"input_tokens": 123, "api_key": "secret", "nested": {"password": "pw"}})
        self.assertEqual(value["input_tokens"], 123)
        self.assertEqual(value["api_key"], "[REDACTED]")
        self.assertEqual(value["nested"]["password"], "[REDACTED]")

    def test_model_settings_persist_without_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            app = AppState(
                config_path_value=str(config_path),
                database_path=str(Path(tmp) / "agent.sqlite3"),
            )

            result = app.update_model(
                "planner",
                {
                    "provider": "openai-compatible",
                    "api_style": "chat_completions",
                    "model": "planner-large",
                    "base_url": "https://models.example.test/v1",
                    "reasoning": "high",
                    "structured_outputs": False,
                },
            )
            stored = load_config(str(config_path))
            serialized = config_path.read_text(encoding="utf-8")

        self.assertEqual(result["model"]["model"], "planner-large")
        self.assertEqual(stored["agent"]["models"]["planner"]["base_url"], "https://models.example.test/v1")
        self.assertNotIn("api_key", serialized.lower())

    @patch("wqb_cli.app_server.set_named_secret", return_value={"ok": True})
    def test_model_key_is_written_only_to_keyring(self, set_named_secret: Mock) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            app = AppState(config_path_value=str(config_path))

            result = app.update_model_key("operator", {"key": "operator-secret"})

            serialized = config_path.read_text(encoding="utf-8") if config_path.exists() else ""

        set_named_secret.assert_called_once_with("agent-operator-api-key", "operator-secret")
        self.assertNotIn("operator-secret", serialized)
        self.assertNotIn("operator-secret", repr(result))

    @patch("wqb_cli.app_server.set_secret", return_value={"ok": True})
    @patch("wqb_cli.app_server.save_cookie_payload")
    @patch("wqb_cli.app_server.WqbClient")
    @patch("wqb_cli.app_server.EndpointRegistry.load")
    def test_auth_login_does_not_persist_or_return_password(
        self, load_registry: Mock, client_class: Mock, save_cookies: Mock, set_secret: Mock
    ) -> None:
        registry = Mock()
        registry.get.return_value = Mock()
        load_registry.return_value = registry
        client = Mock()
        client.registry = registry
        client.prepare.return_value = Mock()
        client.call.return_value = {
            "ok": True,
            "request": {"password": "account-secret"},
            "response": {"token": "session-token"},
        }
        client_class.return_value = client

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            app = AppState(config_path_value=str(config_path))

            result = app.auth_login(
                {"email": "researcher@example.test", "password": "account-secret", "expiry": 3600}
            )
            stored = load_config(str(config_path))
            serialized = config_path.read_text(encoding="utf-8")

        self.assertEqual(stored["auth"]["email"], "researcher@example.test")
        self.assertNotIn("account-secret", serialized)
        self.assertEqual(result["request"]["password"], "[REDACTED]")
        self.assertEqual(result["response"]["token"], "[REDACTED]")
        save_cookies.assert_called_once()
        set_secret.assert_called_once_with("wqb-cli", "researcher@example.test", "account-secret")
        self.assertEqual(stored["auth"]["keyring_username"], "researcher@example.test")

    def test_automatic_login_resumes_a_paused_run_twice_at_most(self) -> None:
        app = AppState()
        runtime = Mock()
        paused = SimpleNamespace(state=RunState.NEEDS_AUTH)
        resumed = SimpleNamespace(state=RunState.RUNNING)
        app.auto_login = Mock(return_value={"ok": True})
        runtime.coordinator.resume.return_value = resumed

        result = app._resume_after_automatic_login(runtime, "run-test", paused)

        self.assertIs(result, resumed)
        app.auto_login.assert_called_once_with()
        runtime.coordinator.resume.assert_called_once_with("run-test")

    def test_run_detail_projects_candidate_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "agent.sqlite3"
            store = AgentStore(database)
            store.initialize()
            store.create_run(
                "run-test",
                RunConfig(scope_mode=ScopeMode.AUTO, budget=Budget(rounds=3, total_simulations=9)),
            )
            store.transition("run-test", RunState.RUNNING, "test")
            accepted = store.add_candidate("run-test", "accepted", {"expression": "ts_delta(close, 5)"})
            store.add_candidate("run-test", "rejected", {"raw_candidate": {"expression": "close"}}, status="REJECTED", reason="raw field")
            store.record_simulation("run-test", "sim-1", "COMPLETE", candidate_id=accepted.id, alpha_id="alpha-1")
            attempt = store.start_node_attempt("run-test", WorkflowNode.K)
            store.finish_node_attempt(attempt, "COMPLETED", {"decision": "retry"})

            app = AppState(database_path=str(database), run_root=tmp)
            detail = app.run_detail("run-test")

        states = {item["pipeline_state"] for item in detail["candidates"]}
        self.assertEqual(states, {"REJECTED", "EVALUATED"})
        self.assertEqual(detail["termination"]["actual_simulations"], 1)

    def test_run_detail_and_controls_expose_idea_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "agent.sqlite3"
            store = AgentStore(database)
            store.initialize()
            store.create_run("run-test", RunConfig(scope_mode=ScopeMode.AUTO))
            mechanisms = [{"mechanism_id": "m1", "hypothesis": "price change", "field_ids": ["close"]}]
            store.record_research_plan(
                "run-test", 1, "plan-hash", {"mechanisms": mechanisms}
            )
            store.sync_research_ideas("run-test", 1, "plan-hash", mechanisms)
            attempt = store.begin_idea_attempt("run-test", "p1:m1", "INSPECT")
            store.finish_idea_attempt(
                attempt, "FAILED", "ERROR", error="empty expressions"
            )
            app = AppState(database_path=str(database), run_root=tmp)

            detail = app.run_detail("run-test")
            retried = app.retry_idea("run-test", "p1:m1")
            aborted = app.abort_idea("run-test", "p1:m1")

        self.assertEqual(detail["ideas"][0]["status"], "ERROR")
        self.assertEqual(detail["ideas"][0]["last_error"], "empty expressions")
        self.assertEqual(detail["idea_attempts"][0]["status"], "FAILED")
        self.assertEqual(retried["status"], "PENDING_INSPECT")
        self.assertEqual(aborted["status"], "ABORTED")

    def test_run_detail_compacts_attempt_payload_and_supports_full_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "agent.sqlite3"
            store = AgentStore(database)
            store.initialize()
            store.create_run("run-test", RunConfig(scope_mode=ScopeMode.AUTO))
            store.transition("run-test", RunState.RUNNING, "test")
            marker = "large-raw-marker"
            attempt = store.start_node_attempt("run-test", WorkflowNode.J)
            store.finish_node_attempt(
                attempt,
                "COMPLETED",
                {
                    "simulations": 8,
                    "_coordinator": {
                        "node": "J",
                        "next_node": "K",
                        "payload": {
                            "alpha_results": [{"raw": marker * 20_000}]
                        },
                    },
                },
            )
            app = AppState(database_path=str(database), run_root=tmp)

            compact = app.run_detail("run-test")
            full = app.run_detail("run-test", full=True)

        compact_json = json.dumps(compact)
        full_json = json.dumps(full)
        self.assertNotIn(marker, compact_json)
        self.assertIn(marker, full_json)
        self.assertLess(len(compact_json), len(full_json) // 10)
        self.assertEqual(compact["timeline"][0]["summary"]["simulations"], 8)
        self.assertEqual(
            compact["timeline"][0]["summary"]["_coordinator"]["next_node"],
            "K",
        )
        self.assertEqual(
            compact["node_attempt_counts"],
            [{"node": "J", "status": "COMPLETED", "count": 1}],
        )

    def test_failed_k_is_projected_as_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "agent.sqlite3"
            store = AgentStore(database)
            store.initialize()
            store.create_run("run-test", RunConfig(scope_mode=ScopeMode.AUTO))
            store.transition("run-test", RunState.RUNNING, "test")
            attempt = store.start_node_attempt("run-test", WorkflowNode.K)
            store.finish_node_attempt(attempt, "FAILED", {"failure": "TypeError"})
            store.transition("run-test", RunState.FAILED, "node K failed")

            detail = AppState(
                database_path=str(database), run_root=tmp
            ).run_detail("run-test")

        self.assertTrue(detail["recoverable"])
        self.assertEqual(detail["failed_node"], "K")
        self.assertEqual(detail["next_action"], "resume_failed_node")

    def test_failed_h_is_projected_as_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "agent.sqlite3"
            store = AgentStore(database)
            store.initialize()
            store.create_run("run-test", RunConfig(scope_mode=ScopeMode.AUTO))
            store.transition("run-test", RunState.RUNNING, "test")
            attempt = store.start_node_attempt("run-test", WorkflowNode.H)
            store.finish_node_attempt(attempt, "FAILED", {"failure": "ModelReadTimeoutError"})
            store.transition("run-test", RunState.FAILED, "node H failed")

            detail = AppState(
                database_path=str(database), run_root=tmp
            ).run_detail("run-test")

        self.assertTrue(detail["recoverable"])
        self.assertEqual(detail["failed_node"], "H")
        self.assertEqual(detail["next_action"], "resume_failed_node")

    def test_failed_f_is_projected_as_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "agent.sqlite3"
            store = AgentStore(database)
            store.initialize()
            store.create_run("run-test", RunConfig(scope_mode=ScopeMode.AUTO))
            store.transition("run-test", RunState.RUNNING, "test")
            attempt = store.start_node_attempt("run-test", WorkflowNode.F)
            store.finish_node_attempt(attempt, "FAILED", {"failure": "EvidenceError"})
            store.transition("run-test", RunState.FAILED, "node F failed")

            detail = AppState(
                database_path=str(database), run_root=tmp
            ).run_detail("run-test")

        self.assertTrue(detail["recoverable"])
        self.assertEqual(detail["failed_node"], "F")
        self.assertEqual(detail["next_action"], "resume_failed_node")

    def test_stop_run_marks_active_research_stopped_and_blocks_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "agent.sqlite3"
            store = AgentStore(database)
            store.initialize()
            store.create_run("run-test", RunConfig(scope_mode=ScopeMode.AUTO))
            store.transition("run-test", RunState.RUNNING, "test")
            app = AppState(database_path=str(database), run_root=tmp)

            result = app.stop_run("run-test")
            stopped = store.get_run("run-test")

            with self.assertRaisesRegex(ValueError, "terminal"):
                app.resume_run("run-test")

        self.assertEqual(result["state"], "STOPPED")
        self.assertEqual(stopped.state, RunState.STOPPED)

    def test_budget_finalization_is_projected_as_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "agent.sqlite3"
            store = AgentStore(database)
            store.initialize()
            store.create_run("run-test", RunConfig(scope_mode=ScopeMode.AUTO))
            store.transition("run-test", RunState.RUNNING, "test")
            attempt = store.start_node_attempt("run-test", WorkflowNode.J)
            store.finish_node_attempt(
                attempt,
                "COMPLETED",
                {"_coordinator": {"next_node": "K", "payload": {}}},
            )
            store.transition(
                "run-test", RunState.BUDGET_EXHAUSTED, "budget reached"
            )

            detail = AppState(
                database_path=str(database), run_root=tmp
            ).run_detail("run-test")

        self.assertTrue(detail["recoverable"])
        self.assertEqual(detail["next_action"], "resume_budget_finalization")

    def test_health_and_static_assets_are_served(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "assets"
            root.mkdir()
            (root / "index.html").write_text("<!doctype html><title>test</title>", encoding="utf-8")
            (root / "app.js").write_text("'use strict';", encoding="utf-8")
            (root / "styles.css").write_text("body{}", encoding="utf-8")
            state = AppState(database_path=str(Path(tmp) / "agent.sqlite3"), asset_root=root)
            server = ResearchDeskServer(("127.0.0.1", 0), state)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                with urlopen(base + "/api/health", timeout=5) as response:
                    self.assertTrue(json.load(response)["ok"])
                with urlopen(base + "/", timeout=5) as response:
                    self.assertIn(b"<title>test</title>", response.read())
            finally:
                server.shutdown()
                server.server_close()

    def test_mutating_http_routes_delegate_to_app_state(self) -> None:
        app = Mock()
        app.create_run.return_value = {"ok": True, "run_id": "run-1"}
        app.resume_run.return_value = {"ok": True, "run_id": "run-1"}
        app.approve_run.return_value = {"ok": True, "run_id": "run-1"}
        app.reject_run.return_value = {"ok": True, "run_id": "run-1", "state": "REJECTED"}
        app.retry_idea.return_value = {"ok": True, "idea_id": "p1:m1"}
        app.abort_idea.return_value = {"ok": True, "idea_id": "p1:m1"}
        app.update_model.return_value = {"ok": True}
        app.update_model_key.return_value = {"ok": True}
        server = ResearchDeskServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"

        def request(path: str, method: str, body: dict[str, object]) -> tuple[int, dict[str, object]]:
            payload = json.dumps(body).encode("utf-8")
            with urlopen(
                Request(
                    base + path,
                    data=payload,
                    method=method,
                    headers={"Content-Type": "application/json"},
                ),
                timeout=5,
            ) as response:
                return response.status, json.load(response)

        try:
            self.assertEqual(request("/api/runs", "POST", {"scope_mode": "auto"})[0], 202)
            self.assertEqual(request("/api/runs/run-1/resume", "POST", {})[0], 202)
            self.assertEqual(request("/api/runs/run-1/approve", "POST", {})[0], 202)
            self.assertEqual(request("/api/runs/run-1/reject", "POST", {"reason": "no"})[0], 200)
            self.assertEqual(request("/api/runs/run-1/ideas/p1:m1/retry", "POST", {})[0], 202)
            self.assertEqual(request("/api/runs/run-1/ideas/p1:m1/abort", "POST", {})[0], 202)
            self.assertEqual(request("/api/models/planner", "PUT", {"model": "large"})[0], 200)
            self.assertEqual(request("/api/models/operator/key", "PUT", {"key": "secret"})[0], 200)
        finally:
            server.shutdown()
            server.server_close()

        app.create_run.assert_called_once_with({"scope_mode": "auto"})
        app.resume_run.assert_called_once_with("run-1")
        app.approve_run.assert_called_once_with("run-1")
        app.reject_run.assert_called_once_with("run-1", "no")
        app.retry_idea.assert_called_once_with("run-1", "p1:m1")
        app.abort_idea.assert_called_once_with("run-1", "p1:m1")
        app.update_model.assert_called_once_with("planner", {"model": "large"})
        app.update_model_key.assert_called_once_with("operator", {"key": "secret"})


if __name__ == "__main__":
    unittest.main()
