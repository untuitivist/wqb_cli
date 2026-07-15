from __future__ import annotations

from dataclasses import FrozenInstanceError
from math import nan
import unittest


class AgentPolicySmokeTests(unittest.TestCase):
    def test_operator_cannot_modify_budget(self) -> None:
        from wqb_cli.agent.policy import AgentPolicy, PolicyViolation
        from wqb_cli.agent.types import Budget

        policy = AgentPolicy(Budget())

        with self.assertRaisesRegex(PolicyViolation, "operator cannot modify"):
            policy.validate_operator_result(
                {"task_result": {"status": "COMPLETED", "payload": {"budget": 80}}}
            )

    def test_simulation_capacity_rejects_equal_limit(self) -> None:
        from wqb_cli.agent.policy import AgentPolicy, PolicyViolation, UsageSnapshot
        from wqb_cli.agent.types import Budget

        policy = AgentPolicy(Budget(total_simulations=2))
        usage = UsageSnapshot(
            simulations=2,
            planner_calls=0,
            operator_calls=0,
            elapsed_minutes=1,
        )

        with self.assertRaisesRegex(PolicyViolation, "simulation budget"):
            policy.require_simulation_capacity(usage)


class AgentPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        from wqb_cli.agent.policy import AgentPolicy
        from wqb_cli.agent.types import Budget

        self.policy = AgentPolicy(Budget())

    def test_usage_snapshot_is_frozen_and_strictly_validated(self) -> None:
        from wqb_cli.agent.policy import UsageSnapshot

        valid = UsageSnapshot(0, 0, 0, 0.0)
        with self.assertRaises(FrozenInstanceError):
            valid.simulations = 1  # type: ignore[misc]

        integer_fields = ("simulations", "planner_calls", "operator_calls", "rounds")
        for field in integer_fields:
            for value in (True, -1, 1.0, "1"):
                with self.subTest(field=field, value=value):
                    kwargs = {
                        "simulations": 0,
                        "planner_calls": 0,
                        "operator_calls": 0,
                        "elapsed_minutes": 0.0,
                        field: value,
                    }
                    with self.assertRaises(ValueError):
                        UsageSnapshot(**kwargs)  # type: ignore[arg-type]

        for field in ("elapsed_minutes", "model_cost_usd"):
            for value in (True, -0.1, nan, float("inf"), float("-inf"), "1"):
                with self.subTest(field=field, value=value):
                    kwargs = {
                        "simulations": 0,
                        "planner_calls": 0,
                        "operator_calls": 0,
                        "elapsed_minutes": 0.0,
                        field: value,
                    }
                    with self.assertRaises(ValueError):
                        UsageSnapshot(**kwargs)  # type: ignore[arg-type]

    def test_role_node_matrix_is_exact_and_immutable(self) -> None:
        from wqb_cli.agent.policy import ROLE_NODES
        from wqb_cli.agent.types import ModelRole, WorkflowNode

        expected = {
            ModelRole.PLANNER: set("BDFGHIKL"),
            ModelRole.OPERATOR: set("BFGHIKL"),
        }
        for role in ModelRole:
            for node in WorkflowNode:
                with self.subTest(role=role, node=node):
                    if node.value in expected[role]:
                        self.policy.require_model_role(role, node)
                    else:
                        with self.assertRaisesRegex(Exception, "role"):
                            self.policy.require_model_role(role, node)

        with self.assertRaises(TypeError):
            ROLE_NODES[ModelRole.PLANNER] = frozenset()  # type: ignore[index]
        with self.assertRaises(AttributeError):
            ROLE_NODES[ModelRole.PLANNER].add(WorkflowNode.A)  # type: ignore[attr-defined]

    def test_model_role_requires_exact_enums(self) -> None:
        from wqb_cli.agent.policy import PolicyViolation
        from wqb_cli.agent.types import ModelRole, WorkflowNode

        for role, node in (
            (ModelRole.PLANNER.value, WorkflowNode.B),
            (ModelRole.PLANNER, WorkflowNode.B.value),
        ):
            with self.subTest(role=role, node=node):
                with self.assertRaises(PolicyViolation):
                    self.policy.require_model_role(role, node)  # type: ignore[arg-type]

    def test_operator_control_keys_are_rejected_at_any_depth(self) -> None:
        from wqb_cli.agent.policy import OPERATOR_CONTROL_KEYS, PolicyViolation

        for key in OPERATOR_CONTROL_KEYS:
            for disguised in (key, key.upper(), f"  {key}  "):
                with self.subTest(key=disguised):
                    value = {"outer": [{"nested": {disguised: "sensitive-value"}}]}
                    with self.assertRaises(PolicyViolation) as raised:
                        self.policy.validate_operator_result(value)
                    message = str(raised.exception)
                    self.assertIn(key, message)
                    self.assertNotIn("sensitive-value", message)

        self.policy.validate_operator_result({"mybudget": 1, "tokenization": "ordinary"})

    def test_operator_result_requires_bounded_acyclic_json_native_data(self) -> None:
        from wqb_cli.agent.policy import PolicyViolation

        cyclic: list[object] = []
        cyclic.append(cyclic)
        deep: object = None
        for _ in range(80):
            deep = [deep]
        huge = [None] * 10_001
        invalid_values = (
            {1: "non-string-key"},
            ("tuple",),
            {"value": nan},
            cyclic,
            deep,
            huge,
            object(),
        )
        for value in invalid_values:
            with self.subTest(kind=type(value).__name__):
                with self.assertRaises(PolicyViolation):
                    self.policy.validate_operator_result(value)

    def test_simulation_capacity_validates_usage_and_allows_below_limit(self) -> None:
        from wqb_cli.agent.policy import PolicyViolation, UsageSnapshot

        self.policy.require_simulation_capacity(UsageSnapshot(39, 0, 0, 0.0))
        with self.assertRaises(PolicyViolation):
            self.policy.require_simulation_capacity("not-a-snapshot")  # type: ignore[arg-type]

    def test_stop_reason_checks_every_hard_cap_at_equality(self) -> None:
        from wqb_cli.agent.policy import AgentPolicy, UsageSnapshot
        from wqb_cli.agent.types import Budget

        policy = AgentPolicy(
            Budget(
                rounds=2,
                total_simulations=3,
                planner_calls=4,
                operator_calls=5,
                max_runtime_minutes=6,
                max_model_cost_usd=7.0,
            )
        )
        capped = (
            UsageSnapshot(0, 0, 0, 0.0, rounds=2),
            UsageSnapshot(3, 0, 0, 0.0),
            UsageSnapshot(0, 4, 0, 0.0),
            UsageSnapshot(0, 0, 5, 0.0),
            UsageSnapshot(0, 0, 0, 6.0),
            UsageSnapshot(0, 0, 0, 0.0, model_cost_usd=7.0),
        )
        for usage in capped:
            with self.subTest(usage=usage):
                self.assertEqual(policy.stop_reason(usage, 0), "BUDGET_EXHAUSTED")

        below = UsageSnapshot(2, 3, 4, 5.9, rounds=1, model_cost_usd=6.9)
        self.assertIsNone(policy.stop_reason(below, 1))
        self.assertEqual(policy.stop_reason(below, 2), "NO_PROGRESS")

    def test_stop_reason_hard_cap_precedes_no_progress_and_validates_counter(self) -> None:
        from wqb_cli.agent.policy import UsageSnapshot

        capped = UsageSnapshot(40, 0, 0, 0.0)
        self.assertEqual(self.policy.stop_reason(capped, 2), "BUDGET_EXHAUSTED")
        for value in (True, -1, 1.0, "2"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.policy.stop_reason(UsageSnapshot(0, 0, 0, 0.0), value)  # type: ignore[arg-type]

    def test_zero_cost_cap_is_a_hard_cap(self) -> None:
        from wqb_cli.agent.policy import AgentPolicy, UsageSnapshot
        from wqb_cli.agent.types import Budget

        policy = AgentPolicy(Budget(max_model_cost_usd=0))
        self.assertEqual(
            policy.stop_reason(UsageSnapshot(0, 0, 0, 0.0), 0),
            "BUDGET_EXHAUSTED",
        )

    def test_default_command_allowlist_enforces_exact_node_prefixes(self) -> None:
        from wqb_cli.agent.policy import PolicyViolation
        from wqb_cli.agent.types import WorkflowNode

        allowed = (
            (WorkflowNode.A, ("auth", "status")),
            (WorkflowNode.G, ("community", "search", "alpha idea")),
            (WorkflowNode.K, ("alpha", "correlation", "self", "alpha-id")),
            (WorkflowNode.M, ("alpha", "submit", "alpha-id")),
        )
        for node, argv in allowed:
            with self.subTest(node=node, argv=argv):
                self.policy.require_command(node, argv)

        rejected = (
            (WorkflowNode.L, ("alpha", "submit", "alpha-id")),
            (WorkflowNode.M, ("alpha", "submitter", "alpha-id")),
            (WorkflowNode.A, ("auth", "status-extra")),
            (WorkflowNode.A, "auth status"),
            (WorkflowNode.A, ("auth", " ")),
            ("A", ("auth", "status")),
        )
        for node, argv in rejected:
            with self.subTest(node=node, argv=argv):
                with self.assertRaises(PolicyViolation):
                    self.policy.require_command(node, argv)  # type: ignore[arg-type]

    def test_scope_decision_uses_the_registered_user_diversity_command(self) -> None:
        from wqb_cli.agent.policy import PolicyViolation
        from wqb_cli.agent.types import WorkflowNode

        self.policy.require_command(
            WorkflowNode.D,
            ("user", "user-diversity", "user-id"),
        )
        with self.assertRaises(PolicyViolation):
            self.policy.require_command(WorkflowNode.D, ("user", "diversity", "user-id"))

    def test_default_node_command_contract_is_complete_and_exact(self) -> None:
        from wqb_cli.agent.policy import NODE_COMMANDS, PolicyViolation
        from wqb_cli.agent.types import WorkflowNode

        expected = {
            WorkflowNode.A: (("auth", "status"),),
            WorkflowNode.B: (
                ("user", "consultant-summary"),
                ("user", "messages-summary"),
                ("user", "messages"),
                ("event", "list"),
            ),
            WorkflowNode.C: (
                ("alpha", "list"),
                ("user", "alphas-summary"),
                ("user", "pyramid-alphas"),
                ("user", "pyramid-multipliers"),
            ),
            WorkflowNode.D: (
                ("user", "consultant-summary"),
                ("user", "pyramid-alphas"),
                ("user", "pyramid-multipliers"),
                ("user", "user-diversity"),
                ("data", "categories"),
            ),
            WorkflowNode.F: (
                ("scope", "files"),
                ("scope", "list"),
                ("scope", "show"),
                ("scope", "top"),
                ("scope", "alpha-rows"),
                ("data", "fields"),
                ("data", "datasets"),
                ("alpha", "list"),
            ),
            WorkflowNode.G: (
                ("community", "search"),
                ("docs", "list"),
                ("docs", "show"),
                ("search",),
            ),
            WorkflowNode.H: (("data", "field"),),
            WorkflowNode.I: (
                ("data", "operators"),
                ("data", "field"),
                ("docs", "show"),
            ),
            WorkflowNode.J: (
                ("sim", "options"),
                ("sim", "create"),
                ("sim", "get"),
                ("alpha", "get"),
                ("alpha", "check"),
                ("alpha", "recordsets"),
            ),
            WorkflowNode.K: (
                ("alpha", "get"),
                ("alpha", "check"),
                ("alpha", "pnl"),
                ("alpha", "yearly-stats"),
                ("alpha", "correlation", "self"),
                ("alpha", "correlation", "prod"),
            ),
            WorkflowNode.L: (
                ("alpha", "get"),
                ("alpha", "check"),
                ("alpha", "correlation", "self"),
                ("alpha", "correlation", "prod"),
                ("alpha", "performance-comparison"),
            ),
            WorkflowNode.M: (("alpha", "submit"), ("alpha", "get")),
        }
        self.assertEqual(dict(NODE_COMMANDS), expected)

        for node, prefixes in expected.items():
            for prefix in prefixes:
                with self.subTest(node=node, prefix=prefix):
                    self.policy.require_command(node, prefix + ("argument",))

        for node in WorkflowNode:
            if node is WorkflowNode.M:
                continue
            with self.subTest(reject_submit=node):
                with self.assertRaises(PolicyViolation):
                    self.policy.require_command(node, ("alpha", "submit", "alpha-id"))

        for argv in (
            ("alpha", "submitter", "alpha-id"),
            ("alpha-submit", "alpha-id"),
            ("alph", "submit", "alpha-id"),
        ):
            with self.subTest(similar_prefix=argv):
                with self.assertRaises(PolicyViolation):
                    self.policy.require_command(WorkflowNode.M, argv)

    def test_custom_command_allowlist_is_snapshotted_and_fails_closed(self) -> None:
        from wqb_cli.agent.policy import AgentPolicy, PolicyViolation
        from wqb_cli.agent.types import Budget, WorkflowNode

        prefixes = [("tool", "read")]
        supplied = {WorkflowNode.B: prefixes}
        policy = AgentPolicy(Budget(), command_allowlist=supplied)
        prefixes[0] = ("tool", "write")
        supplied.clear()

        policy.require_command(WorkflowNode.B, ("tool", "read", "item"))
        with self.assertRaises(PolicyViolation):
            policy.require_command(WorkflowNode.B, ("tool", "write", "item"))
        with self.assertRaises(PolicyViolation):
            policy.require_command(WorkflowNode.C, ("alpha", "list"))
        with self.assertRaises(TypeError):
            policy.command_allowlist[WorkflowNode.B] = ()  # type: ignore[index]

    def test_submission_approval_requires_exact_state_and_true(self) -> None:
        from wqb_cli.agent.policy import PolicyViolation
        from wqb_cli.agent.types import RunState

        self.policy.require_submission_approval(RunState.AWAITING_APPROVAL, True)
        for state, approval in (
            (RunState.RUNNING, True),
            (RunState.AWAITING_APPROVAL, False),
            (RunState.AWAITING_APPROVAL, 1),
            (RunState.AWAITING_APPROVAL.value, True),
        ):
            with self.subTest(state=state, approval=approval):
                with self.assertRaises(PolicyViolation):
                    self.policy.require_submission_approval(state, approval)  # type: ignore[arg-type]


class ContextBuilderSmokeTests(unittest.TestCase):
    def test_operator_receives_only_selected_task_and_explicit_evidence(self) -> None:
        from wqb_cli.agent.context import ContextBuilder

        builder = ContextBuilder(resolve_artifact=lambda ref: {"id": ref, "text": "safe"})
        plan = {
            "version": 3,
            "hash": "plan-hash",
            "tasks": [
                {"id": "task-1", "instruction": "inspect", "api_key": "do-not-leak"},
                {"id": "task-2", "instruction": "submit"},
            ],
        }

        context = builder.for_operator(
            task="task-1",
            plan=plan,
            evidence_refs=["artifact:a"],
        )

        self.assertEqual(context["task"]["task_id"], "task-1")
        self.assertNotIn("task-2", repr(context))
        self.assertNotIn("do-not-leak", repr(context))
        self.assertEqual(context["evidence"]["artifacts"][0]["id"], "artifact:a")


class ContextBuilderTests(unittest.TestCase):
    def test_resolver_must_be_callable(self) -> None:
        from wqb_cli.agent.context import ContextBuilder

        with self.assertRaises(TypeError):
            ContextBuilder(resolve_artifact=None)  # type: ignore[arg-type]

    def test_planner_context_is_redacted_explicit_and_manifested(self) -> None:
        from wqb_cli.agent.context import ContextBuilder

        calls: list[str] = []
        artifacts = {
            "artifact:a": {
                "id": "artifact:a",
                "text": "research",
                "Authorization": "Bearer planner-secret",
            },
            "artifact:unused": {"id": "artifact:unused", "text": "must-not-expand"},
        }

        def resolve(ref: str) -> dict[str, object]:
            calls.append(ref)
            return artifacts[ref]

        builder = ContextBuilder(resolve_artifact=resolve)
        run_config = {
            "scope_mode": "auto",
            "password": "planner-password",
            "api-key": "planner-api-key",
            "tokenization": "keep-this-word",
        }
        plan = {
            "id": "plan-1",
            "version": 4,
            "tasks": [{"id": "task-1"}],
            "long_document_ref": "artifact:unused",
        }
        metrics = {"simulations": 2, "cost": 0.5}
        route_history = [{"node": "F", "Cookie": "planner-cookie"}]
        experiences = [
            {
                "id": "experience:1",
                "summary": {"lesson": "use rank", "clientSecret": "experience-secret"},
            }
        ]

        context = builder.for_planner(
            run_config=run_config,
            current_plan=plan,
            metrics=metrics,
            evidence_refs=["artifact:a", "artifact:a"],
            route_history=route_history,
            experience_summaries=experiences,
        )

        self.assertEqual(calls, ["artifact:a"])
        self.assertEqual(context["run_config"]["tokenization"], "keep-this-word")
        self.assertEqual(context["metrics"], metrics)
        self.assertEqual(context["evidence"]["classification"], "untrusted_data")
        self.assertEqual(len(context["evidence"]["artifacts"]), 1)
        self.assertEqual(
            context["context_manifest"],
            {
                "plan_id": "plan-1",
                "plan_version": 4,
                "artifact_ids": ["artifact:a"],
                "experience_ids": ["experience:1"],
            },
        )
        rendered = repr(context)
        for secret in (
            "planner-password",
            "planner-api-key",
            "planner-secret",
            "planner-cookie",
            "experience-secret",
            "must-not-expand",
        ):
            self.assertNotIn(secret, rendered)
        self.assertIn("[REDACTED]", rendered)

    def test_operator_context_exposes_only_selected_execution_contract(self) -> None:
        from wqb_cli.agent.context import ContextBuilder

        calls: list[str] = []

        def resolve(ref: str) -> dict[str, object]:
            calls.append(ref)
            return {"id": ref, "text": ["observed"], "accessToken": "artifact-secret"}

        builder = ContextBuilder(resolve)
        plan = {
            "id": "plan-2",
            "plan_version": 8,
            "plan_hash": "locked-hash",
            "scope": {"region": "USA"},
            "budget": {"simulations": 40},
            "tasks": [
                {
                    "id": "task-1",
                    "instruction": "inspect fields",
                    "required_fields": ["close"],
                    "required_operators": ["rank"],
                    "output_schema": {"type": "object"},
                    "budget": 99,
                    "nested": {"scope": "forbidden", "token": "task-secret"},
                },
                {"id": "task-2", "instruction": "submit alpha"},
            ],
        }

        context = builder.for_operator(
            task="task-1",
            plan=plan,
            evidence_refs=["artifact:a"],
        )

        self.assertEqual(context["task"]["task_id"], "task-1")
        self.assertEqual(context["plan_lock"], {"version": 8, "hash": "locked-hash"})
        self.assertEqual(context["required_fields"], ["close"])
        self.assertEqual(context["required_operators"], ["rank"])
        self.assertEqual(context["output_schema"], {"type": "object"})
        self.assertEqual(calls, ["artifact:a"])
        self.assertEqual(
            context["context_manifest"],
            {
                "plan_id": "plan-2",
                "plan_version": 8,
                "plan_hash": "locked-hash",
                "task_id": "task-1",
                "artifact_ids": ["artifact:a"],
            },
        )
        rendered = repr(context)
        for forbidden in ("task-2", "submit alpha", "task-secret", "artifact-secret"):
            self.assertNotIn(forbidden, rendered)
        self.assertNotIn("'budget'", rendered)
        self.assertNotIn("'scope'", rendered)

    def test_operator_task_is_a_strict_minimal_projection(self) -> None:
        from wqb_cli.agent.context import ContextBuilder, ContextError

        builder = ContextBuilder(lambda ref: {"id": ref})
        selected = {
            "id": "task-1",
            "instruction": "inspect fields",
            "parameters": {"arbitrary": "must-not-project"},
            "tasks": [{"id": "embedded-task", "instruction": "embedded-secret"}],
            "current_plan": {"notes": "current-plan-secret"},
            "plan": {"notes": "plan-secret"},
            "other_task": {"id": "task-2", "instruction": "other-task-secret"},
            "budget": 100,
            "api_key": "task-api-secret",
        }
        plan = {
            "version": 2,
            "hash": "locked-plan",
            "tasks": [selected, {"id": "task-2", "instruction": "submit"}],
        }

        context = builder.for_operator(task="task-1", plan=plan, evidence_refs=[])

        self.assertEqual(
            context["task"],
            {"task_id": "task-1", "instruction": "inspect fields"},
        )
        rendered = repr(context)
        for forbidden in (
            "must-not-project",
            "embedded-task",
            "embedded-secret",
            "current-plan-secret",
            "plan-secret",
            "other-task-secret",
            "task-api-secret",
        ):
            self.assertNotIn(forbidden, rendered)

        for instruction in (None, "", "   ", 1):
            with self.subTest(instruction=instruction):
                invalid_plan = {
                    "version": 2,
                    "hash": "locked-plan",
                    "tasks": [{"id": "task-1", "instruction": instruction}],
                }
                with self.assertRaises(ContextError):
                    builder.for_operator(
                        task="task-1",
                        plan=invalid_plan,
                        evidence_refs=[],
                    )

    def test_operator_explicit_contract_arguments_override_task_defaults(self) -> None:
        from wqb_cli.agent.context import ContextBuilder

        builder = ContextBuilder(lambda ref: {"id": ref})
        plan = {
            "version": 1,
            "hash": "override-plan",
            "tasks": [
                {"id": "task-1", "instruction": "inspect", "required_fields": ["old"]}
            ],
        }
        context = builder.for_operator(
            task={"id": "task-1"},
            plan=plan,
            required_fields=["new"],
            required_operators=["ts_mean"],
            output_schema={"description": "result only"},
            evidence_refs=[],
        )

        self.assertEqual(context["required_fields"], ["new"])
        self.assertEqual(context["required_operators"], ["ts_mean"])
        self.assertEqual(context["output_schema"], {"description": "result only"})

    def test_operator_requires_exact_locked_plan_version_and_hash(self) -> None:
        from wqb_cli.agent.context import ContextBuilder, ContextError

        calls: list[str] = []

        def resolve(ref: str) -> dict[str, str]:
            calls.append(ref)
            return {"id": ref}

        builder = ContextBuilder(resolve)
        valid = {
            "version": 1,
            "hash": "plan-hash",
            "tasks": [{"id": "task-1", "instruction": "inspect"}],
        }
        context = builder.for_operator(task="task-1", plan=valid, evidence_refs=[])
        self.assertEqual(context["plan_lock"], {"version": 1, "hash": "plan-hash"})

        invalid_plans = (
            {"hash": "plan-hash", "tasks": valid["tasks"]},
            {"version": 1, "tasks": valid["tasks"]},
            {**valid, "version": True},
            {**valid, "version": 0},
            {**valid, "version": -1},
            {**valid, "version": 1.0},
            {**valid, "hash": ""},
            {**valid, "hash": "   "},
        )
        for plan in invalid_plans:
            with self.subTest(plan=plan):
                with self.assertRaises(ContextError):
                    builder.for_operator(task="task-1", plan=plan, evidence_refs=[])

        with self.assertRaises(ContextError):
            builder.for_operator(
                task="task-1",
                plan={"version": 0, "hash": "invalid", "tasks": valid["tasks"]},
                evidence_refs=["artifact:a"],
            )
        self.assertEqual(calls, [])

    def test_operator_normalizes_task_id_selectors_and_rejects_conflicts(self) -> None:
        from wqb_cli.agent.context import ContextBuilder, ContextError

        builder = ContextBuilder(lambda ref: {"id": ref})
        plan = {
            "version": 3,
            "hash": "task-id-plan",
            "tasks": [{"task_id": "task-1", "instruction": "inspect"}],
        }
        selectors: tuple[object, ...] = (
            "task-1",
            {"task_id": "task-1"},
            {"id": "task-1", "task_id": "task-1"},
        )
        for selector in selectors:
            with self.subTest(selector=selector):
                context = builder.for_operator(
                    task=selector,
                    plan=plan,
                    evidence_refs=[],
                )
                self.assertEqual(
                    context["task"],
                    {"task_id": "task-1", "instruction": "inspect"},
                )
                self.assertEqual(context["context_manifest"]["task_id"], "task-1")

        conflicting_selectors = (
            {"id": "task-1", "task_id": "task-2"},
            "task-1",
        )
        conflicting_plans = (
            plan,
            {
                **plan,
                "tasks": [
                    {"id": "task-1", "task_id": "task-2", "instruction": "inspect"}
                ],
            },
        )
        for selector, conflicting_plan in zip(
            conflicting_selectors,
            conflicting_plans,
            strict=True,
        ):
            with self.subTest(selector=selector, plan=conflicting_plan):
                with self.assertRaises(ContextError):
                    builder.for_operator(
                        task=selector,
                        plan=conflicting_plan,
                        evidence_refs=[],
                    )

    def test_contexts_are_deep_snapshots_without_cross_call_aliases(self) -> None:
        from wqb_cli.agent.context import ContextBuilder

        resolved = {"id": "artifact:a", "nested": {"values": [1]}}
        builder = ContextBuilder(lambda ref: resolved)
        plan = {
            "version": 1,
            "hash": "snapshot-plan",
            "tasks": [{"id": "task-1", "instruction": "inspect"}],
        }
        refs = ["artifact:a"]

        first = builder.for_operator(task="task-1", plan=plan, evidence_refs=refs)
        plan["tasks"][0]["instruction"] = "mutated"
        refs.append("artifact:b")
        resolved["nested"]["values"].append(2)

        self.assertEqual(first["task"]["instruction"], "inspect")
        self.assertEqual(first["evidence"]["artifacts"][0]["nested"]["values"], [1])
        self.assertEqual(first["context_manifest"]["artifact_ids"], ["artifact:a"])

        plan["tasks"][0]["instruction"] = "inspect"
        resolved["nested"]["values"] = [1]
        second = builder.for_operator(task="task-1", plan=plan, evidence_refs=["artifact:a"])
        first["task"]["instruction"] = "changed"
        first["evidence"]["artifacts"][0]["nested"]["values"].append(3)
        self.assertEqual(second["task"]["instruction"], "inspect")
        self.assertEqual(second["evidence"]["artifacts"][0]["nested"]["values"], [1])

    def test_secret_key_variants_are_redacted_but_tokenization_is_not(self) -> None:
        from wqb_cli.agent.context import ContextBuilder

        variants = {
            "PASSWORD": "value-1",
            "databasePassword": "value-2",
            "api_key": "value-3",
            "Api-Key": "value-4",
            "Authorization": "value-5",
            "session_cookie": "value-6",
            "clientSecret": "value-7",
            "accessToken": "value-8",
            "refresh-token": "value-9",
            "ACCESSTOKEN": "value-10",
            "accesstoken": "value-11",
            "access_token": "value-12",
            "token_value": "value-13",
            "tokenization": "ordinary-word",
            "token_bucket": "rate-limit-state",
        }
        builder = ContextBuilder(lambda ref: {"id": ref})
        context = builder.for_planner(
            run_config=variants,
            current_plan={"id": "plan"},
            metrics={},
            evidence_refs=[],
            route_history=[],
            experience_summaries=[],
        )

        for key in variants:
            expected = (
                variants[key]
                if key in {"tokenization", "token_bucket"}
                else "[REDACTED]"
            )
            self.assertEqual(context["run_config"][key], expected)

    def test_malformed_inputs_and_resolver_fail_without_leaking_values(self) -> None:
        from wqb_cli.agent.context import ContextBuilder, ContextError

        cyclic: list[object] = []
        cyclic.append(cyclic)
        deep: object = None
        for _ in range(80):
            deep = [deep]

        builder = ContextBuilder(lambda ref: {"id": ref})
        invalid_planner_values = (
            {"run_config": {1: "bad"}},
            {"metrics": {"cost": nan}},
            {"route_history": ("tuple",)},
            {"current_plan": cyclic},
            {"current_plan": deep},
            {"run_config": {"secret": object()}},
        )
        defaults = {
            "run_config": {},
            "current_plan": {},
            "metrics": {},
            "evidence_refs": [],
            "route_history": [],
            "experience_summaries": [],
        }
        for override in invalid_planner_values:
            with self.subTest(field=next(iter(override))):
                with self.assertRaises(ContextError) as raised:
                    builder.for_planner(**{**defaults, **override})
                self.assertNotIn("bad", str(raised.exception))

        malformed_experiences = ("not-a-list", ["not-an-object"], [{}], [{"id": " "}])
        for experiences in malformed_experiences:
            with self.subTest(experiences=experiences):
                with self.assertRaises(ContextError):
                    builder.for_planner(
                        **{**defaults, "experience_summaries": experiences}  # type: ignore[arg-type]
                    )

        bad_refs = (("artifact:a",), [1], [""], ["artifact:a", None])
        for refs in bad_refs:
            with self.subTest(refs=refs):
                with self.assertRaises(ContextError):
                    builder.for_planner(**{**defaults, "evidence_refs": refs})  # type: ignore[arg-type]

        resolvers = (
            lambda ref: "not-an-object",
            lambda ref: {"id": "artifact:other", "secret": "resolver-secret"},
            lambda ref: {"id": ref, "value": nan},
            lambda ref: (_ for _ in ()).throw(RuntimeError("resolver-secret")),
        )
        for resolver in resolvers:
            with self.subTest(resolver=resolver):
                with self.assertRaises(ContextError) as raised:
                    ContextBuilder(resolver).for_planner(
                        **{**defaults, "evidence_refs": ["artifact:a"]}
                    )
                self.assertNotIn("resolver-secret", str(raised.exception))
                self.assertIsNone(raised.exception.__cause__)

    def test_operator_rejects_missing_or_duplicate_task_ids(self) -> None:
        from wqb_cli.agent.context import ContextBuilder, ContextError

        builder = ContextBuilder(lambda ref: {"id": ref})
        for plan in (
            {"tasks": [{"id": "task-2"}]},
            {"tasks": [{"id": "task-1"}, {"id": "task-1"}]},
            {"tasks": "not-a-list"},
        ):
            with self.subTest(plan=plan):
                with self.assertRaises(ContextError):
                    builder.for_operator(task="task-1", plan=plan, evidence_refs=[])


if __name__ == "__main__":
    unittest.main()
