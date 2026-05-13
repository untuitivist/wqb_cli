from __future__ import annotations

import re
import sys
from pathlib import Path


PATTERN = re.compile(r"^(?P<num>\d{2})_node_(?P<name>.+)$")


def main() -> int:
    if len(sys.argv) not in {3, 4}:
        raise SystemExit("Usage: find_latest_node_dir.py RUN_DIR NODE_SLUG [MAX_STEP]")

    run_dir = Path(sys.argv[1]).resolve()
    slug = sys.argv[2].strip()
    max_step = None
    if len(sys.argv) == 4:
        max_step = int(sys.argv[3])

    matches: list[tuple[int, Path]] = []
    for child in run_dir.iterdir():
        if not child.is_dir():
            continue
        m = PATTERN.match(child.name)
        if not m:
            continue
        step = int(m.group("num"))
        if max_step is not None and step >= max_step:
            continue
        if m.group("name") == slug:
            matches.append((step, child))

    if not matches:
        raise SystemExit(f"No node directory found for slug: {slug}")

    matches.sort(key=lambda x: x[0])
    print(matches[-1][1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
