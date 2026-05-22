from __future__ import annotations

import argparse
import time
from typing import Any

from ..core.auth import session_from_cookies
from ..core.client import WqbClient
from ..core.io import parse_key_values, read_json_file, write_json
from ..core.registry import EndpointRegistry
from .common import add_range_argument, put_bool_if_set, put_if_set, put_range_if_set


ALPHA_RANGE_FILTERS = [
    ("--date-created", "dateCreated"),
    ("--start-date", "os.startDate"),
    ("--settings-decay", "settings.decay"),
    ("--settings-truncation", "settings.truncation"),
    ("--is-sharpe", "is.sharpe"),
    ("--is-returns", "is.returns"),
    ("--is-pnl", "is.pnl"),
    ("--is-turnover", "is.turnover"),
    ("--is-drawdown", "is.drawdown"),
    ("--is-margin", "is.margin"),
    ("--is-fitness", "is.fitness"),
    ("--is-book-size", "is.bookSize"),
    ("--is-long-count", "is.longCount"),
    ("--is-short-count", "is.shortCount"),
    ("--os-sharpe60", "os.sharpe60"),
    ("--os-sharpe125", "os.sharpe125"),
    ("--os-sharpe250", "os.sharpe250"),
    ("--os-sharpe500", "os.sharpe500"),
    ("--os-is-sharpe-ratio", "os.osISSharpeRatio"),
    ("--os-pre-close-sharpe", "os.preCloseSharpe"),
    ("--os-pre-close-sharpe-ratio", "os.preCloseSharpeRatio"),
    ("--is-self-correlation", "is.selfCorrelation"),
    ("--is-prod-correlation", "is.prodCorrelation"),
]

ALPHA_DIRECT_FILTERS = [
    ("language", "settings.language"),
    ("status", "status"),
    ("category", "category"),
    ("settings_region", "settings.region"),
    ("settings_instrument_type", "settings.instrumentType"),
    ("settings_universe", "settings.universe"),
    ("settings_delay", "settings.delay"),
    ("settings_neutralization", "settings.neutralization"),
    ("settings_unit_handling", "settings.unitHandling"),
    ("settings_nan_handling", "settings.nanHandling"),
    ("settings_pasteurization", "settings.pasteurization"),
]

ALPHA_RANGE_HELP = {
    "--date-created": "dateCreated range. Common: >2026-01-01T00:00:00-0500, <2026-05-01T00:00:00-0500.",
    "--start-date": "os.startDate range.",
    "--settings-decay": "settings.decay range. Common values: 0, 1, 3, 4, 5, 6, 8, 10, 12, 15, 20, 30, 60.",
    "--settings-truncation": "settings.truncation range. Common values: 0.08, 0.01, 0.04, 0.05, 0.06, 0.1, 0.15, 0.2.",
    "--is-sharpe": "is.sharpe range. Common candidate filters: >=1.58 or >=1; weak bucket: >=1 and <1.58.",
    "--is-returns": "is.returns range.",
    "--is-pnl": "is.pnl range.",
    "--is-turnover": "is.turnover range. Common: >=0.01 and <=0.7.",
    "--is-drawdown": "is.drawdown range.",
    "--is-margin": "is.margin range. Common: >=0.001; looser: >=0.0005.",
    "--is-fitness": "is.fitness range. Common: >=1 or >=1.5.",
    "--is-book-size": "is.bookSize range.",
    "--is-long-count": "is.longCount range.",
    "--is-short-count": "is.shortCount range.",
    "--os-sharpe60": "os.sharpe60 range.",
    "--os-sharpe125": "os.sharpe125 range.",
    "--os-sharpe250": "os.sharpe250 range. Common order field: -os.sharpe250.",
    "--os-sharpe500": "os.sharpe500 range. Common order field: -os.sharpe500.",
    "--os-is-sharpe-ratio": "os.osISSharpeRatio range.",
    "--os-pre-close-sharpe": "os.preCloseSharpe range.",
    "--os-pre-close-sharpe-ratio": "os.preCloseSharpeRatio range.",
    "--is-self-correlation": "is.selfCorrelation range.",
    "--is-prod-correlation": "is.prodCorrelation range. Common flags: >0.5, >0.7.",
}


def add_alpha_parser(subparsers: argparse._SubParsersAction) -> None:
    alpha = subparsers.add_parser("alpha", help="Alpha API commands")
    alpha_sub = alpha.add_subparsers(dest="alpha_command", required=True)

    get_parser = alpha_sub.add_parser("get", help="GET /alphas/{alpha_id}")
    get_parser.add_argument("alpha_id", help="Alpha id")
    get_parser.add_argument("--output", help="Write JSON result to file")

    list_parser = alpha_sub.add_parser("list", help="GET /users/self/alphas")
    list_parser.add_argument("--limit", default="20", help="Result limit")
    list_parser.add_argument("--offset", default="0", help="Result offset")
    list_parser.add_argument("--name", help="Name filter. Prefix with ~ or = for explicit name operator.")
    list_parser.add_argument("--competition", action=argparse.BooleanOptionalAction, default=None, help="Competition filter")
    list_parser.add_argument("--type", dest="alpha_type", help="Alpha type. Common: REGULAR; occasional: SUPER.")
    list_parser.add_argument("--language", help="settings.language filter. Common: FASTEXPR; also PYTHON.")
    add_range_argument(list_parser, "--date-created", help=ALPHA_RANGE_HELP["--date-created"])
    list_parser.add_argument("--favorite", action=argparse.BooleanOptionalAction, default=None, help="Favorite filter")
    list_parser.add_argument("--color", help="Alpha color filter. Common: GREEN, BLUE, PURPLE, YELLOW, RED.")
    list_parser.add_argument("--tag", help="Alpha tag filter")
    list_parser.add_argument(
        "--hidden",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Hidden filter. Common: --no-hidden for candidates; --hidden for bad archived alphas.",
    )
    list_parser.add_argument("--status", help="Status filter. Common: UNSUBMITTED.")
    list_parser.add_argument("--category", help="Alpha category filter")
    list_parser.add_argument("--date-submitted", help="dateSubmitted filter/range accepted by BRAIN API")
    list_parser.add_argument("--date-submitted-after", help="dateSubmitted lower bound, passed as dateSubmitted>")
    list_parser.add_argument("--date-submitted-before", help="dateSubmitted upper bound, passed as dateSubmitted<")
    add_range_argument(list_parser, "--start-date", help=ALPHA_RANGE_HELP["--start-date"])
    list_parser.add_argument("--settings-region", help="settings.region filter. Common: USA, EUR, GLB, ASI, CHN, JPN, AMR.")
    list_parser.add_argument("--settings-instrument-type", help="settings.instrumentType filter. Common: EQUITY.")
    list_parser.add_argument(
        "--settings-universe",
        help="settings.universe filter. Common: TOP3000, TOP1000, TOP500, TOP2500, TOP1200, TOP800, TOP600, TOP2000U.",
    )
    list_parser.add_argument("--settings-delay", help="settings.delay filter. Common: 1; also 0.")
    add_range_argument(list_parser, "--settings-decay", help=ALPHA_RANGE_HELP["--settings-decay"])
    list_parser.add_argument(
        "--settings-neutralization",
        help="settings.neutralization filter. Common: SUBINDUSTRY, INDUSTRY, MARKET, NONE, SECTOR, STATISTICAL.",
    )
    add_range_argument(list_parser, "--settings-truncation", help=ALPHA_RANGE_HELP["--settings-truncation"])
    list_parser.add_argument("--settings-unit-handling", help="settings.unitHandling filter. Common: VERIFY.")
    list_parser.add_argument("--settings-nan-handling", help="settings.nanHandling filter. Common: ON, OFF.")
    list_parser.add_argument("--settings-pasteurization", help="settings.pasteurization filter. Common: ON.")
    for flag, _ in ALPHA_RANGE_FILTERS[4:]:
        add_range_argument(list_parser, flag, help=ALPHA_RANGE_HELP[flag])
    list_parser.add_argument(
        "--order",
        help=(
            "Sort order. Common: -dateSubmitted, dateSubmitted, -is.sharpe, "
            "-is.fitness, -is.returns, -is.turnover, -os.sharpe250, -os.sharpe500"
        ),
    )
    list_parser.add_argument("--param", action="append", help="Extra query parameter KEY=VALUE")
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
        _add_wait_argument(parser)
        parser.add_argument("--output", help="Write JSON result to file")

    all_parser = alpha_sub.add_parser("all", help="GET /alphas")
    all_parser.add_argument("--limit", default="20", help="Result limit")
    all_parser.add_argument("--offset", default="0", help="Result offset")
    all_parser.add_argument("--output", help="Write JSON result to file")

    check_parser = alpha_sub.add_parser("check", help="GET /alphas/{alpha_id}/check")
    check_parser.add_argument("alpha_id", help="Alpha id")
    _add_wait_argument(check_parser)
    check_parser.add_argument("--output", help="Write JSON result to file")

    recordsets_parser = alpha_sub.add_parser("recordsets", help="GET /alphas/{alpha_id}/recordsets")
    recordsets_parser.add_argument("alpha_id", help="Alpha id")
    _add_wait_argument(recordsets_parser)
    recordsets_parser.add_argument("--output", help="Write JSON result to file")

    related_parser = alpha_sub.add_parser("related", help="GET /alphas/{alpha_id}/alphas")
    related_parser.add_argument("alpha_id", help="Alpha id")
    _add_wait_argument(related_parser)
    related_parser.add_argument("--output", help="Write JSON result to file")

    recordset_parser = alpha_sub.add_parser("recordset", help="GET /alphas/{alpha_id}/recordsets/{record_set_name}")
    recordset_parser.add_argument("alpha_id", help="Alpha id")
    recordset_parser.add_argument("name", help="Record set name, e.g. pnl, sharpe, turnover, yearly-stats")
    _add_wait_argument(recordset_parser)
    recordset_parser.add_argument("--output", help="Write JSON result to file")

    for recordset_name in ["pnl", "sharpe", "yearly-stats"]:
        parser = alpha_sub.add_parser(recordset_name, help=f"GET /alphas/{{alpha_id}}/recordsets/{recordset_name}")
        parser.add_argument("alpha_id", help="Alpha id")
        _add_wait_argument(parser)
        parser.add_argument("--output", help="Write JSON result to file")

    patch_parser = alpha_sub.add_parser("patch", help="PATCH /alphas/{alpha_id}")
    patch_parser.add_argument("alpha_id", help="Alpha id")
    patch_parser.add_argument("--input", required=True, help="JSON file containing patch body")
    patch_parser.add_argument("--output", help="Write JSON result to file")

    submit_parser = alpha_sub.add_parser("submit", help="POST /alphas/{alpha_id}/submit")
    submit_parser.add_argument("alpha_id", help="Alpha id")
    submit_parser.add_argument(
        "--max-wait-seconds",
        type=float,
        default=1800.0,
        help="Maximum total wait time while following submit Retry-After",
    )
    submit_parser.add_argument(
        "--retry-after-multiplier",
        type=float,
        default=2.0,
        help="Multiplier applied to submit Retry-After polling waits",
    )
    submit_parser.add_argument("--output", help="Write JSON result to file")

    correlation_parser = alpha_sub.add_parser("correlation", help="Alpha correlation commands")
    correlation_sub = correlation_parser.add_subparsers(dest="correlation_command", required=True)
    self_parser = correlation_sub.add_parser("self", help="GET /alphas/{alpha_id}/correlations/self")
    self_parser.add_argument("alpha_id", help="Alpha id")
    _add_wait_argument(self_parser)
    self_parser.add_argument("--output", help="Write JSON result to file")
    base_parser = correlation_sub.add_parser("base", help="GET /alphas/{alpha_id}/correlations")
    base_parser.add_argument("alpha_id", help="Alpha id")
    _add_wait_argument(base_parser)
    base_parser.add_argument("--output", help="Write JSON result to file")
    prod_parser = correlation_sub.add_parser("prod", help="GET /alphas/{alpha_id}/correlations/prod")
    prod_parser.add_argument("alpha_id", help="Alpha id")
    _add_wait_argument(prod_parser)
    prod_parser.add_argument("--output", help="Write JSON result to file")
    power_pool_parser = correlation_sub.add_parser("power-pool", help="GET /alphas/{alpha_id}/correlations/power-pool")
    power_pool_parser.add_argument("alpha_id", help="Alpha id")
    _add_wait_argument(power_pool_parser)
    power_pool_parser.add_argument("--output", help="Write JSON result to file")

    performance_parser = alpha_sub.add_parser("performance-comparison", help="GET /alphas/{alpha_id}/performance-comparison")
    performance_parser.add_argument("alpha_id", help="Alpha id")
    _add_wait_argument(performance_parser)
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
        result = _call_waiting_alpha(client, prepared, args.max_wait_seconds)
        write_json(result, args.output)
        return 0 if result.get("ok") else 1
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
        _put_name_filter(params, args.name)
        put_bool_if_set(params, "competition", args.competition)
        put_if_set(params, "type", args.alpha_type)
        put_bool_if_set(params, "favorite", args.favorite)
        put_if_set(params, "color", args.color)
        put_if_set(params, "tag", args.tag)
        put_bool_if_set(params, "hidden", args.hidden)
        put_if_set(params, "dateSubmitted", args.date_submitted)
        put_if_set(params, "dateSubmitted>", args.date_submitted_after)
        put_if_set(params, "dateSubmitted<", args.date_submitted_before)
        for attr, param_key in ALPHA_DIRECT_FILTERS:
            put_if_set(params, param_key, getattr(args, attr))
        for flag, param_key in ALPHA_RANGE_FILTERS:
            put_range_if_set(params, param_key, getattr(args, flag.removeprefix("--").replace("-", "_")))
        put_if_set(params, "order", args.order)
        params.update(parse_key_values(args.param))
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
        result = _call_waiting_alpha(client, prepared, args.max_wait_seconds)
        write_json(result, args.output)
        return 0 if result.get("ok") else 1
    if args.alpha_command in {"pnl", "sharpe", "yearly-stats"}:
        endpoint = registry.get(f"/alphas/{{alpha_id}}/recordsets/{args.alpha_command}")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"alpha_id": args.alpha_id})
        result = _call_waiting_alpha(client, prepared, args.max_wait_seconds)
        write_json(result, args.output)
        return 0 if result.get("ok") else 1
    if args.alpha_command == "related":
        endpoint = registry.get("/alphas/{alpha_id}/alphas")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"alpha_id": args.alpha_id})
        result = _call_waiting_alpha(client, prepared, args.max_wait_seconds)
        write_json(result, args.output)
        return 0 if result.get("ok") else 1
    if args.alpha_command == "patch":
        endpoint = registry.get("/alphas/{alpha_id}")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(
            endpoint,
            "PATCH",
            path_vars={"alpha_id": args.alpha_id},
            json_body=read_json_file(args.input),
        )
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.alpha_command == "submit":
        endpoint = registry.get("/alphas/{alpha_id}/submit")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "POST", path_vars={"alpha_id": args.alpha_id})
        result = _submit_alpha(
            client,
            registry,
            prepared,
            args.alpha_id,
            args.max_wait_seconds,
            args.retry_after_multiplier,
        )
        write_json(result, args.output)
        return 0 if result.get("ok") else 1
    if args.alpha_command == "check":
        endpoint = registry.get("/alphas/{alpha_id}/check")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"alpha_id": args.alpha_id})
        result = _call_waiting_alpha(client, prepared, args.max_wait_seconds)
        write_json(result, args.output)
        return 0 if result.get("ok") else 1
    if args.alpha_command == "recordsets":
        endpoint = registry.get("/alphas/{alpha_id}/recordsets")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"alpha_id": args.alpha_id})
        result = _call_waiting_alpha(client, prepared, args.max_wait_seconds)
        write_json(result, args.output)
        return 0 if result.get("ok") else 1
    if args.alpha_command == "correlation":
        if args.correlation_command == "base":
            endpoint = registry.get("/alphas/{alpha_id}/correlations")
            client = WqbClient(registry, session_from_cookies(args.cookies))
            prepared = client.prepare(endpoint, "GET", path_vars={"alpha_id": args.alpha_id})
            result = _call_waiting_alpha(client, prepared, args.max_wait_seconds)
            write_json(result, args.output)
            return 0 if result.get("ok") else 1
        if args.correlation_command == "self":
            endpoint = registry.get("/alphas/{alpha_id}/correlations/self")
            client = WqbClient(registry, session_from_cookies(args.cookies))
            prepared = client.prepare(endpoint, "GET", path_vars={"alpha_id": args.alpha_id})
            result = _call_waiting_alpha(client, prepared, args.max_wait_seconds)
            write_json(result, args.output)
            return 0 if result.get("ok") else 1
        if args.correlation_command == "prod":
            endpoint = registry.get("/alphas/{alpha_id}/correlations/prod")
            client = WqbClient(registry, session_from_cookies(args.cookies))
            prepared = client.prepare(endpoint, "GET", path_vars={"alpha_id": args.alpha_id})
            result = _call_waiting_alpha(client, prepared, args.max_wait_seconds)
            write_json(result, args.output)
            return 0 if result.get("ok") else 1
        if args.correlation_command == "power-pool":
            endpoint = registry.get("/alphas/{alpha_id}/correlations/power-pool")
            client = WqbClient(registry, session_from_cookies(args.cookies))
            prepared = client.prepare(endpoint, "GET", path_vars={"alpha_id": args.alpha_id})
            result = _call_waiting_alpha(client, prepared, args.max_wait_seconds)
            write_json(result, args.output)
            return 0 if result.get("ok") else 1
        raise AssertionError(args.correlation_command)
    if args.alpha_command == "performance-comparison":
        endpoint = registry.get("/alphas/{alpha_id}/performance-comparison")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"alpha_id": args.alpha_id})
        result = _call_waiting_alpha(client, prepared, args.max_wait_seconds)
        write_json(result, args.output)
        return 0 if result.get("ok") else 1
    raise AssertionError(args.alpha_command)


def _add_wait_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--max-wait-seconds",
        type=float,
        default=900.0,
        help="Maximum total wait time while following Retry-After",
    )


def _call_waiting_alpha(client: WqbClient, prepared: Any, max_wait_seconds: float) -> dict[str, Any]:
    result = client.call(prepared, wait_retry_after=True, max_wait_seconds=max_wait_seconds)
    result["classification"] = _classify_waiting_alpha_result(result)
    result["ok"] = bool(result.get("ok") and result["classification"]["ok"])
    return result


def _classify_waiting_alpha_result(result: dict[str, Any]) -> dict[str, Any]:
    response = result.get("response", {})
    if response.get("wait_timed_out"):
        return {"ok": False, "reason": "alpha_wait_timed_out"}
    if not result.get("ok"):
        return {"ok": False, "reason": "alpha_request_failed"}
    body = response.get("body")
    if body == "":
        return {"ok": False, "reason": "alpha_empty_body_after_wait"}
    return {"ok": True, "reason": "alpha_result_ready"}


def _put_name_filter(params: dict[str, Any], value: str | None) -> None:
    if value is None:
        return
    text = value.strip()
    if not text:
        return
    if text[0] in {"~", "="}:
        params["name" + text[0]] = text[1:]
        return
    params["name~"] = text


def _submit_alpha(
    client: WqbClient,
    registry: EndpointRegistry,
    prepared: Any,
    alpha_id: str,
    max_wait_seconds: float,
    retry_after_multiplier: float,
) -> dict[str, Any]:
    post_result = client.call(prepared)
    classified = _classify_submit_post(post_result)

    if classified["submit_code"] in {200, 403, 460} and not post_result.get("ok"):
        return {
            "ok": classified["submit_code"] == 200,
            "alpha_id": alpha_id,
            "submit_code": classified["submit_code"],
            "classification": classified,
            "post": post_result,
        }

    if not post_result.get("ok"):
        return {
            "ok": False,
            "alpha_id": alpha_id,
            "submit_code": classified["submit_code"],
            "classification": classified,
            "post": post_result,
        }

    submit_endpoint = registry.get("/alphas/{alpha_id}/submit")
    wait_prepared = client.prepare(submit_endpoint, "GET", path_vars={"alpha_id": alpha_id})
    wait_result = _wait_submit_status(
        client,
        wait_prepared,
        max_wait_seconds=max_wait_seconds,
        retry_after_multiplier=retry_after_multiplier,
    )

    alpha_endpoint = registry.get("/alphas/{alpha_id}")
    alpha_prepared = client.prepare(alpha_endpoint, "GET", path_vars={"alpha_id": alpha_id})
    alpha_result = client.call(alpha_prepared)
    wait_classified = _classify_submit_wait(wait_result)

    return {
        "ok": post_result.get("ok") and wait_classified["submit_code"] == 200 and alpha_result.get("ok"),
        "alpha_id": alpha_id,
        "submit_code": wait_classified["submit_code"],
        "classification": wait_classified,
        "post_classification": classified,
        "post": post_result,
        "wait": wait_result,
        "alpha": alpha_result,
    }


def _wait_submit_status(
    client: WqbClient,
    prepared: Any,
    *,
    max_wait_seconds: float,
    retry_after_multiplier: float,
) -> dict[str, Any]:
    started = time.time()
    retries = 0
    wait_events: list[dict[str, Any]] = []
    last_result: dict[str, Any] | None = None
    retry_after_multiplier = max(retry_after_multiplier, 0.0)

    while True:
        result = _raw_client_call(client, prepared)
        last_result = result
        response = result.get("response", {})
        status_code = response.get("status_code")
        retry_after = response.get("retry_after")
        elapsed_seconds = time.time() - started

        if status_code == 429:
            sleep_seconds = 60.0
            if elapsed_seconds + sleep_seconds > max_wait_seconds:
                response["wait_timed_out"] = True
                wait_events.append(
                    {
                        "status_code": status_code,
                        "retry_after": retry_after,
                        "sleep_seconds": 0,
                        "reason": "max_wait_seconds_exceeded",
                    }
                )
                break
            wait_events.append(
                {
                    "status_code": status_code,
                    "retry_after": retry_after,
                    "sleep_seconds": sleep_seconds,
                    "reason": "rate_limited",
                }
            )
            time.sleep(sleep_seconds)
            retries += 1
            continue

        if retry_after:
            sleep_seconds = float(retry_after) * retry_after_multiplier
            if elapsed_seconds + sleep_seconds > max_wait_seconds:
                response["wait_timed_out"] = True
                wait_events.append(
                    {
                        "status_code": status_code,
                        "retry_after": float(retry_after),
                        "sleep_seconds": 0,
                        "reason": "max_wait_seconds_exceeded",
                    }
                )
                break
            wait_events.append(
                {
                    "status_code": status_code,
                    "retry_after": float(retry_after),
                    "sleep_seconds": sleep_seconds,
                }
            )
            time.sleep(sleep_seconds)
            retries += 1
            continue

        break

    assert last_result is not None
    last_response = last_result.setdefault("response", {})
    last_response["retries"] = retries
    last_response["wait_events"] = wait_events
    last_response["wait_timed_out"] = bool(last_response.get("wait_timed_out"))
    last_response["max_wait_seconds"] = max_wait_seconds
    return last_result


def _raw_client_call(client: WqbClient, prepared: Any) -> dict[str, Any]:
    if not prepared.executable:
        return {
            "ok": False,
            "reason": prepared.reason,
            "request": prepared.__dict__,
        }
    started = time.time()
    response = client.session.request(
        prepared.method,
        prepared.url,
        params=prepared.params,
        json=prepared.json_body,
        timeout=60,
        allow_redirects=False,
    )
    elapsed_ms = int((time.time() - started) * 1000)
    body = _response_body(response)
    return {
        "ok": 200 <= response.status_code < 400,
        "endpoint": prepared.endpoint,
        "request": {
            "method": prepared.method,
            "url": prepared.url,
            "params": prepared.params,
            "mutating": prepared.mutating,
        },
        "response": {
            "status_code": response.status_code,
            "reason": response.reason,
            "elapsed_ms": elapsed_ms,
            "content_type": response.headers.get("Content-Type", "").split(";")[0],
            "allow": response.headers.get("Allow"),
            "retry_after": response.headers.get("Retry-After"),
            "retries": 0,
            "wait_events": [],
            "wait_timed_out": False,
            "max_wait_seconds": None,
            "location": response.headers.get("Location"),
            "body": body,
        },
    }


def _response_body(response: Any) -> Any:
    text = response.text
    if text:
        try:
            return response.json()
        except ValueError:
            return text
    return ""


def _classify_submit_post(result: dict[str, Any]) -> dict[str, Any]:
    response = result.get("response", {})
    status_code = response.get("status_code")
    body = response.get("body")
    checks = _checks_by_name(body)
    regular = checks.get("REGULAR_SUBMISSION", {})
    super_submission = checks.get("SUPER_SUBMISSION", {})
    already_submitted = checks.get("ALREADY_SUBMITTED", {})

    if status_code == 403:
        if regular.get("result") == "FAIL" or super_submission.get("result") == "FAIL":
            return {
                "submit_code": 460,
                "reason": "submission_quota_or_rule_failed",
                "regular_submission": regular,
                "super_submission": super_submission,
                "already_submitted": already_submitted,
            }
        if already_submitted.get("result") == "FAIL":
            return {
                "submit_code": 200,
                "reason": "already_submitted",
                "regular_submission": regular,
                "super_submission": super_submission,
                "already_submitted": already_submitted,
            }
        return {
            "submit_code": 403,
            "reason": "forbidden",
            "regular_submission": regular,
            "super_submission": super_submission,
            "already_submitted": already_submitted,
        }
    if status_code == 401:
        return {"submit_code": 401, "reason": "unauthorized"}
    if isinstance(status_code, int) and 200 <= status_code < 400:
        return {"submit_code": status_code, "reason": "submit_api_accepted"}
    return {"submit_code": status_code, "reason": "failed"}


def _classify_submit_wait(result: dict[str, Any]) -> dict[str, Any]:
    response = result.get("response", {})
    status_code = response.get("status_code")
    body = response.get("body")
    checks = _checks_by_name(body)
    regular = checks.get("REGULAR_SUBMISSION", {})
    super_submission = checks.get("SUPER_SUBMISSION", {})
    power_pool_monthly = checks.get("POWER_POOL_MONTHLY_SUBMISSION", {})
    power_pool = checks.get("POWER_POOL_SUBMISSION", {})
    already_submitted = checks.get("ALREADY_SUBMITTED", {})

    if response.get("wait_timed_out"):
        return {
            "submit_code": 408,
            "reason": "submit_wait_timed_out",
            "checks": checks,
        }
    if status_code == 200:
        return {
            "submit_code": 200,
            "reason": "submitted_or_submit_checks_complete",
            "checks": checks,
        }
    if status_code == 403:
        if regular.get("result") == "FAIL" or super_submission.get("result") == "FAIL":
            return {
                "submit_code": 460,
                "reason": "daily_submission_quota_or_submission_rule_failed",
                "checks": checks,
            }
        if power_pool_monthly.get("result") == "FAIL":
            return {
                "submit_code": 461,
                "reason": "power_pool_monthly_submission_failed",
                "checks": checks,
            }
        if power_pool.get("result") == "FAIL":
            return {
                "submit_code": 462,
                "reason": "power_pool_submission_failed",
                "checks": checks,
            }
        if already_submitted.get("result") == "FAIL":
            return {
                "submit_code": 200,
                "reason": "already_submitted",
                "checks": checks,
            }
        return {
            "submit_code": 403,
            "reason": "submit_forbidden",
            "checks": checks,
        }
    if status_code == 401:
        return {"submit_code": 401, "reason": "unauthorized", "checks": checks}
    if status_code == 429:
        return {"submit_code": 429, "reason": "rate_limited", "checks": checks}
    return {"submit_code": status_code, "reason": "submit_failed", "checks": checks}


def _checks_by_name(body: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(body, dict):
        return {}
    checks = body.get("is", {}).get("checks")
    if not isinstance(checks, list):
        checks = body.get("checks")
    if not isinstance(checks, list):
        return {}
    return {check.get("name"): check for check in checks if isinstance(check, dict) and check.get("name")}
