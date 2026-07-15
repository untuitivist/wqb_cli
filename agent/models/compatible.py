from __future__ import annotations

import json
from dataclasses import replace
from time import perf_counter
from typing import Any

import requests

from ..config import ModelConfig
from ..schemas import (
    MAX_SCHEMA_REPAIR_RETRIES,
    ModelRefusal,
    SchemaViolation,
    has_open_object_schema,
    parse_json_text,
    schema_for,
    validate_model_output,
)
from .base import (
    ModelError,
    ModelRequest,
    ModelResponseError,
    ModelResult,
    UsageAccumulator,
    attach_failure_metadata,
    elapsed_ms,
    post_json_with_retries,
    response_object,
    safe_response_id,
    usage_counts,
)
from .openai import _json_only_instructions


class CompatibleAdapter:
    def __init__(
        self,
        config: ModelConfig,
        api_key: str,
        *,
        session: requests.Session | None = None,
        _transport_identity: object | None = None,
    ) -> None:
        if type(config) is not ModelConfig:
            raise TypeError("config must be a ModelConfig")
        if config.api_style != "chat_completions":
            raise ValueError("config.api_style must be chat_completions")
        if type(api_key) is not str:
            raise TypeError("api_key must be a string")
        if not api_key.strip():
            raise ValueError("api_key must be nonblank")
        self.config = config
        self._api_key = api_key
        self._session = session or requests.Session()
        self._transport_identity = (
            _transport_identity if _transport_identity is not None else object()
        )

    @property
    def transport_identity(self) -> object:
        return self._transport_identity

    def __repr__(self) -> str:
        return f"{type(self).__name__}(model={self.config.model!r})"

    def with_model(self, model: str) -> CompatibleAdapter:
        if type(model) is not str or not model.strip():
            raise ValueError("model override must be a nonblank string")
        return type(self)(
            replace(self.config, model=model),
            self._api_key,
            session=self._session,
            _transport_identity=self._transport_identity,
        )

    def invoke(self, request: ModelRequest) -> ModelResult:
        if type(request) is not ModelRequest:
            raise TypeError("request must be a ModelRequest")
        started_at = perf_counter()
        current = request
        usage = UsageAccumulator()
        provider_request_id: str | None = None
        for repair_attempt in range(MAX_SCHEMA_REPAIR_RETRIES + 1):
            try:
                response = post_json_with_retries(
                    self._session,
                    self.config.base_url.rstrip("/") + "/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    body=self._body(current),
                )
                payload = response_object(response)
            except ModelError as error:
                raise attach_failure_metadata(
                    error,
                    usage,
                    latency_ms=elapsed_ms(started_at),
                    provider_request_id=provider_request_id,
                )
            id_error: ModelResponseError | None = None
            try:
                provider_request_id = safe_response_id(payload, self._api_key)
            except ModelResponseError as error:
                id_error = error
            usage_error: ModelResponseError | None = None
            try:
                input_tokens, output_tokens = usage_counts(
                    payload,
                    input_names=("input_tokens", "prompt_tokens"),
                    output_names=("output_tokens", "completion_tokens"),
                )
            except ModelResponseError as error:
                usage_error = error
                input_tokens = getattr(error, "model_input_tokens", None)
                output_tokens = getattr(error, "model_output_tokens", None)
            usage.add(input_tokens, output_tokens)
            if id_error is not None:
                raise attach_failure_metadata(
                    id_error,
                    usage,
                    latency_ms=elapsed_ms(started_at),
                    provider_request_id=provider_request_id,
                )
            if usage_error is not None:
                raise attach_failure_metadata(
                    usage_error,
                    usage,
                    latency_ms=elapsed_ms(started_at),
                    provider_request_id=provider_request_id,
                )
            try:
                text = self._message_text(payload)
                value = validate_model_output(
                    current.role,
                    current.node,
                    parse_json_text(text),
                )
            except ModelRefusal as error:
                raise attach_failure_metadata(
                    error,
                    usage,
                    latency_ms=elapsed_ms(started_at),
                    provider_request_id=provider_request_id,
                )
            except ModelResponseError as error:
                raise attach_failure_metadata(
                    error,
                    usage,
                    latency_ms=elapsed_ms(started_at),
                    provider_request_id=provider_request_id,
                )
            except SchemaViolation as error:
                if repair_attempt == MAX_SCHEMA_REPAIR_RETRIES:
                    raise attach_failure_metadata(
                        error,
                        usage,
                        latency_ms=elapsed_ms(started_at),
                        provider_request_id=provider_request_id,
                    )
                current = replace(current, repair_error=str(error))
                continue
            input_tokens, output_tokens = usage.values()
            return ModelResult(
                value=value,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=elapsed_ms(started_at),
                provider_request_id=provider_request_id,
            )
        raise ModelResponseError("model schema repair retries exhausted")

    def _body(self, request: ModelRequest) -> dict[str, object]:
        schema = schema_for(request.role, request.node)
        if self.config.structured_outputs and not has_open_object_schema(schema):
            response_format: dict[str, object] = {
                "type": "json_schema",
                "json_schema": {
                    "name": f"{request.role.value}_{request.node.value}_response",
                    "strict": True,
                    "schema": schema,
                },
            }
        else:
            response_format = {"type": "json_object"}
        return {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": _json_only_instructions(request)},
                {
                    "role": "user",
                    "content": json.dumps(
                        request.context,
                        ensure_ascii=False,
                        allow_nan=False,
                    ),
                },
            ],
            "response_format": response_format,
        }

    @staticmethod
    def _message_text(payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if type(choices) is not list or not choices or type(choices[0]) is not dict:
            raise ModelResponseError("model provider returned malformed choices")
        choice = choices[0]
        finish_reason = choice.get("finish_reason")
        if finish_reason == "content_filter":
            raise ModelRefusal("model response was blocked by content filtering")
        if finish_reason is not None and finish_reason != "stop":
            raise ModelResponseError("model provider returned a non-stop finish reason")
        message = choice.get("message")
        if type(message) is not dict:
            raise ModelResponseError("model provider returned malformed message")
        if message.get("refusal") is not None:
            raise ModelRefusal("model refused to provide a response")
        content = message.get("content")
        if type(content) is not str or not content:
            raise ModelResponseError("model provider returned empty message content")
        return content


OpenAICompatibleAdapter = CompatibleAdapter
