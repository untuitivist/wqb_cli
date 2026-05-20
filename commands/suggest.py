from __future__ import annotations

import argparse

from ..core.auth import session_from_cookies
from ..core.client import WqbClient
from ..core.io import read_json_file, write_json
from ..core.registry import EndpointRegistry


def add_suggest_parser(subparsers: argparse._SubParsersAction) -> None:
    suggest = subparsers.add_parser("suggest", help="Suggestion API commands")
    suggest_sub = suggest.add_subparsers(dest="suggest_command", required=True)
    for name in ["examples", "expression", "fastexpr", "fields"]:
        parser = suggest_sub.add_parser(name, help=f"GET/POST /suggest/{name}")
        parser.add_argument("--method", choices=["GET", "POST"], default="GET")
        parser.add_argument("--input", help="JSON file for POST body")
        parser.add_argument("--execute", action="store_true", help="Actually execute POST")
        parser.add_argument("--output", help="Write JSON result to file")


def handle_suggest(args: argparse.Namespace, registry: EndpointRegistry) -> int:
    if args.suggest_command in {"examples", "expression", "fastexpr", "fields"}:
        endpoint = registry.get(f"/suggest/{args.suggest_command}")
        payload = read_json_file(args.input) if args.input else None
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, args.method, json_body=payload, execute=args.execute)
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    raise AssertionError(args.suggest_command)
