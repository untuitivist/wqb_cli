from __future__ import annotations

import unittest

from wqb_cli.agent.expressions import (
    ExpressionViolation,
    fingerprint_expression,
    normalize_expression,
    validate_candidate,
)
from wqb_cli.agent.strategies import (
    materialize_strategy_templates,
    profile_research_strategy,
    strategy_catalog,
    validate_research_strategy,
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

    def test_left_deep_binary_expression_never_raises_raw_recursion_error(self) -> None:
        result = validate_candidate(
            self.candidate("+".join(["volume"] * 1000)),
            allowed_fields={"volume"},
            banned_fields=set(),
            operators={},
        )
        self.assertEqual(result.fields, ("volume",))
        self.assertEqual(result.operators, ())

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

    def test_original_candidate_snapshot_rejects_nonfinite_float(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ExpressionViolation, "finite"):
                    validate_candidate(
                        self.candidate("rank(volume)", settings={"value": value}),
                        allowed_fields={"volume"},
                        banned_fields=set(),
                        operators={"rank": {"arity": 1}},
                    )

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

    def test_research_strategy_rejects_cosmetic_only_and_operator_stacking(self) -> None:
        cosmetic = validate_candidate(
            self.candidate("rank(volume)"),
            allowed_fields={"volume"},
            banned_fields=set(),
            operators={"rank": {"arity": 1}},
        )
        with self.assertRaisesRegex(ExpressionViolation, "cosmetic-only"):
            validate_research_strategy(cosmetic)

        stacked = validate_candidate(
            self.candidate("ts_zscore(ts_rank(volume,22),63)"),
            allowed_fields={"volume"},
            banned_fields=set(),
            operators={"ts_rank": {"arity": 2}, "ts_zscore": {"arity": 2}},
        )
        with self.assertRaisesRegex(ExpressionViolation, "stacks"):
            validate_research_strategy(stacked)

    def test_research_strategy_profiles_meaningful_binary_relation(self) -> None:
        validated = validate_candidate(
            self.candidate("ts_corr(volume,close,63)"),
            allowed_fields={"volume", "close"},
            banned_fields=set(),
            operators={"ts_corr": {"arity": 3}},
        )
        profile = validate_research_strategy(validated)
        self.assertEqual(profile.template_id, "binary:ts_corr")
        self.assertEqual(profile.strategy_family, "relational")
        self.assertEqual(profile.field_ids, ("volume", "close"))

    def test_expression_allows_more_than_two_authorized_fields(self) -> None:
        validated = validate_candidate(
            self.candidate("add(add(volume,close),group)"),
            allowed_fields={"volume", "close", "group"},
            banned_fields=set(),
            operators={"add": {"arity": 2}},
        )

        profile = profile_research_strategy(validated)

        self.assertEqual(set(profile.field_ids), {"volume", "close", "group"})
        self.assertEqual(profile.template_type, "multivariate")

    def test_strategy_catalog_uses_only_live_operators_and_field_capacity(self) -> None:
        operators = {
            "ts_delta": {"arity": 2},
            "ts_corr": {"arity": 3},
            "ts_regression": {"arity": 3},
        }
        unary = strategy_catalog(operators, field_count=1)
        binary = strategy_catalog(operators, field_count=2)
        self.assertEqual([item["strategy_id"] for item in unary], ["change_delta"])
        self.assertEqual(
            [item["strategy_id"] for item in binary],
            ["change_delta", "relationship_correlation", "relationship_regression"],
        )

    def test_local_template_expansion_round_robins_strategy_families(self) -> None:
        candidates = materialize_strategy_templates(
            {
                "ts_delta": {"arity": 2},
                "ts_zscore": {"arity": 2},
                "days_from_last_change": {"arity": 1},
                "ts_corr": {"arity": 3},
                "ts_regression": {"arity": 3},
                "if_else": {"arity": 3},
                "ts_mean": {"arity": 2},
            },
            ["volume", "close"],
            limit=6,
        )

        self.assertEqual(
            [item["strategy_id"] for item in candidates],
            [
                "change_delta",
                "temporal_abnormality",
                "change_recency",
                "relationship_correlation",
                "relationship_regression",
                "conditional_regime",
            ],
        )

    def test_vector_field_requires_direct_vector_reducer(self) -> None:
        operators = {
            "ts_delta": {"arity": 2},
            "vec_avg": {"arity": 1},
        }
        with self.assertRaisesRegex(ExpressionViolation, "vec_\\*"):
            validate_candidate(
                self.candidate("ts_delta(volume,22)"),
                allowed_fields={"volume"},
                banned_fields=set(),
                operators=operators,
                field_types={"volume": "VECTOR"},
            )

        validated = validate_candidate(
            self.candidate("ts_delta(vec_avg(volume),22)"),
            allowed_fields={"volume"},
            banned_fields=set(),
            operators=operators,
            field_types={"volume": "VECTOR"},
        )

        self.assertEqual(validated.operators, ("ts_delta", "vec_avg"))

    def test_local_template_expansion_reduces_vector_fields(self) -> None:
        candidates = materialize_strategy_templates(
            {"ts_delta": {"arity": 2}, "vec_avg": {"arity": 1}},
            ["event_signal"],
            strategy_ids=["change_delta"],
            limit=1,
            field_types={"event_signal": "VECTOR"},
        )

        self.assertEqual(
            candidates[0]["expression"],
            "ts_delta(vec_avg(event_signal), 22)",
        )
        catalog = strategy_catalog(
            {"ts_delta": {"arity": 2}, "vec_avg": {"arity": 1}},
            field_count=1,
            field_types={"event_signal": "VECTOR"},
        )
        self.assertEqual(
            catalog[0]["required_operators"], ["ts_delta", "vec_avg"]
        )


if __name__ == "__main__":
    unittest.main()
