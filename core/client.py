from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import requests

from .auth import (
    clear_worldquantbrain_cookies,
    resolve_login_payload,
    save_cookie_payload,
)
from .registry import Endpoint, EndpointRegistry


MUTATING_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
WQB_SESSION_REAUTH_STATUSES = frozenset({204, 401, 429})


@dataclass(frozen=True)
class AutoAuthPolicy:
    """Bounded WQBSession-style authentication and request replay policy."""

    request_replays: int = 3
    login_attempts: int = 3
    delay_seconds: float = 2.0
    expiry_seconds: int = 3600
    statuses: frozenset[int] = WQB_SESSION_REAUTH_STATUSES

    def __post_init__(self) -> None:
        if self.request_replays < 0:
            raise ValueError("request_replays must not be negative")
        if self.login_attempts < 1:
            raise ValueError("login_attempts must be at least 1")
        if self.delay_seconds < 0:
            raise ValueError("delay_seconds must not be negative")
        if self.expiry_seconds < 1:
            raise ValueError("expiry_seconds must be at least 1")


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
    def __init__(
        self,
        registry: EndpointRegistry,
        session: requests.Session,
        *,
        auto_auth: bool = True,
        auto_auth_policy: AutoAuthPolicy | None = None,
        login_payload_provider: Callable[[], dict[str, Any]] | None = None,
        cookie_path: str | None = None,
        cookie_saver: Callable[[requests.Session, str | None], None] | None = save_cookie_payload,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.registry = registry
        self.session = session
        self.auto_auth = auto_auth
        self.auto_auth_policy = auto_auth_policy or AutoAuthPolicy()
        self.login_payload_provider = login_payload_provider or (
            lambda: resolve_login_payload(expiry=self.auto_auth_policy.expiry_seconds)
        )
        self.cookie_path = (
            cookie_path
            if cookie_path is not None
            else getattr(session, "_wqb_cookie_path", None)
        )
        self.cookie_saver = cookie_saver
        self.sleeper = sleeper
        self._auth_lock = threading.Lock()
        self._auth_generation = 0

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

    def call_once(
        self,
        prepared: PreparedRequest,
        *,
        auto_auth: bool | None = None,
    ) -> dict[str, Any]:
        """Execute one logical request without following Retry-After.

        Automatic authentication and replay still apply because a rejected
        request has not produced the requested server outcome.
        """

        return self.call(
            prepared,
            wait_retry_after=False,
            auto_auth=auto_auth,
        )

    def call(
        self,
        prepared: PreparedRequest,
        *,
        wait_retry_after: bool = False,
        max_wait_seconds: float | None = None,
        auto_auth: bool | None = None,
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
        auth_events: list[dict[str, Any]] = []
        auth_replays = 0
        wait_timed_out = False
        while True:
            response, request_auth_events, request_auth_replays = self._request_with_auto_auth(
                prepared,
                enabled=self.auto_auth if auto_auth is None else auto_auth,
            )
            auth_events.extend(request_auth_events)
            auth_replays += request_auth_replays
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
            self.sleeper(sleep_seconds)
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
        authentication_exhausted = self._should_reauthenticate(
            prepared,
            response,
            enabled=self.auto_auth if auto_auth is None else auto_auth,
        )
        response_payload = {
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
        }
        if auth_events:
            response_payload["authentication"] = {
                "triggered": True,
                "replays": auth_replays,
                "exhausted": authentication_exhausted,
                "events": auth_events,
            }
        return {
            "ok": self._response_succeeded(prepared, response)
            and not authentication_exhausted,
            "endpoint": prepared.endpoint,
            "request": {
                "method": prepared.method,
                "url": prepared.url,
                "params": prepared.params,
                "mutating": prepared.mutating,
            },
            "response": response_payload,
        }

    def _request_with_auto_auth(
        self,
        prepared: PreparedRequest,
        *,
        enabled: bool,
    ) -> tuple[requests.Response, list[dict[str, Any]], int]:
        observed_generation = self._auth_generation
        response = self._request_once(prepared)
        events: list[dict[str, Any]] = []
        replays = 0
        for replay in range(1, self.auto_auth_policy.request_replays + 1):
            if not self._should_reauthenticate(prepared, response, enabled=enabled):
                break
            delay = self.auto_auth_policy.delay_seconds
            if delay:
                self.sleeper(delay)
            refresh = self._ensure_authenticated(observed_generation)
            events.append(
                {
                    "trigger_status": response.status_code,
                    "replay": replay,
                    "delay_seconds": delay,
                    "refresh": refresh,
                }
            )
            response = self._request_once(prepared)
            replays += 1
            observed_generation = self._auth_generation
        return response, events, replays

    def _request_once(self, prepared: PreparedRequest) -> requests.Response:
        auth = prepared.auth
        json_body = prepared.json_body
        if (
            auth is None
            and prepared.endpoint == "/authentication"
            and prepared.method == "POST"
            and isinstance(json_body, dict)
        ):
            email = json_body.get("email")
            password = json_body.get("password")
            if email and password:
                auth = (str(email), str(password))
                json_body = {
                    key: value
                    for key, value in json_body.items()
                    if key not in {"email", "password"}
                }
        if prepared.endpoint == "/authentication" and prepared.method == "POST":
            clear_worldquantbrain_cookies(self.session)
        return self.session.request(
            prepared.method,
            prepared.url,
            params=prepared.params,
            json=json_body,
            auth=auth,
            timeout=60,
            allow_redirects=False,
        )

    def _should_reauthenticate(
        self,
        prepared: PreparedRequest,
        response: requests.Response,
        *,
        enabled: bool,
    ) -> bool:
        if not enabled or prepared.endpoint == "/authentication":
            return False
        return response.status_code in self.auto_auth_policy.statuses

    @staticmethod
    def _response_succeeded(
        prepared: PreparedRequest,
        response: requests.Response,
    ) -> bool:
        if prepared.endpoint == "/authentication" and prepared.method == "POST":
            return response.status_code == 201
        return 200 <= response.status_code < 400

    def _ensure_authenticated(self, observed_generation: int) -> dict[str, Any]:
        with self._auth_lock:
            if self._auth_generation != observed_generation:
                return {
                    "ok": True,
                    "shared": True,
                    "generation": self._auth_generation,
                    "attempts": [],
                }
            result = self._authenticate_locked()
            if result["ok"]:
                self._auth_generation += 1
            return {
                **result,
                "shared": False,
                "generation": self._auth_generation,
            }

    def _authenticate_locked(self) -> dict[str, Any]:
        try:
            payload = self.login_payload_provider()
        except Exception as exc:
            return {
                "ok": False,
                "reason": "credential_provider_failed",
                "error_type": type(exc).__name__,
                "detail": str(exc),
                "attempts": [],
            }
        email = str(payload.get("email") or "").strip()
        password = str(payload.get("password") or "")
        if not email or not password:
            return {
                "ok": False,
                "reason": "credentials_unavailable",
                "attempts": [],
            }
        json_body = {
            key: value
            for key, value in payload.items()
            if key not in {"email", "password"}
        }
        attempts: list[dict[str, Any]] = []
        for attempt in range(1, self.auto_auth_policy.login_attempts + 1):
            try:
                clear_worldquantbrain_cookies(self.session)
                response = self.session.request(
                    "POST",
                    self.registry.base_url + "/authentication",
                    params={},
                    json=json_body,
                    auth=(email, password),
                    timeout=60,
                    allow_redirects=False,
                )
            except requests.RequestException as exc:
                attempts.append(
                    {
                        "attempt": attempt,
                        "ok": False,
                        "error_type": type(exc).__name__,
                        "detail": str(exc),
                    }
                )
            else:
                succeeded = response.status_code == 201
                attempts.append(
                    {
                        "attempt": attempt,
                        "ok": succeeded,
                        "status_code": response.status_code,
                        "reason": response.reason,
                    }
                )
                if succeeded:
                    cookie_saved = True
                    cookie_error: dict[str, str] | None = None
                    if self.cookie_saver is not None:
                        try:
                            self.cookie_saver(self.session, self.cookie_path)
                        except Exception as exc:
                            cookie_saved = False
                            cookie_error = {
                                "error_type": type(exc).__name__,
                                "detail": str(exc),
                            }
                    return {
                        "ok": True,
                        "reason": "authenticated",
                        "attempts": attempts,
                        "cookie_saved": cookie_saved,
                        "cookie_error": cookie_error,
                    }
            if attempt < self.auto_auth_policy.login_attempts:
                self.sleeper(self.auto_auth_policy.delay_seconds)
        return {
            "ok": False,
            "reason": "login_attempts_exhausted",
            "attempts": attempts,
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
