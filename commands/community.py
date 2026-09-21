from __future__ import annotations

import argparse
from typing import Any

from ..core.community_client import CommunityClient, load_community_registry, prepare_community_request
from ..core.io import parse_key_values, read_json_file, write_json
from ..core.registry import EndpointRegistry


def add_community_parser(subparsers: argparse._SubParsersAction) -> None:
    community = subparsers.add_parser("community", help="Online BRAIN forum API; local data uses sqlitecom")
    community_sub = community.add_subparsers(dest="community_command", required=True)
    routes = {
        "list": ("GET", "/api/v2/community/posts.json", (), "List online posts, newest first"),
        "topics": ("GET", "/api/v2/community/topics.json", (), "List accessible forum sections"),
        "topic": ("GET", "/api/v2/community/topics/{topic_id}.json", ("topic_id",), "Read a forum section"),
        "get": ("GET", "/api/v2/community/posts/{post_id}.json", ("post_id",), "Read a post and its HTML"),
        "comments": ("GET", "/api/v2/community/posts/{post_id}/comments.json", ("post_id",), "Read a page of comments"),
        "search": ("GET", "/api/v2/help_center/community_posts/search.json", ("query",), "Search online posts; offline search is sqlitecom search"),
        "user-posts": ("GET", "/api/v2/community/users/{user_id}/posts.json", ("user_id",), "List a user's posts; me is supported"),
        "user-comments": ("GET", "/api/v2/community/users/{user_id}/comments.json", ("user_id",), "List a user's comments"),
        "create": ("POST", "/api/v2/community/posts.json", (), "Explicitly publish a post from JSON"),
        "update": ("PUT", "/api/v2/community/posts/{post_id}.json", ("post_id",), "Explicitly update a post from JSON"),
        "delete": ("DELETE", "/api/v2/community/posts/{post_id}.json", ("post_id",), "Explicitly delete a post"),
        "comment-create": ("POST", "/api/v2/community/posts/{post_id}/comments.json", ("post_id",), "Explicitly publish a comment from JSON"),
        "comment-update": ("PUT", "/api/v2/community/posts/{post_id}/comments/{comment_id}.json", ("post_id", "comment_id"), "Explicitly update a comment"),
        "comment-delete": ("DELETE", "/api/v2/community/posts/{post_id}/comments/{comment_id}.json", ("post_id", "comment_id"), "Explicitly delete a comment"),
    }
    for name, (method, path, variables, help_text) in routes.items():
        command = community_sub.add_parser(name, help=help_text)
        command.set_defaults(community_method=method, community_path=path)
        for variable in variables:
            command.add_argument(variable)
        if method == "GET":
            command.add_argument("--page", type=int, default=1)
            command.add_argument("--limit", type=int, default=25, help="Results per page; next-page links are preserved")
        if name in {"list", "search", "user-posts"}:
            command.add_argument("--sort", choices=["created_at", "updated_at", "recent_activity", "votes", "comments"], default="created_at")
            command.add_argument("--order", choices=["asc", "desc"], default="desc")
        if name in {"list", "search"}:
            command.add_argument("--topic", dest="section_id", help="Forum section ID")
        if method in {"POST", "PUT"}:
            body = command.add_mutually_exclusive_group(required=True)
            body.add_argument("--input", help="JSON request body file")
            body.add_argument("--json", help="Inline JSON request body")
        _request_options(command)
    api = community_sub.add_parser("api", help="Inspect the forum API inventory or issue a raw request")
    api_sub = api.add_subparsers(dest="community_api_command", required=True)
    for name in ("stats", "list", "show", "params", "call"):
        command = api_sub.add_parser(name)
        if name in {"show", "params", "call"}:
            if name == "call":
                command.add_argument("method")
            command.add_argument("path")
        if name == "call":
            command.add_argument("--var", action="append")
            command.add_argument("--input", help="JSON containing path_vars, params and json")
            command.add_argument("--json")
            _request_options(command)
        else:
            command.add_argument("--output")


def _request_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", dest="config_path", help="BRAIN authentication configuration")
    parser.add_argument("--param", action="append", help="Query parameter KEY=VALUE")
    parser.add_argument("--dry-run", action="store_true", help="Preview without authentication or HTTP")
    parser.add_argument("--max-wait-seconds", type=float, default=300, help="Read retry sleep budget; writes are never retried")
    parser.add_argument("--output", help="Write JSON result to file")


def handle_community(args: argparse.Namespace) -> int:
    import json

    registry = load_community_registry()
    params: dict[str, Any] = {}
    variables: dict[str, Any] = {}
    json_body = None
    if args.community_command == "api":
        operation = args.community_api_command
        if operation != "call":
            if operation == "stats":
                result = registry.stats()
            elif operation == "list":
                result = [endpoint.raw for endpoint in registry.list()]
            else:
                endpoint = registry.get(args.path)
                result = endpoint.raw if operation == "show" else {"path": endpoint.path, "variables": endpoint.variables, "params": endpoint.params, "request_body": endpoint.request_body}
            write_json(result, args.output)
            return 0
        payload = read_json_file(args.input)
        variables.update(payload.get("path_vars") or {})
        variables.update(parse_key_values(args.var))
        params.update(payload.get("params") or {})
        json_body = payload.get("json")
        method, path = args.method, args.path
    else:
        method, path = args.community_method, args.community_path
        for name in registry.get(path).variables:
            variables[name] = getattr(args, name)
        if method == "GET":
            if not 1 <= args.limit <= 100 or args.page < 1:
                raise ValueError("limit must be 1..100 and page must be positive")
            params.update({"per_page": args.limit, "page": args.page, "include": "users,topics"})
        if hasattr(args, "sort"):
            if args.community_command == "search" and args.sort not in {"created_at", "updated_at"}:
                raise ValueError("Online search supports only created_at or updated_at sorting")
            params.update({"sort_by": args.sort, "sort_order": args.order})
        if args.community_command == "search":
            params["query"] = args.query
            if args.section_id:
                params["topic"] = args.section_id
        elif args.community_command == "list" and args.section_id:
            path = "/api/v2/community/topics/{topic_id}/posts.json"
            variables["topic_id"] = args.section_id
        if getattr(args, "input", None):
            json_body = read_json_file(args.input)
    if getattr(args, "json", None):
        json_body = json.loads(args.json)
    params.update(parse_key_values(args.param))
    prepared = prepare_community_request(registry, method, path, path_vars=variables, params=params, json_body=json_body)
    if args.dry_run:
        write_json({"ok": True, "dry_run": True, "request": prepared}, args.output)
        return 0
    client = CommunityClient(cookies_path=args.cookies, config_path=args.config_path, brain_registry=EndpointRegistry.load(args.registry), max_wait_seconds=args.max_wait_seconds)
    result = client.call(prepared["method"], prepared["url"], params=prepared["params"], json_body=prepared["json"])
    write_json(result, args.output)
    return 0 if result["ok"] else 1
