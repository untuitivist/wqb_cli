from __future__ import annotations

import json
import tempfile
import unittest
from collections import deque
from dataclasses import replace
from math import isfinite
from unittest.mock import patch

import requests

from wqb_cli.agent.config import ModelConfig
from wqb_cli.agent.models.base import (
    ModelConnectError,
    ModelNetworkError,
    ModelReadTimeoutError,
    ModelRateLimitError,
    ModelRequest,
    ModelResponseError,
    ModelResult,
    ModelServerError,
    ModelTransportError,
    ModelUpstreamError,
    create_model_session,
)
from wqb_cli.agent.models.compatible import CompatibleAdapter
from wqb_cli.agent.models.openai import OpenAIResponsesAdapter
from wqb_cli.agent.models.router import (
    ModelError,
    ModelPersistenceError,
    ModelRouter,
    RoleRoutingError,
)
from wqb_cli.agent.schemas import ModelRefusal
from wqb_cli.agent.store import AgentStore
from wqb_cli.agent.types import ModelRole, RunConfig, ScopeMode, WorkflowNode
from wqb_cli.core.secrets import get_named_secret


FAKE_SECRET = "sk-test-super-secret"
UNSAFE_PROVIDER_REQUEST_IDS = (
    "request\nInjected",
    "request\x00control",
    "Authorization: Bearer credential",
    '{"id":"raw-body"}',
    "request-id-nonascii-\u8bf7\u6c42",
    "a" * 256,
    f"request-{FAKE_SECRET}",
)


def model_config(
    *,
    role: ModelRole,
    structured_outputs: bool = True,
    fallback_model: str = "",
    reasoning: str = "",
) -> ModelConfig:
    return ModelConfig(
        provider="openai" if role is ModelRole.PLANNER else "openai-compatible",
        api_style="responses" if role is ModelRole.PLANNER else "chat_completions",
        model=f"{role.value}-model",
        base_url="https://models.example.test/v1/",
        reasoning=reasoning,
        secret_name=f"{role.value}-secret",
        structured_outputs=structured_outputs,
        fallback_model=fallback_model,
        input_cost_per_million=2.0,
        output_cost_per_million=4.0,
    )


def valid_output(role: ModelRole, node: WorkflowNode) -> dict[str, object]:
    value: dict[str, object] = {
        "decision": "continue",
        "reasoning_summary": "The evidence supports continuing",
        "evidence_refs": ["artifact:1"],
        "confidence": 0.75,
    }
    if role is ModelRole.OPERATOR:
        value["task_result"] = {"status": "COMPLETED", "payload": {}}
    elif node is WorkflowNode.D:
        value["scope_decision"] = {"candidate_id": "USA_D1_PV"}
    elif node in {WorkflowNode.F, WorkflowNode.G}:
        value["evidence_requirements"] = {}
    elif node is WorkflowNode.H:
        value["research_plan"] = {
            "mechanisms": [
                {
                    "mechanism_id": "m1",
                    "tower_id": "tower-1",
                    "field_ids": ["vwap"],
                    "field_bindings": [
                        {
                            "field_id": "vwap",
                            "role": "primary_signal",
                            "rationale": "Volume-weighted price measures persistent price discovery pressure.",
                            "evidence_refs": ["artifact:1"],
                        }
                    ],
                    "evidence_refs": ["artifact:1"],
                    "hypothesis": "Persistent price-volume divergence may reveal delayed price discovery.",
                }
            ]
        }
    elif node is WorkflowNode.I:
        value["candidate_plan"] = {}
    elif node is WorkflowNode.K:
        value["diagnosis"] = {"failure_class": "PASS", "next_node": "L"}
    elif node is WorkflowNode.L:
        value["final_recommendation"] = {}
    return value


class FakeResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        if isinstance(self._payload, BaseException):
            raise self._payload
        return self._payload


class FakeSession:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = deque(outcomes)
        self.calls: list[dict[str, object]] = []

    def post(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        outcome = self.outcomes.popleft()
        if isinstance(outcome, BaseException):
            raise outcome
        assert isinstance(outcome, FakeResponse)
        return outcome


def openai_response(
    value: dict[str, object],
    *,
    input_tokens: int = 11,
    output_tokens: int = 7,
    request_id: str = "resp_123",
) -> FakeResponse:
    return FakeResponse(
        200,
        {
            "id": request_id,
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": json.dumps(value)}
                    ],
                }
            ],
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        },
    )


def compatible_response(value: dict[str, object]) -> FakeResponse:
    return FakeResponse(
        200,
        {
            "id": "chatcmpl_123",
            "choices": [{"message": {"content": json.dumps(value)}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
        },
    )


class ModelValueTests(unittest.TestCase):
    def test_request_and_result_validate_exact_types_and_json_values(self) -> None:
        request = ModelRequest(
            ModelRole.PLANNER,
            WorkflowNode.B,
            " Plan the next step ",
            {"round": 1, "ready": True},
        )
        result = ModelResult({"ok": True}, 1, 2, 0, "request-1")
        self.assertEqual(request.role, ModelRole.PLANNER)
        self.assertEqual(result.output_tokens, 2)

        invalid_requests = (
            lambda: ModelRequest("planner", WorkflowNode.B, "plan", {}),
            lambda: ModelRequest(ModelRole.PLANNER, "B", "plan", {}),
            lambda: ModelRequest(ModelRole.PLANNER, WorkflowNode.B, " ", {}),
            lambda: ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "plan", {"x": (1,)}),
            lambda: ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "plan", {}, " "),
        )
        for operation in invalid_requests:
            with self.subTest(operation=operation):
                with self.assertRaises((TypeError, ValueError)):
                    operation()

        invalid_results = (
            lambda: ModelResult({"x": object()}, 1, 2, 0, None),
            lambda: ModelResult({}, True, 2, 0, None),
            lambda: ModelResult({}, 1, -1, 0, None),
            lambda: ModelResult({}, 1, 2, -1, None),
        )
        for operation in invalid_results:
            with self.subTest(operation=operation):
                with self.assertRaises((TypeError, ValueError)):
                    operation()

    def test_model_result_sanitizes_untrusted_provider_request_ids(self) -> None:
        for safe_id in (
            "resp_123",
            "chatcmpl-123",
            "request.123",
            "a" * 255,
        ):
            with self.subTest(safe_id=safe_id):
                result = ModelResult({"ok": True}, 1, 2, 3, safe_id)
                self.assertEqual(result.provider_request_id, safe_id)
        for unsafe_id in (*UNSAFE_PROVIDER_REQUEST_IDS, " ", 123):
            with self.subTest(unsafe_id=unsafe_id):
                result = ModelResult({"ok": True}, 1, 2, 3, unsafe_id)  # type: ignore[arg-type]
                self.assertIsNone(result.provider_request_id)
                self.assertNotIn("provider_request_id", repr(result))
                if unsafe_id not in {" ", 123}:
                    self.assertNotIn(str(unsafe_id), repr(result))

    def test_request_and_result_repr_do_not_expand_sensitive_payloads(self) -> None:
        request = ModelRequest(
            ModelRole.PLANNER,
            WorkflowNode.B,
            f"Use credential {FAKE_SECRET}",
            {"Authorization": f"Bearer {FAKE_SECRET}"},
            repair_error=FAKE_SECRET,
        )
        result = ModelResult({"secret": FAKE_SECRET}, 1, 1, 1, FAKE_SECRET)
        self.assertNotIn(FAKE_SECRET, repr(request))
        self.assertNotIn("Authorization", repr(request))
        self.assertNotIn(FAKE_SECRET, repr(result))

    def test_json_native_shared_containers_are_snapshotted_not_rejected_as_cycles(self) -> None:
        shared = [1, 2]
        request = ModelRequest(
            ModelRole.PLANNER,
            WorkflowNode.B,
            "Plan",
            {"first": shared, "second": shared},
        )
        shared.append(3)
        self.assertEqual(request.context, {"first": [1, 2], "second": [1, 2]})


class AdapterTests(unittest.TestCase):
    def test_openai_includes_configured_reasoning_effort_only_when_nonblank(self) -> None:
        for reasoning, expected in (("high", {"effort": "high"}), ("", None)):
            with self.subTest(reasoning=reasoning):
                session = FakeSession(
                    [openai_response(valid_output(ModelRole.PLANNER, WorkflowNode.B))]
                )
                adapter = OpenAIResponsesAdapter(
                    model_config(role=ModelRole.PLANNER, reasoning=reasoning),
                    FAKE_SECRET,
                    session=session,
                )
                adapter.invoke(
                    ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {})
                )
                body = session.calls[0]["json"]
                if expected is None:
                    self.assertNotIn("reasoning", body)
                else:
                    self.assertEqual(body["reasoning"], expected)

    def test_adapters_reject_mismatched_api_style_before_http(self) -> None:
        cases = (
            (
                OpenAIResponsesAdapter,
                replace(
                    model_config(role=ModelRole.PLANNER),
                    api_style="chat_completions",
                ),
            ),
            (
                CompatibleAdapter,
                replace(
                    model_config(role=ModelRole.OPERATOR),
                    api_style="responses",
                ),
            ),
        )
        for adapter_type, config in cases:
            with self.subTest(adapter_type=adapter_type):
                session = FakeSession([])
                with self.assertRaisesRegex(ValueError, "api_style"):
                    adapter_type(config, FAKE_SECRET, session=session)
                self.assertEqual(session.calls, [])

    def test_openai_closed_schema_uses_strict_json_schema_without_secret_in_body_or_repr(self) -> None:
        session = FakeSession([openai_response(valid_output(ModelRole.PLANNER, WorkflowNode.K))])
        adapter = OpenAIResponsesAdapter(model_config(role=ModelRole.PLANNER), FAKE_SECRET, session=session)
        result = adapter.invoke(
            ModelRequest(ModelRole.PLANNER, WorkflowNode.K, "Diagnose", {"metric": 1})
        )

        call = session.calls[0]
        body = call["json"]
        assert isinstance(body, dict)
        self.assertEqual(call["url"], "https://models.example.test/v1/responses")
        self.assertEqual(call["timeout"], (10, 300))
        self.assertEqual(body["text"]["format"]["type"], "json_schema")
        self.assertIs(body["text"]["format"]["strict"], True)
        self.assertEqual(result.input_tokens, 11)
        self.assertEqual(result.output_tokens, 7)
        self.assertEqual(result.provider_request_id, "resp_123")
        self.assertGreaterEqual(result.latency_ms, 0)
        self.assertNotIn(FAKE_SECRET, repr(adapter))
        self.assertNotIn(FAKE_SECRET, json.dumps(body))

    def test_adapter_repr_hides_base_url_userinfo(self) -> None:
        config = replace(
            model_config(role=ModelRole.PLANNER),
            base_url=f"https://{FAKE_SECRET}@models.example.test/v1",
        )
        adapter = OpenAIResponsesAdapter(config, FAKE_SECRET, session=FakeSession([]))
        self.assertNotIn(FAKE_SECRET, repr(adapter))

    def test_openai_open_schema_uses_json_object_and_repairs_local_validation_twice_at_most(self) -> None:
        incomplete = valid_output(ModelRole.PLANNER, WorkflowNode.F)
        incomplete.pop("evidence_requirements")
        session = FakeSession(
            [
                openai_response(incomplete),
                openai_response(incomplete),
                openai_response(valid_output(ModelRole.PLANNER, WorkflowNode.F)),
            ]
        )
        adapter = OpenAIResponsesAdapter(model_config(role=ModelRole.PLANNER), FAKE_SECRET, session=session)
        result = adapter.invoke(
            ModelRequest(ModelRole.PLANNER, WorkflowNode.F, "Choose evidence", {"regions": ["USA"]})
        )

        self.assertEqual(result.value["evidence_requirements"], {})
        self.assertEqual(result.input_tokens, 33)
        self.assertEqual(result.output_tokens, 21)
        self.assertEqual(len(session.calls), 3)
        for call in session.calls:
            body = call["json"]
            assert isinstance(body, dict)
            self.assertEqual(body["text"]["format"], {"type": "json_object"})
            self.assertIn("JSON object", body["instructions"])
        self.assertIn("evidence_requirements", session.calls[1]["json"]["instructions"])

    def test_openai_unsupported_strict_schema_uses_json_object(self) -> None:
        session = FakeSession(
            [openai_response(valid_output(ModelRole.PLANNER, WorkflowNode.H))]
        )
        adapter = OpenAIResponsesAdapter(
            model_config(role=ModelRole.PLANNER), FAKE_SECRET, session=session
        )

        adapter.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.H, "Plan", {}))

        self.assertEqual(
            session.calls[0]["json"]["text"]["format"], {"type": "json_object"}
        )

    def test_schema_repair_is_bounded_to_initial_plus_two_retries(self) -> None:
        incomplete = valid_output(ModelRole.PLANNER, WorkflowNode.F)
        incomplete.pop("evidence_requirements")
        session = FakeSession([openai_response(incomplete) for _ in range(3)])
        adapter = OpenAIResponsesAdapter(model_config(role=ModelRole.PLANNER), FAKE_SECRET, session=session)
        with self.assertRaisesRegex(ValueError, "evidence_requirements"):
            adapter.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.F, "Choose", {}))
        self.assertEqual(len(session.calls), 3)

    def test_compatible_closed_open_and_disabled_structured_modes(self) -> None:
        cases = (
            (ModelRole.PLANNER, WorkflowNode.K, True, "json_schema"),
            (ModelRole.PLANNER, WorkflowNode.D, True, "json_schema"),
            (ModelRole.PLANNER, WorkflowNode.H, True, "json_object"),
            (ModelRole.OPERATOR, WorkflowNode.F, True, "json_object"),
            (ModelRole.PLANNER, WorkflowNode.K, False, "json_object"),
        )
        for role, node, enabled, expected_type in cases:
            with self.subTest(role=role, node=node, enabled=enabled):
                session = FakeSession([compatible_response(valid_output(role, node))])
                config = replace(
                    model_config(role=role, structured_outputs=enabled),
                    api_style="chat_completions",
                )
                adapter = CompatibleAdapter(
                    config,
                    FAKE_SECRET,
                    session=session,
                )
                result = adapter.invoke(ModelRequest(role, node, "Execute", {}))
                request_body = session.calls[0]["json"]
                response_format = request_body["response_format"]
                self.assertEqual(response_format["type"], expected_type)
                if expected_type == "json_schema":
                    self.assertIs(response_format["json_schema"]["strict"], True)
                instructions = request_body["messages"][0]["content"]
                self.assertIn("Required JSON Schema:", instructions)
                self.assertIn('"decision"', instructions)
                self.assertIn('"reasoning_summary"', instructions)
                self.assertIn('"evidence_refs"', instructions)
                self.assertEqual(result.value, valid_output(role, node))
                self.assertNotIn(FAKE_SECRET, json.dumps(session.calls[0]["json"]))

    def test_compatible_drops_untrusted_request_ids_without_losing_usage(self) -> None:
        for unsafe_id in UNSAFE_PROVIDER_REQUEST_IDS:
            with self.subTest(unsafe_id=unsafe_id):
                response = compatible_response(
                    valid_output(ModelRole.OPERATOR, WorkflowNode.B)
                )
                assert isinstance(response._payload, dict)
                response._payload["id"] = unsafe_id
                adapter = CompatibleAdapter(
                    model_config(role=ModelRole.OPERATOR),
                    FAKE_SECRET,
                    session=FakeSession([response]),
                )
                result = adapter.invoke(
                    ModelRequest(ModelRole.OPERATOR, WorkflowNode.B, "Execute", {})
                )
                self.assertIsNone(result.provider_request_id)
                self.assertEqual(result.input_tokens, 5)
                self.assertEqual(result.output_tokens, 3)

    def test_refusal_is_controlled_and_not_repaired(self) -> None:
        session = FakeSession(
            [
                FakeResponse(
                    200,
                    {
                        "output": [
                            {
                                "type": "message",
                                "content": [
                                    {"type": "refusal", "refusal": FAKE_SECRET}
                                ],
                            }
                        ]
                    },
                )
            ]
        )
        adapter = OpenAIResponsesAdapter(model_config(role=ModelRole.PLANNER), FAKE_SECRET, session=session)
        with self.assertRaises(ModelRefusal) as raised:
            adapter.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {}))
        self.assertEqual(len(session.calls), 1)
        self.assertNotIn(FAKE_SECRET, str(raised.exception))

    def test_openai_provider_status_prevents_valid_content_from_succeeding(self) -> None:
        cases = (
            ("incomplete", "content_filter", ModelRefusal),
            ("incomplete", "max_output_tokens", ModelResponseError),
            ("failed", None, ModelResponseError),
        )
        for status, reason, expected_error in cases:
            with self.subTest(status=status, reason=reason):
                response = openai_response(
                    valid_output(ModelRole.OPERATOR, WorkflowNode.B)
                )
                assert isinstance(response._payload, dict)
                response._payload["status"] = status
                if reason is not None:
                    response._payload["incomplete_details"] = {"reason": reason}
                session = FakeSession([response])
                operator_config = replace(
                    model_config(
                        role=ModelRole.OPERATOR,
                        fallback_model="operator-fallback",
                    ),
                    provider="openai",
                    api_style="responses",
                )
                operator = OpenAIResponsesAdapter(
                    operator_config, FAKE_SECRET, session=session
                )
                planner = RecordingAdapter(
                    model_config(role=ModelRole.PLANNER),
                    [ModelResult(valid_output(ModelRole.PLANNER, WorkflowNode.B), 1, 1, 1, None)],
                )
                store = RecordingStore()
                router = ModelRouter(planner, operator, store=store, run_id="run-1")
                with self.assertRaises(expected_error):
                    router.invoke(
                        ModelRequest(ModelRole.OPERATOR, WorkflowNode.B, "Execute", {})
                    )
                self.assertEqual(len(session.calls), 1)
                self.assertEqual(len(store.calls), 1)
                self.assertEqual(store.calls[0]["status"], "FAILED")
                self.assertEqual(store.calls[0]["input_tokens"], 11)
                self.assertEqual(store.calls[0]["output_tokens"], 7)
                self.assertEqual(store.calls[0]["provider_request_id"], "resp_123")
                self.assertGreaterEqual(store.calls[0]["latency_ms"], 0)
                self.assertIs(store.calls[0]["fallback_used"], False)

        completed = openai_response(valid_output(ModelRole.PLANNER, WorkflowNode.B))
        assert isinstance(completed._payload, dict)
        completed._payload["status"] = "completed"
        adapter = OpenAIResponsesAdapter(
            model_config(role=ModelRole.PLANNER),
            FAKE_SECRET,
            session=FakeSession([completed]),
        )
        result = adapter.invoke(
            ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {})
        )
        self.assertEqual(result.value, valid_output(ModelRole.PLANNER, WorkflowNode.B))

    def test_compatible_finish_reason_prevents_valid_content_from_succeeding(self) -> None:
        cases = (
            ("content_filter", ModelRefusal),
            ("length", ModelResponseError),
            ("tool_calls", ModelResponseError),
            ({"malformed": True}, ModelResponseError),
        )
        for finish_reason, expected_error in cases:
            with self.subTest(finish_reason=finish_reason):
                response = compatible_response(
                    valid_output(ModelRole.OPERATOR, WorkflowNode.B)
                )
                assert isinstance(response._payload, dict)
                response._payload["choices"][0]["finish_reason"] = finish_reason
                session = FakeSession([response])
                operator = CompatibleAdapter(
                    model_config(
                        role=ModelRole.OPERATOR,
                        fallback_model="operator-fallback",
                    ),
                    FAKE_SECRET,
                    session=session,
                )
                planner = RecordingAdapter(
                    model_config(role=ModelRole.PLANNER),
                    [ModelResult(valid_output(ModelRole.PLANNER, WorkflowNode.B), 1, 1, 1, None)],
                )
                store = RecordingStore()
                router = ModelRouter(planner, operator, store=store, run_id="run-1")
                with self.assertRaises(expected_error):
                    router.invoke(
                        ModelRequest(ModelRole.OPERATOR, WorkflowNode.B, "Execute", {})
                    )
                self.assertEqual(len(session.calls), 1)
                self.assertEqual(len(store.calls), 1)
                self.assertEqual(store.calls[0]["status"], "FAILED")
                self.assertEqual(store.calls[0]["input_tokens"], 5)
                self.assertEqual(store.calls[0]["output_tokens"], 3)
                self.assertEqual(store.calls[0]["provider_request_id"], "chatcmpl_123")
                self.assertGreaterEqual(store.calls[0]["latency_ms"], 0)
                self.assertIs(store.calls[0]["fallback_used"], False)

        stopped = compatible_response(valid_output(ModelRole.OPERATOR, WorkflowNode.B))
        assert isinstance(stopped._payload, dict)
        stopped._payload["choices"][0]["finish_reason"] = "stop"
        adapter = CompatibleAdapter(
            model_config(role=ModelRole.OPERATOR),
            FAKE_SECRET,
            session=FakeSession([stopped]),
        )
        result = adapter.invoke(
            ModelRequest(ModelRole.OPERATOR, WorkflowNode.B, "Execute", {})
        )
        self.assertEqual(result.value, valid_output(ModelRole.OPERATOR, WorkflowNode.B))

    def test_openai_ignores_non_content_output_items(self) -> None:
        payload = openai_response(valid_output(ModelRole.PLANNER, WorkflowNode.B))._payload
        assert isinstance(payload, dict)
        payload["output"].insert(0, {"type": "reasoning", "summary": []})
        session = FakeSession([FakeResponse(200, payload)])
        adapter = OpenAIResponsesAdapter(model_config(role=ModelRole.PLANNER), FAKE_SECRET, session=session)
        result = adapter.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {}))
        self.assertEqual(result.value, valid_output(ModelRole.PLANNER, WorkflowNode.B))

    def test_openai_only_accepts_output_text_from_message_items(self) -> None:
        fake = valid_output(ModelRole.PLANNER, WorkflowNode.B)
        fake["decision"] = "reasoning must not win"
        real = valid_output(ModelRole.PLANNER, WorkflowNode.B)
        reasoning_item = {
            "type": "reasoning",
            "content": [{"type": "output_text", "text": json.dumps(fake)}],
        }
        message_item = {
            "type": "message",
            "content": [{"type": "output_text", "text": json.dumps(real)}],
        }

        mixed_response = FakeResponse(
            200, {"output": [reasoning_item, message_item]}
        )
        session = FakeSession([mixed_response, mixed_response, mixed_response])
        adapter = OpenAIResponsesAdapter(
            model_config(role=ModelRole.PLANNER), FAKE_SECRET, session=session
        )
        result = adapter.invoke(
            ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {})
        )
        self.assertEqual(result.value, real)

    def test_openai_rejects_reasoning_only_pseudo_output_text(self) -> None:
        fake = valid_output(ModelRole.PLANNER, WorkflowNode.B)
        reasoning_item = {
            "type": "reasoning",
            "content": [{"type": "output_text", "text": json.dumps(fake)}],
        }
        reasoning_only = FakeSession(
            [FakeResponse(200, {"output": [reasoning_item]})]
        )
        adapter = OpenAIResponsesAdapter(
            model_config(role=ModelRole.PLANNER),
            FAKE_SECRET,
            session=reasoning_only,
        )
        with self.assertRaisesRegex(RuntimeError, "no output text"):
            adapter.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {}))

    def test_retryable_http_and_network_failures_are_finite_and_sanitized(self) -> None:
        retryable = (requests.ConnectionError(FAKE_SECRET), FakeResponse(429, {}), FakeResponse(503, {}))
        session = FakeSession(list(retryable))
        adapter = OpenAIResponsesAdapter(model_config(role=ModelRole.PLANNER), FAKE_SECRET, session=session)
        with patch("wqb_cli.agent.models.base.sleep") as sleeper, self.assertRaises(
            ModelServerError
        ) as raised:
            adapter.invoke(
                ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {})
            )
        self.assertEqual(len(session.calls), 3)
        self.assertEqual(sleeper.call_args_list[0].args, (1.0,))
        self.assertEqual(sleeper.call_args_list[1].args, (2.0,))
        self.assertNotIn(FAKE_SECRET, str(raised.exception))

    def test_retry_exhaustion_classifies_network_rate_limit_and_server_errors(self) -> None:
        cases = (
            (
                [requests.ConnectionError(FAKE_SECRET) for _ in range(3)],
                ModelNetworkError,
            ),
            ([FakeResponse(429, {}) for _ in range(3)], ModelRateLimitError),
            ([FakeResponse(502, {}) for _ in range(3)], ModelServerError),
            (
                [
                    FakeResponse(
                        424,
                        {"error": {"type": "api_error", "message": FAKE_SECRET}},
                    )
                    for _ in range(3)
                ],
                ModelUpstreamError,
            ),
        )
        for outcomes, expected in cases:
            with self.subTest(expected=expected):
                session = FakeSession(outcomes)
                adapter = OpenAIResponsesAdapter(
                    model_config(role=ModelRole.PLANNER),
                    FAKE_SECRET,
                    session=session,
                )
                with patch("wqb_cli.agent.models.base.sleep") as sleeper:
                    with self.assertRaises(expected) as raised:
                        adapter.invoke(
                            ModelRequest(
                                ModelRole.PLANNER, WorkflowNode.B, "Plan", {}
                            )
                        )
                self.assertEqual(sleeper.call_count, 2)
                if expected is ModelUpstreamError:
                    self.assertIn("HTTP 424", str(raised.exception))
                    self.assertIn("type=api_error", str(raised.exception))
                    self.assertNotIn(FAKE_SECRET, str(raised.exception))

    def test_read_timeout_is_not_retried_after_request_submission(self) -> None:
        session = FakeSession([requests.ReadTimeout(FAKE_SECRET)])
        adapter = OpenAIResponsesAdapter(
            model_config(role=ModelRole.PLANNER), FAKE_SECRET, session=session
        )

        with patch("wqb_cli.agent.models.base.sleep") as sleeper:
            with self.assertRaisesRegex(ModelReadTimeoutError, "300 seconds"):
                adapter.invoke(
                    ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {})
                )

        self.assertEqual(len(session.calls), 1)
        self.assertEqual(session.calls[0]["timeout"], (10, 300))
        sleeper.assert_not_called()

    def test_connect_failures_remain_bounded_and_retryable(self) -> None:
        session = FakeSession([requests.ConnectTimeout("down") for _ in range(3)])
        adapter = OpenAIResponsesAdapter(
            model_config(role=ModelRole.PLANNER), FAKE_SECRET, session=session
        )

        with patch("wqb_cli.agent.models.base.sleep") as sleeper:
            with self.assertRaises(ModelConnectError):
                adapter.invoke(
                    ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {})
                )

        self.assertEqual(len(session.calls), 3)
        self.assertEqual(sleeper.call_count, 2)

    def test_model_session_applies_role_proxy_mode(self) -> None:
        direct = create_model_session(
            replace(model_config(role=ModelRole.PLANNER), proxy_mode="direct")
        )
        self.assertIs(direct.trust_env, False)
        self.assertEqual(direct.proxies, {})

        custom = create_model_session(
            replace(
                model_config(role=ModelRole.PLANNER),
                proxy_mode="custom",
                proxy_url="http://127.0.0.1:7890",
            )
        )
        self.assertIs(custom.trust_env, False)
        self.assertEqual(custom.proxies["http"], "http://127.0.0.1:7890")
        self.assertEqual(custom.proxies["https"], "http://127.0.0.1:7890")

    def test_compatible_h_json_object_keeps_local_schema_repair(self) -> None:
        incomplete = valid_output(ModelRole.PLANNER, WorkflowNode.H)
        incomplete.pop("research_plan")
        session = FakeSession(
            [
                compatible_response(incomplete),
                compatible_response(valid_output(ModelRole.PLANNER, WorkflowNode.H)),
            ]
        )
        config = replace(
            model_config(role=ModelRole.PLANNER, structured_outputs=True),
            api_style="chat_completions",
        )
        adapter = CompatibleAdapter(config, FAKE_SECRET, session=session)

        result = adapter.invoke(
            ModelRequest(ModelRole.PLANNER, WorkflowNode.H, "Plan", {})
        )

        self.assertEqual(len(session.calls), 2)
        self.assertEqual(
            session.calls[0]["json"]["response_format"], {"type": "json_object"}
        )
        self.assertIn(
            "research_plan",
            session.calls[1]["json"]["messages"][0]["content"],
        )
        self.assertIn("research_plan", result.value)

    def test_nonretryable_and_malformed_responses_fail_without_echoing_payload(self) -> None:
        cases = (
            [FakeResponse(400, {"error": FAKE_SECRET})],
            [FakeResponse(200, {"output": []})],
            [FakeResponse(200, ValueError(FAKE_SECRET))],
        )
        for outcomes in cases:
            with self.subTest(outcomes=outcomes):
                session = FakeSession(outcomes)
                adapter = OpenAIResponsesAdapter(model_config(role=ModelRole.PLANNER), FAKE_SECRET, session=session)
                with self.assertRaises(RuntimeError) as raised:
                    adapter.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {}))
                self.assertEqual(len(session.calls), 1)
                self.assertNotIn(FAKE_SECRET, str(raised.exception))


class SecretTests(unittest.TestCase):
    def test_named_secret_validates_and_delegates_without_exposing_value(self) -> None:
        with patch("wqb_cli.core.secrets.get_secret", return_value=FAKE_SECRET) as getter:
            self.assertEqual(get_named_secret("planner-key"), FAKE_SECRET)
        getter.assert_called_once_with("wqb-cli", "planner-key")
        for invalid in ("", " ", 1):
            with self.subTest(invalid=invalid):
                with self.assertRaises((TypeError, ValueError)) as raised:
                    get_named_secret(invalid)  # type: ignore[arg-type]
                self.assertNotIn(FAKE_SECRET, str(raised.exception))


class RecordingAdapter:
    def __init__(
        self,
        config: ModelConfig,
        outcomes: list[object],
        invocations: list[tuple[str, ModelRequest]] | None = None,
        transport_identity: object | None = None,
    ) -> None:
        self.config = config
        self.outcomes = deque(outcomes)
        self.invocations = invocations if invocations is not None else []
        self.transport_identity = (
            transport_identity if transport_identity is not None else object()
        )

    def invoke(self, request: ModelRequest) -> ModelResult:
        self.invocations.append((self.config.model, request))
        outcome = self.outcomes.popleft()
        if isinstance(outcome, BaseException):
            raise outcome
        assert isinstance(outcome, ModelResult)
        return outcome

    def with_model(self, model: str) -> RecordingAdapter:
        return RecordingAdapter(
            replace(self.config, model=model),
            list(self.outcomes),
            self.invocations,
            self.transport_identity,
        )


class RecordingStore:
    def __init__(self, error: BaseException | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self.error = error

    def record_model_call(self, *args: object, **kwargs: object) -> object:
        names = ("run_id", "role", "node", "provider", "model", "purpose", "status")
        values = dict(zip(names, args, strict=False))
        values.update(kwargs)
        self.calls.append(values)
        if self.error is not None:
            raise self.error
        return object()


class InvalidResultAdapter:
    def __init__(self, config: ModelConfig) -> None:
        self.config = config
        self.invocations: list[ModelRequest] = []

    def invoke(self, request: ModelRequest) -> object:
        self.invocations.append(request)
        return {"not": "a ModelResult"}


class ExplosiveMetadataTransportError(ModelTransportError):
    def __init__(self, explosive_name: str) -> None:
        super().__init__("provider unavailable")
        self.explosive_name = explosive_name
        self.model_input_tokens = 3
        self.model_output_tokens = 2
        self.model_latency_ms = 7
        self.model_provider_request_id = "metadata-id"

    def __getattribute__(self, name: str) -> object:
        if name == object.__getattribute__(self, "explosive_name"):
            raise RuntimeError(FAKE_SECRET)
        return super().__getattribute__(name)


class OneShotConfigAdapter(RecordingAdapter):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._config_reads = 0

    def __getattribute__(self, name: str) -> object:
        if name == "config":
            reads = object.__getattribute__(self, "_config_reads")
            if reads:
                raise RuntimeError(FAKE_SECRET)
            object.__setattr__(self, "_config_reads", reads + 1)
        return super().__getattribute__(name)

    def invoke(self, request: ModelRequest) -> ModelResult:
        config = object.__getattribute__(self, "config")
        self.invocations.append((config.model, request))
        outcome = self.outcomes.popleft()
        if isinstance(outcome, BaseException):
            raise outcome
        assert isinstance(outcome, ModelResult)
        return outcome


class RouterTests(unittest.TestCase):
    def make_router(
        self,
        *,
        planner_outcomes: list[object] | None = None,
        operator_outcomes: list[object] | None = None,
        fallback_model: str = "",
        store: RecordingStore | None = None,
    ) -> tuple[ModelRouter, RecordingAdapter, RecordingAdapter, RecordingStore]:
        success = ModelResult(valid_output(ModelRole.PLANNER, WorkflowNode.K), 10, 20, 12, "p")
        operator_success = ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.K), 3, 4, 8, "o")
        planner = RecordingAdapter(
            model_config(role=ModelRole.PLANNER),
            planner_outcomes if planner_outcomes is not None else [success],
        )
        operator = RecordingAdapter(
            model_config(role=ModelRole.OPERATOR, fallback_model=fallback_model),
            operator_outcomes if operator_outcomes is not None else [operator_success],
        )
        recording_store = store or RecordingStore()
        router = ModelRouter(
            planner,
            operator,
            store=recording_store,
            run_id="run-1",
        )
        return router, planner, operator, recording_store

    def test_planner_k_only_uses_planner_and_operator_k_is_allowed(self) -> None:
        router, planner, operator, _ = self.make_router()
        planner_result = router.invoke(
            ModelRequest(ModelRole.PLANNER, WorkflowNode.K, "Diagnose", {}),
            purpose="diagnose",
        )
        operator_result = router.invoke(
            ModelRequest(ModelRole.OPERATOR, WorkflowNode.K, "Organize metrics", {}),
            purpose="organize",
        )
        self.assertEqual(planner_result.provider_request_id, "p")
        self.assertEqual(operator_result.provider_request_id, "o")
        self.assertEqual([request.role for _, request in planner.invocations], [ModelRole.PLANNER])
        self.assertEqual([request.role for _, request in operator.invocations], [ModelRole.OPERATOR])

    def test_router_caches_adapter_config_after_single_guarded_read(self) -> None:
        planner = OneShotConfigAdapter(
            model_config(role=ModelRole.PLANNER),
            [ModelResult(valid_output(ModelRole.PLANNER, WorkflowNode.B), 1, 1, 2, "cached")],
        )
        operator = RecordingAdapter(
            model_config(role=ModelRole.OPERATOR),
            [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
        )
        store = RecordingStore()
        router = ModelRouter(planner, operator, store=store, run_id="run-1")
        result = router.invoke(
            ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {})
        )
        self.assertEqual(result.provider_request_id, "cached")
        self.assertEqual(planner._config_reads, 1)
        self.assertEqual(store.calls[0]["status"], "COMPLETED")

    def test_operator_d_and_non_model_nodes_are_rejected_before_invocation(self) -> None:
        router, planner, operator, store = self.make_router()
        for role, node in (
            (ModelRole.OPERATOR, WorkflowNode.D),
            (ModelRole.PLANNER, WorkflowNode.A),
            (ModelRole.OPERATOR, WorkflowNode.J),
            (ModelRole.PLANNER, WorkflowNode.M),
        ):
            with self.subTest(role=role, node=node):
                with self.assertRaises(RoleRoutingError):
                    router.invoke(ModelRequest(role, node, "Not allowed", {}))
        self.assertEqual(planner.invocations, [])
        self.assertEqual(operator.invocations, [])
        self.assertEqual(store.calls, [])

    def test_planner_transport_failure_never_calls_operator_or_fallback(self) -> None:
        router, planner, operator, store = self.make_router(
            planner_outcomes=[ModelTransportError("planner unavailable")],
            fallback_model="operator-fallback",
        )
        with self.assertRaises(ModelTransportError):
            router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.K, "Diagnose", {}))
        self.assertEqual(len(planner.invocations), 1)
        self.assertEqual(operator.invocations, [])
        self.assertEqual(len(store.calls), 1)
        self.assertEqual(store.calls[0]["status"], "FAILED")
        self.assertIs(store.calls[0]["fallback_used"], False)

    def test_operator_transport_exhaustion_uses_same_adapter_fallback_once_and_records_both(self) -> None:
        fallback_result = ModelResult(
            valid_output(ModelRole.OPERATOR, WorkflowNode.K), 3, 4, 9, "fallback-id"
        )
        router, _, operator, store = self.make_router(
            operator_outcomes=[ModelTransportError("primary exhausted"), fallback_result],
            fallback_model="operator-fallback",
        )
        result = router.invoke(
            ModelRequest(ModelRole.OPERATOR, WorkflowNode.K, "Organize", {}),
            purpose="organize",
        )
        self.assertEqual(result.provider_request_id, "fallback-id")
        self.assertEqual(
            [model for model, _ in operator.invocations],
            ["operator-model", "operator-fallback"],
        )
        self.assertEqual([call["status"] for call in store.calls], ["FAILED", "COMPLETED"])
        self.assertEqual([call["model"] for call in store.calls], ["operator-model", "operator-fallback"])
        self.assertEqual([call["fallback_used"] for call in store.calls], [False, True])
        self.assertAlmostEqual(store.calls[1]["cost_usd"], 0.000022)

    def test_success_persists_usage_cost_latency_and_request_id(self) -> None:
        router, _, _, store = self.make_router()
        router.invoke(
            ModelRequest(ModelRole.PLANNER, WorkflowNode.K, "Diagnose", {}),
            purpose="diagnose",
        )
        call = store.calls[0]
        self.assertEqual(call["input_tokens"], 10)
        self.assertEqual(call["output_tokens"], 20)
        self.assertEqual(call["latency_ms"], 12)
        self.assertAlmostEqual(call["cost_usd"], 0.0001)
        self.assertEqual(call["provider_request_id"], "p")
        self.assertEqual(call["purpose"], "diagnose")

    def test_cost_calculation_scales_terms_before_summing(self) -> None:
        result = ModelResult(
            valid_output(ModelRole.PLANNER, WorkflowNode.B), 1, 1, 4, "cost"
        )
        planner = RecordingAdapter(
            replace(
                model_config(role=ModelRole.PLANNER),
                input_cost_per_million=1e308,
                output_cost_per_million=1e308,
            ),
            [result],
        )
        operator = RecordingAdapter(
            model_config(role=ModelRole.OPERATOR),
            [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
        )
        store = RecordingStore()
        router = ModelRouter(planner, operator, store=store, run_id="run-1")
        router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {}))
        self.assertEqual(store.calls[0]["status"], "COMPLETED")
        self.assertTrue(isfinite(store.calls[0]["cost_usd"]))
        self.assertAlmostEqual(store.calls[0]["cost_usd"], 2e302)

    def test_missing_usage_or_rate_persists_none_cost(self) -> None:
        result = ModelResult(valid_output(ModelRole.PLANNER, WorkflowNode.K), None, 20, 1, None)
        router, _, _, store = self.make_router(planner_outcomes=[result])
        router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.K, "Diagnose", {}))
        self.assertIsNone(store.calls[0]["cost_usd"])

    def test_failed_call_error_is_sanitized_and_store_failure_is_controlled(self) -> None:
        router, _, _, store = self.make_router(
            planner_outcomes=[ModelTransportError(FAKE_SECRET)]
        )
        with self.assertRaises(ModelTransportError) as raised:
            router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.K, "Diagnose", {}))
        self.assertNotIn(FAKE_SECRET, str(raised.exception))
        self.assertNotIn(FAKE_SECRET, json.dumps(store.calls))

        broken_store = RecordingStore(RuntimeError(FAKE_SECRET))
        router, _, _, _ = self.make_router(store=broken_store)
        with self.assertRaises(ModelPersistenceError) as persistence_error:
            router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.K, "Diagnose", {}))
        self.assertNotIn(FAKE_SECRET, str(persistence_error.exception))

    def test_explosive_failure_metadata_getters_are_sanitized_and_recorded(self) -> None:
        names = (
            "model_input_tokens",
            "model_output_tokens",
            "model_latency_ms",
            "model_provider_request_id",
        )
        for name in names:
            with self.subTest(name=name):
                planner = RecordingAdapter(
                    model_config(role=ModelRole.PLANNER),
                    [ExplosiveMetadataTransportError(name)],
                )
                operator = RecordingAdapter(
                    model_config(role=ModelRole.OPERATOR),
                    [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
                )
                store = RecordingStore()
                router = ModelRouter(planner, operator, store=store, run_id="run-1")
                with self.assertRaises(ModelTransportError) as raised:
                    router.invoke(
                        ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {})
                    )
                self.assertEqual(len(store.calls), 1)
                self.assertEqual(store.calls[0]["status"], "FAILED")
                self.assertNotIn(FAKE_SECRET, str(raised.exception))

    def test_invalid_adapter_result_is_controlled_and_recorded_as_failed(self) -> None:
        planner = InvalidResultAdapter(model_config(role=ModelRole.PLANNER))
        operator = RecordingAdapter(
            model_config(role=ModelRole.OPERATOR),
            [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
        )
        store = RecordingStore()
        router = ModelRouter(planner, operator, store=store, run_id="run-1")  # type: ignore[arg-type]
        with self.assertRaises(ModelError) as raised:
            router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {}))
        self.assertNotIsInstance(raised.exception, AttributeError)
        self.assertEqual(len(planner.invocations), 1)
        self.assertEqual(len(store.calls), 1)
        self.assertEqual(store.calls[0]["status"], "FAILED")

    def test_router_revalidates_custom_model_result_for_requested_schema(self) -> None:
        invalid_for_k = ModelResult(
            valid_output(ModelRole.PLANNER, WorkflowNode.B),
            3,
            2,
            7,
            "custom-invalid",
        )
        planner = RecordingAdapter(
            model_config(role=ModelRole.PLANNER), [invalid_for_k]
        )
        operator = RecordingAdapter(
            model_config(role=ModelRole.OPERATOR),
            [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
        )
        store = RecordingStore()
        router = ModelRouter(planner, operator, store=store, run_id="run-1")
        with self.assertRaisesRegex(ValueError, "diagnosis"):
            router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.K, "Diagnose", {}))
        self.assertEqual(store.calls[0]["status"], "FAILED")
        self.assertEqual(store.calls[0]["input_tokens"], 3)
        self.assertEqual(store.calls[0]["output_tokens"], 2)
        self.assertEqual(store.calls[0]["latency_ms"], 7)
        self.assertEqual(store.calls[0]["provider_request_id"], "custom-invalid")

    def test_schema_failure_persists_aggregate_usage_cost_and_request_id(self) -> None:
        incomplete = valid_output(ModelRole.PLANNER, WorkflowNode.D)
        incomplete.pop("scope_decision")
        session = FakeSession([openai_response(incomplete) for _ in range(3)])
        planner = OpenAIResponsesAdapter(
            model_config(role=ModelRole.PLANNER), FAKE_SECRET, session=session
        )
        operator = RecordingAdapter(
            model_config(role=ModelRole.OPERATOR),
            [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.K), 1, 1, 1, None)],
        )
        store = RecordingStore()
        router = ModelRouter(planner, operator, store=store, run_id="run-1")
        with self.assertRaisesRegex(ValueError, "scope_decision"):
            router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.D, "Choose", {}))
        self.assertEqual(store.calls[0]["input_tokens"], 33)
        self.assertEqual(store.calls[0]["output_tokens"], 21)
        self.assertAlmostEqual(store.calls[0]["cost_usd"], 0.00015)
        self.assertEqual(store.calls[0]["provider_request_id"], "resp_123")
        self.assertGreaterEqual(store.calls[0]["latency_ms"], 0)

    def test_malformed_output_persists_available_usage_and_request_id(self) -> None:
        malformed = FakeResponse(
            200,
            {
                "id": "malformed-id",
                "output": [],
                "usage": {"input_tokens": 2, "output_tokens": 1},
            },
        )
        planner = OpenAIResponsesAdapter(
            model_config(role=ModelRole.PLANNER),
            FAKE_SECRET,
            session=FakeSession([malformed]),
        )
        operator = RecordingAdapter(
            model_config(role=ModelRole.OPERATOR),
            [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
        )
        store = RecordingStore()
        router = ModelRouter(planner, operator, store=store, run_id="run-1")
        with self.assertRaises(RuntimeError):
            router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {}))
        self.assertEqual(store.calls[0]["input_tokens"], 2)
        self.assertEqual(store.calls[0]["output_tokens"], 1)
        self.assertAlmostEqual(store.calls[0]["cost_usd"], 0.000008)
        self.assertEqual(store.calls[0]["provider_request_id"], "malformed-id")

    def test_untrusted_provider_response_ids_are_dropped_without_losing_usage(self) -> None:
        for unsafe_id in UNSAFE_PROVIDER_REQUEST_IDS:
            with self.subTest(unsafe_id=unsafe_id):
                session = FakeSession(
                    [
                        openai_response(
                            valid_output(ModelRole.PLANNER, WorkflowNode.B),
                            request_id=unsafe_id,
                        )
                    ]
                )
                planner = OpenAIResponsesAdapter(
                    model_config(role=ModelRole.PLANNER), FAKE_SECRET, session=session
                )
                operator = RecordingAdapter(
                    model_config(role=ModelRole.OPERATOR),
                    [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
                )
                store = RecordingStore()
                router = ModelRouter(planner, operator, store=store, run_id="run-1")
                result = router.invoke(
                    ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {})
                )
                self.assertIsNone(result.provider_request_id)
                self.assertIsNone(store.calls[0]["provider_request_id"])
                self.assertEqual(store.calls[0]["input_tokens"], 11)
                self.assertEqual(store.calls[0]["output_tokens"], 7)
                self.assertGreaterEqual(store.calls[0]["latency_ms"], 0)
                self.assertNotIn(unsafe_id, json.dumps(store.calls))

    def test_custom_model_results_cannot_bypass_request_id_sanitizer(self) -> None:
        for unsafe_id in UNSAFE_PROVIDER_REQUEST_IDS:
            with self.subTest(unsafe_id=unsafe_id):
                result = ModelResult(
                    valid_output(ModelRole.PLANNER, WorkflowNode.B),
                    3,
                    2,
                    7,
                    unsafe_id,
                )
                planner = RecordingAdapter(
                    model_config(role=ModelRole.PLANNER), [result]
                )
                operator = RecordingAdapter(
                    model_config(role=ModelRole.OPERATOR),
                    [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
                )
                store = RecordingStore()
                router = ModelRouter(planner, operator, store=store, run_id="run-1")
                returned = router.invoke(
                    ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {})
                )
                self.assertIsNone(returned.provider_request_id)
                self.assertIsNone(store.calls[0]["provider_request_id"])
                self.assertEqual(store.calls[0]["input_tokens"], 3)
                self.assertEqual(store.calls[0]["latency_ms"], 7)

    def test_failure_metadata_cannot_bypass_request_id_sanitizer(self) -> None:
        for unsafe_id in UNSAFE_PROVIDER_REQUEST_IDS:
            with self.subTest(unsafe_id=unsafe_id):
                error = ModelTransportError("provider unavailable")
                error.model_input_tokens = 3
                error.model_output_tokens = 2
                error.model_latency_ms = 7
                error.model_provider_request_id = unsafe_id
                planner = RecordingAdapter(
                    model_config(role=ModelRole.PLANNER), [error]
                )
                operator = RecordingAdapter(
                    model_config(role=ModelRole.OPERATOR),
                    [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
                )
                store = RecordingStore()
                router = ModelRouter(planner, operator, store=store, run_id="run-1")
                with self.assertRaises(ModelTransportError) as raised:
                    router.invoke(
                        ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {})
                    )
                self.assertIsNone(store.calls[0]["provider_request_id"])
                self.assertEqual(store.calls[0]["input_tokens"], 3)
                self.assertEqual(store.calls[0]["output_tokens"], 2)
                self.assertEqual(store.calls[0]["latency_ms"], 7)
                self.assertNotIn(unsafe_id, str(raised.exception))

    def test_malformed_usage_preserves_request_id_and_valid_token_side(self) -> None:
        payload = openai_response(valid_output(ModelRole.PLANNER, WorkflowNode.B))._payload
        assert isinstance(payload, dict)
        payload["id"] = "known-id"
        payload["usage"] = {"input_tokens": 2, "output_tokens": "bad"}
        planner = OpenAIResponsesAdapter(
            model_config(role=ModelRole.PLANNER),
            FAKE_SECRET,
            session=FakeSession([FakeResponse(200, payload)]),
        )
        operator = RecordingAdapter(
            model_config(role=ModelRole.OPERATOR),
            [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
        )
        store = RecordingStore()
        router = ModelRouter(planner, operator, store=store, run_id="run-1")
        with self.assertRaises(RuntimeError):
            router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {}))
        self.assertEqual(store.calls[0]["provider_request_id"], "known-id")
        self.assertEqual(store.calls[0]["input_tokens"], 2)
        self.assertIsNone(store.calls[0]["output_tokens"])
        self.assertIsNone(store.calls[0]["cost_usd"])

    def test_repair_transport_failure_preserves_prior_usage_and_request_id(self) -> None:
        incomplete = valid_output(ModelRole.PLANNER, WorkflowNode.D)
        incomplete.pop("scope_decision")
        session = FakeSession(
            [
                openai_response(incomplete),
                requests.ConnectionError("down-1"),
                requests.ConnectionError("down-2"),
                requests.ConnectionError("down-3"),
            ]
        )
        planner = OpenAIResponsesAdapter(
            model_config(role=ModelRole.PLANNER), FAKE_SECRET, session=session
        )
        operator = RecordingAdapter(
            model_config(role=ModelRole.OPERATOR),
            [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
        )
        store = RecordingStore()
        router = ModelRouter(planner, operator, store=store, run_id="run-1")
        with self.assertRaises(ModelTransportError):
            router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.D, "Choose", {}))
        self.assertEqual(len(session.calls), 4)
        self.assertEqual(store.calls[0]["input_tokens"], 11)
        self.assertEqual(store.calls[0]["output_tokens"], 7)
        self.assertAlmostEqual(store.calls[0]["cost_usd"], 0.00005)
        self.assertEqual(store.calls[0]["provider_request_id"], "resp_123")

    def test_initial_transport_failure_records_unknown_not_zero_usage(self) -> None:
        session = FakeSession(
            [requests.ConnectionError("down") for _ in range(3)]
        )
        planner = OpenAIResponsesAdapter(
            model_config(role=ModelRole.PLANNER), FAKE_SECRET, session=session
        )
        operator = RecordingAdapter(
            model_config(role=ModelRole.OPERATOR),
            [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
        )
        store = RecordingStore()
        router = ModelRouter(planner, operator, store=store, run_id="run-1")
        with self.assertRaises(ModelTransportError):
            router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {}))
        self.assertIsNone(store.calls[0]["input_tokens"])
        self.assertIsNone(store.calls[0]["output_tokens"])
        self.assertIsNone(store.calls[0]["cost_usd"])

    def test_malformed_request_id_does_not_discard_valid_usage(self) -> None:
        payload = openai_response(valid_output(ModelRole.PLANNER, WorkflowNode.B))._payload
        assert isinstance(payload, dict)
        payload["id"] = 123
        payload["usage"] = {"input_tokens": 2, "output_tokens": 1}
        planner = OpenAIResponsesAdapter(
            model_config(role=ModelRole.PLANNER),
            FAKE_SECRET,
            session=FakeSession([FakeResponse(200, payload)]),
        )
        operator = RecordingAdapter(
            model_config(role=ModelRole.OPERATOR),
            [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
        )
        store = RecordingStore()
        router = ModelRouter(planner, operator, store=store, run_id="run-1")
        result = router.invoke(
            ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {})
        )
        self.assertIsNone(result.provider_request_id)
        self.assertEqual(store.calls[0]["status"], "COMPLETED")
        self.assertEqual(store.calls[0]["input_tokens"], 2)
        self.assertEqual(store.calls[0]["output_tokens"], 1)
        self.assertAlmostEqual(store.calls[0]["cost_usd"], 0.000008)
        self.assertIsNone(store.calls[0]["provider_request_id"])

    def test_unpersistable_usage_records_controlled_accounting_failure(self) -> None:
        huge_tokens = 10**1000
        result = ModelResult(
            valid_output(ModelRole.PLANNER, WorkflowNode.B),
            huge_tokens,
            huge_tokens,
            1,
            "huge",
        )
        planner = RecordingAdapter(
            replace(
                model_config(role=ModelRole.PLANNER),
                input_cost_per_million=1e308,
                output_cost_per_million=1e308,
            ),
            [result],
        )
        operator = RecordingAdapter(
            model_config(role=ModelRole.OPERATOR),
            [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
        )
        store = RecordingStore()
        router = ModelRouter(planner, operator, store=store, run_id="run-1")
        with self.assertRaises(ModelPersistenceError):
            router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {}))
        self.assertEqual(store.calls[0]["status"], "FAILED")
        self.assertIsNone(store.calls[0]["input_tokens"])
        self.assertIsNone(store.calls[0]["output_tokens"])
        self.assertIsNone(store.calls[0]["cost_usd"])
        self.assertEqual(store.calls[0]["error"], "model usage exceeded persistence range")

    def test_unpersistable_latency_records_controlled_accounting_failure(self) -> None:
        result = ModelResult(
            valid_output(ModelRole.PLANNER, WorkflowNode.B),
            3,
            2,
            10**1000,
            "latency-overflow",
        )
        planner = RecordingAdapter(model_config(role=ModelRole.PLANNER), [result])
        operator = RecordingAdapter(
            model_config(role=ModelRole.OPERATOR),
            [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
        )
        store = RecordingStore()
        router = ModelRouter(planner, operator, store=store, run_id="run-1")
        with self.assertRaises(ModelPersistenceError):
            router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {}))
        self.assertEqual(store.calls[0]["status"], "FAILED")
        self.assertEqual(store.calls[0]["input_tokens"], 3)
        self.assertEqual(store.calls[0]["output_tokens"], 2)
        self.assertAlmostEqual(store.calls[0]["cost_usd"], 0.000014)
        self.assertIsNone(store.calls[0]["latency_ms"])
        self.assertEqual(store.calls[0]["provider_request_id"], "latency-overflow")

    def test_compatible_refusal_persists_available_usage_without_repair(self) -> None:
        refusal = FakeResponse(
            200,
            {
                "id": "chat-refusal",
                "choices": [{"message": {"content": None, "refusal": FAKE_SECRET}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3},
            },
        )
        planner = CompatibleAdapter(
            replace(
                model_config(role=ModelRole.PLANNER),
                api_style="chat_completions",
            ),
            FAKE_SECRET,
            session=FakeSession([refusal]),
        )
        operator = RecordingAdapter(
            model_config(role=ModelRole.OPERATOR),
            [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.K), 1, 1, 1, None)],
        )
        store = RecordingStore()
        router = ModelRouter(planner, operator, store=store, run_id="run-1")
        with self.assertRaises(ModelRefusal) as raised:
            router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {}))
        self.assertEqual(len(planner._session.calls), 1)
        self.assertEqual(store.calls[0]["input_tokens"], 5)
        self.assertEqual(store.calls[0]["output_tokens"], 3)
        self.assertEqual(store.calls[0]["provider_request_id"], "chat-refusal")
        self.assertNotIn(FAKE_SECRET, str(raised.exception))

    def test_router_rejects_invalid_price_boundaries_before_invocation(self) -> None:
        for invalid_rate in (True, -1, float("nan"), 10**1000):
            with self.subTest(invalid_rate=invalid_rate):
                planner = RecordingAdapter(
                    replace(
                        model_config(role=ModelRole.PLANNER),
                        input_cost_per_million=invalid_rate,
                    ),
                    [ModelResult(valid_output(ModelRole.PLANNER, WorkflowNode.B), 1, 1, 1, None)],
                )
                operator = RecordingAdapter(
                    model_config(role=ModelRole.OPERATOR),
                    [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
                )
                with self.assertRaisesRegex(ValueError, "price"):
                    ModelRouter(planner, operator, store=RecordingStore(), run_id="run-1")
                self.assertEqual(planner.invocations, [])


class UnsafeFallbackAdapter(RecordingAdapter):
    def with_model(self, model: str) -> RecordingAdapter:
        return RecordingAdapter(
            replace(self.config, model=model, base_url="https://other.example.test/v1"),
            list(self.outcomes),
            self.invocations,
        )


class CrossTypeFallbackAdapter(RecordingAdapter):
    def with_model(self, model: str) -> RecordingAdapter:
        return RecordingAdapter(
            replace(self.config, model=model),
            list(self.outcomes),
            self.invocations,
        )


class ChangedIdentityFallbackAdapter(RecordingAdapter):
    def with_model(self, model: str) -> ChangedIdentityFallbackAdapter:
        return type(self)(
            replace(self.config, model=model),
            list(self.outcomes),
            self.invocations,
        )


class ExplosiveIdentityFallbackAdapter(RecordingAdapter):
    def __getattribute__(self, name: str) -> object:
        if name == "transport_identity":
            raise RuntimeError(FAKE_SECRET)
        return super().__getattribute__(name)


class ExplosiveCloneConfigAdapter(RecordingAdapter):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._explode_config = False

    def __getattribute__(self, name: str) -> object:
        if name == "config" and object.__getattribute__(self, "_explode_config"):
            raise RuntimeError(FAKE_SECRET)
        return super().__getattribute__(name)

    def with_model(self, model: str) -> ExplosiveCloneConfigAdapter:
        clone = type(self)(
            replace(self.config, model=model),
            list(self.outcomes),
            self.invocations,
            self.transport_identity,
        )
        clone._explode_config = True
        return clone


class FallbackInvariantTests(unittest.TestCase):
    def test_builtin_model_clones_preserve_transport_identity_session_and_key(self) -> None:
        cases = (
            OpenAIResponsesAdapter(
                model_config(role=ModelRole.PLANNER),
                FAKE_SECRET,
                session=FakeSession([]),
            ),
            CompatibleAdapter(
                model_config(role=ModelRole.OPERATOR),
                FAKE_SECRET,
                session=FakeSession([]),
            ),
        )
        for adapter in cases:
            with self.subTest(adapter=type(adapter).__name__):
                clone = adapter.with_model("fallback-model")
                self.assertIs(clone.transport_identity, adapter.transport_identity)
                self.assertIs(clone._session, adapter._session)
                self.assertEqual(clone._api_key, adapter._api_key)
                self.assertEqual(clone.config, replace(adapter.config, model="fallback-model"))

    def test_fallback_clone_may_only_change_model(self) -> None:
        planner = RecordingAdapter(
            model_config(role=ModelRole.PLANNER),
            [ModelResult(valid_output(ModelRole.PLANNER, WorkflowNode.B), 1, 1, 1, None)],
        )
        operator = UnsafeFallbackAdapter(
            model_config(role=ModelRole.OPERATOR, fallback_model="operator-fallback"),
            [ModelTransportError("down"), ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
        )
        router = ModelRouter(planner, operator, store=RecordingStore(), run_id="run-1")
        with self.assertRaises(ModelError):
            router.invoke(ModelRequest(ModelRole.OPERATOR, WorkflowNode.B, "Execute", {}))
        self.assertEqual([model for model, _ in operator.invocations], ["operator-model"])

    def test_fallback_clone_must_keep_exact_adapter_type(self) -> None:
        planner = RecordingAdapter(
            model_config(role=ModelRole.PLANNER),
            [ModelResult(valid_output(ModelRole.PLANNER, WorkflowNode.B), 1, 1, 1, None)],
        )
        operator = CrossTypeFallbackAdapter(
            model_config(role=ModelRole.OPERATOR, fallback_model="operator-fallback"),
            [ModelTransportError("down"), ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
        )
        router = ModelRouter(planner, operator, store=RecordingStore(), run_id="run-1")
        with self.assertRaises(ModelError):
            router.invoke(ModelRequest(ModelRole.OPERATOR, WorkflowNode.B, "Execute", {}))
        self.assertEqual([model for model, _ in operator.invocations], ["operator-model"])

    def test_fallback_clone_must_preserve_opaque_transport_identity(self) -> None:
        planner = RecordingAdapter(
            model_config(role=ModelRole.PLANNER),
            [ModelResult(valid_output(ModelRole.PLANNER, WorkflowNode.B), 1, 1, 1, None)],
        )
        operator = ChangedIdentityFallbackAdapter(
            model_config(role=ModelRole.OPERATOR, fallback_model="operator-fallback"),
            [ModelTransportError("down"), ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
        )
        store = RecordingStore()
        router = ModelRouter(planner, operator, store=store, run_id="run-1")
        with self.assertRaises(ModelError) as raised:
            router.invoke(ModelRequest(ModelRole.OPERATOR, WorkflowNode.B, "Execute", {}))
        self.assertEqual([model for model, _ in operator.invocations], ["operator-model"])
        self.assertEqual(len(store.calls), 1)
        self.assertNotIn(FAKE_SECRET, str(raised.exception))
        self.assertNotIn("models.example.test", str(raised.exception))

    def test_fallback_identity_getter_failure_is_controlled_and_does_not_invoke_clone(self) -> None:
        planner = RecordingAdapter(
            model_config(role=ModelRole.PLANNER),
            [ModelResult(valid_output(ModelRole.PLANNER, WorkflowNode.B), 1, 1, 1, None)],
        )
        operator = ExplosiveIdentityFallbackAdapter(
            model_config(role=ModelRole.OPERATOR, fallback_model="operator-fallback"),
            [ModelTransportError("down"), ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
        )
        store = RecordingStore()
        router = ModelRouter(planner, operator, store=store, run_id="run-1")
        with self.assertRaises(ModelError) as raised:
            router.invoke(ModelRequest(ModelRole.OPERATOR, WorkflowNode.B, "Execute", {}))
        self.assertEqual([model for model, _ in operator.invocations], ["operator-model"])
        self.assertEqual(len(store.calls), 1)
        self.assertNotIn(FAKE_SECRET, str(raised.exception))

    def test_fallback_clone_config_getter_failure_is_controlled(self) -> None:
        planner = RecordingAdapter(
            model_config(role=ModelRole.PLANNER),
            [ModelResult(valid_output(ModelRole.PLANNER, WorkflowNode.B), 1, 1, 1, None)],
        )
        operator = ExplosiveCloneConfigAdapter(
            model_config(role=ModelRole.OPERATOR, fallback_model="operator-fallback"),
            [ModelTransportError("down"), ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
        )
        store = RecordingStore()
        router = ModelRouter(planner, operator, store=store, run_id="run-1")
        with self.assertRaises(ModelError) as raised:
            router.invoke(ModelRequest(ModelRole.OPERATOR, WorkflowNode.B, "Execute", {}))
        self.assertEqual([model for model, _ in operator.invocations], ["operator-model"])
        self.assertEqual(len(store.calls), 1)
        self.assertNotIn(FAKE_SECRET, str(raised.exception))


class RouterStoreIntegrationTests(unittest.TestCase):
    def test_router_persists_usage_to_agent_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(f"{tmp}/agent.sqlite3")
            store.initialize()
            store.create_run("run-1", RunConfig(scope_mode=ScopeMode.AUTO))
            planner = RecordingAdapter(
                model_config(role=ModelRole.PLANNER),
                [ModelResult(valid_output(ModelRole.PLANNER, WorkflowNode.K), 10, 20, 12, "p")],
            )
            operator = RecordingAdapter(
                model_config(role=ModelRole.OPERATOR),
                [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.K), 1, 1, 1, "o")],
            )
            router = ModelRouter(planner, operator, store=store, run_id="run-1")
            router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.K, "Diagnose", {}))

            self.assertEqual(
                store.usage_summary("run-1")["planner"],
                {
                    "calls": 1,
                    "input_tokens": 10,
                    "output_tokens": 20,
                    "cost_usd": 0.0001,
                    "latency_ms": 12.0,
                    "failures": 0,
                    "fallbacks": 0,
                },
            )

    def test_unpersistable_usage_still_creates_a_real_failure_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(f"{tmp}/agent.sqlite3")
            store.initialize()
            store.create_run("run-1", RunConfig(scope_mode=ScopeMode.AUTO))
            huge_tokens = 10**1000
            planner = RecordingAdapter(
                replace(
                    model_config(role=ModelRole.PLANNER),
                    input_cost_per_million=1e308,
                    output_cost_per_million=1e308,
                ),
                [
                    ModelResult(
                        valid_output(ModelRole.PLANNER, WorkflowNode.B),
                        huge_tokens,
                        huge_tokens,
                        1,
                        "huge",
                    )
                ],
            )
            operator = RecordingAdapter(
                model_config(role=ModelRole.OPERATOR),
                [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
            )
            router = ModelRouter(planner, operator, store=store, run_id="run-1")
            with self.assertRaises(ModelPersistenceError):
                router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {}))

            summary = store.usage_summary("run-1")["planner"]
            self.assertEqual(summary["calls"], 1)
            self.assertEqual(summary["failures"], 1)
            self.assertEqual(summary["input_tokens"], 0)
            self.assertEqual(summary["output_tokens"], 0)

    def test_combined_unpersistable_usage_and_latency_creates_real_failure_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(f"{tmp}/agent.sqlite3")
            store.initialize()
            store.create_run("run-1", RunConfig(scope_mode=ScopeMode.AUTO))
            overflow = 10**1000
            planner = RecordingAdapter(
                model_config(role=ModelRole.PLANNER),
                [
                    ModelResult(
                        valid_output(ModelRole.PLANNER, WorkflowNode.B),
                        overflow,
                        overflow,
                        overflow,
                        "combined-overflow",
                    )
                ],
            )
            operator = RecordingAdapter(
                model_config(role=ModelRole.OPERATOR),
                [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
            )
            router = ModelRouter(planner, operator, store=store, run_id="run-1")
            with self.assertRaises(ModelPersistenceError) as raised:
                router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {}))
            self.assertNotIn(str(overflow), str(raised.exception))
            summary = store.usage_summary("run-1")["planner"]
            self.assertEqual(summary["calls"], 1)
            self.assertEqual(summary["failures"], 1)
            self.assertEqual(summary["input_tokens"], 0)
            self.assertEqual(summary["output_tokens"], 0)
            self.assertEqual(summary["cost_usd"], 0.0)
            self.assertEqual(summary["latency_ms"], 0.0)

    def test_extreme_finite_cost_persists_to_agent_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(f"{tmp}/agent.sqlite3")
            store.initialize()
            store.create_run("run-1", RunConfig(scope_mode=ScopeMode.AUTO))
            planner = RecordingAdapter(
                replace(
                    model_config(role=ModelRole.PLANNER),
                    input_cost_per_million=1e308,
                    output_cost_per_million=1e308,
                ),
                [ModelResult(valid_output(ModelRole.PLANNER, WorkflowNode.B), 1, 1, 4, "cost")],
            )
            operator = RecordingAdapter(
                model_config(role=ModelRole.OPERATOR),
                [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
            )
            router = ModelRouter(planner, operator, store=store, run_id="run-1")
            router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {}))
            summary = store.usage_summary("run-1")["planner"]
            self.assertEqual(summary["calls"], 1)
            self.assertEqual(summary["failures"], 0)
            self.assertTrue(isfinite(summary["cost_usd"]))
            self.assertAlmostEqual(summary["cost_usd"], 2e302)

    def test_unrepresentable_cost_creates_real_failure_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(f"{tmp}/agent.sqlite3")
            store.initialize()
            store.create_run("run-1", RunConfig(scope_mode=ScopeMode.AUTO))
            tokens = 1_000_000
            planner = RecordingAdapter(
                replace(
                    model_config(role=ModelRole.PLANNER),
                    input_cost_per_million=1e308,
                    output_cost_per_million=1e308,
                ),
                [
                    ModelResult(
                        valid_output(ModelRole.PLANNER, WorkflowNode.B),
                        tokens,
                        tokens,
                        4,
                        "cost-overflow",
                    )
                ],
            )
            operator = RecordingAdapter(
                model_config(role=ModelRole.OPERATOR),
                [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
            )
            router = ModelRouter(planner, operator, store=store, run_id="run-1")
            with self.assertRaises(ModelPersistenceError):
                router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {}))
            summary = store.usage_summary("run-1")["planner"]
            self.assertEqual(summary["calls"], 1)
            self.assertEqual(summary["failures"], 1)
            self.assertEqual(summary["input_tokens"], tokens)
            self.assertEqual(summary["output_tokens"], tokens)
            self.assertEqual(summary["cost_usd"], 0.0)
            self.assertEqual(summary["latency_ms"], 4.0)

    def test_positive_cost_underflow_creates_real_failure_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(f"{tmp}/agent.sqlite3")
            store.initialize()
            store.create_run("run-1", RunConfig(scope_mode=ScopeMode.AUTO))
            planner = RecordingAdapter(
                replace(
                    model_config(role=ModelRole.PLANNER),
                    input_cost_per_million=5e-324,
                    output_cost_per_million=5e-324,
                ),
                [ModelResult(valid_output(ModelRole.PLANNER, WorkflowNode.B), 1, 1, 4, "cost-underflow")],
            )
            operator = RecordingAdapter(
                model_config(role=ModelRole.OPERATOR),
                [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
            )
            router = ModelRouter(planner, operator, store=store, run_id="run-1")
            with self.assertRaises(ModelPersistenceError):
                router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {}))
            summary = store.usage_summary("run-1")["planner"]
            self.assertEqual(summary["calls"], 1)
            self.assertEqual(summary["failures"], 1)
            self.assertEqual(summary["input_tokens"], 1)
            self.assertEqual(summary["output_tokens"], 1)
            self.assertEqual(summary["cost_usd"], 0.0)

    def test_unpersistable_latency_creates_real_failure_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(f"{tmp}/agent.sqlite3")
            store.initialize()
            store.create_run("run-1", RunConfig(scope_mode=ScopeMode.AUTO))
            planner = RecordingAdapter(
                model_config(role=ModelRole.PLANNER),
                [
                    ModelResult(
                        valid_output(ModelRole.PLANNER, WorkflowNode.B),
                        3,
                        2,
                        10**1000,
                        "latency-overflow",
                    )
                ],
            )
            operator = RecordingAdapter(
                model_config(role=ModelRole.OPERATOR),
                [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
            )
            router = ModelRouter(planner, operator, store=store, run_id="run-1")
            with self.assertRaises(ModelPersistenceError):
                router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {}))
            summary = store.usage_summary("run-1")["planner"]
            self.assertEqual(summary["calls"], 1)
            self.assertEqual(summary["failures"], 1)
            self.assertEqual(summary["input_tokens"], 3)
            self.assertEqual(summary["output_tokens"], 2)
            self.assertAlmostEqual(summary["cost_usd"], 0.000014)
            self.assertEqual(summary["latency_ms"], 0.0)

    def test_failure_metadata_unpersistable_latency_still_records_real_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(f"{tmp}/agent.sqlite3")
            store.initialize()
            store.create_run("run-1", RunConfig(scope_mode=ScopeMode.AUTO))
            error = ModelTransportError("down")
            error.model_input_tokens = 3
            error.model_output_tokens = 2
            error.model_latency_ms = 10**1000
            error.model_provider_request_id = "latency-failure"
            planner = RecordingAdapter(model_config(role=ModelRole.PLANNER), [error])
            operator = RecordingAdapter(
                model_config(role=ModelRole.OPERATOR),
                [ModelResult(valid_output(ModelRole.OPERATOR, WorkflowNode.B), 1, 1, 1, None)],
            )
            router = ModelRouter(planner, operator, store=store, run_id="run-1")
            with self.assertRaises(ModelTransportError):
                router.invoke(ModelRequest(ModelRole.PLANNER, WorkflowNode.B, "Plan", {}))
            summary = store.usage_summary("run-1")["planner"]
            self.assertEqual(summary["calls"], 1)
            self.assertEqual(summary["failures"], 1)
            self.assertEqual(summary["input_tokens"], 3)
            self.assertEqual(summary["output_tokens"], 2)
            self.assertAlmostEqual(summary["cost_usd"], 0.000014)
            self.assertEqual(summary["latency_ms"], 0.0)


if __name__ == "__main__":
    unittest.main()
