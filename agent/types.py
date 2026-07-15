from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ModelRole(StrEnum):
    PLANNER = "planner"
    OPERATOR = "operator"


class ScopeMode(StrEnum):
    MANUAL = "manual"
    AUTO = "auto"


class RunState(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    NEEDS_AUTH = "NEEDS_AUTH"
    PAUSED_MODEL = "PAUSED_MODEL"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    SUBMITTED = "SUBMITTED"
    REJECTED = "REJECTED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    NO_PROGRESS = "NO_PROGRESS"
    FAILED = "FAILED"


class WorkflowNode(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"
    G = "G"
    H = "H"
    I = "I"
    J = "J"
    K = "K"
    L = "L"
    M = "M"


@dataclass(frozen=True)
class NodeResult:
    node: WorkflowNode
    summary: dict[str, Any]
    artifact_ids: tuple[str, ...] = ()
    next_node: WorkflowNode | None = None
    run_state: RunState | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Budget:
    candidates_per_round: int = 8
    rounds: int = 5
    total_simulations: int = 40
    max_runtime_minutes: int = 180
    planner_calls: int = 20
    operator_calls: int = 100
    max_model_cost_usd: float | None = None

    def __post_init__(self) -> None:
        positive_fields = (
            "candidates_per_round",
            "rounds",
            "total_simulations",
            "max_runtime_minutes",
            "planner_calls",
            "operator_calls",
        )
        for name in positive_fields:
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.max_model_cost_usd is not None and self.max_model_cost_usd < 0:
            raise ValueError("max_model_cost_usd must be non-negative")


@dataclass(frozen=True)
class RunConfig:
    scope_mode: ScopeMode
    region: str | None = None
    delay: int | None = None
    universe: str | None = None
    neutralization: str | None = None
    budget: Budget = field(default_factory=Budget)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunConfig:
        values = dict(data)
        values["scope_mode"] = ScopeMode(values["scope_mode"])
        budget = values.get("budget", Budget())
        if isinstance(budget, dict):
            budget = Budget(**budget)
        if not isinstance(budget, Budget):
            raise ValueError("budget must be a Budget or object")
        values["budget"] = budget

        market_fields = ("region", "delay", "universe", "neutralization")
        if values["scope_mode"] is ScopeMode.MANUAL:
            missing = [name for name in market_fields if values.get(name) is None]
            if missing:
                raise ValueError(f"manual scope requires {', '.join(missing)}")
        elif any(values.get(name) is not None for name in market_fields):
            raise ValueError("auto scope must not pin market fields")
        return cls(**values)
