from __future__ import annotations

import gzip
import json
import re
import sys
import zlib
from pathlib import Path

import msgpack


ROOT_DIR = Path(__file__).resolve().parents[4]


def decode_info_data() -> dict:
    info_path = ROOT_DIR / "docs" / "data_all" / "info_data.bin"
    raw = info_path.read_bytes()
    for fn in (
        lambda b: zlib.decompress(b),
        lambda b: zlib.decompress(b, -zlib.MAX_WBITS),
        lambda b: gzip.decompress(b),
    ):
        try:
            dec = fn(raw)
            return msgpack.unpackb(dec, raw=False)
        except Exception:
            continue
    raise RuntimeError("failed to decode info_data.bin")


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit("Usage: screen_datasets.py NODE_DIR REGION DELAY CATEGORY")

    node_dir = Path(sys.argv[1]).resolve()
    region = sys.argv[2].upper()
    delay = sys.argv[3]
    category = sys.argv[4].lower()
    category_upper = sys.argv[4].upper()

    info = decode_info_data()
    region_delay_key = f"{region}_{delay}"
    data_block = info[region_delay_key]

    all_items = []
    for name, value in data_block["isos"]["dataset"].items():
        if name.startswith(category):
            all_items.append(
                {
                    "dataset": name,
                    "sharpe_ratio": value.get("sharpe_ratio"),
                    "fitness_ratio": value.get("fitness_ratio"),
                    "count": value.get("count"),
                }
            )

    active_path = node_dir / f"active_tower_alphas__{region}_D{delay}_{category_upper}__WQBRAIN.json"
    active = json.loads(active_path.read_text(encoding="utf-8"))
    results = active[0]["json"]["results"]

    used = set()
    field_pat = re.compile(r"\banl\d+_[A-Za-z0-9_]+\b")
    prefix_pat = re.compile(r"anl(\d+)_")
    for row in results:
        code = row.get("regular", {}).get("code", "") or ""
        for field in field_pat.findall(code):
            match = prefix_pat.match(field)
            if match:
                used.add(f"analyst{match.group(1)}")

    floor = data_block["isos"]["category"][category]["sharpe_ratio"]
    rejected_os = [x for x in all_items if x["sharpe_ratio"] is None or x["sharpe_ratio"] < floor]
    remaining = [x for x in all_items if x["sharpe_ratio"] is not None and x["sharpe_ratio"] >= floor]
    unused_remaining = [x for x in remaining if x["dataset"] not in used]
    unused_remaining.sort(key=lambda x: (-x["sharpe_ratio"], -x["fitness_ratio"], -x["count"]))

    out = {
        "category_sharpe_floor": floor,
        "used_datasets": sorted(used),
        "rejected_for_bad_os": rejected_os,
        "remaining_after_os_filter": remaining,
        "preferred_unused_candidates": unused_remaining,
    }

    out_path = node_dir / f"dataset_screening_step1__{region}_D{delay}_{category_upper}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
