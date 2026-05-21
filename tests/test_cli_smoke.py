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
    def test_top_level_help_smoke(self) -> None:
        result = run_wqb("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("shortcut", result.stdout)
        self.assertIn("docs", result.stdout)

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

    def test_shortcut_simulate_requires_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = Path(tmp) / "sim.json"
            payload.write_text(
                json.dumps(
                    {
                        "type": "REGULAR",
                        "settings": {
                            "instrumentType": "EQUITY",
                            "region": "USA",
                            "universe": "TOP3000",
                            "delay": 1,
                            "decay": 1,
                            "neutralization": "SUBINDUSTRY",
                            "truncation": 0.08,
                            "pasteurization": "ON",
                            "unitHandling": "VERIFY",
                            "nanHandling": "OFF",
                            "language": "FASTEXPR",
                            "visualization": False,
                        },
                        "regular": "close",
                    }
                ),
                encoding="utf-8",
            )
            result = run_wqb("shortcut", "simulate", "--input", str(payload))
            self.assertEqual(result.returncode, 1)
            body = json.loads(result.stdout)
            self.assertEqual(body["create"]["reason"], "mutating_method_requires_execute")

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

    def test_alpha_list_help_includes_adjacent_wqb_sdk_filters(self) -> None:
        result = run_wqb("alpha", "list", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--settings-neutralization", result.stdout)
        self.assertIn("--is-sharpe", result.stdout)
        self.assertIn("--os-is-sharpe-ratio", result.stdout)

    def test_data_fields_help_accepts_extra_query_params(self) -> None:
        result = run_wqb("data", "fields", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--coverage", result.stdout)
        self.assertIn("--alpha-count", result.stdout)
        self.assertIn("--order", result.stdout)
        self.assertIn("--param", result.stdout)


if __name__ == "__main__":
    unittest.main()
