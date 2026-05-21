from __future__ import annotations

import argparse

from ..core.auth import session_from_cookies
from ..core.client import WqbClient
from ..core.io import parse_key_values, read_json_file, write_json
from ..core.registry import EndpointRegistry
from .common import add_range_argument, put_bool_if_set, put_if_set, put_range_if_set


def add_data_parser(subparsers: argparse._SubParsersAction) -> None:
    data = subparsers.add_parser("data", help="Data API commands")
    data_sub = data.add_subparsers(dest="data_command", required=True)

    categories_parser = data_sub.add_parser("categories", help="GET /data-categories")
    categories_parser.add_argument("--output", help="Write JSON result to file")

    datasets_parser = data_sub.add_parser("datasets", help="GET /data-sets")
    datasets_parser.add_argument("--instrument-type", default="EQUITY", help="Instrument type")
    datasets_parser.add_argument("--region", default="USA", help="Region")
    datasets_parser.add_argument("--delay", default="1", help="Delay")
    datasets_parser.add_argument("--universe", default="TOP3000", help="Universe")
    datasets_parser.add_argument("--limit", default="20", help="Result limit")
    datasets_parser.add_argument("--offset", default="0", help="Result offset")
    datasets_parser.add_argument("--search", help="Search query")
    datasets_parser.add_argument("--category", help="Data category filter")
    datasets_parser.add_argument("--category-id", help="Observed platform category.id filter")
    datasets_parser.add_argument("--theme", action=argparse.BooleanOptionalAction, default=None, help="Theme filter")
    add_range_argument(datasets_parser, "--coverage")
    add_range_argument(datasets_parser, "--value-score")
    add_range_argument(datasets_parser, "--alpha-count")
    add_range_argument(datasets_parser, "--user-count")
    datasets_parser.add_argument(
        "--order",
        help="Sort order. Common: -coverage, coverage, -valueScore, -alphaCount, -userCount, name",
    )
    datasets_parser.add_argument("--param", action="append", help="Extra query parameter KEY=VALUE")
    datasets_parser.add_argument("--output", help="Write JSON result to file")

    dataset_parser = data_sub.add_parser("dataset", help="GET /data-sets/{dataset_id}")
    dataset_parser.add_argument("dataset_id", help="Dataset id")
    dataset_parser.add_argument("--output", help="Write JSON result to file")

    fields_parser = data_sub.add_parser("fields", help="GET /data-fields")
    fields_parser.add_argument("--dataset", help="Dataset id")
    fields_parser.add_argument("--instrument-type", default="EQUITY", help="Instrument type")
    fields_parser.add_argument("--region", default="USA", help="Region")
    fields_parser.add_argument("--delay", default="1", help="Delay")
    fields_parser.add_argument("--universe", default="TOP3000", help="Universe")
    fields_parser.add_argument("--limit", default="20", help="Result limit")
    fields_parser.add_argument("--offset", default="0", help="Result offset")
    fields_parser.add_argument("--search", help="Search query")
    fields_parser.add_argument("--category", help="Data category filter")
    fields_parser.add_argument("--theme", action=argparse.BooleanOptionalAction, default=None, help="Theme filter")
    add_range_argument(fields_parser, "--coverage")
    fields_parser.add_argument("--type", dest="field_type", help="Field type")
    add_range_argument(fields_parser, "--alpha-count")
    add_range_argument(fields_parser, "--user-count")
    fields_parser.add_argument(
        "--order",
        help="Sort order. Common: -coverage, coverage, -alphaCount, -userCount, name, dataset.id",
    )
    fields_parser.add_argument("--param", action="append", help="Extra query parameter KEY=VALUE")
    fields_parser.add_argument("--output", help="Write JSON result to file")

    fields_summary_parser = data_sub.add_parser("fields-summary", help="GET /data-fields/summary")
    fields_summary_parser.add_argument("--output", help="Write JSON result to file")

    dataset_search_parser = data_sub.add_parser("dataset-search", help="GET/POST /data-sets/search")
    dataset_search_parser.add_argument("--method", choices=["GET", "POST"], default="GET")
    dataset_search_parser.add_argument("--input", help="JSON file for POST body")
    dataset_search_parser.add_argument("--execute", action="store_true", help="Actually execute POST")
    dataset_search_parser.add_argument("--output", help="Write JSON result to file")

    field_parser = data_sub.add_parser("field", help="GET /data-fields/{field_id}")
    field_parser.add_argument("field_id", help="Data field id")
    field_parser.add_argument("--output", help="Write JSON result to file")

    operators_parser = data_sub.add_parser("operators", help="GET /operators")
    operators_parser.add_argument("--instrument-type", help="Instrument type")
    operators_parser.add_argument("--region", help="Region")
    operators_parser.add_argument("--delay", help="Delay")
    operators_parser.add_argument("--param", action="append", help="Extra query parameter KEY=VALUE")
    operators_parser.add_argument("--output", help="Write JSON result to file")


def handle_data(args: argparse.Namespace, registry: EndpointRegistry) -> int:
    if args.data_command == "categories":
        endpoint = registry.get("/data-categories")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET")
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.data_command == "datasets":
        endpoint = registry.get("/data-sets")
        params = {
            "instrumentType": args.instrument_type,
            "region": args.region,
            "delay": args.delay,
            "universe": args.universe,
            "limit": args.limit,
            "offset": args.offset,
        }
        put_if_set(params, "search", args.search)
        put_if_set(params, "category", args.category)
        put_if_set(params, "category.id", args.category_id)
        put_bool_if_set(params, "theme", args.theme)
        put_range_if_set(params, "coverage", args.coverage)
        put_range_if_set(params, "valueScore", args.value_score)
        put_range_if_set(params, "alphaCount", args.alpha_count)
        put_range_if_set(params, "userCount", args.user_count)
        put_if_set(params, "order", args.order)
        params.update(parse_key_values(args.param))
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", params=params)
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.data_command == "dataset":
        endpoint = registry.get("/data-sets/{dataset_id}")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"dataset_id": args.dataset_id})
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.data_command == "fields":
        endpoint = registry.get("/data-fields")
        params = {
            "instrumentType": args.instrument_type,
            "region": args.region,
            "delay": args.delay,
            "universe": args.universe,
            "limit": args.limit,
            "offset": args.offset,
        }
        put_if_set(params, "dataset.id", args.dataset)
        put_if_set(params, "search", args.search)
        put_if_set(params, "category", args.category)
        put_bool_if_set(params, "theme", args.theme)
        put_range_if_set(params, "coverage", args.coverage)
        put_if_set(params, "type", args.field_type)
        put_range_if_set(params, "alphaCount", args.alpha_count)
        put_range_if_set(params, "userCount", args.user_count)
        put_if_set(params, "order", args.order)
        params.update(parse_key_values(args.param))
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", params=params)
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.data_command == "field":
        endpoint = registry.get("/data-fields/{field_id}")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", path_vars={"field_id": args.field_id})
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.data_command == "fields-summary":
        endpoint = registry.get("/data-fields/summary")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET")
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.data_command == "dataset-search":
        endpoint = registry.get("/data-sets/search")
        body = read_json_file(args.input) if args.input else None
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, args.method, json_body=body, execute=args.execute)
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.data_command == "operators":
        endpoint = registry.get("/operators")
        params = {}
        if args.instrument_type:
            params["instrumentType"] = args.instrument_type
        if args.region:
            params["region"] = args.region
        if args.delay:
            params["delay"] = args.delay
        params.update(parse_key_values(args.param))
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET", params=params)
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    raise AssertionError(args.data_command)
