from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from wqb_cli.commands.alpha import add_alpha_parser, handle_alpha
from wqb_cli.core.registry import EndpointRegistry


class FakeResponse:
    def __init__(self, *, status_code: int, json_body: object) -> None:
        self.status_code = status_code
        self.reason = "OK" if status_code == 200 else "Bad Request"
        self.headers = {"Content-Type": "application/json"}
        self.text = json.dumps(json_body)
        self._json_body = json_body

    def json(self) -> object:
        return self._json_body


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls = 0
        self.kwargs_history: list[dict[str, object]] = []

    def request(self, *args: object, **kwargs: object) -> FakeResponse:
        self.kwargs_history.append(dict(kwargs))
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return response


def _os_alpha(alpha_id: str, code: str, date_submitted: str) -> dict[str, object]:
    return {
        "id": alpha_id,
        "name": f"alpha-{alpha_id}",
        "status": "ACTIVE",
        "dateCreated": date_submitted,
        "dateSubmitted": date_submitted,
        "settings": {"region": "USA", "delay": 1},
        "regular": {"code": code, "operatorCount": 3},
    }


def _list_result(items: list[dict[str, object]]) -> dict[str, object]:
    return {
        "ok": True,
        "endpoint": "/users/self/alphas",
        "response": {"status_code": 200, "body": {"count": len(items), "results": items}},
    }


def _parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    add_alpha_parser(sub)
    args = parser.parse_args(["alpha", *argv])
    args.cookies = None
    return args


def _recent_date(days_ago: int) -> str:
    tz = ZoneInfo("America/New_York")
    return (datetime.now(tz) - timedelta(days=days_ago)).strftime("%Y-%m-%d")


class AlphaOsStoreTests(unittest.TestCase):
    def test_sync_partitions_by_quarter_and_usage_reads_local(self) -> None:
        session = FakeSession(
            [
                FakeResponse(
                    status_code=200,
                    json_body={
                        "count": 3,
                        "results": [
                            _os_alpha("aaa111", "rank(ts_backfill(field_one,63))", f"{_recent_date(5)}T10:00:00-04:00"),
                            _os_alpha("bbb222", "group_rank(field_two_x, subindustry)", f"{_recent_date(1)}T10:00:00-04:00"),
                        ],
                    },
                ),
                FakeResponse(
                    status_code=200,
                    json_body={
                        "count": 3,
                        "results": [_os_alpha("ccc333", "rank(unrelated)", f"{_recent_date(2)}T10:00:00-04:00")],
                    },
                ),
            ]
        )
        registry = EndpointRegistry.load()
        with tempfile.TemporaryDirectory() as tmp:
            store = str(Path(tmp) / "os_alphas")
            sync_args = _parse(
                ["os-sync", "--since", _recent_date(8), "--limit", "2", "--store", store]
            )
            sync_args.output = None
            with patch("wqb_cli.commands.alpha.session_from_cookies", return_value=session):
                code = handle_alpha(sync_args, registry)
            self.assertEqual(code, 0)

            q3 = json.loads((Path(store) / "meta.json").read_text(encoding="utf-8"))
            self.assertIn("last_sync", q3)
            self.assertEqual(q3["total_alphas"], 3)
            # second transport call continued pagination at offset 2
            second_params = session.kwargs_history[1].get("params") or {}
            self.assertEqual(second_params.get("offset"), "2")
            self.assertEqual(second_params.get("status"), "ACTIVE")

            usage_args = _parse(
                [
                    "field-usage",
                    "--fields",
                    "field_one,field_two_x,field_three",
                    "--store",
                    store,
                ]
            )
            usage_args.output = None
            code = handle_alpha(usage_args, registry)
            self.assertEqual(code, 0)

    def test_sync_watermark_makes_second_run_incremental(self) -> None:
        session = FakeSession(
            [
                FakeResponse(
                    status_code=200,
                    json_body={"count": 1, "results": [_os_alpha("aaa111", "rank(field_one)", "2026-09-28T10:00:00-04:00")]},
                )
            ]
        )
        registry = EndpointRegistry.load()
        with tempfile.TemporaryDirectory() as tmp:
            store = str(Path(tmp) / "os_alphas")
            first = _parse(["os-sync", "--since", _recent_date(8), "--store", store])
            first.output = None
            with patch("wqb_cli.commands.alpha.session_from_cookies", return_value=session):
                self.assertEqual(handle_alpha(first, registry), 0)
            first_calls = session.calls

            second = _parse(["os-sync", "--store", store])
            second.output = None
            with patch("wqb_cli.commands.alpha.session_from_cookies", return_value=session):
                self.assertEqual(handle_alpha(second, registry), 0)

            meta = json.loads((Path(store) / "meta.json").read_text(encoding="utf-8"))
            self.assertIn("mode", meta)
            # incremental run resumes from the watermark, not the original --since
            second_params = session.kwargs_history[first_calls].get("params") or {}
            self.assertGreater(str(second_params.get("dateCreated>")), "2025-01-01")

    def test_field_usage_empty_store_hints_sync(self) -> None:
        registry = EndpointRegistry.load()
        with tempfile.TemporaryDirectory() as tmp:
            args = _parse(["field-usage", "--fields", "field_one", "--store", str(Path(tmp) / "missing")])
            args.output = None
            code = handle_alpha(args, registry)
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
