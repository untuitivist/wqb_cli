from __future__ import annotations

import argparse
from typing import Any

from ..core.auth import session_from_cookies
from ..core.client import WqbClient
from ..core.io import read_json_file, write_json
from ..core.registry import EndpointRegistry
from ..core.simulation import is_region_agnostic, region_agnostic_child_ids


def add_simu_parser(subparsers: argparse._SubParsersAction) -> None:
    simu_parser = subparsers.add_parser("simu", help="Simulation API commands")
    simu_subparsers = simu_parser.add_subparsers(dest="simu_command", required=True)

    options_parser = simu_subparsers.add_parser("options", help="OPTIONS /simulations")
    options_parser.add_argument("--output", help="Write JSON result to file")

    list_parser = simu_subparsers.add_parser("list", help="GET /simulations")
    list_parser.add_argument("--output", help="Write JSON result to file")

    get_parser = simu_subparsers.add_parser("get", help="GET /simulations/{simulation_id}")
    get_parser.add_argument("simulation_id", help="Simulation id")
    get_parser.add_argument("--max-wait-seconds", type=float, default=900.0, help="Maximum total wait time while following Retry-After")
    get_parser.add_argument("--output", help="Write JSON result to file")

    create_parser = simu_subparsers.add_parser("create", help="POST /simulations")
    create_parser.add_argument("--input", required=True, help="JSON file containing simulation request body")
    create_parser.add_argument("--dry-run", action="store_true", help="Validate and preview the request without simulating")
    create_parser.add_argument("--max-wait-seconds", type=float, default=900.0, help="Maximum total wait time after creation")
    create_parser.add_argument("--output", help="Write JSON result to file")

    super_selection_parser = simu_subparsers.add_parser("super-selection", help="GET/POST /simulations/super-selection")
    super_selection_parser.add_argument("--method", choices=["GET", "POST"], default="GET")
    super_selection_parser.add_argument("--input", help="JSON file for POST body")
    super_selection_parser.add_argument("--output", help="Write JSON result to file")


def handle_simu(args: argparse.Namespace, registry: EndpointRegistry) -> int:
    if args.simu_command == "options":
        endpoint = registry.get("/simulations")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "OPTIONS")
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.simu_command == "list":
        endpoint = registry.get("/simulations")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET")
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.simu_command == "get":
        endpoint = registry.get("/simulations/{simulation_id}")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"simulation_id": args.simulation_id})
        result = client.call(prepared, wait_retry_after=True, max_wait_seconds=args.max_wait_seconds)
        result["classification"] = _classify_simulation_result(result)
        result["ok"] = bool(result.get("ok") and result["classification"]["ok"])
        write_json(result, args.output)
        return 0 if result.get("ok") else 1
    if args.simu_command == "create":
        endpoint = registry.get("/simulations")
        payload = read_json_file(args.input)
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "POST", json_body=payload)
        if args.dry_run:
            write_json({"ok": True, "dry_run": True, "request": prepared.__dict__}, args.output)
            return 0
        result = _create_and_wait_simulation(client, registry, prepared, args.max_wait_seconds)
        write_json(result, args.output)
        return 0 if result.get("ok") else 1
    if args.simu_command == "super-selection":
        endpoint = registry.get("/simulations/super-selection")
        payload = read_json_file(args.input) if args.input else None
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, args.method, json_body=payload)
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    raise AssertionError(args.simu_command)


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
    region_agnostic = is_region_agnostic(prepared.json_body)
    child_results = [] if region_agnostic else _wait_child_simulations(
        client, registry, wait_result, max_wait_seconds=max_wait_seconds
    )
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
    if region_agnostic and result["ok"]:
        parent_id = (wait_result.get("response", {}).get("body") or {}).get("alpha")
        try:
            collected = _collect_region_agnostic(client, registry, parent_id, max_wait_seconds)
            result["region_agnostic"] = collected
            result["ok"] = collected["ok"]
        except (TypeError, ValueError) as error:
            result["ok"] = False
            result["collection_error"] = str(error)
    return result


def _collect_region_agnostic(
    client: WqbClient, registry: EndpointRegistry, parent_id: str, max_wait_seconds: float
) -> dict[str, Any]:
    parent = client.call(
        client.prepare(registry.get("/alphas/{alpha_id}"), "GET", path_vars={"alpha_id": parent_id}),
        wait_retry_after=True, max_wait_seconds=max_wait_seconds,
    )
    collected: dict[str, Any] = {"ok": False, "parent": parent, "children": [], "parent_pnl": "NOT_APPLICABLE"}
    if not parent.get("ok") or parent.get("response", {}).get("wait_timed_out"):
        return collected
    children = region_agnostic_child_ids(parent.get("response", {}).get("body") or {}, parent_id)
    regions = set()
    for child_id in children:
        child = {"alpha_id": child_id}
        for key, path in (("detail", "/alphas/{alpha_id}"), ("pnl", "/alphas/{alpha_id}/recordsets/pnl")):
            result = client.call(
                client.prepare(registry.get(path), "GET", path_vars={"alpha_id": child_id}),
                wait_retry_after=True, max_wait_seconds=max_wait_seconds,
            )
            child[key] = result
            if not result.get("ok") or result.get("response", {}).get("wait_timed_out"):
                collected["children"].append(child)
                return collected
        detail = child["detail"]["response"]["body"]
        region = (detail.get("settings") or {}).get("region")
        if detail.get("id") != child_id or detail.get("type") != "RA_CHILD" or region not in {"USA", "EUR", "ASI", "GLB"}:
            raise ValueError("Invalid region-agnostic child identity, type or region")
        if region in regions or not (child["pnl"]["response"]["body"] or {}).get("records"):
            raise ValueError("Region-agnostic child has duplicate region or empty PnL")
        regions.add(region)
        child["region"] = region
        collected["children"].append(child)
    collected["ok"] = True
    return collected


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
