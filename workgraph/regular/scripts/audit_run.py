from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validate_node_bundle import validate as validate_node_bundle


RUN_ROOT_ALLOWED = {
    "run_manifest.json",
    "graph_state.json",
    "commander_log.md",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def assert_inside(child: Path, parent: Path) -> None:
    child_resolved = child.resolve()
    parent_resolved = parent.resolve()
    if child_resolved != parent_resolved and parent_resolved not in child_resolved.parents:
        raise SystemExit(f"Path escapes boundary: {child}")


def audit_run(run_dir: Path) -> dict[str, Any]:
    root = repo_root()
    assert_inside(run_dir, root / "research_runs")

    issues: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    state_path = run_dir / "graph_state.json"
    state: dict[str, Any] = {}
    if state_path.is_file():
        state = load_json(state_path)
    else:
        issues.append({"type": "missing_graph_state", "path": str(state_path)})

    steps = state.get("steps", []) if isinstance(state.get("steps"), list) else []
    step_dirs = {Path(step.get("node_dir", "")).resolve() for step in steps if step.get("node_dir")}

    nodes_dir = run_dir / "nodes"
    node_dirs = sorted([p for p in nodes_dir.iterdir() if p.is_dir()]) if nodes_dir.is_dir() else []
    for node_dir in node_dirs:
        if node_dir.resolve() not in step_dirs:
            issues.append({
                "type": "node_dir_not_in_graph_state_steps",
                "node_dir": str(node_dir),
            })
        report = validate_node_bundle(run_dir, node_dir)
        if not report["ok"]:
            issues.append({
                "type": "invalid_node_bundle",
                "node_dir": str(node_dir),
                "errors": report["errors"],
            })
        if report["warnings"]:
            warnings.append({
                "type": "node_bundle_warning",
                "node_dir": str(node_dir),
                "warnings": report["warnings"],
            })

    if len(steps) != len(node_dirs):
        issues.append({
            "type": "graph_state_step_count_mismatch",
            "steps": len(steps),
            "node_dirs": len(node_dirs),
        })

    for child in run_dir.iterdir():
        if child.is_file() and child.name not in RUN_ROOT_ALLOWED:
            warnings.append({
                "type": "unexpected_run_root_file",
                "path": str(child),
                "reason": "run-level summaries or batch artifacts should be written only after completion or inside node outputs",
            })

    current_node = state.get("current_node")
    if current_node and state.get("status") != "node_assigned":
        issues.append({
            "type": "current_node_status_inconsistent",
            "current_node": current_node,
            "status": state.get("status"),
        })

    return {
        "run_dir": str(run_dir),
        "ok": not issues,
        "issue_count": len(issues),
        "warning_count": len(warnings),
        "issues": issues,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit a workgraph run for graph compliance.")
    parser.add_argument("run_dir")
    args = parser.parse_args()

    report = audit_run(Path(args.run_dir).resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
