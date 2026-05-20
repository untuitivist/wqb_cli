from __future__ import annotations

import argparse

from ..core.io import write_json
from ..core.scope_store import (
    list_scopes,
    load_scope_info,
    load_scope_pickle,
    neutralization_rows,
    pickle_alpha_rows,
    pickle_scope_summary,
    scope_files,
    search_scope_items,
    show_scope,
    top_scope_items,
)


def add_scope_parser(subparsers: argparse._SubParsersAction) -> None:
    scope = subparsers.add_parser("scope", help="Local data_all scope inspection")
    scope.add_argument("--info", dest="info_path", help="Path to info_data.bin")
    scope.add_argument("--pickle", dest="pickle_path", help="Path to all_data.pickle")
    scope_sub = scope.add_subparsers(dest="scope_command", required=True)

    files = scope_sub.add_parser("files", help="Show local scope data files")
    files.add_argument("--output", help="Write JSON result to file")

    list_parser = scope_sub.add_parser("list", help="List available REGION_DELAY scopes")
    list_parser.add_argument("--output", help="Write JSON result to file")

    show_parser = scope_sub.add_parser("show", help="Show one scope summary")
    show_parser.add_argument("scope", help="Scope key, e.g. USA_1")
    show_parser.add_argument("--output", help="Write JSON result to file")

    top = scope_sub.add_parser("top", help="Rank datafields, datasets, or categories by historical ratios")
    top.add_argument("scope", help="Scope key, e.g. USA_1")
    top.add_argument("--group", choices=["datafield", "dataset", "category"], default="datafield")
    top.add_argument("--metric", choices=["sharpe_ratio", "fitness_ratio"], default="sharpe_ratio")
    top.add_argument("--limit", type=int, default=20)
    top.add_argument("--min-count", type=int, default=1)
    top.add_argument("--ascending", action="store_true", help="Sort low to high")
    top.add_argument("--output", help="Write JSON result to file")

    search = scope_sub.add_parser("search", help="Search local scope datafields, datasets, or categories")
    search.add_argument("scope", help="Scope key, e.g. USA_1")
    search.add_argument("query", help="Case-insensitive substring")
    search.add_argument("--group", choices=["datafield", "dataset", "category"], default="datafield")
    search.add_argument("--limit", type=int, default=20)
    search.add_argument("--output", help="Write JSON result to file")

    neutral = scope_sub.add_parser("neutralization", help="Inspect neutralization performance by scope")
    neutral.add_argument("scope", help="Scope key, e.g. USA_1")
    neutral.add_argument("--group", choices=["mean", "datafield", "dataset", "category"], default="mean")
    neutral.add_argument("--name", help="Required when group is not mean")
    neutral.add_argument("--metric", choices=["sharpe_ratio", "fitness_ratio"], default="sharpe_ratio")
    neutral.add_argument("--limit", type=int, default=20)
    neutral.add_argument("--min-count", type=int, default=1)
    neutral.add_argument("--output", help="Write JSON result to file")

    pickle_summary = scope_sub.add_parser("pickle-summary", help="Show one scope from all_data.pickle")
    pickle_summary.add_argument("scope", help="Scope key, e.g. USA_1")
    pickle_summary.add_argument("--sample", type=int, default=2, help="Sample rows per table")
    pickle_summary.add_argument("--output", help="Write JSON result to file")

    alpha_rows = scope_sub.add_parser("alpha-rows", help="Read alpha detail rows from all_data.pickle")
    alpha_rows.add_argument("scope", help="Scope key, e.g. USA_1")
    alpha_rows.add_argument("--table", choices=["base", "settings", "is", "os"], default="base")
    alpha_rows.add_argument("--limit", type=int, default=20)
    alpha_rows.add_argument("--offset", type=int, default=0)
    alpha_rows.add_argument("--datafield", help="Filter by exact datafield from the base table")
    alpha_rows.add_argument("--dataset", help="Filter by exact dataset from the base table")
    alpha_rows.add_argument("--columns", help="Comma-separated output columns")
    alpha_rows.add_argument("--output", help="Write JSON result to file")


def handle_scope(args: argparse.Namespace) -> int:
    if args.scope_command == "files":
        write_json({"ok": True, **scope_files(info_path=args.info_path, all_data_path=args.pickle_path)}, args.output)
        return 0

    if args.scope_command == "pickle-summary":
        data = load_scope_pickle(args.pickle_path)
        write_json({"ok": True, **pickle_scope_summary(data, args.scope, sample=args.sample)}, args.output)
        return 0
    if args.scope_command == "alpha-rows":
        data = load_scope_pickle(args.pickle_path)
        columns = [item.strip() for item in args.columns.split(",") if item.strip()] if args.columns else None
        rows = pickle_alpha_rows(
            data,
            args.scope,
            table=args.table,
            limit=args.limit,
            offset=args.offset,
            datafield=args.datafield,
            dataset=args.dataset,
            columns=columns,
        )
        write_json({"ok": True, **rows}, args.output)
        return 0

    info = load_scope_info(args.info_path)
    if args.scope_command == "list":
        write_json({"ok": True, "scopes": list_scopes(info)}, args.output)
        return 0
    if args.scope_command == "show":
        write_json({"ok": True, **show_scope(info, args.scope)}, args.output)
        return 0
    if args.scope_command == "top":
        rows = top_scope_items(
            info,
            args.scope,
            group=args.group,
            metric=args.metric,
            limit=args.limit,
            min_count=args.min_count,
            descending=not args.ascending,
        )
        write_json({"ok": True, "scope": args.scope, "group": args.group, "metric": args.metric, "results": rows}, args.output)
        return 0
    if args.scope_command == "search":
        rows = search_scope_items(info, args.scope, group=args.group, query=args.query, limit=args.limit)
        write_json({"ok": True, "scope": args.scope, "group": args.group, "query": args.query, "results": rows}, args.output)
        return 0
    if args.scope_command == "neutralization":
        if args.group != "mean" and not args.name:
            write_json({"ok": False, "reason": "name_required_for_group", "group": args.group}, args.output)
            return 1
        rows = neutralization_rows(
            info,
            args.scope,
            group=args.group,
            name=args.name,
            metric=args.metric,
            limit=args.limit,
            min_count=args.min_count,
        )
        write_json({"ok": True, "scope": args.scope, "group": args.group, "name": args.name, "metric": args.metric, "results": rows}, args.output)
        return 0
    raise AssertionError(args.scope_command)
