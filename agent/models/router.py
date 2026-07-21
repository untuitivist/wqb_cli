from __future__ import annotations

from dataclasses import replace
from decimal import Decimal, InvalidOperation
from math import isfinite
from time import perf_counter
from typing import Protocol

from ..config import ModelConfig
from ..schemas import ModelRefusal, SchemaViolation, validate_model_output
from ..types import ModelRole, WorkflowNode
from .base import (
    FallbackCapableAdapter,
    ModelAdapter,
    ModelConnectError,
    ModelError,
    ModelNetworkError,
    ModelProxyError,
    ModelRateLimitError,
    ModelReadTimeoutError,
    ModelRequest,
    ModelResponseError,
    ModelResult,
    ModelServerError,
    ModelTLSError,
    ModelTransportError,
    ModelUpstreamError,
    elapsed_ms,
    sanitize_provider_request_id,
)


class RoleRoutingError(ModelError):
    pass


class ModelPersistenceError(ModelError):
    pass


class _UnpersistableCost(ValueError):
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
        planner, planner_config = self._validate_adapter(
            planner_adapter, "planner_adapter"
        )
        operator, operator_config = self._validate_adapter(
            operator_adapter, "operator_adapter"
        )
        self._adapters = {
            ModelRole.PLANNER: planner,
            ModelRole.OPERATOR: operator,
        }
        self._configs = {
            ModelRole.PLANNER: planner_config,
            ModelRole.OPERATOR: operator_config,
        }
        for config in self._configs.values():
            _validate_prices(config)
        if not callable(getattr(store, "record_model_call", None)):
            raise TypeError("store must provide record_model_call")
        self._store = store
        self._run_id = run_id

    def __repr__(self) -> str:
        return f"{type(self).__name__}(run_id={self._run_id!r})"

    @staticmethod
    def _validate_adapter(
        adapter: ModelAdapter, name: str
    ) -> tuple[ModelAdapter, ModelConfig]:
        try:
            invoke = getattr(adapter, "invoke", None)
            config = getattr(adapter, "config", None)
        except Exception:
            raise TypeError(f"{name} has inaccessible protocol attributes") from None
        if not callable(invoke):
            raise TypeError(f"{name} must provide invoke")
        if type(config) is not ModelConfig:
            raise TypeError(f"{name} must expose a ModelConfig")
        return adapter, config

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
        config = self._configs[request.role]
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
                raise
            try:
                fallback_capable = isinstance(adapter, FallbackCapableAdapter)
                transport_identity = (
                    adapter.transport_identity if fallback_capable else None
                )
            except Exception:
                raise ModelError("operator adapter transport identity is unavailable") from None
            if not fallback_capable:
                raise ModelError("operator adapter does not support model fallback") from None
            if transport_identity is None:
                raise ModelError("operator adapter transport identity is unavailable")
            try:
                fallback_adapter = adapter.with_model(fallback_model)
            except Exception:
                raise ModelError("operator fallback model could not be configured") from None
            if type(fallback_adapter) is not type(adapter):
                raise ModelError("operator fallback must keep the same adapter type")
            try:
                fallback_config = fallback_adapter.config
            except Exception:
                raise ModelError("operator fallback configuration is unavailable") from None
            if fallback_config != replace(config, model=fallback_model):
                raise ModelError("operator fallback must only change the model")
            try:
                preserves_identity = (
                    isinstance(fallback_adapter, FallbackCapableAdapter)
                    and fallback_adapter.transport_identity is transport_identity
                )
            except Exception:
                preserves_identity = False
            if not preserves_identity:
                raise ModelError("operator fallback must preserve transport identity")
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
            try:
                value = validate_model_output(request.role, request.node, result.value)
            except SchemaViolation as error:
                error.model_input_tokens = result.input_tokens
                error.model_output_tokens = result.output_tokens
                error.model_latency_ms = result.latency_ms
                error.model_provider_request_id = result.provider_request_id
                raise
            result = ModelResult(
                value,
                result.input_tokens,
                result.output_tokens,
                result.latency_ms,
                result.provider_request_id,
            )
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
            persisted_latency = _persistable_latency_ms(latency_ms)
            if persisted_latency != latency_ms:
                safe_error = "model failure latency exceeded persistence range"
            provider_request_id = _failure_request_id(error)
            try:
                failure_cost = _cost_from_counts(
                    config, persisted_input, persisted_output
                )
            except _UnpersistableCost:
                failure_cost = None
                safe_error = "model failure cost exceeded persistence range"
            self._record(
                config,
                request,
                purpose,
                status="FAILED",
                input_tokens=persisted_input,
                output_tokens=persisted_output,
                cost_usd=failure_cost,
                latency_ms=persisted_latency,
                fallback_used=fallback_used,
                provider_request_id=sanitize_provider_request_id(provider_request_id),
                error=safe_error,
            )
            raise _sanitized_exception(error) from None

        persisted_input = _persistable_token_count(result.input_tokens)
        persisted_output = _persistable_token_count(result.output_tokens)
        persisted_latency = _persistable_latency_ms(result.latency_ms)
        invalid_usage = (
            persisted_input != result.input_tokens
            or persisted_output != result.output_tokens
        )
        invalid_latency = persisted_latency != result.latency_ms
        if invalid_usage or invalid_latency:
            try:
                failure_cost = _cost_from_counts(
                    config, persisted_input, persisted_output
                )
            except _UnpersistableCost:
                failure_cost = None
            invalid_fields = []
            if invalid_usage:
                invalid_fields.append("usage")
            if invalid_latency:
                invalid_fields.append("latency")
            self._record(
                config,
                request,
                purpose,
                status="FAILED",
                input_tokens=persisted_input,
                output_tokens=persisted_output,
                cost_usd=failure_cost,
                latency_ms=persisted_latency,
                fallback_used=fallback_used,
                provider_request_id=result.provider_request_id,
                error=f"model {' and '.join(invalid_fields)} exceeded persistence range",
            )
            raise ModelPersistenceError("model metadata could not be persisted")

        try:
            cost_usd = _cost_usd(config, result)
        except _UnpersistableCost:
            self._record(
                config,
                request,
                purpose,
                status="FAILED",
                input_tokens=persisted_input,
                output_tokens=persisted_output,
                latency_ms=persisted_latency,
                fallback_used=fallback_used,
                provider_request_id=result.provider_request_id,
                error="model cost exceeded persistence range",
            )
            raise ModelPersistenceError("model cost could not be persisted")

        self._record(
            config,
            request,
            purpose,
            status="COMPLETED",
            input_tokens=persisted_input,
            output_tokens=persisted_output,
            cost_usd=cost_usd,
            latency_ms=persisted_latency,
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
        cost_decimal = (
            Decimal(input_tokens) * Decimal(str(input_rate))
            + Decimal(output_tokens) * Decimal(str(output_rate))
        ) / Decimal(1_000_000)
        cost = float(cost_decimal)
    except (ArithmeticError, InvalidOperation, ValueError):
        raise _UnpersistableCost from None
    if not isfinite(cost) or cost < 0 or cost == 0 and cost_decimal != 0:
        raise _UnpersistableCost
    return cost


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
    value = _safe_exception_metadata(error, name)
    if type(value) is int and value >= 0:
        return value
    return None


def _persistable_token_count(value: int | None) -> int | None:
    if value is None or value > 2**63 - 1:
        return None
    return value


def _persistable_latency_ms(value: int) -> int | None:
    if value > 2**63 - 1:
        return None
    return value


def _failure_request_id(error: Exception) -> str | None:
    return sanitize_provider_request_id(
        _safe_exception_metadata(error, "model_provider_request_id")
    )


def _safe_exception_metadata(error: Exception, name: str) -> object:
    try:
        return getattr(error, name, None)
    except Exception:
        return None


def _safe_error(error: Exception) -> str:
    if isinstance(error, SchemaViolation):
        return str(error)
    if isinstance(error, ModelRefusal):
        return "model refusal"
    if isinstance(error, ModelRateLimitError):
        return "model rate limit exhausted"
    if isinstance(error, ModelServerError):
        status = _safe_exception_metadata(error, "model_http_status")
        return (
            f"model provider HTTP {status} retries exhausted"
            if type(status) is int and 500 <= status <= 599
            else "model provider 5xx retries exhausted"
        )
    if isinstance(error, ModelUpstreamError):
        return _safe_response_error(error, retries_exhausted=True)
    if isinstance(error, ModelReadTimeoutError):
        return str(error)
    if isinstance(error, ModelProxyError):
        return "model provider proxy retries exhausted"
    if isinstance(error, ModelTLSError):
        return "model provider TLS retries exhausted"
    if isinstance(error, ModelConnectError):
        return str(error)
    if isinstance(error, ModelNetworkError):
        return "model network retries exhausted"
    if isinstance(error, ModelTransportError):
        return "model transport failure"
    if isinstance(error, ModelResponseError):
        return _safe_response_error(error)
    if isinstance(error, ModelError):
        return "model invocation failure"
    return "unexpected model invocation failure"


def _sanitized_exception(error: Exception) -> Exception:
    if isinstance(error, SchemaViolation):
        return SchemaViolation(str(error))
    if isinstance(error, ModelRefusal):
        return ModelRefusal("model refused to provide a response")
    if isinstance(error, ModelRateLimitError):
        return ModelRateLimitError("model provider rate limit exhausted")
    if isinstance(error, ModelServerError):
        return ModelServerError("model provider server retries exhausted")
    if isinstance(error, ModelUpstreamError):
        return ModelUpstreamError(_safe_response_error(error, retries_exhausted=True))
    if isinstance(error, ModelReadTimeoutError):
        return ModelReadTimeoutError(str(error))
    if isinstance(error, ModelProxyError):
        return ModelProxyError("model provider proxy retries exhausted")
    if isinstance(error, ModelTLSError):
        return ModelTLSError("model provider TLS retries exhausted")
    if isinstance(error, ModelConnectError):
        return ModelConnectError(str(error))
    if isinstance(error, ModelNetworkError):
        return ModelNetworkError("model provider network retries exhausted")
    if isinstance(error, ModelTransportError):
        return ModelTransportError("model provider transport failed")
    if isinstance(error, ModelResponseError):
        return ModelResponseError(_safe_response_error(error))
    if isinstance(error, ModelError):
        return ModelError("model invocation failed")
    return ModelError("unexpected model invocation failure")


def _safe_response_error(error: Exception, *, retries_exhausted: bool = False) -> str:
    status = _safe_exception_metadata(error, "model_http_status")
    summary = f"model provider HTTP {status}" if type(status) is int else "model response failure"
    details = []
    for name in ("type", "code", "param"):
        value = _safe_exception_metadata(error, f"model_provider_error_{name}")
        if type(value) is str:
            details.append(f"{name}={value}")
    if details:
        summary += f" ({', '.join(details)})"
    if retries_exhausted:
        summary += " retries exhausted"
    return summary
