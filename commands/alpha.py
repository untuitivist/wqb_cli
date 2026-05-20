from __future__ import annotations

import argparse

from ..core.auth import session_from_cookies
from ..core.client import WqbClient
from ..core.io import read_json_file, write_json
from ..core.registry import EndpointRegistry


def add_alpha_parser(subparsers: argparse._SubParsersAction) -> None:
    alpha = subparsers.add_parser("alpha", help="Alpha API commands")
    alpha_sub = alpha.add_subparsers(dest="alpha_command", required=True)

    get_parser = alpha_sub.add_parser("get", help="GET /alphas/{alpha_id}")
    get_parser.add_argument("alpha_id", help="Alpha id")
    get_parser.add_argument("--output", help="Write JSON result to file")

    list_parser = alpha_sub.add_parser("list", help="GET /users/self/alphas")
    list_parser.add_argument("--limit", default="20", help="Result limit")
    list_parser.add_argument("--offset", default="0", help="Result offset")
    list_parser.add_argument("--type", dest="alpha_type", help="Alpha type, e.g. REGULAR or SUPER")
    list_parser.add_argument("--color", help="Alpha color filter")
    list_parser.add_argument("--tag", help="Alpha tag filter")
    list_parser.add_argument("--date-submitted", help="dateSubmitted filter/range accepted by BRAIN API")
    list_parser.add_argument("--output", help="Write JSON result to file")

    simple_gets = {
        "distribution": "GET /alphas/distribution",
        "lists": "GET /alphas/lists",
        "super-selection": "GET /alphas/super-selection",
        "unsubmitted": "GET /alphas/unsubmitted",
        "walkthrough": "GET /alphas/sample-alpha-id-walkthrough",
    }
    for command_name, help_text in simple_gets.items():
        parser = alpha_sub.add_parser(command_name, help=help_text)
        parser.add_argument("--output", help="Write JSON result to file")

    all_parser = alpha_sub.add_parser("all", help="GET /alphas")
    all_parser.add_argument("--limit", default="20", help="Result limit")
    all_parser.add_argument("--offset", default="0", help="Result offset")
    all_parser.add_argument("--output", help="Write JSON result to file")

    check_parser = alpha_sub.add_parser("check", help="GET /alphas/{alpha_id}/check")
    check_parser.add_argument("alpha_id", help="Alpha id")
    check_parser.add_argument("--output", help="Write JSON result to file")

    recordsets_parser = alpha_sub.add_parser("recordsets", help="GET /alphas/{alpha_id}/recordsets")
    recordsets_parser.add_argument("alpha_id", help="Alpha id")
    recordsets_parser.add_argument("--output", help="Write JSON result to file")

    related_parser = alpha_sub.add_parser("related", help="GET /alphas/{alpha_id}/alphas")
    related_parser.add_argument("alpha_id", help="Alpha id")
    related_parser.add_argument("--output", help="Write JSON result to file")

    recordset_parser = alpha_sub.add_parser("recordset", help="GET /alphas/{alpha_id}/recordsets/{record_set_name}")
    recordset_parser.add_argument("alpha_id", help="Alpha id")
    recordset_parser.add_argument("name", help="Record set name, e.g. pnl, sharpe, turnover, yearly-stats")
    recordset_parser.add_argument("--output", help="Write JSON result to file")

    for recordset_name in ["pnl", "sharpe", "yearly-stats"]:
        parser = alpha_sub.add_parser(recordset_name, help=f"GET /alphas/{{alpha_id}}/recordsets/{recordset_name}")
        parser.add_argument("alpha_id", help="Alpha id")
        parser.add_argument("--output", help="Write JSON result to file")

    patch_parser = alpha_sub.add_parser("patch", help="PATCH /alphas/{alpha_id}")
    patch_parser.add_argument("alpha_id", help="Alpha id")
    patch_parser.add_argument("--input", required=True, help="JSON file containing patch body")
    patch_parser.add_argument("--execute", action="store_true", help="Actually patch alpha")
    patch_parser.add_argument("--output", help="Write JSON result to file")

    submit_parser = alpha_sub.add_parser("submit", help="POST /alphas/{alpha_id}/submit")
    submit_parser.add_argument("alpha_id", help="Alpha id")
    submit_parser.add_argument("--execute", action="store_true", help="Actually submit alpha")
    submit_parser.add_argument("--output", help="Write JSON result to file")

    correlation_parser = alpha_sub.add_parser("correlation", help="Alpha correlation commands")
    correlation_sub = correlation_parser.add_subparsers(dest="correlation_command", required=True)
    self_parser = correlation_sub.add_parser("self", help="GET /alphas/{alpha_id}/correlations/self")
    self_parser.add_argument("alpha_id", help="Alpha id")
    self_parser.add_argument("--output", help="Write JSON result to file")
    base_parser = correlation_sub.add_parser("base", help="GET /alphas/{alpha_id}/correlations")
    base_parser.add_argument("alpha_id", help="Alpha id")
    base_parser.add_argument("--output", help="Write JSON result to file")
    prod_parser = correlation_sub.add_parser("prod", help="GET /alphas/{alpha_id}/correlations/prod")
    prod_parser.add_argument("alpha_id", help="Alpha id")
    prod_parser.add_argument("--output", help="Write JSON result to file")
    power_pool_parser = correlation_sub.add_parser("power-pool", help="GET /alphas/{alpha_id}/correlations/power-pool")
    power_pool_parser.add_argument("alpha_id", help="Alpha id")
    power_pool_parser.add_argument("--output", help="Write JSON result to file")

    performance_parser = alpha_sub.add_parser("performance-comparison", help="GET /alphas/{alpha_id}/performance-comparison")
    performance_parser.add_argument("alpha_id", help="Alpha id")
    performance_parser.add_argument("--output", help="Write JSON result to file")


def handle_alpha(args: argparse.Namespace, registry: EndpointRegistry) -> int:
    simple_paths = {
        "distribution": "/alphas/distribution",
        "lists": "/alphas/lists",
        "super-selection": "/alphas/super-selection",
        "unsubmitted": "/alphas/unsubmitted",
        "walkthrough": "/alphas/sample-alpha-id-walkthrough",
    }
    if args.alpha_command in simple_paths:
        endpoint = registry.get(simple_paths[args.alpha_command])
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET")
        result = client.call(prepared, wait_retry_after=True)
        write_json(result, args.output)
        return 0
    if args.alpha_command == "all":
        endpoint = registry.get("/alphas")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", params={"limit": args.limit, "offset": args.offset})
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.alpha_command == "get":
        endpoint = registry.get("/alphas/{alpha_id}")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"alpha_id": args.alpha_id})
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.alpha_command == "list":
        endpoint = registry.get("/users/self/alphas")
        params = {"limit": args.limit, "offset": args.offset}
        if args.alpha_type:
            params["type"] = args.alpha_type
        if args.color:
            params["color"] = args.color
        if args.tag:
            params["tag"] = args.tag
        if args.date_submitted:
            params["dateSubmitted"] = args.date_submitted
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", params=params)
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.alpha_command == "recordset":
        endpoint = registry.get("/alphas/{alpha_id}/recordsets/{record_set_name}")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(
            endpoint,
            "GET",
            path_vars={"alpha_id": args.alpha_id, "record_set_name": args.name},
        )
        result = client.call(prepared, wait_retry_after=True)
        write_json(result, args.output)
        return 0
    if args.alpha_command in {"pnl", "sharpe", "yearly-stats"}:
        endpoint = registry.get(f"/alphas/{{alpha_id}}/recordsets/{args.alpha_command}")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"alpha_id": args.alpha_id})
        result = client.call(prepared, wait_retry_after=True)
        write_json(result, args.output)
        return 0
    if args.alpha_command == "related":
        endpoint = registry.get("/alphas/{alpha_id}/alphas")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"alpha_id": args.alpha_id})
        result = client.call(prepared, wait_retry_after=True)
        write_json(result, args.output)
        return 0
    if args.alpha_command == "patch":
        endpoint = registry.get("/alphas/{alpha_id}")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(
            endpoint,
            "PATCH",
            path_vars={"alpha_id": args.alpha_id},
            json_body=read_json_file(args.input),
            execute=args.execute,
        )
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.alpha_command == "submit":
        endpoint = registry.get("/alphas/{alpha_id}/submit")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "POST", path_vars={"alpha_id": args.alpha_id}, execute=args.execute)
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.alpha_command == "check":
        endpoint = registry.get("/alphas/{alpha_id}/check")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"alpha_id": args.alpha_id})
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.alpha_command == "recordsets":
        endpoint = registry.get("/alphas/{alpha_id}/recordsets")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"alpha_id": args.alpha_id})
        result = client.call(prepared, wait_retry_after=True)
        write_json(result, args.output)
        return 0
    if args.alpha_command == "correlation":
        if args.correlation_command == "base":
            endpoint = registry.get("/alphas/{alpha_id}/correlations")
            client = WqbClient(registry, session_from_cookies(args.cookies))
            prepared = client.prepare(endpoint, "GET", path_vars={"alpha_id": args.alpha_id})
            result = client.call(prepared, wait_retry_after=True)
            write_json(result, args.output)
            return 0
        if args.correlation_command == "self":
            endpoint = registry.get("/alphas/{alpha_id}/correlations/self")
            client = WqbClient(registry, session_from_cookies(args.cookies))
            prepared = client.prepare(endpoint, "GET", path_vars={"alpha_id": args.alpha_id})
            result = client.call(prepared, wait_retry_after=True)
            write_json(result, args.output)
            return 0
        if args.correlation_command == "prod":
            endpoint = registry.get("/alphas/{alpha_id}/correlations/prod")
            client = WqbClient(registry, session_from_cookies(args.cookies))
            prepared = client.prepare(endpoint, "GET", path_vars={"alpha_id": args.alpha_id})
            result = client.call(prepared, wait_retry_after=True)
            write_json(result, args.output)
            return 0
        if args.correlation_command == "power-pool":
            endpoint = registry.get("/alphas/{alpha_id}/correlations/power-pool")
            client = WqbClient(registry, session_from_cookies(args.cookies))
            prepared = client.prepare(endpoint, "GET", path_vars={"alpha_id": args.alpha_id})
            result = client.call(prepared, wait_retry_after=True)
            write_json(result, args.output)
            return 0
        raise AssertionError(args.correlation_command)
    if args.alpha_command == "performance-comparison":
        endpoint = registry.get("/alphas/{alpha_id}/performance-comparison")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"alpha_id": args.alpha_id})
        result = client.call(prepared, wait_retry_after=True)
        write_json(result, args.output)
        return 0
    raise AssertionError(args.alpha_command)
