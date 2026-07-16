from __future__ import annotations

import unittest

from wqb_cli.agent.eval import EvaluationCase, EvaluationRunner, run_evaluation


def case(name: str, **overrides: object) -> EvaluationCase:
    value = {
        "terminal_state": "AWAITING_APPROVAL", "expected_terminal_state": "AWAITING_APPROVAL",
        "routes": [], "expected_routes": [], "candidate_count": 1, "valid_candidate_count": 1,
        "decision_count": 1, "cited_decision_count": 1, "invalid_citation_count": 0,
        "duplicate_count": 0, "blocked_duplicate_count": 0, "resume_replayed_side_effects": 0,
        "simulation_count": 1, "simulation_budget": 1, "approval_gate_violations": 0,
        "model_roles": ["planner"], "expected_model_roles": ["planner"],
        "blocked_operator_privilege_violations": 0, "network_used": False,
        "planner_calls": 1, "operator_calls": 0, "planner_tokens": 20, "operator_tokens": 0,
        "planner_latency_ms": 5, "operator_latency_ms": 0, "planner_failures": 0, "operator_failures": 0,
    }
    value.update(overrides)
    return EvaluationCase(name, lambda: dict(value))


class AgentEvalTests(unittest.TestCase):
    def test_offline_suite_reports_role_and_safety_metrics(self) -> None:
        result = EvaluationRunner([case("pass"), case("route", routes=["I"], expected_routes=["I"]), case("blocked", blocked_operator_privilege_violations=1)]).run()
        self.assertEqual(result["case_count"], 3)
        self.assertEqual(result["approval_gate_violations"], 0)
        self.assertEqual(result["role_routing_accuracy"], 1.0)
        self.assertEqual(result["diagnosis_route_accuracy"], 1.0)
        self.assertEqual(result["blocked_operator_privilege_violations"], 1)

    def test_violations_fail_evaluation(self) -> None:
        result = EvaluationRunner([case("bad", approval_gate_violations=1)]).run()
        self.assertIs(result["ok"], False)

    def test_live_requires_explicit_boundary(self) -> None:
        result = run_evaluation(live=True, max_simulations=1)
        self.assertIs(result["ok"], False)
        self.assertIs(result["refused"], True)

    def test_production_offline_suite_never_uses_network(self) -> None:
        result = run_evaluation()
        self.assertIs(result["ok"], True)
        self.assertIs(result["network_used"], False)


if __name__ == "__main__":
    unittest.main()
