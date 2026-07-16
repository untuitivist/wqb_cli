from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import closing
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .artifacts import ArtifactWriter
from .policy import AgentPolicy, UsageSnapshot
from .reporting import build_final_report, write_final_report
from .store import AgentStore, RunRecord
from .types import Budget, NodeResult, RunConfig, RunState, ScopeMode, WorkflowNode


FORWARD: Mapping[WorkflowNode, WorkflowNode] = {
    WorkflowNode.A: WorkflowNode.B,
    WorkflowNode.B: WorkflowNode.C,
    WorkflowNode.C: WorkflowNode.D,
    WorkflowNode.D: WorkflowNode.F,
    WorkflowNode.F: WorkflowNode.G,
    WorkflowNode.G: WorkflowNode.H,
    WorkflowNode.H: WorkflowNode.I,
    WorkflowNode.I: WorkflowNode.J,
    WorkflowNode.J: WorkflowNode.K,
}
K_ROUTES = frozenset(
    {WorkflowNode.F, WorkflowNode.G, WorkflowNode.H, WorkflowNode.I, WorkflowNode.L}
)
L_ROUTES = frozenset({WorkflowNode.K, WorkflowNode.M})
TERMINAL_STATES = frozenset(
    {
        RunState.SUBMITTED,
        RunState.REJECTED,
        RunState.BUDGET_EXHAUSTED,
        RunState.NO_PROGRESS,
        RunState.FAILED,
    }
)


class CoordinatorError(RuntimeError):
    """Raised when an untrusted node result violates the workflow contract."""


class AuthenticationRequired(CoordinatorError):
    """Signals that an interactive authentication prerequisite is missing."""


class PlannerUnavailable(CoordinatorError):
    """Signals that bounded Planner retries have been exhausted."""


@runtime_checkable
class NodeRunner(Protocol):
    def run(
        self, run_id: str, node: WorkflowNode, context: dict[str, object]
    ) -> NodeResult: ...


class RegistryNodeRunner:
    """Adapt a node-to-callable registry to the coordinator's single interface."""

    def __init__(
        self,
        registry: Mapping[
            WorkflowNode, Callable[[str, dict[str, object]], NodeResult]
        ],
    ) -> None:
        if not isinstance(registry, Mapping):
            raise TypeError("registry must be a mapping")
        copied: dict[
            WorkflowNode, Callable[[str, dict[str, object]], NodeResult]
        ] = {}
        for node, handler in registry.items():
            if type(node) is not WorkflowNode or not callable(handler):
                raise TypeError("registry entries must map WorkflowNode to callable")
            copied[node] = handler
        self._registry = copied

    def run(
        self, run_id: str, node: WorkflowNode, context: dict[str, object]
    ) -> NodeResult:
        try:
            handler = self._registry[node]
        except KeyError:
            raise CoordinatorError(f"node {node.value} is not registered") from None
        return handler(run_id, context)


NodeRegistryRunner = RegistryNodeRunner


class AgentCoordinator:
    def __init__(
        self,
        *,
        store: AgentStore,
        policy: AgentPolicy,
        node_runner: NodeRunner,
        submission: Any,
        artifacts: ArtifactWriter | None = None,
        workflow_root: str | Path | None = None,
    ) -> None:
        if not isinstance(store, AgentStore):
            raise TypeError("store must be an AgentStore")
        if not isinstance(policy, AgentPolicy):
            raise TypeError("policy must be an AgentPolicy")
        if not callable(getattr(node_runner, "run", None)):
            raise TypeError("node_runner must provide run")
        if submission is None:
            raise TypeError("submission must not be None")
        self.store = store
        self.policy = policy
        self.node_runner = node_runner
        self.submission = submission
        inherited_artifacts = getattr(node_runner, "artifacts", None)
        self.artifacts = artifacts or (
            inherited_artifacts
            if isinstance(inherited_artifacts, ArtifactWriter)
            else ArtifactWriter(store.path.parent / "research_runs", store)
        )
        self.workflow_root = (
            Path(workflow_root).resolve()
            if workflow_root is not None
            else Path(__file__).resolve().parents[1] / "workflow" / "nodes"
        )

    def run_manual(self, *, run_id: str, scope: RunConfig) -> RunRecord:
        if not isinstance(scope, RunConfig) or scope.scope_mode is not ScopeMode.MANUAL:
            raise TypeError("scope must be a manual RunConfig")
        return self._start(run_id, scope)

    def run_auto(
        self,
        *,
        run_id: str,
        config: RunConfig | None = None,
        budget: Budget | None = None,
    ) -> RunRecord:
        if config is None:
            config = RunConfig(scope_mode=ScopeMode.AUTO, budget=budget or self.policy.budget)
        if not isinstance(config, RunConfig) or config.scope_mode is not ScopeMode.AUTO:
            raise TypeError("config must be an auto RunConfig")
        return self._start(run_id, config)

    def _start(self, run_id: str, config: RunConfig) -> RunRecord:
        if config.budget != self.policy.budget:
            raise CoordinatorError("run budget must match the coordinator policy")
        self.store.create_run(run_id, config)
        self.store.transition(run_id, RunState.RUNNING, "coordinator started")
        context = self._initial_context(config)
        return self._execute(run_id, WorkflowNode.A, context, 0, set())

    def resume(self, run_id: str) -> RunRecord:
        run = self.store.get_run(run_id)
        if run.state is RunState.AWAITING_APPROVAL or run.state in TERMINAL_STATES:
            return run
        paused = run.state in {RunState.NEEDS_AUTH, RunState.PAUSED_MODEL}
        if paused:
            self.store.transition(run_id, RunState.RUNNING, "resume prerequisite retry")

        checkpoint = self._checkpoint(run_id)
        context = self._initial_context(run.config)
        context.update(checkpoint["context"])
        node = checkpoint["node"]
        if paused and checkpoint["paused_node"] is not None:
            node = checkpoint["paused_node"]
        if checkpoint["incomplete_j"]:
            node = WorkflowNode.J
            context["resume_simulation_ids"] = self._incomplete_simulations(run_id)
        return self._execute(
            run_id,
            node,
            context,
            checkpoint["no_progress"],
            checkpoint["fingerprints"],
        )

    def _execute(
        self,
        run_id: str,
        node: WorkflowNode,
        context: dict[str, object],
        consecutive_no_progress: int,
        fingerprints_since_k: set[str],
    ) -> RunRecord:
        while True:
            stop = self.policy.stop_reason(
                self._usage(run_id), consecutive_no_progress
            )
            if stop is not None:
                return self._record_only(run_id, RunState(stop), stop)

            attempt = self.store.start_node_attempt(run_id, node)
            call_context = dict(context)
            try:
                call_context["context_manifest"] = self._rules_manifest(node)
                if node is WorkflowNode.K:
                    call_context["node_attempt_id"] = attempt.id
                node_result = self.node_runner.run(run_id, node, call_context)
                self._validate_result(node, node_result)
                self._validate_scope(context, node_result)
            except Exception as error:
                if self._is_auth_failure(error):
                    self.store.finish_node_attempt(
                        attempt,
                        "INTERRUPTED",
                        {
                            "failure": "authentication_required",
                            "_coordinator": {
                                "paused_node": node.value,
                                "next_node": None,
                                "payload": {},
                            },
                        },
                    )
                    return self.store.transition(
                        run_id, RunState.NEEDS_AUTH, "authentication required"
                    )
                if self._is_model_failure(error):
                    self.store.finish_node_attempt(
                        attempt,
                        "INTERRUPTED",
                        {
                            "failure": "planner_unavailable",
                            "_coordinator": {
                                "paused_node": node.value,
                                "next_node": None,
                                "payload": {},
                            },
                        },
                    )
                    return self.store.transition(
                        run_id, RunState.PAUSED_MODEL, "planner retries exhausted"
                    )
                self.store.finish_node_attempt(
                    attempt,
                    "FAILED",
                    {"failure": type(error).__name__, "node": node.value},
                )
                return self.store.transition(
                    run_id, RunState.FAILED, f"node {node.value} failed closed"
                )

            try:
                if node_result.run_state is RunState.NEEDS_AUTH:
                    summary = self._attempt_summary(node_result, node)
                    summary["_coordinator"]["paused_node"] = node.value
                    self.store.finish_node_attempt(attempt, "COMPLETED", summary)
                    return self.store.transition(
                        run_id, RunState.NEEDS_AUTH, "authentication required"
                    )
                if node_result.run_state is RunState.PAUSED_MODEL:
                    summary = self._attempt_summary(node_result, node)
                    summary["_coordinator"]["paused_node"] = node.value
                    self.store.finish_node_attempt(attempt, "COMPLETED", summary)
                    return self.store.transition(
                        run_id, RunState.PAUSED_MODEL, "planner retries exhausted"
                    )

                payload = self._json_object(node_result.payload, "node payload")
                context.update(payload)
                context["last_summary"] = self._json_object(
                    node_result.summary, "node summary"
                )
                routes = list(context.get("route_history", []))
                routes.append(node.value)
                context["route_history"] = routes
                if node is WorkflowNode.D and isinstance(payload.get("scope"), dict):
                    selected_scope = dict(payload["scope"])
                    context["scope"] = selected_scope
                    context["scope_lock"] = selected_scope
                if node is WorkflowNode.I:
                    fingerprints_since_k.update(self._fingerprints(payload))

                if node is WorkflowNode.K:
                    consecutive_no_progress = (
                        0 if fingerprints_since_k else consecutive_no_progress + 1
                    )
                    fingerprints_since_k.clear()
                    self._ensure_k_diagnosis(run_id, attempt.id, node_result)
                    self._record_k_experiences(run_id, context, node_result)

                self.store.finish_node_attempt(
                    attempt, "COMPLETED", self._attempt_summary(node_result, node)
                )
            except Exception as error:
                self.store.finish_node_attempt(
                    attempt,
                    "FAILED",
                    {"failure": type(error).__name__, "node": node.value},
                )
                return self.store.transition(
                    run_id, RunState.FAILED, f"node {node.value} failed closed"
                )

            if node is WorkflowNode.K and consecutive_no_progress >= 2:
                return self._record_only(run_id, RunState.NO_PROGRESS, "NO_PROGRESS")
            if node is WorkflowNode.L and node_result.next_node is WorkflowNode.M:
                return self._await_approval(run_id, context, node_result)
            next_node = node_result.next_node
            if next_node is None:
                return self._fail_without_attempt(run_id, node, "node returned no route")
            node = next_node

    def _validate_result(self, node: WorkflowNode, result: object) -> None:
        if not isinstance(result, NodeResult):
            raise CoordinatorError("node runner must return NodeResult")
        if result.node is not node:
            raise CoordinatorError("returned node does not match invoked node")
        if result.run_state not in {None, RunState.NEEDS_AUTH, RunState.PAUSED_MODEL}:
            raise CoordinatorError("node cannot control terminal run state")
        route = result.next_node
        if node in FORWARD:
            allowed = {FORWARD[node]}
        elif node is WorkflowNode.K:
            allowed = set(K_ROUTES)
        elif node is WorkflowNode.L:
            allowed = set(L_ROUTES)
        else:
            allowed = set()
        if result.run_state is None and route not in allowed:
            raise CoordinatorError(f"route from {node.value} is not allowed")
        if result.run_state is not None and route is not None:
            raise CoordinatorError("paused node must not return a route")

    def _validate_scope(
        self, context: Mapping[str, object], result: NodeResult
    ) -> None:
        locked = context.get("scope_lock")
        candidate = result.payload.get("scope")
        if not isinstance(locked, Mapping) or not isinstance(candidate, Mapping):
            return
        for key, value in locked.items():
            if key in candidate and candidate[key] != value:
                raise CoordinatorError(f"node attempted to change locked scope {key}")

    def _initial_context(self, config: RunConfig) -> dict[str, object]:
        lock = {
            key: value
            for key, value in {
                "region": config.region,
                "delay": config.delay,
                "universe": config.universe,
                "neutralization": config.neutralization,
            }.items()
            if value is not None
        }
        return {
            "run_config": asdict(config),
            "scope_mode": config.scope_mode.value,
            "scope_lock": lock,
            "route_history": [],
        }

    def _rules_manifest(self, node: WorkflowNode) -> dict[str, object]:
        matches = sorted(self.workflow_root.glob(f"{node.value}_*/node.md"))
        if len(matches) != 1:
            raise CoordinatorError(f"workflow rules for node {node.value} are unavailable")
        path = matches[0]
        rules = path.read_text(encoding="utf-8")
        return {
            "node": node.value,
            "rules_path": str(path),
            "rules_sha256": hashlib.sha256(rules.encode("utf-8")).hexdigest(),
            "rules": rules,
        }

    def _attempt_summary(
        self, result: NodeResult, node: WorkflowNode
    ) -> dict[str, object]:
        summary = self._json_object(result.summary, "node summary")
        summary["_coordinator"] = {
            "node": node.value,
            "next_node": None if result.next_node is None else result.next_node.value,
            "payload": self._json_object(result.payload, "node payload"),
            "run_state": None if result.run_state is None else result.run_state.value,
        }
        return summary

    def _usage(self, run_id: str) -> UsageSnapshot:
        run = self.store.get_run(run_id)
        summary = self.store.usage_summary(run_id)
        coordinator = summary.get("coordinator", {})
        planner = summary.get("planner", {})
        operator = summary.get("operator", {})
        with closing(self.store.connect()) as connection:
            simulations = connection.execute(
                "SELECT COUNT(*) FROM simulations WHERE run_id = ?", (run_id,)
            ).fetchone()[0]
            rounds = connection.execute(
                "SELECT COUNT(*) FROM node_attempts WHERE run_id = ? "
                "AND node = ? AND status = 'COMPLETED'",
                (run_id, WorkflowNode.K.value),
            ).fetchone()[0]
        elapsed = 0.0
        if run.created_at:
            try:
                created = datetime.fromisoformat(run.created_at.replace("Z", "+00:00"))
                elapsed = max(
                    0.0,
                    (datetime.now(timezone.utc) - created).total_seconds() / 60.0,
                )
            except ValueError:
                elapsed = 0.0
        return UsageSnapshot(
            simulations=int(coordinator.get("simulations", simulations)),
            planner_calls=int(planner.get("calls", 0)),
            operator_calls=int(operator.get("calls", 0)),
            elapsed_minutes=elapsed,
            rounds=int(coordinator.get("rounds", rounds)),
            model_cost_usd=float(planner.get("cost_usd", 0.0))
            + float(operator.get("cost_usd", 0.0)),
        )

    def _record_only(
        self, run_id: str, state: RunState, reason: str
    ) -> RunRecord:
        finalizer = getattr(self.submission, "finalize_record_only", None)
        if not callable(finalizer):
            finalizer = getattr(self.submission, "record_only", None)
        if callable(finalizer):
            finalizer(run_id, state, reason)
        current = self.store.get_run(run_id)
        if current.state is RunState.RUNNING:
            current = self.store.transition(run_id, state, reason)
        self._update_experiences(run_id, state.value, (), approval="NOT_REQUESTED")
        return current

    def _await_approval(
        self,
        run_id: str,
        context: dict[str, object],
        result: NodeResult,
    ) -> RunRecord:
        alpha_id = result.payload.get("alpha_id")
        if type(alpha_id) is not str or not alpha_id.strip():
            selected = result.payload.get("selected_alpha")
            alpha_id = selected.get("alpha_id") if isinstance(selected, Mapping) else None
        if type(alpha_id) is not str or not alpha_id.strip():
            return self._fail_without_attempt(run_id, WorkflowNode.L, "missing alpha id")
        alpha_id = alpha_id.strip()
        latest_plan = self.store.get_latest_research_plan(run_id)
        plan_version = 1 if latest_plan is None else latest_plan.plan_version
        plan_hash = "unavailable" if latest_plan is None else latest_plan.plan_hash
        usage = self.store.usage_summary(run_id)
        raw_report = result.payload.get("report", result.payload.get("final_report", {}))
        checks = []
        if isinstance(raw_report, Mapping):
            raw_checks = raw_report.get("checks", [])
            checks = raw_checks if isinstance(raw_checks, list) else [raw_checks]
        report = build_final_report(
            run_id=run_id,
            run_config=asdict(self.store.get_run(run_id).config),
            scope=dict(context.get("scope", context.get("scope_lock", {}))),
            plan_version=plan_version,
            plan_hash=plan_hash,
            candidate={"alpha_id": alpha_id, "final_checks": raw_report},
            checks=checks,
            evidence_refs=[str(item) for item in result.artifact_ids],
            route_history=list(context.get("route_history", [])) + [WorkflowNode.M.value],
            budgets={"policy": asdict(self.policy.budget), "usage": usage},
            role_usage=usage,
            terminal_recommendation={"decision": "SUBMIT", "alpha_id": alpha_id},
        )
        attempt = self.store.start_node_attempt(run_id, WorkflowNode.M)
        try:
            written = write_final_report(self.artifacts, run_id, report)
        except BaseException as error:
            self.store.finish_node_attempt(
                attempt, "FAILED", {"failure": type(error).__name__}
            )
            return self.store.transition(
                run_id, RunState.FAILED, "final report generation failed"
            )
        artifact_ids = tuple(
            str(getattr(item, "id"))
            for item in (written.json_artifact, written.markdown_artifact)
            if getattr(item, "id", None) is not None
        )
        self.store.finish_node_attempt(
            attempt,
            "COMPLETED",
            {
                "status": "awaiting_approval",
                "alpha_id": alpha_id,
                "report_hash": written.approval_subject["report_hash"],
                "artifact_ids": list(artifact_ids),
            },
        )
        run = self.store.transition(
            run_id, RunState.AWAITING_APPROVAL, "final report awaits human approval"
        )
        self._update_experiences(
            run_id, "RECOMMEND_SUBMIT", artifact_ids, approval="PENDING"
        )
        return run

    def _record_k_experiences(
        self, run_id: str, context: Mapping[str, object], result: NodeResult
    ) -> None:
        scope = context.get("scope", context.get("scope_lock", {}))
        if not isinstance(scope, Mapping):
            return
        region = scope.get("region")
        delay = scope.get("delay")
        category = scope.get("category", "UNKNOWN")
        if type(region) is not str or type(delay) is not int or type(category) is not str:
            return
        candidates: list[Mapping[str, object]] = []
        for source in (
            result.payload.get("evaluated_candidates"),
            result.payload.get("metrics"),
            context.get("alpha_results"),
            context.get("accepted"),
        ):
            if isinstance(source, (list, tuple)):
                candidates = [
                    item
                    for item in source
                    if isinstance(item, Mapping)
                    and type(
                        item.get("fingerprint", item.get("expression_fingerprint"))
                    )
                    is str
                ]
                if candidates:
                    break
        diagnosis = result.payload.get("diagnosis")
        diagnosed = (
            diagnosis.get("failure_class") if isinstance(diagnosis, Mapping) else None
        )
        failure_class = str(
            result.payload.get("failure_class")
            or result.summary.get("decision")
            or diagnosed
            or ("PASS" if result.next_node is WorkflowNode.L else "UNKNOWN")
        )
        for candidate in candidates:
            fingerprint = candidate.get(
                "fingerprint", candidate.get("expression_fingerprint")
            )
            if type(fingerprint) is not str or not fingerprint.strip():
                continue
            fields = candidate.get("field_ids", ["unknown"])
            if not isinstance(fields, list) or not fields:
                fields = ["unknown"]
            self.store.add_experience(
                run_id,
                {
                    "region": region,
                    "delay": delay,
                    "category": category,
                    "field_ids": [str(item) for item in fields],
                    "expression_fingerprint": fingerprint,
                    "failure_class": failure_class,
                    "hypothesis": candidate.get("hypothesis"),
                    "record": {"candidate": dict(candidate)},
                    "metrics": dict(candidate),
                },
            )

    def _ensure_k_diagnosis(
        self, run_id: str, attempt_id: int, result: NodeResult
    ) -> None:
        with closing(self.store.connect()) as connection:
            exists = connection.execute(
                "SELECT 1 FROM diagnoses WHERE run_id = ? AND node_attempt_id = ?",
                (run_id, attempt_id),
            ).fetchone()
        if exists is not None:
            return
        diagnosis = result.payload.get("diagnosis")
        diagnosis_payload = (
            dict(diagnosis) if isinstance(diagnosis, Mapping) else {}
        )
        failure_class = diagnosis_payload.get("failure_class")
        if type(failure_class) is not str or not failure_class.strip():
            decision = result.summary.get("decision")
            failure_class = (
                decision
                if type(decision) is str and decision.strip()
                else "PASS" if result.next_node is WorkflowNode.L else "UNKNOWN"
            )
        diagnosis_payload.update(
            {
                "failure_class": failure_class,
                "next_node": result.next_node.value,
                "coordinator_recorded": True,
            }
        )
        self.store.record_diagnosis(
            run_id,
            failure_class,
            result.next_node,
            diagnosis_payload,
            node_attempt_id=attempt_id,
        )

    def _update_experiences(
        self,
        run_id: str,
        final_decision: str,
        artifact_ids: tuple[str, ...],
        *,
        approval: str,
    ) -> None:
        self.store.finalize_run_experiences(
            run_id,
            final_decision=final_decision,
            approval_outcome=approval,
            terminal_artifact_ids=list(artifact_ids),
        )

    def _checkpoint(self, run_id: str) -> dict[str, object]:
        context: dict[str, object] = {}
        route = WorkflowNode.A
        paused_node: WorkflowNode | None = None
        no_progress = 0
        fingerprints: set[str] = set()
        with closing(self.store.connect()) as connection:
            rows = connection.execute(
                "SELECT node, status, summary_json FROM node_attempts "
                "WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
        incomplete_j = any(
            row["node"] == WorkflowNode.J.value and row["status"] == "RUNNING"
            for row in rows
        )
        for row in rows:
            if row["status"] not in {"COMPLETED", "INTERRUPTED"}:
                continue
            node = WorkflowNode(row["node"])
            summary = json.loads(row["summary_json"] or "{}")
            metadata = summary.get("_coordinator", {})
            payload = metadata.get("payload", {})
            if isinstance(payload, dict):
                context.update(payload)
            next_value = metadata.get("next_node")
            if type(next_value) is str:
                route = WorkflowNode(next_value)
            elif node in FORWARD:
                route = FORWARD[node]
            if type(metadata.get("paused_node")) is str:
                paused_node = WorkflowNode(metadata["paused_node"])
            if node is WorkflowNode.I:
                fingerprints.update(self._fingerprints(payload))
            if node is WorkflowNode.K:
                no_progress = 0 if fingerprints else no_progress + 1
                fingerprints.clear()
        return {
            "node": route,
            "paused_node": paused_node,
            "context": context,
            "no_progress": no_progress,
            "fingerprints": fingerprints,
            "incomplete_j": incomplete_j,
        }

    def _incomplete_simulations(self, run_id: str) -> list[str]:
        with closing(self.store.connect()) as connection:
            rows = connection.execute(
                "SELECT simulation_id FROM simulations WHERE run_id = ? "
                "AND status NOT IN ('COMPLETE','WARNING','ERROR','FAIL','FAILED') "
                "ORDER BY id",
                (run_id,),
            ).fetchall()
        return [row["simulation_id"] for row in rows]

    def _fail_without_attempt(
        self, run_id: str, node: WorkflowNode, reason: str
    ) -> RunRecord:
        return self.store.transition(
            run_id, RunState.FAILED, f"node {node.value}: {reason}"
        )

    @staticmethod
    def _fingerprints(payload: object) -> set[str]:
        if not isinstance(payload, Mapping):
            return set()
        values = payload.get("new_fingerprints", [])
        if not isinstance(values, (list, tuple)):
            raise CoordinatorError("new_fingerprints must be an array")
        if any(type(value) is not str or not value.strip() for value in values):
            raise CoordinatorError("new_fingerprints must contain nonblank strings")
        return set(values)

    @staticmethod
    def _json_object(value: object, label: str) -> dict[str, object]:
        if not isinstance(value, Mapping):
            raise CoordinatorError(f"{label} must be an object")
        try:
            return json.loads(
                json.dumps(
                    dict(value),
                    allow_nan=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
        except (TypeError, ValueError):
            raise CoordinatorError(f"{label} must contain finite JSON values") from None

    @staticmethod
    def _is_auth_failure(error: BaseException) -> bool:
        name = type(error).__name__.casefold()
        return isinstance(error, AuthenticationRequired) or "auth" in name

    @staticmethod
    def _is_model_failure(error: BaseException) -> bool:
        name = type(error).__name__
        module = type(error).__module__
        return isinstance(error, PlannerUnavailable) or (
            name
            in {
                "ModelError",
                "ModelTransportError",
                "ModelResponseError",
                "RoleRoutingError",
            }
            and ".models" in module
        )


__all__ = [
    "AgentCoordinator",
    "AuthenticationRequired",
    "CoordinatorError",
    "FORWARD",
    "K_ROUTES",
    "L_ROUTES",
    "NodeRegistryRunner",
    "NodeRunner",
    "PlannerUnavailable",
    "RegistryNodeRunner",
]
