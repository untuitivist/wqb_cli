from __future__ import annotations

import argparse
from typing import Any

from ..core.auth import session_from_cookies
from ..core.client import WqbClient
from ..core.io import write_json
from ..core.registry import EndpointRegistry


RANGE_HELP = "Range filter. Use VALUE, >VALUE, >=VALUE, <VALUE, <=VALUE, or =VALUE."


def add_range_argument(parser: argparse.ArgumentParser, name: str, **kwargs: Any) -> None:
    parser.add_argument(name, help=kwargs.pop("help", RANGE_HELP), **kwargs)


def put_if_set(params: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        params[key] = value


def put_bool_if_set(params: dict[str, Any], key: str, value: bool | None) -> None:
    if value is not None:
        params[key] = "true" if value else "false"


def put_range_if_set(params: dict[str, Any], key: str, value: str | None) -> None:
    if value is None:
        return
    text = value.strip()
    for op in (">=", "<=", ">", "<", "="):
        if text.startswith(op):
            params[key + op] = text[len(op) :].strip()
            return
    params[key] = text


def run_endpoint(
    args: argparse.Namespace,
    registry: EndpointRegistry,
    *,
    path: str,
    method: str = "GET",
    path_vars: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json_body: Any = None,
    wait_retry_after: bool = False,
    execute: bool = False,
) -> int:
    endpoint = registry.get(path)
    client = WqbClient(registry, session_from_cookies(args.cookies))
    prepared = client.prepare(
        endpoint,
        method,
        path_vars=path_vars or {},
        params=params or {},
        json_body=json_body,
        execute=execute,
    )
    output = getattr(args, "output", None)
    result = client.call(prepared, wait_retry_after=wait_retry_after)
    write_json(result, output)
    return 0
