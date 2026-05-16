from __future__ import annotations

import argparse
import json
import subprocess
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
        raise SystemExit(proc.stderr.strip() or "git status failed")
    return [line for line in proc.stdout.splitlines() if line.strip()]


def status_path(line: str) -> str:
    raw = line[3:]
    if " -> " in raw:
        raw = raw.split(" -> ", 1)[1]
    return raw.strip().strip('"')


def is_allowed_status(line: str, run_rel: str) -> bool:
    path = status_path(line).replace("\\", "/")
    return path == run_rel or path.startswith(run_rel.rstrip("/") + "/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate that runtime writes stayed inside a run directory.")
    parser.add_argument("run_dir")
    args = parser.parse_args()

    root = repo_root()
    run_dir = Path(args.run_dir).resolve()
    research_root = (root / "research_runs").resolve()
    if research_root != run_dir and research_root not in run_dir.parents:
        raise SystemExit(f"Run dir must be under research_runs: {run_dir}")

    manifest_path = run_dir / "run_manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"Missing run manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    baseline = set(manifest.get("baseline_git_status", []))
    current = set(git_status(root))
    new_changes = sorted(current - baseline)

    run_rel = run_dir.relative_to(root).as_posix()
    violations = [line for line in new_changes if not is_allowed_status(line, run_rel)]
    report = {"run_dir": str(run_dir), "new_change_count": len(new_changes), "violations": violations, "ok": not violations}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
