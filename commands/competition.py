from __future__ import annotations

import argparse
import json
from typing import Any

from ..core.auth import session_from_cookies
from ..core.client import WqbClient
from ..core.io import parse_key_values, read_json_file, write_json
from ..core.registry import EndpointRegistry


def _add_pagination_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--limit", default="20", help="Result limit")
    parser.add_argument("--offset", default="0", help="Result offset")


def _add_json_payload_args(parser: argparse.ArgumentParser) -> None:
    payload = parser.add_mutually_exclusive_group(required=True)
    payload.add_argument("--input", help="JSON request body file")
    payload.add_argument("--json", help="Inline JSON request body")


def _json_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.json:
        payload = json.loads(args.json)
        if not isinstance(payload, dict):
            raise ValueError("SPC submission body must be a JSON object")
        return payload
    return read_json_file(args.input)


def _call(
    args: argparse.Namespace,
    registry: EndpointRegistry,
    endpoint_path: str,
    method: str,
    *,
    path_vars: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json_body: Any = None,
) -> dict[str, Any]:
    endpoint = registry.get(endpoint_path)
    client = WqbClient(registry, session_from_cookies(args.cookies))
    prepared = client.prepare(
        endpoint,
        method,
        path_vars=path_vars,
        params=params,
        json_body=json_body,
    )
    return client.call(prepared)


def add_competition_parser(subparsers: argparse._SubParsersAction) -> None:
    competition = subparsers.add_parser("competition", help="Competition API commands")
    competition_sub = competition.add_subparsers(dest="competition_command", required=True)

    list_parser = competition_sub.add_parser("list", help="GET /competitions")
    _add_pagination_args(list_parser)
    list_parser.add_argument("--output", help="Write JSON result to file")

    get_parser = competition_sub.add_parser("get", help="GET /competitions/{competition_id}")
    get_parser.add_argument("competition_id", help="Competition id")
    get_parser.add_argument("--output", help="Write JSON result to file")

    agreement_parser = competition_sub.add_parser("agreement", help="GET/POST /competitions/{competition_id}/agreement")
    agreement_parser.add_argument("competition_id", help="Competition id")
    agreement_parser.add_argument("--method", choices=["GET", "POST"], default="GET")
    agreement_parser.add_argument("--output", help="Write JSON result to file")

    leaderboard_parser = competition_sub.add_parser(
        "leaderboard",
        help="GET/OPTIONS a competition or consultant leaderboard",
    )
    leaderboard_parser.add_argument(
        "identifier",
        help="Competition id in competition scope, or consultant board type in consultant scope",
    )
    leaderboard_parser.add_argument(
        "--scope",
        choices=["competition", "consultant"],
        default="competition",
        help="Leaderboard namespace (default: competition)",
    )
    leaderboard_parser.add_argument(
        "--board-type",
        help="Competition board type such as leader, university, prize, referral, or power-pool (default: leader)",
    )
    leaderboard_parser.add_argument("--method", choices=["GET", "OPTIONS"], default="GET")
    _add_pagination_args(leaderboard_parser)
    leaderboard_parser.add_argument("--board", help="Board period/region value returned by OPTIONS")
    leaderboard_parser.add_argument("--aggregate", help="Aggregation returned by OPTIONS, such as user or team")
    leaderboard_parser.add_argument("--order", help="Order expression, for example -score")
    leaderboard_parser.add_argument("--param", action="append", help="Extra query parameter KEY=VALUE")
    leaderboard_parser.add_argument("--output", help="Write JSON result to file")

    guidelines_parser = competition_sub.add_parser(
        "guidelines",
        help="GET /competitions/{competition_id}/agreement",
    )
    guidelines_parser.add_argument("competition_id", help="Competition id")
    guidelines_parser.add_argument("--output", help="Write JSON result to file")

    faq_parser = competition_sub.add_parser(
        "faq",
        help="Read the FAQ URL from GET /competitions/{competition_id}",
    )
    faq_parser.add_argument("competition_id", help="Competition id")
    faq_parser.add_argument("--output", help="Write JSON result to file")

    spc_parser = competition_sub.add_parser("spc", help="SPC prompt submission commands")
    spc_sub = spc_parser.add_subparsers(dest="spc_command", required=True)

    spc_list_parser = spc_sub.add_parser("submissions", help="GET /competitions/spc/submissions")
    _add_pagination_args(spc_list_parser)
    spc_list_parser.add_argument("--param", action="append", help="Extra query parameter KEY=VALUE")
    spc_list_parser.add_argument("--output", help="Write JSON result to file")

    spc_history_parser = spc_sub.add_parser(
        "submission-history",
        help="GET /competitions/spc/submissions/{submission_id}",
    )
    spc_history_parser.add_argument("submission_id", help="SPC submission id")
    _add_pagination_args(spc_history_parser)
    spc_history_parser.add_argument("--param", action="append", help="Extra query parameter KEY=VALUE")
    spc_history_parser.add_argument("--output", help="Write JSON result to file")

    spc_options_parser = spc_sub.add_parser(
        "submission-options",
        help="OPTIONS the SPC submission collection or one submission",
    )
    spc_options_parser.add_argument("submission_id", nargs="?", help="Optional SPC submission id")
    spc_options_parser.add_argument("--output", help="Write JSON result to file")

    spc_create_parser = spc_sub.add_parser(
        "create-submission",
        help="POST /competitions/spc/submissions",
    )
    _add_json_payload_args(spc_create_parser)
    spc_create_parser.add_argument("--output", help="Write JSON result to file")

    spc_update_parser = spc_sub.add_parser(
        "update-submission",
        help="PUT/PATCH /competitions/spc/submissions/{submission_id}",
    )
    spc_update_parser.add_argument("submission_id", help="SPC submission id")
    spc_update_parser.add_argument("--method", choices=["PUT", "PATCH"], default="PATCH")
    _add_json_payload_args(spc_update_parser)
    spc_update_parser.add_argument("--output", help="Write JSON result to file")


def handle_competition(args: argparse.Namespace, registry: EndpointRegistry) -> int:
    if args.competition_command == "list":
        result = _call(
            args,
            registry,
            "/competitions",
            "GET",
            params={"limit": args.limit, "offset": args.offset},
        )
        write_json(result, args.output)
        return 0
    if args.competition_command == "get":
        result = _call(
            args,
            registry,
            "/competitions/{competition_id}",
            "GET",
            path_vars={"competition_id": args.competition_id},
        )
        write_json(result, args.output)
        return 0
    if args.competition_command == "agreement":
        result = _call(
            args,
            registry,
            "/competitions/{competition_id}/agreement",
            args.method,
            path_vars={"competition_id": args.competition_id},
        )
        write_json(result, args.output)
        return 0
    if args.competition_command == "leaderboard":
        params = parse_key_values(args.param)
        if args.method == "GET":
            params = {"limit": args.limit, "offset": args.offset, **params}
        for key in ("board", "aggregate", "order"):
            value = getattr(args, key)
            if value is not None:
                params[key] = value
        if args.scope == "competition":
            endpoint_path = "/competitions/{competition_id}/boards/{board_type}"
            path_vars = {
                "competition_id": args.identifier,
                "board_type": args.board_type or "leader",
            }
        else:
            if args.board_type is not None:
                raise ValueError("--board-type applies only to --scope competition")
            endpoint_path = "/consultant/boards/{board_type}"
            path_vars = {"board_type": args.identifier}
        result = _call(
            args,
            registry,
            endpoint_path,
            args.method,
            path_vars=path_vars,
            params=params,
        )
        write_json(result, args.output)
        return 0
    if args.competition_command == "guidelines":
        result = _call(
            args,
            registry,
            "/competitions/{competition_id}/agreement",
            "GET",
            path_vars={"competition_id": args.competition_id},
        )
        write_json(result, args.output)
        return 0
    if args.competition_command == "faq":
        result = _call(
            args,
            registry,
            "/competitions/{competition_id}",
            "GET",
            path_vars={"competition_id": args.competition_id},
        )
        response = dict(result.get("response") or {})
        body = response.get("body")
        if result.get("ok") and isinstance(body, dict):
            response["body"] = {
                "id": body.get("id"),
                "name": body.get("name"),
                "faq": body.get("faq"),
            }
            result = {**result, "response": response}
        write_json(result, args.output)
        return 0
    if args.competition_command == "spc":
        collection_path = "/competitions/spc/submissions"
        item_path = "/competitions/spc/submissions/{submission_id}"
        if args.spc_command == "submissions":
            params = {"limit": args.limit, "offset": args.offset, **parse_key_values(args.param)}
            result = _call(args, registry, collection_path, "GET", params=params)
        elif args.spc_command == "submission-history":
            params = {"limit": args.limit, "offset": args.offset, **parse_key_values(args.param)}
            result = _call(
                args,
                registry,
                item_path,
                "GET",
                path_vars={"submission_id": args.submission_id},
                params=params,
            )
        elif args.spc_command == "submission-options":
            if args.submission_id:
                result = _call(
                    args,
                    registry,
                    item_path,
                    "OPTIONS",
                    path_vars={"submission_id": args.submission_id},
                )
            else:
                result = _call(args, registry, collection_path, "OPTIONS")
        elif args.spc_command == "create-submission":
            result = _call(args, registry, collection_path, "POST", json_body=_json_payload(args))
        elif args.spc_command == "update-submission":
            result = _call(
                args,
                registry,
                item_path,
                args.method,
                path_vars={"submission_id": args.submission_id},
                json_body=_json_payload(args),
            )
        else:
            raise AssertionError(args.spc_command)
        write_json(result, args.output)
        return 0
    raise AssertionError(args.competition_command)
