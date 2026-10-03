from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from wqb_cli.commands.alpha import add_alpha_parser, handle_alpha
from wqb_cli.core.client import WqbClient
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


def _alpha(alpha_id: str, code: str, *, submitted: bool) -> dict[str, object]:
    return {
        "id": alpha_id,
        "status": "ACTIVE" if submitted else "UNSUBMITTED",
        "dateCreated": "2026-08-01T00:00:00-04:00",
        "dateSubmitted": "2026-08-02T00:00:00-04:00" if submitted else None,
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


class AlphaFieldUsageTests(unittest.TestCase):
    def test_matches_fields_across_pages_and_buckets(self) -> None:
        session = FakeSession(
            [
                FakeResponse(
                    status_code=200,
                    json_body={
                        "count": 3,
                        "results": [
                            _alpha("aaa111", "rank(ts_backfill(field_one,63))", submitted=True),
                            _alpha("bbb222", "group_rank(field_two_x, subindustry)", submitted=False),
                        ],
                    },
                ),
                FakeResponse(
                    status_code=200,
                    json_body={
                        "count": 3,
                        "results": [_alpha("ccc333", "rank(field_one_extended)", submitted=False)],
                    },
                ),
            ]
        )
        registry = EndpointRegistry.load()
        args = _parse(
            [
                "field-usage",
                "--fields",
                "field_one,field_two_x,field_three",
                "--after",
                "2026-07-01",
                "--limit",
                "2",
                "--settings-region",
                "USA",
                "--settings-delay",
                "1",
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "usage.json")
            args.output = out
            with patch_session(session):
                code = handle_alpha(args, registry)
            self.assertEqual(code, 0)
            result = json.loads(Path(out).read_text(encoding="utf-8"))
        self.assertEqual(result["alphas_scanned"], 3)
        self.assertEqual(result["verdict"]["field_one"], "used-in-submitted:aaa111")
        self.assertEqual(result["verdict"]["field_two_x"], "used-in-unsubmitted:bbb222")
        self.assertEqual(result["verdict"]["field_three"], "not-used")
        submitted_records = result["fields"]["field_one"]["submitted"]
        self.assertEqual(submitted_records[0]["id"], "aaa111")
        # word-boundary: field_one must not match field_one_extended
        self.assertEqual(result["fields"]["field_one"]["unsubmitted"], [])
        # paging and filters reached the transport
        first_kwargs = session.kwargs_history[0]
        params = first_kwargs.get("params") or {}
        self.assertEqual(params.get("offset"), "0")
        self.assertIn("dateCreated>", params)
        self.assertTrue(str(params["dateCreated>"]).startswith("2026-07-01T00:00:00"))
        self.assertEqual(params.get("settings.region"), "USA")
        second_kwargs = session.kwargs_history[1]
        self.assertEqual((second_kwargs.get("params") or {}).get("offset"), "2")

    def test_empty_fields_fails_fast(self) -> None:
        registry = EndpointRegistry.load()
        args = _parse(["field-usage", "--fields", " , "])
        args.output = None
        with patch_session(FakeSession([])):
            code = handle_alpha(args, registry)
        self.assertEqual(code, 2)

    def test_transport_error_returns_one(self) -> None:
        session = FakeSession(
            [FakeResponse(status_code=400, json_body=["Expected ISO 8601 datetime with timezone"])]
        )
        registry = EndpointRegistry.load()
        args = _parse(["field-usage", "--fields", "field_one", "--limit", "100"])
        args.output = None
        with patch_session(session):
            code = handle_alpha(args, registry)
        self.assertEqual(code, 1)


def patch_session(session: FakeSession):
    import unittest.mock

    return unittest.mock.patch(
        "wqb_cli.commands.alpha.session_from_cookies", return_value=session
    )


if __name__ == "__main__":
    unittest.main()
