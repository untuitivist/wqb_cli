from __future__ import annotations

import argparse
from typing import Any

from ..core.community_client import CommunityClient, prepare_community_request
from ..core.help_center import article_reference, collect_help_center_pages, help_center_locale, load_help_center_registry
from ..core.io import parse_key_values, read_json_file, write_json
from ..core.registry import EndpointRegistry


def add_help_center_parser(subparsers: argparse._SubParsersAction) -> None:
    help_center = subparsers.add_parser("help-center", help="Read official BRAIN Help Center articles with community SSO")
    commands = help_center.add_subparsers(dest="help_center_command", required=True)
    routes = {
        "categories": ("/api/v2/help_center/{locale}/categories.json", "categories", None, "List official documentation categories"),
        "category": ("/api/v2/help_center/{locale}/categories/{category_id}.json", None, "category_id", "Read a documentation category"),
        "sections": ("/api/v2/help_center/{locale}/sections.json", "sections", None, "List sections, optionally within a category"),
        "section": ("/api/v2/help_center/{locale}/sections/{section_id}.json", None, "section_id", "Read a documentation section"),
        "articles": ("/api/v2/help_center/{locale}/articles.json", "articles", None, "List articles, optionally within a section or category"),
        "get": ("/api/v2/help_center/{locale}/articles/{article_id}.json", None, "article", "Read an official article by ID or Help Center URL"),
        "search": ("/api/v2/help_center/articles/search.json", "results", "query", "Search official articles, not forum posts"),
    }
    for name, (path, collection, positional, help_text) in routes.items():
        command = commands.add_parser(name, help=help_text)
        command.set_defaults(help_center_path=path, help_center_collection=collection)
        if positional:
            command.add_argument(positional)
        command.add_argument("--locale", help="Help Center locale; default en-us, or the locale in a get URL")
        if collection:
            command.add_argument("--page", type=int, default=1)
            command.add_argument("--limit", type=int, default=25, help="Results per page, 1..100")
            command.add_argument("--all-pages", action="store_true", help="Follow same-resource pagination links")
            command.add_argument("--max-pages", type=int, default=100, help="All-pages budget; incomplete reads exit nonzero")
            sort_choices = ["created_at", "updated_at", "relevance"] if name == "search" else ["created_at", "updated_at", "position"]
            command.add_argument("--sort", choices=sort_choices, default="relevance" if name == "search" else "updated_at")
            command.add_argument("--order", choices=["asc", "desc"], default="desc")
        if name == "sections":
            command.add_argument("--category", dest="category_id")
        if name in {"articles", "search"}:
            filters = command.add_mutually_exclusive_group() if name == "articles" else command
            filters.add_argument("--category", dest="category_id")
            filters.add_argument("--section", dest="section_id")
        _request_options(command)
    api = commands.add_parser("api", help="Inspect the official Help Center inventory or call one read-only endpoint")
    api_commands = api.add_subparsers(dest="help_center_api_command", required=True)
    for name in ("stats", "list", "show", "params", "call"):
        command = api_commands.add_parser(name)
        if name in {"show", "params", "call"}:
            if name == "call":
                command.add_argument("method", choices=["GET"])
            command.add_argument("path")
        if name == "list":
            command.add_argument("--prefix")
        if name == "call":
            command.add_argument("--var", action="append", help="Path variable KEY=VALUE, including locale")
            command.add_argument("--input", help="JSON containing path_vars and params; request bodies are not allowed")
            _request_options(command)
        else:
            command.add_argument("--output")


def _request_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", dest="config_path", help="Existing BRAIN authentication configuration")
    parser.add_argument("--param", action="append", help="Query parameter KEY=VALUE")
    parser.add_argument("--dry-run", action="store_true", help="Preview without authentication or HTTP")
    parser.add_argument("--max-wait-seconds", type=float, default=300, help="Retry-After sleep budget for read retries")
    parser.add_argument("--output", help="Write UTF-8 JSON result to file")


def handle_help_center(args: argparse.Namespace) -> int:
    registry = load_help_center_registry()
    params: dict[str, Any] = {}
    variables: dict[str, Any] = {}
    json_body = None
    if args.help_center_command == "api":
        operation = args.help_center_api_command
        if operation != "call":
            if operation == "stats":
                result = registry.stats()
            elif operation == "list":
                result = [endpoint.raw for endpoint in registry.list(args.prefix)]
            else:
                endpoint = registry.get(args.path)
                result = endpoint.raw if operation == "show" else {
                    "path": endpoint.path, "variables": endpoint.variables,
                    "params": endpoint.params, "request_body": endpoint.request_body,
                }
            write_json(result, args.output)
            return 0
        payload = read_json_file(args.input)
        variables.update(payload.get("path_vars") or {})
        variables.update(parse_key_values(args.var))
        params.update(payload.get("params") or {})
        json_body = payload.get("json")
        path = args.path
    else:
        path = args.help_center_path
        variables["locale"] = help_center_locale(args.locale)
        if args.help_center_command == "get":
            variables.update(article_reference(args.article, args.locale))
        for name in ("category_id", "section_id"):
            value = getattr(args, name, None)
            if value is not None:
                variables[name] = value
        if args.help_center_command == "sections" and args.category_id:
            path = "/api/v2/help_center/{locale}/categories/{category_id}/sections.json"
        if args.help_center_command == "articles":
            if args.section_id:
                path = "/api/v2/help_center/{locale}/sections/{section_id}/articles.json"
            elif args.category_id:
                path = "/api/v2/help_center/{locale}/categories/{category_id}/articles.json"
        if args.help_center_collection:
            if not 1 <= args.limit <= 100 or args.page < 1 or args.max_pages < 1:
                raise ValueError("limit must be 1..100; page and max-pages must be positive")
            params.update({"per_page": args.limit, "page": args.page})
            if args.sort != "relevance":
                params.update({"sort_by": args.sort, "sort_order": args.order})
        if args.help_center_command == "search":
            if not args.query.strip():
                raise ValueError("Search query must not be empty")
            params.update({"query": args.query, "locale": variables["locale"]})
            for name in ("category", "section"):
                if getattr(args, name + "_id"):
                    params[name] = getattr(args, name + "_id")
    params.update(parse_key_values(args.param))
    prepared = prepare_community_request(registry, "GET", path, path_vars=variables, params=params, json_body=json_body)
    if args.dry_run:
        write_json({"ok": True, "dry_run": True, "request": prepared}, args.output)
        return 0
    client = CommunityClient(cookies_path=args.cookies, config_path=args.config_path,
                             brain_registry=EndpointRegistry.load(args.registry), max_wait_seconds=args.max_wait_seconds)
    if getattr(args, "all_pages", False):
        result = collect_help_center_pages(client, prepared, collection=args.help_center_collection, max_pages=args.max_pages)
    else:
        result = client.call("GET", prepared["url"], params=prepared["params"])
    write_json(result, args.output)
    return 0 if result["ok"] else 1
