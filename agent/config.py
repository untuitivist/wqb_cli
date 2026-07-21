from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..core.config_store import load_config
from ..core.paths import DEFAULT_AGENT_SQLITE_PATH, DEFAULT_RESEARCH_RUNS_ROOT
from .types import Budget, ModelRole


_PROVIDERS = {"openai", "openai-compatible"}
_API_STYLES = {"responses", "chat_completions"}
_AGENT_FIELDS = {"database_path", "run_root", "models", "budget"}
_MODEL_TEXT_FIELDS = (
    "provider",
    "api_style",
    "model",
    "base_url",
    "reasoning",
    "secret_name",
    "fallback_model",
    "proxy_mode",
    "proxy_url",
)
_MODEL_TIMEOUT_FIELDS = ("connect_timeout_seconds", "read_timeout_seconds")
_MODEL_PRICE_FIELDS = ("input_cost_per_million", "output_cost_per_million")
_MODEL_FIELDS = {
    *_MODEL_TEXT_FIELDS,
    *_MODEL_TIMEOUT_FIELDS,
    *_MODEL_PRICE_FIELDS,
    "structured_outputs",
}
_BUDGET_COUNT_FIELDS = (
    "candidates_per_round",
    "rounds",
    "total_simulations",
)
_LEGACY_BUDGET_FIELDS = {
    "max_runtime_minutes",
    "planner_calls",
    "operator_calls",
    "max_model_cost_usd",
}
_BUDGET_FIELDS = {*_BUDGET_COUNT_FIELDS, *_LEGACY_BUDGET_FIELDS}


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    api_style: str
    model: str
    base_url: str
    reasoning: str
    secret_name: str
    structured_outputs: bool
    fallback_model: str
    input_cost_per_million: float | None
    output_cost_per_million: float | None
    connect_timeout_seconds: int = 10
    read_timeout_seconds: int = 300
    proxy_mode: str = "system"
    proxy_url: str = ""


@dataclass(frozen=True)
class AgentConfig:
    database_path: Path
    run_root: Path
    models: dict[ModelRole, ModelConfig]
    budget: Budget


def load_agent_config(path: str | None, *, require_models: bool = False) -> AgentConfig:
    raw = _require_object(load_config(path).get("agent"), "agent")
    _reject_unknown_keys(raw, _AGENT_FIELDS, "agent")
    model_values = _require_object(raw.get("models"), "agent.models")
    _reject_unknown_keys(model_values, {role.value for role in ModelRole}, "agent.models")
    models = {
        role: _load_model_config(
            role,
            _require_object(model_values.get(role.value), f"agent.models.{role.value}"),
        )
        for role in ModelRole
    }
    database_path = _configured_path(
        raw.get("database_path"),
        DEFAULT_AGENT_SQLITE_PATH,
        "agent.database_path",
    )
    run_root = _configured_path(raw.get("run_root"), DEFAULT_RESEARCH_RUNS_ROOT, "agent.run_root")
    return validate_agent_config(
        AgentConfig(
            database_path=database_path,
            run_root=run_root,
            models=models,
            budget=_load_budget(raw.get("budget")),
        ),
        require_models=require_models,
    )


def with_model_overrides(
    config: AgentConfig,
    *,
    planner_model: str | None = None,
    operator_model: str | None = None,
    require_models: bool = False,
) -> AgentConfig:
    validate_agent_config(config, require_models=False)
    overrides = {
        ModelRole.PLANNER: planner_model,
        ModelRole.OPERATOR: operator_model,
    }
    models = {
        role: replace(model, model=overrides[role]) if overrides[role] is not None else model
        for role, model in config.models.items()
    }
    return validate_agent_config(
        replace(config, models=models),
        require_models=require_models,
    )


def validate_agent_config(
    config: AgentConfig,
    *,
    require_models: bool = True,
) -> AgentConfig:
    if not isinstance(config, AgentConfig):
        raise ValueError("agent config must be an AgentConfig")
    for name in ("database_path", "run_root"):
        if not isinstance(getattr(config, name), Path):
            raise ValueError(f"agent.{name} must be a path")
    if not isinstance(config.models, dict):
        raise ValueError("agent.models must be an object")
    expected_roles = set(ModelRole)
    for role in config.models:
        if not isinstance(role, ModelRole) or role not in expected_roles:
            label = role.value if isinstance(role, ModelRole) else str(role)
            raise ValueError(f"agent.models.{label} is not supported")
    for role in ModelRole:
        model = config.models.get(role)
        if not isinstance(model, ModelConfig):
            raise ValueError(f"agent.models.{role.value} must be a ModelConfig")
        _validate_model_config(role, model)
    if not isinstance(config.budget, Budget):
        raise ValueError("agent.budget must be a Budget")
    if require_models:
        missing = [role.value for role in ModelRole if not config.models[role].model.strip()]
        if missing:
            raise ValueError(f"Missing model IDs for roles: {', '.join(missing)}")
    return config


def _load_model_config(role: ModelRole, values: dict[str, Any]) -> ModelConfig:
    path = f"agent.models.{role.value}"
    _reject_unknown_keys(values, _MODEL_FIELDS, path)
    return _validate_model_config(role, ModelConfig(**values))


def _validate_model_config(role: ModelRole, model: ModelConfig) -> ModelConfig:
    path = f"agent.models.{role.value}"
    for name in _MODEL_TEXT_FIELDS:
        if not isinstance(getattr(model, name), str):
            raise ValueError(f"{path}.{name} must be a string")
    if type(model.structured_outputs) is not bool:
        raise ValueError(f"{path}.structured_outputs must be a boolean")
    for name in _MODEL_TIMEOUT_FIELDS:
        value = getattr(model, name)
        if type(value) is not int or value <= 0 or value > 3600:
            raise ValueError(f"{path}.{name} must be an integer between 1 and 3600")
    for name in _MODEL_PRICE_FIELDS:
        value = getattr(model, name)
        if value is not None and (
            type(value) not in {int, float} or not isfinite(value) or value < 0
        ):
            raise ValueError(f"{path}.{name} must be a finite non-negative number or null")
    if model.provider not in _PROVIDERS:
        raise ValueError(f"{path}.provider has unsupported value: {model.provider}")
    if model.api_style not in _API_STYLES:
        raise ValueError(f"{path}.api_style has unsupported value: {model.api_style}")
    if model.proxy_mode not in {"system", "direct", "custom"}:
        raise ValueError(f"{path}.proxy_mode has unsupported value: {model.proxy_mode}")
    if model.proxy_mode == "custom":
        try:
            parsed_proxy_url = urlparse(model.proxy_url.strip())
        except ValueError as exc:
            raise ValueError(f"{path}.proxy_url must be an absolute http(s) URL") from exc
        if (
            parsed_proxy_url.scheme.lower() not in {"http", "https"}
            or not parsed_proxy_url.netloc
        ):
            raise ValueError(f"{path}.proxy_url must be an absolute http(s) URL")
    elif model.proxy_url.strip():
        raise ValueError(f"{path}.proxy_url must be blank unless proxy_mode is custom")
    if role is ModelRole.PLANNER and model.fallback_model.strip():
        raise ValueError(f"{path}.fallback_model must be blank")
    if model.model.strip():
        if not model.base_url.strip():
            raise ValueError(f"{path}.base_url must be nonblank when model is configured")
        try:
            parsed_base_url = urlparse(model.base_url.strip())
        except ValueError as exc:
            raise ValueError(f"{path}.base_url must be an absolute http(s) URL") from exc
        if parsed_base_url.scheme.lower() not in {"http", "https"} or not parsed_base_url.netloc:
            raise ValueError(f"{path}.base_url must be an absolute http(s) URL")
        if not model.secret_name.strip():
            raise ValueError(f"{path}.secret_name must be nonblank when model is configured")
    return model


def _load_budget(value: object) -> Budget:
    values = _require_object(value, "agent.budget")
    _reject_unknown_keys(values, _BUDGET_FIELDS, "agent.budget")
    for name in _BUDGET_COUNT_FIELDS:
        count = values.get(name)
        if type(count) is not int or count <= 0:
            raise ValueError(f"agent.budget.{name} must be a positive integer")
    return Budget(**{name: values[name] for name in _BUDGET_COUNT_FIELDS})


def _configured_path(value: object, default: Path, dotted_path: str) -> Path:
    if value is None or isinstance(value, str) and not value.strip():
        return default
    if not isinstance(value, (str, Path)):
        raise ValueError(f"{dotted_path} must be a string, path, or null")
    return Path(value)


def _require_object(value: object, dotted_path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{dotted_path} must be an object")
    return value


def _reject_unknown_keys(values: dict[str, Any], allowed: set[str], dotted_path: str) -> None:
    for key in values:
        if key not in allowed:
            raise ValueError(f"{dotted_path}.{key} is not supported")
