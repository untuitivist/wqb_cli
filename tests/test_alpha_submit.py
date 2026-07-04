from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from wqb_cli.commands.alpha import (
    _call_waiting_alpha,
    _classify_submit_post,
    _classify_submit_wait,
    _response_body,
    _should_retry_alpha_with_basic_auth,
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
        self.kwargs_history: list[dict[str, object]] = []

    def request(self, *args: object, **kwargs: object) -> FakeResponse:
        self.kwargs_history.append(dict(kwargs))
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

    def test_classify_submit_post_success_as_api_accepted_only(self) -> None:
        classified = _classify_submit_post({"response": {"status_code": 303}})
        self.assertEqual(classified["submit_code"], 303)
        self.assertEqual(classified["reason"], "submit_api_accepted")

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

    def test_alpha_check_retries_with_basic_auth_after_cookie_401(self) -> None:
        session = FakeSession(
            [
                FakeResponse(
                    status_code=401,
                    reason="Unauthorized",
                    headers={"Content-Type": "application/json"},
                    json_body={"detail": "Incorrect authentication credentials."},
                ),
                FakeResponse(
                    status_code=200,
                    reason="OK",
                    headers={"Content-Type": "application/json"},
                    json_body={"is": {"checks": [{"name": "LOW_SHARPE", "result": "PASS"}]}},
                ),
            ]
        )
        client = SimpleNamespace(session=session, call=None)

        from wqb_cli.core.client import WqbClient, PreparedRequest

        client = WqbClient(SimpleNamespace(base_url="https://api.worldquantbrain.com"), session)
        prepared = PreparedRequest(
            endpoint="/alphas/{alpha_id}/check",
            method="GET",
            url="https://api.worldquantbrain.com/alphas/demo/check",
            params={},
            json_body=None,
            headers={},
            auth=None,
            mutating=False,
            executable=True,
            reason=None,
        )
        result = _call_waiting_alpha(client, prepared, 60.0, basic_auth=("user@example.com", "secret"))
        self.assertTrue(result["ok"])
        self.assertEqual(session.calls, 2)
        self.assertIsNone(session.kwargs_history[0].get("auth"))
        self.assertEqual(session.kwargs_history[1].get("auth"), ("user@example.com", "secret"))

    def test_alpha_basic_auth_retry_only_for_alpha_401(self) -> None:
        result = {
            "ok": False,
            "response": {"status_code": 401},
        }
        prepared = SimpleNamespace(endpoint="/users/self/alphas", auth=None)
        self.assertFalse(_should_retry_alpha_with_basic_auth(result, prepared, ("u", "p")))
        prepared = SimpleNamespace(endpoint="/alphas/{alpha_id}/check", auth=("u", "p"))
        self.assertFalse(_should_retry_alpha_with_basic_auth(result, prepared, ("u", "p")))
        prepared = SimpleNamespace(endpoint="/alphas/{alpha_id}/check", auth=None)
        self.assertTrue(_should_retry_alpha_with_basic_auth(result, prepared, ("u", "p")))


if __name__ == "__main__":
    unittest.main()
