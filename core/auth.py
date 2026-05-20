from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

from .config_store import load_config
from .io import read_dotenv
from .paths import DEFAULT_COOKIE_PATH, LEGACY_COOKIE_PATH
from .secrets import get_secret


def load_cookie_payload(cookie_path: str | None = None) -> dict[str, Any]:
    path = Path(cookie_path) if cookie_path else DEFAULT_COOKIE_PATH
    if not path.exists() and cookie_path is None and LEGACY_COOKIE_PATH.exists():
        path = LEGACY_COOKIE_PATH
    if not path.exists():
        return {"cookies": {}}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_cookie_payload(session: requests.Session, cookie_path: str | None = None) -> None:
    path = Path(cookie_path) if cookie_path else DEFAULT_COOKIE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    cookies = {
        cookie.name: cookie.value
        for cookie in session.cookies
        if cookie.value and "worldquantbrain.com" in (cookie.domain or "")
    }
    path.write_text(json.dumps({"cookies": cookies}, indent=2, sort_keys=True), encoding="utf-8")


def session_from_cookies(cookie_path: str | None = None) -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "wqb-cli/0.1"})
    payload = load_cookie_payload(cookie_path)
    for key, value in (payload.get("cookies") or {}).items():
        if not value:
            continue
        session.cookies.set(key, value, domain=".worldquantbrain.com")
        session.cookies.set(key, value, domain="api.worldquantbrain.com")
    return session


def resolve_login_payload(
    *,
    input_payload: dict[str, Any] | None = None,
    email: str | None = None,
    password: str | None = None,
    expiry: int | None = None,
    config_path: str | None = None,
) -> dict[str, Any]:
    payload = dict(input_payload or {})
    config = load_config(config_path)
    env = read_dotenv()

    resolved_email = (
        email
        or payload.get("email")
        or env.get("EMAIL")
        or env.get("WQB_EMAIL")
        or config.get("auth", {}).get("email")
    )
    keyring_username = config.get("auth", {}).get("keyring_username") or resolved_email
    keyring_service = config.get("auth", {}).get("keyring_service") or "wqb-cli"
    keyring_password = get_secret(str(keyring_service), str(keyring_username)) if keyring_username else None
    resolved_password = password or payload.get("password") or keyring_password
    if not resolved_password:
        resolved_password = env.get("PASSWORD") or env.get("WQB_PASSWORD")

    result = {key: value for key, value in payload.items() if key not in {"email", "password"}}
    result["email"] = str(resolved_email or "")
    result["password"] = str(resolved_password or "")
    result["expiry"] = int(expiry or payload.get("expiry") or 3600)
    return result
