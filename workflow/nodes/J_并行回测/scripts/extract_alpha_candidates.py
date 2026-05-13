from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    if len(sys.argv) != 5:
        raise SystemExit("Usage: extract_alpha_candidates.py NODE_DIR REGION DELAY CATEGORY")

    node_dir = Path(sys.argv[1]).resolve()
    region = sys.argv[2].upper()
    delay = int(sys.argv[3])
    category = sys.argv[4].upper()
    tower_id = f"{region}_D{delay}_{category}"

    primary = load_json(node_dir / f"primary_batch__{tower_id}.json")
    raw = load_json(node_dir / f"concurrent_simulate__{tower_id}.json")

    candidates = []
    payload = None
    try:
        payload = json.loads(raw["stdout"])
    except Exception:
        payload = None

    if isinstance(payload, list):
        child_ids: list[str] = []
        if payload and isinstance(payload[0], dict):
            child_ids = payload[0].get("json", {}).get("children", []) or []

        repo_root = Path(__file__).resolve().parents[4]
        python_exe = r"D:\_soft\Anaconda\envs\WQBRAIN\python.exe"
        cli_path = repo_root / "wqb_core" / "simulation" / "get_simulation_status.py"

        for idx, child_id in enumerate(child_ids):
            candidate_meta = primary["candidates"][idx] if idx < len(primary["candidates"]) else None
            cmd = [
                python_exe,
                str(cli_path),
                "--simulation-url",
                f"https://api.worldquantbrain.com/simulations/{child_id}",
            ]
            proc = subprocess.run(
                cmd,
                cwd=repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            child_payload = None
            try:
                child_payload = json.loads(proc.stdout)
            except Exception:
                child_payload = {
                    "returncode": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                }
            child_json = child_payload.get("json") if isinstance(child_payload, dict) else None
            alpha_id = child_json.get("alpha") if isinstance(child_json, dict) else None
            candidates.append(
                {
                    "index": idx,
                    "candidate_id": None if candidate_meta is None else candidate_meta["id"],
                    "regular": None if candidate_meta is None else candidate_meta["regular"],
                    "child_simulation_id": child_id,
                    "alpha_id": alpha_id,
                    "child_simulation": child_payload,
                }
            )

    out = {
        "region": region,
        "delay": delay,
        "category": category,
        "count": len(candidates),
        "alphas": candidates,
    }
    out_path = node_dir / f"alpha_candidates__{tower_id}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
