from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


CORR_MAX_THRESHOLD = 0.70


def step_num(path: Path) -> int:
    return int(path.name.split("_", 1)[0])


def find_latest_node_dir(run_dir: Path, slug: str, before_step: int | None = None) -> Path:
    matches: list[tuple[int, Path]] = []
    for child in run_dir.iterdir():
        if not child.is_dir():
            continue
        name = child.name
        parts = name.split("_node_", 1)
        if len(parts) != 2:
            continue
        try:
            step = int(parts[0])
        except Exception:
            continue
        if before_step is not None and step >= before_step:
            continue
        if parts[1] == slug:
            matches.append((step, child))
    if not matches:
        raise FileNotFoundError(f"No node directory found for slug: {slug}")
    matches.sort(key=lambda x: x[0])
    return matches[-1][1]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def run_json(pyexe: str, script: Path, args: list[str], timeout: int = 180) -> dict:
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


def check_result(checks: list[dict], name: str) -> str | None:
    for check in checks:
        if check.get("name") == name:
            return check.get("result")
    return None


def corr_max(payload) -> float | None:
    if isinstance(payload, list) and payload:
        payload = payload[0]
    if isinstance(payload, dict):
        value = payload.get("max")
        try:
            return float(value)
        except Exception:
            return None
    return None


def main() -> int:
    if len(sys.argv) != 6:
        raise SystemExit(
            "Usage: collect_slow_final_checks.py RUN_DIR NODE_DIR REGION DELAY CATEGORY"
        )

    run_dir = Path(sys.argv[1]).resolve()
    node_dir = Path(sys.argv[2]).resolve()
    region = sys.argv[3]
    delay = sys.argv[4]
    category = sys.argv[5].upper()

    node_dir.mkdir(parents=True, exist_ok=True)

    root_dir = Path(__file__).resolve().parents[4]
    pyexe = sys.executable
    current_step = step_num(node_dir)
    k_dir = find_latest_node_dir(run_dir, "K_diagnosis", before_step=current_step)
    diagnosis_path = k_dir / f"diagnosis__{region}_D{delay}_{category}.json"
    diagnosis = read_json(diagnosis_path)

    ranked = diagnosis.get("ranked_alphas", [])
    good_rows = [row for row in ranked if row.get("good_alpha_hard_pass")]
    if not good_rows:
        good_rows = [row for row in ranked if row.get("quality_bucket") == "keep_for_iteration"][:3]

    check_script = root_dir / "wqb_core" / "simulation" / "check.py"
    submission_script = root_dir / "wqb_core" / "alpha" / "get_submission_check.py"
    correlation_script = root_dir / "wqb_core" / "alpha" / "get_correlation.py"

    rows = []
    for row in good_rows:
        alpha_id = row["alpha_id"]
        check_payload = run_json(pyexe, check_script, ["--alpha-id", alpha_id], timeout=180)
        submission_payload = run_json(pyexe, submission_script, ["--alpha-id", alpha_id], timeout=180)
        self_corr = run_json(
            pyexe,
            correlation_script,
            ["--alpha-id", alpha_id, "--correlation-type", "self"],
            timeout=180,
        )
        powerpool_corr = run_json(
            pyexe,
            correlation_script,
            ["--alpha-id", alpha_id, "--correlation-type", "powerpool"],
            timeout=180,
        )

        check_json = check_payload.get("json", {})
        checks = (check_json.get("is") or {}).get("checks") or []
        regular_submission = check_result(checks, "REGULAR_SUBMISSION")
        matches_pyramid = check_result(checks, "MATCHES_PYRAMID")
        prod_max = corr_max(submission_payload.get("correlation_checks"))
        self_max = corr_max(self_corr)
        powerpool_max = corr_max(powerpool_corr)

        correlation_gate_pass = all(
            value is not None and value <= CORR_MAX_THRESHOLD
            for value in (prod_max, self_max, powerpool_max)
        )
        approved = (
            bool(row.get("good_alpha_hard_pass"))
            and regular_submission == "PASS"
            and matches_pyramid == "PASS"
            and correlation_gate_pass
        )

        rows.append(
            {
                "candidate_id": row.get("candidate_id"),
                "alpha_id": alpha_id,
                "regular": row.get("regular"),
                "source_quality_bucket": row.get("quality_bucket"),
                "source_good_alpha_hard_pass": row.get("good_alpha_hard_pass"),
                "k_metrics": row.get("metrics", {}),
                "slow_checks": {
                    "regular_submission": regular_submission,
                    "matches_pyramid": matches_pyramid,
                    "prod_correlation_max": prod_max,
                    "self_correlation_max": self_max,
                    "powerpool_correlation_max": powerpool_max,
                    "correlation_gate_threshold": CORR_MAX_THRESHOLD,
                    "correlation_gate_pass": correlation_gate_pass,
                },
                "approved_for_submit": approved,
                "raw": {
                    "check": check_payload,
                    "submission_check": submission_payload,
                    "self_correlation": self_corr,
                    "powerpool_correlation": powerpool_corr,
                },
            }
        )

    approved_rows = [row for row in rows if row["approved_for_submit"]]
    next_node = "M_submit_light_tower_pool_sa_osm"
    rollback_target = None
    rollback_reason = None

    if not rows or not approved_rows:
        next_node = "E_data_and_field_feasibility"
        rollback_target = "E_data_and_field_feasibility"
        rollback_reason = "L found no approved submit candidates after slow correlation and submission checks"
        if rows and any(
            row["slow_checks"].get("matches_pyramid") != "PASS" for row in rows
        ):
            next_node = "D_main_tower"
            rollback_target = "D_main_tower"
            rollback_reason = "L detected tower mismatch during slow final check"

    slow_final = {
        "region": region,
        "delay": int(delay),
        "category": category,
        "source_k_dir": str(k_dir),
        "source_k_next_node": diagnosis.get("next_node"),
        "source_k_good_alpha_count": diagnosis.get("quality_summary", {}).get("good_alpha", 0),
        "evaluated_count": len(rows),
        "approved_count": len(approved_rows),
        "next_node": next_node,
        "rollback_target": rollback_target,
        "rollback_reason": rollback_reason,
        "rows": rows,
    }

    submission_candidates = {
        "region": region,
        "delay": int(delay),
        "category": category,
        "count": len(approved_rows),
        "mode": "submit_ready" if approved_rows else "empty",
        "candidates": approved_rows,
    }

    (node_dir / f"slow_final_check__{region}_D{delay}_{category}.json").write_text(
        json.dumps(slow_final, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (node_dir / f"submission_candidates__{region}_D{delay}_{category}.json").write_text(
        json.dumps(submission_candidates, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
