from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_wqb(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    package_parent = str(REPO_ROOT.parent)
    env["PYTHONPATH"] = package_parent + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, "-m", "wqb_cli", *args],
        cwd=REPO_ROOT.parent,
        env=env,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )


class CliSmokeTests(unittest.TestCase):
    def test_upgrade_help_is_native_and_invalid_version_is_offline_json(self) -> None:
        help_result = run_wqb("upgrade", "--help")
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("--allow-downgrade", help_result.stdout)
        result = run_wqb("upgrade", "--version", "../master", "--check")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["reason"], "invalid_version")

    def test_upgrade_status_is_readable_offline_without_locking_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            receipt = Path(temporary) / "result.json"
            expected = {"ok": True, "status": "updated", "installed": True}
            receipt.write_text(json.dumps(expected), encoding="utf-8")
            result = run_wqb("upgrade", "--status", str(receipt))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), expected)

    def test_api_output_can_be_saved_without_shell_redirection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            for command in (("api", "stats"), ("api", "list"), ("api", "show", "/authentication")):
                target = Path(temporary) / "result.json"
                result = run_wqb(*command, "--output", str(target))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIsNotNone(json.loads(target.read_text(encoding="utf-8")))

    def test_top_level_help_smoke(self) -> None:
        result = run_wqb("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("shortcut", result.stdout)
        self.assertIn("docs", result.stdout)
        self.assertIn("help-center", result.stdout)

    def test_help_center_is_discoverable_and_dry_runs_without_auth(self) -> None:
        help_result = run_wqb("help-center", "--help")
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        for command in ("categories", "category", "sections", "section", "articles", "get", "search", "api"):
            self.assertIn(command, help_result.stdout)
        stats = run_wqb("help-center", "api", "stats")
        self.assertEqual(stats.returncode, 0, stats.stderr)
        self.assertEqual(json.loads(stats.stdout)["method_counts"], {"GET": 10})
        preview = run_wqb("help-center", "get", "38927747787031", "--dry-run")
        self.assertEqual(preview.returncode, 0, preview.stderr)
        payload = json.loads(preview.stdout)
        self.assertTrue(payload["dry_run"])
        self.assertFalse(payload["request"]["mutating"])
        docs = run_wqb("docs", "show", "help-center")
        self.assertEqual(docs.returncode, 0, docs.stderr)
        self.assertIn("Help Center", json.loads(docs.stdout)["text"])

    def test_config_init_get_set_with_temp_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            init = run_wqb("config", "--config", str(config_path), "init")
            self.assertEqual(init.returncode, 0, init.stderr)
            self.assertIs(json.loads(init.stdout)["ok"], True)

            set_result = run_wqb("config", "--config", str(config_path), "set", "defaults.region", "CHN")
            self.assertEqual(set_result.returncode, 0, set_result.stderr)
            self.assertEqual(json.loads(set_result.stdout)["value"], "CHN")

            get_result = run_wqb("config", "--config", str(config_path), "get", "defaults.region")
            self.assertEqual(get_result.returncode, 0, get_result.stderr)
            self.assertEqual(json.loads(get_result.stdout)["value"], "CHN")

    def test_docs_list_smoke(self) -> None:
        result = run_wqb("docs", "list")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        nodes = {item["node"] for item in payload["nodes"]}
        self.assertIn("shortcut", nodes)
        self.assertIn("config", nodes)

    def test_docs_show_accepts_node_name(self) -> None:
        result = run_wqb("docs", "show", "alpha/submit")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIs(payload["ok"], True)
        self.assertIn("alpha submit", payload["text"])

    def test_shortcut_simulate_help_has_no_execute_gate(self) -> None:
        result = run_wqb("shortcut", "simulate", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("--execute", result.stdout)
        self.assertNotIn("--wait", result.stdout)

    def test_simu_create_help_waits_by_default(self) -> None:
        result = run_wqb("simu", "create", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--max-wait-seconds", result.stdout)

    def test_legacy_sim_command_is_rejected(self) -> None:
        result = run_wqb("sim", "options")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("invalid choice: 'sim'", result.stderr)

    def test_scope_files_smoke(self) -> None:
        result = run_wqb("scope", "files")
        self.assertEqual(result.returncode, 0, result.stderr)
        body = json.loads(result.stdout)
        self.assertIs(body["ok"], True)
        self.assertIn("info_data", body)

    def test_scope_help_includes_pickle_commands(self) -> None:
        result = run_wqb("scope", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("pickle-summary", result.stdout)
        self.assertIn("alpha-rows", result.stdout)

    def test_user_messages_help_includes_filters(self) -> None:
        result = run_wqb("user", "messages", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--order", result.stdout)
        self.assertIn("--type", result.stdout)

    def test_alpha_list_help_includes_submission_range_filters(self) -> None:
        result = run_wqb("alpha", "list", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--date-submitted-after", result.stdout)
        self.assertIn("--date-submitted-before", result.stdout)
        self.assertIn("--order", result.stdout)
        self.assertIn("--param", result.stdout)

    def test_alpha_waiting_commands_include_max_wait(self) -> None:
        for args in [
            ("alpha", "check", "--help"),
            ("alpha", "recordsets", "--help"),
            ("alpha", "correlation", "prod", "--help"),
            ("alpha", "performance-comparison", "--help"),
        ]:
            result = run_wqb(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--max-wait-seconds", result.stdout)

    def test_alpha_list_help_includes_adjacent_wqb_sdk_filters(self) -> None:
        result = run_wqb("alpha", "list", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--settings-neutralization", result.stdout)
        self.assertIn("--is-sharpe", result.stdout)
        self.assertIn("--os-is-sharpe-ratio", result.stdout)
        self.assertIn("-dateSubmitted", result.stdout)
        self.assertIn("-is.fitness", result.stdout)
        self.assertIn("SUBINDUSTRY", result.stdout)
        self.assertIn(">=1.58", result.stdout)
        self.assertIn(">=0.001", result.stdout)

    def test_data_fields_help_accepts_extra_query_params(self) -> None:
        result = run_wqb("data", "fields", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--coverage", result.stdout)
        self.assertIn("--alpha-count", result.stdout)
        self.assertIn("--order", result.stdout)
        self.assertIn("MATRIX", result.stdout)
        self.assertIn(">0.8", result.stdout)
        self.assertIn("-userCount", result.stdout)
        self.assertIn("--param", result.stdout)

    def test_data_datasets_help_includes_order_examples(self) -> None:
        result = run_wqb("data", "datasets", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("-valueScore", result.stdout)
        self.assertIn("-alphaCount", result.stdout)
        self.assertIn("model, analyst", result.stdout)
        self.assertIn("fundamental", result.stdout)
        self.assertIn(">=5", result.stdout)

    def test_competition_help_exposes_generic_resources_and_spc_submissions(self) -> None:
        result = run_wqb("competition", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for command in ["leaderboard", "guidelines", "faq", "spc"]:
            self.assertIn(command, result.stdout)

        leaderboard = run_wqb("competition", "leaderboard", "--help")
        self.assertEqual(leaderboard.returncode, 0, leaderboard.stderr)
        self.assertIn("--scope", leaderboard.stdout)
        self.assertIn("competition", leaderboard.stdout)
        self.assertIn("consultant", leaderboard.stdout)
        self.assertIn("--board-type", leaderboard.stdout)
        self.assertIn("--method", leaderboard.stdout)
        self.assertIn("--param", leaderboard.stdout)

        spc = run_wqb("competition", "spc", "--help")
        self.assertEqual(spc.returncode, 0, spc.stderr)
        for command in [
            "submissions",
            "submission-history",
            "submission-options",
            "create-submission",
            "update-submission",
        ]:
            self.assertIn(command, spc.stdout)

        create = run_wqb("competition", "spc", "create-submission", "--help")
        self.assertEqual(create.returncode, 0, create.stderr)
        self.assertIn("--input", create.stdout)
        self.assertIn("--json", create.stdout)

        update = run_wqb("competition", "spc", "update-submission", "--help")
        self.assertEqual(update.returncode, 0, update.stderr)
        self.assertIn("PUT", update.stdout)
        self.assertIn("PATCH", update.stdout)


if __name__ == "__main__":
    unittest.main()
