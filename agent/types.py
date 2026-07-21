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
    NEEDS_DATA = "NEEDS_DATA"
    PAUSED_MODEL = "PAUSED_MODEL"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    SUBMITTED = "SUBMITTED"
    REJECTED = "REJECTED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    NO_PROGRESS = "NO_PROGRESS"
    STOPPED = "STOPPED"
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

    def __post_init__(self) -> None:
        positive_fields = (
            "candidates_per_round",
            "rounds",
            "total_simulations",
        )
        for name in positive_fields:
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class RunConfig:
    scope_mode: ScopeMode
    region: str | None = None
    delay: int | None = None
    universe: str | None = None
    neutralization: str | None = None
    dataset_id: str | None = None
    budget: Budget = field(default_factory=Budget)

    def __post_init__(self) -> None:
        if not isinstance(self.scope_mode, ScopeMode):
            raise ValueError("scope_mode must be a ScopeMode")
        if not isinstance(self.budget, Budget):
            raise ValueError("budget must be a Budget")
        if self.dataset_id is not None and (
            not isinstance(self.dataset_id, str) or not self.dataset_id.strip()
        ):
            raise ValueError("dataset_id must be a nonblank string when provided")

        if self.scope_mode is ScopeMode.MANUAL:
            missing = [
                name
                for name in ("region", "universe", "neutralization")
                if not isinstance(getattr(self, name), str) or not getattr(self, name).strip()
            ]
            if type(self.delay) is not int or self.delay not in {0, 1}:
                missing.append("delay")
            if missing:
                raise ValueError(f"manual scope requires {', '.join(missing)}")
        else:
            if self.region is not None and (
                not isinstance(self.region, str) or not self.region.strip()
            ):
                raise ValueError("auto scope region must be a nonblank string when provided")
            pinned_fields = ("delay", "universe", "neutralization")
            if any(getattr(self, name) is not None for name in pinned_fields):
                raise ValueError("auto scope must not pin delay, universe, or neutralization")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunConfig:
        values = dict(data)
        values["scope_mode"] = ScopeMode(values["scope_mode"])
        budget = values.get("budget", Budget())
        if isinstance(budget, dict):
            budget = Budget(
                **{
                    key: budget[key]
                    for key in ("candidates_per_round", "rounds", "total_simulations")
                    if key in budget
                }
            )
        if not isinstance(budget, Budget):
            raise ValueError("budget must be a Budget or object")
        values["budget"] = budget
        return cls(**values)
