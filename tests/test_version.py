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
        self.assertEqual(package_version, "0.3.2")


if __name__ == "__main__":
    unittest.main()
