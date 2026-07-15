from __future__ import annotations

import json
from copy import deepcopy
from math import isfinite
from typing import Any

from jsonschema import Draft202012Validator

from .types import ModelRole, WorkflowNode


class ModelRefusal(RuntimeError):
    pass


class SchemaViolation(ValueError):
    pass


MAX_SCHEMA_REPAIR_RETRIES = 2


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


def validate_model_output(
    role: ModelRole, node: WorkflowNode, value: object
) -> dict[str, Any]:
    schema = schema_for(role, node)
    if type(value) is not dict:
        raise TypeError("value must be a dict")
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: (list(error.absolute_path), error.message),
    )
    if errors:
        details = []
        for error in errors:
            path = ".".join(str(part) for part in error.absolute_path) or "$"
            details.append(f"{path}: {error.message}")
        raise SchemaViolation("; ".join(details))

    if not isfinite(value["confidence"]):
        raise SchemaViolation("confidence: must be a finite number")

    result = value
    if role is ModelRole.PLANNER and node is WorkflowNode.K:
        diagnosis = result["diagnosis"]
        expected = DIAGNOSIS_ROUTES[diagnosis["failure_class"]]
        if diagnosis["next_node"] != expected:
            raise SchemaViolation(
                "diagnosis.next_node: "
                f"{diagnosis['failure_class']} must route to {expected}"
            )
    return result
