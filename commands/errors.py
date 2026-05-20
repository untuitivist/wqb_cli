from __future__ import annotations

import argparse

from ..core.auth import session_from_cookies
from ..core.client import WqbClient
from ..core.io import read_json_file, write_json
from ..core.registry import EndpointRegistry


def add_errors_parser(subparsers: argparse._SubParsersAction) -> None:
    errors = subparsers.add_parser("errors", help="Error-reporting API commands")
    errors_sub = errors.add_subparsers(dest="errors_command", required=True)
    envelope = errors_sub.add_parser("envelope", help="POST /errors/api/2/envelope")
    envelope.add_argument("--input", required=True, help="JSON file for request body")
    envelope.add_argument("--execute", action="store_true", help="Actually execute POST")
    envelope.add_argument("--output", help="Write JSON result to file")


def handle_errors(args: argparse.Namespace, registry: EndpointRegistry) -> int:
    if args.errors_command == "envelope":
        endpoint = registry.get("/errors/api/2/envelope")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "POST", json_body=read_json_file(args.input), execute=args.execute)
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    raise AssertionError(args.errors_command)
