"""Run the workspace version of wqb_cli without relying on a global install."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def main() -> None:
    root = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(
        "wqb_cli",
        root / "__init__.py",
        submodule_search_locations=[str(root)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load local wqb_cli package")
    package = importlib.util.module_from_spec(spec)
    sys.modules["wqb_cli"] = package
    spec.loader.exec_module(package)

    from wqb_cli.cli import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
