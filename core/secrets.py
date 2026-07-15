from __future__ import annotations

from typing import Any


def keyring_available() -> bool:
    try:
        import keyring  # noqa: F401
    except Exception:
        return False
    return True


def set_secret(service: str, username: str, password: str) -> dict[str, Any]:
    try:
        import keyring

        keyring.set_password(service, username, password)
    except Exception as exc:
        return {"ok": False, "backend": "keyring", "error_type": type(exc).__name__, "detail": str(exc)}
    return {"ok": True, "backend": "keyring", "service": service, "username": username}


def get_secret(service: str, username: str) -> str | None:
    try:
        import keyring

        return keyring.get_password(service, username)
    except Exception:
        return None


def get_named_secret(secret_name: str, service: str = "wqb-cli") -> str | None:
    if type(secret_name) is not str:
        raise TypeError("secret_name must be a string")
    if not secret_name.strip():
        raise ValueError("secret_name must be nonblank")
    if type(service) is not str:
        raise TypeError("service must be a string")
    if not service.strip():
        raise ValueError("service must be nonblank")
    return get_secret(service, secret_name)
