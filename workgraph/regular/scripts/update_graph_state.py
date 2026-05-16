from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_output_bundle(node_dir: Path) -> list[str]:
    missing = []
    for name in [
        "process_log.md",
        "evidence_index.json",
        "validation_report.json",
        "handoff.md",
        "node_result.json",
    ]:
        if not (node_dir / name).exists():
            missing.append(name)
    if not (node_dir / "outputs").is_dir():
        missing.append("outputs/")
    return missing


def main() -> None:
    parser = argparse.ArgumentParser(description="Update workgraph state from a node_result.json.")
    parser.add_argument("run_dir")
    parser.add_argument("node_dir")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    node_dir = Path(args.node_dir).resolve()
    if run_dir != node_dir and run_dir not in node_dir.parents:
        raise SystemExit("node_dir must be inside run_dir")

    result_path = node_dir / "node_result.json"
    if not result_path.exists():
        raise SystemExit(f"Missing node_result.json: {result_path}")
    missing_bundle = validate_output_bundle(node_dir)
    if missing_bundle:
        raise SystemExit(f"Missing required node output bundle files: {missing_bundle}")

    state_path = run_dir / "graph_state.json"
    state = load_json(state_path)
    result = load_json(result_path)
    node_id = result.get("node_id")
    status = result.get("status")
    if status not in {"success", "blocked", "degraded", "failed"}:
        raise SystemExit(f"Invalid node status: {status}")

    for step in state.get("steps", []):
        if Path(step.get("node_dir", "")).resolve() == node_dir:
            step["status"] = status
            step["result_path"] = str(result_path)
            break

    if status in {"success", "degraded"}:
        if node_id not in state["completed_nodes"]:
            state["completed_nodes"].append(node_id)
        state["status"] = "ready_for_next_decision"
    elif status == "blocked":
        state["blocked_nodes"].append(node_id)
        state["status"] = "blocked"
    else:
        state["status"] = "failed"

    state["current_node"] = None
    state["decisions"].append(
        {
            "node_id": node_id,
            "status": status,
            "next_recommendation": result.get("next_recommendation"),
            "blocking_reason": result.get("blocking_reason"),
        }
    )
    write_json(state_path, state)
    print(state["status"])


if __name__ == "__main__":
    main()
