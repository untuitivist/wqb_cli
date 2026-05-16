from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FILES = [
    "process_log.md",
    "evidence_index.json",
    "validation_report.json",
    "handoff.md",
    "node_result.json",
]

FINAL_STATUSES = {"success", "blocked", "degraded", "failed"}
VALIDATION_FINAL_STATUSES = {"passed", "warning", "failed"}
REQUIRED_CONSTRAINTS = [
    "write_scope_only_node_dir",
    "used_required_inputs",
    "process_log_complete",
    "evidence_index_complete",
    "validation_report_complete",
    "handoff_complete",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def assert_inside(child: Path, parent: Path) -> None:
    child_resolved = child.resolve()
    parent_resolved = parent.resolve()
    if child_resolved != parent_resolved and parent_resolved not in child_resolved.parents:
        raise SystemExit(f"Path escapes boundary: {child}")


def validate(run_dir: Path, node_dir: Path) -> dict[str, Any]:
    assert_inside(node_dir, run_dir)
    errors: list[str] = []
    warnings: list[str] = []

    for name in REQUIRED_FILES:
        if not (node_dir / name).is_file():
            errors.append(f"missing {name}")
    if not (node_dir / "outputs").is_dir():
        errors.append("missing outputs/")

    node_input: dict[str, Any] = {}
    if (node_dir / "node_input.json").is_file():
        node_input = load_json(node_dir / "node_input.json")
    else:
        errors.append("missing node_input.json")

    result: dict[str, Any] = {}
    if (node_dir / "node_result.json").is_file():
        result = load_json(node_dir / "node_result.json")

    validation_report: dict[str, Any] = {}
    if (node_dir / "validation_report.json").is_file():
        validation_report = load_json(node_dir / "validation_report.json")

    expected_node_id = node_input.get("node", {}).get("id")
    result_node_id = result.get("node_id")
    if expected_node_id and result_node_id != expected_node_id:
        errors.append(f"node_result node_id mismatch: expected {expected_node_id}, got {result_node_id}")

    status = result.get("status")
    if status not in FINAL_STATUSES:
        errors.append(f"invalid node_result status: {status}")

    node_contract = node_input.get("node", {})
    required_outputs = node_contract.get("required_outputs", [])
    if not isinstance(required_outputs, list):
        errors.append("node_input.node.required_outputs must be a list when present")
        required_outputs = []
    for rel in required_outputs:
        if not isinstance(rel, str):
            errors.append(f"required output path is not a string: {rel!r}")
            continue
        out_path = node_dir / rel
        if rel.endswith("/"):
            if not out_path.is_dir():
                errors.append(f"missing required output directory: {rel}")
        elif not out_path.is_file():
            errors.append(f"missing required output file: {rel}")

    constraints = result.get("constraints_checked")
    if not isinstance(constraints, dict):
        errors.append("node_result.constraints_checked missing or not an object")
    else:
        for key in REQUIRED_CONSTRAINTS:
            if constraints.get(key) is not True:
                errors.append(f"constraint not true: {key}")

    validation_status = validation_report.get("status")
    if validation_status == "started":
        errors.append("validation_report still in started status")
    elif validation_status not in VALIDATION_FINAL_STATUSES:
        errors.append(f"invalid validation_report status: {validation_status}")

    checks = validation_report.get("checks")
    if checks is not None and not isinstance(checks, list):
        errors.append("validation_report.checks must be a list when present")
    if isinstance(checks, list):
        failed = [c for c in checks if isinstance(c, dict) and c.get("status") == "failed"]
        if failed and status in {"success", "degraded"}:
            errors.append("node_result cannot be success/degraded when validation_report has failed checks")

    for name in ["process_log.md", "handoff.md"]:
        path = node_dir / name
        if path.is_file() and not path.read_text(encoding="utf-8", errors="replace").strip():
            errors.append(f"{name} is empty")

    evidence = {}
    if (node_dir / "evidence_index.json").is_file():
        evidence = load_json(node_dir / "evidence_index.json")
        inputs_read = evidence.get("inputs_read")
        if inputs_read is not None and not isinstance(inputs_read, list):
            errors.append("evidence_index.inputs_read must be a list when present")
        outputs_written = evidence.get("outputs_written")
        if outputs_written is not None and not isinstance(outputs_written, list):
            errors.append("evidence_index.outputs_written must be a list when present")

    declared_upstreams = node_input.get("upstream_artifacts", {})
    if declared_upstreams and isinstance(evidence.get("inputs_read"), list):
        declared_paths = set()
        for value in declared_upstreams.values():
            if isinstance(value, str):
                declared_paths.add(str((run_dir / value).resolve()) if not Path(value).is_absolute() else str(Path(value).resolve()))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        declared_paths.add(str((run_dir / item).resolve()) if not Path(item).is_absolute() else str(Path(item).resolve()))
        for item in evidence["inputs_read"]:
            if not isinstance(item, dict) or "path" not in item:
                continue
            raw = item["path"]
            if not isinstance(raw, str):
                continue
            path = Path(raw)
            resolved = str(path.resolve() if path.is_absolute() else (run_dir / path).resolve())
            if declared_paths and resolved not in declared_paths and "node_input.json" not in raw:
                warnings.append(f"input read not declared in node_input.upstream_artifacts: {raw}")

    if status == "success" and result.get("blocking_reason") not in (None, ""):
        warnings.append("success node_result has a blocking_reason")

    return {
        "run_dir": str(run_dir),
        "node_dir": str(node_dir),
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a completed workgraph node bundle.")
    parser.add_argument("run_dir")
    parser.add_argument("node_dir")
    args = parser.parse_args()

    report = validate(Path(args.run_dir).resolve(), Path(args.node_dir).resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
