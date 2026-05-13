from __future__ import annotations

import ast
import json
import pickle
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[4]
ANALYST_FIELD_RE = re.compile(r"^anl(\d+)_", re.I)


def parse_listlike(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    try:
        if pd.isna(value):
            return []
    except Exception:
        pass
    text = str(value).strip()
    if text in {"", "nan", "None"}:
        return []
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, (list, tuple)):
                return [str(item) for item in parsed]
        except Exception:
            pass
    return [text]


def infer_dataset_from_field(field_name: str) -> str | None:
    match = ANALYST_FIELD_RE.match(field_name)
    if not match:
        return None
    return f"analyst{int(match.group(1))}"


def safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return None


def mean_of(values: list[float | None]) -> float | None:
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return statistics.fmean(nums)


def median_of(values: list[float | None]) -> float | None:
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return statistics.median(nums)


def mode_of(values: list[str]) -> str | None:
    vals = [v for v in values if v not in {"", "nan", "None"}]
    if not vals:
        return None
    return Counter(vals).most_common(1)[0][0]


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit("Usage: build_available_datafields.py NODE_DIR REGION DELAY CATEGORY")

    node_dir = Path(sys.argv[1]).resolve()
    region = sys.argv[2].upper()
    delay = str(sys.argv[3])
    category = sys.argv[4].upper()
    category_lower = category.lower()

    screening_path = node_dir / f"dataset_screening_step1__{region}_D{delay}_{category}.json"
    used_fields_path = node_dir / f"used_fields_by_alpha__{region}_D{delay}_{category}.json"
    out_path = node_dir / f"available_datafields__{region}_D{delay}_{category}.json"

    screening = json.loads(screening_path.read_text(encoding="utf-8"))
    used_fields_obj = json.loads(used_fields_path.read_text(encoding="utf-8"))
    used_field_rows = (used_fields_obj.get("alphas") if isinstance(used_fields_obj, dict) else used_fields_obj) or []
    used_fields = sorted({field for row in used_field_rows for field in row.get("fields", [])})
    preferred_datasets = [item["dataset"] for item in screening["preferred_unused_candidates"]]
    preferred_dataset_set = set(preferred_datasets)
    dataset_scores = {item["dataset"]: item for item in screening["preferred_unused_candidates"]}

    all_data = pickle.load((ROOT_DIR / "docs" / "data_all" / "all_data.pickle").open("rb"))
    res, res_settings, res_is, res_os = all_data[f"{region}_{delay}"]

    df = pd.concat(
        [
            res[["id", "datafield", "dataset", "category", "operatorCount"]],
            res_settings[["region", "delay", "universe", "neutralization", "language"]],
            res_is[["sharpe", "fitness", "selfCorrelation", "prodCorrelation"]].rename(
                columns={"sharpe": "is_sharpe", "fitness": "is_fitness"}
            ),
            res_os[
                [
                    "sharpe",
                    "fitness",
                    "osISSharpeRatio",
                    "turnover",
                    "drawdown",
                    "returns",
                    "preCloseSharpe",
                    "sharpe60",
                    "sharpe125",
                    "sharpe250",
                    "sharpe500",
                ]
            ].rename(columns={"sharpe": "os_sharpe", "fitness": "os_fitness"}),
        ],
        axis=1,
    )

    analyst_df = df[
        df["category"].map(parse_listlike).map(lambda items: category_lower in {item.lower() for item in items})
    ].copy()

    buckets: dict[tuple[str, str], dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for row in analyst_df.to_dict(orient="records"):
        row_datasets = {item.lower() for item in parse_listlike(row["dataset"])}
        if not (row_datasets & preferred_dataset_set):
            continue

        for field_name in parse_listlike(row["datafield"]):
            inferred_dataset = infer_dataset_from_field(field_name)
            if inferred_dataset is None:
                continue
            if inferred_dataset not in preferred_dataset_set:
                continue
            if inferred_dataset not in row_datasets:
                continue
            if field_name in used_fields:
                continue

            key = (inferred_dataset, field_name)
            bucket = buckets[key]
            bucket["id"].append(row["id"])
            bucket["os_sharpe"].append(safe_float(row.get("os_sharpe")))
            bucket["os_fitness"].append(safe_float(row.get("os_fitness")))
            bucket["osis_ratio"].append(safe_float(row.get("osISSharpeRatio")))
            bucket["turnover"].append(safe_float(row.get("turnover")))
            bucket["returns"].append(safe_float(row.get("returns")))
            bucket["drawdown"].append(safe_float(row.get("drawdown")))
            bucket["is_sharpe"].append(safe_float(row.get("is_sharpe")))
            bucket["is_fitness"].append(safe_float(row.get("is_fitness")))
            bucket["self_corr"].append(safe_float(row.get("selfCorrelation")))
            bucket["prod_corr"].append(safe_float(row.get("prodCorrelation")))
            bucket["operator_count"].append(safe_float(row.get("operatorCount")))
            bucket["neutralization"].append(str(row.get("neutralization") or ""))
            bucket["universe"].append(str(row.get("universe") or ""))
            bucket["language"].append(str(row.get("language") or ""))

    results = []
    for (dataset, field_name), bucket in buckets.items():
        results.append(
            {
                "dataset": dataset,
                "datafield": field_name,
                "dataset_sharpe_ratio": dataset_scores.get(dataset, {}).get("sharpe_ratio"),
                "dataset_fitness_ratio": dataset_scores.get(dataset, {}).get("fitness_ratio"),
                "dataset_count": dataset_scores.get(dataset, {}).get("count"),
                "alpha_count": len(bucket["id"]),
                "os_sharpe_mean": mean_of(bucket["os_sharpe"]),
                "os_sharpe_median": median_of(bucket["os_sharpe"]),
                "os_fitness_mean": mean_of(bucket["os_fitness"]),
                "osis_ratio_mean": mean_of(bucket["osis_ratio"]),
                "turnover_mean": mean_of(bucket["turnover"]),
                "returns_mean": mean_of(bucket["returns"]),
                "drawdown_mean": mean_of(bucket["drawdown"]),
                "is_sharpe_mean": mean_of(bucket["is_sharpe"]),
                "is_fitness_mean": mean_of(bucket["is_fitness"]),
                "self_corr_mean": mean_of(bucket["self_corr"]),
                "prod_corr_mean": mean_of(bucket["prod_corr"]),
                "operator_count_mean": mean_of(bucket["operator_count"]),
                "neutralization_mode": mode_of(bucket["neutralization"]),
                "universe_mode": mode_of(bucket["universe"]),
                "language_mode": mode_of(bucket["language"]),
            }
        )

    results.sort(
        key=lambda item: (
            -(item["os_sharpe_mean"] or float("-inf")),
            -(item["os_fitness_mean"] or float("-inf")),
            -(item["osis_ratio_mean"] or float("-inf")),
            -(item["alpha_count"] or 0),
        )
    )

    out = {
        "region": region,
        "delay": int(delay),
        "category": category,
        "preferred_datasets": preferred_datasets,
        "used_fields_excluded": used_fields,
        "candidate_count": len(results),
        "datafields": results,
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
