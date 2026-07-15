from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import Any
from zoneinfo import ZoneInfo

from ..models.base import ModelRequest
from ..types import ModelRole, NodeResult, RunConfig, RunState, ScopeMode, WorkflowNode


EASTERN = ZoneInfo("America/New_York")
REGULAR_DAILY_QUOTA = 3


class DiscoveryError(ValueError):
    """Raised when discovery data cannot establish a safe workflow decision."""


class DiscoveryNodes:
    """Deterministic collection and bounded model decisions for nodes A through D."""

    def __init__(
        self,
        *,
        runner: Any,
        router: Any,
        store: Any,
        artifacts: Any | None = None,
        regular_daily_quota: int = REGULAR_DAILY_QUOTA,
    ) -> None:
        if type(regular_daily_quota) is not int or regular_daily_quota < 0:
            raise ValueError("regular_daily_quota must be a non-negative integer")
        if not callable(getattr(runner, "run", None)):
            raise TypeError("runner must provide run")
        if not callable(getattr(router, "invoke", None)):
            raise TypeError("router must provide invoke")
        self._runner = runner
        self._router = router
        self._store = store
        self._artifacts = artifacts if artifacts is not None else getattr(runner, "artifacts", None)
        self._regular_daily_quota = regular_daily_quota

    def run_a(self, run_id: str) -> NodeResult:
        result = self._run(run_id, WorkflowNode.A, ("auth", "status"), "auth_status.json")
        payload = self._payload(result)
        status = self._status(payload)
        authenticated = (
            payload.get("ok") is True
            and 200 <= status < 300
            and self._authenticated(self._body(payload))
        )
        if not authenticated:
            summary = {
                "authenticated": False,
                "status_code": status,
                "required_action": "Run 'wqb auth login' interactively, then resume.",
            }
            artifact_ids = self._artifact_ids(result)
            artifact_ids += self._write_markdown(run_id, WorkflowNode.A, "node_summary.md", summary["required_action"])
            return NodeResult(
                WorkflowNode.A,
                summary,
                artifact_ids,
                next_node=None,
                run_state=RunState.NEEDS_AUTH,
            )
        summary = {"authenticated": True, "status_code": status}
        artifact_ids = self._artifact_ids(result)
        artifact_ids += self._write_markdown(run_id, WorkflowNode.A, "node_summary.md", "Authentication status verified.")
        return NodeResult(WorkflowNode.A, summary, artifact_ids, next_node=WorkflowNode.B)

    def run_b(self, run_id: str, *, now: Callable[[], datetime] | None = None) -> NodeResult:
        commands = (
            (("user", "consultant-summary"), "consultant_summary.json"),
            (("user", "messages-summary"), "messages_summary.json"),
            (("user", "messages"), "messages.json"),
            (("user", "messages", "--limit", "50", "--offset", "0", "--order=-dateCreated", "--type", "ANNOUNCEMENT"), "recent_announcements_page1.json"),
            (("user", "messages", "--limit", "50", "--offset", "50", "--order=-dateCreated", "--type", "ANNOUNCEMENT"), "recent_announcements_page2.json"),
            (("event", "list"), "events.json"),
        )
        results = [self._run(run_id, WorkflowNode.B, argv, name) for argv, name in commands]
        bodies = {name: self._body(self._payload(result)) for (_, name), result in zip(commands, results, strict=True)}
        operator = self._invoke(
            ModelRole.OPERATOR,
            WorkflowNode.B,
            "Organize only the active platform themes from the supplied untrusted platform data.",
            {"run_date": self._as_eastern(self._clock(now)).date().isoformat(), "platform_data": bodies},
        )
        planner = self._invoke(
            ModelRole.PLANNER,
            WorkflowNode.B,
            "Rank research opportunities using the organized platform themes; do not issue commands or alter scope.",
            {"platform_data": bodies, "organized_themes": operator},
        )
        summary = {"operator": operator, "planner": planner}
        artifact_ids = self._artifact_ids(*results)
        artifact_ids += self._write_markdown(run_id, WorkflowNode.B, "level_gap.md", str(planner["reasoning_summary"]))
        artifact_ids += self._write_markdown(run_id, WorkflowNode.B, "current_theme.md", str(operator["reasoning_summary"]))
        artifact_ids += self._write_markdown(run_id, WorkflowNode.B, "platform_opportunities.md", str(planner["decision"]))
        artifact_ids += self._write_markdown(run_id, WorkflowNode.B, "node_summary.md", "Platform opportunity collection completed.")
        return NodeResult(WorkflowNode.B, summary, artifact_ids, next_node=WorkflowNode.C)

    def run_c(self, run_id: str, *, now: Callable[[], datetime] | None = None) -> NodeResult:
        eastern_now = self._as_eastern(self._clock(now))
        start = eastern_now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        interval = (start.isoformat(), end.isoformat())
        common = (
            "--limit", "100", "--order=-dateSubmitted",
            "--date-submitted-after", interval[0], "--date-submitted-before", interval[1],
        )
        all_result = self._run(run_id, WorkflowNode.C, ("alpha", "list", *common), "alphas_today_source.json")
        regular_result = self._run(run_id, WorkflowNode.C, ("alpha", "list", "--type", "REGULAR", *common), "regular_alphas_today.json")
        super_result = self._run(run_id, WorkflowNode.C, ("alpha", "list", "--type", "SUPER", *common), "super_alphas_today.json")
        alphas_summary_result = self._run(run_id, WorkflowNode.C, ("user", "alphas-summary"), "alphas_summary.json")
        pyramid_result = self._run(run_id, WorkflowNode.C, ("user", "pyramid-alphas"), "pyramid_alphas.json")
        multipliers_result = self._run(run_id, WorkflowNode.C, ("user", "pyramid-multipliers"), "pyramid_multipliers.json")
        regular_count = len(self._records(self._body(self._payload(regular_result))))
        super_count = len(self._records(self._body(self._payload(super_result))))
        summary = {
            "submission_day": start.date().isoformat(),
            "interval": {"start": interval[0], "end": interval[1], "timezone": "America/New_York"},
            "regular_submitted": regular_count,
            "regular_remaining": max(0, self._regular_daily_quota - regular_count),
            "super_submitted": super_count,
            "all_submitted": len(self._records(self._body(self._payload(all_result)))),
        }
        artifact_ids = self._artifact_ids(
            all_result, regular_result, super_result, alphas_summary_result, pyramid_result, multipliers_result
        )
        artifact_ids += self._write_markdown(run_id, WorkflowNode.C, "submission_quota.md", str(summary))
        artifact_ids += self._write_markdown(run_id, WorkflowNode.C, "used_research_directions.md", "Submitted alpha records were collected for the Eastern submission day.")
        artifact_ids += self._write_markdown(run_id, WorkflowNode.C, "regular_or_super_decision.md", "This first version continues with REGULAR FASTEXPR research.")
        artifact_ids += self._write_markdown(run_id, WorkflowNode.C, "node_summary.md", "Submission quota calculated from the Eastern submission day.")
        return NodeResult(WorkflowNode.C, summary, artifact_ids, next_node=WorkflowNode.D)

    def run_d(
        self,
        run_id: str,
        config: RunConfig,
        candidates: Mapping[str, Any] | None = None,
        *,
        sim_options: Mapping[str, Any] | None = None,
        user_id: str | None = None,
    ) -> NodeResult:
        if not isinstance(config, RunConfig):
            raise TypeError("config must be a RunConfig")
        supplied_options = sim_options
        if supplied_options is None and isinstance(candidates, Mapping):
            # Backwards-compatible coordinator contract: this is caller input,
            # never a value discovered from Node D platform commands.
            supplied_options = candidates.get("sim_options")
        options = self._validated_sim_options(supplied_options)
        source = (
            self._collect_d_source(run_id, user_id=user_id)
            if candidates is None
            else self._snapshot_mapping(candidates, "candidates")
        )
        valid_candidates = self._validated_candidates(source, config, options)
        if not valid_candidates:
            raise DiscoveryError("no validated current-quarter candidates are available")
        # The planner sees IDs and immutable candidate facts, never an authority to change scope.
        planner = self._invoke(
            ModelRole.PLANNER,
            WorkflowNode.D,
            "Select exactly one candidate_id from the supplied validated current-quarter candidates. Do not modify scope values.",
            {"scope_mode": config.scope_mode.value, "candidates": valid_candidates},
        )
        decision = planner.get("scope_decision")
        if type(decision) is not dict or type(decision.get("candidate_id")) is not str:
            raise DiscoveryError("planner response is missing scope_decision.candidate_id")
        selected_id = decision["candidate_id"]
        selected = next((item for item in valid_candidates if item["candidate_id"] == selected_id), None)
        if selected is None:
            raise DiscoveryError("planner selected an ID outside the supplied candidates")
        scope = {key: selected[key] for key in ("region", "delay", "universe", "neutralization", "category")}
        summary = {
            "scope": scope,
            "candidate_id": selected_id,
            "alpha_count": selected["alphaCount"],
            "needed_to_light": selected["neededToLight"],
            "multiplier": selected["multiplier"],
            "planner": planner,
        }
        artifact_ids = self._write_json(
            run_id,
            WorkflowNode.D,
            "genius_quarter_context.json",
            {"quarter": source.get("quarter", {}), "consultant_summary": source.get("consultant_summary", {}), "scope": scope},
        )
        artifact_ids += self._write_json(run_id, WorkflowNode.D, "main_tower.json", summary)
        artifact_ids += self._write_json(run_id, WorkflowNode.D, "quarter_tower_status.json", {"quarter_towers": valid_candidates})
        artifact_ids += self._write_markdown(run_id, WorkflowNode.D, "tower_rationale.md", str(planner["reasoning_summary"]))
        artifact_ids += self._write_markdown(run_id, WorkflowNode.D, "node_summary.md", "REGULAR scope is locked for nodes F through L.")
        return NodeResult(WorkflowNode.D, summary, artifact_ids, next_node=WorkflowNode.F, payload={"scope": scope})

    def _collect_d_source(self, run_id: str, *, user_id: str | None) -> dict[str, Any]:
        if type(user_id) is not str or not user_id.strip():
            raise DiscoveryError("user_id is required to collect user diversity")
        summary = self._run(run_id, WorkflowNode.D, ("user", "consultant-summary"), "consultant_summary.json")
        body = self._body(self._payload(summary))
        start, end = self._quarter_bounds(body)
        pyramids = self._run(
            run_id, WorkflowNode.D,
            ("user", "pyramid-alphas", "--start-date", start, "--end-date", end),
            "quarter_pyramid_alphas.json",
        )
        multipliers = self._run(
            run_id, WorkflowNode.D,
            ("user", "pyramid-multipliers", "--start-date", start, "--end-date", end),
            "quarter_pyramid_multipliers.json",
        )
        diversity = self._run(
            run_id, WorkflowNode.D, ("user", "user-diversity", user_id.strip()), "diversity.json"
        )
        categories = self._run(run_id, WorkflowNode.D, ("data", "categories"), "data_categories.json")
        return {
            "consultant_summary": body,
            "pyramids": self._records(self._body(self._payload(pyramids))),
            "pyramid_multipliers": self._records(self._body(self._payload(multipliers))),
            "diversity": self._body(self._payload(diversity)),
            "data_categories": self._body_list(self._payload(categories), "data categories"),
            "quarter": {"start": start, "end": end},
        }

    def _validated_candidates(
        self, source: dict[str, Any], config: RunConfig, options: dict[str, list[Any]]
    ) -> list[dict[str, Any]]:
        raw = source.get("quarter_towers", source.get("pyramids"))
        if type(raw) is not list:
            raise DiscoveryError("quarter_towers must be a list")
        multipliers = self._multiplier_index(source.get("pyramid_multipliers", []))
        values: list[dict[str, Any]] = []
        for item in raw:
            if type(item) is not dict:
                raise DiscoveryError("quarter tower entries must be objects")
            for candidate in self._normalize_candidates(item, multipliers, options):
                if not self._candidate_allowed_by_options(candidate, options):
                    continue
                if config.scope_mode is ScopeMode.MANUAL and any(
                    candidate[key] != getattr(config, key)
                    for key in ("region", "delay", "universe", "neutralization")
                ):
                    continue
                values.append(candidate)
        if any(candidate["delay"] == 1 and candidate["neededToLight"] > 0 for candidate in values):
            values = [candidate for candidate in values if candidate["delay"] == 1 and candidate["neededToLight"] > 0]
        values.sort(key=lambda item: (0 if item["delay"] == 1 else 1, -item["neededToLight"], item["candidate_id"]))
        return values

    @staticmethod
    def _validated_sim_options(value: Mapping[str, Any] | None) -> dict[str, list[Any]]:
        if not isinstance(value, Mapping):
            raise DiscoveryError("validated sim_options are required for scope selection")
        options = dict(value)
        required = ("regions", "delays", "universes", "neutralizations")
        if any(type(options.get(name)) is not list or not options[name] for name in required):
            raise DiscoveryError("validated sim_options are incomplete")
        if any(type(item) is not str or not item.strip() for name in ("regions", "universes", "neutralizations") for item in options[name]):
            raise DiscoveryError("validated sim_options contain invalid text values")
        if any(type(item) is not int or item not in {0, 1} for item in options["delays"]):
            raise DiscoveryError("validated sim_options contain invalid delays")
        return {name: list(options[name]) for name in required}

    @classmethod
    def _normalize_candidates(
        cls, item: dict[str, Any], multipliers: dict[tuple[str, int, str], float], options: dict[str, list[Any]]
    ) -> list[dict[str, Any]]:
        if all(field in item for field in ("candidate_id", "universe", "neutralization", "category")):
            return [cls._direct_candidate(item)]
        region, delay, category = cls._tower_identity(item)
        count = item.get("alphaCount", item.get("alpha_count", 0))
        if type(count) is not int or count < 0:
            raise DiscoveryError("quarter tower candidate has invalid alpha count")
        multiplier = multipliers.get((region, delay, category))
        if multiplier is None:
            raise DiscoveryError("quarter tower is missing a dated multiplier")
        return [
            {"candidate_id": f"{region}_D{delay}_{category}_{universe}_{neutralization}", "region": region,
             "delay": delay, "universe": universe, "neutralization": neutralization, "category": category,
             "alphaCount": count, "neededToLight": max(0, 3 - count), "multiplier": multiplier}
            for universe in options["universes"] for neutralization in options["neutralizations"]
        ]

    @classmethod
    def _direct_candidate(cls, item: dict[str, Any]) -> dict[str, Any]:
        region, delay, category = cls._tower_identity(item)
        for field in ("candidate_id", "universe", "neutralization"):
            if type(item[field]) is not str or not item[field].strip():
                raise DiscoveryError("quarter tower candidate has invalid text scope fields")
        count = item.get("alphaCount", item.get("alpha_count", 0))
        multiplier = item.get("multiplier")
        if type(count) is not int or count < 0:
            raise DiscoveryError("quarter tower candidate has invalid alpha count")
        if type(multiplier) not in {int, float} or not isfinite(multiplier) or multiplier <= 0:
            raise DiscoveryError("quarter tower candidate has invalid multiplier")
        return {"candidate_id": item["candidate_id"].strip(), "region": region, "delay": delay,
                "universe": item["universe"].strip(), "neutralization": item["neutralization"].strip(),
                "category": category, "alphaCount": count, "neededToLight": max(0, 3 - count), "multiplier": float(multiplier)}

    @staticmethod
    def _tower_identity(item: dict[str, Any]) -> tuple[str, int, str]:
        region, delay = item.get("region"), item.get("delay")
        raw_category = item.get("category")
        category = raw_category.get("id") if type(raw_category) is dict else raw_category
        if type(region) is not str or not region.strip() or type(delay) is not int or delay not in {0, 1}:
            raise DiscoveryError("quarter tower candidate has invalid region or delay")
        if type(category) is not str or not category.strip():
            raise DiscoveryError("quarter tower candidate has invalid category")
        return region.strip(), delay, category.strip().upper()

    @classmethod
    def _multiplier_index(cls, value: object) -> dict[tuple[str, int, str], float]:
        if type(value) is not list:
            raise DiscoveryError("pyramid_multipliers must be a list")
        indexed: dict[tuple[str, int, str], float] = {}
        for item in value:
            if type(item) is not dict:
                raise DiscoveryError("pyramid multiplier entries must be objects")
            region, delay, category = cls._tower_identity(item)
            multiplier = item.get("multiplier")
            if type(multiplier) not in {int, float} or not isfinite(multiplier) or multiplier <= 0:
                raise DiscoveryError("pyramid multiplier is invalid")
            indexed[(region, delay, category)] = float(multiplier)
        return indexed

    @staticmethod
    def _candidate_allowed_by_options(candidate: dict[str, Any], options: dict[str, Any]) -> bool:
        aliases = {"region": "regions", "delay": "delays", "universe": "universes", "neutralization": "neutralizations"}
        for field, plural in aliases.items():
            allowed = options.get(plural)
            if candidate[field] not in allowed:
                return False
        return True

    def _invoke(self, role: ModelRole, node: WorkflowNode, instructions: str, context: dict[str, Any]) -> dict[str, Any]:
        result = self._router.invoke(ModelRequest(role, node, instructions, context))
        value = getattr(result, "value", None)
        if type(value) is not dict:
            raise DiscoveryError("model returned malformed structured data")
        return value

    def _run(self, run_id: str, node: WorkflowNode, argv: tuple[str, ...], artifact_name: str) -> Any:
        return self._runner.run(run_id, node, argv, artifact_name)

    @staticmethod
    def _payload(result: Any) -> dict[str, Any]:
        payload = getattr(result, "payload", None)
        if type(payload) is not dict:
            raise DiscoveryError("command returned malformed payload")
        return payload

    @staticmethod
    def _body(payload: dict[str, Any]) -> dict[str, Any]:
        response = payload.get("response")
        if type(response) is not dict or type(response.get("body")) is not dict:
            raise DiscoveryError("command response body must be an object")
        return response["body"]

    @staticmethod
    def _body_list(payload: dict[str, Any], label: str) -> list[dict[str, Any]]:
        response = payload.get("response")
        body = response.get("body") if type(response) is dict else None
        if type(body) is not list or any(type(item) is not dict for item in body):
            raise DiscoveryError(f"{label} response body must be a list of objects")
        try:
            return deepcopy(body)
        except (TypeError, RecursionError):
            raise DiscoveryError(f"{label} response body cannot be snapshotted") from None

    @staticmethod
    def _status(payload: dict[str, Any]) -> int:
        response = payload.get("response")
        if type(response) is not dict or type(response.get("status_code")) is not int:
            return 0
        return response["status_code"]

    @staticmethod
    def _authenticated(body: dict[str, Any]) -> bool:
        if body.get("authenticated") is True or body.get("is_authenticated") is True:
            return True
        user = body.get("user")
        token = body.get("token")
        expiry = token.get("expiry") if type(token) is dict else None
        return (
            type(user) is dict
            and type(user.get("id")) is str
            and bool(user["id"].strip())
            and type(expiry) in {int, float}
            and not isinstance(expiry, bool)
            and isfinite(expiry)
            and expiry > 0
        )

    @staticmethod
    def _records(body: dict[str, Any]) -> list[dict[str, Any]]:
        for key in ("results", "alphas", "pyramidAlphas", "pyramids", "items"):
            values = body.get(key)
            if type(values) is list and all(type(value) is dict for value in values):
                return values
        return []

    @staticmethod
    def _as_eastern(value: datetime) -> datetime:
        if not isinstance(value, datetime):
            raise TypeError("clock must return a datetime")
        if value.tzinfo is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return value.astimezone(EASTERN)

    @staticmethod
    def _clock(clock: Callable[[], datetime] | None) -> datetime:
        return datetime.now(timezone.utc) if clock is None else clock()

    @staticmethod
    def _quarter_bounds(body: dict[str, Any]) -> tuple[str, str]:
        try:
            performance = body["performance"]
            quarter = performance.get("currentQuarter")
            if type(quarter) is not dict:
                quarter = performance["current"]["quarter"]
            start, end = quarter["startDate"], quarter["endDate"]
        except (KeyError, TypeError):
            raise DiscoveryError("consultant summary lacks current quarter dates") from None
        if type(start) is not str or type(end) is not str or not start or not end:
            raise DiscoveryError("current quarter dates are invalid")
        return start, end

    @staticmethod
    def _snapshot_mapping(value: Mapping[str, Any], name: str) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            raise TypeError(f"{name} must be a mapping")
        return dict(value)

    @staticmethod
    def _artifact_ids(*results: Any) -> tuple[str, ...]:
        identifiers: list[str] = []
        for result in results:
            artifact = getattr(result, "artifact", None)
            identifier = getattr(artifact, "id", None)
            if type(identifier) is int and identifier > 0:
                identifiers.append(str(identifier))
        return tuple(identifiers)

    def _write_json(self, run_id: str, node: WorkflowNode, name: str, value: dict[str, Any]) -> tuple[str, ...]:
        writer = self._artifacts
        if not callable(getattr(writer, "write_json", None)):
            return ()
        artifact = writer.write_json(run_id, node, name, value)
        identifier = getattr(artifact, "id", None)
        return (str(identifier),) if type(identifier) is int and identifier > 0 else ()

    def _write_markdown(self, run_id: str, node: WorkflowNode, name: str, value: str) -> tuple[str, ...]:
        writer = self._artifacts
        if not callable(getattr(writer, "write_markdown", None)):
            return ()
        artifact = writer.write_markdown(run_id, node, name, value)
        identifier = getattr(artifact, "id", None)
        return (str(identifier),) if type(identifier) is int and identifier > 0 else ()
