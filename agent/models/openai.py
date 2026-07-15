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


class OpenAIResponsesAdapter:
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
        if config.api_style != "responses":
            raise ValueError("config.api_style must be responses")
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

    def with_model(self, model: str) -> OpenAIResponsesAdapter:
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
                    self.config.base_url.rstrip("/") + "/responses",
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
                    input_names=("input_tokens",),
                    output_names=("output_tokens",),
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
                self._check_status(payload)
                text = self._output_text(payload)
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

    @staticmethod
    def _check_status(payload: dict[str, Any]) -> None:
        status = payload.get("status")
        if status is None or status == "completed":
            return
        if status == "incomplete":
            details = payload.get("incomplete_details")
            reason = details.get("reason") if type(details) is dict else None
            if reason == "content_filter":
                raise ModelRefusal("model response was blocked by content filtering")
            raise ModelResponseError("model provider returned an incomplete response")
        raise ModelResponseError("model provider returned a non-completed response")

    def _body(self, request: ModelRequest) -> dict[str, object]:
        schema = schema_for(request.role, request.node)
        instructions = _json_only_instructions(request)
        if self.config.structured_outputs and not has_open_object_schema(schema):
            response_format: dict[str, object] = {
                "type": "json_schema",
                "name": f"{request.role.value}_{request.node.value}_response",
                "strict": True,
                "schema": schema,
            }
        else:
            response_format = {"type": "json_object"}
        body: dict[str, object] = {
            "model": self.config.model,
            "instructions": instructions,
            "input": json.dumps(request.context, ensure_ascii=False, allow_nan=False),
            "text": {"format": response_format},
        }
        if self.config.reasoning.strip():
            body["reasoning"] = {"effort": self.config.reasoning}
        return body

    @staticmethod
    def _output_text(payload: dict[str, Any]) -> str:
        output = payload.get("output")
        if type(output) is not list:
            raise ModelResponseError("model provider returned malformed output")
        chunks: list[str] = []
        for item in output:
            if type(item) is not dict:
                raise ModelResponseError("model provider returned malformed output")
            if item.get("type") != "message":
                continue
            content = item.get("content")
            if type(content) is not list:
                raise ModelResponseError("model provider returned malformed output content")
            for part in content:
                if type(part) is not dict:
                    raise ModelResponseError("model provider returned malformed output content")
                if part.get("type") == "refusal":
                    raise ModelRefusal("model refused to provide a response")
                if part.get("type") == "output_text":
                    text = part.get("text")
                    if type(text) is not str or not text:
                        raise ModelResponseError("model provider returned empty output text")
                    chunks.append(text)
        if not chunks:
            raise ModelResponseError("model provider returned no output text")
        return "".join(chunks)


def _json_only_instructions(request: ModelRequest) -> str:
    instructions = request.instructions.rstrip()
    instructions += "\nReturn only a JSON object matching the required schema."
    if request.repair_error is not None:
        instructions += f"\nThe previous output failed schema validation: {request.repair_error}"
    return instructions
