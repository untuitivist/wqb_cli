from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: read_diagnosis_next_node.py DIAGNOSIS_JSON")

    path = Path(sys.argv[1]).resolve()
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    print(obj.get("next_node") or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
