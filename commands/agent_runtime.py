from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Mapping

from ..agent.artifacts import ArtifactWriter
from ..agent.config import AgentConfig
from ..agent.coordinator import AgentCoordinator
from ..agent.models.compatible import CompatibleAdapter
from ..agent.models.openai import OpenAIResponsesAdapter
from ..agent.models.router import ModelRouter
from ..agent.nodes.discovery import CoordinatorPlatformBinding, DiscoveryNodes
from ..agent.nodes.evaluation import EvaluationNodes
from ..agent.nodes.evidence import EvidenceNodes
from ..agent.nodes.research import (
    MIN_EXPRESSIONS_PER_IDEA,
    UNDERFILLED_IDEA_ERROR,
    ResearchNodes,
)
from ..agent.nodes.submission import SubmissionNode
from ..agent.policy import AgentPolicy
from ..agent.reporting import canonical_report_hash
from ..agent.runner import AgentRunner
from ..agent.store import AgentStore
from ..agent.types import ModelRole, NodeResult, RunState, WorkflowNode
from ..core.secrets import get_named_secret


@dataclass
class RuntimeBundle:
    run_id: str
    coordinator: AgentCoordinator | None
    submission: SubmissionNode
    artifacts: ArtifactWriter
    store: AgentStore

    def run_manual(self, **kwargs: Any) -> Any:
        if self.coordinator is None:
            raise RuntimeError("research coordinator is unavailable in submission runtime")
        return self.coordinator.run_manual(**kwargs)

    def run_auto(self, **kwargs: Any) -> Any:
        if self.coordinator is None:
            raise RuntimeError("research coordinator is unavailable in submission runtime")
        return self.coordinator.run_auto(**kwargs)

    def approve(self, run_id: str) -> dict[str, object]:
        artifact = self._final_report_artifact(run_id)
        report = self.artifacts.read_json(artifact)
        recommendation = report.get("terminal_recommendation")
        alpha_id = recommendation.get("alpha_id") if isinstance(recommendation, Mapping) else None
        if type(alpha_id) is not str or not alpha_id.strip():
            raise ValueError("final report has no recommended alpha")
        self.store.record_approval(run_id, alpha_id, canonical_report_hash(report))
        result = self.submission.submit(run_id, alpha_id, report)
        return {"ok": True, "run_id": run_id, "state": result.run_state.value}

    def _final_report_artifact(self, run_id: str) -> Any:
        with closing(self.store.connect()) as connection:
            row = connection.execute(
                "SELECT id FROM artifacts WHERE run_id=? AND node='M' AND name='final_report.json' ORDER BY id DESC LIMIT 1",
                (run_id,),
            ).fetchone()
        if row is None:
            raise ValueError("final report artifact is missing")
        return self.store.get_artifact(int(row["id"]))


def build_runtime(config: AgentConfig, store: AgentStore, run_id: str) -> RuntimeBundle:
    artifacts = ArtifactWriter(config.run_root, store)
    policy = AgentPolicy(config.budget)
    runner = AgentRunner(store, policy, artifacts)
    router = ModelRouter(
        build_model_adapter(config, ModelRole.PLANNER),
        build_model_adapter(config, ModelRole.OPERATOR),
        store=store,
        run_id=run_id,
    )
    dispatcher = _Dispatcher(config, store, artifacts, runner, router)
    submission = SubmissionNode(runner=runner, store=store)
    coordinator = AgentCoordinator(
        store=store, policy=policy, node_runner=dispatcher,
        submission=submission, artifacts=artifacts,
    )
    return RuntimeBundle(run_id, coordinator, submission, artifacts, store)


def build_submission_runtime(
    config: AgentConfig, store: AgentStore, run_id: str
) -> RuntimeBundle:
    artifacts = ArtifactWriter(config.run_root, store)
    runner = AgentRunner(store, AgentPolicy(config.budget), artifacts)
    submission = SubmissionNode(runner=runner, store=store)
    return RuntimeBundle(run_id, None, submission, artifacts, store)


def build_model_adapter(config: AgentConfig, role: ModelRole) -> Any:
    model = config.models[role]
    if not model.model.strip():
        raise ValueError(f"missing {role.value} model ID")
    secret = get_named_secret(model.secret_name)
    if secret is None:
        raise ValueError(f"missing secret reference for {role.value}: {model.secret_name}")
    if model.api_style == "responses":
        return OpenAIResponsesAdapter(model, secret)
    if model.api_style == "chat_completions":
        return CompatibleAdapter(model, secret)
    raise ValueError(f"unsupported API style: {model.api_style}")


_adapter = build_model_adapter


class _Dispatcher:
    def __init__(self, config: AgentConfig, store: AgentStore, artifacts: ArtifactWriter, runner: AgentRunner, router: ModelRouter) -> None:
        self.config = config
        self.store = store
        self.artifacts = artifacts
        self.runner = runner
        self.discovery = DiscoveryNodes(runner=runner, router=router, store=store, artifacts=artifacts)
        self.evidence = EvidenceNodes(runner=runner, router=router, store=store, artifacts=artifacts)
        self.research = ResearchNodes(runner=runner, router=router, store=store, artifacts=artifacts)
        self.evaluation = EvaluationNodes(runner=runner, router=router, store=store, artifacts=artifacts)

    def run(self, run_id: str, node: WorkflowNode, context: dict[str, object]) -> NodeResult:
        if node is WorkflowNode.A:
            return self.discovery.run_a(run_id)
        if node is WorkflowNode.B:
            return self.discovery.run_b(run_id)
        if node is WorkflowNode.C:
            return self.discovery.run_c(run_id)
        if node is WorkflowNode.D:
            return self._run_d(run_id, context)
        scope = _mapping(context.get("scope", context.get("scope_lock")), "scope")
        if node is WorkflowNode.F:
            tower = context.get("tower")
            if not isinstance(tower, Mapping):
                scope_hash = str(context.get("scope_hash", "scope"))
                tower = {"id": f"scope-seed-{scope_hash[:12]}"}
            run_config = _mapping(context.get("run_config", {}), "run_config")
            dataset_id = run_config.get("dataset_id")
            return self.evidence.run_f(
                run_id,
                scope,
                tower,
                dataset_id=dataset_id if type(dataset_id) is str else None,
            )
        if node is WorkflowNode.G:
            requirements = _mapping(context.get("evidence_requirements", {}), "evidence_requirements")
            keywords = requirements.get("keywords", ["market mechanism"])
            if type(keywords) is str:
                keywords = [keywords]
            elif not isinstance(keywords, (list, tuple)):
                keywords = ["market mechanism"]
            return self.evidence.run_g(run_id, list(keywords))
        if node is WorkflowNode.H:
            refinement_context = {
                key: context[key]
                for key in (
                    "diagnosis",
                    "metrics",
                    "template_density",
                    "anti_patterns",
                )
                if key in context
            }
            return self.research.run_h(
                run_id, scope, str(context.get("current_tower", context.get("tower_id", "REGULAR"))),
                list(context.get("candidate_fields", context.get("fields", []))),
                _mapping(context.get("evidence_bundle"), "evidence_bundle"),
                refinement_context=refinement_context or None,
            )
        if node is WorkflowNode.I:
            refinement_context = {
                key: context[key]
                for key in (
                    "diagnosis",
                    "metrics",
                    "template_density",
                    "anti_patterns",
                )
                if key in context
            }
            return self.research.run_i(
                run_id,
                scope,
                self._operators(run_id),
                refinement_context=refinement_context or None,
            )
        if node is WorkflowNode.J:
            return self._run_j(run_id, scope, context)
        if node is WorkflowNode.K:
            plan = self.store.get_latest_research_plan(run_id)
            if plan is None:
                raise ValueError("evaluation requires a locked research plan")
            return self.evaluation.run_k(
                run_id,
                _alpha_results_for_plan(
                    context.get("alpha_results", []),
                    plan.plan_version,
                    plan.plan_hash,
                ),
                evidence_ids=list(context.get("evidence_refs", [])),
                node_attempt_id=context.get("node_attempt_id") if type(context.get("node_attempt_id")) is int else None,
            )
        if node is WorkflowNode.L:
            selected = _mapping(context.get("selected_alpha", {}), "selected_alpha")
            alpha_id = selected.get("alpha_id", context.get("alpha_id"))
            return self.evaluation.run_l(run_id, str(alpha_id))
        raise ValueError(f"unsupported runtime node: {node.value}")

    def _run_j(
        self,
        run_id: str,
        scope: Mapping[str, object],
        context: Mapping[str, object],
    ) -> NodeResult:
        plan = self.store.get_latest_research_plan(run_id)
        if plan is None:
            raise ValueError("simulation requires a locked research plan")
        mechanisms = [
            dict(item)
            for item in plan.plan.get("mechanisms", [])
            if isinstance(item, Mapping)
            and type(item.get("mechanism_id")) is str
            and item["mechanism_id"].strip()
        ]
        if not mechanisms:
            raise ValueError("simulation requires at least one persisted research idea")
        ideas = self.store.sync_research_ideas(
            run_id,
            plan.plan_version,
            plan.plan_hash,
            mechanisms,
        )
        for idea in ideas:
            mechanism_id = idea.idea.get("mechanism_id")
            if (
                not idea.abort_requested
                and idea.stage == "SIMULATE"
                and idea.status in {"READY", "ERROR"}
                and type(mechanism_id) is str
                and len(self._idea_candidates(run_id, mechanism_id))
                < MIN_EXPRESSIONS_PER_IDEA
            ):
                self.store.set_research_idea_status(
                    run_id,
                    idea.idea_id,
                    "PENDING_INSPECT",
                    stage="INSPECT",
                    error=(
                        f"{UNDERFILLED_IDEA_ERROR} "
                        f"{MIN_EXPRESSIONS_PER_IDEA} validated expressions"
                    ),
                )
        ideas = self.store.list_research_ideas(
            run_id, plan_version=plan.plan_version
        )
        inspect_pending = [
            idea
            for idea in ideas
            if not idea.abort_requested
            and idea.stage == "INSPECT"
            and idea.status in {"PENDING_INSPECT", "INSPECTING", "ERROR"}
        ]
        prior_results = _alpha_results_for_plan(
            context.get("alpha_results", []),
            plan.plan_version,
            plan.plan_hash,
        )
        if inspect_pending:
            return NodeResult(
                WorkflowNode.J,
                {
                    "status": "NEEDS_INSPECTION",
                    "pending_idea_ids": [item.idea_id for item in inspect_pending],
                },
                next_node=WorkflowNode.I,
                payload={
                    "alpha_results": prior_results,
                    "new_fingerprints": [],
                    "platform_failures": [],
                },
            )
        waiting = [
            idea
            for idea in ideas
            if not idea.abort_requested
            and idea.stage == "SIMULATE"
            and idea.status in {"READY", "ERROR"}
        ]
        eligible = [idea for idea in waiting if _retry_due(idea.next_retry_at)]
        if not eligible:
            if waiting:
                retry_after = _retry_wait_seconds(waiting)
                return NodeResult(
                    WorkflowNode.J,
                    {
                        "status": "RETRY_WAIT",
                        "pending_idea_ids": [item.idea_id for item in waiting],
                        "retry_after_seconds": retry_after,
                    },
                    next_node=WorkflowNode.J,
                    payload={
                        "alpha_results": prior_results,
                        "new_fingerprints": [],
                        "platform_failures": [],
                        "retry_after_seconds": retry_after,
                    },
                )
            return NodeResult(
                WorkflowNode.J,
                {
                    "simulations": self._simulation_count(run_id),
                    "alphas": len(prior_results),
                    "completed_ideas": sum(
                        item.status == "COMPLETED" for item in ideas
                    ),
                },
                next_node=WorkflowNode.K,
                payload={
                    "simulation_ids": self._simulation_ids(run_id),
                    "alpha_results": prior_results,
                    "new_fingerprints": [],
                    "platform_failures": [],
                },
            )

        idea = eligible[0]
        mechanism_id = idea.idea.get("mechanism_id")
        if type(mechanism_id) is not str or not mechanism_id.strip():
            raise ValueError("persisted idea has no mechanism id")
        candidates = self._idea_candidates(run_id, mechanism_id)
        attempt = self.store.begin_idea_attempt(
            run_id, idea.idea_id, "SIMULATE"
        )
        try:
            if not candidates:
                raise ValueError("idea has no validated candidates to simulate")
            resume_ids, create_candidates = self._idea_simulation_work(
                run_id, candidates
            )
            batch = self.evaluation.run_j(
                run_id,
                scope,
                candidates,
                resume_simulation_ids=resume_ids,
                idea_id=idea.idea_id,
                create_candidates=create_candidates,
            )
            failures = list(batch.platform_failures)
            if failures and _platform_requires_auth(failures):
                self.store.finish_idea_attempt(
                    attempt,
                    "FAILED",
                    "ERROR",
                    detail={"failure": "authentication_required"},
                    error="WorldQuant authentication required",
                )
                return NodeResult(
                    WorkflowNode.J,
                    {
                        "idea_id": idea.idea_id,
                        "idea_status": "ERROR",
                        "reason": "WorldQuant authentication required",
                    },
                    run_state=RunState.NEEDS_AUTH,
                    payload={
                        "alpha_results": prior_results,
                        "new_fingerprints": [],
                        "platform_failures": failures,
                    },
                )
            if failures and _platform_requires_vector_reduction(failures):
                reason = "VECTOR fields require a vec_* reducer before other operators"
                self.store.finish_idea_attempt(
                    attempt,
                    "FAILED",
                    "ERROR",
                    detail={
                        "failure": "vector_reducer_required",
                        "platform_failures": failures,
                    },
                    error=reason,
                )
                return NodeResult(
                    WorkflowNode.J,
                    {
                        "idea_id": idea.idea_id,
                        "idea_status": "ERROR",
                        "reason": reason,
                    },
                    next_node=WorkflowNode.H,
                    payload={
                        "alpha_results": prior_results,
                        "new_fingerprints": [],
                        "platform_failures": failures,
                        "expression_validation_failure": {
                            "code": "VECTOR_REDUCER_REQUIRED",
                            "idea_id": idea.idea_id,
                            "reason": reason,
                        },
                    },
                )
            if failures or not batch.alpha_results:
                reason = (
                    "simulation returned platform failures"
                    if failures
                    else "simulation produced no alpha results"
                )
                raise ValueError(reason)
            current = self.store.get_research_idea(run_id, idea.idea_id)
            if current.abort_requested:
                self.store.finish_idea_attempt(
                    attempt,
                    "ABORTED",
                    "ABORTED",
                    detail={"simulation_ids": list(batch.simulation_ids)},
                    error="aborted by user",
                )
                return NodeResult(
                    WorkflowNode.J,
                    {"idea_id": idea.idea_id, "idea_status": "ABORTED"},
                    next_node=WorkflowNode.J,
                    payload={"alpha_results": prior_results, "new_fingerprints": []},
                )
            self.store.finish_idea_attempt(
                attempt,
                "COMPLETED",
                "COMPLETED",
                detail={
                    "simulation_ids": list(batch.simulation_ids),
                    "alpha_count": len(batch.alpha_results),
                },
            )
        except Exception as error:
            current = self.store.get_research_idea(run_id, idea.idea_id)
            error_text = " ".join(str(error).split())[:1000] or type(error).__name__
            if not current.abort_requested:
                retry_after = min(60, 5 * (2 ** min(current.retry_count, 4)))
                self.store.finish_idea_attempt(
                    attempt,
                    "FAILED",
                    "ERROR",
                    detail={"error_type": type(error).__name__},
                    error=error_text,
                    retry_after_seconds=retry_after,
                )
            else:
                retry_after = 0
                self.store.finish_idea_attempt(
                    attempt,
                    "ABORTED",
                    "ABORTED",
                    detail={"error_type": type(error).__name__},
                    error="aborted by user",
                )
            other_ready = any(
                item.idea_id != idea.idea_id
                and not item.abort_requested
                and item.stage == "SIMULATE"
                and item.status in {"READY", "ERROR"}
                and _retry_due(item.next_retry_at)
                for item in self.store.list_research_ideas(
                    run_id, plan_version=plan.plan_version
                )
            )
            loop_delay = 0 if other_ready else retry_after
            return NodeResult(
                WorkflowNode.J,
                {
                    "idea_id": idea.idea_id,
                    "idea_status": "ABORTED" if current.abort_requested else "ERROR",
                    "reason": error_text,
                    "retry_after_seconds": loop_delay,
                },
                next_node=WorkflowNode.J,
                payload={
                    "alpha_results": prior_results,
                    "new_fingerprints": [],
                    "platform_failures": [
                        {"idea_id": idea.idea_id, "reason": error_text}
                    ],
                    "retry_after_seconds": loop_delay,
                },
            )

        combined = _merge_alpha_results(prior_results, list(batch.alpha_results))
        remaining = [
            item.idea_id
            for item in self.store.list_research_ideas(
                run_id, plan_version=plan.plan_version
            )
            if not item.abort_requested
            and item.stage == "SIMULATE"
            and item.status in {"READY", "ERROR"}
        ]
        return NodeResult(
            WorkflowNode.J,
            {
                "idea_id": idea.idea_id,
                "idea_status": "COMPLETED",
                "simulations": len(batch.simulation_ids),
                "alphas": len(batch.alpha_results),
                "pending_idea_ids": remaining,
            },
            next_node=WorkflowNode.J if remaining else WorkflowNode.K,
            payload={
                "simulation_ids": self._simulation_ids(run_id),
                "alpha_results": combined,
                "new_fingerprints": list(batch.new_fingerprints),
                "platform_failures": [],
            },
        )

    def _idea_candidates(
        self, run_id: str, idea_id: str
    ) -> list[dict[str, object]]:
        plan = self.store.get_latest_research_plan(run_id)
        if plan is None:
            return []
        output: list[dict[str, object]] = []
        for record in self.store.list_candidates(run_id):
            candidate = record.candidate
            candidate_version = candidate.get("plan_version")
            candidate_hash = candidate.get("plan_hash")
            matches_plan = (
                candidate_version == plan.plan_version
                and candidate_hash == plan.plan_hash
            ) or (
                plan.plan_version == 1
                and candidate_version is None
                and candidate_hash is None
            )
            if (
                record.status not in {"ACCEPTED", "REVALIDATED"}
                or candidate.get("mechanism_id") != idea_id
                or not matches_plan
            ):
                continue
            output.append(
                {
                    "fingerprint": record.expression_fingerprint,
                    "candidate": dict(candidate),
                }
            )
        return output

    def _idea_simulation_work(
        self, run_id: str, candidates: list[dict[str, object]]
    ) -> tuple[list[str], list[dict[str, object]]]:
        by_fingerprint = {
            record.expression_fingerprint: record.id
            for record in self.store.list_candidates(run_id)
        }
        by_id = {
            by_fingerprint[item["fingerprint"]]: item
            for item in candidates
            if type(item.get("fingerprint")) is str
            and item["fingerprint"] in by_fingerprint
        }
        with closing(self.store.connect()) as connection:
            rows = connection.execute(
                "SELECT simulation_id,candidate_id,status FROM simulations "
                "WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
        reusable = [
            str(row["simulation_id"])
            for row in rows
            if row["candidate_id"] in by_id
            and row["status"] not in {"ERROR", "FAIL", "FAILED"}
        ]
        reusable_candidates = {
            int(row["candidate_id"])
            for row in rows
            if row["candidate_id"] in by_id
            and row["status"] not in {"ERROR", "FAIL", "FAILED"}
        }
        create = [
            candidate
            for candidate_id, candidate in by_id.items()
            if candidate_id not in reusable_candidates
        ]
        return reusable, create

    def _simulation_ids(self, run_id: str) -> list[str]:
        with closing(self.store.connect()) as connection:
            rows = connection.execute(
                "SELECT simulation_id FROM simulations WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
        return [str(row["simulation_id"]) for row in rows]

    def _simulation_count(self, run_id: str) -> int:
        return len(self._simulation_ids(run_id))

    def _run_d(self, run_id: str, context: Mapping[str, object]) -> NodeResult:
        sim = self.runner.run(run_id, WorkflowNode.J, ("sim", "options"), "coordinator_sim_options.json")
        categories = self.runner.run(run_id, WorkflowNode.D, ("data", "categories"), "coordinator_data_categories.json")
        sim_artifact = self.artifacts.write_json(run_id, WorkflowNode.D, "validated_sim_options.json", sim.payload)
        category_artifact = self.artifacts.write_json(run_id, WorkflowNode.D, "data_categories.json", categories.payload)
        binding = CoordinatorPlatformBinding(sim_artifact.id, dict(sim.payload), category_artifact.id, dict(categories.payload))
        run = self.store.get_run(run_id)
        dataset_id = run.config.dataset_id
        if type(dataset_id) is not str or not dataset_id.strip():
            raise ValueError("research run requires an explicitly selected dataset")
        dataset_result = self.runner.run(
            run_id,
            WorkflowNode.D,
            ("data", "dataset", dataset_id.strip()),
            "selected_dataset.json",
        )
        dataset_body = _successful_platform_body(
            dataset_result.payload, "selected dataset"
        )
        dataset_constraint = _dataset_scope_constraint(
            dataset_body, dataset_id.strip()
        )
        candidates = None
        if run.config.scope_mode.value == "manual":
            candidates = {"quarter": {}, "consultant_summary": {}, "quarter_towers": [{
                "candidate_id": "manual-scope", "region": run.config.region, "delay": run.config.delay,
                "universe": run.config.universe, "neutralization": run.config.neutralization,
                "category": dataset_constraint["category"], "alphaCount": 0, "neededToLight": 0, "multiplier": 1,
            }]}
        artifact_id = getattr(getattr(dataset_result, "artifact", None), "id", None)
        return self.discovery.run_d(
            run_id,
            run.config,
            candidates,
            platform_binding=binding,
            user_id=self._user_id(run_id),
            dataset_constraint=dataset_constraint,
            dataset_artifact_id=(
                artifact_id if type(artifact_id) is int and artifact_id > 0 else None
            ),
        )

    def _user_id(self, run_id: str) -> str | None:
        with self.store.connect() as connection:
            row = connection.execute("SELECT id FROM artifacts WHERE run_id=? AND node='A' AND name='auth_status.json' ORDER BY id DESC LIMIT 1", (run_id,)).fetchone()
        if row is None:
            return None
        body = self.artifacts.read_json(self.store.get_artifact(int(row["id"])))
        response = body.get("response", {}) if isinstance(body, dict) else {}
        value = response.get("body", body) if isinstance(response, dict) else body
        user = value.get("user", {}) if isinstance(value, dict) else {}
        identifier = user.get("id") if isinstance(user, dict) else None
        return identifier if isinstance(identifier, str) else None

    def _operators(self, run_id: str) -> dict[str, Mapping[str, object]]:
        result = self.runner.run(run_id, WorkflowNode.I, ("data", "operators"), "operators.json")
        payload = result.payload
        response = payload.get("response", {}) if isinstance(payload, Mapping) else {}
        body = response.get("body", response) if isinstance(response, Mapping) else {}
        if isinstance(body, list):
            rows = body
        elif isinstance(body, Mapping):
            rows = body.get("results", body.get("operators", []))
        else:
            rows = []
        return {
            str(item["name"]): {
                **dict(item),
                "arity": _operator_arity(item),
            }
            for item in rows
            if isinstance(item, Mapping) and isinstance(item.get("name"), str)
        }


def _operator_arity(item: Mapping[str, object]) -> int:
    value = item.get("arity")
    if type(value) is int and value >= 0:
        return value
    definition = item.get("definition")
    if not isinstance(definition, str):
        return 1
    match = re.search(r"\(([^()]*)\)", definition)
    if match is None:
        return 1
    count = 0
    for parameter in match.group(1).split(","):
        parameter = parameter.strip()
        if not parameter or "=" in parameter or "..." in parameter:
            break
        count += 1
    return count


def _retry_due(value: str | None) -> bool:
    if value is None:
        return True
    try:
        due = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return True
    return due <= datetime.now(timezone.utc)


def _platform_requires_auth(value: object) -> bool:
    if isinstance(value, Mapping):
        if value.get("status_code") in {401, 403}:
            return True
        return any(_platform_requires_auth(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_platform_requires_auth(item) for item in value)
    return False


def _platform_requires_vector_reduction(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(_platform_requires_vector_reduction(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_platform_requires_vector_reduction(item) for item in value)
    if type(value) is not str:
        return False
    normalized = " ".join(value.casefold().split())
    return (
        "does not support event inputs" in normalized
        or "vector field" in normalized and "vec_" in normalized
    )


def _retry_wait_seconds(ideas: list[Any]) -> int:
    now = datetime.now(timezone.utc)
    waits: list[float] = []
    for idea in ideas:
        value = getattr(idea, "next_retry_at", None)
        if type(value) is not str:
            return 1
        try:
            due = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return 1
        waits.append(max(0.0, (due - now).total_seconds()))
    return max(1, min(60, int(min(waits, default=0.0)) + 1))


def _merge_alpha_results(
    previous: list[dict[str, object]], current: list[Mapping[str, object]]
) -> list[dict[str, object]]:
    merged: list[dict[str, object]] = []
    positions: dict[str, int] = {}
    for item in [*previous, *(dict(value) for value in current)]:
        identity = item.get("alpha_id")
        key = str(identity) if identity else repr(sorted(item.items()))
        if key in positions:
            merged[positions[key]] = dict(item)
        else:
            positions[key] = len(merged)
            merged.append(dict(item))
    return merged


def _alpha_results_for_plan(
    results: object,
    plan_version: int,
    plan_hash: str,
) -> list[dict[str, object]]:
    if not isinstance(results, (list, tuple)):
        return []
    filtered: list[dict[str, object]] = []
    for item in results:
        if not isinstance(item, Mapping):
            continue
        candidate_version = item.get("plan_version")
        candidate_hash = item.get("plan_hash")
        matches_plan = (
            candidate_version == plan_version and candidate_hash == plan_hash
        ) or (
            plan_version == 1
            and candidate_version is None
            and candidate_hash is None
        )
        if matches_plan:
            filtered.append(dict(item))
    return filtered


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"runtime context is missing {name}")
    return value


def _successful_platform_body(
    value: object, label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or value.get("ok") is not True:
        raise ValueError(f"{label} request failed")
    response = value.get("response")
    body = response.get("body") if isinstance(response, Mapping) else None
    if not isinstance(body, Mapping):
        raise ValueError(f"{label} response body is invalid")
    return body


def _dataset_scope_constraint(
    body: Mapping[str, Any], dataset_id: str
) -> dict[str, object]:
    if body.get("id") != dataset_id:
        raise ValueError("selected dataset response identity does not match")
    category = body.get("category")
    category_id = category.get("id") if isinstance(category, Mapping) else None
    if type(category_id) is not str or not category_id.strip():
        raise ValueError("selected dataset has no category")
    rows = body.get("data")
    if not isinstance(rows, list):
        raise ValueError("selected dataset has no scope availability")
    supported_scopes: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        region = row.get("region")
        delay = row.get("delay")
        universe = row.get("universe")
        if (
            type(region) is str
            and region.strip()
            and type(delay) is int
            and type(universe) is str
            and universe.strip()
        ):
            supported_scopes.append(
                {
                    "region": region.strip().upper(),
                    "delay": delay,
                    "universe": universe.strip().upper(),
                }
            )
    if not supported_scopes:
        raise ValueError("selected dataset has no supported research scope")
    return {
        "dataset_id": dataset_id,
        "category": category_id.strip().upper(),
        "supported_scopes": supported_scopes,
    }
