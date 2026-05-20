from __future__ import annotations

import argparse
from pathlib import Path

from ..core.io import write_json
from ..core.paths import RESOURCES_ROOT


DOCS_ROOT = RESOURCES_ROOT / "docs" / "commands"


def add_docs_parser(subparsers: argparse._SubParsersAction) -> None:
    docs = subparsers.add_parser("docs", help="Discover bundled command documentation")
    docs_sub = docs.add_subparsers(dest="docs_command", required=True)

    list_parser = docs_sub.add_parser("list", help="List documented command nodes")
    list_parser.add_argument("--output", help="Write JSON result to file")

    show_parser = docs_sub.add_parser("show", help="Show one documentation file")
    show_parser.add_argument("path", help="Doc path under wqb_cli/resources/docs/commands, e.g. shortcut/README.md")
    show_parser.add_argument("--output", help="Write JSON result to file")


def handle_docs(args: argparse.Namespace) -> int:
    if args.docs_command == "list":
        nodes = []
        for readme in sorted(DOCS_ROOT.rglob("README.md")):
            rel = readme.relative_to(DOCS_ROOT).as_posix()
            nodes.append(
                {
                    "node": rel.removesuffix("/README.md"),
                    "readme": rel,
                    "examples": [
                        path.relative_to(DOCS_ROOT).as_posix()
                        for path in sorted((readme.parent / "examples").glob("*.md"))
                    ]
                    if (readme.parent / "examples").exists()
                    else [],
                }
            )
        write_json({"ok": True, "docs_root": str(DOCS_ROOT), "nodes": nodes}, args.output)
        return 0
    if args.docs_command == "show":
        target = (DOCS_ROOT / args.path).resolve()
        root = DOCS_ROOT.resolve()
        if root not in target.parents and target != root:
            write_json({"ok": False, "reason": "path_outside_docs_root", "path": args.path}, args.output)
            return 1
        if target.is_dir():
            target = target / "README.md"
        if not target.exists() or not target.is_file():
            write_json({"ok": False, "reason": "doc_not_found", "path": args.path}, args.output)
            return 1
        write_json({"ok": True, "path": str(target), "text": target.read_text(encoding="utf-8-sig")}, args.output)
        return 0
    raise AssertionError(args.docs_command)
