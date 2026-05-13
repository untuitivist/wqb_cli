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

    slow_path = node_dir / f"slow_final_check__{region}_D{delay}_{category}.json"
    cand_path = node_dir / f"submission_candidates__{region}_D{delay}_{category}.json"
    slow = json.loads(slow_path.read_text(encoding="utf-8-sig"))
    candidates = json.loads(cand_path.read_text(encoding="utf-8-sig"))

    lines = [
        f"# L summary: {region}/D{delay}/{category}",
        "",
        f"- source K: {Path(slow['source_k_dir']).name}",
        f"- evaluated count: {slow['evaluated_count']}",
        f"- approved count: {slow['approved_count']}",
        f"- next node: {slow['next_node']}",
    ]
    if slow.get("rollback_reason"):
        lines.append(f"- rollback reason: {slow['rollback_reason']}")
    lines.extend(
        [
            "",
            "## approved candidates",
        ]
    )
    if candidates["candidates"]:
        for row in candidates["candidates"][:5]:
            checks = row["slow_checks"]
            lines.append(
                "- "
                + f"{row['candidate_id']} / {row['alpha_id']} / "
                + f"prod={checks['prod_correlation_max']} / "
                + f"self={checks['self_correlation_max']} / "
                + f"pp={checks['powerpool_correlation_max']} / "
                + f"regular_submission={checks['regular_submission']}"
            )
    else:
        lines.append("- none")

    (node_dir / "node_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
