from __future__ import annotations

import argparse

from ..core.auth import session_from_cookies
from ..core.client import WqbClient
from ..core.io import read_json_file, write_json
from ..core.registry import EndpointRegistry


def add_user_parser(subparsers: argparse._SubParsersAction) -> None:
    user = subparsers.add_parser("user", help="User API commands")
    user_sub = user.add_subparsers(dest="user_command", required=True)

    self_parser = user_sub.add_parser("self", help="GET /users/self")
    self_parser.add_argument("--output", help="Write JSON result to file")

    consultant_summary_parser = user_sub.add_parser("consultant-summary", help="GET /users/self/consultant/summary")
    consultant_summary_parser.add_argument("--output", help="Write JSON result to file")

    messages_parser = user_sub.add_parser("messages", help="GET /users/self/messages")
    messages_parser.add_argument("--limit", default="20", help="Result limit")
    messages_parser.add_argument("--offset", default="0", help="Result offset")
    messages_parser.add_argument("--order", help="Sort order, e.g. -dateCreated")
    messages_parser.add_argument("--type", help="Message type filter, e.g. ANNOUNCEMENT or NOTIFICATION")
    messages_parser.add_argument("--output", help="Write JSON result to file")

    users_parser = user_sub.add_parser("list", help="GET /users")
    users_parser.add_argument("--limit", default="20", help="Result limit")
    users_parser.add_argument("--output", help="Write JSON result to file")

    simple_self = {
        "achievements": "GET /users/self/achievements",
        "simulation-activity": "GET /users/self/activities/simulations",
        "pyramid-alphas": "GET /users/self/activities/pyramid-alphas",
        "pyramid-multipliers": "GET /users/self/activities/pyramid-multipliers",
        "agreements": "GET /users/self/agreements",
        "alphas-summary": "GET /users/self/alphas/summary",
        "messages-summary": "GET /users/self/messages/summary",
        "pyramid-alpha-summary": "GET /users/self/pyramid/alphas",
        "teams": "GET /users/self/teams",
        "tutorial-steps": "GET /users/self/tutorial/steps",
        "tutorial-summary": "GET /users/self/tutorial/summary",
        "consultant-tutorial-summary": "GET /users/self/consultant/tutorial/summary",
    }
    for name, help_text in simple_self.items():
        parser = user_sub.add_parser(name, help=help_text)
        if name in {"pyramid-alphas", "pyramid-multipliers"}:
            parser.add_argument("--start-date", help="Quarter start date, e.g. 2026-04-01")
            parser.add_argument("--end-date", help="Quarter end date, e.g. 2026-07-01")
        parser.add_argument("--output", help="Write JSON result to file")

    consultant_tutorial_patch = user_sub.add_parser("consultant-tutorial-patch", help="PATCH /users/self/consultant/tutorial/summary")
    consultant_tutorial_patch.add_argument("--input", required=True, help="JSON file containing patch body")
    consultant_tutorial_patch.add_argument("--output", help="Write JSON result to file")

    get_parser = user_sub.add_parser("get", help="GET /users/{user_id}")
    get_parser.add_argument("user_id", help="User id")
    get_parser.add_argument("--output", help="Write JSON result to file")

    user_scoped = {
        "user-achievements": "/users/{user_id}/achievements",
        "user-activities": "/users/{user_id}/activities",
        "user-diversity": "/users/{user_id}/activities/diversity",
        "user-alphas-options": "/users/{user_id}/alphas",
        "user-competitions": "/users/{user_id}/competitions",
        "user-simulation-settings": "/users/{user_id}/settings/simulation",
    }
    for name in user_scoped:
        parser = user_sub.add_parser(name, help=user_scoped[name])
        parser.add_argument("user_id", help="User id")
        parser.add_argument("--output", help="Write JSON result to file")


def handle_user(args: argparse.Namespace, registry: EndpointRegistry) -> int:
    if args.user_command == "self":
        endpoint = registry.get("/users/self")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET")
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.user_command == "consultant-summary":
        endpoint = registry.get("/users/self/consultant/summary")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET")
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.user_command == "messages":
        endpoint = registry.get("/users/self/messages")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        params = {"limit": args.limit, "offset": args.offset}
        if args.order:
            params["order"] = args.order
        if args.type:
            params["type"] = args.type
        prepared = client.prepare(endpoint, "GET", params=params)
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.user_command == "list":
        endpoint = registry.get("/users")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", params={"limit": args.limit})
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    simple_paths = {
        "achievements": "/users/self/achievements",
        "simulation-activity": "/users/self/activities/simulations",
        "pyramid-alphas": "/users/self/activities/pyramid-alphas",
        "pyramid-multipliers": "/users/self/activities/pyramid-multipliers",
        "agreements": "/users/self/agreements",
        "alphas-summary": "/users/self/alphas/summary",
        "messages-summary": "/users/self/messages/summary",
        "pyramid-alpha-summary": "/users/self/pyramid/alphas",
        "teams": "/users/self/teams",
        "tutorial-steps": "/users/self/tutorial/steps",
        "tutorial-summary": "/users/self/tutorial/summary",
        "consultant-tutorial-summary": "/users/self/consultant/tutorial/summary",
    }
    if args.user_command in simple_paths:
        endpoint = registry.get(simple_paths[args.user_command])
        client = WqbClient(registry, session_from_cookies(args.cookies))
        params = {}
        if args.user_command in {"pyramid-alphas", "pyramid-multipliers"}:
            if args.start_date:
                params["startDate"] = args.start_date
            if args.end_date:
                params["endDate"] = args.end_date
        prepared = client.prepare(endpoint, "GET", params=params)
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.user_command == "consultant-tutorial-patch":
        endpoint = registry.get("/users/self/consultant/tutorial/summary")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "PATCH", json_body=read_json_file(args.input))
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.user_command == "get":
        endpoint = registry.get("/users/{user_id}")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"user_id": args.user_id})
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    scoped_paths = {
        "user-achievements": ("/users/{user_id}/achievements", "GET", {}),
        "user-activities": ("/users/{user_id}/activities", "GET", {}),
        "user-diversity": ("/users/{user_id}/activities/diversity", "GET", {"grouping": "region,delay,dataCategory"}),
        "user-alphas-options": ("/users/{user_id}/alphas", "OPTIONS", {}),
        "user-competitions": ("/users/{user_id}/competitions", "GET", {}),
        "user-simulation-settings": ("/users/{user_id}/settings/simulation", "GET", {}),
    }
    if args.user_command in scoped_paths:
        path, method, params = scoped_paths[args.user_command]
        endpoint = registry.get(path)
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, method, path_vars={"user_id": args.user_id}, params=params)
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    raise AssertionError(args.user_command)
