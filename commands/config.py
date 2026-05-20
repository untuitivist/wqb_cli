from __future__ import annotations

import argparse

from ..core.auth import session_from_cookies
from ..core.client import WqbClient
from ..core.config_store import get_config_value, init_config, load_config, parse_config_value, save_config, set_config_value
from ..core.io import write_json
from ..core.registry import EndpointRegistry
from ..core.secrets import keyring_available, set_secret


def add_config_parser(subparsers: argparse._SubParsersAction) -> None:
    config = subparsers.add_parser("config", help="Local CLI config and platform configuration commands")
    config.add_argument("--config", dest="config_path", help="Path to local config.json")
    config_sub = config.add_subparsers(dest="config_command", required=True)

    init_parser = config_sub.add_parser("init", help="Create wqb_cli/local/config.json")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing config")
    init_parser.add_argument("--output", help="Write JSON result to file")

    list_parser = config_sub.add_parser("list", help="List local CLI config")
    list_parser.add_argument("--output", help="Write JSON result to file")

    get_parser = config_sub.add_parser("get", help="Get one local CLI config key")
    get_parser.add_argument("key", help="Dot key, e.g. defaults.region")
    get_parser.add_argument("--output", help="Write JSON result to file")

    set_parser = config_sub.add_parser("set", help="Set one local CLI config key")
    set_parser.add_argument("key", help="Dot key, e.g. defaults.region")
    set_parser.add_argument("value", help="JSON scalar/object/array or plain string")
    set_parser.add_argument("--output", help="Write JSON result to file")

    secret_parser = config_sub.add_parser("set-secret", help="Store a secret in keyring")
    secret_parser.add_argument("key", choices=["auth.password"], help="Secret key")
    secret_parser.add_argument("value", help="Secret value")
    secret_parser.add_argument("--service", default="wqb-cli", help="Keyring service name")
    secret_parser.add_argument("--username", help="Keyring username; defaults to auth.email")
    secret_parser.add_argument("--output", help="Write JSON result to file")

    platform_parser = config_sub.add_parser("platform", help="GET /configuration")
    platform_parser.add_argument("--output", help="Write JSON result to file")

    levels_parser = config_sub.add_parser("competition-levels", help="GET /competition-levels")
    levels_parser.add_argument("--output", help="Write JSON result to file")


def handle_config(args: argparse.Namespace, registry: EndpointRegistry) -> int:
    if args.config_command == "init":
        result = {"ok": True, **init_config(args.config_path, force=args.force), "keyring_available": keyring_available()}
        write_json(result, args.output)
        return 0
    if args.config_command == "list":
        result = {
            "ok": True,
            "config_path": str(args.config_path) if args.config_path else None,
            "config": load_config(args.config_path),
            "keyring_available": keyring_available(),
        }
        write_json(result, args.output)
        return 0
    if args.config_command == "get":
        config = load_config(args.config_path)
        try:
            value = get_config_value(config, args.key)
            result = {"ok": True, "key": args.key, "value": value}
        except KeyError:
            result = {"ok": False, "reason": "config_key_not_found", "key": args.key}
        write_json(result, args.output)
        return 0 if result["ok"] else 1
    if args.config_command == "set":
        config = load_config(args.config_path)
        value = parse_config_value(args.value)
        set_config_value(config, args.key, value)
        path = save_config(config, args.config_path)
        write_json({"ok": True, "path": str(path), "key": args.key, "value": value}, args.output)
        return 0
    if args.config_command == "set-secret":
        config = load_config(args.config_path)
        username = args.username or config.get("auth", {}).get("email")
        if not username:
            write_json({"ok": False, "reason": "missing_keyring_username", "hint": "Set auth.email first or pass --username"}, args.output)
            return 1
        result = set_secret(args.service, username, args.value)
        if result.get("ok"):
            set_config_value(config, "auth.keyring_service", args.service)
            set_config_value(config, "auth.keyring_username", username)
            path = save_config(config, args.config_path)
            result["config_path"] = str(path)
            result["key"] = args.key
        write_json(result, args.output)
        return 0 if result.get("ok") else 1
    if args.config_command == "platform":
        endpoint = registry.get("/configuration")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET")
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    if args.config_command == "competition-levels":
        endpoint = registry.get("/competition-levels")
        client = WqbClient(registry, session_from_cookies(args.cookies))
        prepared = client.prepare(endpoint, "GET")
        result = client.call(prepared)
        write_json(result, args.output)
        return 0
    raise AssertionError(args.config_command)
