from __future__ import annotations

import re
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
        self.assertEqual(package_version, "0.6.3")

        for readme_name in ("README.md", "README_CN.md"):
            readme = (REPO_ROOT / readme_name).read_text(encoding="utf-8")
            self.assertIn(f'version = "{package_version}"', readme)
            self.assertIn("https://github.com/untuitivist/wqb_cli/releases", readme)

        changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertRegex(changelog, rf"(?m)^## {re.escape(package_version)} - \d{{4}}-\d{{2}}-\d{{2}}$")


if __name__ == "__main__":
    unittest.main()
