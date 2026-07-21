from __future__ import annotations

import argparse
from typing import Any

from ..app_server import serve_app


def add_app_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser("app", help="Run the local WQB Research Desk")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true", help="Do not open the default browser")
    parser.add_argument("--config", dest="config_path")
    parser.add_argument("--database")
    parser.add_argument("--run-root")


def handle_app(args: argparse.Namespace) -> int:
    if not 0 <= args.port <= 65535:
        raise ValueError("port must be between 0 and 65535")
    if args.host not in {"127.0.0.1", "localhost"}:
        raise ValueError("host must be 127.0.0.1 or localhost")
    serve_app(
        host=args.host,
        port=args.port,
        open_browser=not args.no_open,
        config_path_value=args.config_path,
        database_path=args.database,
        run_root=args.run_root,
        registry_path=getattr(args, "registry", None),
        cookie_path=getattr(args, "cookies", None),
    )
    return 0
