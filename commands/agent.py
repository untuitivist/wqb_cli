from __future__ import annotations

import argparse
from contextlib import closing
from dataclasses import asdict, replace
from datetime import datetime, timezone
import getpass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..agent.config import AgentConfig, load_agent_config, with_model_overrides
from ..agent.store import AgentStore
from ..agent.models.base import ModelError, ModelRequest
from ..agent.schemas import SchemaViolation
from ..agent.types import Budget, ModelRole, RunConfig, RunState, WorkflowNode
from ..core.config_store import load_config, save_config
from ..core.io import write_json
from ..core.secrets import get_named_secret, set_named_secret


def add_agent_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser("agent", help="Run the bounded multi-model research agent")
    parser.add_argument("--config", dest="config_path")
    parser.add_argument("--database")
    parser.add_argument("--run-root")
    commands = parser.add_subparsers(dest="agent_command", required=True)

    run = commands.add_parser("run")
    run.add_argument("--scope-mode", choices=("manual", "auto"), default="manual")
    run.add_argument("--region")
    run.add_argument("--delay", type=int)
    run.add_argument("--universe")
    run.add_argument("--neutralization")
    run.add_argument("--dataset-id", required=True)
    run.add_argument("--planner-model")
    run.add_argument("--operator-model")
    _add_budget_options(run)

    for name in ("resume", "status", "approve"):
        command = commands.add_parser(name)
        command.add_argument("run_id")
    reject = commands.add_parser("reject")
    reject.add_argument("run_id")
    reject.add_argument("--reason", required=True)
    history = commands.add_parser("history")
    history.add_argument("--limit", type=int, default=20)
    history.add_argument("--state", choices=tuple(state.value for state in RunState))

    models = commands.add_parser("models")
    model_commands = models.add_subparsers(dest="models_command", required=True)
    model_commands.add_parser("list")
    set_model = model_commands.add_parser("set")
    set_model.add_argument("role", choices=tuple(role.value for role in ModelRole))
    set_model.add_argument("--provider", required=True, choices=("openai", "openai-compatible"))
    set_model.add_argument("--api-style", required=True, choices=("responses", "chat_completions"))
    set_model.add_argument("--model", required=True)
    set_model.add_argument("--base-url")
    set_model.add_argument("--reasoning")
    set_model.add_argument("--secret-name")
    set_model.add_argument("--structured-outputs", choices=("true", "false"))
    set_model.add_argument("--fallback-model")
    set_model.add_argument("--connect-timeout-seconds", type=int)
    set_model.add_argument("--read-timeout-seconds", type=int)
    set_model.add_argument("--proxy-mode", choices=("system", "direct", "custom"))
    set_model.add_argument("--proxy-url")
    set_model.add_argument("--input-cost-per-million", type=float)
    set_model.add_argument("--output-cost-per-million", type=float)
    set_key = model_commands.add_parser("set-key")
    set_key.add_argument("role", choices=tuple(role.value for role in ModelRole))
    test = model_commands.add_parser("test")
    test.add_argument("role", nargs="?", choices=tuple(role.value for role in ModelRole))

    evaluate = commands.add_parser("eval")
    evaluate.add_argument("--suite", default="offline")
    evaluate.add_argument("--live", action="store_true")
    evaluate.add_argument("--max-simulations", type=int)


def _add_budget_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--max-rounds", type=int)
    parser.add_argument("--max-simulations", type=int)


class AgentService:
    def __init__(self, config: AgentConfig, store: AgentStore, args: argparse.Namespace) -> None:
        self.config = config
        self.store = store
        self.args = args

    def run(self, scope: RunConfig) -> dict[str, object]:
        coordinator = self._coordinator(_run_id())
        record = (
            coordinator.run_manual(run_id=coordinator.run_id, scope=scope)
            if scope.scope_mode.value == "manual"
            else coordinator.run_auto(run_id=coordinator.run_id, config=scope)
        )
        return status_projection(self.store, record.run_id)

    def resume(self, run_id: str) -> dict[str, object]:
        return status_projection(self.store, self._coordinator(run_id).coordinator.resume(run_id).run_id)

    def status(self, run_id: str) -> dict[str, object]:
        return status_projection(self.store, run_id)

    def history(self, limit: int, state: str | None) -> dict[str, object]:
        return history_projection(self.store, limit, state)

    def approve(self, run_id: str) -> dict[str, object]:
        from .agent_runtime import build_submission_runtime

        run = self.store.get_run(run_id)
        config = replace(self.config, budget=run.config.budget)
        return build_submission_runtime(config, self.store, run_id).approve(run_id)

    def reject(self, run_id: str, reason: str) -> dict[str, object]:
        result = self.store.record_rejection(run_id, reason)
        return {"ok": True, "run_id": run_id, "state": result.state.value}

    def model_healthcheck(self, role: ModelRole | None) -> dict[str, object]:
        from .agent_runtime import build_model_adapter

        roles = tuple(ModelRole) if role is None else (role,)
        checks: list[dict[str, object]] = []
        for selected in roles:
            config = self.config.models[selected]
            try:
                adapter = build_model_adapter(self.config, selected)
                result = adapter.invoke(
                    ModelRequest(
                        selected,
                        WorkflowNode.B,
                        "Model health check. Return a valid response for the required JSON schema.",
                        {"healthcheck": True},
                    )
                )
                checks.append(
                    {
                        "role": selected.value,
                        "ok": True,
                        "model": config.model,
                        "api_style": config.api_style,
                        "latency_ms": result.latency_ms,
                        "input_tokens": result.input_tokens,
                        "output_tokens": result.output_tokens,
                        "provider_request_id": result.provider_request_id,
                    }
                )
            except Exception as error:
                detail = (
                    str(error)
                    if isinstance(error, (ModelError, SchemaViolation, ValueError))
                    else "unexpected model healthcheck failure"
                )
                checks.append(
                    {
                        "role": selected.value,
                        "ok": False,
                        "model": config.model,
                        "api_style": config.api_style,
                        "error_type": type(error).__name__,
                        "detail": detail,
                    }
                )
        return {
            "ok": all(bool(check["ok"]) for check in checks),
            "roles": [item.value for item in roles],
            "checks": checks,
        }

    def _coordinator(self, run_id: str) -> Any:
        # Imports are deferred so status/history/help work before model setup.
        from .agent_runtime import build_runtime

        return build_runtime(self.config, self.store, run_id)


def build_service(args: argparse.Namespace) -> AgentService:
    config = load_agent_config(getattr(args, "config_path", None), require_models=False)
    if getattr(args, "database", None):
        config = replace(config, database_path=Path(args.database))
    if getattr(args, "run_root", None):
        config = replace(config, run_root=Path(args.run_root))
    config = with_model_overrides(
        config,
        planner_model=getattr(args, "planner_model", None),
        operator_model=getattr(args, "operator_model", None),
        require_models=False,
    )
    config = replace(config, budget=_budget_override(config.budget, args))
    store = AgentStore(config.database_path)
    store.initialize()
    return AgentService(config, store, args)


def handle_agent(args: argparse.Namespace) -> int:
    try:
        if args.agent_command == "models":
            payload = _handle_models(args)
        else:
            service = build_service(args)
            if args.agent_command == "run":
                payload = service.run(_run_config(service.config.budget, args))
            elif args.agent_command == "resume":
                payload = service.resume(args.run_id)
            elif args.agent_command == "status":
                payload = service.status(args.run_id)
            elif args.agent_command == "approve":
                payload = service.approve(args.run_id)
            elif args.agent_command == "reject":
                payload = service.reject(args.run_id, args.reason)
            elif args.agent_command == "history":
                payload = service.history(args.limit, args.state)
            elif args.agent_command == "eval":
                from ..agent.eval import run_evaluation
                payload = run_evaluation(args.suite, live=args.live, max_simulations=args.max_simulations)
            else:
                raise AssertionError(args.agent_command)
        write_json(payload)
        return _exit_code(payload)
    except (TypeError, ValueError) as exc:
        write_json({"ok": False, "error_type": type(exc).__name__, "detail": str(exc)})
        return 2


def _handle_models(args: argparse.Namespace) -> dict[str, object]:
    config = load_agent_config(args.config_path, require_models=False)
    if args.models_command == "list":
        return {"ok": True, "models": [_model_projection(role, config) for role in ModelRole]}
    if args.models_command == "set-key":
        role = ModelRole(args.role)
        secret_name = config.models[role].secret_name
        result = set_named_secret(secret_name, getpass.getpass(f"API key for {role.value}: "))
        return {"ok": bool(result.get("ok")), "role": role.value, "secret_name": secret_name}
    if args.models_command == "set":
        raw = load_config(args.config_path)
        current = raw["agent"]["models"][args.role]
        values = {
            "provider": args.provider, "api_style": args.api_style, "model": args.model,
            "base_url": args.base_url, "reasoning": args.reasoning,
            "secret_name": args.secret_name,
            "structured_outputs": None if args.structured_outputs is None else args.structured_outputs == "true",
            "fallback_model": args.fallback_model,
            "connect_timeout_seconds": args.connect_timeout_seconds,
            "read_timeout_seconds": args.read_timeout_seconds,
            "proxy_mode": args.proxy_mode,
            "proxy_url": (
                ""
                if args.proxy_mode in {"system", "direct"}
                and args.proxy_url is None
                else args.proxy_url
            ),
            "input_cost_per_million": args.input_cost_per_million,
            "output_cost_per_million": args.output_cost_per_million,
        }
        current.update({key: value for key, value in values.items() if value is not None})
        save_config(raw, args.config_path)
        load_agent_config(args.config_path, require_models=False)
        return {"ok": True, "role": args.role, "model": args.model}
    if args.models_command == "test":
        return build_service(args).model_healthcheck(None if args.role is None else ModelRole(args.role))
    raise AssertionError(args.models_command)


def _model_projection(role: ModelRole, config: AgentConfig) -> dict[str, object]:
    model = config.models[role]
    return {
        "role": role.value, "provider": model.provider, "api_style": model.api_style,
        "model": model.model, "endpoint_host": urlparse(model.base_url).hostname or "",
        "secret_name": model.secret_name, "secret_configured": get_named_secret(model.secret_name) is not None,
    }


def _run_config(budget: Budget, args: argparse.Namespace) -> RunConfig:
    return RunConfig.from_dict({
        "scope_mode": args.scope_mode, "region": args.region, "delay": args.delay,
        "universe": args.universe, "neutralization": args.neutralization,
        "dataset_id": args.dataset_id,
        "budget": asdict(budget),
    })


def _budget_override(budget: Budget, args: argparse.Namespace) -> Budget:
    names = {
        "max_rounds": "rounds", "max_simulations": "total_simulations",
    }
    values = {target: getattr(args, source, None) for source, target in names.items() if getattr(args, source, None) is not None}
    return replace(budget, **values)


def status_projection(store: AgentStore, run_id: str) -> dict[str, object]:
    run = store.get_run(run_id)
    plan = store.get_latest_research_plan(run_id)
    with closing(store.connect()) as connection:
        actual_simulations = connection.execute(
            "SELECT COUNT(*) FROM simulations "
            "WHERE run_id = ? "
            "AND (candidate_id IS NOT NULL OR alpha_id IS NOT NULL)",
            (run_id,),
        ).fetchone()[0]
        rounds = connection.execute(
            "SELECT COUNT(*) FROM node_attempts "
            "WHERE run_id = ? AND node = 'K' AND status = 'COMPLETED'",
            (run_id,),
        ).fetchone()[0]
    return {
        "ok": True, "run_id": run_id, "state": run.state.value,
        "latest_node": None if store.latest_completed_node(run_id) is None else store.latest_completed_node(run_id).value,
        "scope": {key: getattr(run.config, key) for key in ("region", "delay", "universe", "neutralization")},
        "plan_version": None if plan is None else plan.plan_version,
        "plan_hash": None if plan is None else plan.plan_hash,
        "usage": store.usage_summary(run_id),
        "termination": {
            "actual_simulations": actual_simulations,
            "max_simulations": run.config.budget.total_simulations,
            "rounds": rounds,
            "max_rounds": run.config.budget.rounds,
        },
        "next_action": _next_action(run.state),
    }


def history_projection(store: AgentStore, limit: int, state: str | None) -> dict[str, object]:
    if type(limit) is not int or limit <= 0 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    with store.connect() as connection:
        sql = "SELECT run_id FROM runs"
        params: list[object] = []
        if state is not None:
            sql += " WHERE state = ?"; params.append(state)
        sql += " ORDER BY created_at DESC, run_id DESC LIMIT ?"; params.append(limit)
        ids = [row["run_id"] for row in connection.execute(sql, params)]
    return {"ok": True, "runs": [status_projection(store, run_id) for run_id in ids]}


def _next_action(state: RunState) -> str:
    return {RunState.NEEDS_AUTH: "auth_login_then_resume", RunState.NEEDS_DATA: "install_scope_data_then_resume", RunState.PAUSED_MODEL: "fix_model_then_resume", RunState.AWAITING_APPROVAL: "approve_or_reject"}.get(state, "none" if state in {RunState.SUBMITTED, RunState.REJECTED, RunState.STOPPED, RunState.FAILED, RunState.BUDGET_EXHAUSTED, RunState.NO_PROGRESS} else "resume")


def _exit_code(payload: object) -> int:
    return 0 if isinstance(payload, dict) and payload.get("ok", True) else 1


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S_quant")
