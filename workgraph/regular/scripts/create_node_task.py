from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


NODE_DIR_RE = re.compile(r"^(?P<num>\d{2})_(?P<node_id>.+)$")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def assert_inside(child: Path, parent: Path) -> None:
    child_resolved = child.resolve()
    parent_resolved = parent.resolve()
    if child_resolved != parent_resolved and parent_resolved not in child_resolved.parents:
        raise SystemExit(f"Path escapes boundary: {child}")


def next_step(nodes_dir: Path) -> int:
    nums = []
    for child in nodes_dir.iterdir() if nodes_dir.exists() else []:
        if not child.is_dir():
            continue
        match = NODE_DIR_RE.match(child.name)
        if match:
            nums.append(int(match.group("num")))
    return (max(nums) if nums else 0) + 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a single workgraph node task.")
    parser.add_argument("run_dir")
    parser.add_argument("node_id")
    parser.add_argument("--input", dest="extra_input", help="Optional JSON file inside run_dir merged into node_input.json.")
    args = parser.parse_args()

    root = repo_root()
    regular_dir = root / "workgraph" / "regular"
    registry = load_json(regular_dir / "node_registry.json")
    nodes = {node["id"]: node for node in registry["nodes"]}
    if args.node_id not in nodes:
        raise SystemExit(f"Unknown node id: {args.node_id}")

    run_dir = Path(args.run_dir).resolve()
    assert_inside(run_dir, root / "research_runs")
    manifest = load_json(run_dir / "run_manifest.json")
    if Path(manifest["run_dir"]).resolve() != run_dir:
        raise SystemExit("Run manifest does not match requested run_dir")

    nodes_dir = run_dir / "nodes"
    nodes_dir.mkdir(exist_ok=True)
    step = next_step(nodes_dir)
    node_dir = nodes_dir / f"{step:02d}_{args.node_id}"
    node_dir.mkdir(exist_ok=False)
    (node_dir / "outputs").mkdir()

    node_input = {
        "run_dir": str(run_dir),
        "node_dir": str(node_dir),
        "node": nodes[args.node_id],
        "write_boundary": str(node_dir),
        "contracts": {
            "node_contract": str((root / nodes[args.node_id]["contract_path"]).resolve()),
            "nodesubagent_contract": str((regular_dir / "nodesubagent_contract.md").resolve()),
            "node_output_contract": str((regular_dir / "node_output_contract.md").resolve()),
            "subagent_prompt_template": str((regular_dir / "subagent_prompt_template.md").resolve()),
        },
        "required_output_bundle": [
            "process_log.md",
            "evidence_index.json",
            "validation_report.json",
            "handoff.md",
            "node_result.json",
            "outputs/"
        ],
        "upstream_artifacts": {},
        "extra": {},
    }
    if args.extra_input:
        extra_path = Path(args.extra_input).resolve()
        assert_inside(extra_path, run_dir)
        node_input["extra"] = load_json(extra_path)

    write_json(node_dir / "node_input.json", node_input)

    state_path = run_dir / "graph_state.json"
    state = load_json(state_path)
    state["status"] = "node_assigned"
    state["current_node"] = args.node_id
    state["steps"].append({"step": step, "node_id": args.node_id, "node_dir": str(node_dir), "status": "assigned"})
    write_json(state_path, state)
    print(node_dir)


if __name__ == "__main__":
    main()
