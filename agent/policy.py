from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .types import Budget, ModelRole, RunState, WorkflowNode


MAX_POLICY_RESULT_DEPTH = 64
MAX_POLICY_RESULT_NODES = 10_000
MAX_POLICY_RESULT_CHARS = 250_000
MAX_POLICY_INTEGER_BITS = 4_096


class PolicyViolation(ValueError):
    """Raised when an agent action violates a workflow safety policy."""


@dataclass(frozen=True)
class UsageSnapshot:
    simulations: int
    planner_calls: int
    operator_calls: int
    elapsed_minutes: float
    rounds: int = 0
    model_cost_usd: float = 0.0

    def __post_init__(self) -> None:
        for name in ("simulations", "planner_calls", "operator_calls", "rounds"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        for name in ("elapsed_minutes", "model_cost_usd"):
            value = getattr(self, name)
            try:
                valid = type(value) in {int, float} and isfinite(value) and value >= 0
            except OverflowError:
                valid = False
            if not valid:
                raise ValueError(f"{name} must be a finite non-negative number")


ROLE_NODES = MappingProxyType(
    {
        ModelRole.PLANNER: frozenset(
            {
                WorkflowNode.B,
                WorkflowNode.D,
                WorkflowNode.F,
                WorkflowNode.G,
                WorkflowNode.H,
                WorkflowNode.I,
                WorkflowNode.K,
                WorkflowNode.L,
            }
        ),
        ModelRole.OPERATOR: frozenset(
            {
                WorkflowNode.B,
                WorkflowNode.F,
                WorkflowNode.G,
                WorkflowNode.H,
                WorkflowNode.I,
                WorkflowNode.K,
                WorkflowNode.L,
            }
        ),
    }
)

OPERATOR_CONTROL_KEYS = frozenset(
    {
        "scope",
        "budget",
        "success_criteria",
        "next_node",
        "route",
        "plan_version",
        "submission",
    }
)

NODE_COMMANDS = MappingProxyType(
    {
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
)


class AgentPolicy:
    def __init__(
        self,
        budget: Budget,
        command_allowlist: Mapping[WorkflowNode, Iterable[tuple[str, ...]]] | None = None,
    ) -> None:
        if type(budget) is not Budget:
            raise TypeError("budget must be a Budget")
        self.budget = budget

        source = NODE_COMMANDS if command_allowlist is None else command_allowlist
        if not isinstance(source, Mapping):
            raise TypeError("command_allowlist must be a mapping")
        copied: dict[WorkflowNode, tuple[tuple[str, ...], ...]] = {}
        for node, prefixes in source.items():
            if type(node) is not WorkflowNode:
                raise TypeError("command allowlist nodes must be WorkflowNode values")
            try:
                prefix_values = tuple(prefixes)
            except TypeError as exc:
                raise TypeError("command prefixes must be iterable") from exc
            for prefix in prefix_values:
                if (
                    type(prefix) is not tuple
                    or not prefix
                    or any(type(token) is not str or not token.strip() for token in prefix)
                ):
                    raise TypeError("command prefixes must be non-empty tuples of nonblank strings")
            copied[node] = tuple(tuple(prefix) for prefix in prefix_values)
        self.command_allowlist = MappingProxyType(copied)

    def require_model_role(self, role: ModelRole, node: WorkflowNode) -> None:
        if type(role) is not ModelRole or type(node) is not WorkflowNode:
            raise PolicyViolation("model role and node must be exact enum values")
        if node not in ROLE_NODES[role]:
            raise PolicyViolation(f"model role {role.value} is not allowed at node {node.value}")

    def validate_operator_result(self, value: Any) -> None:
        controls: set[str] = set()
        active: set[int] = set()
        nodes_seen = 0
        characters_seen = 0

        def visit(item: Any, depth: int) -> None:
            nonlocal characters_seen, nodes_seen
            nodes_seen += 1
            if nodes_seen > MAX_POLICY_RESULT_NODES:
                raise PolicyViolation("operator result exceeds the JSON size limit")
            if depth > MAX_POLICY_RESULT_DEPTH:
                raise PolicyViolation("operator result exceeds the JSON depth limit")

            if type(item) is dict:
                identity = id(item)
                if identity in active:
                    raise PolicyViolation("operator result must not contain cycles")
                active.add(identity)
                for key, child in item.items():
                    if type(key) is not str:
                        raise PolicyViolation("operator result object keys must be strings")
                    characters_seen += len(key)
                    if characters_seen > MAX_POLICY_RESULT_CHARS:
                        raise PolicyViolation("operator result exceeds the character limit")
                    normalized = key.strip().casefold()
                    if normalized in OPERATOR_CONTROL_KEYS:
                        controls.add(normalized)
                    visit(child, depth + 1)
                active.remove(identity)
            elif type(item) is list:
                identity = id(item)
                if identity in active:
                    raise PolicyViolation("operator result must not contain cycles")
                active.add(identity)
                for child in item:
                    visit(child, depth + 1)
                active.remove(identity)
            elif item is None or type(item) is bool:
                return
            elif type(item) is int:
                if item.bit_length() > MAX_POLICY_INTEGER_BITS:
                    raise PolicyViolation("operator result integer exceeds the bit-length limit")
            elif type(item) is float:
                if not isfinite(item):
                    raise PolicyViolation("operator result numbers must be finite")
            elif type(item) is str:
                characters_seen += len(item)
                if characters_seen > MAX_POLICY_RESULT_CHARS:
                    raise PolicyViolation("operator result exceeds the character limit")
            else:
                raise PolicyViolation("operator result must contain only JSON-native values")

        visit(value, 0)
        if controls:
            fields = ", ".join(sorted(controls))
            raise PolicyViolation(f"operator cannot modify control fields: {fields}")

    def require_simulation_capacity(self, usage: UsageSnapshot) -> None:
        if type(usage) is not UsageSnapshot:
            raise PolicyViolation("usage must be a UsageSnapshot")
        if usage.simulations >= self.budget.total_simulations:
            raise PolicyViolation("simulation budget is exhausted")

    def stop_reason(
        self,
        usage: UsageSnapshot,
        consecutive_no_progress: int,
    ) -> str | None:
        if type(usage) is not UsageSnapshot:
            raise PolicyViolation("usage must be a UsageSnapshot")
        if type(consecutive_no_progress) is not int or consecutive_no_progress < 0:
            raise PolicyViolation("consecutive_no_progress must be a non-negative integer")

        hard_cap_reached = (
            usage.rounds >= self.budget.rounds
            or usage.simulations >= self.budget.total_simulations
            or usage.planner_calls >= self.budget.planner_calls
            or usage.operator_calls >= self.budget.operator_calls
            or usage.elapsed_minutes >= self.budget.max_runtime_minutes
            or self.budget.max_model_cost_usd is not None
            and usage.model_cost_usd >= self.budget.max_model_cost_usd
        )
        if hard_cap_reached:
            return "BUDGET_EXHAUSTED"
        if consecutive_no_progress >= 2:
            return "NO_PROGRESS"
        return None

    def require_command(self, node: WorkflowNode, argv: tuple[str, ...]) -> None:
        if type(node) is not WorkflowNode:
            raise PolicyViolation("command node must be a WorkflowNode")
        if (
            type(argv) is not tuple
            or not argv
            or any(type(token) is not str or not token.strip() for token in argv)
        ):
            raise PolicyViolation("command argv must be a non-empty tuple of nonblank strings")
        prefixes = self.command_allowlist.get(node, ())
        if not any(argv[: len(prefix)] == prefix for prefix in prefixes):
            raise PolicyViolation(f"command is not allowed for node {node.value}")

    def require_submission_approval(
        self,
        run_state: RunState,
        approval_matches: bool,
    ) -> None:
        if run_state is not RunState.AWAITING_APPROVAL or approval_matches is not True:
            raise PolicyViolation("submission requires a matching explicit approval")
