from __future__ import annotations

import argparse
import subprocess

import requests

from ..core.io import write_json
from ..core.upgrade import UpgradeError, upgrade, upgrade_status


def add_upgrade_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("upgrade", help="Check or install a verified stable GitHub release in this Python environment")
    parser.add_argument("--version", dest="target_version", help="Exact stable release version, e.g. 0.6.3 or v0.6.3")
    preview = parser.add_mutually_exclusive_group()
    preview.add_argument("--check", action="store_true", help="Check release metadata without installing")
    preview.add_argument("--dry-run", action="store_true", help="Preview the selected release without downloading or installing the wheel")
    parser.add_argument("--reinstall", action="store_true", help="Reinstall even when the selected version is already installed")
    parser.add_argument("--allow-downgrade", action="store_true", help="Allow an explicitly selected older stable release")
    parser.add_argument("--output", help="Write JSON result to file")
    parser.add_argument("--status", help="Read a Windows upgrade job's status_path receipt")
    parser.add_argument("--wait", action="store_true", help="With --status, wait up to 60 seconds for the upgrade process")


def handle_upgrade(args: argparse.Namespace) -> int:
    try:
        if args.status:
            if args.target_version or args.check or args.dry_run or args.reinstall or args.allow_downgrade:
                raise UpgradeError("invalid_upgrade_options", "--status cannot be combined with release-selection options")
            result = upgrade_status(args.status, wait=args.wait)
        elif args.wait:
            raise UpgradeError("invalid_upgrade_options", "--wait requires --status PATH")
        else:
            result = upgrade(target_version=args.target_version, check=args.check, dry_run=args.dry_run,
                             reinstall=args.reinstall, allow_downgrade=args.allow_downgrade, output=args.output)
    except UpgradeError as error:
        result = error.as_dict()
    except requests.RequestException as error:
        result = {"ok": False, "reason": "release_network_error", "detail": type(error).__name__}
    except subprocess.TimeoutExpired as error:
        result = {"ok": False, "reason": "upgrade_process_timed_out", "detail": "The update process exceeded its wait budget; verify the installed version before retrying",
                  "timeout_seconds": error.timeout}
    except (OSError, ValueError, KeyError, TypeError) as error:
        result = {"ok": False, "reason": "upgrade_failed", "detail": str(error)}
    write_json(result, args.output)
    return 0 if result["ok"] else 1
