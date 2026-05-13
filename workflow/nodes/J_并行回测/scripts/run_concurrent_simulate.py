from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    if len(sys.argv) != 6:
        raise SystemExit("Usage: run_concurrent_simulate.py RUN_DIR NODE_DIR REGION DELAY CATEGORY")

    run_dir = Path(sys.argv[1]).resolve()
    node_dir = Path(sys.argv[2]).resolve()
    region = sys.argv[3].upper()
    delay = int(sys.argv[4])
    category = sys.argv[5].upper()
    tower_id = f"{region}_D{delay}_{category}"

    primary_path = node_dir / f"primary_batch__{tower_id}.json"
    primary = load_json(primary_path)
    batch_path = node_dir / f"primary_batch_payload__{tower_id}.json"
    batch_path.write_text(
        json.dumps(primary["simulation_batch"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    repo_root = Path(__file__).resolve().parents[4]

    cmd = [
        r"D:\_soft\Anaconda\envs\WQBRAIN\python.exe",
        str(repo_root / "wqb_core" / "simulation" / "concurrent_simulate.py"),
        "--targets",
        f"@file:{batch_path}",
        "--concurrency",
        str(primary["concurrency"]),
        "--slot-count",
        str(primary["slot_count"]),
        "--auto-pack",
        "true",
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
        timeout=1800,
    )

    out = {
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
    out_path = node_dir / f"concurrent_simulate__{tower_id}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
