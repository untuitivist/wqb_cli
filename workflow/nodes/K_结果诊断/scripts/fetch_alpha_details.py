from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 6:
        raise SystemExit("Usage: fetch_alpha_details.py RUN_ROOT NODE_DIR REGION DELAY CATEGORY")

    run_root = Path(sys.argv[1]).resolve()
    node_dir = Path(sys.argv[2]).resolve()
    region = sys.argv[3]
    delay = sys.argv[4]
    category = sys.argv[5].upper()
    current_step = int(node_dir.name.split("_", 1)[0])

    repo_root = Path(__file__).resolve().parents[4]
    finder = repo_root / "workflow" / "shared" / "find_latest_node_dir.py"
    proc = subprocess.run(
        [sys.executable, str(finder), str(run_root), "J_parallel_simulation", str(current_step)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    j_dir = Path(proc.stdout.strip())

    source = j_dir / f"alpha_candidates__{region}_D{delay}_{category}.json"
    target = node_dir / f"alpha_details__{region}_D{delay}_{category}.json"

    candidates = json.loads(source.read_text(encoding="utf-8"))
    cli_path = repo_root / "wqb_core" / "alpha" / "get_alpha_details.py"
    python_exe = Path(r"D:\_soft\Anaconda\envs\WQBRAIN\python.exe")

    rows = []
    for item in candidates["alphas"]:
        alpha_id = item.get("alpha_id")
        result: dict[str, object] = {
            "candidate_id": item.get("candidate_id"),
            "regular": item.get("regular"),
            "child_simulation_id": item.get("child_simulation_id"),
            "alpha_id": alpha_id,
        }
        if not alpha_id:
            result["detail_error"] = "missing alpha_id"
            rows.append(result)
            continue

        completed = subprocess.run(
            [str(python_exe), str(cli_path), "--alpha-id", alpha_id],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
            check=False,
        )
        result["returncode"] = completed.returncode
        result["stdout"] = completed.stdout
        result["stderr"] = completed.stderr
        if completed.returncode == 0:
            try:
                result["detail"] = json.loads(completed.stdout)
            except json.JSONDecodeError as exc:
                result["detail_error"] = f"json decode error: {exc}"
        else:
            result["detail_error"] = "command failed"
        rows.append(result)

    payload = {
        "region": region,
        "delay": int(delay),
        "category": category,
        "count": len(rows),
        "alphas": rows,
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
