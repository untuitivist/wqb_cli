from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit("Usage: extract_used_fields.py NODE_DIR REGION DELAY CATEGORY")

    node_dir = Path(sys.argv[1]).resolve()
    region = sys.argv[2]
    delay = sys.argv[3]
    category = sys.argv[4].upper()

    active_path = node_dir / f"active_tower_alphas__{region}_D{delay}_{category}__WQBRAIN.json"
    out_path = node_dir / f"used_fields_by_alpha__{region}_D{delay}_{category}.json"

    text = active_path.read_text(encoding="utf-8")
    data = json.loads(text)
    results = data[0]["json"]["results"]

    field_pat = re.compile(r"\banl\d+_[A-Za-z0-9_]+\b")
    rows = []
    for row in results:
        code = row.get("regular", {}).get("code", "") or ""
        fields = sorted(set(field_pat.findall(code)))
        rows.append(
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "fields": fields,
                "operatorCount": row.get("regular", {}).get("operatorCount"),
                "tags": row.get("tags", []),
                "stage": row.get("stage"),
                "status": row.get("status"),
            }
        )

    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
