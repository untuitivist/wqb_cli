from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from math import isfinite
from time import perf_counter
from typing import Any, Protocol, runtime_checkable

import requests

from ..types import ModelRole, WorkflowNode


HTTP_TIMEOUT_SECONDS = 60
MAX_HTTP_RETRIES = 2


class ModelError(RuntimeError):
    """Base class for controlled model-provider failures."""


class ModelTransportError(ModelError):
    """A retryable provider or network failure exhausted its retry budget."""


class ModelResponseError(ModelError):
    """The provider returned a non-retryable or malformed response."""


@dataclass
class UsageAccumulator:
    input_tokens: int = 0
    output_tokens: int = 0
    input_complete: bool = True
    output_complete: bool = True
    observations: int = 0

    def add(self, input_tokens: int | None, output_tokens: int | None) -> None:
        self.observations += 1
        if input_tokens is None:
            self.input_complete = False
        else:
            self.input_tokens += input_tokens
        if output_tokens is None:
            self.output_complete = False
        else:
            self.output_tokens += output_tokens

    def values(self) -> tuple[int | None, int | None]:
        if self.observations == 0:
            return None, None
        return (
            self.input_tokens if self.input_complete else None,
            self.output_tokens if self.output_complete else None,
        )


def attach_failure_metadata(
    error: Exception,
    usage: UsageAccumulator,
    *,
    latency_ms: int,
    provider_request_id: str | None,
) -> Exception:
    input_tokens, output_tokens = usage.values()
    error.model_input_tokens = input_tokens  # type: ignore[attr-defined]
    error.model_output_tokens = output_tokens  # type: ignore[attr-defined]
    error.model_latency_ms = latency_ms  # type: ignore[attr-defined]
    error.model_provider_request_id = provider_request_id  # type: ignore[attr-defined]
    return error


def _json_snapshot(value: object, name: str) -> dict[str, object]:
    if type(value) is not dict:
        raise TypeError(f"{name} must be an exact JSON object")
    visited: set[int] = set()
    stack = [value]
    while stack:
        current = stack.pop()
        current_type = type(current)
        if current is None or current_type in {str, bool, int}:
            continue
        if current_type is float:
            if not isfinite(current):
                raise ValueError(f"{name} must contain finite JSON numbers")
            continue
        if current_type not in {dict, list}:
            raise TypeError(f"{name} must contain only JSON-native values")
        identity = id(current)
        if identity in visited:
            continue
        visited.add(identity)
        if current_type is dict:
            for key, child in current.items():
                if type(key) is not str:
                    raise TypeError(f"{name} must contain only string object keys")
                stack.append(child)
        else:
            stack.extend(current)
    try:
        json.dumps(value, allow_nan=False)
        snapshot = deepcopy(value)
    except (TypeError, ValueError, RecursionError):
        raise ValueError(f"{name} must be a valid JSON object") from None
    return snapshot


def _optional_token_count(value: object, name: str) -> int | None:
    if value is None:
        return None
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer or None")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def _optional_nonblank(value: object, name: str) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise TypeError(f"{name} must be a string or None")
    if not value.strip():
        raise ValueError(f"{name} must be nonblank or None")
    return value


@dataclass(frozen=True)
class ModelRequest:
    role: ModelRole
    node: WorkflowNode
    instructions: str = field(repr=False)
    context: dict[str, object] = field(repr=False)
    repair_error: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.role) is not ModelRole:
            raise TypeError("role must be a ModelRole")
        if type(self.node) is not WorkflowNode:
            raise TypeError("node must be a WorkflowNode")
        if type(self.instructions) is not str:
            raise TypeError("instructions must be a string")
        if not self.instructions.strip():
            raise ValueError("instructions must be nonblank")
        object.__setattr__(self, "context", _json_snapshot(self.context, "context"))
        object.__setattr__(
            self,
            "repair_error",
            _optional_nonblank(self.repair_error, "repair_error"),
        )


@dataclass(frozen=True)
class ModelResult:
    value: dict[str, object] = field(repr=False)
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int
    provider_request_id: str | None = field(repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _json_snapshot(self.value, "value"))
        object.__setattr__(
            self, "input_tokens", _optional_token_count(self.input_tokens, "input_tokens")
        )
        object.__setattr__(
            self,
            "output_tokens",
            _optional_token_count(self.output_tokens, "output_tokens"),
        )
        if type(self.latency_ms) is not int:
            raise TypeError("latency_ms must be an integer")
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")
        object.__setattr__(
            self,
            "provider_request_id",
            _optional_nonblank(self.provider_request_id, "provider_request_id"),
        )


@runtime_checkable
class ModelAdapter(Protocol):
    def invoke(self, request: ModelRequest) -> ModelResult: ...


def elapsed_ms(started_at: float) -> int:
    return max(0, int((perf_counter() - started_at) * 1000))


def post_json_with_retries(
    session: requests.Session,
    url: str,
    *,
    headers: dict[str, str],
    body: dict[str, object],
) -> requests.Response:
    for attempt in range(MAX_HTTP_RETRIES + 1):
        try:
            response = session.post(
                url,
                headers=headers,
                json=body,
                timeout=HTTP_TIMEOUT_SECONDS,
            )
        except requests.RequestException:
            if attempt == MAX_HTTP_RETRIES:
                raise ModelTransportError("model provider network retries exhausted") from None
            continue
        status = response.status_code
        if status == 429 or 500 <= status <= 599:
            if attempt == MAX_HTTP_RETRIES:
                raise ModelTransportError(
                    f"model provider retryable HTTP {status} retries exhausted"
                )
            continue
        if not 200 <= status <= 299:
            raise ModelResponseError(f"model provider rejected request with HTTP {status}")
        return response
    raise ModelTransportError("model provider retries exhausted")


def response_object(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except (ValueError, TypeError, RecursionError):
        raise ModelResponseError("model provider returned malformed JSON") from None
    if type(payload) is not dict:
        raise ModelResponseError("model provider returned a malformed response object")
    return payload


def optional_response_id(payload: dict[str, Any]) -> str | None:
    value = payload.get("id")
    if value is None:
        return None
    if type(value) is not str or not value.strip():
        raise ModelResponseError("model provider returned an invalid request id")
    return value


def safe_response_id(payload: dict[str, Any], secret: str) -> str | None:
    value = optional_response_id(payload)
    if value is not None and secret in value:
        return None
    return value


def usage_counts(
    payload: dict[str, Any],
    *,
    input_names: tuple[str, ...],
    output_names: tuple[str, ...],
) -> tuple[int | None, int | None]:
    usage = payload.get("usage")
    if usage is None:
        return None, None
    if type(usage) is not dict:
        raise ModelResponseError("model provider returned malformed usage")

    def first(names: tuple[str, ...], label: str) -> tuple[int | None, bool]:
        for name in names:
            if name in usage:
                try:
                    return _optional_token_count(usage[name], label), False
                except (TypeError, ValueError):
                    return None, True
        return None, False

    input_tokens, invalid_input = first(input_names, "input_tokens")
    output_tokens, invalid_output = first(output_names, "output_tokens")
    if invalid_input or invalid_output:
        error = ModelResponseError("model provider returned malformed usage")
        error.model_input_tokens = input_tokens  # type: ignore[attr-defined]
        error.model_output_tokens = output_tokens  # type: ignore[attr-defined]
        raise error
    return input_tokens, output_tokens
