from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ..core.paths import LOCAL_ROOT
from ..sdk import PluginContext
from .db import SCHEMA_VERSION, SqliteStore
from .gateway import WqbApiGateway
from .manifest import load_manifest
from .models import RuntimePolicy
from .runtime import SqliteSimuRuntime
from .template_report import (
    build_template_report,
    render_template_report_markdown,
    validate_template_manifest,
)


DEFAULT_DATABASE_PATH = LOCAL_ROOT / "sqlitesimu" / "simulations.sqlite3"


class SqliteSimuPlugin:
    name = "sqlitesimu"

    def register(self, subparsers: Any) -> argparse.ArgumentParser:
        parser = subparsers.add_parser(
            self.name,
            help="Run durable, agent-independent simulation workflows",
        )
        commands = parser.add_subparsers(dest="sqlitesimu_command", required=True)

        init = commands.add_parser("init", help="Initialize the simulation database")
        _add_database_argument(init)
        init.add_argument("--output", help="Write the JSON result to a file")

        enqueue = commands.add_parser("enqueue", help="Validate and enqueue a manifest")
        enqueue.add_argument("input", help="Simulation manifest JSON path")
        _add_database_argument(enqueue)
        enqueue.add_argument("--output", help="Write the JSON result to a file")

        run = commands.add_parser("run", help="Enqueue a manifest and run it to completion")
        run.add_argument("input", help="Simulation manifest JSON path")
        _add_database_argument(run)
        _add_runtime_arguments(run)
        run.add_argument("--output", help="Write the final JSON result to a file")

        resume = commands.add_parser("resume", help="Resume an existing durable run")
        resume.add_argument("run_id")
        _add_database_argument(resume)
        _add_runtime_arguments(resume)
        resume.add_argument("--output", help="Write the final JSON result to a file")

        status = commands.add_parser("status", help="Inspect one run or recent runs")
        status.add_argument("run_id", nargs="?")
        status.add_argument("--limit", type=int, default=20)
        _add_database_argument(status)
        status.add_argument("--output", help="Write the JSON result to a file")

        cancel = commands.add_parser("cancel", help="Stop a durable run without deleting history")
        cancel.add_argument("run_id")
        cancel.add_argument("--reason", default="user_requested")
        cancel.add_argument(
            "--force-active-lease",
            action="store_true",
            help="Cancel despite an unexpired lease after independently verifying the worker is dead",
        )
        _add_database_argument(cancel)
        cancel.add_argument("--output", help="Write the JSON result to a file")

        export = commands.add_parser("export", help="Export normalized and legacy-ready results")
        export.add_argument("run_id")
        _add_database_argument(export)
        export.add_argument("--output", help="Write the JSON result to a file")

        validate = commands.add_parser(
            "template-validate",
            help="Validate the strict BatchSimu template and lineage format",
        )
        validate.add_argument("input", help="Simulation manifest JSON path")
        validate.add_argument("--output", help="Write the JSON result to a file")

        report = commands.add_parser(
            "template-report",
            help="Render the fixed template analysis format from a terminal run export",
        )
        report.add_argument("input", help="JSON path produced by sqlitesimu export")
        report.add_argument("--output", help="Write the normalized JSON report to a file")
        report.add_argument("--markdown-output", help="Write the three-section report to Markdown")
        return parser

    def handle(self, args: argparse.Namespace, context: PluginContext) -> int:
        command = args.sqlitesimu_command
        if command == "template-validate":
            payload = validate_template_manifest(load_manifest(args.input))
            context.write_json(payload, args.output)
            return 0 if payload["ok"] else 1
        if command == "template-report":
            export_payload = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
            payload = build_template_report(export_payload)
            if args.markdown_output:
                markdown_path = Path(args.markdown_output)
                markdown_path.parent.mkdir(parents=True, exist_ok=True)
                markdown_path.write_text(
                    render_template_report_markdown(payload),
                    encoding="utf-8",
                )
            context.write_json(payload, args.output)
            return 0

        store = SqliteStore(args.db)
        store.initialize()
        if command == "init":
            context.write_json(
                {
                    "ok": True,
                    "database": _database_name(store),
                    "schema_version": SCHEMA_VERSION,
                },
                args.output,
            )
            return 0
        if command == "enqueue":
            enqueued = store.enqueue(load_manifest(args.input))
            context.write_json(
                {"ok": True, "database": _database_name(store), **enqueued.as_dict()},
                args.output,
            )
            return 0
        if command == "run":
            enqueued = store.enqueue(load_manifest(args.input))
            summary = _run(store, context, enqueued.run_id, args)
            payload = {
                "ok": summary["state"] == "COMPLETED",
                "database": _database_name(store),
                "enqueue": enqueued.as_dict(),
                "run": summary,
            }
            context.write_json(payload, args.output)
            return _run_exit_code(summary)
        if command == "resume":
            summary = _run(store, context, args.run_id, args)
            payload = {
                "ok": summary["state"] == "COMPLETED",
                "database": _database_name(store),
                "run": summary,
            }
            context.write_json(payload, args.output)
            return _run_exit_code(summary)
        if command == "status":
            if args.limit < 1:
                raise ValueError("limit must be at least 1")
            if args.run_id:
                payload = {
                    "ok": True,
                    "database": _database_name(store),
                    "run": store.run_summary(args.run_id),
                }
            else:
                payload = {
                    "ok": True,
                    "database": _database_name(store),
                    "runs": store.list_runs(limit=args.limit),
                }
            context.write_json(payload, args.output)
            return 0
        if command == "cancel":
            summary = store.cancel_run(
                args.run_id,
                reason=args.reason,
                allow_active_lease=args.force_active_lease,
            )
            context.write_json(
                {
                    "ok": True,
                    "database": _database_name(store),
                    "run": summary,
                },
                args.output,
            )
            return 0
        if command == "export":
            payload = {
                "ok": True,
                "schema_version": SCHEMA_VERSION,
                "database": _database_name(store),
                "run": store.run_summary(args.run_id),
                "experiments": store.experiment_results(args.run_id),
                "results": store.analysis_results(args.run_id),
                "checks": store.check_results(args.run_id),
                "simued_alpha_is_pnl": store.compatibility_results(args.run_id),
            }
            context.write_json(payload, args.output)
            return 0
        raise AssertionError(command)


def _add_database_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DATABASE_PATH),
        help=f"SQLite database path (default: {DEFAULT_DATABASE_PATH})",
    )


def _add_runtime_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--max-attempts", type=int, default=5)
    parser.add_argument("--retry-seconds", type=float, default=5.0)
    parser.add_argument("--idle-sleep-seconds", type=float, default=1.0)
    parser.add_argument(
        "--max-runtime-seconds",
        type=float,
        help="Return with state RUNNING after this many seconds; default waits for a terminal state",
    )


def _run(
    store: SqliteStore,
    context: PluginContext,
    run_id: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    if args.max_runtime_seconds is not None and args.max_runtime_seconds <= 0:
        raise ValueError("max-runtime-seconds must be positive")
    policy = RuntimePolicy(
        max_attempts=args.max_attempts,
        default_retry_seconds=args.retry_seconds,
        idle_sleep_seconds=args.idle_sleep_seconds,
    )
    runtime = SqliteSimuRuntime(store, WqbApiGateway(context), policy=policy)
    return runtime.run(run_id, max_runtime_seconds=args.max_runtime_seconds)


def _run_exit_code(summary: dict[str, Any]) -> int:
    state = summary["state"]
    if state == "COMPLETED":
        return 0
    if summary.get("timed_out") or state == "RUNNING":
        return 2
    if state == "COMPLETED_WITH_ERRORS":
        return 3
    if state == "BLOCKED":
        return 4
    return 1


def _database_name(store: SqliteStore) -> str:
    return str(Path(store.path).resolve())


plugin = SqliteSimuPlugin()


__all__ = ["DEFAULT_DATABASE_PATH", "SqliteSimuPlugin", "plugin"]
