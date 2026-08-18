from __future__ import annotations

import unittest

from wqb_cli.sqlitesimu.manifest import parse_manifest
from wqb_cli.sqlitesimu.template_report import (
    build_template_report,
    calculation_hash,
    expression_hash,
    render_template_report_markdown,
    settings_hash,
    validate_template_manifest,
)


SETTINGS = {
    "instrumentType": "EQUITY",
    "region": "CHN",
    "universe": "TOP2000U",
    "delay": 1,
    "decay": 5,
    "neutralization": "INDUSTRY",
    "truncation": 0.08,
    "language": "FASTEXPR",
}

EXPRESSION = """# [Search Attention Persistence]
# [20260818] - [CHN search attention] - [epoch 2]
attention_matrix_variable = vec_avg(mobile_search_engagement_score);
template_LLM = ts_mean(attention_matrix_variable, 32);
template_LLM"""


class TemplateFormatTests(unittest.TestCase):
    def test_strict_template_manifest_accepts_the_notebook_format_with_lineage(self) -> None:
        manifest = parse_manifest(
            {
                "run": {"name": "template-format"},
                "candidates": [
                    {
                        "expression": EXPRESSION,
                        "settings": SETTINGS,
                        **template_metadata(EXPRESSION),
                    }
                ],
            }
        )

        result = validate_template_manifest(manifest)

        self.assertTrue(result["ok"])
        self.assertEqual(result["template_count"], 1)
        self.assertEqual(result["violation_count"], 0)

    def test_template_manifest_rejects_duplicate_variables_and_stale_hashes(self) -> None:
        invalid = EXPRESSION.replace(
            "template_LLM = ts_mean(attention_matrix_variable, 32);",
            "attention_matrix_variable = ts_mean(attention_matrix_variable, 32);",
        )
        metadata = template_metadata(EXPRESSION)
        manifest = parse_manifest(
            [{"expression": invalid, "settings": SETTINGS, **metadata}]
        )

        result = validate_template_manifest(manifest)
        codes = {row["code"] for row in result["violations"]}

        self.assertFalse(result["ok"])
        self.assertIn("duplicate_variable", codes)
        self.assertIn("template_assignment", codes)
        self.assertIn("expression_hash_mismatch", codes)

    def test_template_manifest_rejects_unresolved_placeholders(self) -> None:
        invalid = EXPRESSION.replace("32", "{price_window}")
        metadata = template_metadata(invalid)
        manifest = parse_manifest(
            [{"expression": invalid, "settings": SETTINGS, **metadata}]
        )

        result = validate_template_manifest(manifest)

        self.assertFalse(result["verdict"])
        self.assertIn(
            "unresolved_placeholder",
            {row["code"] for row in result["violations"]},
        )

    def test_template_manifest_rejects_settings_drift_and_duplicate_calculation(self) -> None:
        second_expression = EXPRESSION.replace(
            "# [Search Attention Persistence]",
            "# [Search Attention Persistence Variant]",
        )
        second_metadata = template_metadata(second_expression)
        second_metadata["template_name"] = "Search Attention Persistence Variant"
        second_metadata["template_family_id"] = "variant_family"
        second_metadata["workflow_run_id"] = "workflow-run-2"
        manifest = parse_manifest(
            {
                "candidates": [
                    {
                        "expression": EXPRESSION,
                        "settings": SETTINGS,
                        **template_metadata(EXPRESSION),
                    },
                    {
                        "expression": second_expression,
                        "settings": {**SETTINGS, "decay": 7},
                        **second_metadata,
                    },
                ]
            }
        )

        result = validate_template_manifest(manifest)
        codes = {row["code"] for row in result["violations"]}

        self.assertIn("settings_drift", codes)
        self.assertIn("workflow_run_id_mismatch", codes)

        second_metadata["workflow_run_id"] = "workflow-run-1"
        second_metadata["settings_hash"] = settings_hash(SETTINGS)
        duplicate = parse_manifest(
            {
                "candidates": [
                    {
                        "expression": EXPRESSION,
                        "settings": SETTINGS,
                        **template_metadata(EXPRESSION),
                    },
                    {
                        "expression": second_expression,
                        "settings": SETTINGS,
                        **second_metadata,
                    },
                ]
            }
        )
        duplicate_result = validate_template_manifest(duplicate)
        self.assertIn(
            "duplicate_calculation_identity",
            {row["code"] for row in duplicate_result["violations"]},
        )


class TemplateReportTests(unittest.TestCase):
    def test_report_reproduces_three_sections_and_uses_signed_maxima(self) -> None:
        payload = terminal_export()

        report = build_template_report(payload)
        sections = report["sections"]
        family_a = sections["template_alphas_performance_each_template"][0]
        best = sections["template_alphas_best_performance_each_metric"][0]
        markdown = render_template_report_markdown(report)

        self.assertEqual(report["summary"]["assigned_count"], 3)
        self.assertEqual(family_a["metrics"]["sharpe"]["50%"], -0.75)
        self.assertEqual(best["metric"], "sharpe")
        self.assertEqual(best["alpha_id"], "alpha-positive")
        self.assertEqual(best["sharpe"], 0.5)
        self.assertIn("```template alphas performance each template", markdown)
        self.assertIn("```template alphas checks statistics", markdown)
        self.assertIn("```template alphas best performance each metric", markdown)
        self.assertIn("实验成果评估:", markdown)
        self.assertIn("关键发现:", markdown)
        self.assertIn("改进方向:", markdown)

    def test_report_keeps_error_checks_and_marks_cancelled_runs_ineligible(self) -> None:
        payload = terminal_export()
        payload["run"]["state"] = "CANCELLED"
        payload["experiments"][2]["state"] = "CANCELLED"

        report = build_template_report(payload)
        rows = report["sections"]["template_alphas_checks_statistics"]

        self.assertFalse(report["summary"]["analysis_eligible"])
        self.assertIn("run_state_cancelled", report["summary"]["ineligibility_reasons"])
        family_b = next(row for row in rows if row["template_name"] == "Family B")
        self.assertEqual(family_b["status_counts"]["ERROR"], 1)

    def test_report_rejects_non_terminal_exports(self) -> None:
        payload = terminal_export()
        payload["run"]["state"] = "RUNNING"

        with self.assertRaisesRegex(ValueError, "terminal run"):
            build_template_report(payload)

    def test_report_normalizes_legacy_simulation_request_state_names(self) -> None:
        payload = terminal_export()
        payload["run"]["state"] = "CANCELLED"
        payload["experiments"][0]["state"] = "SUBMIT_UNKNOWN"

        report = build_template_report(payload)

        self.assertEqual(report["summary"]["state_counts"]["SIMULATE_UNKNOWN"], 1)
        self.assertNotIn("SUBMIT_UNKNOWN", report["summary"]["state_counts"])


def template_metadata(expression: str) -> dict[str, object]:
    return {
        "template_format_version": 1,
        "workflow_run_id": "workflow-run-1",
        "template_family_id": "E2_01_search_attention_persistence",
        "template_version": 2,
        "template_name": "Search Attention Persistence",
        "template_name_zh": "搜索关注持续性",
        "template_logic_zh": "搜索关注在短期内具有持续性。",
        "template_epoch": 2,
        "family_ordinal": 1,
        "family_draw_index": 1,
        "mechanism_id": "search_attention",
        "field_roles": {"mobile_search_engagement_score": "attention"},
        "parameters": {"window": 32},
        "rng_seed": 20260818,
        "population_ordinal": 1,
        "expression_hash": expression_hash(expression),
        "calculation_hash": calculation_hash(expression),
        "settings_hash": settings_hash(SETTINGS),
        "single_mechanism": True,
    }


def terminal_export() -> dict[str, object]:
    metadata_a = {
        "template_family_id": "family_a",
        "template_version": 1,
        "template_name": "Family A",
        "template_name_zh": "模板甲",
        "template_logic_zh": "测试机制甲。",
        "template_epoch": 1,
        "family_ordinal": 1,
    }
    metadata_b = {
        "template_family_id": "family_b",
        "template_version": 1,
        "template_name": "Family B",
        "template_name_zh": "模板乙",
        "template_logic_zh": "测试机制乙。",
        "template_epoch": 1,
        "family_ordinal": 2,
    }
    return {
        "schema_version": 2,
        "database": "simulations.sqlite3",
        "run": {
            "run_id": "run-1",
            "state": "COMPLETED",
        },
        "experiments": [
            {
                "experiment_id": "exp-negative",
                "state": "READY",
                "metadata": metadata_a,
                "payload": {"regular": "rank(close)"},
            },
            {
                "experiment_id": "exp-positive",
                "state": "READY",
                "metadata": metadata_a,
                "payload": {"regular": "rank(volume)"},
            },
            {
                "experiment_id": "exp-b",
                "state": "READY",
                "metadata": metadata_b,
                "payload": {"regular": "rank(returns)"},
            },
        ],
        "results": [
            metric_row("exp-negative", "alpha-negative", metadata_a, -2.0, -0.8),
            metric_row("exp-positive", "alpha-positive", metadata_a, 0.5, 0.2),
            metric_row("exp-b", "alpha-b", metadata_b, 0.2, 0.1),
        ],
        "checks": [
            check_row("exp-negative", "alpha-negative", metadata_a, "FAIL"),
            check_row("exp-positive", "alpha-positive", metadata_a, "FAIL"),
            check_row("exp-b", "alpha-b", metadata_b, "ERROR"),
        ],
    }


def metric_row(
    experiment_id: str,
    alpha_id: str,
    metadata: dict[str, object],
    sharpe: float,
    fitness: float,
) -> dict[str, object]:
    return {
        "experiment_id": experiment_id,
        "alpha_id": alpha_id,
        "metadata": metadata,
        "regular_code": "rank(close)",
        "sharpe": sharpe,
        "fitness": fitness,
        "turnover": 0.1,
        "margin": 0.001,
        "returns_value": 0.02,
        "drawdown": 0.03,
        "pnl": 100.0,
        "long_count": 100,
        "short_count": 90,
    }


def check_row(
    experiment_id: str,
    alpha_id: str,
    metadata: dict[str, object],
    result: str,
) -> dict[str, object]:
    return {
        "experiment_id": experiment_id,
        "alpha_id": alpha_id,
        "metadata": metadata,
        "name": "LOW_SHARPE",
        "result": result,
        "value": 0.5,
        "limit": 1.0,
    }


if __name__ == "__main__":
    unittest.main()
