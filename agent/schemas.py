from __future__ import annotations

import json
import re
from copy import deepcopy
from math import isfinite
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from .types import ModelRole, WorkflowNode


MAX_SCHEMA_VIOLATION_LENGTH = 1024
MAX_RESEARCH_IDEAS = 20


class ModelRefusal(RuntimeError):
    pass


class SchemaViolation(ValueError):
    def __init__(self, message: object) -> None:
        if type(message) is str:
            normalized = " ".join(message.split())
        else:
            normalized = "model output schema violation"
        if not normalized:
            normalized = "model output schema violation"
        super().__init__(normalized[:MAX_SCHEMA_VIOLATION_LENGTH])


MAX_SCHEMA_REPAIR_RETRIES = 2
MAX_JSON_NESTING = 64

_MAX_VALIDATION_ERRORS = 8
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
_NONBLANK_STRING = {"type": "string", "minLength": 1, "pattern": r"\S"}
_FIELD_ROLES = (
    "primary_signal",
    "confirmation",
    "condition",
    "grouping",
    "weighting",
    "normalization",
    "risk_control",
    "benchmark",
)
_FIELD_BINDING = {
    "type": "object",
    "properties": {
        "field_id": _NONBLANK_STRING,
        "role": {"type": "string", "enum": list(_FIELD_ROLES)},
        "rationale": {"type": "string", "minLength": 20, "pattern": r"\S"},
        "evidence_refs": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": _NONBLANK_STRING,
        },
    },
    "required": ["field_id", "role", "rationale", "evidence_refs"],
    "additionalProperties": False,
}
_SCOPE_DECISION = {
    "type": "object",
    "properties": {"candidate_id": _NONBLANK_STRING},
    "required": ["candidate_id"],
    "additionalProperties": False,
}
_RESEARCH_PLAN = {
    "type": "object",
    "properties": {
        "mechanisms": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_RESEARCH_IDEAS,
            "items": {
                "type": "object",
                "properties": {
                    "mechanism_id": _NONBLANK_STRING,
                    "tower_id": _NONBLANK_STRING,
                    "field_ids": {
                        "type": "array",
                        "minItems": 1,
                        "uniqueItems": True,
                        "items": _NONBLANK_STRING,
                    },
                    "field_bindings": {
                        "type": "array",
                        "minItems": 1,
                        "uniqueItems": True,
                        "items": _FIELD_BINDING,
                    },
                    "evidence_refs": {
                        "type": "array",
                        "minItems": 1,
                        "uniqueItems": True,
                        "items": _NONBLANK_STRING,
                    },
                    "hypothesis": {
                        "type": "string",
                        "minLength": 40,
                        "pattern": r"\S",
                    },
                },
                "required": [
                    "mechanism_id",
                    "tower_id",
                    "field_ids",
                    "field_bindings",
                    "evidence_refs",
                    "hypothesis",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["mechanisms"],
    "additionalProperties": False,
}
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
    WorkflowNode.D: ("scope_decision", _SCOPE_DECISION),
    WorkflowNode.F: ("evidence_requirements", _OBJECT_PAYLOAD),
    WorkflowNode.G: ("evidence_requirements", _OBJECT_PAYLOAD),
    WorkflowNode.H: ("research_plan", _RESEARCH_PLAN),
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

_SCHEMA_MAPPING_KEYWORDS = frozenset(
    {
        "$defs",
        "definitions",
        "dependentSchemas",
        "patternProperties",
        "properties",
    }
)
_SCHEMA_VALUE_KEYWORDS = frozenset(
    {
        "additionalProperties",
        "allOf",
        "anyOf",
        "contains",
        "contentSchema",
        "else",
        "if",
        "items",
        "not",
        "oneOf",
        "prefixItems",
        "propertyNames",
        "then",
        "unevaluatedItems",
        "unevaluatedProperties",
    }
)

_UNSUPPORTED_STRICT_OUTPUT_KEYWORDS = frozenset({"uniqueItems"})


def has_open_object_schema(schema: object) -> bool:
    """Return whether any object node permits unspecified properties.

    This is a narrow routing signal, not a complete provider compatibility check.
    """

    visited: set[int] = set()
    stack = [schema]
    while stack:
        current = stack.pop()
        if type(current) is not dict or id(current) in visited:
            continue
        visited.add(id(current))
        schema_type = current.get("type")
        declares_object = schema_type == "object" or (
            type(schema_type) is list and "object" in schema_type
        )
        if declares_object and current.get("additionalProperties") is not False:
            return True

        for keyword in _SCHEMA_MAPPING_KEYWORDS:
            children = current.get(keyword)
            if type(children) is dict:
                stack.extend(children.values())
        for keyword in _SCHEMA_VALUE_KEYWORDS:
            child = current.get(keyword)
            if type(child) is dict:
                stack.append(child)
            elif type(child) is list:
                stack.extend(child)
    return False


def has_unsupported_strict_output_schema(schema: object) -> bool:
    """Return whether the schema uses keywords rejected by provider strict mode."""

    visited: set[int] = set()
    stack = [schema]
    while stack:
        current = stack.pop()
        if type(current) is dict:
            identity = id(current)
            if identity in visited:
                continue
            visited.add(identity)
            if _UNSUPPORTED_STRICT_OUTPUT_KEYWORDS.intersection(current):
                return True
            stack.extend(current.values())
        elif type(current) is list:
            stack.extend(current)
    return False


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
    except (json.JSONDecodeError, ValueError, RecursionError, TypeError):
        raise SchemaViolation("model output is not valid JSON") from None
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


def _validate_json_native(value: object) -> None:
    active: set[int] = set()
    stack: list[tuple[object, int, bool]] = [(value, 0, False)]
    while stack:
        current, depth, exiting = stack.pop()
        current_type = type(current)
        if exiting:
            active.remove(id(current))
            continue
        if current is None or current_type in {str, bool, int}:
            continue
        if current_type is float:
            if not isfinite(current):
                raise SchemaViolation("model output contains a non-finite number")
            continue
        if current_type not in {dict, list}:
            raise SchemaViolation("model output contains a non-JSON-native value")
        if depth > MAX_JSON_NESTING:
            raise SchemaViolation("model output exceeds maximum JSON nesting")

        identity = id(current)
        if identity in active:
            raise SchemaViolation("model output contains a circular JSON container")
        active.add(identity)
        stack.append((current, depth, True))
        if current_type is dict:
            children: list[tuple[object, int, bool]] = []
            for key, child in current.items():
                if type(key) is not str:
                    raise SchemaViolation(
                        "model output contains a non-string object key"
                    )
                children.append((child, depth + 1, False))
            stack.extend(reversed(children))
        else:
            stack.extend(
                (child, depth + 1, False) for child in reversed(current)
            )


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
        label = "property" if len(unexpected) == 1 else "properties"
        return f"{path}: {len(unexpected)} unexpected {label}"
    validator = _safe_field_name(str(error.validator))
    return f"{path}: failed {validator} validation"


def validate_model_output(
    role: ModelRole, node: WorkflowNode, value: object
) -> dict[str, Any]:
    schema = schema_for(role, node)
    if type(value) is not dict:
        raise SchemaViolation("$: model output must be an exact JSON object")
    _validate_json_native(value)
    try:
        snapshot: dict[str, Any] = deepcopy(value)
    except (RecursionError, TypeError):
        raise SchemaViolation("model output snapshot could not be created") from None
    try:
        errors = sorted(
            Draft202012Validator(schema).iter_errors(snapshot),
            key=lambda error: (
                tuple(str(part) for part in error.absolute_path),
                str(error.validator),
            ),
        )
    except (RecursionError, TypeError):
        raise SchemaViolation("model output validation could not be completed") from None
    if errors:
        details = [
            _format_validation_error(error)
            for error in errors[:_MAX_VALIDATION_ERRORS]
        ]
        if len(errors) > len(details):
            details.append("additional validation errors omitted")
        raise SchemaViolation("; ".join(details))

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
