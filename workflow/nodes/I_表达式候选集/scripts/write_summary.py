from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 5:
        raise SystemExit("Usage: write_summary.py NODE_DIR REGION DELAY CATEGORY")

    node_dir = Path(sys.argv[1]).resolve()
    region = sys.argv[2].upper()
    delay = int(sys.argv[3])
    category = sys.argv[4].upper()
    tower_id = f"{region}_D{delay}_{category}"

    obj = json.loads((node_dir / f"expression_candidates__{tower_id}.json").read_text(encoding="utf-8-sig"))
    lines = [
        "# Expression Candidates",
        "",
        "## Inputs",
        "- D: selected tower",
        "- E: candidate datafields",
        "- F: community/help-center experience",
        "- H: mechanism hypotheses",
        "",
        "## Tower",
        f"- `{region} / D{delay} / {category}`",
        "",
        "## Constraints Applied",
    ]
    for item in obj["expression_build_rules"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Batch Summary",
            f"- candidate fields upstream: {obj['candidate_field_pool_count']}",
            f"- expression candidates: {obj['expression_count']}",
            f"- selected dataset bias: {obj['selected_dataset_bias']}",
            "- all operators: see all_operators.json",
            "",
            "## First 5 Candidates",
        ]
    )
    for row in obj["candidates"][:5]:
        lines.append(f"- `{row['id']}`: {row['regular']}")

    (node_dir / "node_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(node_dir / "node_summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
