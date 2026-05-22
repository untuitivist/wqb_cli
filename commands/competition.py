from __future__ import annotations

import argparse

from ..core.auth import session_from_cookies
from ..core.client import WqbClient
from ..core.io import write_json
from ..core.registry import EndpointRegistry


def add_competition_parser(subparsers: argparse._SubParsersAction) -> None:
    competition = subparsers.add_parser("competition", help="Competition API commands")
    competition_sub = competition.add_subparsers(dest="competition_command", required=True)

    list_parser = competition_sub.add_parser("list", help="GET /competitions")
    list_parser.add_argument("--limit", default="20", help="Result limit")
    list_parser.add_argument("--offset", default="0", help="Result offset")
    list_parser.add_argument("--output", help="Write JSON result to file")

    get_parser = competition_sub.add_parser("get", help="GET /competitions/{competition_id}")
    get_parser.add_argument("competition_id", help="Competition id")
    get_parser.add_argument("--output", help="Write JSON result to file")

    agreement_parser = competition_sub.add_parser("agreement", help="GET/POST /competitions/{competition_id}/agreement")
    agreement_parser.add_argument("competition_id", help="Competition id")
    agreement_parser.add_argument("--method", choices=["GET", "POST"], default="GET")
    agreement_parser.add_argument("--output", help="Write JSON result to file")


def handle_competition(args: argparse.Namespace, registry: EndpointRegistry) -> int:
    if args.competition_command == "list":
        endpoint = registry.get("/competitions")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", params={"limit": args.limit, "offset": args.offset})
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.competition_command == "get":
        endpoint = registry.get("/competitions/{competition_id}")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"competition_id": args.competition_id})
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.competition_command == "agreement":
        endpoint = registry.get("/competitions/{competition_id}/agreement")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, args.method, path_vars={"competition_id": args.competition_id})
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    raise AssertionError(args.competition_command)
