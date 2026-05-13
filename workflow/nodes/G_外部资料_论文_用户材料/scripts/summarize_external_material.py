from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def classify(row: dict) -> str:
    text = (row.get("title", "") + " " + row.get("summary", "")).lower()
    if "target price" in text or "recommendation" in text:
        return "price_target_and_recommendation"
    if "revision" in text or "forecast" in text or "earnings" in text:
        return "forecast_revision_and_expectation"
    if "dispersion" in text or "disagreement" in text:
        return "dispersion_and_disagreement"
    if "coverage" in text:
        return "coverage_and_attention"
    return "general_analyst_signal"


def insight_for_bucket(bucket: str) -> str:
    mapping = {
        "price_target_and_recommendation": "target price and recommendation changes can proxy analyst-upside repricing and sentiment-adjusted expected return",
        "forecast_revision_and_expectation": "forecast and earnings expectation revisions can capture delayed repricing of changing analyst information",
        "dispersion_and_disagreement": "dispersion between optimistic and base analyst views can indicate uncertainty, convex upside, or heterogeneous information arrival",
        "coverage_and_attention": "coverage can act as a credibility or attention regime variable rather than a pure alpha on its own",
        "general_analyst_signal": "analyst variables can matter when transformed into repricing, gap, or condition structures rather than raw level ranks",
    }
    return mapping[bucket]


def short_note(row: dict) -> str:
    title = row.get("title", "")
    summary = re.sub(r"\s+", " ", row.get("summary", "")).strip()
    if len(summary) > 220:
        summary = summary[:217] + "..."
    return f"{title}: {summary}"


def main() -> None:
    if len(sys.argv) != 6:
        raise SystemExit("Usage: summarize_external_material.py RUN_DIR NODE_DIR REGION DELAY CATEGORY")

    _run_dir = Path(sys.argv[1]).resolve()
    node_dir = Path(sys.argv[2]).resolve()
    region = sys.argv[3].upper()
    delay = sys.argv[4]
    category = sys.argv[5].upper()

    arxiv = json.loads((node_dir / f"arxiv_results__{region}_D{delay}_{category}.json").read_text(encoding="utf-8"))
    rows = arxiv["results"]

    grouped: dict[str, list[dict]] = {}
    for row in rows:
        bucket = classify(row)
        grouped.setdefault(bucket, []).append(row)

    mechanism_support = []
    for bucket, items in grouped.items():
        mechanism_support.append(
            {
                "theme": bucket,
                "insight": insight_for_bucket(bucket),
                "paper_count": len(items),
                "top_papers": [
                    {
                        "title": item["title"],
                        "published": item["published"],
                        "id": item["id"],
                        "note": short_note(item),
                    }
                    for item in items[:3]
                ],
            }
        )

    out = {
        "region": region,
        "delay": int(delay),
        "category": category,
        "user_materials_present": False,
        "mechanism_support": mechanism_support,
        "top_external_papers": [
            {
                "title": row["title"],
                "published": row["published"],
                "id": row["id"],
                "categories": row["categories"],
                "note": short_note(row),
            }
            for row in rows[:10]
        ],
        "external_conclusions": [
            "Analyst target price and recommendation information is most useful when expressed as repricing or upside-gap structures rather than raw levels.",
            "Forecast and earnings revisions are consistent with delayed information incorporation and can support revision-based mechanisms.",
            "Analyst dispersion or optimistic-vs-base gaps can support convexity-style hypotheses, especially when combined with coverage or attention gating.",
            "Coverage should be treated as a regime or credibility condition instead of a standalone signal when building analyst alphas.",
        ],
    }

    out_path = node_dir / f"external_material_summary__{region}_D{delay}_{category}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
