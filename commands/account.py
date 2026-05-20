from __future__ import annotations

import argparse

from ..core.auth import session_from_cookies
from ..core.client import WqbClient
from ..core.io import read_json_file, write_json
from ..core.registry import EndpointRegistry


ACCOUNT_PATHS = {
    "email-change": "/user/email/change",
    "email-reverify": "/user/email/reverify",
    "email-verify": "/user/email/verify",
    "password-change": "/user/password/change",
    "password-forgot": "/user/password/forgot",
    "password-reset": "/user/password/reset",
    "token": "/user/token",
}


def add_account_parser(subparsers: argparse._SubParsersAction) -> None:
    account = subparsers.add_parser("account", help="Account mutation/token commands")
    account_sub = account.add_subparsers(dest="account_command", required=True)
    for name, path in ACCOUNT_PATHS.items():
        parser = account_sub.add_parser(name, help=f"GET/POST {path}")
        parser.add_argument("--method", choices=["GET", "POST"], default="GET")
        parser.add_argument("--input", help="JSON file for POST body")
        parser.add_argument("--execute", action="store_true", help="Actually execute POST")
        parser.add_argument("--output", help="Write JSON result to file")


def handle_account(args: argparse.Namespace, registry: EndpointRegistry) -> int:
    if args.account_command in ACCOUNT_PATHS:
        endpoint = registry.get(ACCOUNT_PATHS[args.account_command])
        payload = read_json_file(args.input) if args.input else None
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, args.method, json_body=payload, execute=args.execute)
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    raise AssertionError(args.account_command)
