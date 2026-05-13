from __future__ import annotations

import json
import re
import sys
from pathlib import Path


BASE_QUERIES = [
    "analyst forecast stock return",
    "target price revision stock return",
    "analyst recommendation return predictability",
    "earnings expectation revision stock returns",
    "analyst dispersion stock return",
]

TOKEN_MAP = {
    "ntp": "target price",
    "ntprep": "target price revision",
    "epsrep": "earnings revision",
    "numofests": "analyst coverage",
    "ebitda": "profitability expectation",
}

STOPWORDS = {
    "mean", "median", "high", "low", "fy0", "fy1", "fy2", "fy3", "fy4", "fy5",
    "fp1", "fp2", "fp3", "fp4", "fp5",
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
    e_obj = json.loads((e_dir / f"available_datafields__{region}_D{delay}_{category}.json").read_text(encoding="utf-8"))

    queries = list(BASE_QUERIES)
    field_hints: list[str] = []
    for row in e_obj["datafields"][:12]:
        suffix = re.sub(r"^anl\d+_", "", row["datafield"], flags=re.I)
        for token in suffix.split("_"):
            token = token.lower().strip()
            if not token or token in STOPWORDS:
                continue
            mapped = TOKEN_MAP.get(token)
            if mapped and mapped not in field_hints:
                field_hints.append(mapped)

    for hint in field_hints[:4]:
        q = f"analyst {hint} stock returns"
        if q not in queries:
            queries.append(q)

    out = {
        "region": region,
        "delay": int(delay),
        "category": category,
        "queries": queries,
        "field_hints": field_hints,
        "user_materials": [],
    }
    out_path = node_dir / f"queries__{region}_D{delay}_{category}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
