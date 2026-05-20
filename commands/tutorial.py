from __future__ import annotations

import argparse

from ..core.auth import session_from_cookies
from ..core.client import WqbClient
from ..core.io import write_json
from ..core.registry import EndpointRegistry


def add_tutorial_parser(subparsers: argparse._SubParsersAction) -> None:
    tutorial = subparsers.add_parser("tutorial", help="Tutorial API commands")
    tutorial_sub = tutorial.add_subparsers(dest="tutorial_command", required=True)

    list_parser = tutorial_sub.add_parser("list", help="GET /tutorials")
    list_parser.add_argument("--limit", default="20", help="Result limit")
    list_parser.add_argument("--output", help="Write JSON result to file")

    pages_parser = tutorial_sub.add_parser("pages", help="GET /tutorial-pages")
    pages_parser.add_argument("--output", help="Write JSON result to file")

    page_parser = tutorial_sub.add_parser("page", help="GET /tutorial-pages/{page_id}")
    page_parser.add_argument("page_id", help="Tutorial page id")
    page_parser.add_argument("--output", help="Write JSON result to file")

    slug_parser = tutorial_sub.add_parser("slug", help="GET /tutorial/{tutorial_slug}")
    slug_parser.add_argument("tutorial_slug", help="Tutorial slug")
    slug_parser.add_argument("--output", help="Write JSON result to file")


def handle_tutorial(args: argparse.Namespace, registry: EndpointRegistry) -> int:
    if args.tutorial_command == "list":
        endpoint = registry.get("/tutorials")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", params={"limit": args.limit})
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.tutorial_command == "pages":
        endpoint = registry.get("/tutorial-pages")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET")
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.tutorial_command == "page":
        endpoint = registry.get("/tutorial-pages/{page_id}")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"page_id": args.page_id})
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.tutorial_command == "slug":
        endpoint = registry.get("/tutorial/{tutorial_slug}")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"tutorial_slug": args.tutorial_slug})
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    raise AssertionError(args.tutorial_command)
