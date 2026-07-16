from __future__ import annotations

from dataclasses import dataclass
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
from ..agent.nodes.research import ResearchNodes
from ..agent.nodes.submission import SubmissionNode
from ..agent.policy import AgentPolicy
from ..agent.reporting import canonical_report_hash
from ..agent.runner import AgentRunner
from ..agent.store import AgentStore
from ..agent.types import ModelRole, NodeResult, WorkflowNode
from ..core.secrets import get_named_secret


@dataclass
class RuntimeBundle:
    run_id: str
    coordinator: AgentCoordinator
    submission: SubmissionNode
    artifacts: ArtifactWriter
    store: AgentStore

    def run_manual(self, **kwargs: Any) -> Any:
        return self.coordinator.run_manual(**kwargs)

    def run_auto(self, **kwargs: Any) -> Any:
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
        with self.store.connect() as connection:
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
        _adapter(config, ModelRole.PLANNER),
        _adapter(config, ModelRole.OPERATOR),
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


def _adapter(config: AgentConfig, role: ModelRole) -> Any:
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
            return self.evidence.run_f(run_id, scope, _mapping(context.get("tower", scope), "tower"))
        if node is WorkflowNode.G:
            requirements = _mapping(context.get("evidence_requirements", {}), "evidence_requirements")
            keywords = requirements.get("keywords", ("market mechanism",))
            return self.evidence.run_g(run_id, keywords if isinstance(keywords, list) else [str(keywords)])
        if node is WorkflowNode.H:
            return self.research.run_h(
                run_id, scope, str(context.get("current_tower", context.get("tower_id", "REGULAR"))),
                list(context.get("candidate_fields", context.get("fields", []))),
                _mapping(context.get("evidence_bundle"), "evidence_bundle"),
            )
        if node is WorkflowNode.I:
            return self.research.run_i(run_id, scope, self._operators(run_id))
        if node is WorkflowNode.J:
            batch = self.evaluation.run_j(
                run_id, scope, list(context.get("accepted", [])),
                resume_simulation_ids=list(context.get("resume_simulation_ids", [])),
            )
            return NodeResult(
                WorkflowNode.J, {"simulations": len(batch.simulation_ids), "alphas": len(batch.alpha_results)},
                next_node=WorkflowNode.K, payload={
                    "simulation_ids": list(batch.simulation_ids), "alpha_results": list(batch.alpha_results),
                    "new_fingerprints": list(batch.new_fingerprints), "platform_failures": list(batch.platform_failures),
                },
            )
        if node is WorkflowNode.K:
            return self.evaluation.run_k(
                run_id, list(context.get("alpha_results", [])),
                evidence_ids=list(context.get("evidence_refs", [])),
                node_attempt_id=context.get("node_attempt_id") if type(context.get("node_attempt_id")) is int else None,
            )
        if node is WorkflowNode.L:
            selected = _mapping(context.get("selected_alpha", {}), "selected_alpha")
            alpha_id = selected.get("alpha_id", context.get("alpha_id"))
            return self.evaluation.run_l(run_id, str(alpha_id))
        raise ValueError(f"unsupported runtime node: {node.value}")

    def _run_d(self, run_id: str, context: Mapping[str, object]) -> NodeResult:
        sim = self.runner.run(run_id, WorkflowNode.J, ("sim", "options"), "coordinator_sim_options.json")
        categories = self.runner.run(run_id, WorkflowNode.D, ("data", "categories"), "coordinator_data_categories.json")
        sim_artifact = self.artifacts.write_json(run_id, WorkflowNode.D, "validated_sim_options.json", sim.payload)
        category_artifact = self.artifacts.write_json(run_id, WorkflowNode.D, "data_categories.json", categories.payload)
        binding = CoordinatorPlatformBinding(sim_artifact.id, dict(sim.payload), category_artifact.id, dict(categories.payload))
        run = self.store.get_run(run_id)
        candidates = None
        if run.config.scope_mode.value == "manual":
            candidates = {"quarter": {}, "consultant_summary": {}, "quarter_towers": [{
                "candidate_id": "manual-scope", "region": run.config.region, "delay": run.config.delay,
                "universe": run.config.universe, "neutralization": run.config.neutralization,
                "category": "PV", "alphaCount": 0, "neededToLight": 0, "multiplier": 1,
            }]}
        return self.discovery.run_d(run_id, run.config, candidates, platform_binding=binding, user_id=self._user_id(run_id))

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
        rows = body.get("results", body.get("operators", [])) if isinstance(body, Mapping) else []
        return {str(item["name"]): dict(item) for item in rows if isinstance(item, Mapping) and isinstance(item.get("name"), str)}


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"runtime context is missing {name}")
    return value
