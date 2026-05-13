from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit("Usage: write_summary.py NODE_DIR REGION DELAY CATEGORY")

    node_dir = Path(sys.argv[1]).resolve()
    region = sys.argv[2]
    delay = sys.argv[3]
    category = sys.argv[4].upper()

    actions = json.loads(
        (node_dir / f"submission_actions__{region}_D{delay}_{category}.json").read_text(
            encoding="utf-8-sig"
        )
    )
    results = json.loads(
        (node_dir / f"submit_results__{region}_D{delay}_{category}.json").read_text(
            encoding="utf-8-sig"
        )
    )

    lines = [
        f"# M summary: {region}/D{delay}/{category}",
        "",
        f"- mode: {actions['mode']}",
        f"- planned count: {actions['count']}",
        f"- executed result count: {results['count']}",
        "",
        "## results",
    ]
    if results["results"]:
        for row in results["results"][:5]:
            lines.append(
                f"- {row['candidate_id']} / {row['alpha_id']} / executed={row['executed']} / status={row['status']}"
            )
    else:
        lines.append("- none")

    (node_dir / "node_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
