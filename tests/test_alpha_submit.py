from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from wqb_cli.commands.alpha import (
    _classify_submit_wait,
    _response_body,
    _wait_submit_status,
)


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int,
        reason: str = "OK",
        headers: dict[str, str] | None = None,
        text: str = "",
        json_body: object | None = None,
    ) -> None:
        self.status_code = status_code
        self.reason = reason
        self.headers = headers or {}
        self.text = text
        self._json_body = json_body

    def json(self) -> object:
        if self._json_body is None:
            raise ValueError("no json")
        return self._json_body


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls = 0

    def request(self, *args: object, **kwargs: object) -> FakeResponse:
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return response


class AlphaSubmitTests(unittest.TestCase):
    def test_response_body_keeps_full_non_json_text(self) -> None:
        text = "x" * 3000
        response = FakeResponse(status_code=200, text=text)
        self.assertEqual(_response_body(response), text)

    def test_classify_regular_submission_failure_as_460(self) -> None:
        result = {
            "response": {
                "status_code": 403,
                "body": {
                    "is": {
                        "checks": [
                            {"name": "REGULAR_SUBMISSION", "result": "FAIL", "value": 4},
                        ]
                    }
                },
            }
        }
        classified = _classify_submit_wait(result)
        self.assertEqual(classified["submit_code"], 460)

    def test_classify_power_pool_failures(self) -> None:
        monthly = {
            "response": {
                "status_code": 403,
                "body": {"is": {"checks": [{"name": "POWER_POOL_MONTHLY_SUBMISSION", "result": "FAIL"}]}},
            }
        }
        power_pool = {
            "response": {
                "status_code": 403,
                "body": {"is": {"checks": [{"name": "POWER_POOL_SUBMISSION", "result": "FAIL"}]}},
            }
        }
        self.assertEqual(_classify_submit_wait(monthly)["submit_code"], 461)
        self.assertEqual(_classify_submit_wait(power_pool)["submit_code"], 462)

    def test_classify_already_submitted_as_success(self) -> None:
        result = {
            "response": {
                "status_code": 403,
                "body": {"is": {"checks": [{"name": "ALREADY_SUBMITTED", "result": "FAIL"}]}},
            }
        }
        classified = _classify_submit_wait(result)
        self.assertEqual(classified["submit_code"], 200)
        self.assertEqual(classified["reason"], "already_submitted")

    def test_wait_submit_status_times_out_on_retry_after(self) -> None:
        client = SimpleNamespace(
            session=FakeSession(
                [
                    FakeResponse(
                        status_code=200,
                        headers={"Retry-After": "1.0", "Content-Type": "text/html"},
                        text="",
                    )
                ]
            )
        )
        prepared = SimpleNamespace(
            executable=True,
            endpoint="/alphas/{alpha_id}/submit",
            method="GET",
            url="https://api.worldquantbrain.com/alphas/A/submit",
            params={},
            json_body=None,
            mutating=False,
        )

        with patch("wqb_cli.commands.alpha.time.sleep"):
            result = _wait_submit_status(
                client, prepared, max_wait_seconds=0.5, retry_after_multiplier=2.0
            )

        self.assertTrue(result["response"]["wait_timed_out"])
        self.assertEqual(result["response"]["wait_events"][0]["reason"], "max_wait_seconds_exceeded")
        self.assertEqual(_classify_submit_wait(result)["submit_code"], 408)


if __name__ == "__main__":
    unittest.main()
