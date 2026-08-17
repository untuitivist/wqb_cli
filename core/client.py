from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

from .registry import Endpoint, EndpointRegistry


MUTATING_METHODS = {"POST", "PATCH", "PUT", "DELETE"}


@dataclass
class PreparedRequest:
    endpoint: str
    method: str
    url: str
    params: dict[str, Any]
    json_body: Any
    headers: dict[str, str]
    auth: tuple[str, str] | None
    mutating: bool
    executable: bool
    reason: str | None = None


class WqbClient:
    def __init__(self, registry: EndpointRegistry, session: requests.Session) -> None:
        self.registry = registry
        self.session = session

    def prepare(
        self,
        endpoint: Endpoint,
        method: str,
        *,
        path_vars: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        auth: tuple[str, str] | None = None,
    ) -> PreparedRequest:
        method = method.upper()
        path_vars = path_vars or {}
        resolved = endpoint.path
        missing = []
        for name in endpoint.variables:
            value = path_vars.get(name)
            if value is None:
                missing.append(name)
                continue
            resolved = resolved.replace("{" + name + "}", str(value))
        mutating = method in MUTATING_METHODS
        executable = not missing
        reason = None
        if missing:
            reason = "missing_path_variables: " + ", ".join(missing)
        return PreparedRequest(
            endpoint=endpoint.path,
            method=method,
            url=self.registry.base_url + resolved,
            params=params or {},
            json_body=json_body,
            headers={},
            auth=auth,
            mutating=mutating,
            executable=executable,
            reason=reason,
        )

    def call_once(self, prepared: PreparedRequest) -> dict[str, Any]:
        """Execute exactly one HTTP request without following Retry-After."""

        return self.call(prepared, wait_retry_after=False)

    def call(
        self,
        prepared: PreparedRequest,
        *,
        wait_retry_after: bool = False,
        max_wait_seconds: float | None = None,
    ) -> dict[str, Any]:
        if not prepared.executable:
            return {
                "ok": False,
                "reason": prepared.reason,
                "request": prepared.__dict__,
            }
        started = time.time()
        retries = 0
        wait_events: list[dict[str, Any]] = []
        wait_timed_out = False
        while True:
            auth = prepared.auth
            json_body = prepared.json_body
            if auth is None and prepared.endpoint == "/authentication" and prepared.method == "POST" and isinstance(json_body, dict):
                email = json_body.get("email")
                password = json_body.get("password")
                if email and password:
                    auth = (str(email), str(password))
                    json_body = {key: value for key, value in json_body.items() if key not in {"email", "password"}}
            response = self.session.request(
                prepared.method,
                prepared.url,
                params=prepared.params,
                json=json_body,
                auth=auth,
                timeout=60,
                allow_redirects=False,
            )
            retry_after = response.headers.get("Retry-After")
            if not wait_retry_after or not retry_after:
                break
            sleep_seconds = float(retry_after)
            progress = self._response_progress(response)
            multiplier = 10 if self._is_sticky_sim_progress(progress) else 1
            sleep_seconds *= multiplier
            elapsed_seconds = time.time() - started
            if max_wait_seconds is not None and elapsed_seconds + sleep_seconds > max_wait_seconds:
                wait_timed_out = True
                wait_events.append(
                    {
                        "retry_after": float(retry_after),
                        "sleep_seconds": 0,
                        "progress": progress,
                        "multiplier": multiplier,
                        "skipped": True,
                        "reason": "max_wait_seconds_exceeded",
                    }
                )
                break
            wait_events.append(
                {
                    "retry_after": float(retry_after),
                    "sleep_seconds": sleep_seconds,
                    "progress": progress,
                    "multiplier": multiplier,
                }
            )
            time.sleep(sleep_seconds)
            retries += 1
        elapsed_ms = int((time.time() - started) * 1000)
        content_type = response.headers.get("Content-Type", "")
        body: Any
        if "application/json" in content_type:
            try:
                body = response.json()
            except ValueError:
                body = response.text
        elif prepared.method == "HEAD":
            body = None
        else:
            body = response.text
        return {
            "ok": 200 <= response.status_code < 400,
            "endpoint": prepared.endpoint,
            "request": {
                "method": prepared.method,
                "url": prepared.url,
                "params": prepared.params,
                "mutating": prepared.mutating,
            },
            "response": {
                "status_code": response.status_code,
                "reason": response.reason,
                "elapsed_ms": elapsed_ms,
                "content_type": content_type.split(";")[0],
                "allow": response.headers.get("Allow"),
                "retry_after": response.headers.get("Retry-After"),
                "retries": retries,
                "wait_events": wait_events,
                "wait_timed_out": wait_timed_out,
                "max_wait_seconds": max_wait_seconds,
                "location": response.headers.get("Location"),
                "body": body,
            },
        }

    @staticmethod
    def _response_progress(response: requests.Response) -> float | None:
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            return None
        try:
            body = response.json()
        except ValueError:
            return None
        progress = body.get("progress") if isinstance(body, dict) else None
        return float(progress) if isinstance(progress, int | float) else None

    @staticmethod
    def _is_sticky_sim_progress(progress: float | None) -> bool:
        if progress is None:
            return False
        return abs(progress - 0.15) <= 0.01 or abs(progress - 0.35) <= 0.01
