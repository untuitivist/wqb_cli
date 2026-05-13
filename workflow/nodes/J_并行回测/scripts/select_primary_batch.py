from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    if len(sys.argv) != 6:
        raise SystemExit("Usage: select_primary_batch.py RUN_DIR NODE_DIR REGION DELAY CATEGORY")

    run_dir = Path(sys.argv[1]).resolve()
    node_dir = Path(sys.argv[2]).resolve()
    region = sys.argv[3].upper()
    delay = int(sys.argv[4])
    category = sys.argv[5].upper()
    tower_id = f"{region}_D{delay}_{category}"
    current_step = int(node_dir.name.split("_", 1)[0])

    repo_root = Path(__file__).resolve().parents[4]
    finder = repo_root / "workflow" / "shared" / "find_latest_node_dir.py"
    proc = subprocess.run(
        [sys.executable, str(finder), str(run_dir), "I_expression_candidates", str(current_step)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    i_dir = Path(proc.stdout.strip())
    expr_obj = load_json(i_dir / f"expression_candidates__{tower_id}.json")
    sim_batch = load_json(i_dir / f"simulation_batch__{tower_id}.json")

    max_batch = 5 if region == "GLB" else 10
    selected_candidates = expr_obj["candidates"][:max_batch]
    selected_batch = sim_batch[:max_batch]

    out = {
        "region": region,
        "delay": delay,
        "category": category,
        "batch_size": len(selected_batch),
        "candidate_ids": [row["id"] for row in selected_candidates],
        "candidates": selected_candidates,
        "simulation_batch": selected_batch,
        "concurrency": 4 if region == "GLB" else 8,
        "slot_count": 5 if region == "GLB" else 10,
    }
    out_path = node_dir / f"primary_batch__{tower_id}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
