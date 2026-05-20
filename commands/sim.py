from __future__ import annotations

import argparse

from ..core.auth import session_from_cookies
from ..core.client import WqbClient
from ..core.io import read_json_file, write_json
from ..core.registry import EndpointRegistry


def add_sim_parser(subparsers: argparse._SubParsersAction) -> None:
    sim = subparsers.add_parser("sim", help="Simulation API commands")
    sim_sub = sim.add_subparsers(dest="sim_command", required=True)

    options_parser = sim_sub.add_parser("options", help="OPTIONS /simulations")
    options_parser.add_argument("--output", help="Write JSON result to file")

    list_parser = sim_sub.add_parser("list", help="GET /simulations")
    list_parser.add_argument("--output", help="Write JSON result to file")

    get_parser = sim_sub.add_parser("get", help="GET /simulations/{simulation_id}")
    get_parser.add_argument("simulation_id", help="Simulation id")
    get_parser.add_argument("--max-wait-seconds", type=float, default=900.0, help="Maximum total wait time while following Retry-After")
    get_parser.add_argument("--output", help="Write JSON result to file")

    create_parser = sim_sub.add_parser("create", help="POST /simulations")
    create_parser.add_argument("--input", required=True, help="JSON file containing simulation request body")
    create_parser.add_argument("--execute", action="store_true", help="Actually create simulation")
    create_parser.add_argument("--output", help="Write JSON result to file")

    super_selection_parser = sim_sub.add_parser("super-selection", help="GET/POST /simulations/super-selection")
    super_selection_parser.add_argument("--method", choices=["GET", "POST"], default="GET")
    super_selection_parser.add_argument("--input", help="JSON file for POST body")
    super_selection_parser.add_argument("--execute", action="store_true", help="Actually execute POST")
    super_selection_parser.add_argument("--output", help="Write JSON result to file")


def handle_sim(args: argparse.Namespace, registry: EndpointRegistry) -> int:
    if args.sim_command == "options":
        endpoint = registry.get("/simulations")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "OPTIONS")
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.sim_command == "list":
        endpoint = registry.get("/simulations")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET")
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.sim_command == "get":
        endpoint = registry.get("/simulations/{simulation_id}")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"simulation_id": args.simulation_id})
        result = client.call(prepared, wait_retry_after=True, max_wait_seconds=args.max_wait_seconds)
        write_json(result, args.output)
        return 0
    if args.sim_command == "create":
        endpoint = registry.get("/simulations")
        payload = read_json_file(args.input)
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "POST", json_body=payload, execute=args.execute)
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.sim_command == "super-selection":
        endpoint = registry.get("/simulations/super-selection")
        payload = read_json_file(args.input) if args.input else None
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, args.method, json_body=payload, execute=args.execute)
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    raise AssertionError(args.sim_command)
