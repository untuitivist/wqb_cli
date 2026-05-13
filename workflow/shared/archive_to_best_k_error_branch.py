from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def step_num(path: Path) -> int:
    return int(path.name.split("_", 1)[0])


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: archive_to_best_k_error_branch.py RUN_DIR CURRENT_K_DIR")

    run_dir = Path(sys.argv[1]).resolve()
    current_k_dir = Path(sys.argv[2]).resolve()
    if not run_dir.is_dir():
        raise SystemExit(f"Run dir not found: {run_dir}")
    if not current_k_dir.is_dir():
        raise SystemExit(f"Current K dir not found: {current_k_dir}")

    current_diag_path = next(current_k_dir.glob("diagnosis__*.json"), None)
    if current_diag_path is None:
        raise SystemExit("Current K diagnosis file not found")

    current_diag = load_json(current_diag_path)
    best_hist = current_diag.get("best_historical_k")
    if not best_hist:
        print(json.dumps({"action": "noop", "reason": "no_best_historical_k"}, ensure_ascii=False))
        return 0
    if current_diag.get("next_node") != "BEST_K_BRANCH":
        print(json.dumps({"action": "noop", "reason": "current_k_not_requesting_best_k_branch"}, ensure_ascii=False))
        return 0

    best_step = int(best_hist["step_num"])
    best_dir_name = best_hist["dir_name"]
    best_k_dir = run_dir / best_dir_name
    if not best_k_dir.is_dir():
        raise SystemExit(f"Best historical K dir not found: {best_k_dir}")

    branch_root = best_k_dir / "error_branch"
    branch_root.mkdir(parents=True, exist_ok=True)

    current_step = step_num(current_k_dir)
    now = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d_%H%M%S")
    branch_dir = branch_root / f"{now}__from_{best_step:02d}_to_{current_step:02d}"
    branch_dir.mkdir(parents=True, exist_ok=True)

    moved = []
    for child in sorted(run_dir.iterdir(), key=lambda p: (0 if p.is_dir() else 1, p.name)):
        if not child.is_dir():
            continue
        try:
            num = step_num(child)
        except Exception:
            continue
        if num <= best_step:
            continue
        target = branch_dir / child.name
        shutil.move(str(child), str(target))
        moved.append(child.name)

    manifest = {
        "action": "archived_to_best_k_error_branch",
        "source_run_dir": str(run_dir),
        "current_k_dir": str(current_k_dir),
        "current_k_step": current_step,
        "selected_best_k_dir": str(best_k_dir),
        "selected_best_k_step": best_step,
        "selected_best_k_quality_summary": best_hist.get("quality_summary", {}),
        "selected_best_k_next_node": best_hist.get("next_node"),
        "selected_best_k_rollback_target": best_hist.get("rollback_target"),
        "selected_best_k_rollback_reason": best_hist.get("rollback_reason"),
        "branch_dir": str(branch_dir),
        "moved_directories": moved,
    }

    manifest_path = branch_dir / "branch_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
