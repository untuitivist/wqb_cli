from __future__ import annotations

import unittest

from wqb_cli.agent.schemas import (
    MAX_SCHEMA_REPAIR_RETRIES,
    ModelRefusal,
    SchemaViolation,
    has_open_object_schema,
    parse_json_text,
    schema_for,
    validate_model_output,
)
from wqb_cli.agent.types import ModelRole, WorkflowNode


class AgentSchemaTests(unittest.TestCase):
    BASE = {
        "decision": "decide",
        "reasoning_summary": "Evidence supports this decision",
        "evidence_refs": ["artifact:a"],
        "confidence": 0.5,
    }

    PLANNER_PAYLOADS = {
        WorkflowNode.D: ("scope_decision", {}),
        WorkflowNode.F: ("evidence_requirements", {}),
        WorkflowNode.G: ("evidence_requirements", {}),
        WorkflowNode.H: ("research_plan", {}),
        WorkflowNode.I: ("candidate_plan", {}),
        WorkflowNode.K: (
            "diagnosis",
            {"failure_class": "PASS", "next_node": "L"},
        ),
        WorkflowNode.L: ("final_recommendation", {}),
    }

    SUPPORTED_NODES = {
        ModelRole.PLANNER: {
            WorkflowNode.B,
            WorkflowNode.D,
            WorkflowNode.F,
            WorkflowNode.G,
            WorkflowNode.H,
            WorkflowNode.I,
            WorkflowNode.K,
            WorkflowNode.L,
        },
        ModelRole.OPERATOR: {
            WorkflowNode.B,
            WorkflowNode.F,
            WorkflowNode.G,
            WorkflowNode.H,
            WorkflowNode.I,
            WorkflowNode.K,
            WorkflowNode.L,
        },
    }

    def valid_value(self, role: ModelRole, node: WorkflowNode) -> dict[str, object]:
        value: dict[str, object] = dict(self.BASE)
        if role is ModelRole.OPERATOR:
            value["task_result"] = {"status": "COMPLETED", "payload": {}}
        elif node in self.PLANNER_PAYLOADS:
            name, payload = self.PLANNER_PAYLOADS[node]
            value[name] = payload
        return value

    def test_supported_role_and_node_combinations_have_valid_schemas(self) -> None:
        for role, nodes in self.SUPPORTED_NODES.items():
            for node in nodes:
                with self.subTest(role=role, node=node):
                    schema = schema_for(role, node)
                    self.assertFalse(schema["additionalProperties"])
                    self.assertEqual(
                        validate_model_output(role, node, self.valid_value(role, node)),
                        self.valid_value(role, node),
                    )

    def test_unsupported_role_and_node_combinations_fail_closed(self) -> None:
        for role in ModelRole:
            unsupported = set(WorkflowNode) - self.SUPPORTED_NODES[role]
            for node in unsupported:
                for call in (
                    lambda: schema_for(role, node),
                    lambda: validate_model_output(
                        role, node, self.valid_value(role, node)
                    ),
                ):
                    with self.subTest(role=role, node=node, call=call):
                        with self.assertRaises(SchemaViolation) as caught:
                            call()
                        self.assertIn(role.value, str(caught.exception))
                        self.assertIn(node.value, str(caught.exception))

    def test_schema_for_returns_an_independent_copy(self) -> None:
        first = schema_for(ModelRole.PLANNER, WorkflowNode.K)
        first["properties"]["decision"]["minLength"] = 99

        second = schema_for(ModelRole.PLANNER, WorkflowNode.K)

        self.assertEqual(second["properties"]["decision"]["minLength"], 1)

    def test_open_object_detection_matches_supported_schema_matrix(self) -> None:
        for node in (WorkflowNode.B, WorkflowNode.K):
            with self.subTest(role=ModelRole.PLANNER, node=node):
                self.assertFalse(
                    has_open_object_schema(schema_for(ModelRole.PLANNER, node))
                )

        for node in (
            WorkflowNode.D,
            WorkflowNode.F,
            WorkflowNode.G,
            WorkflowNode.H,
            WorkflowNode.I,
            WorkflowNode.L,
        ):
            with self.subTest(role=ModelRole.PLANNER, node=node):
                self.assertTrue(
                    has_open_object_schema(schema_for(ModelRole.PLANNER, node))
                )

        for node in self.SUPPORTED_NODES[ModelRole.OPERATOR]:
            with self.subTest(role=ModelRole.OPERATOR, node=node):
                self.assertTrue(
                    has_open_object_schema(schema_for(ModelRole.OPERATOR, node))
                )

    def test_open_object_detection_recurses_through_schema_containers(self) -> None:
        open_schemas = (
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {"nested": {"type": "object"}},
            },
            {"type": "array", "items": {"type": "object"}},
            {"$defs": {"nullable": {"type": ["object", "null"]}}},
            {"anyOf": [{"type": "string"}, {"type": "object"}]},
        )
        for schema in open_schemas:
            with self.subTest(schema=schema):
                self.assertTrue(has_open_object_schema(schema))

        closed = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": ["object", "null"],
                        "additionalProperties": False,
                    },
                }
            },
            "anyOf": [{"type": "string"}, {"$ref": "#/$defs/closed"}],
            "$defs": {
                "closed": {"type": "object", "additionalProperties": False}
            },
        }
        self.assertFalse(has_open_object_schema(closed))
        self.assertFalse(has_open_object_schema(object()))

    def test_responses_reject_unknown_top_level_properties(self) -> None:
        for role in ModelRole:
            value = self.valid_value(role, WorkflowNode.K)
            value["budget"] = {"planner_calls": 100}
            with self.subTest(role=role):
                with self.assertRaisesRegex(SchemaViolation, "budget"):
                    validate_model_output(role, WorkflowNode.K, value)

    def test_schema_errors_do_not_echo_invalid_instance_values(self) -> None:
        fake_secret = "sk-fake-secret-value-should-never-be-echoed"
        invalid_cases = (
            ("confidence", fake_secret),
            (
                "diagnosis",
                {"failure_class": fake_secret, "next_node": "L"},
            ),
        )
        for field, invalid in invalid_cases:
            value = self.valid_value(ModelRole.PLANNER, WorkflowNode.K)
            value[field] = invalid
            with self.subTest(field=field):
                with self.assertRaises(SchemaViolation) as caught:
                    validate_model_output(ModelRole.PLANNER, WorkflowNode.K, value)
                message = str(caught.exception)
                self.assertIn(field, message)
                self.assertNotIn(fake_secret, message)

    def test_schema_errors_are_bounded_and_keep_safe_field_names(self) -> None:
        value = self.valid_value(ModelRole.PLANNER, WorkflowNode.K)
        fake_secret = "secret-instance-value"
        for index in range(200):
            value[f"unexpected_{index:03d}"] = fake_secret

        with self.assertRaises(SchemaViolation) as caught:
            validate_model_output(ModelRole.PLANNER, WorkflowNode.K, value)

        message = str(caught.exception)
        self.assertLessEqual(len(message), 1024)
        self.assertIn("unexpected properties", message)
        self.assertIn("unexpected_000", message)
        self.assertNotIn(fake_secret, message)

    def test_base_properties_are_required_and_bounded(self) -> None:
        invalid_values = {
            "decision": "",
            "reasoning_summary": "",
            "evidence_refs": [],
            "confidence": 1.01,
        }
        for field, invalid in invalid_values.items():
            value = self.valid_value(ModelRole.PLANNER, WorkflowNode.K)
            value[field] = invalid
            with self.subTest(field=field):
                with self.assertRaisesRegex(SchemaViolation, field):
                    validate_model_output(ModelRole.PLANNER, WorkflowNode.K, value)

        missing = self.valid_value(ModelRole.PLANNER, WorkflowNode.K)
        del missing["decision"]
        with self.assertRaisesRegex(SchemaViolation, "decision"):
            validate_model_output(ModelRole.PLANNER, WorkflowNode.K, missing)

    def test_base_properties_reject_wrong_json_types_and_lower_bound(self) -> None:
        invalid_values = {
            "decision": 1,
            "reasoning_summary": ["summary"],
            "evidence_refs": [""],
            "confidence": -0.01,
        }
        for field, invalid in invalid_values.items():
            value = self.valid_value(ModelRole.PLANNER, WorkflowNode.K)
            value[field] = invalid
            with self.subTest(field=field):
                with self.assertRaisesRegex(SchemaViolation, field):
                    validate_model_output(ModelRole.PLANNER, WorkflowNode.K, value)

        boolean_confidence = self.valid_value(ModelRole.PLANNER, WorkflowNode.K)
        boolean_confidence["confidence"] = True
        with self.assertRaisesRegex(SchemaViolation, "confidence"):
            validate_model_output(
                ModelRole.PLANNER, WorkflowNode.K, boolean_confidence
            )

    def test_nonblank_fields_reject_whitespace_only_strings(self) -> None:
        planner_cases = {
            "decision": " \t",
            "reasoning_summary": "\r\n",
            "evidence_refs": [" \n\t"],
        }
        for field, invalid in planner_cases.items():
            value = self.valid_value(ModelRole.PLANNER, WorkflowNode.K)
            value[field] = invalid
            with self.subTest(field=field):
                with self.assertRaisesRegex(SchemaViolation, field):
                    validate_model_output(ModelRole.PLANNER, WorkflowNode.K, value)

        operator = self.valid_value(ModelRole.OPERATOR, WorkflowNode.K)
        operator["task_result"] = {"status": "  ", "payload": {}}
        with self.assertRaisesRegex(SchemaViolation, "task_result.status"):
            validate_model_output(ModelRole.OPERATOR, WorkflowNode.K, operator)

    def test_confidence_rejects_non_finite_numbers(self) -> None:
        value = self.valid_value(ModelRole.PLANNER, WorkflowNode.K)
        value["confidence"] = float("nan")

        with self.assertRaisesRegex(SchemaViolation, "confidence"):
            validate_model_output(ModelRole.PLANNER, WorkflowNode.K, value)

    def test_each_planner_node_payload_is_required_and_must_be_an_object(self) -> None:
        for node, (payload_name, _) in self.PLANNER_PAYLOADS.items():
            missing = self.valid_value(ModelRole.PLANNER, node)
            del missing[payload_name]
            wrong_type = self.valid_value(ModelRole.PLANNER, node)
            wrong_type[payload_name] = []
            for value in (missing, wrong_type):
                with self.subTest(node=node, value=value):
                    with self.assertRaisesRegex(SchemaViolation, payload_name):
                        validate_model_output(ModelRole.PLANNER, node, value)

    def test_operator_task_result_has_an_exact_envelope(self) -> None:
        base = self.valid_value(ModelRole.OPERATOR, WorkflowNode.I)
        missing = dict(base)
        del missing["task_result"]
        with self.assertRaisesRegex(SchemaViolation, "task_result"):
            validate_model_output(ModelRole.OPERATOR, WorkflowNode.I, missing)

        invalid_results = (
            {},
            {"status": "", "payload": {}},
            {"status": "COMPLETED"},
            {"status": "COMPLETED", "payload": [], "route": "H"},
        )
        for task_result in invalid_results:
            value = dict(base)
            value["task_result"] = task_result
            with self.subTest(task_result=task_result):
                with self.assertRaises(SchemaViolation):
                    validate_model_output(ModelRole.OPERATOR, WorkflowNode.I, value)

    def test_diagnosis_rejects_unknown_or_additional_fields(self) -> None:
        invalid_diagnoses = (
            {"failure_class": "OTHER", "next_node": "I"},
            {"failure_class": "PASS", "next_node": "M"},
            {"failure_class": "PASS", "next_node": "L", "budget": 1},
        )
        for diagnosis in invalid_diagnoses:
            value = self.valid_value(ModelRole.PLANNER, WorkflowNode.K)
            value["diagnosis"] = diagnosis
            with self.subTest(diagnosis=diagnosis):
                with self.assertRaises(SchemaViolation):
                    validate_model_output(ModelRole.PLANNER, WorkflowNode.K, value)

    def test_validate_model_output_requires_an_exact_dict(self) -> None:
        class DictSubclass(dict[str, object]):
            pass

        value = DictSubclass(self.valid_value(ModelRole.PLANNER, WorkflowNode.K))
        with self.assertRaisesRegex(SchemaViolation, "JSON object"):
            validate_model_output(ModelRole.PLANNER, WorkflowNode.K, value)

    def test_validate_model_output_rejects_non_json_native_nested_values(self) -> None:
        class DictSubclass(dict[str, object]):
            pass

        class ListSubclass(list[object]):
            pass

        invalid_values = (
            object(),
            ("tuple",),
            {"set"},
            1 + 2j,
            float("nan"),
            float("inf"),
            float("-inf"),
            DictSubclass(),
            ListSubclass(),
        )
        for invalid in invalid_values:
            value = self.valid_value(ModelRole.PLANNER, WorkflowNode.I)
            value["candidate_plan"] = {"nested": invalid}
            with self.subTest(invalid_type=type(invalid).__name__):
                with self.assertRaisesRegex(SchemaViolation, "candidate_plan"):
                    validate_model_output(ModelRole.PLANNER, WorkflowNode.I, value)

    def test_validate_model_output_rejects_non_string_object_keys(self) -> None:
        value = self.valid_value(ModelRole.PLANNER, WorkflowNode.I)
        value["candidate_plan"] = {1: "not-json"}

        with self.assertRaisesRegex(SchemaViolation, "candidate_plan"):
            validate_model_output(ModelRole.PLANNER, WorkflowNode.I, value)

    def test_validate_model_output_rejects_circular_containers(self) -> None:
        circular_dict: dict[str, object] = {}
        circular_dict["self"] = circular_dict
        circular_list: list[object] = []
        circular_list.append(circular_list)

        for circular in (circular_dict, circular_list):
            value = self.valid_value(ModelRole.PLANNER, WorkflowNode.I)
            value["candidate_plan"] = {"nested": circular}
            with self.subTest(container_type=type(circular).__name__):
                with self.assertRaisesRegex(SchemaViolation, "circular"):
                    validate_model_output(ModelRole.PLANNER, WorkflowNode.I, value)

    def test_validate_model_output_returns_a_deep_snapshot(self) -> None:
        value = self.valid_value(ModelRole.PLANNER, WorkflowNode.I)
        value["candidate_plan"] = {
            "candidates": [{"expression": "rank(close)"}]
        }

        validated = validate_model_output(ModelRole.PLANNER, WorkflowNode.I, value)
        value["decision"] = "changed"
        value["evidence_refs"].append("artifact:later")  # type: ignore[union-attr]
        value["candidate_plan"]["candidates"][0]["expression"] = "changed"  # type: ignore[index]

        self.assertIsNot(validated, value)
        self.assertEqual(validated["decision"], "decide")
        self.assertEqual(validated["evidence_refs"], ["artifact:a"])
        self.assertEqual(
            validated["candidate_plan"],
            {"candidates": [{"expression": "rank(close)"}]},
        )

    def test_planner_k_accepts_only_bounded_route(self) -> None:
        value = {
            "decision": "revise_expression",
            "reasoning_summary": "Mechanism remains plausible",
            "evidence_refs": ["artifact:alpha-fail"],
            "confidence": 0.81,
            "diagnosis": {"failure_class": "EXPRESSION", "next_node": "I"},
        }

        validated = validate_model_output(ModelRole.PLANNER, WorkflowNode.K, value)

        self.assertEqual(validated["diagnosis"]["next_node"], "I")

    def test_planner_k_accepts_each_exact_diagnosis_route(self) -> None:
        routes = {
            "DATA_FIELD": "F",
            "EVIDENCE_GAP": "G",
            "ECONOMIC_MECHANISM": "H",
            "EXPRESSION": "I",
            "PASS": "L",
        }
        for failure_class, next_node in routes.items():
            value = self.valid_value(ModelRole.PLANNER, WorkflowNode.K)
            value["diagnosis"] = {
                "failure_class": failure_class,
                "next_node": next_node,
            }
            with self.subTest(failure_class=failure_class):
                self.assertEqual(
                    validate_model_output(ModelRole.PLANNER, WorkflowNode.K, value),
                    value,
                )

    def test_planner_k_rejects_mismatched_diagnosis_routes(self) -> None:
        value = self.valid_value(ModelRole.PLANNER, WorkflowNode.K)
        value["diagnosis"] = {
            "failure_class": "DATA_FIELD",
            "next_node": "I",
        }

        with self.assertRaisesRegex(SchemaViolation, "must route to F"):
            validate_model_output(ModelRole.PLANNER, WorkflowNode.K, value)

    def test_schema_api_requires_exact_role_and_node_enums(self) -> None:
        invalid_calls = (
            lambda: schema_for("planner", WorkflowNode.K),
            lambda: schema_for(ModelRole.PLANNER, "K"),
            lambda: validate_model_output("planner", WorkflowNode.K, {}),
            lambda: validate_model_output(ModelRole.PLANNER, "K", {}),
        )
        for call in invalid_calls:
            with self.subTest(call=call):
                with self.assertRaises(TypeError):
                    call()  # type: ignore[misc]

    def test_parse_json_text_accepts_only_a_pure_json_object(self) -> None:
        self.assertEqual(
            parse_json_text(' \n {"decision": "choose", "confidence": 1} \t'),
            {"decision": "choose", "confidence": 1},
        )

    def test_parse_json_text_rejects_non_object_json(self) -> None:
        for text in ('[1, 2]', '"answer"', "null", "true", "3"):
            with self.subTest(text=text):
                with self.assertRaisesRegex(SchemaViolation, "JSON object"):
                    parse_json_text(text)

    def test_parse_json_text_does_not_extract_prose_or_markdown_fences(self) -> None:
        invalid = (
            'Result: {"decision": "choose"}',
            '```json\n{"decision": "choose"}\n```',
            '{"decision": "choose"}\nThis is why.',
        )
        for text in invalid:
            with self.subTest(text=text):
                with self.assertRaisesRegex(SchemaViolation, "valid JSON"):
                    parse_json_text(text)

    def test_parse_json_text_rejects_nonstandard_json_constants(self) -> None:
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                with self.assertRaisesRegex(SchemaViolation, "valid JSON"):
                    parse_json_text('{"confidence": ' + constant + "}")

    def test_parse_json_text_requires_text_and_surfaces_provider_refusal(self) -> None:
        with self.assertRaisesRegex(TypeError, "text"):
            parse_json_text(b"{}")  # type: ignore[arg-type]
        with self.assertRaisesRegex(ModelRefusal, "cannot provide"):
            parse_json_text("", refusal="I cannot provide that result")

    def test_schema_repair_retry_limit_is_bounded(self) -> None:
        self.assertEqual(MAX_SCHEMA_REPAIR_RETRIES, 2)

    def test_operator_cannot_return_route_or_budget(self) -> None:
        base = {
            "decision": "organized",
            "reasoning_summary": "Sorted metrics",
            "evidence_refs": ["artifact:sim-1"],
            "confidence": 0.9,
            "task_result": {"status": "COMPLETED", "payload": {}},
        }
        for key, extra in (
            ("next_node", "H"),
            ("route", "H"),
            ("budget", {"operator_calls": 100}),
        ):
            value = {**base, key: extra}
            with self.subTest(key=key):
                with self.assertRaisesRegex(SchemaViolation, key):
                    validate_model_output(ModelRole.OPERATOR, WorkflowNode.K, value)

    def test_all_referenced_evidence_is_required(self) -> None:
        value = {
            "decision": "choose",
            "reasoning_summary": "No source",
            "evidence_refs": [],
            "confidence": 0.7,
        }

        with self.assertRaisesRegex(SchemaViolation, "evidence_refs"):
            validate_model_output(ModelRole.PLANNER, WorkflowNode.D, value)


if __name__ == "__main__":
    unittest.main()
