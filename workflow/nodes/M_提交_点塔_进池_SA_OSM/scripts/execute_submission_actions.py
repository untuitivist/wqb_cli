from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_json(pyexe: str, script: Path, args: list[str], timeout: int = 300) -> dict:
    proc = subprocess.run(
        [pyexe, str(script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed: {script.name}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


def main() -> int:
    if len(sys.argv) != 5:
        raise SystemExit("Usage: execute_submission_actions.py NODE_DIR REGION DELAY CATEGORY MODE")

    node_dir = Path(sys.argv[1]).resolve()
    region = sys.argv[2]
    delay = sys.argv[3]
    category = sys.argv[4].upper()
    mode = sys.argv[5].strip().lower()

    root_dir = Path(__file__).resolve().parents[4]
    pyexe = sys.executable
    submit_script = root_dir / "wqb_core" / "simulation" / "submit.py"
    actions_path = node_dir / f"submission_actions__{region}_D{delay}_{category}.json"
    actions = json.loads(actions_path.read_text(encoding="utf-8-sig"))

    results = []
    for action in actions.get("actions", []):
        alpha_id = action["alpha_id"]
        if mode != "execute":
            results.append(
                {
                    "candidate_id": action["candidate_id"],
                    "alpha_id": alpha_id,
                    "executed": False,
                    "status": "SKIPPED_BY_MODE",
                    "mode": mode,
                }
            )
            continue

        try:
            submit_payload = run_json(pyexe, submit_script, ["--alpha-id", alpha_id], timeout=300)
            results.append(
                {
                    "candidate_id": action["candidate_id"],
                    "alpha_id": alpha_id,
                    "executed": True,
                    "status": "OK",
                    "submit": submit_payload,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "candidate_id": action["candidate_id"],
                    "alpha_id": alpha_id,
                    "executed": True,
                    "status": "FAILED",
                    "error": str(exc),
                }
            )

    payload = {
        "region": region,
        "delay": int(delay),
        "category": category,
        "mode": mode,
        "count": len(results),
        "results": results,
    }
    (node_dir / f"submit_results__{region}_D{delay}_{category}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
