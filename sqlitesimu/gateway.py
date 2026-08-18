from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, Protocol

import requests

from ..core.auth import resolve_login_payload, save_cookie_payload
from ..sdk import PluginContext


SQLITESIMU_REAUTH_STATUSES = frozenset({204, 401, 429})
SQLITESIMU_REAUTH_ATTEMPTS = 5
SQLITESIMU_REAUTH_DELAY_SECONDS = 2.0


class ApiTransportError(RuntimeError):
    """The server outcome could not be observed because transport failed."""


class ApiGateway(Protocol):
    def call(
        self,
        method: str,
        path: str,
        *,
        path_vars: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> dict[str, Any]: ...


class WqbApiGateway:
    """Registry-backed adapter with an extra five-round authentication guard."""

    def __init__(
        self,
        context: PluginContext,
        *,
        reauth_attempts: int = SQLITESIMU_REAUTH_ATTEMPTS,
        reauth_delay_seconds: float = SQLITESIMU_REAUTH_DELAY_SECONDS,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if reauth_attempts < 1:
            raise ValueError("reauth_attempts must be at least 1")
        if reauth_delay_seconds < 0:
            raise ValueError("reauth_delay_seconds must not be negative")
        self.context = context
        self.registry = context.load_registry()
        self.client = context.new_client(self.registry)
        self.reauth_attempts = reauth_attempts
        self.reauth_delay_seconds = reauth_delay_seconds
        self.sleeper = sleeper

    def call(
        self,
        method: str,
        path: str,
        *,
        path_vars: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> dict[str, Any]:
        result = self._call_once(
            method,
            path,
            path_vars=path_vars,
            params=params,
            json_body=json_body,
        )
        if not self._should_reauthenticate(path, result):
            return result
        trigger_status = _status_code(result)
        attempts: list[dict[str, Any]] = []
        for attempt in range(1, self.reauth_attempts + 1):
            if self.reauth_delay_seconds:
                self.sleeper(self.reauth_delay_seconds)
            try:
                authentication = self._reauthenticate()
            except ApiTransportError as exc:
                attempts.append(
                    {
                        "attempt": attempt,
                        "ok": False,
                        "error_type": type(exc).__name__,
                        "detail": str(exc),
                    }
                )
                continue
            authentication = {"attempt": attempt, **authentication}
            attempts.append(authentication)
            if not authentication["ok"]:
                continue
            result = self._call_once(
                method,
                path,
                path_vars=path_vars,
                params=params,
                json_body=json_body,
                auto_auth=False,
            )
            authentication["replay_status"] = _status_code(result)
            if not self._should_reauthenticate(path, result):
                result["reauthentication"] = {
                    "layer": "sqlitesimu",
                    "ok": True,
                    "exhausted": False,
                    "trigger_status": trigger_status,
                    "attempts": attempts,
                }
                return result
        result["ok"] = False
        result["reauthentication"] = {
            "layer": "sqlitesimu",
            "ok": False,
            "exhausted": True,
            "trigger_status": trigger_status,
            "attempts": attempts,
        }
        return result

    def _call_once(
        self,
        method: str,
        path: str,
        *,
        path_vars: dict[str, str] | None,
        params: dict[str, Any] | None,
        json_body: Any,
        auto_auth: bool = True,
    ) -> dict[str, Any]:
        endpoint = self.registry.get(path)
        prepared = self.client.prepare(
            endpoint,
            method,
            path_vars=path_vars,
            params=params,
            json_body=json_body,
        )
        try:
            return self.client.call_once(prepared, auto_auth=auto_auth)
        except requests.RequestException as exc:
            raise ApiTransportError(f"{method.upper()} {path}: {exc}") from exc

    def _reauthenticate(self) -> dict[str, Any]:
        try:
            payload = resolve_login_payload(expiry=3600)
        except Exception as exc:
            return {
                "ok": False,
                "reason": "credential_provider_failed",
                "status_code": None,
                "error_type": type(exc).__name__,
                "detail": str(exc),
            }
        if not payload.get("email") or not payload.get("password"):
            return {
                "ok": False,
                "reason": "credentials_unavailable",
                "status_code": None,
            }
        result = self._call_once(
            "POST",
            "/authentication",
            path_vars=None,
            params=None,
            json_body=payload,
            auto_auth=False,
        )
        if not result.get("ok"):
            return {
                "ok": False,
                "reason": "authentication_rejected",
                "status_code": _status_code(result),
            }
        try:
            save_cookie_payload(self.client.session, self.context.cookies_path)
        except Exception as exc:
            return {
                "ok": True,
                "reason": "authenticated",
                "status_code": _status_code(result),
                "cookie_saved": False,
                "cookie_error": {
                    "error_type": type(exc).__name__,
                    "detail": str(exc),
                },
            }
        return {
            "ok": True,
            "reason": "authenticated",
            "status_code": _status_code(result),
            "cookie_saved": True,
        }

    @staticmethod
    def _should_reauthenticate(
        path: str,
        result: dict[str, Any],
    ) -> bool:
        if path == "/authentication":
            return False
        return _status_code(result) in SQLITESIMU_REAUTH_STATUSES


def _status_code(result: dict[str, Any]) -> int | None:
    value = (result.get("response") or {}).get("status_code")
    return int(value) if isinstance(value, int) else None


__all__ = [
    "ApiGateway",
    "ApiTransportError",
    "SQLITESIMU_REAUTH_ATTEMPTS",
    "SQLITESIMU_REAUTH_STATUSES",
    "WqbApiGateway",
]
