from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping

from .budget import BudgetDecision, BudgetPolicy, CostProfile, estimate_plan_p95
from .providers.wind.contract import require_wind_access


MIN_CALIBRATION_SAMPLES = 3


@dataclass(frozen=True)
class RealityCheckSpec:
    mechanism_id: str
    node: str
    purpose: str
    server_type: str
    tool_name: str
    cost_profile_key: str | None = None
    allow_expensive_fallback: bool = False
    fallback_reason: str | None = None

    @property
    def query_type(self) -> str:
        return f"{self.server_type}.{self.tool_name}"

    @property
    def cost_key(self) -> str:
        value = (self.cost_profile_key or self.query_type).strip()
        if not value:
            raise RealityPlanError("cost_profile_key must be non-empty")
        return value


@dataclass(frozen=True)
class RealityPlanAssessment:
    call_count: int
    mechanism_count: int
    estimated_p95: float
    budget: BudgetDecision
    query_counts: tuple[tuple[str, int], ...]


class RealityPlanError(ValueError):
    pass


def assess_wind_reality_plan(
    specs: Iterable[RealityCheckSpec],
    *,
    profiles: Mapping[str, CostProfile],
    available_points: float,
    budget_policy: BudgetPolicy | None = None,
) -> RealityPlanAssessment:
    resolved = tuple(specs)
    if not resolved:
        raise RealityPlanError("reality plan must contain at least one check")

    mechanisms = Counter(item.mechanism_id for item in resolved)
    if "" in mechanisms or any(not key.strip() for key in mechanisms):
        raise RealityPlanError("mechanism_id must be non-empty")

    # G/H are research-budget consumers; K is diagnosis-budget only. Mixing the
    # two in one plan makes the budget standing ambiguous and is rejected.
    purposes: set[str] = set()
    for item in resolved:
        decision = require_wind_access(item.node, item.purpose)
        purposes.add("diagnosis" if decision.standing == "diagnostic" else "research")

    if len(purposes) != 1:
        raise RealityPlanError("research and diagnosis Wind calls cannot share one budget plan")
    budget_purpose = next(iter(purposes))

    if budget_purpose == "research":
        if len(mechanisms) > 6:
            raise RealityPlanError("research plan exceeds 6 mechanisms")
        excessive = {key: count for key, count in mechanisms.items() if count > 3}
        if excessive:
            raise RealityPlanError(
                f"research plan exceeds 3 Wind calls per mechanism: {excessive}"
            )
    else:
        if len(resolved) > 3:
            raise RealityPlanError("diagnosis plan exceeds 3 Wind calls")

    for item in resolved:
        if item.server_type == "analytics_data":
            reason = (item.fallback_reason or "").strip()
            if not item.allow_expensive_fallback or not reason:
                raise RealityPlanError(
                    "analytics_data requires allow_expensive_fallback=true and a non-empty fallback_reason"
                )

    query_counts = Counter(item.cost_key for item in resolved)
    for cost_key in query_counts:
        profile = profiles.get(cost_key)
        if profile is None:
            raise KeyError(f"missing cost profile for {cost_key}")
        if profile.sample_count < MIN_CALIBRATION_SAMPLES:
            raise RealityPlanError(
                f"insufficient calibration for {cost_key}: "
                f"{profile.sample_count} < {MIN_CALIBRATION_SAMPLES} successful samples"
            )
    estimate = estimate_plan_p95(query_counts, profiles)
    policy = budget_policy or BudgetPolicy()
    decision = policy.decide(
        available_points=available_points,
        estimated_p95=estimate,
        purpose=budget_purpose,
    )
    return RealityPlanAssessment(
        call_count=len(resolved),
        mechanism_count=len(mechanisms),
        estimated_p95=estimate,
        budget=decision,
        query_counts=tuple(sorted(query_counts.items())),
    )
