from __future__ import annotations

import argparse
import unittest

from wqb_cli.cli import build_parser
from wqb_cli.core.plugins import PluginLoadError, register_plugins
from wqb_cli.sdk import PluginContext


class DemoPlugin:
    name = "demo-plugin"

    def register(self, subparsers: object) -> argparse.ArgumentParser:
        parser = subparsers.add_parser(self.name)
        parser.add_argument("--value", default="ok")
        return parser

    def handle(self, args: argparse.Namespace, context: PluginContext) -> int:
        return 0


class InvalidPlugin:
    name = ""


class PluginTests(unittest.TestCase):
    def test_builtin_sqlitesimu_plugin_is_registered(self) -> None:
        args = build_parser().parse_args(["sqlitesimu", "status"])

        self.assertEqual(args._wqb_plugin.name, "sqlitesimu")

    def test_sqlitesimu_exposes_template_workflow_commands(self) -> None:
        parser = build_parser()

        cancel = parser.parse_args(
            ["sqlitesimu", "cancel", "run-1", "--force-active-lease"]
        )
        validate = parser.parse_args(["sqlitesimu", "template-validate", "manifest.json"])
        report = parser.parse_args(
            [
                "sqlitesimu",
                "template-report",
                "export.json",
                "--markdown-output",
                "report.md",
            ]
        )

        self.assertEqual(cancel.sqlitesimu_command, "cancel")
        self.assertTrue(cancel.force_active_lease)
        self.assertEqual(validate.sqlitesimu_command, "template-validate")
        self.assertEqual(report.sqlitesimu_command, "template-report")
        self.assertEqual(report.markdown_output, "report.md")

    def test_parser_binds_plugin_instance(self) -> None:
        plugin = DemoPlugin()
        parser = build_parser(plugins=[plugin])

        args = parser.parse_args([plugin.name, "--value", "demo"])

        self.assertIs(args._wqb_plugin, plugin)
        self.assertEqual(args.value, "demo")

    def test_duplicate_plugin_names_are_rejected(self) -> None:
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")

        with self.assertRaisesRegex(PluginLoadError, "Duplicate plugin name"):
            register_plugins(subparsers, [DemoPlugin(), DemoPlugin()])

    def test_invalid_plugin_contract_is_rejected(self) -> None:
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")

        with self.assertRaisesRegex(PluginLoadError, "non-empty string name"):
            register_plugins(subparsers, [InvalidPlugin()])


if __name__ == "__main__":
    unittest.main()
