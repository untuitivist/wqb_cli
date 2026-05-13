from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit("Usage: write_summary.py NODE_DIR REGION DELAY CATEGORY")

    node_dir = Path(sys.argv[1]).resolve()
    region = sys.argv[2]
    delay = sys.argv[3]
    category = sys.argv[4].upper()

    dataset_path = node_dir / f"dataset_screening_step1__{region}_D{delay}_{category}.json"
    fields_path = node_dir / f"available_datafields__{region}_D{delay}_{category}.json"

    dataset_info = json.loads(dataset_path.read_text(encoding="utf-8"))
    field_info = json.loads(fields_path.read_text(encoding="utf-8"))

    rejected = [item["dataset"] for item in dataset_info["rejected_for_bad_os"][:12]]
    preferred = [item["dataset"] for item in dataset_info["preferred_unused_candidates"][:8]]
    top_fields = field_info["datafields"][:10]

    top_lines = "\n".join(
        f"- `{row['dataset']}` / `{row['datafield']}`: "
        f"os_sharpe_mean={row['os_sharpe_mean']:.4f}, "
        f"os_fitness_mean={row['os_fitness_mean']:.4f}, "
        f"alpha_count={row['alpha_count']}"
        for row in top_fields
    )
    if not top_lines:
        top_lines = "- No candidate datafields."

    summary = f"""# Data And Field Feasibility

## Commands
- `WQBRAIN\\python.exe workflow/nodes/E_数据与字段可行性/scripts/fetch_active_alphas.py "{node_dir}" "{region}" "{delay}" "{category}"`
- `WQBRAIN\\python.exe workflow/nodes/E_数据与字段可行性/scripts/extract_used_fields.py "{node_dir}" "{region}" "{delay}" "{category}"`
- `WQBRAIN\\python.exe workflow/nodes/E_数据与字段可行性/scripts/screen_datasets.py "{node_dir}" "{region}" "{delay}" "{category}"`
- `WQBRAIN\\python.exe workflow/nodes/E_数据与字段可行性/scripts/build_available_datafields.py "{node_dir}" "{region}" "{delay}" "{category}"`

## Outputs
- active_tower_alphas__{region}_D{delay}_{category}__WQBRAIN.json
- used_fields_by_alpha__{region}_D{delay}_{category}.json
- dataset_screening_step1__{region}_D{delay}_{category}.json
- available_datafields__{region}_D{delay}_{category}.json

## Node Judgment
- OS/IS first-pass rejected datasets:
  - {", ".join(rejected) if rejected else "None"}
- Preferred remaining datasets:
  - {", ".join(preferred) if preferred else "None"}
- Hard-excluded used datafields:
  - {len(field_info["used_fields_excluded"])} fields
- Available candidate datafields:
  - {field_info["candidate_count"]} fields

## Top Candidate Datafields
{top_lines}
"""
    out_path = node_dir / "node_summary.md"
    out_path.write_text(summary, encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
