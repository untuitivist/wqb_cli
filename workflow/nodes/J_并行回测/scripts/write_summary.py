from __future__ import annotations

import json
import sys
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    if len(sys.argv) != 5:
        raise SystemExit("Usage: write_summary.py NODE_DIR REGION DELAY CATEGORY")

    node_dir = Path(sys.argv[1]).resolve()
    region = sys.argv[2].upper()
    delay = int(sys.argv[3])
    category = sys.argv[4].upper()
    tower_id = f"{region}_D{delay}_{category}"

    primary = load_json(node_dir / f"primary_batch__{tower_id}.json")
    raw = load_json(node_dir / f"concurrent_simulate__{tower_id}.json")
    alphas = load_json(node_dir / f"alpha_candidates__{tower_id}.json")

    lines = [
        "# Parallel Simulation",
        "",
        "## Inputs",
        "- I: primary expression batch",
        "",
        "## Tower",
        f"- `{region} / D{delay} / {category}`",
        "",
        "## Batch Settings",
        f"- concurrency: {primary['concurrency']}",
        f"- slot_count: {primary['slot_count']}",
        f"- selected candidates: {primary['batch_size']}",
        f"- policy: {'GLB 5*4' if region == 'GLB' else 'non-GLB 10*8'}",
        "",
        "## Command Result",
        f"- returncode: {raw['returncode']}",
        f"- extracted alpha rows: {alphas['count']}",
        "",
        "## Candidate IDs",
    ]
    for cid in primary["candidate_ids"]:
        lines.append(f"- {cid}")
    (node_dir / "node_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(node_dir / "node_summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
