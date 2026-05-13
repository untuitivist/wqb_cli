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


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: fetch_all_operators.py NODE_DIR")

    node_dir = Path(sys.argv[1]).resolve()
    node_dir.mkdir(parents=True, exist_ok=True)

    session = WQBSession()
    out = None
    error_payload = None
    try:
        resp = session.get_operators()
        out = serialize(resp)
    except Exception as exc:
        error_payload = {
            "status": "fallback",
            "error": repr(exc),
        }
        candidates = []
        for p in sorted(node_dir.parents[2].glob("*_node_I_expression_candidates/all_operators.json")):
            if p.resolve() != (node_dir / "all_operators.json").resolve():
                candidates.append(p)
        if not candidates:
            repo_docs = node_dir.parents[2].parents[1] / "research_runs"
            for p in sorted(repo_docs.glob("**/all_operators.json")):
                if p.resolve() != (node_dir / "all_operators.json").resolve():
                    candidates.append(p)
        if candidates:
            latest = max(candidates, key=lambda p: p.stat().st_mtime)
            base = json.loads(latest.read_text(encoding="utf-8-sig"))
            if isinstance(base, dict):
                base["fallback_info"] = {
                    "reused_from": str(latest),
                    **error_payload,
                }
            out = base
        else:
            out = {
                "status": "fallback-empty",
                **error_payload,
                "operators": [],
            }
    out_path = node_dir / "all_operators.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
