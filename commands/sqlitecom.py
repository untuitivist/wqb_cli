from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from ..core.community_client import CommunityClient
from ..core.community_sqlite import get_local_post, import_storage, query_storage, schema_storage, search_local_storage, stats_storage
from ..core.community_sync import sync_storage
from ..core.io import parse_key_values, write_json
from ..core.paths import DEFAULT_COMMUNITY_SQLITE_PATH
from ..core.registry import EndpointRegistry


def add_sqlitecom_parser(subparsers: argparse._SubParsersAction) -> None:
    group = subparsers.add_parser("sqlitecom", help="Local community SQLite, read-only SQL and durable incremental sync")
    commands = group.add_subparsers(dest="sqlitecom_command", required=True)
    for name in ("sync", "search", "get", "stats", "status", "schema", "import", "sql"):
        parser = commands.add_parser(name, aliases=["query"] if name == "sql" else [])
        parser.add_argument("--sqlite", dest="sqlite_path", help="Database path; also supports WQB_COMMUNITY_SQLITE")
        parser.add_argument("--output", help="Write JSON result to file")
        if name == "sync":
            parser.add_argument("--config", dest="config_path", help="BRAIN authentication configuration")
            parser.add_argument("--topic", help="Restrict discovery to a forum section ID")
            parser.add_argument("--since", help="Initial lower bound, ISO date/time; default resumes or uses the last completed sync")
            parser.add_argument("--overlap-hours", type=float, default=48)
            parser.add_argument("--refresh-comments-days", type=float, default=7)
            parser.add_argument("--max-pages", type=int, default=0, help="Pause after this many index pages; 0 means finish")
            parser.add_argument("--reconcile", action="store_true", help="Scan the complete index, including older posts and stale comments")
            parser.add_argument("--max-wait-seconds", type=float, default=300)
            parser.add_argument("--log", help="Append UTF-8 progress events to a file")
        elif name == "search":
            parser.add_argument("query", nargs="?", default="")
            parser.add_argument("--scope", choices=["all", "forum", "topics", "comments", "docs", "articles"], default="all")
            parser.add_argument("--author", help="Exact author name or account label")
            parser.add_argument("--since", help="Only content created on/after this ISO date/time")
            parser.add_argument("--sort", choices=["newest", "updated", "votes"], default="newest")
            parser.add_argument("--limit", type=int, default=20)
        elif name == "get":
            parser.add_argument("post_id")
        elif name == "import":
            parser.add_argument("--source", help="Plugin JSON/WQCS to merge; omitted sections and existing documents are preserved")
        elif name == "sql":
            source = parser.add_mutually_exclusive_group(required=True)
            source.add_argument("--sql", help="One read-only SQLite statement")
            source.add_argument("--file", help="UTF-8 SQL file; preferred for shell quoting")
            parser.add_argument("--param", action="append", help="Named SQL bind parameter NAME=VALUE; JSON values are recognized")
            parser.add_argument("--max-rows", type=int, default=200)
            parser.add_argument("--timeout", type=float, default=10, help="Query execution deadline in seconds")


def handle_sqlitecom(args: argparse.Namespace) -> int:
    path = Path(args.sqlite_path or os.environ.get("WQB_COMMUNITY_SQLITE") or DEFAULT_COMMUNITY_SQLITE_PATH)
    operation = args.sqlitecom_command
    if operation == "sync":
        client = CommunityClient(cookies_path=args.cookies, config_path=args.config_path, brain_registry=EndpointRegistry.load(args.registry), max_wait_seconds=args.max_wait_seconds)

        def emit(event: dict[str, Any]) -> None:
            line = json.dumps(event, ensure_ascii=False)
            print(line, file=sys.stderr, flush=True)
            if args.log:
                log_path = Path(args.log)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                with log_path.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")

        result = sync_storage(path, client, topic_id=args.topic, since=args.since, overlap_hours=args.overlap_hours, refresh_comments_days=args.refresh_comments_days, max_pages=args.max_pages, reconcile=args.reconcile, emit=emit)
    elif operation in {"stats", "status"}:
        result = stats_storage(path)
    elif operation == "schema":
        result = schema_storage(path)
    elif operation == "get":
        result = get_local_post(path, args.post_id)
    elif operation == "search":
        result = search_local_storage(path, args.query, scope=args.scope, author=args.author, since=args.since, sort=args.sort, limit=args.limit)
    elif operation == "import":
        result = import_storage(args.source, path)
    elif operation in {"sql", "query"}:
        sql = Path(args.file).read_text(encoding="utf-8-sig") if args.file else args.sql
        parameters = {}
        for name, value in parse_key_values(args.param).items():
            try:
                parameters[name] = json.loads(value)
            except (ValueError, TypeError):
                parameters[name] = value
        result = query_storage(path, sql, parameters=parameters, max_rows=args.max_rows, timeout=args.timeout)
    else:
        raise AssertionError(operation)
    write_json(result, args.output)
    return 0 if result.get("ok") else 1
