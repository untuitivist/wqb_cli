from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def git_status(root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        return []
    return [line for line in proc.stdout.splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize a WQB workgraph run.")
    parser.add_argument("--timestamp", help="Optional timestamp in YYYYMMDD_HHMMSS format.")
    args = parser.parse_args()

    root = repo_root()
    timestamp = args.timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = root / "research_runs" / f"run_{timestamp}"
    nodes_dir = run_dir / "nodes"
    nodes_dir.mkdir(parents=True, exist_ok=False)

    manifest = {
        "run_id": f"run_{timestamp}",
        "created_at_local": datetime.now().isoformat(timespec="seconds"),
        "repo_root": str(root),
        "run_dir": str(run_dir),
        "allowed_write_roots": [str(run_dir)],
        "workgraph_dir": str(root / "workgraph" / "regular"),
        "node_registry": str(root / "workgraph" / "regular" / "node_registry.json"),
        "baseline_git_status": git_status(root),
    }
    state = {
        "run_id": manifest["run_id"],
        "status": "initialized",
        "current_node": None,
        "completed_nodes": [],
        "blocked_nodes": [],
        "steps": [],
        "decisions": [],
    }

    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "graph_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "commander_log.md").write_text(f"# Commander Log\n\nRun: `{manifest['run_id']}`\n", encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
