from __future__ import annotations

import json
import math
import sys
from pathlib import Path


def fmt(value: float, digits: int) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "nan"
    return f"{value:.{digits}f}"


def main() -> int:
    if len(sys.argv) != 5:
        raise SystemExit("Usage: write_summary.py NODE_DIR REGION DELAY CATEGORY")

    node_dir = Path(sys.argv[1]).resolve()
    region = sys.argv[2]
    delay = sys.argv[3]
    category = sys.argv[4].upper()

    diagnosis = json.loads((node_dir / f"diagnosis__{region}_D{delay}_{category}.json").read_text(encoding="utf-8"))
    survivors = json.loads((node_dir / f"survivors__{region}_D{delay}_{category}.json").read_text(encoding="utf-8"))

    lines = [
        f"# K summary: {region}/D{delay}/{category}",
        "",
        f"- alpha count: {diagnosis['count']}",
        f"- rollback target: {diagnosis['rollback_target']}",
        f"- rollback reason: {diagnosis['rollback_reason']}",
        f"- quality summary: {json.dumps(diagnosis['quality_summary'], ensure_ascii=False)}",
        "",
        "## good alpha definition",
    ]

    hard_req = diagnosis["good_alpha_definition"]["hard_requirements"]
    lines.append(
        f"- hard thresholds: sharpe>{hard_req['sharpe_gt']}, fitness>{hard_req['fitness_gt']}, turnover in ({hard_req['turnover_between'][0]}, {hard_req['turnover_between'][1]}), margin>{hard_req['margin_gt']}"
    )
    for bullet in diagnosis["good_alpha_definition"]["must_have"]:
        lines.append(f"- must have: {bullet}")
    for bullet in diagnosis["good_alpha_definition"]["preferred"]:
        lines.append(f"- preferred: {bullet}")

    lines.extend(["", "## top ranked"])
    for row in diagnosis["ranked_alphas"][:5]:
        metrics = row["metrics"]
        lines.append(
            "- "
            + f"{row['candidate_id']} / {row['alpha_id']} / bucket={row['quality_bucket']} / "
            + f"score={fmt(row['good_alpha_score'], 2)} / "
            + f"sharpe={fmt(metrics['sharpe'], 2)} / "
            + f"fitness={fmt(metrics['fitness'], 2)} / "
            + f"turnover={fmt(metrics['turnover'], 4)} / "
            + f"inv_sharpe={fmt(metrics['investability_sharpe'], 2)} / "
            + f"rn_sharpe={fmt(metrics['risk_neutralized_sharpe'], 2)} / "
            + f"fetch_failed={row['detail_fetch_failed']}"
        )

    lines.extend(["", "## survivors"])
    for row in survivors["survivors"]:
        lines.append(
            f"- {row['candidate_id']} / {row['alpha_id']} / bucket={row['quality_bucket']} / tags={', '.join(row['diagnosis_tags'])}"
        )

    best_hist = diagnosis.get("best_historical_k")
    if best_hist:
        lines.extend(["", "## best historical k"])
        lines.append(f"- dir: {best_hist.get('dir_name')}")
        lines.append(f"- step: {best_hist.get('step_num')}")
        lines.append(f"- quality summary: {json.dumps(best_hist.get('quality_summary', {}), ensure_ascii=False)}")
        lines.append(f"- next node: {best_hist.get('next_node')}")
        lines.append(f"- rollback target: {best_hist.get('rollback_target')}")
        lines.append(f"- rollback reason: {best_hist.get('rollback_reason')}")
        for reason in best_hist.get("dominance_reasons", []):
            lines.append(f"- dominance reason: {reason}")

    (node_dir / "node_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
