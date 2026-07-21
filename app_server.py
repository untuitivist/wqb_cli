from __future__ import annotations

import json
import mimetypes
import re
import threading
import time
import traceback
import webbrowser
from copy import deepcopy
from contextlib import closing
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import unquote, urlparse
from urllib.parse import parse_qs

from .agent.config import (
    AgentConfig,
    ModelConfig,
    load_agent_config,
    validate_agent_config,
)
from .agent.coordinator import RECOVERABLE_FAILED_NODES
from .agent.store import AgentStore, RunNotFound, StoreRecordNotFound
from .agent.types import ModelRole, RunConfig, RunState
from .commands.agent import _model_projection, status_projection
from .commands.agent_runtime import build_runtime, build_submission_runtime
from .core.auth import (
    load_cookie_payload,
    resolve_login_payload,
    save_cookie_payload,
    session_from_cookies,
)
from .core.client import WqbClient
from .core.config_store import config_path, load_config, save_config
from .core.registry import EndpointRegistry
from .core.secrets import set_named_secret, set_secret


APP_ASSET_ROOT = Path(__file__).resolve().parent / "docs" / "ui-prototype"
_JSON_COLUMNS = {
    "summary_json": "summary",
    "diagnosis_json": "diagnosis",
    "candidate_json": "candidate",
    "idea_json": "idea",
    "detail_json": "detail",
}
_TERMINAL_STATES = {
    RunState.SUBMITTED.value,
    RunState.REJECTED.value,
    RunState.FAILED.value,
    RunState.BUDGET_EXHAUSTED.value,
    RunState.NO_PROGRESS.value,
    RunState.STOPPED.value,
}
_PLATFORM_OPTIONS_CACHE_SECONDS = 6 * 60 * 60
_PLATFORM_OPTIONS_SCHEMA_VERSION = 1
_CHOICE_LABELS = {
    "NONE": "None",
    "REVERSION_AND_MOMENTUM": "RAM",
    "STATISTICAL": "Statistical",
    "CROWDING": "Crowding Factors",
    "FAST": "Fast Factors",
    "SLOW": "Slow Factors",
    "MARKET": "Market",
    "SECTOR": "Sector",
    "INDUSTRY": "Industry",
    "SUBINDUSTRY": "Subindustry",
    "COUNTRY": "Country / Region",
    "SLOW_AND_FAST": "Slow + Fast Factors",
}
_BUNDLED_SCOPE_OPTIONS = {
    "instrument_type": "EQUITY",
    "regions": ["USA", "GLB", "EUR", "ASI", "CHN", "AMR", "IND", "MEA"],
    "delays": {
        "USA": [1, 0], "GLB": [1], "EUR": [1, 0], "ASI": [1],
        "CHN": [0, 1], "AMR": [1, 0], "IND": [1], "MEA": [1],
    },
    "universes": {
        "USA": ["TOP3000", "TOP2000", "TOP1000", "TOP500", "TOP200", "ILLIQUID_MINVOL1M", "TOPSP500"],
        "GLB": ["TOP3000", "MINVOL1M", "MINVOL10M", "TOPDIV3000"],
        "EUR": ["TOP2500", "TOP1200", "TOP800", "TOP400", "ILLIQUID_MINVOL1M", "TOPCS1600"],
        "ASI": ["MINVOL1M", "MINVOL10M", "ILLIQUID_MINVOL1M", "TOP500"],
        "CHN": ["TOP2000U"], "AMR": ["TOP600"], "IND": ["TOP500"],
        "MEA": ["TOP400", "TOP300"],
    },
    "neutralizations": {
        "USA": ["NONE", "REVERSION_AND_MOMENTUM", "STATISTICAL", "CROWDING", "FAST", "SLOW", "MARKET", "SECTOR", "INDUSTRY", "SUBINDUSTRY", "SLOW_AND_FAST"],
        "GLB": ["NONE", "REVERSION_AND_MOMENTUM", "STATISTICAL", "CROWDING", "FAST", "SLOW", "MARKET", "SECTOR", "INDUSTRY", "SUBINDUSTRY", "COUNTRY", "SLOW_AND_FAST"],
        "EUR": ["NONE", "REVERSION_AND_MOMENTUM", "STATISTICAL", "CROWDING", "FAST", "SLOW", "MARKET", "SECTOR", "INDUSTRY", "SUBINDUSTRY", "COUNTRY", "SLOW_AND_FAST"],
        "ASI": ["NONE", "REVERSION_AND_MOMENTUM", "STATISTICAL", "CROWDING", "FAST", "SLOW", "MARKET", "SECTOR", "INDUSTRY", "SUBINDUSTRY", "COUNTRY", "SLOW_AND_FAST"],
        "CHN": ["NONE", "REVERSION_AND_MOMENTUM", "STATISTICAL", "CROWDING", "FAST", "SLOW", "MARKET", "SECTOR", "INDUSTRY", "SUBINDUSTRY", "SLOW_AND_FAST"],
        "AMR": ["NONE", "STATISTICAL", "MARKET", "SECTOR", "INDUSTRY", "SUBINDUSTRY", "COUNTRY"],
        "IND": ["NONE", "REVERSION_AND_MOMENTUM", "STATISTICAL", "CROWDING", "FAST", "SLOW", "MARKET", "SECTOR", "INDUSTRY", "SUBINDUSTRY", "SLOW_AND_FAST"],
        "MEA": ["NONE", "MARKET", "SECTOR", "INDUSTRY", "SUBINDUSTRY", "COUNTRY"],
    },
}


@dataclass
class JobRecord:
    run_id: str
    action: str
    state: str = "QUEUED"
    started_at: str | None = None
    finished_at: str | None = None
    error_type: str | None = None
    detail: str | None = None

    def projection(self) -> dict[str, object]:
        return asdict(self)


class AppState:
    def __init__(
        self,
        *,
        config_path_value: str | None = None,
        database_path: str | None = None,
        run_root: str | None = None,
        registry_path: str | None = None,
        cookie_path: str | None = None,
        asset_root: Path | None = None,
    ) -> None:
        self.config_path = config_path_value
        self.database_override = database_path
        self.run_root_override = run_root
        self.registry_path = registry_path
        self.cookie_path = cookie_path
        self.asset_root = (asset_root or APP_ASSET_ROOT).resolve()
        self.jobs: dict[str, JobRecord] = {}
        self._jobs_lock = threading.Lock()
        self._platform_options: dict[str, object] | None = None
        self._platform_options_lock = threading.Lock()

    def config(self) -> AgentConfig:
        config = load_agent_config(self.config_path, require_models=False)
        if self.database_override:
            config = replace(config, database_path=Path(self.database_override))
        if self.run_root_override:
            config = replace(config, run_root=Path(self.run_root_override))
        return config

    def store(self) -> AgentStore:
        store = AgentStore(self.config().database_path)
        store.initialize()
        return store

    def bootstrap(self) -> dict[str, object]:
        config = self.config()
        raw = load_config(self.config_path)
        cookies = load_cookie_payload(self.cookie_path).get("cookies") or {}
        return {
            "ok": True,
            "app": {"name": "WQB Research Desk", "api_version": 1},
            "config_path": str(config_path(self.config_path)),
            "database_path": str(config.database_path),
            "run_root": str(config.run_root),
            "auth": {
                "email": str(raw.get("auth", {}).get("email") or ""),
                "cookie_present": bool(cookies),
            },
            "models": [_app_model_projection(role, config) for role in ModelRole],
            "defaults": deepcopy(raw.get("defaults", {})),
            "budget": {
                "max_rounds": config.budget.rounds,
                "max_simulations": config.budget.total_simulations,
            },
        }

    def list_runs(self, limit: int = 100) -> dict[str, object]:
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        store = self.store()
        with closing(store.connect()) as connection:
            rows = connection.execute(
                "SELECT run_id FROM runs ORDER BY created_at DESC, run_id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return {
            "ok": True,
            "runs": [self.run_summary(store, str(row["run_id"])) for row in rows],
        }

    def run_summary(self, store: AgentStore, run_id: str) -> dict[str, object]:
        result = status_projection(store, run_id)
        run = store.get_run(run_id)
        failed_node = (
            store.latest_failed_node(run_id)
            if run.state is RunState.FAILED
            else None
        )
        budget_finalization_node = (
            store.budget_finalization_node(run_id)
            if run.state is RunState.BUDGET_EXHAUSTED
            else None
        )
        recoverable = (
            failed_node in RECOVERABLE_FAILED_NODES
            or budget_finalization_node is not None
        )
        result["created_at"] = run.created_at
        result["updated_at"] = run.updated_at
        result["job"] = self.job(run_id)
        result["failed_node"] = None if failed_node is None else failed_node.value
        result["recoverable"] = recoverable
        if budget_finalization_node is not None:
            result["next_action"] = "resume_budget_finalization"
        elif recoverable:
            result["next_action"] = "resume_failed_node"
        return result

    def run_detail(self, run_id: str, *, full: bool = False) -> dict[str, object]:
        store = self.store()
        base = self.run_summary(store, run_id)
        with closing(store.connect()) as connection:
            attempts = self._rows(
                connection,
                (
                    "SELECT id,node,attempt_number,status,summary_json,"
                    "started_at,finished_at FROM node_attempts WHERE run_id=? "
                    "ORDER BY id"
                    if full
                    else "SELECT id,node,attempt_number,status,summary_json,"
                    "started_at,finished_at FROM (SELECT id,node,attempt_number,"
                    "status,summary_json,started_at,finished_at FROM node_attempts "
                    "WHERE run_id=? ORDER BY id DESC LIMIT 100) ORDER BY id"
                ),
                (run_id,),
            )
            attempt_counts = self._rows(
                connection,
                "SELECT node,status,COUNT(*) AS count FROM node_attempts "
                "WHERE run_id=? GROUP BY node,status ORDER BY node,status",
                (run_id,),
            )
            candidates = self._rows(
                connection,
                "SELECT id,expression_fingerprint,candidate_json,status,reason,created_at,updated_at "
                "FROM candidates WHERE run_id=? ORDER BY id",
                (run_id,),
            )
            simulations = self._rows(
                connection,
                "SELECT id,candidate_id,simulation_id,alpha_id,status,result_artifact_id,created_at,updated_at "
                "FROM simulations WHERE run_id=? ORDER BY id",
                (run_id,),
            )
            artifacts = self._rows(
                connection,
                "SELECT id,node,name,kind,sha256,created_at,updated_at "
                "FROM artifacts WHERE run_id=? ORDER BY id DESC"
                + ("" if full else " LIMIT 80"),
                (run_id,),
            )
            diagnoses = self._rows(
                connection,
                "SELECT id,node_attempt_id,failure_class,next_node,diagnosis_json,created_at "
                "FROM diagnoses WHERE run_id=? ORDER BY id",
                (run_id,),
            )
            model_calls = self._rows(
                connection,
                "SELECT id,role,node,provider,model,purpose,status,input_tokens,output_tokens,"
                "cost_usd,latency_ms,fallback_used,error,created_at "
                "FROM model_calls WHERE run_id=? ORDER BY id",
                (run_id,),
            )
            commands = self._rows(
                connection,
                "SELECT id,node,status,exit_code,resource_id,error,created_at,updated_at "
                "FROM command_ledger WHERE run_id=? ORDER BY id DESC LIMIT 200",
                (run_id,),
            )
            approvals = self._rows(
                connection,
                "SELECT id,alpha_id,report_hash,decision,reason,consumed_at,created_at "
                "FROM approvals WHERE run_id=? ORDER BY id DESC",
                (run_id,),
            )
            ideas = self._rows(
                connection,
                "SELECT id,idea_id,plan_version,plan_hash,status,stage,idea_json,"
                "retry_count,last_error,next_retry_at,abort_requested,created_at,updated_at "
                "FROM research_ideas WHERE run_id=? ORDER BY id",
                (run_id,),
            )
            idea_attempts = self._rows(
                connection,
                "SELECT id,idea_id,stage,attempt_number,status,detail_json,error,"
                "started_at,finished_at FROM idea_attempts WHERE run_id=? ORDER BY id",
                (run_id,),
            )

        plan = store.get_latest_research_plan(run_id)
        artifact_payloads = {
            name: self._latest_artifact_payload(store, run_id, name)
            for name in (
                "best_alpha_candidates.json",
                "template_density.json",
                "anti_patterns.json",
                "diagnosis.json",
                "final_report.json",
            )
        }
        evaluated = artifact_payloads["best_alpha_candidates.json"] or {}
        ranked = evaluated.get("candidates", []) if isinstance(evaluated, Mapping) else []
        simulations = self._enrich_legacy_simulations(store, run_id, simulations)
        candidates = self._candidate_pipeline(candidates, simulations, ranked, attempts)
        if not full:
            attempts = [self._compact_attempt(item) for item in attempts]
            diagnoses = []
        base.update(
            {
                "plan": None if plan is None else _redact(plan.plan),
                "ideas": _redact(ideas),
                "idea_attempts": _redact(idea_attempts),
                "timeline": _redact(attempts),
                "node_attempt_counts": _redact(attempt_counts),
                "candidates": _redact(candidates),
                "simulations": _redact(simulations),
                "diagnoses": _redact(diagnoses),
                "model_calls": _redact(model_calls),
                "commands": _redact(commands),
                "approvals": _redact(approvals),
                "artifacts": artifacts,
                "evaluation": _redact(evaluated) if full else None,
                "template_density": _redact(artifact_payloads["template_density.json"]) if full else None,
                "anti_patterns": _redact(artifact_payloads["anti_patterns.json"]) if full else None,
                "latest_diagnosis": _redact(artifact_payloads["diagnosis.json"]) if full else None,
                "final_report": _redact(artifact_payloads["final_report.json"]),
            }
        )
        return base

    def retry_idea(self, run_id: str, idea_id: str) -> dict[str, object]:
        store = self.store()
        store.get_run(run_id)
        idea = store.retry_research_idea(run_id, idea_id)
        return {
            "ok": True,
            "run_id": run_id,
            "idea_id": idea.idea_id,
            "status": idea.status,
            "stage": idea.stage,
        }

    def abort_idea(self, run_id: str, idea_id: str) -> dict[str, object]:
        store = self.store()
        store.get_run(run_id)
        idea = store.abort_research_idea(run_id, idea_id)
        return {
            "ok": True,
            "run_id": run_id,
            "idea_id": idea.idea_id,
            "status": idea.status,
            "stage": idea.stage,
        }

    def create_run(self, payload: Mapping[str, object]) -> dict[str, object]:
        config = self.config()
        self._ensure_models_ready(config)
        mode = str(payload.get("scope_mode", "manual"))
        budget = {
            "candidates_per_round": config.budget.candidates_per_round,
            "rounds": _positive_int(payload.get("max_rounds", config.budget.rounds), "max_rounds"),
            "total_simulations": _positive_int(
                payload.get("max_simulations", config.budget.total_simulations),
                "max_simulations",
            ),
        }
        values: dict[str, object] = {"scope_mode": mode, "budget": budget}
        dataset_id = payload.get("dataset_id")
        if type(dataset_id) is not str or not dataset_id.strip():
            raise ValueError("dataset_id is required; choose a dataset for each research run")
        values["dataset_id"] = dataset_id.strip()
        if mode == "manual":
            values.update(
                {
                    "region": payload.get("region"),
                    "delay": payload.get("delay"),
                    "universe": payload.get("universe"),
                    "neutralization": payload.get("neutralization"),
                }
            )
            available_datasets = self.dataset_options(
                region=values["region"], delay=None, universe=None
            )["datasets"]
            if dataset_id.strip().lower() not in {
                item["id"].lower() for item in available_datasets
            }:
                raise ValueError("selected dataset is unavailable for the chosen scope")
        elif mode == "auto":
            values["region"] = payload.get("region")
        scope = RunConfig.from_dict(values)
        run_id = datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S_%f_quant")

        def execute() -> None:
            runtime = build_runtime(replace(config, budget=scope.budget), self.store(), run_id)
            if mode == "manual":
                record = runtime.run_manual(run_id=run_id, scope=scope)
            else:
                record = runtime.run_auto(run_id=run_id, config=scope)
            self._resume_after_automatic_login(runtime, run_id, record)

        self._start_job(run_id, "run", execute)
        self._wait_for_run_registration(run_id)
        return {"ok": True, "run_id": run_id, "job": self.job(run_id)}

    def dataset_options(
        self, *, region: object, delay: object | None, universe: object | None
    ) -> dict[str, object]:
        if type(region) is not str or not region.strip():
            raise ValueError("region is required")
        if delay is not None and (type(delay) is not int or delay not in {0, 1}):
            raise ValueError("delay must be 0 or 1")
        if universe is not None and (type(universe) is not str or not universe.strip()):
            raise ValueError("universe is required")
        if (delay is None) != (universe is None):
            raise ValueError("delay and universe must be provided together")
        registry = EndpointRegistry.load(self.registry_path)
        client = WqbClient(registry, session_from_cookies(self.cookie_path))
        requested_region = region.strip()
        if delay is None:
            scope = self.simulation_options().get("scope")
            delays = scope.get("delays", {}).get(requested_region, []) if isinstance(scope, Mapping) else []
            universes = scope.get("universes", {}).get(requested_region, []) if isinstance(scope, Mapping) else []
            first_delay = next(
                (item["value"] for item in delays if isinstance(item, Mapping) and type(item.get("value")) is int),
                None,
            )
            first_universe = next(
                (item["value"] for item in universes if isinstance(item, Mapping)
                 and isinstance(item.get("value"), str) and item["value"].strip()),
                None,
            )
            pairs = [(first_delay, first_universe)] if first_delay is not None and first_universe else []
            if not pairs:
                raise ValueError("selected region has no platform dataset scopes")
            datasets: list[dict[str, str]] = []
            failures = 0
            for available_delay, available_universe in pairs:
                scope_rows, complete = self._dataset_scope_rows(
                    client, registry, requested_region, available_delay, available_universe
                )
                datasets.extend(scope_rows)
                if not complete:
                    failures += 1
                    datasets.extend(self._cached_dataset_rows(
                        region=requested_region,
                        delay=available_delay,
                        universe=available_universe,
                    ))
            rows = self._unique_dataset_rows(datasets)
            if rows:
                return {
                    "ok": True,
                    "datasets": rows,
                    "source": "platform" if failures == 0 else "platform_partial",
                    "stale": failures > 0,
                }
            raise ValueError("unable to load platform datasets for the selected region")

        datasets, complete = self._dataset_scope_rows(
            client, registry, requested_region, delay, universe
        )
        if datasets:
            return {
                "ok": True,
                "datasets": self._unique_dataset_rows(datasets),
                "source": "platform" if complete else "platform_partial",
                "stale": not complete,
            }
        cached = (
            self._cached_dataset_rows(
                region=requested_region, delay=delay, universe=universe.strip()
            )
        )
        if cached:
            return {"ok": True, "datasets": cached, "source": "run_artifact", "stale": True}
        raise ValueError("unable to load platform datasets")

    @classmethod
    def _dataset_scope_rows(
        cls,
        client: WqbClient,
        registry: EndpointRegistry,
        region: str,
        delay: int,
        universe: str,
    ) -> tuple[list[dict[str, str]], bool]:
        response = cls._dataset_request(client, registry, region, delay, universe, offset=0)
        if response.get("ok") is not True:
            return [], False
        try:
            rows = cls._dataset_rows(response)
            total = cls._dataset_result_count(response, len(rows))
        except ValueError:
            return [], False

        # The platform rejects pages above 50 records; keep fetching until its count is exhausted.
        offset = 50
        while offset < total:
            page = cls._dataset_request(client, registry, region, delay, universe, offset=offset)
            if page.get("ok") is not True:
                return rows, False
            try:
                page_rows = cls._dataset_rows(page)
            except ValueError:
                return rows, False
            if not page_rows:
                return rows, False
            rows.extend(page_rows)
            offset += 50
        return rows, True

    @staticmethod
    def _dataset_result_count(response: Mapping[str, object], fallback: int) -> int:
        envelope = response.get("response")
        body = envelope.get("body") if isinstance(envelope, Mapping) else None
        count = body.get("count") if isinstance(body, Mapping) else None
        if type(count) is int and count >= fallback:
            return count
        return fallback

    @staticmethod
    def _dataset_request(
        client: WqbClient,
        registry: EndpointRegistry,
        region: str,
        delay: int,
        universe: str,
        *,
        offset: int,
    ) -> Mapping[str, object]:
        prepared = client.prepare(registry.get("/data-sets"), "GET", params={
            "instrumentType": "EQUITY", "region": region,
            "delay": str(delay), "universe": universe,
            "limit": "50", "offset": str(offset),
        })
        response = client.call(prepared)
        return response if isinstance(response, Mapping) else {}

    @staticmethod
    def _unique_dataset_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
        unique: dict[str, dict[str, str]] = {}
        for row in rows:
            identifier = row.get("id")
            if identifier and identifier not in unique:
                unique[identifier] = row
        return sorted(unique.values(), key=lambda row: (row["category"], row["label"], row["id"]))

    @staticmethod
    def _dataset_rows(response: Mapping[str, object]) -> list[dict[str, str]]:
        envelope = response.get("response")
        body = envelope.get("body") if isinstance(envelope, Mapping) else None
        rows = body.get("results", body.get("datasets")) if isinstance(body, Mapping) else None
        if not isinstance(rows, list):
            raise ValueError("platform datasets response is invalid")
        datasets: list[dict[str, str]] = []
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, Mapping) or type(row.get("id")) is not str:
                continue
            identifier = row["id"].strip()
            if not identifier or identifier in seen:
                continue
            seen.add(identifier)
            label = row.get("name", row.get("description", identifier))
            category = row.get("category", row.get("type", "uncategorized"))
            if isinstance(category, Mapping):
                category = category.get("id", category.get("name", "uncategorized"))
            category_text = str(category).strip() or "uncategorized"
            datasets.append({
                "id": identifier,
                "label": str(label).strip() or identifier,
                "category": category_text,
            })
        return datasets

    def _cached_dataset_rows(
        self, *, region: str, delay: int, universe: str
    ) -> list[dict[str, str]]:
        store = self.store()
        with closing(store.connect()) as connection:
            rows = connection.execute(
                "SELECT id,run_id FROM artifacts WHERE name='data_datasets.json' "
                "ORDER BY id DESC LIMIT 100"
            ).fetchall()
        for row in rows:
            artifact = store.get_artifact(int(row["id"]))
            path = Path(artifact.path)
            if not path.is_file():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                continue
            request = payload.get("request") if isinstance(payload, Mapping) else None
            params = request.get("params") if isinstance(request, Mapping) else None
            if not isinstance(params, Mapping) or (
                str(params.get("region", "")).upper() != region.upper()
                or str(params.get("delay", "")) != str(delay)
                or str(params.get("universe", "")).upper() != universe.upper()
            ):
                continue
            if payload.get("ok") is not True:
                continue
            try:
                return self._dataset_rows(payload)
            except ValueError:
                continue
        return []

    def resume_run(self, run_id: str) -> dict[str, object]:
        store = self.store()
        run = store.get_run(run_id)
        recoverable = (
            run.state is RunState.FAILED
            and store.latest_failed_node(run_id) in RECOVERABLE_FAILED_NODES
        )
        budget_finalization = (
            run.state is RunState.BUDGET_EXHAUSTED
            and store.budget_finalization_node(run_id) is not None
        )
        if (
            run.state.value in _TERMINAL_STATES
            and not recoverable
            and not budget_finalization
        ):
            raise ValueError(f"run is terminal and cannot resume: {run.state.value}")
        if run.state is RunState.AWAITING_APPROVAL:
            raise ValueError("run is waiting for approve or reject, not resume")
        config = replace(self.config(), budget=run.config.budget)
        self._ensure_models_ready(config)
        self._start_job(
            run_id,
            "resume",
            lambda: self._resume_after_automatic_login(
                runtime := build_runtime(config, self.store(), run_id),
                run_id,
                runtime.coordinator.resume(run_id),
            ),
        )
        return {"ok": True, "run_id": run_id, "job": self.job(run_id)}

    def stop_run(self, run_id: str) -> dict[str, object]:
        store = self.store()
        run = store.get_run(run_id)
        if run.state.value in _TERMINAL_STATES:
            raise ValueError(f"run is terminal and cannot be stopped: {run.state.value}")
        job = self.job(run_id)
        if job is not None and job.get("action") == "approve" and job.get("state") in {"QUEUED", "RUNNING"}:
            raise ValueError("approved submission cannot be stopped")
        stopped = store.transition(run_id, RunState.STOPPED, "manually stopped by user")
        with self._jobs_lock:
            active = self.jobs.get(run_id)
            if active is not None and active.state in {"QUEUED", "RUNNING"}:
                active.state = "STOPPING"
        return {"ok": True, "run_id": run_id, "state": stopped.state.value, "job": self.job(run_id)}

    def approve_run(self, run_id: str) -> dict[str, object]:
        store = self.store()
        run = store.get_run(run_id)
        if run.state is not RunState.AWAITING_APPROVAL:
            raise ValueError("only AWAITING_APPROVAL runs can be submitted")
        config = replace(self.config(), budget=run.config.budget)
        self._start_job(
            run_id,
            "approve",
            lambda: build_submission_runtime(config, self.store(), run_id).approve(run_id),
        )
        return {"ok": True, "run_id": run_id, "job": self.job(run_id)}

    def reject_run(self, run_id: str, reason: object) -> dict[str, object]:
        if type(reason) is not str or not reason.strip():
            raise ValueError("reason must be nonblank")
        store = self.store()
        run = store.get_run(run_id)
        if run.state is not RunState.AWAITING_APPROVAL:
            raise ValueError("only AWAITING_APPROVAL runs can be rejected")
        result = store.record_rejection(run_id, reason.strip()[:1000])
        return {"ok": True, "run_id": run_id, "state": result.state.value}

    def auth_status(self) -> dict[str, object]:
        client = WqbClient(EndpointRegistry.load(self.registry_path), session_from_cookies(self.cookie_path))
        result = client.call(client.prepare(client.registry.get("/authentication"), "GET"))
        output = _redact(result)
        response = output.get("response", {}) if isinstance(output, Mapping) else {}
        status_code = response.get("status_code") if isinstance(response, Mapping) else None
        authenticated = output.get("ok") is True and status_code not in {204, 401, 403}
        return {**output, "authenticated": authenticated}

    def auth_login(self, payload: Mapping[str, object]) -> dict[str, object]:
        email = payload.get("email")
        password = payload.get("password")
        expiry = payload.get("expiry", 3600)
        if type(email) is not str or not email.strip():
            raise ValueError("email must be nonblank")
        if type(password) is not str or not password:
            raise ValueError("password must be nonblank")
        if type(expiry) is not int or expiry <= 0:
            raise ValueError("expiry must be a positive integer")
        client = WqbClient(EndpointRegistry.load(self.registry_path), session_from_cookies(self.cookie_path))
        login = resolve_login_payload(
            email=email.strip(), password=password, expiry=expiry, config_path=self.config_path
        )
        result = client.call(client.prepare(client.registry.get("/authentication"), "POST", json_body=login))
        if result.get("ok"):
            save_cookie_payload(client.session, self.cookie_path)
            raw = load_config(self.config_path)
            auth = raw.setdefault("auth", {})
            service = str(auth.get("keyring_service") or "wqb-cli")
            secret_result = set_secret(service, email.strip(), password)
            if secret_result.get("ok") is True:
                auth["keyring_service"] = service
                auth["keyring_username"] = email.strip()
            auth["email"] = email.strip()
            save_config(raw, self.config_path)
        return _redact(result)

    def auto_login(self) -> dict[str, object]:
        login = resolve_login_payload(config_path=self.config_path)
        email = login.get("email")
        password = login.get("password")
        if type(email) is not str or not email.strip() or type(password) is not str or not password:
            return {"ok": False, "detail": "automatic login credentials are unavailable"}
        client = WqbClient(EndpointRegistry.load(self.registry_path), session_from_cookies(self.cookie_path))
        result = client.call(client.prepare(client.registry.get("/authentication"), "POST", json_body=login))
        if result.get("ok") is True:
            save_cookie_payload(client.session, self.cookie_path)
        return _redact(result)

    def _resume_after_automatic_login(
        self, runtime: object, run_id: str, record: object
    ) -> object:
        for _ in range(2):
            if getattr(record, "state", None) is not RunState.NEEDS_AUTH:
                break
            if self.auto_login().get("ok") is not True:
                break
            coordinator = getattr(runtime, "coordinator", None)
            resume = getattr(coordinator, "resume", None)
            if not callable(resume):
                raise RuntimeError("runtime coordinator cannot resume after automatic login")
            record = resume(run_id)
        return record

    def models(self) -> dict[str, object]:
        config = self.config()
        return {"ok": True, "models": [_app_model_projection(role, config) for role in ModelRole]}

    def simulation_options(self, *, refresh: bool = False) -> dict[str, object]:
        with self._platform_options_lock:
            if not refresh and self._platform_options is not None:
                return deepcopy(self._platform_options)
            if not refresh:
                cached = self._load_platform_options_cache(require_fresh=True)
                if cached is not None:
                    cached = {
                        **cached,
                        "source": "local_cache",
                        "refresh_status": "fresh_cache",
                    }
                    self._platform_options = cached
                    return deepcopy(cached)

            failure = "platform_unavailable"
            try:
                registry = EndpointRegistry.load(self.registry_path)
                client = WqbClient(registry, session_from_cookies(self.cookie_path))
                result = client.call(client.prepare(registry.get("/simulations"), "OPTIONS"))
                if result.get("ok") is True:
                    normalized = _normalize_platform_options(result)
                    payload = _scope_options_payload(normalized, source="platform", stale=False)
                    self._save_platform_options_cache(payload)
                    self._platform_options = payload
                    return deepcopy(payload)
                status_code = (result.get("response") or {}).get("status_code")
                failure = "authentication_required" if status_code in {401, 403} else "platform_unavailable"
            except Exception:
                failure = "platform_unavailable"

            cached = self._load_platform_options_cache(require_fresh=False)
            if cached is not None:
                cached = {**cached, "source": "local_cache", "stale": True, "refresh_status": failure}
                self._platform_options = cached
                return deepcopy(cached)

            artifact = self._latest_successful_simulation_options()
            if artifact is not None:
                try:
                    normalized = _normalize_platform_options(artifact)
                    payload = _scope_options_payload(
                        normalized, source="run_artifact", stale=True, refresh_status=failure
                    )
                    self._save_platform_options_cache(payload)
                    self._platform_options = payload
                    return deepcopy(payload)
                except ValueError:
                    pass

            payload = _scope_options_payload(
                deepcopy(_BUNDLED_SCOPE_OPTIONS),
                source="bundled_fallback",
                stale=True,
                refresh_status=failure,
            )
            self._platform_options = payload
            return deepcopy(payload)

    def update_model(self, role_name: str, payload: Mapping[str, object]) -> dict[str, object]:
        role = ModelRole(role_name)
        config = self.config()
        current = asdict(config.models[role])
        allowed = set(current)
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(f"unsupported model fields: {', '.join(sorted(unknown))}")
        current.update(payload)
        model = ModelConfig(**current)
        models = dict(config.models)
        models[role] = model
        validate_agent_config(replace(config, models=models), require_models=False)
        raw = load_config(self.config_path)
        raw["agent"]["models"][role.value] = current
        save_config(raw, self.config_path)
        return {"ok": True, "model": _app_model_projection(role, self.config())}

    def update_model_key(self, role_name: str, payload: Mapping[str, object]) -> dict[str, object]:
        role = ModelRole(role_name)
        value = payload.get("key")
        if type(value) is not str or not value:
            raise ValueError("key must be nonblank")
        secret_name = self.config().models[role].secret_name
        result = set_named_secret(secret_name, value)
        if not result.get("ok"):
            raise RuntimeError(str(result.get("detail") or "keyring rejected the key"))
        return {"ok": True, "role": role.value, "secret_configured": True}

    def artifact(self, run_id: str, artifact_id: int) -> tuple[bytes, str]:
        store = self.store()
        artifact = store.get_artifact(artifact_id)
        if artifact.run_id != run_id:
            raise StoreRecordNotFound("artifact does not belong to run")
        path = Path(artifact.path)
        if not path.is_file():
            raise FileNotFoundError(path)
        raw = path.read_bytes()
        if artifact.kind in {"json", "jsonl", "text", "markdown"} or path.suffix.lower() in {
            ".json", ".jsonl", ".txt", ".md"
        }:
            text = raw.decode("utf-8-sig", errors="replace")
            if path.suffix.lower() == ".json":
                try:
                    text = json.dumps(_redact(json.loads(text)), ensure_ascii=False, indent=2)
                except json.JSONDecodeError:
                    text = str(_redact(text))
            else:
                text = str(_redact(text))
            return text.encode("utf-8"), "application/json; charset=utf-8" if path.suffix.lower() == ".json" else "text/plain; charset=utf-8"
        return raw, mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    def job(self, run_id: str) -> dict[str, object] | None:
        with self._jobs_lock:
            record = self.jobs.get(run_id)
            return None if record is None else record.projection()

    def _start_job(self, run_id: str, action: str, target: Callable[[], object]) -> None:
        with self._jobs_lock:
            existing = self.jobs.get(run_id)
            if existing is not None and existing.state in {"QUEUED", "RUNNING"}:
                raise ValueError(f"a {existing.action} job is already active for this run")
            self.jobs[run_id] = JobRecord(run_id=run_id, action=action)

        def wrapped() -> None:
            with self._jobs_lock:
                job = self.jobs[run_id]
                job.state = "RUNNING"
                job.started_at = _now()
            try:
                target()
            except Exception as error:
                with self._jobs_lock:
                    job = self.jobs[run_id]
                    job.state = "FAILED"
                    job.error_type = type(error).__name__
                    job.detail = _safe_error(error)
                    job.finished_at = _now()
                return
            with self._jobs_lock:
                job = self.jobs[run_id]
                job.state = "STOPPED" if job.state == "STOPPING" else "COMPLETED"
                job.finished_at = _now()

        threading.Thread(target=wrapped, name=f"wqb-app-{action}-{run_id}", daemon=True).start()

    def _wait_for_run_registration(self, run_id: str, timeout_seconds: float = 5.0) -> None:
        deadline = time.monotonic() + timeout_seconds
        store = self.store()
        while time.monotonic() < deadline:
            try:
                store.get_run(run_id)
                return
            except RunNotFound:
                pass
            job = self.job(run_id)
            if job is not None and job.get("state") == "FAILED":
                detail = str(job.get("detail") or "background run failed before registration")
                raise RuntimeError(detail)
            time.sleep(0.01)
        raise RuntimeError("background run did not register within 5 seconds")

    def _platform_options_cache_path(self) -> Path:
        return self.config().database_path.parent / "platform_simulation_options.json"

    def _load_platform_options_cache(self, *, require_fresh: bool) -> dict[str, object] | None:
        path = self._platform_options_cache_path()
        try:
            if require_fresh and time.time() - path.stat().st_mtime > _PLATFORM_OPTIONS_CACHE_SECONDS:
                return None
            value = json.loads(path.read_text(encoding="utf-8-sig"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None
        if not isinstance(value, dict) or value.get("schema_version") != _PLATFORM_OPTIONS_SCHEMA_VERSION:
            return None
        try:
            _validate_normalized_scope_options(value.get("scope"))
        except ValueError:
            return None
        return value

    def _save_platform_options_cache(self, payload: Mapping[str, object]) -> None:
        path = self._platform_options_cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    def _latest_successful_simulation_options(self) -> object | None:
        root = self.config().run_root
        try:
            candidates = sorted(
                root.rglob("validated_sim_options.json"),
                key=lambda item: item.stat().st_mtime,
                reverse=True,
            )
        except OSError:
            return None
        for path in candidates:
            try:
                value = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(value, Mapping) and value.get("ok") is True:
                return value
        return None

    @staticmethod
    def _ensure_models_ready(config: AgentConfig) -> None:
        from .core.secrets import get_named_secret

        missing = []
        for role in ModelRole:
            model = config.models[role]
            if not model.model.strip():
                missing.append(f"{role.value} model")
            elif get_named_secret(model.secret_name) is None:
                missing.append(f"{role.value} key")
        if missing:
            raise ValueError("missing model configuration: " + ", ".join(missing))

    @staticmethod
    def _rows(connection: Any, sql: str, params: tuple[object, ...]) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for row in connection.execute(sql, params):
            item = dict(row)
            for column, target in _JSON_COLUMNS.items():
                if column in item:
                    raw = item.pop(column)
                    item[target] = None if raw is None else json.loads(raw)
            result.append(item)
        return result

    @staticmethod
    def _compact_attempt(item: Mapping[str, object]) -> dict[str, object]:
        summary = item.get("summary")
        compact: dict[str, object] = {}
        if isinstance(summary, Mapping):
            for key in (
                "decision",
                "reason",
                "failure",
                "authenticated",
                "accepted",
                "rejected",
                "simulations",
                "alphas",
                "alpha_id",
                "status_code",
                "status",
                "idea_id",
                "idea_status",
                "retry_after_seconds",
            ):
                value = summary.get(key)
                if value is None:
                    continue
                if type(value) in {bool, int, float}:
                    compact[key] = value
                elif type(value) is str:
                    compact[key] = value[:1000]
            coordinator = summary.get("_coordinator")
            if isinstance(coordinator, Mapping):
                route = {
                    key: coordinator[key]
                    for key in ("node", "next_node", "paused_node")
                    if type(coordinator.get(key)) is str
                }
                if route:
                    compact["_coordinator"] = route
        projected = dict(item)
        if compact:
            projected["summary"] = compact
        else:
            projected.pop("summary", None)
        return projected

    @staticmethod
    def _latest_artifact_payload(store: AgentStore, run_id: str, name: str) -> object | None:
        with closing(store.connect()) as connection:
            row = connection.execute(
                "SELECT id FROM artifacts WHERE run_id=? AND name=? ORDER BY id DESC LIMIT 1",
                (run_id, name),
            ).fetchone()
        if row is None:
            return None
        artifact = store.get_artifact(int(row["id"]))
        path = Path(artifact.path)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return None

    @staticmethod
    def _candidate_pipeline(
        candidates: list[dict[str, object]],
        simulations: list[dict[str, object]],
        ranked: object,
        attempts: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        metrics_by_alpha = {
            str(item.get("alpha_id")): item
            for item in ranked
            if isinstance(ranked, list) and isinstance(item, Mapping) and item.get("alpha_id")
        }
        sims_by_candidate: dict[int, list[dict[str, object]]] = {}
        expression_sims: dict[str, list[dict[str, object]]] = {}
        for simulation in simulations:
            candidate_id = simulation.get("candidate_id")
            if type(candidate_id) is int:
                sims_by_candidate.setdefault(candidate_id, []).append(simulation)
            expression = simulation.get("expression")
            if type(expression) is str:
                expression_sims.setdefault(expression.strip(), []).append(simulation)
        k_completed = any(item.get("node") == "K" and item.get("status") == "COMPLETED" for item in attempts)
        output = []
        for candidate in candidates:
            body = candidate.get("candidate")
            expression = body.get("expression") if isinstance(body, Mapping) else None
            linked = list(sims_by_candidate.get(int(candidate["id"]), []))
            if not linked and type(expression) is str:
                linked = list(expression_sims.get(expression.strip(), []))
            alpha_ids = [str(item["alpha_id"]) for item in linked if item.get("alpha_id")]
            metrics = next((metrics_by_alpha[item] for item in alpha_ids if item in metrics_by_alpha), None)
            if candidate.get("status") == "REJECTED":
                pipeline_state = "REJECTED"
            elif not linked:
                pipeline_state = "VALIDATED"
            elif any(str(item.get("status")) in {"CREATED", "PENDING", "QUEUED"} for item in linked):
                pipeline_state = "SIM_QUEUED"
            elif any(str(item.get("status")) in {"RUNNING", "TIMED_OUT"} for item in linked):
                pipeline_state = "SIMULATING"
            elif metrics is not None or k_completed:
                pipeline_state = "EVALUATED"
            else:
                pipeline_state = "SIMULATED"
            output.append(
                {
                    **candidate,
                    "expression": expression,
                    "pipeline_state": pipeline_state,
                    "simulations": linked,
                    "metrics": metrics,
                }
            )
        return output

    @staticmethod
    def _enrich_legacy_simulations(
        store: AgentStore, run_id: str, simulations: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        if all(item.get("candidate_id") is not None for item in simulations):
            return simulations
        payload = AppState._latest_artifact_payload(store, run_id, "simulation_batch_1_result.json")
        if not isinstance(payload, Mapping):
            return simulations
        expressions: dict[str, str] = {}
        children = payload.get("children")
        if isinstance(children, list):
            for child in children:
                if not isinstance(child, Mapping):
                    continue
                simulation_id = child.get("simulation_id")
                result = child.get("result")
                response = result.get("response") if isinstance(result, Mapping) else None
                body = response.get("body") if isinstance(response, Mapping) else None
                expression = body.get("regular") if isinstance(body, Mapping) else None
                if type(simulation_id) is str and type(expression) is str:
                    expressions[simulation_id] = expression
        return [
            {**item, "expression": expressions.get(str(item.get("simulation_id")))}
            for item in simulations
        ]


class AppRequestHandler(BaseHTTPRequestHandler):
    server_version = "WQBResearchDesk/1"

    @property
    def app(self) -> AppState:
        return self.server.app_state  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802
        try:
            self._get()
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as error:
            self._error(error)

    def do_POST(self) -> None:  # noqa: N802
        try:
            self._post()
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as error:
            self._error(error)

    def do_PUT(self) -> None:  # noqa: N802
        try:
            self._put()
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as error:
            self._error(error)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")

    def _get(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path == "/api/health":
            self._json({"ok": True, "status": "ready"})
        elif path == "/api/bootstrap":
            self._json(self.app.bootstrap())
        elif path == "/api/runs":
            self._json(self.app.list_runs())
        elif path == "/api/auth/status":
            self._json(self.app.auth_status())
        elif path == "/api/models":
            self._json(self.app.models())
        elif path == "/api/platform/simulation-options":
            refresh = parse_qs(parsed.query).get("refresh", ["0"])[0] in {"1", "true"}
            self._json(self.app.simulation_options(refresh=refresh))
        elif path == "/api/platform/datasets":
            query = parse_qs(parsed.query)
            delay = query.get("delay", [None])[0]
            self._json(self.app.dataset_options(
                region=query.get("region", [None])[0],
                delay=int(delay) if delay is not None and delay.isdigit() else None,
                universe=query.get("universe", [None])[0],
            ))
        elif match := re.fullmatch(r"/api/runs/([^/]+)/artifacts/(\d+)", path):
            body, content_type = self.app.artifact(match.group(1), int(match.group(2)))
            self._bytes(body, content_type)
        elif match := re.fullmatch(r"/api/runs/([^/]+)", path):
            full = parse_qs(parsed.query).get("full", ["0"])[0] in {"1", "true"}
            self._json(self.app.run_detail(match.group(1), full=full))
        elif path == "/" or path == "/index.html":
            self._static("index.html")
        elif path in {"/app.js", "/styles.css"}:
            self._static(path[1:])
        elif path == "/brand.png":
            brand = Path(__file__).resolve().parent / "resources" / "docs" / "assets" / "branding" / "wqb_cli_logo.png"
            self._bytes(brand.read_bytes(), "image/png")
        else:
            raise FileNotFoundError(path)

    def _post(self) -> None:
        path = unquote(urlparse(self.path).path)
        payload = self._body()
        if path == "/api/runs":
            self._json(self.app.create_run(payload), HTTPStatus.ACCEPTED)
        elif path == "/api/auth/login":
            self._json(self.app.auth_login(payload))
        elif match := re.fullmatch(r"/api/runs/([^/]+)/(resume|approve|reject|stop)", path):
            run_id, action = match.groups()
            if action == "resume":
                result = self.app.resume_run(run_id)
            elif action == "approve":
                result = self.app.approve_run(run_id)
            elif action == "stop":
                result = self.app.stop_run(run_id)
            else:
                result = self.app.reject_run(run_id, payload.get("reason"))
            self._json(result, HTTPStatus.ACCEPTED if action not in {"reject", "stop"} else HTTPStatus.OK)
        elif match := re.fullmatch(
            r"/api/runs/([^/]+)/ideas/([^/]+)/(retry|abort)", path
        ):
            run_id, idea_id, action = match.groups()
            result = (
                self.app.retry_idea(run_id, idea_id)
                if action == "retry"
                else self.app.abort_idea(run_id, idea_id)
            )
            self._json(result, HTTPStatus.ACCEPTED)
        else:
            raise FileNotFoundError(path)

    def _put(self) -> None:
        path = unquote(urlparse(self.path).path)
        payload = self._body()
        if match := re.fullmatch(r"/api/models/(planner|operator)/key", path):
            self._json(self.app.update_model_key(match.group(1), payload))
        elif match := re.fullmatch(r"/api/models/(planner|operator)", path):
            self._json(self.app.update_model(match.group(1), payload))
        else:
            raise FileNotFoundError(path)

    def _body(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise ValueError("request body is too large")
        raw = self.rfile.read(length)
        if not raw:
            return {}
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON body must be an object")
        return value

    def _static(self, name: str) -> None:
        root = self.app.asset_root
        path = (root / name).resolve()
        if root not in path.parents or not path.is_file():
            raise FileNotFoundError(name)
        self._bytes(path.read_bytes(), mimetypes.guess_type(path.name)[0] or "application/octet-stream")

    def _json(self, value: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        self._bytes(
            json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8"),
            "application/json; charset=utf-8",
            status,
        )

    def _bytes(
        self,
        body: bytes,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        self.send_response(status.value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store" if content_type.startswith("application/json") else "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, error: Exception) -> None:
        if isinstance(error, (FileNotFoundError, RunNotFound, StoreRecordNotFound, KeyError)):
            status = HTTPStatus.NOT_FOUND
        elif isinstance(error, (TypeError, ValueError, json.JSONDecodeError)):
            status = HTTPStatus.BAD_REQUEST
        else:
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            traceback.print_exc()
        self._json(
            {"ok": False, "error_type": type(error).__name__, "detail": _safe_error(error)},
            status,
        )


class ResearchDeskServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], app_state: AppState) -> None:
        super().__init__(address, AppRequestHandler)
        self.app_state = app_state


def serve_app(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
    config_path_value: str | None = None,
    database_path: str | None = None,
    run_root: str | None = None,
    registry_path: str | None = None,
    cookie_path: str | None = None,
) -> None:
    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("the local app may only bind to 127.0.0.1 or localhost")
    state = AppState(
        config_path_value=config_path_value,
        database_path=database_path,
        run_root=run_root,
        registry_path=registry_path,
        cookie_path=cookie_path,
    )
    server = ResearchDeskServer((host, port), state)
    actual_port = int(server.server_address[1])
    url = f"http://{host}:{actual_port}/"
    print(json.dumps({"ok": True, "url": url, "database_path": str(state.config().database_path)}, ensure_ascii=False))
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _normalize_platform_options(payload: Mapping[str, object]) -> dict[str, object]:
    response = payload.get("response")
    body = response.get("body") if isinstance(response, Mapping) else None
    actions = body.get("actions") if isinstance(body, Mapping) else None
    post = actions.get("POST") if isinstance(actions, Mapping) else None
    settings = post.get("settings") if isinstance(post, Mapping) else None
    fields = settings.get("children") if isinstance(settings, Mapping) else None
    if not isinstance(fields, Mapping):
        raise ValueError("platform simulation settings metadata is missing")

    instruments = _simple_choices(fields.get("instrumentType"))
    instrument_values = [item["value"] for item in instruments]
    instrument = "EQUITY" if "EQUITY" in instrument_values else (
        str(instrument_values[0]) if instrument_values else ""
    )
    if not instrument:
        raise ValueError("platform instrument type choices are missing")

    region_field = fields.get("region")
    region_choices = _instrument_choices(region_field, instrument)
    regions = _choice_rows(region_choices)
    if not regions:
        raise ValueError("platform region choices are missing")

    delays: dict[str, list[dict[str, object]]] = {}
    universes: dict[str, list[dict[str, object]]] = {}
    neutralizations: dict[str, list[dict[str, object]]] = {}
    for region in (str(item["value"]) for item in regions):
        delays[region] = _choice_rows(
            _region_choices(fields.get("delay"), instrument, region)
        )
        universes[region] = _choice_rows(
            _region_choices(fields.get("universe"), instrument, region)
        )
        neutralizations[region] = _choice_rows(
            _region_choices(fields.get("neutralization"), instrument, region)
        )

    normalized = {
        "instrument_type": instrument,
        "regions": regions,
        "delays": delays,
        "universes": universes,
        "neutralizations": neutralizations,
        "settings_catalog": _settings_catalog(fields),
    }
    _validate_normalized_scope_options(normalized)
    return normalized


def _simple_choices(field: object) -> list[dict[str, object]]:
    if not isinstance(field, Mapping):
        return []
    choices = field.get("choices")
    return _choice_rows(choices if isinstance(choices, list) else [])


def _instrument_choices(field: object, instrument: str) -> object:
    if not isinstance(field, Mapping):
        return []
    choices = field.get("choices")
    instruments = choices.get("instrumentType") if isinstance(choices, Mapping) else None
    return instruments.get(instrument, []) if isinstance(instruments, Mapping) else []


def _region_choices(field: object, instrument: str, region: str) -> object:
    instrument_choices = _instrument_choices(field, instrument)
    regions = instrument_choices.get("region") if isinstance(instrument_choices, Mapping) else None
    return regions.get(region, []) if isinstance(regions, Mapping) else []


def _choice_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in value:
        if isinstance(item, Mapping):
            choice = item.get("value")
            label = item.get("label", choice)
        else:
            choice = item
            label = item
        if type(choice) not in {str, int} or type(choice) is str and not choice.strip():
            continue
        identity = str(choice)
        if identity in seen:
            continue
        seen.add(identity)
        result.append({"value": choice, "label": str(label)})
    return result


def _settings_catalog(fields: Mapping[object, object]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for name, raw in fields.items():
        if type(name) is not str or not isinstance(raw, Mapping):
            continue
        record: dict[str, object] = {
            "name": name,
            "label": str(raw.get("label", name)),
            "type": str(raw.get("type", "field")),
            "required": raw.get("required") is True,
            "read_only": raw.get("readOnly") is True,
        }
        for source, target in (
            ("default", "default"),
            ("minValue", "min_value"),
            ("maxValue", "max_value"),
        ):
            if source in raw:
                record[target] = raw[source]
        choices = raw.get("choices")
        if isinstance(choices, list):
            record["choices"] = _choice_rows(choices)
        elif isinstance(choices, Mapping):
            record["dependent_choices"] = True
        result.append(record)
    return sorted(result, key=lambda item: str(item["name"]))


def _coerce_scope_options(value: Mapping[str, object]) -> dict[str, object]:
    regions = _choice_rows(value.get("regions"))
    result: dict[str, object] = {
        "instrument_type": str(value.get("instrument_type", "EQUITY")),
        "regions": regions,
    }
    for key in ("delays", "universes", "neutralizations"):
        source = value.get(key)
        rows_by_region: dict[str, list[dict[str, object]]] = {}
        if isinstance(source, Mapping):
            for region, choices in source.items():
                rows = _choice_rows(choices)
                if key == "neutralizations":
                    rows = [
                        {
                            **row,
                            "label": _CHOICE_LABELS.get(str(row["value"]), str(row["label"])),
                        }
                        for row in rows
                    ]
                rows_by_region[str(region)] = rows
        result[key] = rows_by_region
    return result


def _validate_normalized_scope_options(value: object) -> None:
    if not isinstance(value, Mapping):
        raise ValueError("scope options must be an object")
    regions = value.get("regions")
    if not isinstance(regions, list) or not regions:
        raise ValueError("scope options require regions")
    region_values = [
        str(item.get("value"))
        for item in regions
        if isinstance(item, Mapping) and item.get("value") is not None
    ]
    if not region_values:
        raise ValueError("scope options require region values")
    for key in ("delays", "universes", "neutralizations"):
        choices = value.get(key)
        if not isinstance(choices, Mapping):
            raise ValueError(f"scope options require {key}")
        for region in region_values:
            rows = choices.get(region)
            if not isinstance(rows, list) or not rows:
                raise ValueError(f"scope options have no {key} for {region}")


def _scope_options_payload(
    normalized: Mapping[str, object],
    *,
    source: str,
    stale: bool,
    refresh_status: str = "ok",
) -> dict[str, object]:
    scope = _coerce_scope_options(normalized)
    _validate_normalized_scope_options(scope)
    catalog = normalized.get("settings_catalog")
    return {
        "ok": True,
        "schema_version": _PLATFORM_OPTIONS_SCHEMA_VERSION,
        "source": source,
        "stale": stale,
        "refresh_status": refresh_status,
        "fetched_at": _now(),
        "scope": scope,
        "settings_catalog": catalog if isinstance(catalog, list) else [],
    }


def _positive_int(value: object, name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_error(error: Exception) -> str:
    return str(_redact(str(error)))[:1000]


def _app_model_projection(role: ModelRole, config: AgentConfig) -> dict[str, object]:
    model = config.models[role]
    return {
        **_model_projection(role, config),
        "base_url": model.base_url,
        "reasoning": model.reasoning,
        "structured_outputs": model.structured_outputs,
        "fallback_model": model.fallback_model,
        "connect_timeout_seconds": model.connect_timeout_seconds,
        "read_timeout_seconds": model.read_timeout_seconds,
        "proxy_mode": model.proxy_mode,
        "proxy_url": model.proxy_url,
        "input_cost_per_million": model.input_cost_per_million,
        "output_cost_per_million": model.output_cost_per_million,
    }


def _sensitive_key(key: object) -> bool:
    normalized = str(key).lower().replace("-", "_")
    if normalized in {"authorization", "cookie", "cookies", "password", "secret", "api_key", "apikey", "token", "access_token", "refresh_token"}:
        return True
    return normalized.endswith(("_password", "_secret", "_api_key", "_access_token", "_refresh_token"))


def _redact(value: object) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if _sensitive_key(key) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        value = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", value)
        value = re.sub(r"(?i)(api[_-]?key|password|secret|token)\s*[:=]\s*[^\s,;]+", r"\1=[REDACTED]", value)
    return value
