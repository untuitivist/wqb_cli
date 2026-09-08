from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class MechanismImpactReport:
    baseline_mechanisms: int
    wind_mechanisms: int
    eliminated_before_i: tuple[str, ...]
    added_in_wind_arm: tuple[str, ...]
    direction_changes: tuple[tuple[str, str, str], ...]
    falsification_strengthened: tuple[str, ...]
    reality_evidence_mechanisms: tuple[str, ...]
    baseline_candidate_count: int | None = None
    wind_candidate_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_mechanisms": self.baseline_mechanisms,
            "wind_mechanisms": self.wind_mechanisms,
            "eliminated_before_i": list(self.eliminated_before_i),
            "added_in_wind_arm": list(self.added_in_wind_arm),
            "direction_changes": [
                {"mechanism_id": mid, "baseline": before, "wind": after}
                for mid, before, after in self.direction_changes
            ],
            "falsification_strengthened": list(self.falsification_strengthened),
            "reality_evidence_mechanisms": list(self.reality_evidence_mechanisms),
            "baseline_candidate_count": self.baseline_candidate_count,
            "wind_candidate_count": self.wind_candidate_count,
            "candidate_reduction": (
                self.baseline_candidate_count - self.wind_candidate_count
                if self.baseline_candidate_count is not None
                and self.wind_candidate_count is not None
                else None
            ),
            "new_mechanism_violation": bool(self.added_in_wind_arm),
        }


def _normalize_contracts(payload: Any) -> dict[str, Mapping[str, Any]]:
    if isinstance(payload, Mapping):
        if "mechanisms" in payload and isinstance(payload["mechanisms"], list):
            items = payload["mechanisms"]
        elif "mechanism_contracts" in payload and isinstance(payload["mechanism_contracts"], list):
            items = payload["mechanism_contracts"]
        elif all(isinstance(value, Mapping) for value in payload.values()):
            items = []
            for key, value in payload.items():
                item = dict(value)
                item.setdefault("mechanism_id", str(key))
                items.append(item)
        else:
            raise ValueError("cannot identify mechanism contract collection")
    elif isinstance(payload, list):
        items = payload
    else:
        raise ValueError("mechanism contracts must be a list or mapping")

    result: dict[str, Mapping[str, Any]] = {}
    for item in items:
        if not isinstance(item, Mapping):
            raise ValueError("each mechanism contract must be an object")
        mechanism_id = str(item.get("mechanism_id") or "").strip()
        if not mechanism_id:
            raise ValueError("mechanism contract missing mechanism_id")
        if mechanism_id in result:
            raise ValueError(f"duplicate mechanism_id: {mechanism_id}")
        result[mechanism_id] = item
    return result


def _condition_count(item: Mapping[str, Any]) -> int:
    conditions = item.get("falsification_conditions")
    if conditions is None:
        return 0
    if isinstance(conditions, (list, tuple)):
        return len(conditions)
    if isinstance(conditions, str):
        return 1 if conditions.strip() else 0
    return 1


def _reality_refs(item: Mapping[str, Any]) -> tuple[str, ...]:
    refs = item.get("reality_evidence_refs") or ()
    if isinstance(refs, str):
        refs = [refs]
    if not isinstance(refs, (list, tuple)):
        return ()
    return tuple(str(ref) for ref in refs if str(ref).strip())


def _candidate_count(payload: Any | None) -> int | None:
    if payload is None:
        return None
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, Mapping):
        for key in ("candidates", "expression_candidates", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
    raise ValueError("cannot identify expression candidate collection")


def compare_mechanism_arms(
    baseline_contracts: Any,
    wind_contracts: Any,
    *,
    baseline_candidates: Any | None = None,
    wind_candidates: Any | None = None,
) -> MechanismImpactReport:
    baseline = _normalize_contracts(baseline_contracts)
    wind = _normalize_contracts(wind_contracts)

    baseline_ids = set(baseline)
    wind_ids = set(wind)
    common = sorted(baseline_ids & wind_ids)

    direction_changes: list[tuple[str, str, str]] = []
    strengthened: list[str] = []
    reality: list[str] = []
    for mechanism_id in common:
        before = str(baseline[mechanism_id].get("direction_status") or "")
        after = str(wind[mechanism_id].get("direction_status") or "")
        if before != after:
            direction_changes.append((mechanism_id, before, after))
        if _condition_count(wind[mechanism_id]) > _condition_count(baseline[mechanism_id]):
            strengthened.append(mechanism_id)
        if _reality_refs(wind[mechanism_id]):
            reality.append(mechanism_id)

    for mechanism_id in sorted(wind_ids - baseline_ids):
        if _reality_refs(wind[mechanism_id]):
            reality.append(mechanism_id)

    return MechanismImpactReport(
        baseline_mechanisms=len(baseline),
        wind_mechanisms=len(wind),
        eliminated_before_i=tuple(sorted(baseline_ids - wind_ids)),
        added_in_wind_arm=tuple(sorted(wind_ids - baseline_ids)),
        direction_changes=tuple(direction_changes),
        falsification_strengthened=tuple(strengthened),
        reality_evidence_mechanisms=tuple(sorted(set(reality))),
        baseline_candidate_count=_candidate_count(baseline_candidates),
        wind_candidate_count=_candidate_count(wind_candidates),
    )


@dataclass(frozen=True)
class PilotArmMetrics:
    simulation_attempts: int
    valid_simulations: int
    reached_l: int
    failure_count: int
    wall_clock_seconds: float
    wind_points_consumed: float = 0.0

    def __post_init__(self) -> None:
        integer_values = (
            self.simulation_attempts,
            self.valid_simulations,
            self.reached_l,
            self.failure_count,
        )
        wind_points = float(self.wind_points_consumed)
        object.__setattr__(
            self,
            "wind_points_consumed",
            wind_points,
        )
        if (
            any(value < 0 for value in integer_values)
            or self.wall_clock_seconds < 0
            or not math.isfinite(wind_points)
            or wind_points < 0
        ):
            raise ValueError(
                "pilot metrics must be non-negative and finite"
            )
        if self.valid_simulations > self.simulation_attempts:
            raise ValueError("valid_simulations cannot exceed simulation_attempts")
        if self.reached_l > self.valid_simulations:
            raise ValueError("reached_l cannot exceed valid_simulations")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "PilotArmMetrics":
        return cls(
            simulation_attempts=int(payload["simulation_attempts"]),
            valid_simulations=int(payload["valid_simulations"]),
            reached_l=int(payload["reached_l"]),
            failure_count=int(payload["failure_count"]),
            wall_clock_seconds=float(payload["wall_clock_seconds"]),
            wind_points_consumed=float(payload.get("wind_points_consumed", 0.0)),
        )

    @property
    def valid_rate(self) -> float | None:
        if self.simulation_attempts == 0:
            return None
        return self.valid_simulations / self.simulation_attempts

    @property
    def reached_l_rate(self) -> float | None:
        if self.valid_simulations == 0:
            return None
        return self.reached_l / self.valid_simulations

    @property
    def failure_density(self) -> float | None:
        if self.simulation_attempts == 0:
            return None
        return self.failure_count / self.simulation_attempts

    def to_dict(self) -> dict[str, Any]:
        return {
            "simulation_attempts": self.simulation_attempts,
            "valid_simulations": self.valid_simulations,
            "valid_rate": self.valid_rate,
            "reached_l": self.reached_l,
            "reached_l_rate": self.reached_l_rate,
            "failure_count": self.failure_count,
            "failure_density": self.failure_density,
            "wall_clock_seconds": self.wall_clock_seconds,
            "wind_points_consumed": self.wind_points_consumed,
        }


@dataclass(frozen=True)
class PilotOutcomeComparison:
    baseline: PilotArmMetrics
    wind: PilotArmMetrics

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline": self.baseline.to_dict(),
            "wind": self.wind.to_dict(),
            "delta": {
                "simulation_attempts": self.wind.simulation_attempts - self.baseline.simulation_attempts,
                "valid_simulations": self.wind.valid_simulations - self.baseline.valid_simulations,
                "valid_rate": _rate_delta(self.wind.valid_rate, self.baseline.valid_rate),
                "reached_l": self.wind.reached_l - self.baseline.reached_l,
                "reached_l_rate": _rate_delta(self.wind.reached_l_rate, self.baseline.reached_l_rate),
                "failure_count": self.wind.failure_count - self.baseline.failure_count,
                "failure_density": _rate_delta(self.wind.failure_density, self.baseline.failure_density),
                "wall_clock_seconds": self.wind.wall_clock_seconds - self.baseline.wall_clock_seconds,
                "wind_points_consumed": self.wind.wind_points_consumed - self.baseline.wind_points_consumed,
            },
        }


def _rate_delta(after: float | None, before: float | None) -> float | None:
    if after is None or before is None:
        return None
    return after - before


def compare_pilot_outcomes(
    baseline_metrics: Mapping[str, Any],
    wind_metrics: Mapping[str, Any],
) -> PilotOutcomeComparison:
    return PilotOutcomeComparison(
        baseline=PilotArmMetrics.from_mapping(baseline_metrics),
        wind=PilotArmMetrics.from_mapping(wind_metrics),
    )
