from __future__ import annotations

import argparse

from ..core.auth import session_from_cookies
from ..core.client import WqbClient
from ..core.io import write_json
from ..core.registry import EndpointRegistry


def add_event_parser(subparsers: argparse._SubParsersAction) -> None:
    event = subparsers.add_parser("event", help="Event API commands")
    event_sub = event.add_subparsers(dest="event_command", required=True)

    list_parser = event_sub.add_parser("list", help="GET /events")
    list_parser.add_argument("--limit", default="20", help="Result limit")
    list_parser.add_argument("--offset", default="0", help="Result offset")
    list_parser.add_argument("--output", help="Write JSON result to file")

    options_parser = event_sub.add_parser("options", help="OPTIONS /events")
    options_parser.add_argument("--output", help="Write JSON result to file")

    get_parser = event_sub.add_parser("get", help="GET /events/{event_id}")
    get_parser.add_argument("event_id", help="Event id")
    get_parser.add_argument("--output", help="Write JSON result to file")


def handle_event(args: argparse.Namespace, registry: EndpointRegistry) -> int:
    if args.event_command == "list":
        endpoint = registry.get("/events")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", params={"limit": args.limit, "offset": args.offset})
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.event_command == "options":
        endpoint = registry.get("/events")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "OPTIONS")
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.event_command == "get":
        endpoint = registry.get("/events/{event_id}")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"event_id": args.event_id})
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    raise AssertionError(args.event_command)
