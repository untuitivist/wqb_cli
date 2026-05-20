from __future__ import annotations

import argparse

from .common import run_endpoint
from ..core.registry import EndpointRegistry


def add_platform_parser(subparsers: argparse._SubParsersAction) -> None:
    platform = subparsers.add_parser("platform", help="Misc platform API commands")
    platform_sub = platform.add_subparsers(dest="platform_command", required=True)
    for name, help_text in {
        "achievements": "GET /achievements",
        "agreements": "GET /agreements",
        "captcha": "GET /captcha",
        "messages": "GET /messages",
        "tags": "GET /tags",
        "teams": "GET /teams",
        "video-courses": "GET /video-courses",
    }.items():
        parser = platform_sub.add_parser(name, help=help_text)
        parser.add_argument("--output", help="Write JSON result to file")

    icon_parser = platform_sub.add_parser("achievement-icon", help="GET /achievements/{achievement_id}/icon")
    icon_parser.add_argument("achievement_id", help="Achievement id")
    icon_parser.add_argument("--output", help="Write JSON result to file")

    level_icon_parser = platform_sub.add_parser("competition-level-icon", help="GET /competition-levels/{competition_level_id}/icon")
    level_icon_parser.add_argument("competition_level_id", help="Competition level id")
    level_icon_parser.add_argument("--output", help="Write JSON result to file")


def handle_platform(args: argparse.Namespace, registry: EndpointRegistry) -> int:
    simple_paths = {
        "achievements": "/achievements",
        "agreements": "/agreements",
        "captcha": "/captcha",
        "messages": "/messages",
        "tags": "/tags",
        "teams": "/teams",
        "video-courses": "/video-courses",
    }
    if args.platform_command in simple_paths:
        return run_endpoint(args, registry, path=simple_paths[args.platform_command])
    if args.platform_command == "achievement-icon":
        return run_endpoint(
            args,
            registry,
            path="/achievements/{achievement_id}/icon",
            path_vars={"achievement_id": args.achievement_id},
        )
    if args.platform_command == "competition-level-icon":
        return run_endpoint(
            args,
            registry,
            path="/competition-levels/{competition_level_id}/icon",
            path_vars={"competition_level_id": args.competition_level_id},
        )
    raise AssertionError(args.platform_command)
