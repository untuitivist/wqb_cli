from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def candidate(
    *,
    cid: str,
    hypothesis_id: str,
    hypothesis_title: str,
    regular: str,
    fields: list[str],
    settings: dict,
    operator_count: int,
    summary: str,
    mechanism: str,
) -> dict:
    return {
        "id": cid,
        "hypothesis_id": hypothesis_id,
        "hypothesis_title": hypothesis_title,
        "summary": summary,
        "fields": fields,
        "fieldCount": len(set(fields)),
        "operatorCount": operator_count,
        "settings": settings,
        "regular": regular,
        "rationale": {
            "mechanism": mechanism,
            "why_neutralization": "Analyst estimate, target-price, and coverage structures have strong industry clustering, so INDUSTRY or SUBINDUSTRY neutralization remains the default risk-control choice.",
            "why_low_turnover": "Prefer repricing structures with controlled 21 to 84 day horizons and gating rather than raw short-horizon noise so turnover stays away from D0 while still improving over very slow level-rank forms.",
        },
    }


def validate_operator_parameter_rules(expression: str) -> None:
    if "ts_quantile(" in expression and "driver='" not in expression:
        raise SystemExit(f"Operator rule violation in expression: {expression}")
    if "ts_weighted_decay(" in expression and "k=" not in expression:
        raise SystemExit(f"Operator rule violation in expression: {expression}")
    if "hump_decay(" in expression and "p=" not in expression:
        raise SystemExit(f"Operator rule violation in expression: {expression}")
    if "ts_poly_regression(" in expression and "k=" not in expression:
        raise SystemExit(f"Operator rule violation in expression: {expression}")
    if "group_mean(" in expression:
        after = expression.split("group_mean(", 1)[1]
        depth = 1
        buf = []
        for ch in after:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    break
            buf.append(ch)
        inner = "".join(buf)
        if inner.count(",") < 2:
            raise SystemExit(f"Operator rule violation in expression: {expression}")
    if "kth_element(" in expression and "k=" not in expression:
        raise SystemExit(f"Operator rule violation in expression: {expression}")
    if "ts_target_tvr_decay(" in expression:
        if "lambda_min=" not in expression or "lambda_max=" not in expression or "target_tvr=" not in expression:
            raise SystemExit(f"Operator rule violation in expression: {expression}")
    if "ts_target_tvr_hump(" in expression:
        if "lambda_min=" not in expression or "lambda_max=" not in expression or "target_tvr=" not in expression:
            raise SystemExit(f"Operator rule violation in expression: {expression}")


def main() -> int:
    if len(sys.argv) != 6:
        raise SystemExit("Usage: build_expression_candidates.py RUN_DIR NODE_DIR REGION DELAY CATEGORY")

    run_dir = Path(sys.argv[1]).resolve()
    node_dir = Path(sys.argv[2]).resolve()
    region = sys.argv[3].upper()
    delay = int(sys.argv[4])
    category = sys.argv[5].upper()
    tower_id = f"{region}_D{delay}_{category}"
    try:
        step_num = int(node_dir.name.split("_", 1)[0])
    except Exception:
        step_num = 0

    repo_root = Path(__file__).resolve().parents[4]
    finder = repo_root / "workflow" / "shared" / "find_latest_node_dir.py"

    def latest_dir(slug: str) -> Path:
        proc = subprocess.run(
            [sys.executable, str(finder), str(run_dir), slug],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        return Path(proc.stdout.strip())

    d_obj = load_json(latest_dir("D_main_tower") / "decision.json")
    e_obj = load_json(latest_dir("E_data_and_field_feasibility") / f"available_datafields__{tower_id}.json")
    h_obj = load_json(latest_dir("H_mechanism_hypotheses") / f"mechanism_hypotheses__{tower_id}.json")

    hypotheses = {row["id"]: row for row in h_obj["hypotheses"]}
    preferred_fields = {row["datafield"] for row in e_obj["datafields"][:20]}

    required_fields = {
        "anl14_median_epsrep_fy1",
        "anl14_median_ntprep_fy1",
        "anl14_median_ebitda_fy2",
        "anl14_numofests_ntp_fy3",
        "anl14_high_ntprep_fy2",
        "anl14_high_ebitda_fy3",
    }
    missing = sorted(required_fields - preferred_fields)
    if missing:
        raise SystemExit(f"Missing required fields from E candidate pool: {missing}")

    tower = d_obj.get("target_tower") or d_obj.get("decision") or {}

    base_settings = {
        "language": "FASTEXPR",
        "instrumentType": "EQUITY",
        "region": tower["region"].upper(),
        "universe": "TOP3000",
        "delay": int(tower["delay"]),
        "decay": 4,
        "neutralization": "INDUSTRY",
        "truncation": 0.08,
        "pasteurization": "ON",
        "unitHandling": "VERIFY",
        "nanHandling": "OFF",
        "visualization": True,
    }

    def s(**overrides):
        out = dict(base_settings)
        out.update(overrides)
        return out

    phase = 0
    if step_num >= 19:
        phase = 1 + (step_num - 19) // 4

    branch_anchor_step = None
    branch_generation = 0
    for k_dir in sorted(run_dir.glob("*_node_K_diagnosis")):
        try:
            k_step = int(k_dir.name.split("_", 1)[0])
        except Exception:
            continue
        err_dir = k_dir / "error_branch"
        if err_dir.is_dir():
            gens = [p for p in err_dir.iterdir() if p.is_dir()]
            if gens and (branch_anchor_step is None or k_step > branch_anchor_step):
                branch_anchor_step = k_step
                branch_generation = len(gens)

    if branch_anchor_step is not None and step_num > branch_anchor_step:
        phase = max(
            phase,
            6 + branch_generation + max(0, (step_num - branch_anchor_step - 1) // 3),
        )

    # Fresh clean runs should start from the strongest known revision family
    # structures learned in prior loops, rather than replaying the earliest
    # weaker batches from the first run. Keep advancing the phase every I step
    # on runs that have not yet branched.
    if branch_anchor_step is None and step_num >= 10:
        phase = max(phase, 5 + max(0, (step_num - 10) // 3))

    if phase <= 0:
        candidates = [
            candidate(
                cid="I1_h1_eps_revision_delta",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 42))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=3,
                summary="Forward EPS repricing via change in smoothed consensus rather than raw level.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I2_h1_ntprep_revision_delta",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_delta(ts_mean(anl14_median_ntprep_fy1, 42), 42))",
                fields=["anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=3,
                summary="Forward net-profit repricing via consensus revision instead of static level.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I3_h1_ebitda_revision_delta",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_delta(ts_mean(anl14_median_ebitda_fy2, 42), 42))",
                fields=["anl14_median_ebitda_fy2"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=3,
                summary="Forward EBITDA repricing via changes in smoothed consensus.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I4_h1_dual_revision_gap",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 42) + ts_delta(ts_mean(anl14_median_ntprep_fy1, 42), 42))",
                fields=["anl14_median_epsrep_fy1", "anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=5,
                summary="Two-field revision composite across EPS and net-profit repricing.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I5_h1_eps_revision_ifelse",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(if_else(ts_delta(anl14_median_epsrep_fy1, 21) > 0, ts_mean(anl14_median_epsrep_fy1, 42), ts_decay_linear(anl14_median_epsrep_fy1, 84)))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=5,
                summary="Conditional EPS repricing with faster response to positive revisions and slower decay otherwise.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I6_h3_coverage_gate_ifelse",
                hypothesis_id="H3_coverage_conditioned_repricing",
                hypothesis_title=hypotheses["H3_coverage_conditioned_repricing"]["id"],
                regular="rank(if_else(ts_zscore(anl14_numofests_ntp_fy3, 63) > 0, ts_mean(anl14_median_ntprep_fy1, 63), ts_decay_linear(anl14_median_ntprep_fy1, 84)))",
                fields=["anl14_numofests_ntp_fy3", "anl14_median_ntprep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=5,
                summary="Coverage-conditioned repricing: faster signal when analyst attention is above baseline, slower otherwise.",
                mechanism=hypotheses["H3_coverage_conditioned_repricing"]["economic_logic"],
            ),
            candidate(
                cid="I7_h3_trade_when_coverage",
                hypothesis_id="H3_coverage_conditioned_repricing",
                hypothesis_title=hypotheses["H3_coverage_conditioned_repricing"]["id"],
                regular="trade_when(ts_zscore(anl14_numofests_ntp_fy3, 63) > 0, rank(ts_mean(anl14_median_ntprep_fy1, 63)), abs(ts_zscore(anl14_numofests_ntp_fy3, 63)) > 2)",
                fields=["anl14_numofests_ntp_fy3", "anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=5,
                summary="Trade only when coverage indicates credible repricing, and close out extreme attention bursts.",
                mechanism=hypotheses["H3_coverage_conditioned_repricing"]["economic_logic"],
            ),
            candidate(
                cid="I8_h4_upside_gap_ntprep_decay63",
                hypothesis_id="H4_upside_minus_base_convexity",
                hypothesis_title=hypotheses["H4_upside_minus_base_convexity"]["id"],
                regular="rank(ts_decay_linear(subtract(anl14_high_ntprep_fy2, anl14_median_ntprep_fy1), 63))",
                fields=["anl14_high_ntprep_fy2", "anl14_median_ntprep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Upward convexity from optimistic versus base net-profit expectations with a faster repricing window.",
                mechanism=hypotheses["H4_upside_minus_base_convexity"]["economic_logic"],
            ),
            candidate(
                cid="I9_h4_upside_gap_ebitda_decay63",
                hypothesis_id="H4_upside_minus_base_convexity",
                hypothesis_title=hypotheses["H4_upside_minus_base_convexity"]["id"],
                regular="rank(ts_decay_linear(subtract(anl14_high_ebitda_fy3, anl14_median_ebitda_fy2), 63))",
                fields=["anl14_high_ebitda_fy3", "anl14_median_ebitda_fy2"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Optimistic versus base EBITDA gap for convex upside repricing.",
                mechanism=hypotheses["H4_upside_minus_base_convexity"]["economic_logic"],
            ),
            candidate(
                cid="I10_h4_convexity_tanh_gap",
                hypothesis_id="H4_upside_minus_base_convexity",
                hypothesis_title=hypotheses["H4_upside_minus_base_convexity"]["id"],
                regular="rank(tanh(ts_mean(subtract(anl14_high_ntprep_fy2, anl14_median_ntprep_fy1), 63)))",
                fields=["anl14_high_ntprep_fy2", "anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=5,
                summary="Nonlinear convexity transform to control concentration while retaining upside-gap information.",
                mechanism=hypotheses["H4_upside_minus_base_convexity"]["economic_logic"],
            ),
        ]
        batch_intent = "third_batch_revision_priority_after_K_to_H"
    elif phase == 1:
        candidates = [
            candidate(
                cid="I1_h1_eps_revision_accel21",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_delta(ts_delta(ts_mean(anl14_median_epsrep_fy1, 21), 21), 21))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Second-order EPS revision acceleration.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I2_h1_ntprep_revision_accel21",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_delta(ts_delta(ts_mean(anl14_median_ntprep_fy1, 21), 21), 21))",
                fields=["anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=4,
                summary="Second-order net-profit revision acceleration.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I3_h1_eps_minus_ntprep_revision",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_delta(ts_mean(anl14_median_epsrep_fy1, 21), 21) - ts_delta(ts_mean(anl14_median_ntprep_fy1, 42), 42))",
                fields=["anl14_median_epsrep_fy1", "anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=5,
                summary="Cross-horizon revision spread between EPS and net-profit repricing.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I4_h1_eps_weighted_decay",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_weighted_decay(ts_delta(anl14_median_epsrep_fy1, 21), k=0.35))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=3,
                summary="Weighted decay on raw EPS revision to preserve fresher repricing.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I5_h1_ntprep_hump_decay",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(hump_decay(ts_delta(anl14_median_ntprep_fy1, 21), p=0.15))",
                fields=["anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=3,
                summary="Hump-decayed net-profit revision to avoid stale tails.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I6_h3_group_mean_revision",
                hypothesis_id="H3_coverage_conditioned_repricing",
                hypothesis_title=hypotheses["H3_coverage_conditioned_repricing"]["id"],
                regular="rank(group_mean(ts_delta(anl14_median_epsrep_fy1, 21), 1, subindustry) - ts_delta(anl14_median_epsrep_fy1, 21))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Revision deviation from group mean as a credibility-conditioned signal.",
                mechanism=hypotheses["H3_coverage_conditioned_repricing"]["economic_logic"],
            ),
            candidate(
                cid="I7_h4_gap_target_tvr_decay",
                hypothesis_id="H4_upside_minus_base_convexity",
                hypothesis_title=hypotheses["H4_upside_minus_base_convexity"]["id"],
                regular="rank(ts_target_tvr_decay(subtract(anl14_high_ntprep_fy2, anl14_median_ntprep_fy1), lambda_min=0, lambda_max=1, target_tvr=0.1))",
                fields=["anl14_high_ntprep_fy2", "anl14_median_ntprep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=3,
                summary="Target-TVR controlled convexity repricing on optimistic gap.",
                mechanism=hypotheses["H4_upside_minus_base_convexity"]["economic_logic"],
            ),
            candidate(
                cid="I8_h4_gap_target_tvr_hump",
                hypothesis_id="H4_upside_minus_base_convexity",
                hypothesis_title=hypotheses["H4_upside_minus_base_convexity"]["id"],
                regular="rank(ts_target_tvr_hump(subtract(anl14_high_ebitda_fy3, anl14_median_ebitda_fy2), lambda_min=0, lambda_max=1, target_tvr=0.1))",
                fields=["anl14_high_ebitda_fy3", "anl14_median_ebitda_fy2"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=3,
                summary="Target-TVR hump control on EBITDA convexity gap.",
                mechanism=hypotheses["H4_upside_minus_base_convexity"]["economic_logic"],
            ),
            candidate(
                cid="I9_h1_eps_quantile_gaussian",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_quantile(ts_delta(anl14_median_epsrep_fy1, 21), 63, driver='gaussian'))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=3,
                summary="Gaussian quantile transform on EPS revision.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I10_h1_ntprep_kth_element",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(kth_element(ts_delta(anl14_median_ntprep_fy1, 21), 63, k=10))",
                fields=["anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=3,
                summary="Robust lower-order statistic on net-profit revision path.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
        ]
        batch_intent = f"iterative_revision_structure_batch_phase_{phase}"
    elif phase == 2:
        candidates = [
            candidate(
                cid="I1_h1_eps_revision_delta_base",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 42))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=3,
                summary="Baseline EPS revision repricing anchor.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I2_h1_eps_revision_weighted",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_weighted_decay(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 21), k=0.4))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Weighted EPS revision repricing around the strongest baseline family.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I3_h1_ntprep_revision_base",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_delta(ts_mean(anl14_median_ntprep_fy1, 42), 42))",
                fields=["anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=3,
                summary="Baseline net-profit revision repricing anchor.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I4_h1_dual_revision_base",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 42) + ts_delta(ts_mean(anl14_median_ntprep_fy1, 42), 42))",
                fields=["anl14_median_epsrep_fy1", "anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=5,
                summary="Dual baseline revision composite retained as a control.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I5_h1_eps_quantile_base",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_quantile(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 21), 63, driver='gaussian'))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Gaussian-quantile EPS revision variant around the strongest baseline path.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I6_h1_ntprep_kth_base",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(kth_element(ts_delta(ts_mean(anl14_median_ntprep_fy1, 42), 21), 63, k=10))",
                fields=["anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=4,
                summary="Robust kth-element filter on net-profit revision path.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I7_h4_convexity_tanh_base",
                hypothesis_id="H4_upside_minus_base_convexity",
                hypothesis_title=hypotheses["H4_upside_minus_base_convexity"]["id"],
                regular="rank(tanh(ts_mean(subtract(anl14_high_ntprep_fy2, anl14_median_ntprep_fy1), 63)))",
                fields=["anl14_high_ntprep_fy2", "anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=5,
                summary="Best prior convexity control retained as non-revision benchmark.",
                mechanism=hypotheses["H4_upside_minus_base_convexity"]["economic_logic"],
            ),
            candidate(
                cid="I8_h4_gap_target_tvr_decay",
                hypothesis_id="H4_upside_minus_base_convexity",
                hypothesis_title=hypotheses["H4_upside_minus_base_convexity"]["id"],
                regular="rank(ts_target_tvr_decay(subtract(anl14_high_ntprep_fy2, anl14_median_ntprep_fy1), lambda_min=0, lambda_max=1, target_tvr=0.1))",
                fields=["anl14_high_ntprep_fy2", "anl14_median_ntprep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=3,
                summary="Target-TVR controlled convexity repricing retained as alternative benchmark.",
                mechanism=hypotheses["H4_upside_minus_base_convexity"]["economic_logic"],
            ),
            candidate(
                cid="I9_h3_coverage_ifelse_base",
                hypothesis_id="H3_coverage_conditioned_repricing",
                hypothesis_title=hypotheses["H3_coverage_conditioned_repricing"]["id"],
                regular="rank(if_else(ts_zscore(anl14_numofests_ntp_fy3, 63) > 0, ts_mean(anl14_median_ntprep_fy1, 63), ts_decay_linear(anl14_median_ntprep_fy1, 84)))",
                fields=["anl14_numofests_ntp_fy3", "anl14_median_ntprep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=5,
                summary="Coverage-conditioned baseline retained as auxiliary support.",
                mechanism=hypotheses["H3_coverage_conditioned_repricing"]["economic_logic"],
            ),
            candidate(
                cid="I10_h1_eps_target_tvr_decay",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_target_tvr_decay(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 21), lambda_min=0, lambda_max=1, target_tvr=0.1))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=3,
                summary="Target-TVR controlled EPS revision variant.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
        ]
        batch_intent = f"iterative_revision_structure_batch_phase_{phase}"
    elif phase == 3:
        candidates = [
            candidate(
                cid="I1_h1_eps_weighted_decay_base",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_weighted_decay(ts_delta(anl14_median_epsrep_fy1, 21), k=0.35))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=3,
                summary="Best surviving weighted EPS revision anchor.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I2_h1_eps_target_tvr_decay",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_target_tvr_decay(ts_delta(anl14_median_epsrep_fy1, 21), lambda_min=0, lambda_max=1, target_tvr=0.1))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=3,
                summary="Target-TVR controlled EPS revision variant around the best surviving family.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I3_h1_eps_hump_decay",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(hump_decay(ts_delta(anl14_median_epsrep_fy1, 21), p=0.1))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=3,
                summary="Hump-decayed EPS revision to suppress stale tails.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I4_h1_ntprep_weighted_decay",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_weighted_decay(ts_delta(anl14_median_ntprep_fy1, 21), k=0.35))",
                fields=["anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=3,
                summary="Weighted net-profit revision variant mirroring the best EPS structure.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I5_h1_ntprep_target_tvr_hump",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_target_tvr_hump(ts_delta(anl14_median_ntprep_fy1, 21), lambda_min=0, lambda_max=1, target_tvr=0.1))",
                fields=["anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=3,
                summary="Target-TVR hump on net-profit revision.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I6_h1_eps_quantile_weighted",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_quantile(ts_weighted_decay(ts_delta(anl14_median_epsrep_fy1, 21), k=0.35), 63, driver='gaussian'))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Gaussian-quantile transform on weighted EPS revision.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I7_h1_ntprep_kth_weighted",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(kth_element(ts_weighted_decay(ts_delta(anl14_median_ntprep_fy1, 21), k=0.35), 63, k=10))",
                fields=["anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=4,
                summary="Robust kth-element transform on weighted net-profit revision.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I8_h1_dual_weighted_sum",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_weighted_decay(ts_delta(anl14_median_epsrep_fy1, 21), k=0.35) + ts_weighted_decay(ts_delta(anl14_median_ntprep_fy1, 21), k=0.35))",
                fields=["anl14_median_epsrep_fy1", "anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=5,
                summary="Dual weighted revision composite across EPS and net-profit.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I9_h4_convexity_control",
                hypothesis_id="H4_upside_minus_base_convexity",
                hypothesis_title=hypotheses["H4_upside_minus_base_convexity"]["id"],
                regular="rank(tanh(ts_mean(subtract(anl14_high_ntprep_fy2, anl14_median_ntprep_fy1), 63)))",
                fields=["anl14_high_ntprep_fy2", "anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=5,
                summary="Convexity control retained as benchmark against revision variants.",
                mechanism=hypotheses["H4_upside_minus_base_convexity"]["economic_logic"],
            ),
            candidate(
                cid="I10_h3_coverage_control",
                hypothesis_id="H3_coverage_conditioned_repricing",
                hypothesis_title=hypotheses["H3_coverage_conditioned_repricing"]["id"],
                regular="rank(if_else(ts_zscore(anl14_numofests_ntp_fy3, 63) > 0, ts_weighted_decay(ts_delta(anl14_median_epsrep_fy1, 21), k=0.35), ts_weighted_decay(ts_delta(anl14_median_ntprep_fy1, 21), k=0.35)))",
                fields=["anl14_numofests_ntp_fy3", "anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=5,
                summary="Coverage-conditioned switch between weighted EPS and net-profit revision paths.",
                mechanism=hypotheses["H3_coverage_conditioned_repricing"]["economic_logic"],
            ),
        ]
        batch_intent = f"iterative_revision_structure_batch_phase_{phase}"
    elif phase == 4:
        candidates = [
            candidate(
                cid="I1_h1_eps_mean42_weighted45",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_weighted_decay(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 42), k=0.45))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Weighted decay on delayed EPS repricing anchor with a stronger decay coefficient.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I2_h1_eps_mean42_target_tvr_hump",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_target_tvr_hump(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 21), lambda_min=0, lambda_max=1, target_tvr=0.12))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Target-TVR hump on EPS repricing with a slightly higher turnover target.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I3_h1_eps_mean42_hump005",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(hump_decay(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 21), p=0.05))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Milder hump-decay on delayed EPS repricing to preserve more recent information.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I4_h1_ntprep_mean42_weighted45",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_weighted_decay(ts_delta(ts_mean(anl14_median_ntprep_fy1, 42), 42), k=0.45))",
                fields=["anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=4,
                summary="Weighted decay on delayed net-profit repricing anchor.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I5_h1_ntprep_mean42_target_tvr_hump",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_target_tvr_hump(ts_delta(ts_mean(anl14_median_ntprep_fy1, 42), 21), lambda_min=0, lambda_max=1, target_tvr=0.12))",
                fields=["anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=4,
                summary="Target-TVR hump on delayed net-profit repricing.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I6_h1_eps_mean42_quantile84",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_quantile(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 21), 84, driver='gaussian'))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Longer-horizon Gaussian quantile on delayed EPS repricing.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I7_h1_ntprep_mean42_kth84",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(kth_element(ts_delta(ts_mean(anl14_median_ntprep_fy1, 42), 21), 84, k=12))",
                fields=["anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=4,
                summary="Longer-window robust order statistic on delayed net-profit repricing.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I8_h3_group_mean_eps_deviation",
                hypothesis_id="H3_coverage_conditioned_repricing",
                hypothesis_title=hypotheses["H3_coverage_conditioned_repricing"]["id"],
                regular="rank(group_mean(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 21), 1, subindustry) - ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 21))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=5,
                summary="Deviation from group mean delayed EPS repricing as a credibility filter.",
                mechanism=hypotheses["H3_coverage_conditioned_repricing"]["economic_logic"],
            ),
            candidate(
                cid="I9_h4_gap_target_tvr_decay008",
                hypothesis_id="H4_upside_minus_base_convexity",
                hypothesis_title=hypotheses["H4_upside_minus_base_convexity"]["id"],
                regular="rank(ts_target_tvr_decay(subtract(anl14_high_ntprep_fy2, anl14_median_ntprep_fy1), lambda_min=0, lambda_max=1, target_tvr=0.08))",
                fields=["anl14_high_ntprep_fy2", "anl14_median_ntprep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=3,
                summary="Lower-target-TVR convexity gap control for upside repricing.",
                mechanism=hypotheses["H4_upside_minus_base_convexity"]["economic_logic"],
            ),
            candidate(
                cid="I10_h1_ebitda_weighted_decay",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_weighted_decay(ts_delta(anl14_median_ebitda_fy2, 21), k=0.35))",
                fields=["anl14_median_ebitda_fy2"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=3,
                summary="EBITDA revision variant to widen the revision family beyond EPS and net-profit.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
        ]
        batch_intent = f"iterative_revision_structure_batch_phase_{phase}"
    elif phase == 5:
        candidates = [
            candidate(
                cid="I1_h1_eps_mean63_weighted50",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_weighted_decay(ts_delta(ts_mean(anl14_median_epsrep_fy1, 63), 21), k=0.5))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Longer-base weighted EPS repricing with stronger freshness weight.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I2_h1_eps_mean42_target_tvr_decay008",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_target_tvr_decay(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 42), lambda_min=0, lambda_max=1, target_tvr=0.08))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Lower target-TVR on the delayed EPS repricing anchor.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I3_h1_ntprep_mean63_target_tvr_decay008",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_target_tvr_decay(ts_delta(ts_mean(anl14_median_ntprep_fy1, 42), 42), lambda_min=0, lambda_max=1, target_tvr=0.08))",
                fields=["anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=4,
                summary="Lower target-TVR on the delayed net-profit repricing anchor.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I4_h1_ntprep_mean42_hump005",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(hump_decay(ts_delta(ts_mean(anl14_median_ntprep_fy1, 42), 21), p=0.05))",
                fields=["anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=4,
                summary="Milder hump-decay on delayed net-profit repricing.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I5_h1_eps_mean63_quantile84",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_quantile(ts_delta(ts_mean(anl14_median_epsrep_fy1, 63), 21), 84, driver='gaussian'))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Longer-base Gaussian quantile on EPS repricing.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I6_h1_ntprep_mean63_kth84",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(kth_element(ts_delta(ts_mean(anl14_median_ntprep_fy1, 63), 21), 84, k=14))",
                fields=["anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=4,
                summary="Longer-base robust kth statistic on net-profit repricing.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I7_h1_ebitda_target_tvr_decay008",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_target_tvr_decay(ts_delta(anl14_median_ebitda_fy2, 21), lambda_min=0, lambda_max=1, target_tvr=0.08))",
                fields=["anl14_median_ebitda_fy2"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=3,
                summary="EBITDA revision control with lower target TVR.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I8_h4_gap_target_tvr_hump008",
                hypothesis_id="H4_upside_minus_base_convexity",
                hypothesis_title=hypotheses["H4_upside_minus_base_convexity"]["id"],
                regular="rank(ts_target_tvr_hump(subtract(anl14_high_ebitda_fy3, anl14_median_ebitda_fy2), lambda_min=0, lambda_max=1, target_tvr=0.08))",
                fields=["anl14_high_ebitda_fy3", "anl14_median_ebitda_fy2"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=3,
                summary="Lower-target-TVH hump on EBITDA convexity gap.",
                mechanism=hypotheses["H4_upside_minus_base_convexity"]["economic_logic"],
            ),
            candidate(
                cid="I9_h3_group_mean_ntprep_deviation",
                hypothesis_id="H3_coverage_conditioned_repricing",
                hypothesis_title=hypotheses["H3_coverage_conditioned_repricing"]["id"],
                regular="rank(group_mean(ts_delta(ts_mean(anl14_median_ntprep_fy1, 42), 21), 1, subindustry) - ts_delta(ts_mean(anl14_median_ntprep_fy1, 42), 21))",
                fields=["anl14_median_ntprep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=5,
                summary="Deviation from group mean delayed net-profit repricing.",
                mechanism=hypotheses["H3_coverage_conditioned_repricing"]["economic_logic"],
            ),
            candidate(
                cid="I10_h1_eps_mean42_target_tvr_hump008",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_target_tvr_hump(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 42), lambda_min=0, lambda_max=1, target_tvr=0.08))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Delayed EPS repricing with lower target TVR hump control.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
        ]
        batch_intent = f"iterative_revision_structure_batch_phase_{phase}"
    elif phase == 6:
        candidates = [
            candidate(
                cid="I1_h1_eps_mean42_target_tvr_hump006",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_target_tvr_hump(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 42), lambda_min=0, lambda_max=1, target_tvr=0.06))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="More aggressive lower-TVR hump control on delayed EPS repricing.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I2_h1_eps_mean42_target_tvr_decay006",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_target_tvr_decay(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 42), lambda_min=0, lambda_max=1, target_tvr=0.06))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Lower target-TVR decay on delayed EPS repricing.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I3_h1_eps_mean42_weighted60",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_weighted_decay(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 42), k=0.6))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Stronger freshness weight on delayed EPS repricing anchor.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I4_h1_eps_mean42_hump003",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(hump_decay(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 42), p=0.03))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Tighter hump control on delayed EPS repricing.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I5_h1_eps_mean42_quantile126",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_quantile(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 42), 126, driver='gaussian'))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Longer Gaussian quantile view of delayed EPS repricing.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I6_h1_eps_mean42_kth126",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(kth_element(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 42), 126, k=18))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Robust order-statistic variant of delayed EPS repricing.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I7_h1_ntprep_mean42_target_tvr_hump010",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_target_tvr_hump(ts_delta(ts_mean(anl14_median_ntprep_fy1, 42), 21), lambda_min=0, lambda_max=1, target_tvr=0.10))",
                fields=["anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=4,
                summary="Net-profit repricing control with slightly looser hump target.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I8_h1_ebitda_target_tvr_hump008",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular="rank(ts_target_tvr_hump(ts_delta(anl14_median_ebitda_fy2, 21), lambda_min=0, lambda_max=1, target_tvr=0.08))",
                fields=["anl14_median_ebitda_fy2"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=3,
                summary="EBITDA revision hump control for family breadth.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid="I9_h3_group_mean_eps_deviation42",
                hypothesis_id="H3_coverage_conditioned_repricing",
                hypothesis_title=hypotheses["H3_coverage_conditioned_repricing"]["id"],
                regular="rank(group_mean(ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 42), 1, subindustry) - ts_delta(ts_mean(anl14_median_epsrep_fy1, 42), 42))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=5,
                summary="Group deviation on delayed EPS repricing as a credibility filter.",
                mechanism=hypotheses["H3_coverage_conditioned_repricing"]["economic_logic"],
            ),
            candidate(
                cid="I10_h4_gap_target_tvr_hump006",
                hypothesis_id="H4_upside_minus_base_convexity",
                hypothesis_title=hypotheses["H4_upside_minus_base_convexity"]["id"],
                regular="rank(ts_target_tvr_hump(subtract(anl14_high_ntprep_fy2, anl14_median_ntprep_fy1), lambda_min=0, lambda_max=1, target_tvr=0.06))",
                fields=["anl14_high_ntprep_fy2", "anl14_median_ntprep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=3,
                summary="More aggressive convexity control as secondary family check.",
                mechanism=hypotheses["H4_upside_minus_base_convexity"]["economic_logic"],
            ),
        ]
        batch_intent = f"iterative_revision_structure_batch_phase_{phase}"
    else:
        target_tvr_values = [0.08, 0.06, 0.05, 0.04, 0.03, 0.025, 0.02]
        weighted_k_values = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
        hump_p_values = [0.05, 0.03, 0.02, 0.015, 0.01, 0.008, 0.005]
        quantile_d_values = [84, 126, 168, 210, 252, 294, 336]
        kth_k_values = [14, 18, 24, 30, 36, 42, 48]
        base_window_values = [42, 42, 42, 42, 63, 63, 84]
        delta_window_values = [42, 42, 42, 42, 21, 21, 21]

        idx = min(max(phase - 5, 0), len(target_tvr_values) - 1)
        tvr = target_tvr_values[idx]
        k_weight = weighted_k_values[idx]
        hump_p = hump_p_values[idx]
        quant_d = quantile_d_values[idx]
        kth_k = kth_k_values[idx]
        base_w = base_window_values[idx]
        delta_w = delta_window_values[idx]
        tvr_tag = str(tvr).replace(".", "")
        weight_tag = str(k_weight).replace(".", "")
        hump_tag = str(hump_p).replace(".", "")

        candidates = [
            candidate(
                cid=f"I1_h1_eps_mean{base_w}_target_tvr_hump{tvr_tag}",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular=f"rank(ts_target_tvr_hump(ts_delta(ts_mean(anl14_median_epsrep_fy1, {base_w}), {delta_w}), lambda_min=0, lambda_max=1, target_tvr={tvr}))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Dynamic target-TVR hump on delayed EPS repricing.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid=f"I2_h1_eps_mean{base_w}_target_tvr_decay{tvr_tag}",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular=f"rank(ts_target_tvr_decay(ts_delta(ts_mean(anl14_median_epsrep_fy1, {base_w}), {delta_w}), lambda_min=0, lambda_max=1, target_tvr={tvr}))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Dynamic target-TVR decay on delayed EPS repricing.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid=f"I3_h1_eps_mean{base_w}_weighted{weight_tag}",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular=f"rank(ts_weighted_decay(ts_delta(ts_mean(anl14_median_epsrep_fy1, {base_w}), {delta_w}), k={k_weight}))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Dynamic weighted decay on delayed EPS repricing.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid=f"I4_h1_eps_mean{base_w}_hump{hump_tag}",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular=f"rank(hump_decay(ts_delta(ts_mean(anl14_median_epsrep_fy1, {base_w}), {delta_w}), p={hump_p}))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Dynamic hump control on delayed EPS repricing.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid=f"I5_h1_eps_mean{base_w}_quantile{quant_d}",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular=f"rank(ts_quantile(ts_delta(ts_mean(anl14_median_epsrep_fy1, {base_w}), {delta_w}), {quant_d}, driver='gaussian'))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Dynamic Gaussian quantile on delayed EPS repricing.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid=f"I6_h1_eps_mean{base_w}_kth{quant_d}",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular=f"rank(kth_element(ts_delta(ts_mean(anl14_median_epsrep_fy1, {base_w}), {delta_w}), {quant_d}, k={kth_k}))",
                fields=["anl14_median_epsrep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=4,
                summary="Dynamic robust statistic on delayed EPS repricing.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid=f"I7_h1_ntprep_mean42_target_tvr_decay{tvr_tag}",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular=f"rank(ts_target_tvr_decay(ts_delta(ts_mean(anl14_median_ntprep_fy1, 42), 21), lambda_min=0, lambda_max=1, target_tvr={max(tvr, 0.08)}))",
                fields=["anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=4,
                summary="Dynamic net-profit repricing control.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid=f"I8_h1_eps_ntprep_gap_target_tvr_hump{tvr_tag}",
                hypothesis_id="H1_repricing_from_forward_consensus_levels",
                hypothesis_title=hypotheses["H1_repricing_from_forward_consensus_levels"]["id"],
                regular=f"rank(ts_target_tvr_hump(ts_delta(ts_mean(anl14_median_epsrep_fy1, {base_w}), {delta_w}) - ts_delta(ts_mean(anl14_median_ntprep_fy1, 42), 21), lambda_min=0, lambda_max=1, target_tvr={max(tvr, 0.06)}))",
                fields=["anl14_median_epsrep_fy1", "anl14_median_ntprep_fy1"],
                settings=s(neutralization="SUBINDUSTRY"),
                operator_count=5,
                summary="Dynamic cross-field revision spread with target-TVR hump control.",
                mechanism=hypotheses["H1_repricing_from_forward_consensus_levels"]["economic_logic"],
            ),
            candidate(
                cid=f"I9_h3_group_mean_ntprep_deviation{base_w}",
                hypothesis_id="H3_coverage_conditioned_repricing",
                hypothesis_title=hypotheses["H3_coverage_conditioned_repricing"]["id"],
                regular=f"rank(group_mean(ts_delta(ts_mean(anl14_median_ntprep_fy1, {base_w}), 21), 1, subindustry) - ts_delta(ts_mean(anl14_median_ntprep_fy1, {base_w}), 21))",
                fields=["anl14_median_ntprep_fy1"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=5,
                summary="Dynamic delayed net-profit repricing deviation from group mean.",
                mechanism=hypotheses["H3_coverage_conditioned_repricing"]["economic_logic"],
            ),
            candidate(
                cid=f"I10_h4_gap_target_tvr_decay{tvr_tag}",
                hypothesis_id="H4_upside_minus_base_convexity",
                hypothesis_title=hypotheses["H4_upside_minus_base_convexity"]["id"],
                regular=f"rank(ts_target_tvr_decay(subtract(anl14_high_ebitda_fy3, anl14_median_ebitda_fy2), lambda_min=0, lambda_max=1, target_tvr={max(tvr, 0.06)}))",
                fields=["anl14_high_ebitda_fy3", "anl14_median_ebitda_fy2"],
                settings=s(neutralization="INDUSTRY"),
                operator_count=3,
                summary="Dynamic secondary convexity check with target-TVR decay.",
                mechanism=hypotheses["H4_upside_minus_base_convexity"]["economic_logic"],
            ),
        ]
        batch_intent = f"iterative_revision_structure_batch_phase_{phase}"

    output = {
        "region": region,
        "delay": delay,
        "category": category,
        "selected_dataset_bias": "analyst14",
        "candidate_field_pool_count": e_obj["candidate_count"],
        "expression_count": len(candidates),
        "expression_build_rules": [
            "economic rationale first",
            "OS-weak datasets excluded upstream by E before expression design",
            "used datafields already excluded upstream by E",
            "used datasets should be avoided where possible",
            "fieldCount <= 2",
            "operatorCount <= 5",
            "prefer slower repricing structures over raw short-horizon noise",
            "use conditional and nonlinear operators when they strengthen regime logic",
            "default risk neutralization enabled",
            "avoid deep nesting beyond 2-3 structural layers",
            "do not add epsilon or residual divide-by-zero guards",
            "respect datafield type compatibility",
            "do not redefine variables; keep final expression as the last line",
        ],
        "operator_parameter_rules": [
            "ts_quantile(x, d, driver='gaussian'): string parameters must use single quotes",
            "kth_element(x, d, k=?): explicit k required",
            "ts_theilsen(x, y, d)",
            "ts_weighted_decay(x, k=0.5): k must not be omitted",
            "hump_decay(x, p=0): p must not be omitted",
            "group_mean(x, weight, group): weight must not be omitted; 1 is allowed",
            "ts_target_tvr_decay(x, lambda_min=0, lambda_max=1, target_tvr=0.1)",
            "ts_target_tvr_hump(x, lambda_min=0, lambda_max=1, target_tvr=0.1)",
            "ts_poly_regression(y, x, d, k=1): k must not be omitted",
        ],
        "batch_intent": batch_intent,
        "candidates": candidates,
    }

    for row in candidates:
        validate_operator_parameter_rules(row["regular"])

    sim_batch = [
        {
            "type": "REGULAR",
            "settings": row["settings"],
            "regular": row["regular"],
        }
        for row in candidates
    ]

    node_dir.mkdir(parents=True, exist_ok=True)
    (node_dir / f"expression_candidates__{tower_id}.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (node_dir / f"simulation_batch__{tower_id}.json").write_text(
        json.dumps(sim_batch, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(node_dir / f"expression_candidates__{tower_id}.json")
    print(node_dir / f"simulation_batch__{tower_id}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
