from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .budget import BalanceObservation, BudgetPolicy, CostObservation, CostProfile, estimate_plan_p95
from .experiment import compare_mechanism_arms, compare_pilot_outcomes
from .freeze import (
    ResearchFreeze,
    ResearchFreezeError,
    build_research_freeze_manifest,
    load_research_freeze,
    require_research_freeze,
)
from .execution import execute_wind_plan, load_executable_checks, summarize_wind_plan
from .models import EvidenceRecord
from .plan import RealityCheckSpec, assess_wind_reality_plan
from .provenance import canonical_json, utc_now_iso, verify_evidence_record
from .providers.wind import WIND_PROVIDER_NAME, WindRuntime
from .store import EvidenceStore


def default_store_root() -> Path:
    return Path(__file__).resolve().parents[1] / "local" / "evidence"


def _parse_json_source(inline: str | None, input_path: str | None) -> Any:
    if inline and input_path:
        raise ValueError("use only one of inline JSON and --input")
    if input_path:
        return json.loads(Path(input_path).read_text(encoding="utf-8-sig"))
    if inline:
        return json.loads(inline)
    return {}


def _parse_key_values(values: list[str] | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in values or ():
        if "=" not in item:
            raise ValueError(f"expected KEY=VALUE, got {item!r}")
        key, value = item.split("=", 1)
        if not key.strip():
            raise ValueError("KEY must be non-empty")
        result[key.strip()] = value
    return result


DEFAULT_CALIBRATION_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


def _age_seconds(timestamp: str) -> float:
    text = timestamp.replace("Z", "+00:00")
    observed = datetime.fromisoformat(text)
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - observed.astimezone(timezone.utc)).total_seconds())


def _profiles(
    store: EvidenceStore,
    *,
    max_age_seconds: int = DEFAULT_CALIBRATION_MAX_AGE_SECONDS,
) -> dict[str, CostProfile]:
    if max_age_seconds < 0:
        raise ValueError("calibration_max_age_seconds must be non-negative")
    observations = [
        item
        for item in store.load_costs(WIND_PROVIDER_NAME)
        if item.success and _age_seconds(item.timestamp) <= max_age_seconds
    ]
    names = sorted({item.query_type for item in observations})
    return {name: CostProfile.from_observations(name, observations) for name in names}


def _research_freeze_error_payload(exc: ResearchFreezeError) -> dict[str, Any]:
    message = str(exc)
    if "requires freeze manifest" in message or "requires a validated freeze manifest" in message:
        reason = "missing_research_freeze_manifest"
    elif "requires run_id" in message or "run_id mismatch" in message:
        reason = "research_freeze_run_mismatch"
    elif "absent from frozen baseline" in message:
        reason = "mechanism_not_frozen"
    else:
        reason = "invalid_research_freeze_manifest"
    return {"ok": False, "reason": reason, "message": message}


def _validated_research_freeze(
    payload: Mapping[str, Any],
    *,
    input_path: str,
    checks: Any,
) -> ResearchFreeze | None:
    mechanism_ids = sorted(
        {
            str(item.mechanism_id).strip()
            for item in checks
            if str(item.node).upper() in {"G", "H"} and str(item.mechanism_id).strip()
        }
    )
    if not mechanism_ids:
        return None
    run_id = str(payload.get("run_id") or "").strip()
    if not run_id:
        raise ResearchFreezeError("research plan requires run_id")
    raw_path = str(payload.get("freeze_manifest") or "").strip()
    if not raw_path:
        raise ResearchFreezeError("research plan requires freeze manifest")
    manifest_path = Path(raw_path).expanduser()
    if not manifest_path.is_absolute():
        manifest_path = Path(input_path).expanduser().resolve().parent / manifest_path
    freeze = load_research_freeze(manifest_path)
    return require_research_freeze(
        freeze,
        run_id=run_id,
        mechanism_ids=mechanism_ids,
    )


def _cost_profile_error(store: EvidenceStore, key: str) -> tuple[str, str]:
    has_historical = any(
        item.success and item.query_type == key for item in store.load_costs(WIND_PROVIDER_NAME)
    )
    if has_historical:
        return "stale_cost_profile", key
    return "missing_cost_profile", key


def _resolve_available_points(
    payload: Mapping[str, Any],
    store: EvidenceStore,
    *,
    allow_inline: bool = True,
) -> tuple[float, dict[str, Any]]:
    if payload.get("available_points") is not None and allow_inline:
        points = float(payload["available_points"])
        if not math.isfinite(points) or points < 0:
            raise ValueError("available_points must be non-negative")
        return points, {"source": "plan_inline", "available_points": points}

    observation = store.latest_balance(WIND_PROVIDER_NAME)
    if observation is None:
        raise ValueError("missing balance observation for wind")
    max_age = int(payload.get("balance_max_age_seconds", 1800))
    if max_age < 0:
        raise ValueError("balance_max_age_seconds must be non-negative")
    text = observation.observed_at.replace("Z", "+00:00")
    observed = datetime.fromisoformat(text)
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    age = max(0.0, (datetime.now(timezone.utc) - observed.astimezone(timezone.utc)).total_seconds())
    if age > max_age:
        raise ValueError(
            f"stale balance observation for wind: age_seconds={int(age)} > {max_age}"
        )
    return observation.available_points, {
        "source": observation.source,
        "available_points": observation.available_points,
        "observed_at": observation.observed_at,
        "age_seconds": int(age),
        "max_age_seconds": max_age,
    }


class EvidencePlugin:
    name = "evidence"

    def register(self, subparsers: Any) -> argparse.ArgumentParser:
        root = subparsers.add_parser(
            self.name,
            help="Capture, verify, budget, and replay external research evidence",
        )
        root.add_argument(
            "--store-root",
            default=str(default_store_root()),
            help="Evidence store root; default is wqb_cli/local/evidence",
        )
        sub = root.add_subparsers(dest="evidence_command", required=True)

        wind = sub.add_parser("wind", help="Wind evidence provider")
        wind_sub = wind.add_subparsers(dest="wind_command", required=True)

        status = wind_sub.add_parser("status", help="Check Wind Skill runtime and contract fingerprint")
        status.add_argument("--skill-dir")

        call = wind_sub.add_parser(
            "call",
            help="Legacy raw-call entrypoint; workflow calls are blocked and must use execute-plan",
        )
        call.add_argument("node", help="Workflow node standing, normally G, H, or K")
        call.add_argument("purpose", help="research/reality_check/clarification/diagnosis")
        call.add_argument("server_type")
        call.add_argument("tool_name")
        call.add_argument("--params", help="Inline UTF-8 JSON object")
        call.add_argument("--input", help="UTF-8 JSON parameter file")
        call.add_argument("--skill-dir")
        call.add_argument("--run-id", help="Lock the Wind provider contract for this WQB run")
        call.add_argument("--entity", action="append", help="Entity identifier KEY=VALUE")
        call.add_argument("--as-of")
        call.add_argument("--period", action="append", help="Period field KEY=VALUE")
        call.add_argument("--support", action="append", help="Mechanism/evidence claim id supported by this observation")
        call.add_argument("--limitation", action="append")
        call.add_argument("--raw-output", help="Optional raw Wind envelope path")
        call.add_argument("--output", help="Optional EvidenceRecord JSON path")

        plan = wind_sub.add_parser("plan-check", help="Validate bounded G/H/K reality-check plan against p95 cost profiles")
        plan.add_argument("--input", required=True, help="JSON file with checks[] and available_points")
        plan.add_argument("--output")

        execute = wind_sub.add_parser(
            "execute-plan",
            help="Execute an admitted Wind reality plan with a resumable no-blind-replay journal",
        )
        execute.add_argument("--input", required=True, help="JSON plan with run_id, available_points and executable checks[]")
        execute.add_argument("--skill-dir")
        execute.add_argument("--output")

        plan_status = wind_sub.add_parser(
            "plan-status",
            help="Read a plan journal without sending any Wind request",
        )
        plan_status.add_argument("--input", required=True, help="Same executable plan JSON used by execute-plan")
        plan_status.add_argument("--output")

        balance = sub.add_parser("balance", help="Record/read observed provider point balances")
        balance_sub = balance.add_subparsers(dest="balance_command", required=True)
        balance_add = balance_sub.add_parser("add", help="Record one authoritative balance observation")
        balance_add.add_argument("provider", choices=["wind"])
        balance_add.add_argument("--available-points", type=float, required=True)
        balance_add.add_argument("--source", default="alice_market_account")
        balance_add.add_argument("--observed-at")
        balance_add.add_argument("--output")
        balance_latest = balance_sub.add_parser("latest", help="Read the latest recorded balance observation")
        balance_latest.add_argument("provider", choices=["wind"])
        balance_latest.add_argument("--output")

        cost = sub.add_parser("cost", help="Wind point-cost calibration and budget gates")
        cost_sub = cost.add_subparsers(dest="cost_command", required=True)

        add = cost_sub.add_parser("add", help="Append one before/after point observation")
        add.add_argument("query_type")
        add.add_argument("--before", type=float, required=True)
        add.add_argument("--after", type=float, required=True)
        outcome = add.add_mutually_exclusive_group(required=True)
        outcome.add_argument("--success", action="store_true")
        outcome.add_argument("--failure", action="store_true")
        add.add_argument("--timestamp", default=None)
        add.add_argument("--output")

        profile = cost_sub.add_parser("profile", help="Build p50/p95 profiles from recorded successful calls")
        profile.add_argument("--query-type")
        profile.add_argument("--max-age-seconds", type=int, default=DEFAULT_CALIBRATION_MAX_AGE_SECONDS)
        profile.add_argument("--output")

        gate = cost_sub.add_parser("gate", help="Gate a query-count plan using p95 cost and current points")
        gate.add_argument("--available-points", type=float, required=True)
        gate.add_argument("--purpose", choices=["research", "diagnosis"], required=True)
        gate.add_argument("--plan", help='Inline JSON mapping, e.g. {"stock_data.get_stock_fundamentals":2}')
        gate.add_argument("--input", help="JSON mapping file")
        gate.add_argument("--output")

        experiment = sub.add_parser("experiment", help="Compare paired research arms")
        experiment_sub = experiment.add_subparsers(dest="experiment_command", required=True)
        freeze = experiment_sub.add_parser(
            "freeze",
            help="Freeze the paired research universe before any G/H Wind treatment",
        )
        freeze.add_argument("--run-id", required=True)
        freeze.add_argument("--main-tower", required=True)
        freeze.add_argument("--candidate-datafields", required=True)
        freeze.add_argument(
            "--mechanisms",
            required=True,
            help="Pre-Wind mechanism_families.json containing mechanism_id + field_ids",
        )
        freeze.add_argument("--run-constraints", required=True)
        freeze.add_argument(
            "--brain-field-snapshot",
            action="append",
            required=True,
            help="Frozen BRAIN field metadata snapshot; repeat for multiple files",
        )
        freeze.add_argument(
            "--non-wind-evidence",
            action="append",
            help="Pre-existing non-Wind evidence artifact to hash into the split",
        )
        freeze.add_argument("--output", required=True, help="Freeze manifest JSON path")

        freeze_verify = experiment_sub.add_parser(
            "freeze-verify",
            help="Recompute every freeze artifact hash and validate field/mechanism traceability",
        )
        freeze_verify.add_argument("--input", required=True)
        freeze_verify.add_argument("--output")

        compare = experiment_sub.add_parser("compare", help="Compare baseline H/I outputs with a Wind-enabled arm")
        compare.add_argument("--baseline-contracts", required=True)
        compare.add_argument("--wind-contracts", required=True)
        compare.add_argument("--baseline-candidates")
        compare.add_argument("--wind-candidates")
        compare.add_argument("--baseline-metrics", help="Optional JSON pilot metrics for the baseline J/K arm")
        compare.add_argument("--wind-metrics", help="Optional JSON pilot metrics for the Wind J/K arm")
        compare.add_argument("--output")

        verify = sub.add_parser("verify", help="Verify one persisted EvidenceRecord")
        verify.add_argument("path")
        verify.add_argument("--output")
        return root

    def handle(self, args: argparse.Namespace, context: Any) -> int:
        store = EvidenceStore(args.store_root)
        if args.evidence_command == "wind":
            return self._handle_wind(args, context, store)
        if args.evidence_command == "balance":
            if args.balance_command == "add":
                observation = BalanceObservation(
                    provider=args.provider,
                    available_points=args.available_points,
                    observed_at=args.observed_at or utc_now_iso(),
                    source=args.source,
                )
                path = store.append_balance(observation)
                context.write_json({"ok": True, "balance": observation.__dict__, "ledger_path": str(path)}, args.output)
                return 0
            if args.balance_command == "latest":
                observation = store.latest_balance(args.provider)
                if observation is None:
                    context.write_json({"ok": False, "reason": "no_balance_observation", "provider": args.provider}, args.output)
                    return 1
                context.write_json({"ok": True, "balance": observation.__dict__}, args.output)
                return 0
            raise AssertionError(args.balance_command)
        if args.evidence_command == "cost":
            return self._handle_cost(args, context, store)
        if args.evidence_command == "experiment":
            if args.experiment_command == "freeze":
                try:
                    manifest = build_research_freeze_manifest(
                        run_id=args.run_id,
                        main_tower_path=args.main_tower,
                        candidate_datafields_path=args.candidate_datafields,
                        mechanisms_path=args.mechanisms,
                        run_constraints_path=args.run_constraints,
                        brain_field_snapshots=args.brain_field_snapshot,
                        non_wind_evidence=args.non_wind_evidence or (),
                    )
                except ResearchFreezeError as exc:
                    context.write_json(_research_freeze_error_payload(exc))
                    return 1
                target = Path(args.output).expanduser().resolve()
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(canonical_json(manifest) + "\n", encoding="utf-8")
                try:
                    verified = load_research_freeze(target)
                except ResearchFreezeError as exc:
                    context.write_json(_research_freeze_error_payload(exc))
                    return 1
                context.write_json({"ok": True, "freeze": verified.to_dict()})
                return 0
            if args.experiment_command == "freeze-verify":
                try:
                    freeze = load_research_freeze(args.input)
                except ResearchFreezeError as exc:
                    context.write_json(_research_freeze_error_payload(exc), args.output)
                    return 1
                context.write_json({"ok": True, "freeze": freeze.to_dict()}, args.output)
                return 0
            if args.experiment_command != "compare":
                raise AssertionError(args.experiment_command)
            baseline_contracts = json.loads(Path(args.baseline_contracts).read_text(encoding="utf-8-sig"))
            wind_contracts = json.loads(Path(args.wind_contracts).read_text(encoding="utf-8-sig"))
            baseline_candidates = (
                json.loads(Path(args.baseline_candidates).read_text(encoding="utf-8-sig"))
                if args.baseline_candidates else None
            )
            wind_candidates = (
                json.loads(Path(args.wind_candidates).read_text(encoding="utf-8-sig"))
                if args.wind_candidates else None
            )
            report = compare_mechanism_arms(
                baseline_contracts,
                wind_contracts,
                baseline_candidates=baseline_candidates,
                wind_candidates=wind_candidates,
            )
            outcomes = None
            if bool(args.baseline_metrics) != bool(args.wind_metrics):
                raise ValueError("--baseline-metrics and --wind-metrics must be provided together")
            if args.baseline_metrics and args.wind_metrics:
                baseline_metrics = json.loads(Path(args.baseline_metrics).read_text(encoding="utf-8-sig"))
                wind_metrics = json.loads(Path(args.wind_metrics).read_text(encoding="utf-8-sig"))
                if not isinstance(baseline_metrics, Mapping) or not isinstance(wind_metrics, Mapping):
                    raise ValueError("pilot metrics files must contain JSON objects")
                outcomes = compare_pilot_outcomes(baseline_metrics, wind_metrics).to_dict()
            context.write_json(
                {"ok": not report.added_in_wind_arm, "impact": report.to_dict(), "outcomes": outcomes},
                args.output,
            )
            return 0 if not report.added_in_wind_arm else 2
        if args.evidence_command == "verify":
            payload = json.loads(Path(args.path).read_text(encoding="utf-8-sig"))
            record = EvidenceRecord.from_dict(payload)
            ok, problems = verify_evidence_record(record)
            context.write_json(
                {"ok": ok, "evidence_id": record.evidence_id, "problems": list(problems)},
                args.output,
            )
            return 0 if ok else 1
        raise AssertionError(args.evidence_command)

    def _handle_wind(self, args: argparse.Namespace, context: Any, store: EvidenceStore) -> int:
        if args.wind_command == "status":
            runtime = WindRuntime(skill_dir=args.skill_dir)
            status = runtime.status()
            context.write_json(status.__dict__)
            return 0 if status.available else 1

        if args.wind_command == "call":
            context.write_json(
                {
                    "ok": False,
                    "reason": "unplanned_wind_call_forbidden",
                    "message": (
                        "Workflow Wind calls must use plan-check + execute-plan so "
                        "freeze, calibration, balance, budget, provider lock, and replay "
                        "journal gates cannot be bypassed."
                    ),
                    "admitted_evidence": False,
                },
                args.output,
            )
            return 2

        if args.wind_command == "plan-status":
            payload = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
            if not isinstance(payload, Mapping):
                raise ValueError("executable Wind plan must be a JSON object")
            run_id = str(payload.get("run_id") or "").strip()
            if not run_id:
                raise ValueError("executable Wind plan requires run_id")
            checks = load_executable_checks(payload)
            try:
                research_freeze = _validated_research_freeze(
                    payload, input_path=args.input, checks=checks
                )
            except ResearchFreezeError as exc:
                context.write_json(_research_freeze_error_payload(exc), args.output)
                return 1
            result = summarize_wind_plan(
                store=store,
                run_id=run_id,
                checks=checks,
                research_freeze=research_freeze,
            )
            context.write_json(result, args.output)
            return 0 if result["ok"] else 2

        if args.wind_command == "execute-plan":
            payload = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
            if not isinstance(payload, Mapping):
                raise ValueError("executable Wind plan must be a JSON object")
            run_id = str(payload.get("run_id") or "").strip()
            if not run_id:
                raise ValueError("executable Wind plan requires run_id")
            checks = load_executable_checks(payload)
            try:
                research_freeze = _validated_research_freeze(
                    payload, input_path=args.input, checks=checks
                )
            except ResearchFreezeError as exc:
                context.write_json(_research_freeze_error_payload(exc), args.output)
                return 1
            runtime = WindRuntime(skill_dir=args.skill_dir)
            try:
                report = execute_wind_plan(
                    store=store,
                    run_id=run_id,
                    checks=checks,
                    available_points=_resolve_available_points(
                        payload, store, allow_inline=False
                    )[0],
                    profiles=_profiles(
                        store,
                        max_age_seconds=int(
                            payload.get("calibration_max_age_seconds", DEFAULT_CALIBRATION_MAX_AGE_SECONDS)
                        ),
                    ),
                    runtime=runtime,
                    research_freeze=research_freeze,
                )
            except KeyError as exc:
                missing = str(exc).strip("'").replace("missing cost profile for ", "")
                reason, query_type = _cost_profile_error(store, missing)
                context.write_json(
                    {"ok": False, "reason": reason, "query_type": query_type},
                    args.output,
                )
                return 1
            except ValueError as exc:
                message = str(exc)
                if "insufficient calibration" in message:
                    reason = "insufficient_calibration"
                elif "missing balance observation" in message:
                    reason = "missing_balance_observation"
                elif "stale balance observation" in message:
                    reason = "stale_balance_observation"
                else:
                    raise
                context.write_json({"ok": False, "reason": reason, "message": message}, args.output)
                return 1
            result = report.to_dict()
            for item in result.get("completed") or ():
                if isinstance(item, dict) and item.get("evidence_id"):
                    item["stored_path"] = str(
                        store.records_root
                        / WIND_PROVIDER_NAME
                        / f"{item['evidence_id']}.json"
                    )
            result["evidence_store_root"] = str(store.root)
            try:
                _, balance = _resolve_available_points(
                    payload, store, allow_inline=False
                )
            except ValueError:
                balance = None
            result["balance"] = balance
            context.write_json(result, args.output)
            return 0 if report.ok else 2

        if args.wind_command == "plan-check":
            payload = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
            if not isinstance(payload, Mapping):
                raise ValueError("Wind plan must be a JSON object")
            checks = [
                RealityCheckSpec(
                    mechanism_id=str(item["mechanism_id"]),
                    node=str(item["node"]),
                    purpose=str(item["purpose"]),
                    server_type=str(item["server_type"]),
                    tool_name=str(item["tool_name"]),
                    cost_profile_key=(
                        str(item["cost_profile_key"])
                        if item.get("cost_profile_key") is not None
                        else None
                    ),
                    allow_expensive_fallback=bool(item.get("allow_expensive_fallback", False)),
                    fallback_reason=(
                        str(item["fallback_reason"])
                        if item.get("fallback_reason") is not None
                        else None
                    ),
                )
                for item in payload.get("checks") or ()
            ]
            try:
                research_freeze = _validated_research_freeze(
                    payload, input_path=args.input, checks=checks
                )
            except ResearchFreezeError as exc:
                context.write_json(_research_freeze_error_payload(exc), args.output)
                return 1
            try:
                assessment = assess_wind_reality_plan(
                    checks,
                    profiles=_profiles(
                        store,
                        max_age_seconds=int(
                            payload.get("calibration_max_age_seconds", DEFAULT_CALIBRATION_MAX_AGE_SECONDS)
                        ),
                    ),
                    available_points=_resolve_available_points(payload, store)[0],
                )
            except KeyError as exc:
                missing = str(exc).strip("'").replace("missing cost profile for ", "")
                reason, query_type = _cost_profile_error(store, missing)
                context.write_json(
                    {"ok": False, "reason": reason, "query_type": query_type},
                    args.output,
                )
                return 1
            except ValueError as exc:
                message = str(exc)
                if "insufficient calibration" in message:
                    reason = "insufficient_calibration"
                elif "missing balance observation" in message:
                    reason = "missing_balance_observation"
                elif "stale balance observation" in message:
                    reason = "stale_balance_observation"
                else:
                    raise
                context.write_json({"ok": False, "reason": reason, "message": message}, args.output)
                return 1
            _, balance = _resolve_available_points(payload, store)
            output = {
                "ok": assessment.budget.allowed,
                "call_count": assessment.call_count,
                "mechanism_count": assessment.mechanism_count,
                "estimated_p95": assessment.estimated_p95,
                "query_counts": dict(assessment.query_counts),
                "budget": assessment.budget.__dict__,
                "balance": balance,
                "freeze": research_freeze.to_dict() if research_freeze is not None else None,
            }
            context.write_json(output, args.output)
            return 0 if assessment.budget.allowed else 2

        raise AssertionError(args.wind_command)

    def _handle_cost(self, args: argparse.Namespace, context: Any, store: EvidenceStore) -> int:
        if args.cost_command == "add":
            observation = CostObservation(
                query_type=args.query_type,
                points_before=args.before,
                points_after=args.after,
                success=bool(args.success),
                timestamp=args.timestamp or utc_now_iso(),
            )
            path = store.append_cost(WIND_PROVIDER_NAME, observation)
            context.write_json(
                {
                    "ok": True,
                    "query_type": observation.query_type,
                    "cost": observation.cost,
                    "success": observation.success,
                    "ledger_path": str(path),
                },
                args.output,
            )
            return 0

        if args.cost_command == "profile":
            profiles = _profiles(store, max_age_seconds=args.max_age_seconds)
            if args.query_type:
                profile = profiles.get(args.query_type)
                if profile is None:
                    context.write_json(
                        {"ok": False, "reason": "no_successful_calibration", "query_type": args.query_type},
                        args.output,
                    )
                    return 1
                result = {args.query_type: profile.__dict__}
            else:
                result = {name: profile.__dict__ for name, profile in profiles.items()}
            context.write_json(
                {"ok": True, "profiles": result, "max_age_seconds": args.max_age_seconds},
                args.output,
            )
            return 0

        if args.cost_command == "gate":
            plan = _parse_json_source(args.plan, args.input)
            if not isinstance(plan, Mapping):
                raise ValueError("budget plan must be a JSON mapping query_type -> count")
            profiles = _profiles(store)
            normalized = {str(key): int(value) for key, value in plan.items()}
            try:
                estimated = estimate_plan_p95(normalized, profiles)
            except KeyError as exc:
                missing = str(exc).strip("'").replace("missing cost profile for ", "")
                reason, query_type = _cost_profile_error(store, missing)
                context.write_json(
                    {"ok": False, "reason": reason, "query_type": query_type},
                    args.output,
                )
                return 1
            decision = BudgetPolicy().decide(
                available_points=args.available_points,
                estimated_p95=estimated,
                purpose=args.purpose,
            )
            context.write_json(
                {
                    "ok": decision.allowed,
                    "plan": normalized,
                    "decision": decision.__dict__,
                },
                args.output,
            )
            return 0 if decision.allowed else 2

        raise AssertionError(args.cost_command)


plugin = EvidencePlugin()

__all__ = ["EvidencePlugin", "default_store_root", "plugin"]
