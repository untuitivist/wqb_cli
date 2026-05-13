from __future__ import annotations

import subprocess
import inspect
import json
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from requests import Response
from wqb_core import WQBSession


def serialize(value):
    if isinstance(value, Response):
        payload = {
            "status_code": value.status_code,
            "reason": value.reason,
            "url": value.url,
            "headers": dict(value.headers),
        }
        try:
            payload["json"] = value.json()
        except ValueError:
            payload["text"] = value.text
        return payload
    if isinstance(value, dict):
        return {str(k): serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [serialize(v) for v in value]
    if inspect.isgenerator(value):
        return [serialize(v) for v in list(value)]
    return value


def main() -> None:
    if len(sys.argv) != 6:
        raise SystemExit("Usage: fetch_field_metadata.py RUN_DIR NODE_DIR REGION DELAY CATEGORY")

    run_dir = Path(sys.argv[1]).resolve()
    node_dir = Path(sys.argv[2]).resolve()
    region = sys.argv[3].upper()
    delay = sys.argv[4]
    category = sys.argv[5].upper()

    repo_root = Path(__file__).resolve().parents[4]
    finder = repo_root / "workflow" / "shared" / "find_latest_node_dir.py"
    proc = subprocess.run(
        [sys.executable, str(finder), str(run_dir), "E_data_and_field_feasibility"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    e_dir = Path(proc.stdout.strip())
    e_path = e_dir / f"available_datafields__{region}_D{delay}_{category}.json"
    e_obj = json.loads(e_path.read_text(encoding="utf-8"))
    target_fields = [row["datafield"] for row in e_obj["datafields"][:10]]

    session = WQBSession()
    rows = []
    for field_id in target_fields:
        resp = session.locate_field(field_id)
        rows.append(serialize(resp))

    out = {
        "region": region,
        "delay": int(delay),
        "category": category,
        "field_ids": target_fields,
        "fields": rows,
    }
    out_path = node_dir / f"field_metadata__{region}_D{delay}_{category}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
