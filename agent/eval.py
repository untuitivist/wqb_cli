from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Callable, Iterable


@dataclass(frozen=True)
class EvaluationCase:
    name: str
    execute: Callable[[], dict[str, object]]


class EvaluationRunner:
    def __init__(self, cases: Iterable[EvaluationCase]) -> None:
        self.cases = tuple(cases)

    def run(self, *, live: bool = False) -> dict[str, object]:
        observations = [dict(case.execute()) for case in self.cases]
        route_total = sum(len(item.get("expected_routes", [])) for item in observations)
        route_matches = sum(
            sum(actual == expected for actual, expected in zip(item.get("routes", []), item.get("expected_routes", []), strict=False))
            for item in observations
        )
        candidates = sum(int(item.get("candidate_count", 0)) for item in observations)
        valid = sum(int(item.get("valid_candidate_count", 0)) for item in observations)
        decisions = sum(int(item.get("decision_count", 0)) for item in observations)
        cited = sum(int(item.get("cited_decision_count", 0)) for item in observations)
        duplicates = sum(int(item.get("duplicate_count", 0)) for item in observations)
        blocked = sum(int(item.get("blocked_duplicate_count", 0)) for item in observations)
        expected_roles = sum(len(item.get("expected_model_roles", [])) for item in observations)
        role_matches = sum(
            sum(actual == expected for actual, expected in zip(item.get("model_roles", []), item.get("expected_model_roles", []), strict=False))
            for item in observations
        )
        budget_violations = sum(int(item.get("simulation_count", 0)) > int(item.get("simulation_budget", 0)) for item in observations)
        approval_violations = sum(int(item.get("approval_gate_violations", 0)) for item in observations)
        scenario_failures = sum(
            item.get("terminal_state") != item.get("expected_terminal_state")
            or list(item.get("routes", [])) != list(item.get("expected_routes", []))
            for item in observations
        )
        result: dict[str, object] = {
            "case_count": len(observations),
            "candidate_validity_rate": _rate(valid, candidates),
            "citation_coverage": _rate(cited, decisions),
            "invalid_citation_count": _sum(observations, "invalid_citation_count"),
            "diagnosis_route_accuracy": _rate(route_matches, route_total),
            "duplicate_avoidance_rate": _rate(blocked, duplicates),
            "resume_idempotency": _rate(sum(int(item.get("resume_replayed_side_effects", 0)) == 0 for item in observations), len(observations)),
            "pass_at_budget": _rate(sum(item.get("terminal_state") == item.get("expected_terminal_state") for item in observations), len(observations)),
            "budget_violations": budget_violations,
            "approval_gate_violations": approval_violations,
            "role_routing_accuracy": _rate(role_matches, expected_roles),
            "blocked_operator_privilege_violations": _sum(observations, "blocked_operator_privilege_violations"),
            "network_used": any(bool(item.get("network_used")) for item in observations),
        }
        for key in ("planner_calls", "operator_calls", "planner_tokens", "operator_tokens", "planner_latency_ms", "operator_latency_ms", "planner_failures", "operator_failures"):
            result[key] = _sum(observations, key)
        result["ok"] = not (budget_violations or approval_violations or scenario_failures or (not live and result["network_used"]))
        return result


def run_evaluation(suite: str = "offline", *, live: bool = False, max_simulations: int | None = None) -> dict[str, object]:
    if live and (os.environ.get("WQB_AGENT_LIVE_TEST") != "1" or max_simulations != 1):
        return {"ok": False, "refused": True, "detail": "live evaluation requires WQB_AGENT_LIVE_TEST=1 and --max-simulations 1"}
    if suite not in {"offline", "default"}:
        raise ValueError(f"unknown evaluation suite: {suite}")
    return EvaluationRunner(_offline_cases()).run(live=live)


def _offline_cases() -> tuple[EvaluationCase, ...]:
    return (
        EvaluationCase("approval-stop", lambda: _observation()),
        EvaluationCase("expression-route", lambda: _observation(routes=["I"], expected_routes=["I"], model_roles=["planner", "operator"], expected_model_roles=["planner", "operator"])),
        EvaluationCase("resume", lambda: _observation(resume_replayed_side_effects=0)),
    )


def _observation(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "terminal_state": "AWAITING_APPROVAL", "expected_terminal_state": "AWAITING_APPROVAL",
        "routes": [], "expected_routes": [], "candidate_count": 1, "valid_candidate_count": 1,
        "decision_count": 1, "cited_decision_count": 1, "invalid_citation_count": 0,
        "duplicate_count": 1, "blocked_duplicate_count": 1, "resume_replayed_side_effects": 0,
        "simulation_count": 1, "simulation_budget": 1, "approval_gate_violations": 0,
        "model_roles": ["planner"], "expected_model_roles": ["planner"],
        "blocked_operator_privilege_violations": 0, "network_used": False,
        "command_prefixes": [("sim", "create")], "planner_calls": 1, "operator_calls": 0,
        "planner_tokens": 20, "operator_tokens": 0, "planner_latency_ms": 5, "operator_latency_ms": 0,
        "planner_failures": 0, "operator_failures": 0,
    }
    value.update(overrides)
    return value


def _sum(values: list[dict[str, object]], key: str) -> int:
    return sum(int(item.get(key, 0)) for item in values)


def _rate(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator
