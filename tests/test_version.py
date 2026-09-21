from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

import wqb_cli


REPO_ROOT = Path(__file__).resolve().parents[1]


class VersionTests(unittest.TestCase):
    def test_runtime_version_matches_package_metadata(self) -> None:
        with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
            package_version = tomllib.load(handle)["project"]["version"]

        self.assertEqual(wqb_cli.__version__, package_version)
        self.assertEqual(package_version, "0.6.1")

        for readme_name in ("README.md", "README_CN.md"):
            readme = (REPO_ROOT / readme_name).read_text(encoding="utf-8")
            self.assertIn(f'version = "{package_version}"', readme)
            self.assertIn("https://github.com/untuitivist/wqb_cli/releases", readme)

        changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"## {package_version} - 2026-09-22", changelog)


if __name__ == "__main__":
    unittest.main()
