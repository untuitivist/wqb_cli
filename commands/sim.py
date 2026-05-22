from __future__ import annotations

import argparse
from typing import Any

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
    create_parser.add_argument("--max-wait-seconds", type=float, default=900.0, help="Maximum total wait time after creation")
    create_parser.add_argument("--output", help="Write JSON result to file")

    super_selection_parser = sim_sub.add_parser("super-selection", help="GET/POST /simulations/super-selection")
    super_selection_parser.add_argument("--method", choices=["GET", "POST"], default="GET")
    super_selection_parser.add_argument("--input", help="JSON file for POST body")
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
        result["classification"] = _classify_simulation_result(result)
        result["ok"] = bool(result.get("ok") and result["classification"]["ok"])
        write_json(result, args.output)
        return 0 if result.get("ok") else 1
    if args.sim_command == "create":
        endpoint = registry.get("/simulations")
        payload = read_json_file(args.input)
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "POST", json_body=payload)
        result = _create_and_wait_simulation(client, registry, prepared, args.max_wait_seconds)
        write_json(result, args.output)
        return 0 if result.get("ok") else 1
    if args.sim_command == "super-selection":
        endpoint = registry.get("/simulations/super-selection")
        payload = read_json_file(args.input) if args.input else None
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, args.method, json_body=payload)
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    raise AssertionError(args.sim_command)


def _create_and_wait_simulation(
    client: WqbClient,
    registry: EndpointRegistry,
    prepared: Any,
    max_wait_seconds: float,
) -> dict[str, Any]:
    create_result = client.call(prepared)
    create_classification = _classify_simulation_create(create_result)
    simulation_id = _simulation_id_from_location(create_result)
    result: dict[str, Any] = {
        "ok": False,
        "simulation_id": simulation_id,
        "create_classification": create_classification,
        "create": create_result,
    }

    if not create_result.get("ok") or not simulation_id:
        result["classification"] = {
            "ok": False,
            "reason": "simulation_create_failed" if not create_result.get("ok") else "missing_simulation_id",
        }
        return result

    wait_endpoint = registry.get("/simulations/{simulation_id}")
    wait_prepared = client.prepare(wait_endpoint, "GET", path_vars={"simulation_id": simulation_id})
    wait_result = client.call(wait_prepared, wait_retry_after=True, max_wait_seconds=max_wait_seconds)
    classification = _classify_simulation_result(wait_result)
    child_results = _wait_child_simulations(client, registry, wait_result, max_wait_seconds=max_wait_seconds)
    children_ok = all(child["classification"]["ok"] for child in child_results)
    result.update(
        {
            "ok": bool(wait_result.get("ok") and classification["ok"] and children_ok),
            "classification": classification,
            "wait": wait_result,
        }
    )
    if child_results:
        result["children"] = child_results
    return result


def _wait_child_simulations(
    client: WqbClient,
    registry: EndpointRegistry,
    parent_result: dict[str, Any],
    *,
    max_wait_seconds: float,
) -> list[dict[str, Any]]:
    child_ids = _child_simulation_ids(parent_result)
    if not child_ids:
        return []
    endpoint = registry.get("/simulations/{simulation_id}")
    children: list[dict[str, Any]] = []
    for child_id in child_ids:
        prepared = client.prepare(endpoint, "GET", path_vars={"simulation_id": child_id})
        child_result = client.call(prepared, wait_retry_after=True, max_wait_seconds=max_wait_seconds)
        children.append(
            {
                "simulation_id": child_id,
                "classification": _classify_simulation_result(child_result),
                "result": child_result,
            }
        )
    return children


def _classify_simulation_create(result: dict[str, Any]) -> dict[str, Any]:
    response = result.get("response", {})
    status_code = response.get("status_code")
    simulation_id = _simulation_id_from_location(result)
    if status_code == 201 and simulation_id:
        return {
            "ok": True,
            "status_code": 201,
            "reason": "simulation_created_waiting_for_results",
            "message": "201 Created, waiting for results...",
        }
    return {
        "ok": bool(result.get("ok") and simulation_id),
        "status_code": status_code,
        "reason": "simulation_create_failed" if not result.get("ok") else "missing_simulation_id",
    }


def _classify_simulation_result(result: dict[str, Any]) -> dict[str, Any]:
    response = result.get("response", {})
    body = response.get("body")
    status = body.get("status") if isinstance(body, dict) else None
    if response.get("wait_timed_out"):
        return {
            "ok": False,
            "status": status,
            "reason": "simulation_wait_timed_out",
        }
    if status in {"COMPLETE", "WARNING"}:
        return {
            "ok": True,
            "status": status,
            "reason": "simulation_finished",
        }
    if status in {"ERROR", "FAIL", "FAILED"}:
        return {
            "ok": False,
            "status": status,
            "reason": "simulation_failed",
        }
    return {
        "ok": bool(result.get("ok") and status is None),
        "status": status,
        "reason": "simulation_result_unknown" if result.get("ok") else "simulation_get_failed",
    }


def _simulation_id_from_location(result: dict[str, Any]) -> str | None:
    location = ((result.get("response") or {}).get("location") or "").strip()
    if not location:
        return None
    return location.rstrip("/").split("/")[-1] or None


def _child_simulation_ids(result: dict[str, Any]) -> list[str]:
    body = ((result.get("response") or {}).get("body") or {})
    if not isinstance(body, dict):
        return []
    children = body.get("children")
    if not isinstance(children, list):
        return []
    ids: list[str] = []
    for child in children:
        if isinstance(child, str):
            ids.append(child)
        elif isinstance(child, dict) and isinstance(child.get("id"), str):
            ids.append(child["id"])
    return ids
