from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from ..core.config_store import load_config
from ..core.paths import DEFAULT_AGENT_SQLITE_PATH, DEFAULT_RESEARCH_RUNS_ROOT
from .types import Budget, ModelRole


_PROVIDERS = {"openai", "openai-compatible"}
_API_STYLES = {"responses", "chat_completions"}


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


@dataclass(frozen=True)
class AgentConfig:
    database_path: Path
    run_root: Path
    models: dict[ModelRole, ModelConfig]
    budget: Budget


def load_agent_config(path: str | None, *, require_models: bool = False) -> AgentConfig:
    raw = load_config(path)["agent"]
    model_values = raw["models"]
    models = {
        role: _load_model_config(role, model_values[role.value])
        for role in ModelRole
    }
    if require_models:
        missing = [role.value for role in ModelRole if not models[role].model]
        if missing:
            raise ValueError(f"Missing model IDs for roles: {', '.join(missing)}")

    database_path = _configured_path(raw["database_path"], DEFAULT_AGENT_SQLITE_PATH)
    run_root = _configured_path(raw["run_root"], DEFAULT_RESEARCH_RUNS_ROOT)
    return AgentConfig(
        database_path=database_path,
        run_root=run_root,
        models=models,
        budget=Budget(**raw["budget"]),
    )


def with_model_overrides(
    config: AgentConfig,
    *,
    planner_model: str | None = None,
    operator_model: str | None = None,
) -> AgentConfig:
    overrides = {
        ModelRole.PLANNER: planner_model,
        ModelRole.OPERATOR: operator_model,
    }
    models = {
        role: replace(model, model=overrides[role]) if overrides[role] is not None else model
        for role, model in config.models.items()
    }
    return replace(config, models=models)


def _load_model_config(role: ModelRole, values: dict[str, object]) -> ModelConfig:
    model = ModelConfig(**values)
    if model.provider not in _PROVIDERS:
        raise ValueError(f"Invalid provider for {role.value}: {model.provider}")
    if model.api_style not in _API_STYLES:
        raise ValueError(f"Invalid api_style for {role.value}: {model.api_style}")
    if role is ModelRole.PLANNER and model.fallback_model:
        raise ValueError("Planner fallback_model must be blank")
    for name in ("input_cost_per_million", "output_cost_per_million"):
        value = getattr(model, name)
        if value is not None and value < 0:
            raise ValueError(f"{role.value} {name} must be non-negative")
    return model


def _configured_path(value: object, default: Path) -> Path:
    if value is None or not str(value).strip():
        return default
    return Path(str(value))
