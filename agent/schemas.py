from __future__ import annotations

import json
import re
from copy import deepcopy
from math import isfinite
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from .types import ModelRole, WorkflowNode


class ModelRefusal(RuntimeError):
    pass


class SchemaViolation(ValueError):
    pass


MAX_SCHEMA_REPAIR_RETRIES = 2

_MAX_VALIDATION_ERRORS = 8
_MAX_VALIDATION_ERROR_LENGTH = 1024
_MAX_ERROR_FIELD_NAMES = 8
_MAX_ERROR_FIELD_NAME_LENGTH = 64


BASE_PROPERTIES: dict[str, dict[str, Any]] = {
    "decision": {"type": "string", "minLength": 1, "pattern": r"\S"},
    "reasoning_summary": {
        "type": "string",
        "minLength": 1,
        "pattern": r"\S",
    },
    "evidence_refs": {
        "type": "array",
        "minItems": 1,
        "items": {"type": "string", "minLength": 1, "pattern": r"\S"},
    },
    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
}
BASE_REQUIRED = tuple(BASE_PROPERTIES)

DIAGNOSIS_ROUTES = {
    "DATA_FIELD": "F",
    "EVIDENCE_GAP": "G",
    "ECONOMIC_MECHANISM": "H",
    "EXPRESSION": "I",
    "PASS": "L",
}

_OBJECT_PAYLOAD = {"type": "object"}
_TASK_RESULT = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "minLength": 1, "pattern": r"\S"},
        "payload": {"type": "object"},
    },
    "required": ["status", "payload"],
    "additionalProperties": False,
}
_DIAGNOSIS = {
    "type": "object",
    "properties": {
        "failure_class": {"type": "string", "enum": list(DIAGNOSIS_ROUTES)},
        "next_node": {"type": "string", "enum": list(DIAGNOSIS_ROUTES.values())},
    },
    "required": ["failure_class", "next_node"],
    "additionalProperties": False,
}

_PLANNER_PAYLOADS: dict[WorkflowNode, tuple[str, dict[str, Any]]] = {
    WorkflowNode.D: ("scope_decision", _OBJECT_PAYLOAD),
    WorkflowNode.F: ("evidence_requirements", _OBJECT_PAYLOAD),
    WorkflowNode.G: ("evidence_requirements", _OBJECT_PAYLOAD),
    WorkflowNode.H: ("research_plan", _OBJECT_PAYLOAD),
    WorkflowNode.I: ("candidate_plan", _OBJECT_PAYLOAD),
    WorkflowNode.K: ("diagnosis", _DIAGNOSIS),
    WorkflowNode.L: ("final_recommendation", _OBJECT_PAYLOAD),
}

_SUPPORTED_NODES = {
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


def has_open_object_schema(schema: object) -> bool:
    """Return whether any object node permits unspecified properties.

    This is a narrow routing signal, not a complete provider compatibility check.
    """

    visited: set[int] = set()

    def visit(value: object) -> bool:
        if type(value) is dict:
            identity = id(value)
            if identity in visited:
                return False
            visited.add(identity)
            schema_type = value.get("type")
            declares_object = schema_type == "object" or (
                type(schema_type) is list and "object" in schema_type
            )
            if declares_object and value.get("additionalProperties") is not False:
                return True
            return any(visit(child) for child in value.values())
        if type(value) is list:
            identity = id(value)
            if identity in visited:
                return False
            visited.add(identity)
            return any(visit(child) for child in value)
        return False

    return visit(schema)


def parse_json_text(text: str, *, refusal: str | None = None) -> dict[str, Any]:
    if type(text) is not str:
        raise TypeError("text must be a string")
    if refusal is not None:
        if type(refusal) is not str:
            raise TypeError("refusal must be a string or None")
        raise ModelRefusal(refusal or "model refused to provide a response")

    def reject_constant(value: str) -> None:
        raise ValueError(f"invalid JSON constant: {value}")

    try:
        value = json.loads(text, parse_constant=reject_constant)
    except (json.JSONDecodeError, ValueError) as error:
        raise SchemaViolation("model output is not valid JSON") from error
    if type(value) is not dict:
        raise SchemaViolation("model output must be a JSON object")
    return value


def schema_for(role: ModelRole, node: WorkflowNode) -> dict[str, Any]:
    if type(role) is not ModelRole:
        raise TypeError("role must be a ModelRole")
    if type(node) is not WorkflowNode:
        raise TypeError("node must be a WorkflowNode")
    if node not in _SUPPORTED_NODES[role]:
        raise SchemaViolation(
            "unsupported model role/node combination: "
            f"role={role.value}, node={node.value}"
        )
    properties = deepcopy(BASE_PROPERTIES)
    required = list(BASE_REQUIRED)
    if role is ModelRole.OPERATOR:
        payload_name, payload_schema = "task_result", _TASK_RESULT
    elif node in _PLANNER_PAYLOADS:
        payload_name, payload_schema = _PLANNER_PAYLOADS[node]
    else:
        payload_name = ""
        payload_schema = {}
    if payload_name:
        properties[payload_name] = deepcopy(payload_schema)
        required.append(payload_name)
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _validate_json_native(value: object, path: str, active: set[int]) -> None:
    value_type = type(value)
    if value is None or value_type in {str, bool, int}:
        return
    if value_type is float:
        if not isfinite(value):
            raise SchemaViolation(f"{path}: number must be finite")
        return
    if value_type is dict:
        identity = id(value)
        if identity in active:
            raise SchemaViolation(f"{path}: circular JSON container")
        active.add(identity)
        try:
            for key, child in value.items():
                if type(key) is not str:
                    raise SchemaViolation(f"{path}: object keys must be strings")
                _validate_json_native(child, f"{path}.{key}", active)
        finally:
            active.remove(identity)
        return
    if value_type is list:
        identity = id(value)
        if identity in active:
            raise SchemaViolation(f"{path}: circular JSON container")
        active.add(identity)
        try:
            for index, child in enumerate(value):
                _validate_json_native(child, f"{path}[{index}]", active)
        finally:
            active.remove(identity)
        return
    raise SchemaViolation(f"{path}: value is not JSON-native")


def _safe_field_name(value: str) -> str:
    sanitized = "".join(
        character if character.isalnum() or character in "_.-" else "?"
        for character in value
    )
    if len(sanitized) > _MAX_ERROR_FIELD_NAME_LENGTH:
        return sanitized[: _MAX_ERROR_FIELD_NAME_LENGTH - 3] + "..."
    return sanitized


def _validation_path(error: ValidationError) -> str:
    path = "$"
    for part in error.absolute_path:
        if type(part) is int:
            path += f"[{part}]"
        else:
            path += "." + _safe_field_name(part)
    return path


def _unexpected_property_names(error: ValidationError) -> list[str]:
    properties = set(error.schema.get("properties", {}))
    patterns = tuple(error.schema.get("patternProperties", {}))
    return sorted(
        key
        for key in error.instance
        if key not in properties
        and not any(re.search(pattern, key) for pattern in patterns)
    )


def _limited_field_list(names: list[str]) -> str:
    shown = [_safe_field_name(name) for name in names[:_MAX_ERROR_FIELD_NAMES]]
    if len(names) > len(shown):
        shown.append("...")
    return ", ".join(shown)


def _format_validation_error(error: ValidationError) -> str:
    path = _validation_path(error)
    if error.validator == "required":
        missing = [
            name for name in error.validator_value if name not in error.instance
        ]
        return f"{path}: missing required properties: {_limited_field_list(missing)}"
    if error.validator == "additionalProperties":
        unexpected = _unexpected_property_names(error)
        return f"{path}: unexpected properties: {_limited_field_list(unexpected)}"
    validator = _safe_field_name(str(error.validator))
    return f"{path}: failed {validator} validation"


def validate_model_output(
    role: ModelRole, node: WorkflowNode, value: object
) -> dict[str, Any]:
    schema = schema_for(role, node)
    if type(value) is not dict:
        raise SchemaViolation("$: model output must be an exact JSON object")
    _validate_json_native(value, "$", set())
    snapshot: dict[str, Any] = deepcopy(value)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(snapshot),
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            str(error.validator),
        ),
    )
    if errors:
        details = [
            _format_validation_error(error)
            for error in errors[:_MAX_VALIDATION_ERRORS]
        ]
        if len(errors) > len(details):
            details.append("additional validation errors omitted")
        raise SchemaViolation("; ".join(details)[:_MAX_VALIDATION_ERROR_LENGTH])

    if not isfinite(snapshot["confidence"]):
        raise SchemaViolation("confidence: must be a finite number")

    result = snapshot
    if role is ModelRole.PLANNER and node is WorkflowNode.K:
        diagnosis = result["diagnosis"]
        expected = DIAGNOSIS_ROUTES[diagnosis["failure_class"]]
        if diagnosis["next_node"] != expected:
            raise SchemaViolation(
                "diagnosis.next_node: "
                f"{diagnosis['failure_class']} must route to {expected}"
            )
    return result
