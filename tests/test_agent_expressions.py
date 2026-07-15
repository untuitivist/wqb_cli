from __future__ import annotations

import unittest

from wqb_cli.agent.expressions import (
    ExpressionViolation,
    fingerprint_expression,
    normalize_expression,
    validate_candidate,
)


class AgentExpressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.allowed_fields = {"volume", "close", "group"}
        self.operators = {
            "rank": {"arity": 1},
            "ts_mean": {"arity": 2},
            "ts_weighted_decay": {"arity": 1},
            "ts_quantile": {"arity": 3},
            "hump_decay": {"arity": 1},
            "group_mean": {"arity": 2},
            "ts_target_tvr_decay": {"arity": 1},
            "ts_target_tvr_hump": {"arity": 1},
            "ts_poly_regression": {"arity": 2},
        }

    def candidate(self, expression: str, **overrides: object) -> dict[str, object]:
        return {
            "expression": expression,
            "field_id": "volume",
            "single_mechanism": True,
            **overrides,
        }

    def test_whitespace_and_case_normalize_to_same_fingerprint(self) -> None:
        self.assertEqual(
            fingerprint_expression("TS_MEAN( volume , 20 )"),
            fingerprint_expression("ts_mean(volume,20)"),
        )

    def test_string_literal_case_is_preserved(self) -> None:
        self.assertNotEqual(
            fingerprint_expression("ts_quantile(volume,20,driver='Gaussian')"),
            fingerprint_expression("ts_quantile(volume,20,driver='gaussian')"),
        )

    def test_normalization_rejects_invalid_syntax(self) -> None:
        for expression in ("rank(volume$)", "rank('unterminated)", "rank(volume"):
            with self.subTest(expression=expression):
                with self.assertRaises(ExpressionViolation):
                    normalize_expression(expression)

    def test_normalization_rejects_significant_whitespace_between_tokens(self) -> None:
        for expression in ("a b", "1 2"):
            with self.subTest(expression=expression):
                with self.assertRaisesRegex(ExpressionViolation, "whitespace"):
                    normalize_expression(expression)

    def test_unknown_field_and_banned_field_are_rejected(self) -> None:
        candidate = self.candidate("rank(secret_field)", field_id="secret_field")
        with self.assertRaisesRegex(ExpressionViolation, "field"):
            validate_candidate(
                candidate,
                allowed_fields={"volume"},
                banned_fields={"secret_field"},
                operators={"rank": {"arity": 1}},
            )

    def test_required_operator_parameters_are_enforced(self) -> None:
        with self.assertRaisesRegex(ExpressionViolation, "k"):
            validate_candidate(
                self.candidate("ts_weighted_decay(volume)"),
                allowed_fields={"volume"},
                banned_fields=set(),
                operators={"ts_weighted_decay": {"arity": 1}},
            )

    def test_static_validation_returns_canonical_candidate(self) -> None:
        result = validate_candidate(
            self.candidate("TS_MEAN( volume , 2.0e1 )"),
            allowed_fields=self.allowed_fields,
            banned_fields=set(),
            operators=self.operators,
        )
        self.assertEqual(result.canonical_expression, "ts_mean(volume,20)")
        self.assertEqual(result.fields, ("volume",))
        self.assertEqual(result.operators, ("ts_mean",))
        self.assertEqual(result.original_candidate["expression"], "TS_MEAN( volume , 2.0e1 )")

    def test_named_argument_identifiers_are_not_fields(self) -> None:
        result = validate_candidate(
            self.candidate("ts_quantile(volume,20,driver='Gaussian')"),
            allowed_fields={"volume"},
            banned_fields=set(),
            operators={"ts_quantile": {"arity": 2}},
        )
        self.assertEqual(result.fields, ("volume",))

    def test_ts_quantile_driver_must_be_a_string_literal(self) -> None:
        with self.assertRaisesRegex(ExpressionViolation, "driver"):
            validate_candidate(
                self.candidate("ts_quantile(volume,20,driver=Gaussian)"),
                allowed_fields={"volume"},
                banned_fields=set(),
                operators={"ts_quantile": {"arity": 2}},
            )

    def test_unknown_named_argument_is_rejected_but_known_parameter_is_allowed(self) -> None:
        with self.assertRaisesRegex(ExpressionViolation, "named argument"):
            validate_candidate(
                self.candidate("rank(volume,evil=1)"),
                allowed_fields={"volume"},
                banned_fields=set(),
                operators={"rank": {"arity": 1}},
            )
        result = validate_candidate(
            self.candidate("ts_weighted_decay(volume,k=0.5)"),
            allowed_fields={"volume"},
            banned_fields=set(),
            operators={"ts_weighted_decay": {"arity": 1}},
        )
        self.assertEqual(result.operators, ("ts_weighted_decay",))

    def test_excessive_unary_operators_raise_expression_violation(self) -> None:
        with self.assertRaisesRegex(ExpressionViolation, "unary"):
            validate_candidate(
                self.candidate("rank(" + "-" * 1000 + "volume)"),
                allowed_fields={"volume"},
                banned_fields=set(),
                operators={"rank": {"arity": 1}},
            )

    def test_original_candidate_is_a_deep_immutable_snapshot(self) -> None:
        candidate = self.candidate("rank(volume)", settings={"window": [20]})
        result = validate_candidate(
            candidate,
            allowed_fields={"volume"},
            banned_fields=set(),
            operators={"rank": {"arity": 1}},
        )
        candidate["settings"]["window"].append(40)  # type: ignore[index]
        self.assertEqual(result.original_candidate["settings"]["window"], (20,))  # type: ignore[index]
        with self.assertRaises(TypeError):
            result.original_candidate["settings"] = {}  # type: ignore[index]

    def test_explicit_i_node_parameters_are_required(self) -> None:
        cases = (
            ("hump_decay(volume)", "p"),
            ("group_mean(volume,group)", "weight"),
            ("ts_target_tvr_decay(volume)", "lambda_min"),
            ("ts_target_tvr_hump(volume,lambda_min=0.1,lambda_max=0.3)", "target_tvr"),
            ("ts_poly_regression(volume,20)", "k"),
        )
        for expression, required in cases:
            with self.subTest(expression=expression):
                with self.assertRaisesRegex(ExpressionViolation, required):
                    validate_candidate(
                        self.candidate(expression),
                        allowed_fields=self.allowed_fields,
                        banned_fields=set(),
                        operators=self.operators,
                    )

    def test_arity_operator_and_candidate_constraints_fail_closed(self) -> None:
        cases = (
            (self.candidate("rank(volume,close)"), "arity"),
            (self.candidate("unknown(volume)"), "operator"),
            (self.candidate("rank(volume)", single_mechanism=False), "single_mechanism"),
            (self.candidate("rank(volume)+rank(close)+rank(group)+rank(volume)+rank(close)+rank(group)"), "operator"),
        )
        for candidate, message in cases:
            with self.subTest(candidate=candidate):
                with self.assertRaisesRegex(ExpressionViolation, message):
                    validate_candidate(
                        candidate,
                        allowed_fields=self.allowed_fields,
                        banned_fields=set(),
                        operators=self.operators,
                    )


if __name__ == "__main__":
    unittest.main()
