from __future__ import annotations

import argparse

from ..core.auth import session_from_cookies
from ..core.client import WqbClient
from ..core.io import write_json
from ..core.registry import EndpointRegistry


def add_consultant_parser(subparsers: argparse._SubParsersAction) -> None:
    consultant = subparsers.add_parser("consultant", help="Consultant API commands")
    consultant_sub = consultant.add_subparsers(dest="consultant_command", required=True)

    simple_paths = {
        "get": "GET /consultant",
        "summary": "GET /consultant/summary",
        "datasets": "GET /consultant-datasets",
        "dos-and-donts": "GET /consultant-information/consultant-dos-and-donts",
        "faqs": "GET /consultant-information/consultant-faqs",
        "osmosis-guide": "GET /consultant-information/osmosis-allocation-guide-consultants",
        "visualization-tool": "GET /consultant-information/visualization-tool",
        "program": "GET /consultant-program",
    }
    for name, help_text in simple_paths.items():
        parser = consultant_sub.add_parser(name, help=help_text)
        parser.add_argument("--output", help="Write JSON result to file")

    program_language = consultant_sub.add_parser("program-language", help="GET /consultant-program/{language}")
    program_language.add_argument("language", help="Language code")
    program_language.add_argument("--output", help="Write JSON result to file")

    boards_parser = consultant_sub.add_parser("boards", help="Consultant board commands")
    boards_sub = boards_parser.add_subparsers(dest="boards_command", required=True)
    leader_parser = boards_sub.add_parser("leader", help="GET /consultant/boards/leader")
    leader_parser.add_argument("--output", help="Write JSON result to file")


def handle_consultant(args: argparse.Namespace, registry: EndpointRegistry) -> int:
    simple_paths = {
        "get": "/consultant",
        "summary": "/consultant/summary",
        "datasets": "/consultant-datasets",
        "dos-and-donts": "/consultant-information/consultant-dos-and-donts",
        "faqs": "/consultant-information/consultant-faqs",
        "osmosis-guide": "/consultant-information/osmosis-allocation-guide-consultants",
        "visualization-tool": "/consultant-information/visualization-tool",
        "program": "/consultant-program",
    }
    if args.consultant_command in simple_paths:
        endpoint = registry.get(simple_paths[args.consultant_command])
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET")
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.consultant_command == "program-language":
        endpoint = registry.get("/consultant-program/{language}")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"language": args.language})
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.consultant_command == "boards":
        if args.boards_command == "leader":
            endpoint = registry.get("/consultant/boards/leader")
            client = WqbClient(registry, session_from_cookies(args.cookies))
            prepared = client.prepare(endpoint, "GET")
            result = client.call(prepared)
            write_json(result, args.output)
            return 0
        raise AssertionError(args.boards_command)
    raise AssertionError(args.consultant_command)
