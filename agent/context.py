from __future__ import annotations

import re
from math import isfinite
from typing import Any, Callable

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

MAX_CONTEXT_DEPTH = 64
MAX_CONTEXT_NODES = 10_000
MAX_CONTEXT_CHARS = 250_000
MAX_CONTEXT_INTEGER_BITS = 4_096
MAX_EVIDENCE_REFS = 100
_MISSING = object()


class ContextError(ValueError):
    """Raised when safe role-specific context cannot be constructed."""


class _SnapshotBudget:
    def __init__(self) -> None:
        self.nodes = 0
        self.characters = 0

    def consume_node(self) -> None:
        self.nodes += 1
        if self.nodes > MAX_CONTEXT_NODES:
            raise ContextError("context input exceeds the JSON node limit")

    def consume_characters(self, count: int) -> None:
        self.characters += count
        if self.characters > MAX_CONTEXT_CHARS:
            raise ContextError("context input exceeds the JSON character limit")


class ContextBuilder:
    def __init__(self, resolve_artifact: Callable[[str], Any]) -> None:
        if not callable(resolve_artifact):
            raise TypeError("resolve_artifact must be callable")
        self._resolve_artifact = resolve_artifact

    def for_planner(
        self,
        *,
        run_config: Any,
        current_plan: Any,
        metrics: Any,
        evidence_refs: Any = None,
        route_history: Any = None,
        experience_summaries: Any = None,
    ) -> dict[str, Any]:
        budget = _SnapshotBudget()
        config_snapshot = _safe_snapshot(run_config, budget)
        plan_snapshot = _safe_snapshot(current_plan, budget)
        metrics_snapshot = _safe_snapshot(metrics, budget)
        route_snapshot = _safe_snapshot(
            [] if route_history is None else route_history, budget
        )
        experience_snapshot = _safe_snapshot(
            [] if experience_summaries is None else experience_summaries,
            budget,
        )

        if type(config_snapshot) is not dict:
            raise ContextError("run_config must be a JSON object")
        if type(plan_snapshot) is not dict:
            raise ContextError("current_plan must be a JSON object")
        plan_snapshot, plan_id, plan_version, plan_hash = _canonical_planner_plan(
            plan_snapshot
        )
        if type(metrics_snapshot) is not dict:
            raise ContextError("metrics must be a JSON object")
        if type(route_snapshot) is not list:
            raise ContextError("route_history must be a JSON array")
        experience_ids = _validate_experiences(experience_snapshot)
        artifact_ids, artifacts = self._resolve_artifacts(
            [] if evidence_refs is None else evidence_refs,
            budget,
        )

        return {
            "run_config": config_snapshot,
            "current_plan": plan_snapshot,
            "metrics": metrics_snapshot,
            "evidence": {
                "classification": "untrusted_data",
                "artifacts": artifacts,
            },
            "route_history": route_snapshot,
            "experience_summaries": experience_snapshot,
            "context_manifest": {
                "plan_id": plan_id,
                "plan_version": plan_version,
                **({"plan_hash": plan_hash} if plan_hash is not None else {}),
                "artifact_ids": artifact_ids,
                "experience_ids": experience_ids,
            },
        }

    def for_operator(
        self,
        *,
        task: Any,
        plan: Any,
        evidence_refs: Any = None,
        required_fields: Any = None,
        required_operators: Any = None,
        output_schema: Any = None,
    ) -> dict[str, Any]:
        budget = _SnapshotBudget()
        plan_snapshot = _safe_snapshot(plan, budget)
        task_snapshot = _safe_snapshot(task, budget)
        if type(plan_snapshot) is not dict:
            raise ContextError("plan must be a JSON object")
        plan_version, plan_hash = _required_plan_lock(plan_snapshot)
        plan_id = _optional_identifier(
            _coalesce_alias(plan_snapshot, "id", "plan_id", "plan id"),
            "plan id",
        )

        task_id = _task_identifier(task_snapshot, "task selector")

        tasks = plan_snapshot.get("tasks")
        if type(tasks) is not list:
            raise ContextError("plan tasks must be a JSON array")
        normalized_tasks: list[tuple[str, dict[str, Any]]] = []
        for item in tasks:
            if type(item) is not dict:
                raise ContextError("plan tasks must be JSON objects")
            normalized_tasks.append((_task_identifier(item, "plan task"), item))
        matches = [item for identifier, item in normalized_tasks if identifier == task_id]
        if len(matches) != 1:
            raise ContextError("task id must identify exactly one plan task")
        selected = matches[0]
        instruction = _required_identifier(selected.get("instruction"), "task instruction")

        fields_snapshot = _validate_name_list(
            selected.get("required_fields", []), "required_fields"
        )
        operators_snapshot = _validate_name_list(
            selected.get("required_operators", []), "required_operators"
        )
        schema_snapshot = _validate_output_schema(selected.get("output_schema", {}))

        if required_fields is not None:
            declared_fields = _validate_name_list(
                _safe_snapshot(required_fields, budget), "required_fields"
            )
            if declared_fields != fields_snapshot:
                raise ContextError("required_fields must match the selected plan task")
        if required_operators is not None:
            declared_operators = _validate_name_list(
                _safe_snapshot(required_operators, budget), "required_operators"
            )
            if declared_operators != operators_snapshot:
                raise ContextError("required_operators must match the selected plan task")
        if output_schema is not None:
            declared_schema = _validate_output_schema(
                _safe_snapshot(output_schema, budget)
            )
            if declared_schema != schema_snapshot:
                raise ContextError("output_schema must match the selected plan task")

        artifact_ids, artifacts = self._resolve_artifacts(
            [] if evidence_refs is None else evidence_refs,
            budget,
        )
        return {
            "task": {"task_id": task_id, "instruction": instruction},
            "plan_lock": {"version": plan_version, "hash": plan_hash},
            "required_fields": fields_snapshot,
            "required_operators": operators_snapshot,
            "output_schema": schema_snapshot,
            "evidence": {
                "classification": "untrusted_data",
                "artifacts": artifacts,
            },
            "context_manifest": {
                "plan_id": plan_id,
                "plan_version": plan_version,
                "plan_hash": plan_hash,
                "task_id": task_id,
                "artifact_ids": artifact_ids,
            },
        }

    def _resolve_artifacts(
        self,
        refs: Any,
        budget: _SnapshotBudget,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        refs_snapshot = _safe_snapshot(refs, budget)
        if type(refs_snapshot) is not list:
            raise ContextError("evidence_refs must be a JSON array")
        if len(refs_snapshot) > MAX_EVIDENCE_REFS:
            raise ContextError("evidence_refs exceeds the reference limit")

        unique_refs: list[str] = []
        seen: set[str] = set()
        for ref in refs_snapshot:
            ref = _required_identifier(ref, "artifact reference")
            if ref not in seen:
                seen.add(ref)
                unique_refs.append(ref)

        artifacts: list[dict[str, Any]] = []
        for ref in unique_refs:
            try:
                resolved = self._resolve_artifact(ref)
            except Exception:
                raise ContextError("artifact resolution failed") from None
            artifact = _safe_snapshot(resolved, budget)
            if type(artifact) is not dict:
                raise ContextError("resolved artifact must be a JSON object")
            identity = _coalesce_alias(artifact, "id", "artifact_id", "artifact id")
            if identity != ref:
                raise ContextError("resolved artifact id does not match its reference")
            canonical = {
                key: value
                for key, value in artifact.items()
                if key not in {"id", "artifact_id"}
            }
            artifacts.append({"id": ref, **canonical})
        return list(unique_refs), artifacts


def _safe_snapshot(value: Any, budget: _SnapshotBudget | None = None) -> Any:
    if budget is None:
        budget = _SnapshotBudget()
    active: set[int] = set()

    def copy(item: Any, depth: int) -> Any:
        budget.consume_node()
        if depth > MAX_CONTEXT_DEPTH:
            raise ContextError("context input exceeds the JSON depth limit")

        if type(item) is dict:
            identity = id(item)
            if identity in active:
                raise ContextError("context input must not contain cycles")
            active.add(identity)
            result: dict[str, Any] = {}
            dynamic_secret = any(
                type(raw_key) is str
                and raw_key.strip().casefold() in {"key", "name", "type"}
                and type(raw_value) is str
                and _is_secret_key(raw_value)
                for raw_key, raw_value in item.items()
            )
            for key, child in item.items():
                if type(key) is not str:
                    raise ContextError("context object keys must be strings")
                budget.consume_characters(len(key))
                if _is_secret_key(key) or (
                    dynamic_secret and key.strip().casefold() == "value"
                ):
                    result[key] = "[REDACTED]"
                    continue
                result[key] = copy(child, depth + 1)
            active.remove(identity)
            return result
        if type(item) is list:
            identity = id(item)
            if identity in active:
                raise ContextError("context input must not contain cycles")
            active.add(identity)
            result = [copy(child, depth + 1) for child in item]
            active.remove(identity)
            return result
        if item is None or type(item) is bool:
            return item
        if type(item) is int:
            if item.bit_length() > MAX_CONTEXT_INTEGER_BITS:
                raise ContextError("context integer exceeds the bit-length limit")
            return item
        if type(item) is float:
            if not isfinite(item):
                raise ContextError("context numbers must be finite")
            return item
        if type(item) is str:
            budget.consume_characters(len(item))
            return item
        raise ContextError("context input must contain only JSON-native values")

    return copy(value, 0)


def _is_secret_key(key: str) -> bool:
    camel_split = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", key)
    camel_split = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", camel_split)
    segments = [
        part.casefold()
        for part in re.split(r"[^A-Za-z0-9]+", camel_split)
        if part
    ]
    compact = "".join(segments)
    if compact in {
        "apikey",
        "auth",
        "authorization",
        "basicauth",
        "cookie",
        "oauthcredentials",
        "passwd",
        "password",
        "privatekey",
        "pwd",
        "sessionid",
        "signingkey",
    }:
        return True
    if compact == "cookies" or compact.endswith(
        ("apikey", "cookie", "password", "secret", "token")
    ):
        return True
    if any(segment in {"authorization", "passwd", "password", "pwd", "secret"} for segment in segments):
        return True
    if (
        len(segments) >= 2
        and segments[0] == "token"
        and segments[1] in {"credential", "credentials", "key", "secret", "value"}
    ):
        return True
    credential_pairs = {
        ("access", "key"),
        ("api", "key"),
        ("auth", "cookie"),
        ("auth", "header"),
        ("basic", "auth"),
        ("client", "key"),
        ("cookie", "header"),
        ("csrf", "cookie"),
        ("csrf", "header"),
        ("oauth", "credentials"),
        ("private", "key"),
        ("session", "cookie"),
        ("session", "id"),
        ("signing", "key"),
    }
    return any(pair in credential_pairs for pair in zip(segments, segments[1:]))


def _required_identifier(value: Any, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise ContextError(f"{label} must be a nonblank string")
    return value


def _validate_name_list(value: Any, label: str) -> list[str]:
    if type(value) is not list:
        raise ContextError(f"{label} must be a JSON array")
    if any(type(item) is not str or not item.strip() for item in value):
        raise ContextError(f"{label} must contain only nonblank strings")
    if len(set(value)) != len(value):
        raise ContextError(f"{label} values must be unique")
    return list(value)


def _validate_output_schema(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise ContextError("output_schema must be a JSON object")
    try:
        Draft202012Validator.check_schema(value)
    except SchemaError:
        raise ContextError("output_schema must be a valid JSON Schema") from None
    return value


def _task_identifier(value: Any, label: str) -> str:
    if type(value) is str:
        return _required_identifier(value, f"{label} id")
    if type(value) is not dict:
        raise ContextError(f"{label} must be a task id or JSON object")

    legacy_present = "id" in value
    canonical_present = "task_id" in value
    if not legacy_present and not canonical_present:
        raise ContextError(f"{label} must contain task_id")
    legacy = _required_identifier(value.get("id"), f"{label} id") if legacy_present else None
    canonical = (
        _required_identifier(value.get("task_id"), f"{label} task_id")
        if canonical_present
        else None
    )
    if legacy is not None and canonical is not None and legacy != canonical:
        raise ContextError(f"{label} id and task_id must match")
    if canonical is not None:
        return canonical
    if legacy is not None:
        return legacy
    raise ContextError(f"{label} must contain task_id")


def _optional_identifier(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _required_identifier(value, label)


def _required_plan_lock(plan: dict[str, Any]) -> tuple[int, str]:
    version = _coalesce_alias(plan, "version", "plan_version", "plan version")
    plan_hash = _coalesce_alias(plan, "hash", "plan_hash", "plan hash")
    if type(version) is not int or version <= 0:
        raise ContextError("plan version must be a positive integer")
    if type(plan_hash) is not str or not plan_hash.strip():
        raise ContextError("plan hash must be a nonblank string")
    return version, plan_hash


def _canonical_planner_plan(
    plan: dict[str, Any],
) -> tuple[dict[str, Any], str | None, int | None, str | None]:
    plan_id = _optional_identifier(
        _coalesce_alias(plan, "id", "plan_id", "plan id"), "plan id"
    )
    version = _coalesce_alias(plan, "version", "plan_version", "plan version")
    plan_hash = _coalesce_alias(plan, "hash", "plan_hash", "plan hash")
    if version is not None and (type(version) is not int or version <= 0):
        raise ContextError("plan version must be a positive integer or null")
    if plan_hash is not None and (
        type(plan_hash) is not str or not plan_hash.strip()
    ):
        raise ContextError("plan hash must be a nonblank string or null")

    aliases = {"id", "plan_id", "version", "plan_version", "hash", "plan_hash"}
    canonical = {key: value for key, value in plan.items() if key not in aliases}
    if plan_id is not None:
        canonical["id"] = plan_id
    if version is not None:
        canonical["version"] = version
    if plan_hash is not None:
        canonical["hash"] = plan_hash
    return canonical, plan_id, version, plan_hash


def _coalesce_alias(
    values: dict[str, Any],
    primary_key: str,
    alias_key: str,
    label: str,
) -> Any:
    primary = values.get(primary_key, _MISSING)
    alias = values.get(alias_key, _MISSING)
    if primary is _MISSING:
        return None if alias is _MISSING else alias
    if alias is _MISSING:
        return primary
    if type(primary) is not type(alias) or primary != alias:
        raise ContextError(f"{label} aliases must match")
    return primary


def _validate_experiences(value: Any) -> list[str]:
    if type(value) is not list:
        raise ContextError("experience_summaries must be a JSON array")
    identifiers: list[str] = []
    seen: set[str] = set()
    for item in value:
        if type(item) is not dict:
            raise ContextError("experience summaries must be JSON objects")
        identifier = _required_identifier(item.get("id"), "experience id")
        if identifier in seen:
            raise ContextError("experience ids must be unique")
        seen.add(identifier)
        identifiers.append(identifier)
    return identifiers
