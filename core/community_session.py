from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from contextlib import closing
from http.cookiejar import Cookie
from pathlib import Path
from typing import Any

import requests


SESSION_MAX_AGE = 6 * 3600
COOKIE_DOMAINS = {"support.worldquantbrain.com", "worldquantbrain.zendesk.com", "worldquantbrain.com", "zendesk.com"}
COOKIE_NAMES = {"_help_center_session", "_zendesk_shared_session", "_zendesk_session",
                "_zendesk_authenticated", "_zendesk_session_id", "_zendesk_cookie", "_zendesk_login_session"}


def profile_key(email: str, config_path: Path, cookies_path: Path) -> str:
    identity = [email.strip().casefold(), str(config_path.resolve()), str(cookies_path.resolve())]
    return hashlib.sha256(json.dumps(identity).encode("utf-8")).hexdigest()


def session_cookies(jar: requests.cookies.RequestsCookieJar) -> list[dict[str, Any]]:
    result = []
    for cookie in jar:
        if cookie.domain.lstrip(".") not in COOKIE_DOMAINS or cookie.is_expired():
            continue
        if cookie.name not in COOKIE_NAMES:
            continue
        result.append({key: getattr(cookie, key) for key in (
            "version", "name", "value", "port", "port_specified", "domain",
            "domain_specified", "domain_initial_dot", "path", "path_specified",
            "secure", "expires", "discard", "comment", "comment_url", "rfc2109",
        )} | {"rest": dict(cookie._rest)})
    return result


def restore_cookies(records: Any) -> requests.cookies.RequestsCookieJar:
    jar = requests.cookies.RequestsCookieJar()
    if not isinstance(records, list):
        raise ValueError("Invalid community cookie cache")
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Invalid community cookie cache entry")
        cookie = Cookie(**record)
        if cookie.domain.lstrip(".") not in COOKIE_DOMAINS:
            raise ValueError("Unexpected community cookie domain")
        if not isinstance(cookie.name, str) or not isinstance(cookie.value, str):
            raise ValueError("Invalid community cookie value")
        if cookie.name not in COOKIE_NAMES:
            continue
        if not cookie.is_expired():
            jar.set_cookie(cookie)
    return jar


class CommunitySessionStore:
    def __init__(self, path: Path, profile: str) -> None:
        self.path = path
        self.profile = profile
        self.revision: str | None = None

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(mode=0o600, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5)
        connection.execute("CREATE TABLE IF NOT EXISTS sessions (profile TEXT PRIMARY KEY, revision TEXT NOT NULL, payload TEXT)")
        connection.commit()
        return connection

    def load(self) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT revision,payload FROM sessions WHERE profile=?", (self.profile,)).fetchone()
        self.revision = row[0] if row else None
        if not row or not row[1]:
            return None
        try:
            payload = json.loads(row[1])
            created = payload["saved_at"]
            if payload["version"] != 1 or not 0 <= time.time() - created < SESSION_MAX_AGE:
                return None
            if not str(payload["user_id"]).isdecimal() or int(payload["user_id"]) <= 0:
                return None
            restore_cookies(payload["cookies"])
            return payload
        except (ValueError, KeyError, TypeError, AttributeError):
            return None

    def save(self, payload: dict[str, Any] | None) -> bool:
        revision = uuid.uuid4().hex
        encoded = json.dumps(payload, ensure_ascii=False) if payload is not None else None
        with closing(self._connect()) as connection, connection:
            if self.revision is None:
                cursor = connection.execute("INSERT OR IGNORE INTO sessions VALUES (?,?,?)",
                                            (self.profile, revision, encoded))
            else:
                cursor = connection.execute("UPDATE sessions SET revision=?,payload=? WHERE profile=? AND revision=?",
                                            (revision, encoded, self.profile, self.revision))
        if cursor.rowcount:
            self.revision = revision
            return True
        return False
