from __future__ import annotations

from collections import Counter, deque
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from agent.policy import AgentPolicy
from agent.store import AgentStore
from agent.types import Budget, NodeResult, RunConfig, RunState, ScopeMode, WorkflowNode
from wqb_cli.agent.models import ModelTransportError


def result(
    node: WorkflowNode,
    next_node: WorkflowNode | None,
    *,
    run_state: RunState | None = None,
    **payload: object,
) -> NodeResult:
    return NodeResult(
        node=node,
        summary={"ok": True},
        next_node=next_node,
        run_state=run_state,
        payload=dict(payload),
    )


class ScriptedNodeRunner:
    def __init__(self, script: dict[WorkflowNode, list[object]]) -> None:
        self.script = {node: deque(values) for node, values in script.items()}
        self.calls: Counter[WorkflowNode] = Counter()
        self.contexts: list[tuple[WorkflowNode, dict[str, object]]] = []

    def run(
        self, run_id: str, node: WorkflowNode, context: dict[str, object]
    ) -> NodeResult:
        self.calls[node] += 1
        self.contexts.append((node, context))
        value = self.script[node].popleft()
        if isinstance(value, BaseException):
            raise value
        assert isinstance(value, NodeResult)
        return value


def successful_script() -> dict[WorkflowNode, list[object]]:
    scope = {
        "region": "USA",
        "delay": 1,
        "universe": "TOP3000",
        "neutralization": "SUBINDUSTRY",
        "category": "PV",
    }
    return {
        WorkflowNode.A: [result(WorkflowNode.A, WorkflowNode.B)],
        WorkflowNode.B: [result(WorkflowNode.B, WorkflowNode.C)],
        WorkflowNode.C: [result(WorkflowNode.C, WorkflowNode.D)],
        WorkflowNode.D: [result(WorkflowNode.D, WorkflowNode.F, scope=scope)],
        WorkflowNode.F: [result(WorkflowNode.F, WorkflowNode.G)],
        WorkflowNode.G: [result(WorkflowNode.G, WorkflowNode.H)],
        WorkflowNode.H: [result(WorkflowNode.H, WorkflowNode.I)],
        WorkflowNode.I: [
            result(
                WorkflowNode.I,
                WorkflowNode.J,
                new_fingerprints=["fp-1"],
                accepted=[{"fingerprint": "fp-1", "field_ids": ["close"]}],
            )
        ],
        WorkflowNode.J: [result(WorkflowNode.J, WorkflowNode.K)],
        WorkflowNode.K: [result(WorkflowNode.K, WorkflowNode.L)],
        WorkflowNode.L: [
            result(
                WorkflowNode.L,
                WorkflowNode.M,
                alpha_id="ALPHA1",
                final_report={"alpha_id": "ALPHA1"},
            )
        ],
    }


class AgentCoordinatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.store = AgentStore(Path(self.temporary.name) / "agent.sqlite3")
        self.store.initialize()
        self.submission = Mock()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def config(*, budget: Budget | None = None) -> RunConfig:
        return RunConfig(
            scope_mode=ScopeMode.MANUAL,
            region="USA",
            delay=1,
            universe="TOP3000",
            neutralization="SUBINDUSTRY",
            budget=budget or Budget(),
        )

    def coordinator(
        self,
        script: dict[WorkflowNode, list[object]],
        *,
        budget: Budget | None = None,
    ):
        from agent.coordinator import AgentCoordinator

        runner = ScriptedNodeRunner(script)
        coordinator = AgentCoordinator(
            store=self.store,
            policy=AgentPolicy(budget or Budget()),
            node_runner=runner,
            submission=self.submission,
        )
        return coordinator, runner

    def attempts(self, run_id: str, node: WorkflowNode) -> list[tuple[str, int]]:
        with closing(self.store.connect()) as connection:
            rows = connection.execute(
                "SELECT status, attempt_number FROM node_attempts "
                "WHERE run_id = ? AND node = ? ORDER BY attempt_number",
                (run_id, node.value),
            ).fetchall()
        return [(row["status"], row["attempt_number"]) for row in rows]

    def test_success_stops_at_approval_and_loads_rules_each_call(self) -> None:
        coordinator, runner = self.coordinator(successful_script())

        run = coordinator.run_manual(run_id="run-1", scope=self.config())

        self.assertEqual(run.state, RunState.AWAITING_APPROVAL)
        self.submission.submit.assert_not_called()
        self.assertNotIn(WorkflowNode.E if hasattr(WorkflowNode, "E") else "E", runner.calls)
        self.assertEqual(runner.calls[WorkflowNode.K], 1)
        for node, context in runner.contexts:
            manifest = context["context_manifest"]
            self.assertEqual(manifest["node"], node.value)
            self.assertIn("rules_sha256", manifest)
            self.assertIn("rules", manifest)
        self.assertEqual(self.attempts("run-1", WorkflowNode.L), [("COMPLETED", 1)])

    def test_k_to_i_creates_a_new_attempt(self) -> None:
        script = successful_script()
        script[WorkflowNode.I] = [
            result(WorkflowNode.I, WorkflowNode.J, new_fingerprints=["fp-1"]),
            result(WorkflowNode.I, WorkflowNode.J, new_fingerprints=["fp-2"]),
        ]
        script[WorkflowNode.J] = [
            result(WorkflowNode.J, WorkflowNode.K),
            result(WorkflowNode.J, WorkflowNode.K),
        ]
        script[WorkflowNode.K] = [
            result(WorkflowNode.K, WorkflowNode.I),
            result(WorkflowNode.K, WorkflowNode.L),
        ]
        coordinator, _ = self.coordinator(script)

        run = coordinator.run_manual(run_id="run-1", scope=self.config())

        self.assertEqual(run.state, RunState.AWAITING_APPROVAL)
        self.assertEqual(
            self.attempts("run-1", WorkflowNode.I),
            [("COMPLETED", 1), ("COMPLETED", 2)],
        )
        with closing(self.store.connect()) as connection:
            routes = connection.execute(
                "SELECT next_node FROM diagnoses WHERE run_id = ? ORDER BY id",
                ("run-1",),
            ).fetchall()
        self.assertEqual([row["next_node"] for row in routes], ["I", "L"])

    def test_two_k_cycles_without_new_fingerprint_stop_no_progress(self) -> None:
        script = successful_script()
        script[WorkflowNode.I] = [
            result(WorkflowNode.I, WorkflowNode.J, new_fingerprints=[]),
            result(WorkflowNode.I, WorkflowNode.J, new_fingerprints=[]),
        ]
        script[WorkflowNode.J] = [
            result(WorkflowNode.J, WorkflowNode.K),
            result(WorkflowNode.J, WorkflowNode.K),
        ]
        script[WorkflowNode.K] = [
            result(WorkflowNode.K, WorkflowNode.I),
            result(WorkflowNode.K, WorkflowNode.I),
        ]
        coordinator, runner = self.coordinator(script)

        run = coordinator.run_manual(run_id="run-1", scope=self.config())

        self.assertEqual(run.state, RunState.NO_PROGRESS)
        self.submission.finalize_record_only.assert_called_once()
        self.submission.submit.assert_not_called()
        self.assertEqual(runner.calls[WorkflowNode.I], 2)

    def test_hard_budget_stops_record_only_before_node_call(self) -> None:
        budget = Budget(rounds=1)
        coordinator, runner = self.coordinator(successful_script(), budget=budget)
        original = self.store.usage_summary

        def exhausted(run_id: str):
            usage = original(run_id)
            usage["coordinator"] = {"rounds": 1, "simulations": 0}
            return usage

        self.store.usage_summary = exhausted  # type: ignore[method-assign]

        run = coordinator.run_manual(run_id="run-1", scope=self.config(budget=budget))

        self.assertEqual(run.state, RunState.BUDGET_EXHAUSTED)
        self.assertEqual(sum(runner.calls.values()), 0)
        self.submission.finalize_record_only.assert_called_once()
        self.submission.submit.assert_not_called()

    def test_invalid_route_and_returned_node_fail_closed(self) -> None:
        for returned in (
            result(WorkflowNode.K, WorkflowNode.M),
            result(WorkflowNode.G, WorkflowNode.B),
        ):
            with self.subTest(returned=returned):
                script = successful_script()
                if returned.node is WorkflowNode.K:
                    script[WorkflowNode.K] = [returned]
                else:
                    script[WorkflowNode.F] = [returned]
                coordinator, _ = self.coordinator(script)
                run_id = f"run-{returned.node.value}"

                run = coordinator.run_manual(run_id=run_id, scope=self.config())

                self.assertEqual(run.state, RunState.FAILED)
                self.submission.submit.assert_not_called()

    def test_manual_and_auto_scope_are_persisted_and_locked(self) -> None:
        from agent.coordinator import AgentCoordinator

        configs = (
            self.config(),
            RunConfig(scope_mode=ScopeMode.AUTO),
        )
        for index, config in enumerate(configs):
            with self.subTest(mode=config.scope_mode):
                script = successful_script()
                script[WorkflowNode.F] = [
                    result(
                        WorkflowNode.F,
                        WorkflowNode.G,
                        scope={"region": "CHN"},
                    )
                ]
                runner = ScriptedNodeRunner(script)
                coordinator = AgentCoordinator(
                    store=self.store,
                    policy=AgentPolicy(config.budget),
                    node_runner=runner,
                    submission=self.submission,
                )
                run_id = f"scope-{index}"

                run = (
                    coordinator.run_manual(run_id=run_id, scope=config)
                    if config.scope_mode is ScopeMode.MANUAL
                    else coordinator.run_auto(run_id=run_id, config=config)
                )

                self.assertEqual(run.state, RunState.FAILED)
                self.assertEqual(self.store.get_run(run_id).config, config)

    def test_auth_and_planner_failures_pause_without_submission(self) -> None:
        cases = (
            (
                result(
                    WorkflowNode.A,
                    None,
                    run_state=RunState.NEEDS_AUTH,
                ),
                RunState.NEEDS_AUTH,
            ),
            (ModelTransportError("planner retries exhausted"), RunState.PAUSED_MODEL),
        )
        for index, (outcome, expected) in enumerate(cases):
            with self.subTest(expected=expected):
                script = successful_script()
                script[WorkflowNode.A] = [outcome]
                coordinator, runner = self.coordinator(script)

                run = coordinator.run_manual(
                    run_id=f"pause-{index}", scope=self.config()
                )

                self.assertEqual(run.state, expected)
                self.assertEqual(sum(runner.calls.values()), 1)
                self.submission.submit.assert_not_called()

    def test_model_pause_resumes_the_interrupted_node(self) -> None:
        script = successful_script()
        script[WorkflowNode.B] = [
            ModelTransportError("planner retries exhausted"),
            result(WorkflowNode.B, WorkflowNode.C),
        ]
        coordinator, runner = self.coordinator(script)

        paused = coordinator.run_manual(run_id="run-1", scope=self.config())
        resumed = coordinator.resume("run-1")

        self.assertEqual(paused.state, RunState.PAUSED_MODEL)
        self.assertEqual(resumed.state, RunState.AWAITING_APPROVAL)
        self.assertEqual(runner.calls[WorkflowNode.A], 1)
        self.assertEqual(runner.calls[WorkflowNode.B], 2)

    def test_resume_after_j_uses_persisted_route(self) -> None:
        coordinator, runner = self.coordinator(successful_script())
        self.store.create_run("run-1", self.config())
        self.store.transition("run-1", RunState.RUNNING, "test")
        path = [
            WorkflowNode.A,
            WorkflowNode.B,
            WorkflowNode.C,
            WorkflowNode.D,
            WorkflowNode.F,
            WorkflowNode.G,
            WorkflowNode.H,
            WorkflowNode.I,
            WorkflowNode.J,
        ]
        for node in path:
            attempt = self.store.start_node_attempt("run-1", node)
            next_node = (
                WorkflowNode.K
                if node is WorkflowNode.J
                else path[path.index(node) + 1]
            )
            self.store.finish_node_attempt(
                attempt,
                "COMPLETED",
                {"_coordinator": {"next_node": next_node.value, "payload": {}}},
            )
        runner.script = {
            WorkflowNode.K: deque([result(WorkflowNode.K, WorkflowNode.L)]),
            WorkflowNode.L: deque(
                [result(WorkflowNode.L, WorkflowNode.M, alpha_id="ALPHA1")]
            ),
        }

        run = coordinator.resume("run-1")

        self.assertEqual(run.state, RunState.AWAITING_APPROVAL)
        self.assertEqual(runner.calls[WorkflowNode.J], 0)
        self.assertEqual(runner.calls[WorkflowNode.K], 1)

    def test_incomplete_j_is_reentered_with_persisted_simulations(self) -> None:
        coordinator, runner = self.coordinator(successful_script())
        self.store.create_run("run-1", self.config())
        self.store.transition("run-1", RunState.RUNNING, "test")
        attempt = self.store.start_node_attempt("run-1", WorkflowNode.J)
        self.store.record_simulation("run-1", "SIM-1", "RUNNING")
        runner.script = {
            WorkflowNode.J: deque([result(WorkflowNode.J, WorkflowNode.K)]),
            WorkflowNode.K: deque([result(WorkflowNode.K, WorkflowNode.L)]),
            WorkflowNode.L: deque(
                [result(WorkflowNode.L, WorkflowNode.M, alpha_id="ALPHA1")]
            ),
        }

        run = coordinator.resume("run-1")

        self.assertEqual(run.state, RunState.AWAITING_APPROVAL)
        self.assertEqual(attempt.status, "RUNNING")
        j_context = next(context for node, context in runner.contexts if node is WorkflowNode.J)
        self.assertEqual(j_context["resume_simulation_ids"], ["SIM-1"])
        self.assertEqual(self.attempts("run-1", WorkflowNode.J)[-1], ("COMPLETED", 2))

    def test_awaiting_approval_and_terminal_resume_do_no_work(self) -> None:
        coordinator, runner = self.coordinator(successful_script())
        for run_id, state in (
            ("pending", RunState.AWAITING_APPROVAL),
            ("terminal", RunState.NO_PROGRESS),
        ):
            self.store.create_run(run_id, self.config())
            self.store.transition(run_id, RunState.RUNNING, "test")
            self.store.transition(run_id, state, "test")

            run = coordinator.resume(run_id)

            self.assertEqual(run.state, state)
        self.assertEqual(sum(runner.calls.values()), 0)
        self.submission.submit.assert_not_called()

    def test_unexpected_failure_marks_attempt_and_run_failed(self) -> None:
        script = successful_script()
        script[WorkflowNode.A] = [RuntimeError("boom")]
        coordinator, _ = self.coordinator(script)

        run = coordinator.run_manual(run_id="run-1", scope=self.config())

        self.assertEqual(run.state, RunState.FAILED)
        self.assertEqual(self.attempts("run-1", WorkflowNode.A), [("FAILED", 1)])
        self.submission.submit.assert_not_called()

    def test_malformed_node_payload_fails_attempt_and_run(self) -> None:
        script = successful_script()
        script[WorkflowNode.I] = [
            result(WorkflowNode.I, WorkflowNode.J, new_fingerprints="not-an-array")
        ]
        coordinator, _ = self.coordinator(script)

        run = coordinator.run_manual(run_id="run-1", scope=self.config())

        self.assertEqual(run.state, RunState.FAILED)
        self.assertEqual(self.attempts("run-1", WorkflowNode.I), [("FAILED", 1)])

    def test_m_updates_candidate_experience_with_terminal_artifacts(self) -> None:
        coordinator, _ = self.coordinator(successful_script())

        coordinator.run_manual(run_id="run-1", scope=self.config())

        experiences = self.store.search_experience("USA", 1, "PV")
        self.assertEqual(len(experiences), 1)
        self.assertEqual(experiences[0].final_decision, "RECOMMEND_SUBMIT")
        self.assertEqual(experiences[0].record["approval_outcome"], "PENDING")
        self.assertEqual(len(experiences[0].record["terminal_artifact_ids"]), 2)

    def test_store_finalizes_run_experiences_as_one_public_operation(self) -> None:
        self.store.create_run("run-1", self.config())
        self.store.add_experience(
            "run-1",
            {
                "region": "USA",
                "delay": 1,
                "category": "PV",
                "field_ids": ["close"],
                "expression_fingerprint": "fp-1",
                "record": {"candidate": {"fingerprint": "fp-1"}},
            },
        )

        updated = self.store.finalize_run_experiences(
            "run-1",
            final_decision="NO_PROGRESS",
            approval_outcome="NOT_REQUESTED",
            terminal_artifact_ids=["artifact:1"],
        )

        self.assertEqual(updated, 1)
        experience = self.store.search_experience("USA", 1, "PV")[0]
        self.assertEqual(experience.final_decision, "NO_PROGRESS")
        self.assertEqual(experience.record["approval_outcome"], "NOT_REQUESTED")
        self.assertEqual(experience.record["terminal_artifact_ids"], ["artifact:1"])


if __name__ == "__main__":
    unittest.main()
