from __future__ import annotations

import argparse
from typing import Any

from ..core.auth import session_from_cookies
from ..core.client import WqbClient
from ..core.io import read_json_file, write_json
from ..core.registry import EndpointRegistry


def add_shortcut_parser(subparsers: argparse._SubParsersAction) -> None:
    shortcut = subparsers.add_parser(
        "shortcut",
        aliases=["quick"],
        help="Shortcut commands for common agent tasks",
    )
    shortcut_sub = shortcut.add_subparsers(dest="shortcut_command", required=True)

    whoami = shortcut_sub.add_parser("whoami", help="Check current authentication session")
    whoami.add_argument("--output", help="Write JSON result to file")

    simulate = shortcut_sub.add_parser("simulate", help="Create a simulation and optionally wait for completion")
    simulate.add_argument("--input", required=True, help="JSON simulation payload")
    simulate.add_argument("--execute", action="store_true", help="Actually create simulation")
    simulate.add_argument("--wait", action="store_true", help="Poll the created simulation until done or timeout")
    simulate.add_argument("--max-wait-seconds", type=float, default=900.0, help="Maximum wait time for polling")
    simulate.add_argument("--output", help="Write JSON result to file")

    alpha = shortcut_sub.add_parser("alpha-report", help="Fetch alpha details, checks, correlations, and yearly stats")
    alpha.add_argument("alpha_id", help="Alpha id")
    alpha.add_argument("--output", help="Write JSON result to file")

    data = shortcut_sub.add_parser("data-fields", help="Search data fields with common settings")
    data.add_argument("--dataset", help="Dataset id")
    data.add_argument("--search", help="Search query")
    data.add_argument("--instrument-type", default="EQUITY", help="Instrument type")
    data.add_argument("--region", default="USA", help="Region")
    data.add_argument("--delay", default="1", help="Delay")
    data.add_argument("--universe", default="TOP3000", help="Universe")
    data.add_argument("--limit", default="20", help="Result limit")
    data.add_argument("--output", help="Write JSON result to file")


def handle_shortcut(args: argparse.Namespace, registry: EndpointRegistry) -> int:
    client = WqbClient(registry, session_from_cookies(args.cookies))
    if args.shortcut_command == "whoami":
        result = _call(client, registry, "/authentication")
        write_json(result, args.output)
        return 0 if result.get("ok") else 1
    if args.shortcut_command == "simulate":
        payload = read_json_file(args.input)
        create = _call(client, registry, "/simulations", method="POST", json_body=payload, execute=args.execute)
        result: dict[str, Any] = {"ok": create.get("ok", False), "create": create}
        simulation_id = _simulation_id_from_location(create)
        if simulation_id:
            result["simulation_id"] = simulation_id
        if args.wait and simulation_id and create.get("ok"):
            result["wait"] = _call(
                client,
                registry,
                "/simulations/{simulation_id}",
                path_vars={"simulation_id": simulation_id},
                wait_retry_after=True,
                max_wait_seconds=args.max_wait_seconds,
            )
            result["ok"] = bool(result["wait"].get("ok"))
        write_json(result, args.output)
        return 0 if result.get("ok") else 1
    if args.shortcut_command == "alpha-report":
        alpha_id = args.alpha_id
        result = {
            "ok": True,
            "alpha_id": alpha_id,
            "alpha": _call(client, registry, "/alphas/{alpha_id}", path_vars={"alpha_id": alpha_id}),
            "check": _call(client, registry, "/alphas/{alpha_id}/check", path_vars={"alpha_id": alpha_id}),
            "self_correlation": _call(
                client,
                registry,
                "/alphas/{alpha_id}/correlations/self",
                path_vars={"alpha_id": alpha_id},
                wait_retry_after=True,
            ),
            "prod_correlation": _call(
                client,
                registry,
                "/alphas/{alpha_id}/correlations/prod",
                path_vars={"alpha_id": alpha_id},
                wait_retry_after=True,
            ),
            "yearly_stats": _call(
                client,
                registry,
                "/alphas/{alpha_id}/recordsets/yearly-stats",
                path_vars={"alpha_id": alpha_id},
                wait_retry_after=True,
            ),
        }
        result["ok"] = all(part.get("ok") for key, part in result.items() if isinstance(part, dict) and key != "alpha_id")
        write_json(result, args.output)
        return 0 if result.get("ok") else 1
    if args.shortcut_command == "data-fields":
        params = {
            "instrumentType": args.instrument_type,
            "region": args.region,
            "delay": args.delay,
            "universe": args.universe,
            "limit": args.limit,
            "offset": "0",
        }
        if args.dataset:
            params["dataset.id"] = args.dataset
        if args.search:
            params["search"] = args.search
        result = _call(client, registry, "/data-fields", params=params)
        write_json(result, args.output)
        return 0 if result.get("ok") else 1
    raise AssertionError(args.shortcut_command)


def _call(
    client: WqbClient,
    registry: EndpointRegistry,
    path: str,
    *,
    method: str = "GET",
    path_vars: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json_body: Any = None,
    execute: bool = False,
    wait_retry_after: bool = False,
    max_wait_seconds: float | None = None,
) -> dict[str, Any]:
    endpoint = registry.get(path)
    prepared = client.prepare(
        endpoint,
        method,
        path_vars=path_vars,
        params=params,
        json_body=json_body,
        execute=execute,
    )
    return client.call(prepared, wait_retry_after=wait_retry_after, max_wait_seconds=max_wait_seconds)


def _simulation_id_from_location(result: dict[str, Any]) -> str | None:
    location = ((result.get("response") or {}).get("location") or "").strip()
    if not location:
        return None
    return location.rstrip("/").split("/")[-1] or None
