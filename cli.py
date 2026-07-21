from __future__ import annotations

import argparse
import sys
from typing import Any

from .core.auth import resolve_login_payload, save_cookie_payload, session_from_cookies
from .core.client import WqbClient
from .commands.account import add_account_parser, handle_account
from .commands.agent import add_agent_parser, handle_agent
from .commands.app import add_app_parser, handle_app
from .commands.alpha import add_alpha_parser, handle_alpha
from .commands.competition import add_competition_parser, handle_competition
from .commands.config import add_config_parser, handle_config
from .commands.consultant import add_consultant_parser, handle_consultant
from .commands.community import add_community_parser, handle_community
from .commands.data import add_data_parser, handle_data
from .commands.docs import add_docs_parser, handle_docs
from .commands.event import add_event_parser, handle_event
from .commands.errors import add_errors_parser, handle_errors
from .commands.platform import add_platform_parser, handle_platform
from .commands.search import add_search_parser, handle_search
from .commands.shortcut import add_shortcut_parser, handle_shortcut
from .commands.sim import add_sim_parser, handle_sim
from .commands.scope import add_scope_parser, handle_scope
from .commands.suggest import add_suggest_parser, handle_suggest
from .commands.tutorial import add_tutorial_parser, handle_tutorial
from .commands.user import add_user_parser, handle_user
from .core.io import parse_key_values, read_json_file, write_json
from .core.registry import EndpointRegistry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wqb", description="Agent-first WorldQuant BRAIN API CLI")
    parser.add_argument("--registry", help="Path to api_inventory_complete.json")
    parser.add_argument("--cookies", help="Path to cookies.json; default is wqb_cli/local/auth/cookies.json")
    sub = parser.add_subparsers(dest="command", required=True)

    api = sub.add_parser("api", help="Call API endpoints from the registry")
    api_sub = api.add_subparsers(dest="api_command", required=True)

    api_sub.add_parser("stats", help="Show registry statistics")

    list_parser = api_sub.add_parser("list", help="List registered endpoints")
    list_parser.add_argument("--prefix", help="Filter endpoint path prefix")

    show_parser = api_sub.add_parser("show", help="Show one endpoint definition")
    show_parser.add_argument("path")

    params_parser = api_sub.add_parser("params", help="Show query/body parameter hints for one endpoint")
    params_parser.add_argument("path")
    params_parser.add_argument("--output", help="Write JSON result to file")

    call_parser = api_sub.add_parser("call", help="Execute an endpoint call")
    call_parser.add_argument("method")
    call_parser.add_argument("path")
    call_parser.add_argument("--var", action="append", help="Template variable KEY=VALUE")
    call_parser.add_argument("--param", action="append", help="Query parameter KEY=VALUE")
    call_parser.add_argument("--input", help="JSON file containing path_vars, params, json")
    call_parser.add_argument("--json", help="Inline JSON request body")
    call_parser.add_argument("--env-auth", action="store_true", help="For POST /authentication, read EMAIL/PASSWORD from wqb_cli/local/.env")
    call_parser.add_argument("--output", help="Write JSON result to file")

    auth = sub.add_parser("auth", help="Authentication helpers")
    auth_sub = auth.add_subparsers(dest="auth_command", required=True)
    auth_sub.add_parser("status", help="GET /authentication")
    auth_sub.add_parser("head", help="HEAD /authentication")
    login_parser = auth_sub.add_parser("login", help="POST /authentication")
    login_parser.add_argument("--input", help="JSON login payload; defaults to keyring/config/env")
    login_parser.add_argument("--email", help="Email override")
    login_parser.add_argument("--password", help="Password override; prefer keyring or .env for normal use")
    login_parser.add_argument("--expiry", type=int, default=3600, help="Token expiry seconds")
    login_parser.add_argument("--config", dest="config_path", help="Path to local config.json")
    logout_parser = auth_sub.add_parser("logout", help="DELETE /authentication")
    for name in ["brainlabs", "persona", "support", "workday"]:
        auth_sub.add_parser(name, help=f"GET /authentication/{name}")
    add_account_parser(sub)
    add_agent_parser(sub)
    add_app_parser(sub)
    add_alpha_parser(sub)
    add_competition_parser(sub)
    add_config_parser(sub)
    add_consultant_parser(sub)
    add_community_parser(sub)
    add_data_parser(sub)
    add_docs_parser(sub)
    add_event_parser(sub)
    add_errors_parser(sub)
    add_platform_parser(sub)
    add_search_parser(sub)
    add_shortcut_parser(sub)
    add_sim_parser(sub)
    add_scope_parser(sub)
    add_suggest_parser(sub)
    add_tutorial_parser(sub)
    add_user_parser(sub)
    return parser


def load_registry(args: argparse.Namespace) -> EndpointRegistry:
    return EndpointRegistry.load(args.registry)


def handle_api(args: argparse.Namespace) -> int:
    registry = load_registry(args)
    if args.api_command == "stats":
        write_json(registry.stats())
        return 0
    if args.api_command == "list":
        write_json(
            [
                {
                    "path": endpoint.path,
                    "methods": list(endpoint.methods),
                    "description": endpoint.description,
                }
                for endpoint in registry.list(args.prefix)
            ]
        )
        return 0
    if args.api_command == "show":
        write_json(registry.get(args.path).raw)
        return 0
    if args.api_command == "params":
        endpoint = registry.get(args.path)
        write_json(
            {
                "path": endpoint.path,
                "methods": list(endpoint.methods),
                "path_variables": endpoint.variables,
                "params": endpoint.params,
                "request_body": endpoint.request_body,
                "source": list(endpoint.source),
            },
            args.output,
        )
        return 0
    if args.api_command == "call":
        endpoint = registry.get(args.path)
        input_payload = read_json_file(args.input)
        path_vars: dict[str, Any] = {}
        path_vars.update(input_payload.get("path_vars") or {})
        path_vars.update(parse_key_values(args.var))
        params: dict[str, Any] = {}
        params.update(input_payload.get("params") or {})
        params.update(parse_key_values(args.param))
        json_body = input_payload.get("json")
        if args.json:
            import json as json_module

            json_body = json_module.loads(args.json)
        if args.env_auth:
            env_payload = input_payload.get("json") if isinstance(input_payload.get("json"), dict) else {}
            json_body = resolve_login_payload(input_payload=env_payload, expiry=env_payload.get("expiry", 3600))
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(
            endpoint,
            args.method,
            path_vars={key: str(value) for key, value in path_vars.items()},
            params=params,
            json_body=json_body,
        )
        result = client.call(prepared)
        if (
            endpoint.path == "/authentication"
            and args.method.upper() == "POST"
            and result.get("ok")
        ):
            save_cookie_payload(client.session, args.cookies)
        write_json(result, args.output)
        return 0
    raise AssertionError(args.api_command)


def handle_auth(args: argparse.Namespace) -> int:
    registry = load_registry(args)
    client = WqbClient(registry, session_from_cookies(args.cookies))
    if args.auth_command == "status":
        endpoint = registry.get("/authentication")
        prepared = client.prepare(endpoint, "GET")
        write_json(client.call(prepared))
        return 0
    if args.auth_command == "head":
        endpoint = registry.get("/authentication")
        prepared = client.prepare(endpoint, "HEAD")
        write_json(client.call(prepared))
        return 0
    if args.auth_command == "login":
        endpoint = registry.get("/authentication")
        payload = resolve_login_payload(
            input_payload=read_json_file(args.input),
            email=args.email,
            password=args.password,
            expiry=args.expiry,
            config_path=args.config_path,
        )
        prepared = client.prepare(endpoint, "POST", json_body=payload)
        result = client.call(prepared)
        if result.get("ok"):
            save_cookie_payload(client.session, args.cookies)
        write_json(result)
        return 0
    if args.auth_command == "logout":
        endpoint = registry.get("/authentication")
        prepared = client.prepare(endpoint, "DELETE")
        result = client.call(prepared)
        write_json(result)
        return 0
    if args.auth_command in {"brainlabs", "persona", "support", "workday"}:
        endpoint = registry.get(f"/authentication/{args.auth_command}")
        prepared = client.prepare(endpoint, "GET")
        write_json(client.call(prepared))
        return 0
    raise AssertionError(args.auth_command)


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "api":
            code = handle_api(args)
        elif args.command == "agent":
            code = handle_agent(args)
        elif args.command == "app":
            code = handle_app(args)
        elif args.command == "account":
            code = handle_account(args, load_registry(args))
        elif args.command == "auth":
            code = handle_auth(args)
        elif args.command == "alpha":
            code = handle_alpha(args, load_registry(args))
        elif args.command == "competition":
            code = handle_competition(args, load_registry(args))
        elif args.command == "config":
            code = handle_config(args, load_registry(args))
        elif args.command == "consultant":
            code = handle_consultant(args, load_registry(args))
        elif args.command == "community":
            code = handle_community(args)
        elif args.command == "data":
            code = handle_data(args, load_registry(args))
        elif args.command == "docs":
            code = handle_docs(args)
        elif args.command == "event":
            code = handle_event(args, load_registry(args))
        elif args.command == "errors":
            code = handle_errors(args, load_registry(args))
        elif args.command == "platform":
            code = handle_platform(args, load_registry(args))
        elif args.command == "search":
            code = handle_search(args, load_registry(args))
        elif args.command in {"shortcut", "quick"}:
            code = handle_shortcut(args, load_registry(args))
        elif args.command == "sim":
            code = handle_sim(args, load_registry(args))
        elif args.command == "scope":
            code = handle_scope(args)
        elif args.command == "suggest":
            code = handle_suggest(args, load_registry(args))
        elif args.command == "tutorial":
            code = handle_tutorial(args, load_registry(args))
        elif args.command == "user":
            code = handle_user(args, load_registry(args))
        else:
            parser.error(f"Unknown command: {args.command}")
            code = 2
    except Exception as exc:
        write_json({"ok": False, "error_type": type(exc).__name__, "detail": str(exc)})
        code = 1
    sys.exit(code)


if __name__ == "__main__":
    main()
