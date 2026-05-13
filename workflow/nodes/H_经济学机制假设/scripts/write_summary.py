from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit("Usage: write_summary.py NODE_DIR REGION DELAY CATEGORY")

    node_dir = Path(sys.argv[1]).resolve()
    region = sys.argv[2]
    delay = sys.argv[3]
    category = sys.argv[4].upper()

    hypo_path = node_dir / f"mechanism_hypotheses__{region}_D{delay}_{category}.json"
    obj = json.loads(hypo_path.read_text(encoding="utf-8"))

    lines = []
    for row in obj["hypotheses"]:
        lines.append(
            f"- `{row['id']}`: {', '.join(row['core_fields'])}\n"
            f"  mechanism: {row['economic_logic']}"
        )

    summary = f"""# Mechanism Hypotheses

## Inputs
- B: recent platform titles
- D: selected tower
- E: candidate datafields
- F: community and help-center experience
- G: external papers / user materials / outside evidence

## Tower
- `{region} / D{delay} / {category}`

## Theme Context
- {obj['theme_context']['judgment']}

## External Conclusions
{chr(10).join(f"- {line}" for line in obj.get('external_material_context', {}).get('external_conclusions', []))}

## Hypotheses
{chr(10).join(lines)}
"""
    out_path = node_dir / "node_summary.md"
    out_path.write_text(summary, encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
