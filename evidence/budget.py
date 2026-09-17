from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Mapping


POINT_PRECISION = 6


def _normalize_points(value: float | int) -> float:
    points = float(value)
    if not math.isfinite(points):
        raise ValueError("points must be finite")
    return round(points, POINT_PRECISION)


@dataclass(frozen=True)
class CostObservation:
    query_type: str
    points_before: float
    points_after: float
    success: bool
    timestamp: str

    def __post_init__(self) -> None:
        if not self.query_type.strip():
            raise ValueError("query_type must be non-empty")

        before = _normalize_points(self.points_before)
        after = _normalize_points(self.points_after)

        object.__setattr__(self, "points_before", before)
        object.__setattr__(self, "points_after", after)

        if before < 0 or after < 0:
            raise ValueError("points must be non-negative")

        if after > before:
            raise ValueError(
                "points_after exceeds points_before; "
                "calibration observation crossed a grant/recharge boundary"
            )

    @property
    def cost(self) -> float:
        return _normalize_points(
            self.points_before - self.points_after
        )


@dataclass(frozen=True)
class CostProfile:
    query_type: str
    sample_count: int
    p50: float
    p95: float
    maximum: float

    @classmethod
    def from_observations(
        cls,
        query_type: str,
        observations: Iterable[CostObservation],
    ) -> "CostProfile":
        costs = sorted(
            item.cost
            for item in observations
            if item.query_type == query_type and item.success
        )

        if not costs:
            raise ValueError(f"no observations for {query_type}")

        return cls(
            query_type=query_type,
            sample_count=len(costs),
            p50=_nearest_rank(costs, 0.50),
            p95=_nearest_rank(costs, 0.95),
            maximum=costs[-1],
        )


def _nearest_rank(
    sorted_values: list[float],
    percentile: float,
) -> float:
    if not 0 < percentile <= 1:
        raise ValueError("percentile must be in (0, 1]")

    rank = max(
        1,
        math.ceil(percentile * len(sorted_values)),
    )

    return sorted_values[rank - 1]


def estimate_plan_p95(
    plan: Mapping[str, int],
    profiles: Mapping[str, CostProfile],
) -> float:
    total = 0.0

    for query_type, count in plan.items():
        if count < 0:
            raise ValueError(
                f"negative call count for {query_type}"
            )

        profile = profiles.get(query_type)

        if profile is None:
            raise KeyError(
                f"missing cost profile for {query_type}"
            )

        total += profile.p95 * count

    return _normalize_points(total)


@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    purpose: str
    available_points: float
    allocation_points: float
    estimated_p95: float
    headroom: float
    reason: str


@dataclass(frozen=True)
class BudgetPolicy:
    """Run-level allocation policy; daily quota is read at runtime, never hard-coded."""

    research_fraction: float = 0.60
    diagnosis_fraction: float = 0.20
    reserve_fraction: float = 0.20

    def __post_init__(self) -> None:
        values = (
            self.research_fraction,
            self.diagnosis_fraction,
            self.reserve_fraction,
        )

        if any(value < 0 or value > 1 for value in values):
            raise ValueError(
                "budget fractions must be between 0 and 1"
            )

        if sum(values) > 1.0000001:
            raise ValueError(
                "budget fractions must sum to <= 1"
            )

    def decide(
        self,
        *,
        available_points: float,
        estimated_p95: float,
        purpose: str,
    ) -> BudgetDecision:
        available_points = _normalize_points(
            available_points
        )
        estimated_p95 = _normalize_points(
            estimated_p95
        )

        if available_points < 0 or estimated_p95 < 0:
            raise ValueError("points must be non-negative")

        if purpose == "research":
            fraction = self.research_fraction
        elif purpose == "diagnosis":
            fraction = self.diagnosis_fraction
        else:
            raise ValueError(
                "purpose must be 'research' or 'diagnosis'"
            )

        allocation = _normalize_points(
            available_points * fraction
        )
        headroom = _normalize_points(
            allocation - estimated_p95
        )
        allowed = headroom >= 0

        return BudgetDecision(
            allowed=allowed,
            purpose=purpose,
            available_points=available_points,
            allocation_points=allocation,
            estimated_p95=estimated_p95,
            headroom=headroom,
            reason=(
                "within_allocation"
                if allowed
                else "estimated_p95_exceeds_allocation"
            ),
        )


@dataclass(frozen=True)
class BalanceObservation:
    provider: str
    available_points: float
    observed_at: str
    source: str

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("provider must be non-empty")

        points = _normalize_points(
            self.available_points
        )
        object.__setattr__(
            self,
            "available_points",
            points,
        )

        if points < 0:
            raise ValueError(
                "available_points must be non-negative"
            )

        if not self.observed_at.strip():
            raise ValueError(
                "observed_at must be non-empty"
            )

        if not self.source.strip():
            raise ValueError("source must be non-empty")
