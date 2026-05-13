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

    queries = json.loads((node_dir / f"queries__{region}_D{delay}_{category}.json").read_text(encoding="utf-8"))
    summary = json.loads((node_dir / f"external_material_summary__{region}_D{delay}_{category}.json").read_text(encoding="utf-8"))

    paper_lines = "\n".join(
        f"- `{row['title']}` ({row['published']})"
        for row in summary["top_external_papers"][:10]
    ) or "- No external papers."

    conclusion_lines = "\n".join(
        f"- {line}" for line in summary["external_conclusions"]
    ) or "- No external conclusions."

    text = f"""# External Materials And Papers

## Queries
- {", ".join(queries['queries'])}

## Outputs
- queries__{region}_D{delay}_{category}.json
- arxiv_results__{region}_D{delay}_{category}.json
- external_material_summary__{region}_D{delay}_{category}.json

## Top Papers
{paper_lines}

## External Conclusions
{conclusion_lines}
"""
    out_path = node_dir / "node_summary.md"
    out_path.write_text(text, encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
