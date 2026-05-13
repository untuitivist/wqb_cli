from __future__ import annotations

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
    if len(sys.argv) != 5:
        raise SystemExit("Usage: fetch_active_alphas.py NODE_DIR REGION DELAY CATEGORY")

    node_dir = Path(sys.argv[1]).resolve()
    region = sys.argv[2]
    delay = sys.argv[3]
    category = sys.argv[4].upper()

    out_path = node_dir / f"active_tower_alphas__{region}_D{delay}_{category}__WQBRAIN.json"
    session = WQBSession()
    result = session.filter_alphas(status="ACTIVE", tag=f"{region}/D{delay}/{category}")
    out_path.write_text(json.dumps(serialize(result), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
