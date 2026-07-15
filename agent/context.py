from __future__ import annotations

import re
from math import isfinite
from typing import Any, Callable

from .policy import OPERATOR_CONTROL_KEYS


_MAX_JSON_DEPTH = 64
_MAX_JSON_NODES = 10_000
_MAX_JSON_STRING_LENGTH = 1_000_000


class ContextError(ValueError):
    """Raised when safe role-specific context cannot be constructed."""


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
        config_snapshot = _safe_snapshot(run_config)
        plan_snapshot = _safe_snapshot(current_plan)
        metrics_snapshot = _safe_snapshot(metrics)
        route_snapshot = _safe_snapshot([] if route_history is None else route_history)
        experience_snapshot = _safe_snapshot(
            [] if experience_summaries is None else experience_summaries
        )

        if type(config_snapshot) is not dict:
            raise ContextError("run_config must be a JSON object")
        if type(plan_snapshot) is not dict:
            raise ContextError("current_plan must be a JSON object")
        if type(metrics_snapshot) is not dict:
            raise ContextError("metrics must be a JSON object")
        if type(route_snapshot) is not list:
            raise ContextError("route_history must be a JSON array")
        experience_ids = _validate_experiences(experience_snapshot)
        artifact_ids, artifacts = self._resolve_artifacts(
            [] if evidence_refs is None else evidence_refs
        )

        plan_id = _optional_identifier(plan_snapshot.get("id"), "plan id")
        plan_version = plan_snapshot.get("version", plan_snapshot.get("plan_version"))
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
        plan_snapshot = _safe_snapshot(plan)
        task_snapshot = _safe_snapshot(task)
        if type(plan_snapshot) is not dict:
            raise ContextError("plan must be a JSON object")

        task_id = task_snapshot if type(task_snapshot) is str else None
        if type(task_snapshot) is dict:
            task_id = task_snapshot.get("id")
        task_id = _required_identifier(task_id, "task id")

        tasks = plan_snapshot.get("tasks")
        if type(tasks) is not list:
            raise ContextError("plan tasks must be a JSON array")
        matches = [
            item
            for item in tasks
            if type(item) is dict and item.get("id") == task_id
        ]
        if len(matches) != 1:
            raise ContextError("task id must identify exactly one plan task")
        selected = matches[0]

        fields_value = selected.get("required_fields", []) if required_fields is None else required_fields
        operators_value = (
            selected.get("required_operators", [])
            if required_operators is None
            else required_operators
        )
        schema_value = selected.get("output_schema", {}) if output_schema is None else output_schema
        fields_snapshot = _safe_snapshot(fields_value)
        operators_snapshot = _safe_snapshot(operators_value)
        schema_snapshot = _safe_snapshot(schema_value)
        if type(fields_snapshot) is not list:
            raise ContextError("required_fields must be a JSON array")
        if type(operators_snapshot) is not list:
            raise ContextError("required_operators must be a JSON array")

        artifact_ids, artifacts = self._resolve_artifacts(
            [] if evidence_refs is None else evidence_refs
        )
        plan_id = _optional_identifier(plan_snapshot.get("id"), "plan id")
        plan_version = plan_snapshot.get("version", plan_snapshot.get("plan_version"))
        plan_hash = plan_snapshot.get("hash", plan_snapshot.get("plan_hash"))
        if plan_hash is not None and (type(plan_hash) is not str or not plan_hash.strip()):
            raise ContextError("plan hash must be a nonblank string or null")

        return {
            "task": _drop_operator_controls(selected),
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

    def _resolve_artifacts(self, refs: Any) -> tuple[list[str], list[dict[str, Any]]]:
        refs_snapshot = _safe_snapshot(refs)
        if type(refs_snapshot) is not list:
            raise ContextError("evidence_refs must be a JSON array")

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
            artifact = _safe_snapshot(resolved)
            if type(artifact) is not dict or artifact.get("id") != ref:
                raise ContextError("resolved artifact id does not match its reference")
            artifacts.append(artifact)
        return list(unique_refs), artifacts


def _safe_snapshot(value: Any) -> Any:
    active: set[int] = set()
    nodes_seen = 0

    def copy(item: Any, depth: int) -> Any:
        nonlocal nodes_seen
        nodes_seen += 1
        if nodes_seen > _MAX_JSON_NODES:
            raise ContextError("context input exceeds the JSON size limit")
        if depth > _MAX_JSON_DEPTH:
            raise ContextError("context input exceeds the JSON depth limit")

        if type(item) is dict:
            identity = id(item)
            if identity in active:
                raise ContextError("context input must not contain cycles")
            active.add(identity)
            result: dict[str, Any] = {}
            for key, child in item.items():
                if type(key) is not str:
                    raise ContextError("context object keys must be strings")
                if len(key) > _MAX_JSON_STRING_LENGTH:
                    raise ContextError("context input exceeds the JSON string limit")
                copied_child = copy(child, depth + 1)
                result[key] = "[REDACTED]" if _is_secret_key(key) else copied_child
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
        if item is None or type(item) is bool or type(item) is int:
            return item
        if type(item) is float:
            if not isfinite(item):
                raise ContextError("context numbers must be finite")
            return item
        if type(item) is str:
            if len(item) > _MAX_JSON_STRING_LENGTH:
                raise ContextError("context input exceeds the JSON string limit")
            return item
        raise ContextError("context input must contain only JSON-native values")

    return copy(value, 0)


def _is_secret_key(key: str) -> bool:
    folded = key.casefold()
    compact = re.sub(r"[^a-z0-9]", "", folded)
    if any(marker in compact for marker in ("password", "apikey", "authorization", "cookie", "secret")):
        return True
    camel_split = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key)
    segments = [part.casefold() for part in re.split(r"[^A-Za-z0-9]+", camel_split) if part]
    return "token" in segments


def _drop_operator_controls(value: Any) -> Any:
    if type(value) is dict:
        return {
            key: _drop_operator_controls(child)
            for key, child in value.items()
            if key.strip().casefold() not in OPERATOR_CONTROL_KEYS
        }
    if type(value) is list:
        return [_drop_operator_controls(child) for child in value]
    return value


def _required_identifier(value: Any, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise ContextError(f"{label} must be a nonblank string")
    return value


def _optional_identifier(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _required_identifier(value, label)


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
