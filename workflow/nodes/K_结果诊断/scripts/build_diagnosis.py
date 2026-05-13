from __future__ import annotations

import json
import math
import sys
from pathlib import Path


GOOD_ALPHA_THRESHOLDS = {
    "sharpe_min": 1.58,
    "fitness_min": 1.0,
    "turnover_min": 0.01,
    "turnover_max": 0.70,
    "margin_min": 0.001,
}


def check_value(checks: list[dict], name: str) -> tuple[str | None, float | None]:
    for check in checks:
        if check.get("name") == name:
            return check.get("result"), check.get("value")
    return None, None


def overused_warning(row: dict) -> bool:
    detail = row.get("detail", {})
    body = detail.get("json", {})
    msg = body.get("message") or ""
    location = body.get("location", {})
    return (
        body.get("status") == "WARNING"
        and location.get("type") == "ALPHA_DATA_CATEGORY_DIVERSITY"
        and "Overused data" in msg
    )


def numeric_or_nan(value):
    if value is None:
        return math.nan
    try:
        return float(value)
    except Exception:
        return math.nan


def safe_ratio(numerator: float, denominator: float) -> float:
    if math.isnan(numerator) or math.isnan(denominator) or abs(denominator) < 1e-12:
        return math.nan
    return numerator / denominator


def finite_and_gt(value: float, threshold: float) -> bool:
    return not math.isnan(value) and math.isfinite(value) and value > threshold


def finite_and_between(value: float, low: float, high: float) -> bool:
    return not math.isnan(value) and math.isfinite(value) and low < value < high


def step_num(path: Path) -> int:
    return int(path.name.split("_", 1)[0])


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def diagnosis_score(obj: dict) -> tuple[float, float, int, float, float, int]:
    quality = obj.get("quality_summary", {})
    ranked = obj.get("ranked_alphas", [])
    top = ranked[0] if ranked else {}
    top_metrics = top.get("metrics", {})
    top_score = top.get("good_alpha_score", float("-inf"))
    try:
        top_score = float(top_score)
    except Exception:
        top_score = float("-inf")
    return (
        float(quality.get("good_alpha", 0)),
        top_score,
        int(quality.get("keep_for_iteration", 0)),
        float(top_metrics.get("sharpe", float("-inf")) or float("-inf")),
        float(top_metrics.get("fitness", float("-inf")) or float("-inf")),
        -int(obj.get("_step_num", 0)),
    )


def main() -> int:
    if len(sys.argv) != 5:
        raise SystemExit("Usage: build_diagnosis.py NODE_DIR REGION DELAY CATEGORY")

    node_dir = Path(sys.argv[1]).resolve()
    region = sys.argv[2]
    delay = sys.argv[3]
    category = sys.argv[4].upper()

    source = node_dir / f"alpha_details__{region}_D{delay}_{category}.json"
    diagnosis_path = node_dir / f"diagnosis__{region}_D{delay}_{category}.json"
    survivors_path = node_dir / f"survivors__{region}_D{delay}_{category}.json"

    payload = json.loads(source.read_text(encoding="utf-8"))
    rows = []
    for item in payload["alphas"]:
        detail = item.get("detail", {})
        status_code = detail.get("status_code")
        body = detail.get("json", {})
        is_block = body.get("is") or {}
        investability = is_block.get("investabilityConstrained") or {}
        risk_neutralized = is_block.get("riskNeutralized") or {}
        checks = is_block.get("checks") or []

        sharpe = numeric_or_nan(is_block.get("sharpe"))
        fitness = numeric_or_nan(is_block.get("fitness"))
        turnover = numeric_or_nan(is_block.get("turnover"))
        margin = numeric_or_nan(is_block.get("margin"))
        drawdown = numeric_or_nan(is_block.get("drawdown"))
        inv_sharpe = numeric_or_nan(investability.get("sharpe"))
        inv_fitness = numeric_or_nan(investability.get("fitness"))
        rn_sharpe = numeric_or_nan(risk_neutralized.get("sharpe"))
        rn_fitness = numeric_or_nan(risk_neutralized.get("fitness"))

        low_sharpe_result, _ = check_value(checks, "LOW_SHARPE")
        low_fitness_result, _ = check_value(checks, "LOW_FITNESS")
        low_turnover_result, _ = check_value(checks, "LOW_TURNOVER")
        high_turnover_result, _ = check_value(checks, "HIGH_TURNOVER")
        low_sub_result, _ = check_value(checks, "LOW_SUB_UNIVERSE_SHARPE")
        matches_pyramid_result, _ = check_value(checks, "MATCHES_PYRAMID")
        ht_ratio_result, ht_ratio_value = check_value(checks, "HT_HIGH_TURNOVER_RETURNS_RATIO")

        detail_fetch_failed = status_code != 200 or not is_block
        tower_match = matches_pyramid_result == "PASS"
        sub_universe_ok = low_sub_result == "PASS"
        low_turnover_fail = low_turnover_result == "FAIL"
        high_turnover_fail = high_turnover_result == "FAIL"
        overused = overused_warning(item)

        inv_survival_ratio = safe_ratio(inv_sharpe, sharpe)
        rn_survival_ratio = safe_ratio(rn_sharpe, sharpe)

        hard_metric_pass = (
            finite_and_gt(sharpe, GOOD_ALPHA_THRESHOLDS["sharpe_min"])
            and finite_and_gt(fitness, GOOD_ALPHA_THRESHOLDS["fitness_min"])
            and finite_and_between(
                turnover,
                GOOD_ALPHA_THRESHOLDS["turnover_min"],
                GOOD_ALPHA_THRESHOLDS["turnover_max"],
            )
            and finite_and_gt(margin, GOOD_ALPHA_THRESHOLDS["margin_min"])
        )

        good_alpha_hard_pass = (
            not detail_fetch_failed
            and tower_match
            and sub_universe_ok
            and hard_metric_pass
            and not overused
        )

        good_alpha_score = -10_000.0
        if not detail_fetch_failed:
            good_alpha_score = (
                sharpe * 100.0
                + fitness * 80.0
                + margin * 5000.0
                - drawdown * 8.0
                + (inv_sharpe * 25.0 if not math.isnan(inv_sharpe) else 0.0)
                + (rn_sharpe * 15.0 if not math.isnan(rn_sharpe) else 0.0)
                + (2.0 if tower_match else -10.0)
                + (2.0 if sub_universe_ok else -6.0)
                + (3.0 if hard_metric_pass else 0.0)
                + (0.5 if ht_ratio_result == "PASS" else -0.5 if ht_ratio_result == "WARNING" else 0.0)
            )
            if not math.isnan(inv_survival_ratio):
                good_alpha_score += min(inv_survival_ratio, 1.5) * 4.0
            if not math.isnan(rn_survival_ratio):
                good_alpha_score += max(min(rn_survival_ratio, 1.5), -1.5) * 3.0

        diagnosis = []
        if detail_fetch_failed:
            diagnosis.append("detail_fetch_failed")
        if tower_match:
            diagnosis.append("matches_target_tower")
        if sub_universe_ok:
            diagnosis.append("subuniverse_ok")
        if overused:
            diagnosis.append("overused_analyst_data")
        if hard_metric_pass:
            diagnosis.append("hard_metric_pass")
        else:
            diagnosis.append("hard_metric_fail")
        if not detail_fetch_failed and not math.isnan(inv_sharpe) and inv_sharpe >= sharpe - 0.1:
            diagnosis.append("investability_stable")
        if not detail_fetch_failed and not math.isnan(rn_sharpe) and rn_sharpe >= 0.0:
            diagnosis.append("risk_neutralized_positive")
        elif not detail_fetch_failed and not math.isnan(rn_sharpe) and rn_sharpe > -0.1:
            diagnosis.append("risk_neutralized_near_flat")

        quality_bucket = "reject"
        if detail_fetch_failed:
            quality_bucket = "invalid_fetch"
        elif good_alpha_hard_pass:
            quality_bucket = "good_alpha"
        elif tower_match and sub_universe_ok and sharpe > 0.20 and fitness > 0.05:
            quality_bucket = "keep_for_iteration"

        rows.append(
            {
                "candidate_id": item.get("candidate_id"),
                "alpha_id": item.get("alpha_id"),
                "regular": item.get("regular"),
                "detail_status_code": status_code,
                "status": body.get("status"),
                "stage": body.get("stage"),
                "visualization": (body.get("settings") or {}).get("visualization"),
                "operator_count_platform": (body.get("regular") or {}).get("operatorCount"),
                "metrics": {
                    "sharpe": sharpe,
                    "fitness": fitness,
                    "turnover": turnover,
                    "margin": margin,
                    "drawdown": drawdown,
                    "investability_sharpe": inv_sharpe,
                    "investability_fitness": inv_fitness,
                    "risk_neutralized_sharpe": rn_sharpe,
                    "risk_neutralized_fitness": rn_fitness,
                    "investability_survival_ratio": inv_survival_ratio,
                    "risk_neutralized_survival_ratio": rn_survival_ratio,
                },
                "check_results": {
                    "LOW_SHARPE": low_sharpe_result,
                    "LOW_FITNESS": low_fitness_result,
                    "LOW_TURNOVER": low_turnover_result,
                    "HIGH_TURNOVER": high_turnover_result,
                    "LOW_SUB_UNIVERSE_SHARPE": low_sub_result,
                    "MATCHES_PYRAMID": matches_pyramid_result,
                    "HT_HIGH_TURNOVER_RETURNS_RATIO": {
                        "result": ht_ratio_result,
                        "value": ht_ratio_value,
                    },
                },
                "detail_fetch_failed": detail_fetch_failed,
                "overused_warning": overused,
                "message": body.get("message"),
                "diagnosis_tags": diagnosis,
                "hard_metric_pass": hard_metric_pass,
                "good_alpha_hard_pass": good_alpha_hard_pass,
                "quality_bucket": quality_bucket,
                "good_alpha_score": good_alpha_score,
            }
        )

    rows.sort(key=lambda x: (x["quality_bucket"] != "invalid_fetch", x["good_alpha_score"]), reverse=True)

    survivors = [row for row in rows if row["quality_bucket"] in {"good_alpha", "keep_for_iteration"}][:3]
    if not survivors:
        survivors = [row for row in rows if not row["detail_fetch_failed"]][:3]

    quality_summary = {
        "total": len(rows),
        "invalid_fetch": sum(1 for row in rows if row["quality_bucket"] == "invalid_fetch"),
        "good_alpha": sum(1 for row in rows if row["quality_bucket"] == "good_alpha"),
        "keep_for_iteration": sum(1 for row in rows if row["quality_bucket"] == "keep_for_iteration"),
        "reject": sum(1 for row in rows if row["quality_bucket"] == "reject"),
    }

    keep_rows = [row for row in rows if row["quality_bucket"] == "keep_for_iteration"]
    family_counts: dict[str, int] = {}
    for row in keep_rows:
        candidate_id = row.get("candidate_id") or ""
        parts = candidate_id.split("_")
        family = parts[1] if len(parts) > 1 else "unknown"
        family_counts[family] = family_counts.get(family, 0) + 1

    rollback_target = "H_mechanism_hypotheses"
    rollback_reason = "current batch still has zero true good_alpha by hard thresholds; use visualization-aware diagnosis to reweight mechanisms before another I batch"
    next_node = "H_mechanism_hypotheses"
    if quality_summary["good_alpha"] > 0:
        rollback_target = None
        rollback_reason = None
        next_node = "L_slow_final_check"
    elif family_counts.get("h1", 0) >= 2:
        rollback_target = "I_expression_candidates"
        rollback_reason = "current batch still has zero true good_alpha by hard thresholds, but the strongest survivors remain in the same H1 family; mechanism is stable and expression form should iterate further"
        next_node = "I_expression_candidates"

    diagnosis = {
        "region": region,
        "delay": int(delay),
        "category": category,
        "count": len(rows),
        "good_alpha_definition": {
            "hard_requirements": {
                "sharpe_gt": GOOD_ALPHA_THRESHOLDS["sharpe_min"],
                "fitness_gt": GOOD_ALPHA_THRESHOLDS["fitness_min"],
                "turnover_between": [
                    GOOD_ALPHA_THRESHOLDS["turnover_min"],
                    GOOD_ALPHA_THRESHOLDS["turnover_max"],
                ],
                "margin_gt": GOOD_ALPHA_THRESHOLDS["margin_min"],
            },
            "must_have": [
                "detail fetch succeeds",
                "MATCHES_PYRAMID = PASS",
                "LOW_SUB_UNIVERSE_SHARPE = PASS",
                "visualization = true for richer diagnosis",
            ],
            "preferred": [
                "investabilityConstrained metrics remain close to raw metrics",
                "riskNeutralized metrics do not collapse too hard",
                "no overused-data warning",
            ],
        },
        "quality_summary": quality_summary,
        "ranked_alphas": rows,
        "recommended_survivors": survivors,
        "rollback_target": rollback_target,
        "rollback_reason": rollback_reason,
        "next_node": next_node,
        "family_counts_in_keep_for_iteration": family_counts,
    }

    current_step = step_num(node_dir)
    diagnosis["_step_num"] = current_step
    run_root = node_dir.parent
    historical_candidates = []
    for k_dir in sorted(run_root.glob("*_node_K_diagnosis"), key=step_num):
        if k_dir == node_dir:
            continue
        diag_file = next(k_dir.glob("diagnosis__*.json"), None)
        if diag_file is None:
            continue
        try:
            prev_obj = load_json(diag_file)
        except Exception:
            continue
        prev_obj["_step_num"] = step_num(k_dir)
        prev_obj["_dir_name"] = k_dir.name
        prev_obj["_score_tuple"] = diagnosis_score(prev_obj)
        historical_candidates.append(prev_obj)

    if historical_candidates and quality_summary["good_alpha"] == 0:
        best_hist = max(historical_candidates, key=diagnosis_score)
        current_score_tuple = diagnosis_score(diagnosis)
        best_score_tuple = diagnosis_score(best_hist)
        current_keep = int(quality_summary["keep_for_iteration"])
        best_keep = int(best_hist.get("quality_summary", {}).get("keep_for_iteration", 0))
        current_top_score = current_score_tuple[1]
        best_top_score = best_score_tuple[1]
        dominance_reasons = []
        if best_score_tuple[0] > current_score_tuple[0]:
            dominance_reasons.append("historical K has more good_alpha")
        if best_keep >= current_keep + 2:
            dominance_reasons.append("historical K has materially more keep_for_iteration survivors")
        if best_top_score >= current_top_score + 8.0:
            dominance_reasons.append("historical K top score is materially stronger")
        if dominance_reasons:
            diagnosis["best_historical_k"] = {
                "dir_name": best_hist.get("_dir_name"),
                "step_num": best_hist.get("_step_num"),
                "quality_summary": best_hist.get("quality_summary", {}),
                "top_score": best_top_score,
                "next_node": best_hist.get("next_node"),
                "rollback_target": best_hist.get("rollback_target"),
                "rollback_reason": best_hist.get("rollback_reason"),
                "dominance_reasons": dominance_reasons,
            }
            diagnosis["rollback_target"] = "BEST_K_BRANCH"
            diagnosis["rollback_reason"] = (
                "historical K branch point dominates current degraded path: "
                + "; ".join(dominance_reasons)
            )
            diagnosis["next_node"] = "BEST_K_BRANCH"

    survivors_payload = {
        "region": region,
        "delay": int(delay),
        "category": category,
        "count": len(survivors),
        "survivors": survivors,
    }

    diagnosis_path.write_text(json.dumps(diagnosis, ensure_ascii=False, indent=2), encoding="utf-8")
    survivors_path.write_text(json.dumps(survivors_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
