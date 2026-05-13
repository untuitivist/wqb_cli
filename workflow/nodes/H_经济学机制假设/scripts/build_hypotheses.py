from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 6:
        raise SystemExit("Usage: build_hypotheses.py RUN_DIR NODE_DIR REGION DELAY CATEGORY")

    run_dir = Path(sys.argv[1]).resolve()
    node_dir = Path(sys.argv[2]).resolve()
    region = sys.argv[3].upper()
    delay = sys.argv[4]
    category = sys.argv[5].upper()

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

    def try_latest_dir(slug: str) -> Path | None:
        proc = subprocess.run(
            [sys.executable, str(finder), str(run_dir), slug],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        return Path(proc.stdout.strip())

    theme_path = latest_dir("B_theme_platform_opportunities") / "messages_summary.json"
    d_path = latest_dir("D_main_tower") / "decision.json"
    e_path = latest_dir("E_data_and_field_feasibility") / f"available_datafields__{region}_D{delay}_{category}.json"
    f_path = latest_dir("F_community_help_center_experience") / f"community_experience__{region}_D{delay}_{category}.json"
    g_path = latest_dir("G_external_material") / f"external_material_summary__{region}_D{delay}_{category}.json"
    k_dir = try_latest_dir("K_diagnosis")
    k_path = None if k_dir is None else k_dir / f"diagnosis__{region}_D{delay}_{category}.json"
    meta_path = node_dir / f"field_metadata__{region}_D{delay}_{category}.json"

    theme_obj = json.loads(theme_path.read_text(encoding="utf-8-sig"))
    d_obj = json.loads(d_path.read_text(encoding="utf-8-sig"))
    e_obj = json.loads(e_path.read_text(encoding="utf-8-sig"))
    f_obj = json.loads(f_path.read_text(encoding="utf-8-sig"))
    g_obj = json.loads(g_path.read_text(encoding="utf-8-sig"))
    k_obj = None if k_path is None or not k_path.exists() else json.loads(k_path.read_text(encoding="utf-8-sig"))
    meta_obj = json.loads(meta_path.read_text(encoding="utf-8-sig"))

    field_map = {row["json"]["id"]: row["json"] for row in meta_obj["fields"] if row.get("json")}
    top_fields = e_obj["datafields"][:12]
    top_titles = [row["title"] for row in f_obj["forum_topics"][:6]]
    recent_titles = [row["title"] for row in theme_obj["results"][:6]]
    external_conclusions = g_obj.get("external_conclusions", [])
    external_themes = [
        {
            "theme": row.get("theme"),
            "insight": row.get("insight"),
            "paper_count": row.get("paper_count"),
        }
        for row in g_obj.get("mechanism_support", [])[:6]
    ]
    top_k = [] if k_obj is None else k_obj.get("ranked_alphas", [])[:5]
    k_feedback = [
        {
            "candidate_id": row.get("candidate_id"),
            "alpha_id": row.get("alpha_id"),
            "quality_bucket": row.get("quality_bucket"),
            "sharpe": row.get("metrics", {}).get("sharpe"),
            "fitness": row.get("metrics", {}).get("fitness"),
            "turnover": row.get("metrics", {}).get("turnover"),
            "margin": row.get("metrics", {}).get("margin"),
        }
        for row in top_k
    ]

    hypotheses = [
        {
            "id": "H1_repricing_from_forward_consensus_levels",
            "priority": 1,
            "core_fields": [
                "anl14_median_epsrep_fy1",
                "anl14_median_ntprep_fy1",
                "anl14_median_ebitda_fy2",
            ],
            "economic_logic": "Forward analyst consensus levels only create usable alpha if the market is still repricing them gradually. K now shows the revision family is the strongest surviving family, so the next mechanism should explicitly prioritize forward-consensus revision and cross-horizon repricing rather than static consensus levels.",
            "why_it_fits_tower": "USA / D1 / ANALYST remains the point-lighting tower, and these fields still define the core profitability family. K shows the tower is right, but only revision-style transformations have real traction under the hard alpha thresholds.",
            "supporting_internal_evidence": [
                "Creating D0 Alphas with Analyst Data",
                "Crafting Alphas from Analyst Estimates: A Guide for Delay 0 Data",
                "Getting started with Analyst Datasets",
            ],
            "supporting_external_evidence": [
                "Forecast and earnings revisions are consistent with delayed information incorporation and can support revision-based mechanisms.",
                "Forecast precision and analyst trading profitability evidence supports transformed repricing structures instead of naive raw levels.",
            ],
            "risk_notes": [
            "Current batch still has zero true good alpha by hard thresholds, so revision needs stronger structure, not just repetition." if k_obj is not None else "First pass: revision family is still the most coherent starting mechanism inside analyst14.",
            "Forward-consensus fields should be pushed into stronger repricing or acceleration structures rather than reused as slow raw levels.",
            ],
            "k_feedback": [
                "I6_h1_eps_revision_delta is the strongest current survivor by a clear margin." if k_obj is not None else "No K feedback yet; use this as the initial primary family.",
                "There are still zero true good alpha under the hard thresholds, so this family should be strengthened further rather than treated as finished." if k_obj is not None else "Start with repricing and revision rather than static levels.",
            ],
        },
        {
            "id": "H4_upside_minus_base_convexity",
            "priority": 2,
            "core_fields": [
                "anl14_high_ntprep_fy2",
                "anl14_high_ebitda_fy3",
            ],
            "economic_logic": "The optimistic tail of analyst expectations should be most useful when expressed as upside-minus-base convexity, not as a slow raw optimistic level. K shows this family still has value, but it is now second to the revision family rather than the main line.",
            "why_it_fits_tower": "This remains the best non-revision family inside the same dataset and gives a secondary path to stronger structures without changing tower or field universe.",
            "supporting_internal_evidence": [
                "Research Paper 12: Stock Recommendations from Stochastic Discounted Cash Flows",
                "Research Paper: First Impression Bias: Evidence from Analyst Forecasts",
            ],
            "supporting_external_evidence": [
                "Analyst dispersion or optimistic-vs-base gaps can support convexity-style hypotheses, especially with coverage or attention gating.",
                "Target price and profitability expectation upside are better framed as gap or convexity structures than slow consensus levels.",
            ],
            "risk_notes": [
                "Still below hard alpha thresholds, so this family should not dominate the next batch.",
                "Optimistic-tail signals may still need sharper gap emphasis or stronger conditional use to compete with the revision family.",
            ],
            "k_feedback": [
                "I3_h4_convexity_tanh_gap is still a useful keeper, but it is no longer the top family once hard-threshold-aware K is applied." if k_obj is not None else "Keep convexity as the main non-revision comparison family.",
                "This family should remain in the batch, but below revision-based mechanisms." if k_obj is not None else "Use as a secondary family in the first batch.",
            ],
        },
        {
            "id": "H2_downside_asymmetric_repricing",
            "priority": 3,
            "core_fields": [
                "anl14_low_epsrep_fp5",
            ],
            "economic_logic": "The pessimistic tail of analyst expectations should matter when downside repricing is gradual and asymmetric. The next mechanism should treat the low estimate as a downside state variable or stress gate rather than a standalone level.",
            "why_it_fits_tower": "It remains in analyst14, survives E-node screening, and is still economically distinct from central-consensus signals, but it now has to be used in an asymmetric stress mechanism.",
            "supporting_internal_evidence": [
                "Research Paper: First Impression Bias: Evidence from Analyst Forecasts",
                "Improving Analyst vs Actual Earnings-Based Alphas",
            ],
            "supporting_external_evidence": [
                "Target price and recommendation style information is more useful as repricing or gap information than as a bare level.",
                "Downside analyst states should be treated as stress conditions or asymmetric repricing triggers.",
            ],
            "risk_notes": [
                "Still under-tested in current K compared with H1 and H4.",
                "Should only be expanded if it complements revision and convexity instead of replacing them.",
            ],
            "k_feedback": [
                "No current candidate from this family cleared hard thresholds." if k_obj is not None else "No K feedback yet; keep this lower priority from the start.",
                "Keep it available as a secondary mechanism, not as the main next-batch driver.",
            ],
        },
        {
            "id": "H3_coverage_conditioned_repricing",
            "priority": 4,
            "core_fields": [
                "anl14_numofests_ntp_fy3",
                "anl14_median_ntprep_fy1",
            ],
            "economic_logic": "Coverage should not simply scale analyst signals; it should decide when repricing information is credible enough to act on. The next mechanism should use coverage as a regime selector or conditional confidence filter, not a dominant standalone family.",
            "why_it_fits_tower": "This still uses one signal field plus one confidence field and remains a clean supporting structure for conditional logic.",
            "supporting_internal_evidence": [
                "Unlocking Insights from Analyst Datasets: A Comprehensive Guide for USA Region",
                "Research Paper 16: Are Analyst Short-Term Trade Ideas Valuable?",
            ],
            "supporting_external_evidence": [
                "Coverage should be treated as a regime or credibility condition instead of a standalone signal.",
                "Coverage-conditioned repricing is better aligned with analyst credibility than a simple multiplicative gate.",
            ],
            "risk_notes": [
                "Current coverage family is still weak in K and should not dominate the next batch.",
                "Best use is as a supporting conditional layer for revision or convexity rather than the main economic mechanism.",
            ],
            "k_feedback": [
                "Coverage-based candidates improved turnover but remained too weak on hard alpha quality." if k_obj is not None else "Use coverage only as support from the first pass.",
                "Keep as a supporting condition, not as the primary family.",
            ],
        },
    ]

    out = {
        "region": region,
        "delay": int(delay),
        "category": category,
        "theme_context": {
            "recent_platform_titles": recent_titles,
            "judgment": "Theme is not the primary driver for this tower; point-lighting priority overrides the currently stronger MEA theme.",
        },
        "tower_context": d_obj,
        "candidate_field_context": {
            "preferred_datasets": e_obj["preferred_datasets"],
            "top_candidate_fields": top_fields,
        },
        "community_context": {
            "queries": f_obj["queries"],
            "top_forum_titles": top_titles,
        },
        "external_material_context": {
            "queries": g_obj.get("queries", []),
            "top_external_papers": g_obj.get("top_external_papers", [])[:8],
            "mechanism_support": external_themes,
            "external_conclusions": external_conclusions,
        },
        "k_context": {
            "quality_summary": {} if k_obj is None else k_obj.get("quality_summary", {}),
            "good_alpha_definition": {} if k_obj is None else k_obj.get("good_alpha_definition", {}),
            "top_k_feedback": k_feedback,
            "judgment": "No K yet; this is the initial mechanism pack built from B/D/E/F/G." if k_obj is None else "Current batch has zero true good alpha by hard thresholds; H1 revision is strongest, H4 convexity is second, and H3 remains a supporting conditional family. The next round should optimize family strength first rather than react to overuse warnings.",
        },
        "field_metadata_summary": {
            field_id: {
                "description": field_map[field_id]["description"],
                "type": field_map[field_id]["type"],
                "dataset": field_map[field_id]["dataset"]["id"],
                "subcategory": field_map[field_id]["subcategory"]["id"],
            }
            for field_id in field_map
        },
        "hypotheses": hypotheses,
    }

    out_path = node_dir / f"mechanism_hypotheses__{region}_D{delay}_{category}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
