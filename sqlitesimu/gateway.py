from __future__ import annotations

from typing import Any, Protocol

import requests

from ..core.auth import resolve_login_payload, save_cookie_payload
from ..sdk import PluginContext


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
    """Registry-backed API adapter with one transparent reauthentication attempt."""

    def __init__(self, context: PluginContext) -> None:
        self.context = context
        self.registry = context.load_registry()
        self.client = context.new_client(self.registry)

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
        if _status_code(result) != 401 or path == "/authentication":
            return result
        try:
            reauthenticated = self._reauthenticate()
        except ApiTransportError as exc:
            result["reauthentication"] = {
                "ok": False,
                "error_type": type(exc).__name__,
                "detail": str(exc),
            }
            return result
        if not reauthenticated:
            return result
        return self._call_once(
            method,
            path,
            path_vars=path_vars,
            params=params,
            json_body=json_body,
        )

    def _call_once(
        self,
        method: str,
        path: str,
        *,
        path_vars: dict[str, str] | None,
        params: dict[str, Any] | None,
        json_body: Any,
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
            return self.client.call_once(prepared)
        except requests.RequestException as exc:
            raise ApiTransportError(f"{method.upper()} {path}: {exc}") from exc

    def _reauthenticate(self) -> bool:
        payload = resolve_login_payload(expiry=3600)
        if not payload.get("email") or not payload.get("password"):
            return False
        result = self._call_once(
            "POST",
            "/authentication",
            path_vars=None,
            params=None,
            json_body=payload,
        )
        if not result.get("ok"):
            return False
        save_cookie_payload(self.client.session, self.context.cookies_path)
        return True


def _status_code(result: dict[str, Any]) -> int | None:
    value = (result.get("response") or {}).get("status_code")
    return int(value) if isinstance(value, int) else None


__all__ = ["ApiGateway", "ApiTransportError", "WqbApiGateway"]
