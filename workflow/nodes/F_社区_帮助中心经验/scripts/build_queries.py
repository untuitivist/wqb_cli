from __future__ import annotations

import json
import re
import sys
from pathlib import Path


CATEGORY_PRESET_QUERIES = {
    "analyst": [
        "analyst data",
        "analyst estimates",
        "analyst forecasts",
        "target price",
        "stock recommendations",
        "analyst revision",
    ],
}

TOKEN_MAP = {
    "ntp": "target price",
    "ntprep": "target price",
    "epsrep": "analyst revision",
    "numofests": "analyst estimates",
}

ALLOWED_ANALYST_MAPPED_QUERIES = {
    "target price",
    "analyst revision",
    "analyst estimates",
}

STOPWORDS = {
    "mean",
    "median",
    "high",
    "low",
    "fy0",
    "fy1",
    "fy2",
    "fy3",
    "fy4",
    "fy5",
    "fp1",
    "fp2",
    "fp3",
    "fp4",
    "fp5",
    "ebit",
    "ebitda",
    "capex",
}


def find_latest_e_dir(run_dir: Path) -> Path:
    matches = sorted(run_dir.glob("*_node_E_data_and_field_feasibility"))
    if not matches:
        raise FileNotFoundError("Could not find *_node_E_data_and_field_feasibility in run directory")
    return matches[-1]


def main() -> None:
    if len(sys.argv) != 6:
        raise SystemExit("Usage: build_queries.py RUN_DIR NODE_DIR REGION DELAY CATEGORY")

    run_dir = Path(sys.argv[1]).resolve()
    node_dir = Path(sys.argv[2]).resolve()
    region = sys.argv[3].upper()
    delay = sys.argv[4]
    category = sys.argv[5].upper()

    e_dir = find_latest_e_dir(run_dir)
    e_path = e_dir / f"available_datafields__{region}_D{delay}_{category}.json"
    e_obj = json.loads(e_path.read_text(encoding="utf-8"))

    queries: list[str] = []
    category_key = category.lower()
    queries.extend(CATEGORY_PRESET_QUERIES.get(category_key, [category_key]))

    top_fields = e_obj["datafields"][:15]
    for row in top_fields:
        field_name = row["datafield"]
        suffix = re.sub(r"^anl\d+_", "", field_name, flags=re.I)
        for token in suffix.split("_"):
            token = token.lower().strip()
            if not token or token in STOPWORDS:
                continue
            mapped = TOKEN_MAP.get(token, token)
            if category_key == "analyst" and mapped not in ALLOWED_ANALYST_MAPPED_QUERIES:
                continue
            if mapped not in queries:
                queries.append(mapped)

    out = {
        "region": region,
        "delay": int(delay),
        "category": category,
        "queries": queries,
    }
    out_path = node_dir / f"queries__{region}_D{delay}_{category}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
