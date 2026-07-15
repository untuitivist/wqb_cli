from __future__ import annotations

from dataclasses import replace
from math import isfinite
from time import perf_counter
from typing import Protocol

from ..config import ModelConfig
from ..schemas import ModelRefusal, SchemaViolation
from ..types import ModelRole, WorkflowNode
from .base import (
    ModelAdapter,
    ModelError,
    ModelRequest,
    ModelResponseError,
    ModelResult,
    ModelTransportError,
    elapsed_ms,
    sanitize_provider_request_id,
)


class RoleRoutingError(ModelError):
    pass


class ModelPersistenceError(ModelError):
    pass


class _ModelCallStore(Protocol):
    def record_model_call(self, *args: object, **kwargs: object) -> object: ...


_ALLOWED_NODES = {
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


class ModelRouter:
    def __init__(
        self,
        planner_adapter: ModelAdapter,
        operator_adapter: ModelAdapter,
        *,
        store: _ModelCallStore,
        run_id: str,
    ) -> None:
        if type(run_id) is not str:
            raise TypeError("run_id must be a string")
        if not run_id.strip():
            raise ValueError("run_id must be nonblank")
        self._adapters = {
            ModelRole.PLANNER: self._validate_adapter(planner_adapter, "planner_adapter"),
            ModelRole.OPERATOR: self._validate_adapter(operator_adapter, "operator_adapter"),
        }
        for adapter in self._adapters.values():
            _validate_prices(adapter.config)  # type: ignore[attr-defined]
        if not callable(getattr(store, "record_model_call", None)):
            raise TypeError("store must provide record_model_call")
        self._store = store
        self._run_id = run_id

    def __repr__(self) -> str:
        return f"{type(self).__name__}(run_id={self._run_id!r})"

    @staticmethod
    def _validate_adapter(adapter: ModelAdapter, name: str) -> ModelAdapter:
        if not callable(getattr(adapter, "invoke", None)):
            raise TypeError(f"{name} must provide invoke")
        if type(getattr(adapter, "config", None)) is not ModelConfig:
            raise TypeError(f"{name} must expose a ModelConfig")
        return adapter

    def invoke(self, request: ModelRequest, *, purpose: str | None = None) -> ModelResult:
        if type(request) is not ModelRequest:
            raise TypeError("request must be a ModelRequest")
        if request.node not in _ALLOWED_NODES[request.role]:
            raise RoleRoutingError(
                f"role {request.role.value} cannot invoke a model at node {request.node.value}"
            )
        if purpose is None:
            purpose = f"{request.role.value} node {request.node.value}"
        elif type(purpose) is not str:
            raise TypeError("purpose must be a string or None")
        elif not purpose.strip():
            raise ValueError("purpose must be nonblank")

        adapter = self._adapters[request.role]
        config = adapter.config  # type: ignore[attr-defined]
        try:
            return self._invoke_and_record(
                adapter,
                config,
                request,
                purpose,
                fallback_used=False,
            )
        except ModelTransportError:
            fallback_model = config.fallback_model.strip()
            if request.role is not ModelRole.OPERATOR or not fallback_model:
                raise ModelTransportError("model provider transport failed") from None
            clone = getattr(adapter, "with_model", None)
            if not callable(clone):
                raise ModelError("operator adapter does not support model fallback") from None
            try:
                fallback_adapter = clone(fallback_model)
            except Exception:
                raise ModelError("operator fallback model could not be configured") from None
            if type(fallback_adapter) is not type(adapter):
                raise ModelError("operator fallback must keep the same adapter type")
            fallback_config = getattr(fallback_adapter, "config", None)
            if fallback_config != replace(config, model=fallback_model):
                raise ModelError("operator fallback must only change the model")
            try:
                return self._invoke_and_record(
                    fallback_adapter,
                    fallback_config,
                    request,
                    purpose,
                    fallback_used=True,
                )
            except ModelTransportError:
                raise ModelTransportError("operator fallback transport failed") from None

    def _invoke_and_record(
        self,
        adapter: ModelAdapter,
        config: ModelConfig,
        request: ModelRequest,
        purpose: str,
        *,
        fallback_used: bool,
    ) -> ModelResult:
        started_at = perf_counter()
        try:
            result = adapter.invoke(request)
            if type(result) is not ModelResult:
                raise ModelResponseError("model adapter returned an invalid result")
        except Exception as error:
            safe_error = _safe_error(error)
            input_tokens = _failure_integer(error, "model_input_tokens")
            output_tokens = _failure_integer(error, "model_output_tokens")
            persisted_input = _persistable_token_count(input_tokens)
            persisted_output = _persistable_token_count(output_tokens)
            if persisted_input != input_tokens or persisted_output != output_tokens:
                safe_error = "model failure usage exceeded persistence range"
            latency_ms = _failure_integer(error, "model_latency_ms")
            if latency_ms is None:
                latency_ms = elapsed_ms(started_at)
            provider_request_id = _failure_request_id(error)
            self._record(
                config,
                request,
                purpose,
                status="FAILED",
                input_tokens=persisted_input,
                output_tokens=persisted_output,
                cost_usd=_cost_from_counts(config, persisted_input, persisted_output),
                latency_ms=latency_ms,
                fallback_used=fallback_used,
                provider_request_id=sanitize_provider_request_id(provider_request_id),
                error=safe_error,
            )
            raise _sanitized_exception(error) from None

        persisted_input = _persistable_token_count(result.input_tokens)
        persisted_output = _persistable_token_count(result.output_tokens)
        if (
            persisted_input != result.input_tokens
            or persisted_output != result.output_tokens
        ):
            self._record(
                config,
                request,
                purpose,
                status="FAILED",
                input_tokens=persisted_input,
                output_tokens=persisted_output,
                latency_ms=result.latency_ms,
                fallback_used=fallback_used,
                provider_request_id=result.provider_request_id,
                error="model usage exceeded persistence range",
            )
            raise ModelPersistenceError("model usage could not be persisted")

        self._record(
            config,
            request,
            purpose,
            status="COMPLETED",
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cost_usd=_cost_usd(config, result),
            latency_ms=result.latency_ms,
            fallback_used=fallback_used,
            provider_request_id=result.provider_request_id,
        )
        return result

    def _record(
        self,
        config: ModelConfig,
        request: ModelRequest,
        purpose: str,
        *,
        status: str,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_usd: float | None = None,
        latency_ms: int | None = None,
        fallback_used: bool,
        provider_request_id: str | None = None,
        error: str | None = None,
    ) -> None:
        try:
            self._store.record_model_call(
                self._run_id,
                request.role,
                request.node,
                config.provider,
                config.model,
                purpose,
                status,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                fallback_used=fallback_used,
                provider_request_id=sanitize_provider_request_id(
                    provider_request_id
                ),
                error=error,
            )
        except Exception:
            raise ModelPersistenceError("model call metadata could not be persisted") from None


def _cost_usd(config: ModelConfig, result: ModelResult) -> float | None:
    return _cost_from_counts(config, result.input_tokens, result.output_tokens)


def _cost_from_counts(
    config: ModelConfig,
    input_tokens: int | None,
    output_tokens: int | None,
) -> float | None:
    values = (input_tokens, output_tokens, config.input_cost_per_million, config.output_cost_per_million)
    if any(value is None for value in values):
        return None
    input_rate = config.input_cost_per_million
    output_rate = config.output_cost_per_million
    if not _valid_price(input_rate) or not _valid_price(output_rate):
        raise ValueError("model token prices must be finite non-negative numbers")
    assert input_tokens is not None and output_tokens is not None
    try:
        cost = (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
    except OverflowError:
        return None
    return cost if isfinite(cost) else None


def _validate_prices(config: ModelConfig) -> None:
    for value in (config.input_cost_per_million, config.output_cost_per_million):
        if value is not None and not _valid_price(value):
            raise ValueError("model token price must be a finite non-negative number or None")


def _valid_price(value: object) -> bool:
    if type(value) not in {int, float}:
        return False
    try:
        return isfinite(value) and value >= 0
    except OverflowError:
        return False


def _failure_integer(error: Exception, name: str) -> int | None:
    value = getattr(error, name, None)
    if type(value) is int and value >= 0:
        return value
    return None


def _persistable_token_count(value: int | None) -> int | None:
    if value is None or value > 2**63 - 1:
        return None
    return value


def _failure_request_id(error: Exception) -> str | None:
    return sanitize_provider_request_id(
        getattr(error, "model_provider_request_id", None)
    )


def _safe_error(error: Exception) -> str:
    if isinstance(error, SchemaViolation):
        return str(error)
    if isinstance(error, ModelRefusal):
        return "model refusal"
    if isinstance(error, ModelTransportError):
        return "model transport failure"
    if isinstance(error, ModelResponseError):
        return "model response failure"
    if isinstance(error, ModelError):
        return "model invocation failure"
    return "unexpected model invocation failure"


def _sanitized_exception(error: Exception) -> Exception:
    if isinstance(error, SchemaViolation):
        return SchemaViolation(str(error))
    if isinstance(error, ModelRefusal):
        return ModelRefusal("model refused to provide a response")
    if isinstance(error, ModelTransportError):
        return ModelTransportError("model provider transport failed")
    if isinstance(error, ModelResponseError):
        return ModelResponseError("model provider response failed")
    if isinstance(error, ModelError):
        return ModelError("model invocation failed")
    return ModelError("unexpected model invocation failure")
