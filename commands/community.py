from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Any

from ..core.community_store import export_community_storage, search_community_storage
from ..core.io import write_json
from ..core.paths import DEFAULT_COMMUNITY_SQLITE_PATH


def add_community_parser(subparsers: argparse._SubParsersAction) -> None:
    community = subparsers.add_parser("community", help="Local community SQLite commands")
    community_sub = community.add_subparsers(dest="community_command", required=True)

    search_parser = community_sub.add_parser("search", help="Search local community SQLite")
    search_parser.add_argument("query", help="Search keyword")
    search_parser.add_argument("--scope", choices=["all", "forum", "topics", "comments", "docs", "articles"], default="all")
    search_parser.add_argument("--limit", type=int, default=20)
    search_parser.add_argument("--sqlite", dest="sqlite_path", help="Path to community.sqlite3")
    search_parser.add_argument("--output", help="Write JSON result to file")

    export_parser = community_sub.add_parser("export", help="Import WebDataScope community export into SQLite")
    export_parser.add_argument("--source", dest="source_path", help="Path to WQPCommunityState_*.json or *.wqcs")
    export_parser.add_argument("--sqlite", dest="sqlite_path", help="Target SQLite path")
    export_parser.add_argument("--export-json", action="store_true", help="Also write normalized JSON next to SQLite")
    export_parser.add_argument("--output", help="Write JSON result to file")

    stats_parser = community_sub.add_parser("stats", help="Show local community SQLite table counts")
    stats_parser.add_argument("--sqlite", dest="sqlite_path", help="Path to community.sqlite3")
    stats_parser.add_argument("--output", help="Write JSON result to file")


def _resolve_sqlite(path: str | None) -> Path:
    return Path(path) if path else DEFAULT_COMMUNITY_SQLITE_PATH


def _default_sqlite_for_write(path: str | None) -> Path:
    return Path(path) if path else DEFAULT_COMMUNITY_SQLITE_PATH


def _table_count(conn: sqlite3.Connection, table: str) -> int:
    cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
    return int(cur.fetchone()[0])


def _stats(sqlite_path: Path) -> dict[str, Any]:
    if not sqlite_path.exists():
        return {
            "ok": False,
            "reason": "community_sqlite_not_found",
            "sqlite_path": str(sqlite_path),
        }
    tables = [
        "forum_communities",
        "forum_topics",
        "forum_comments",
        "docs_categories",
        "docs_sections",
        "docs_articles",
    ]
    conn = sqlite3.connect(sqlite_path)
    try:
        return {
            "ok": True,
            "sqlite_path": str(sqlite_path),
            "counts": {table: _table_count(conn, table) for table in tables},
        }
    finally:
        conn.close()


def handle_community(args: argparse.Namespace) -> int:
    if args.community_command == "search":
        sqlite_path = _resolve_sqlite(args.sqlite_path)
        result = search_community_storage(
            args.query,
            sqlite_path=sqlite_path,
            scope=args.scope,
            limit=args.limit,
        )
        result = {"ok": True, **result}
        write_json(result, args.output)
        return 0
    if args.community_command == "export":
        sqlite_path = _default_sqlite_for_write(args.sqlite_path)
        result = export_community_storage(
            source_path=args.source_path,
            sqlite_path=sqlite_path,
            export_json=args.export_json,
        )
        result = {"ok": True, **result}
        write_json(result, args.output)
        return 0
    if args.community_command == "stats":
        result = _stats(_resolve_sqlite(args.sqlite_path))
        write_json(result, args.output)
        return 0
    raise AssertionError(args.community_command)
