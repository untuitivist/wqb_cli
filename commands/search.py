from __future__ import annotations

import argparse

from ..core.auth import session_from_cookies
from ..core.client import WqbClient
from ..core.io import write_json
from ..core.registry import EndpointRegistry


def add_search_parser(subparsers: argparse._SubParsersAction) -> None:
    search = subparsers.add_parser("search", help="Global platform search")
    search.add_argument("query", help="Search query")
    search.add_argument("--output", help="Write JSON result to file")


def handle_search(args: argparse.Namespace, registry: EndpointRegistry) -> int:
    endpoint = registry.get("/search")
    client = WqbClient(registry, session_from_cookies(args.cookies))
    prepared = client.prepare(endpoint, "GET", params={"query": args.query})
    result = client.call(prepared)
    write_json(result, args.output)
    return 0
