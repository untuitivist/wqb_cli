from __future__ import annotations

import json
import sys
from pathlib import Path


def step_num(path: Path) -> int:
    return int(path.name.split("_", 1)[0])


def find_latest_node_dir(run_dir: Path, slug: str, before_step: int | None = None) -> Path:
    matches: list[tuple[int, Path]] = []
    for child in run_dir.iterdir():
        if not child.is_dir():
            continue
        parts = child.name.split("_node_", 1)
        if len(parts) != 2:
            continue
        try:
            step = int(parts[0])
        except Exception:
            continue
        if before_step is not None and step >= before_step:
            continue
        if parts[1] == slug:
            matches.append((step, child))
    if not matches:
        raise FileNotFoundError(f"No node directory found for slug: {slug}")
    matches.sort(key=lambda x: x[0])
    return matches[-1][1]


def main() -> int:
    if len(sys.argv) != 7:
        raise SystemExit(
            "Usage: prepare_submission_actions.py RUN_DIR NODE_DIR REGION DELAY CATEGORY MODE"
        )

    run_dir = Path(sys.argv[1]).resolve()
    node_dir = Path(sys.argv[2]).resolve()
    region = sys.argv[3]
    delay = sys.argv[4]
    category = sys.argv[5].upper()
    mode = sys.argv[6].strip().lower()

    node_dir.mkdir(parents=True, exist_ok=True)
    current_step = step_num(node_dir)
    l_dir = find_latest_node_dir(run_dir, "L_slow_final_check", before_step=current_step)
    source_path = l_dir / f"submission_candidates__{region}_D{delay}_{category}.json"
    payload = json.loads(source_path.read_text(encoding="utf-8-sig"))

    actions = []
    for row in payload.get("candidates", []):
        actions.append(
            {
                "candidate_id": row["candidate_id"],
                "alpha_id": row["alpha_id"],
                "regular": row.get("regular"),
                "mode": mode,
                "planned_actions": [
                    {
                        "type": "submit",
                        "enabled": mode == "execute",
                    }
                ],
                "target_objectives": [
                    "submit",
                    "light_tower",
                    "pool",
                    "super_alpha",
                    "osmosis",
                ],
            }
        )

    plan = {
        "region": region,
        "delay": int(delay),
        "category": category,
        "mode": mode,
        "source_l_dir": str(l_dir),
        "count": len(actions),
        "actions": actions,
    }
    (node_dir / f"submission_actions__{region}_D{delay}_{category}.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
