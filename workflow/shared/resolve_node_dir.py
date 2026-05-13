from __future__ import annotations

import re
import sys
from pathlib import Path


PATTERN = re.compile(r"^(?P<num>\d{2})_node_(?P<name>.+)$")


def normalize_name(raw: str) -> str:
    return raw.strip().replace(" ", "_")


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit("Usage: resolve_node_dir.py RUN_DIR NODE_NAME MODE")

    run_dir = Path(sys.argv[1]).resolve()
    node_name = normalize_name(sys.argv[2])
    mode = sys.argv[3].lower()
    if mode not in {"create", "reuse"}:
        raise SystemExit("MODE must be create or reuse")

    run_dir.mkdir(parents=True, exist_ok=True)
    existing: list[tuple[int, Path]] = []
    for child in run_dir.iterdir():
        if not child.is_dir():
            continue
        match = PATTERN.match(child.name)
        if match:
            existing.append((int(match.group("num")), child))

    existing.sort(key=lambda x: x[0])

    expected_suffix = f"_node_{node_name}"
    for num, path in existing:
        if path.name.endswith(expected_suffix):
            if mode == "reuse":
                print(path)
                return 0

    next_num = (existing[-1][0] if existing else 0) + 1
    if next_num > 99:
        print("STEP_LIMIT_EXCEEDED")
        return 99

    target = run_dir / f"{next_num:02d}_node_{node_name}"
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
