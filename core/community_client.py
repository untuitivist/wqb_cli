from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable
from urllib.parse import urljoin, urlsplit

import requests

from .auth import resolve_login_payload, session_from_cookies
from .client import MUTATING_METHODS, WqbClient
from .paths import RESOURCES_ROOT
from .registry import EndpointRegistry


SUPPORT_ORIGIN = "https://support.worldquantbrain.com"
SSO_HOSTS = {"api.worldquantbrain.com", "support.worldquantbrain.com", "worldquantbrain.zendesk.com"}
COMMUNITY_REGISTRY = RESOURCES_ROOT / "community_api" / "api_inventory.json"


class CommunityError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def load_community_registry() -> EndpointRegistry:
    return EndpointRegistry.load(str(COMMUNITY_REGISTRY))


def community_url(path: str) -> str:
    address = urljoin(SUPPORT_ORIGIN, path)
    parsed = urlsplit(address)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "support.worldquantbrain.com"
        or parsed.port not in (None, 443)
        or parsed.username
        or parsed.password
        or parsed.fragment
        or ".." in parsed.path.split("/")
        or not (
            parsed.path.startswith("/api/v2/community/")
            or parsed.path.startswith("/api/v2/help_center/community/")
            or parsed.path == "/api/v2/help_center/community_posts/search.json"
            or parsed.path == "/api/v2/help_center/sessions.json"
            or parsed.path in {"/api/v2/guide/user_images/uploads", "/api/v2/guide/user_images"}
        )
    ):
        raise ValueError("Community requests must target the registered HTTPS forum API origin")
    return address


def community_resource(address: str) -> str:
    return urlsplit(community_url(address)).path.removesuffix(".json").replace("/api/v2/help_center/community/", "/api/v2/community/")


def browser_write_context(html: str) -> dict[str, str]:
    for match in re.finditer(r"HelpCenter\.internal\s*=\s*", html):
        try:
            payload = json.JSONDecoder().raw_decode(html[match.end():])[0]
        except ValueError:
            continue
        if not isinstance(payload, dict):
            continue
        session = payload.get("current_session") or {}
        token = session.get("shared_csrf_token")
        brand = str(payload.get("current_brand_id") or "")
        if isinstance(token, str) and token and brand.isdecimal():
            return {"csrf_token": token, "brand_id": brand}
    return {}


def next_page_url(body: dict[str, Any]) -> str | None:
    meta = body.get("meta") or {}
    if meta.get("has_more") is False:
        return None
    candidate = (body.get("links") or {}).get("next") or body.get("next_page")
    if meta.get("has_more") is True and not candidate:
        raise CommunityError("Forum pagination has_more is true but the next link is missing")
    return community_url(str(candidate)) if candidate else None


class CommunityClient:
    def __init__(
        self,
        *,
        cookies_path: str | None = None,
        config_path: str | None = None,
        brain_registry: EndpointRegistry | None = None,
        brain_client: WqbClient | None = None,
        session: requests.Session | None = None,
        timeout: float = 60,
        max_retries: int = 4,
        max_wait_seconds: float = 300,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if timeout <= 0 or max_retries < 0 or max_wait_seconds < 0:
            raise ValueError("Invalid community timeout, retry count or wait budget")
        self.brain = brain_client or WqbClient(
            brain_registry or EndpointRegistry.load(), session_from_cookies(cookies_path),
            login_payload_provider=lambda: resolve_login_payload(config_path=config_path),
        )
        self.session = session or requests.Session()
        if session is None:
            self.session.trust_env = self.brain.session.trust_env
            self.session.headers.update({"User-Agent": self.brain.session.headers.get("User-Agent", "wqb-cli/community")})
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_wait_seconds = max_wait_seconds
        self.sleeper = sleeper
        self.authenticated = False
        self.csrf_token: str | None = None
        self.brand_id: str | None = None

    def authenticate(self) -> None:
        self.csrf_token = None
        self.brand_id = None
        endpoint = self.brain.registry.get("/authentication/support")
        result = self.brain.call_once(self.brain.prepare(endpoint, "GET", params={"return_to": SUPPORT_ORIGIN + "/hc/en-us"}))
        response = result.get("response") or {}
        location = response.get("location")
        if location and urlsplit(location).hostname == "platform.worldquantbrain.com":
            try:
                payload = self.brain.login_payload_provider()
            except Exception as error:
                raise CommunityError(f"BRAIN session renewal credentials are unavailable: {type(error).__name__}") from None
            if not isinstance(payload, dict) or not payload.get("email") or not payload.get("password"):
                raise CommunityError("BRAIN login credentials are unavailable; configure auth or supply --config")
            login = self.brain.prepare(self.brain.registry.get("/authentication"), "POST", json_body=payload)
            renewal = self.brain.call_once(login, auto_auth=False)
            if not renewal.get("ok"):
                raise CommunityError("BRAIN session renewal failed before forum SSO")
            if self.brain.cookie_saver is not None:
                self.brain.cookie_saver(self.brain.session, self.brain.cookie_path)
            result = self.brain.call_once(self.brain.prepare(endpoint, "GET", params={"return_to": SUPPORT_ORIGIN + "/hc/en-us"}))
            response = result.get("response") or {}
            location = response.get("location")
        if not result.get("ok") or not location:
            raise CommunityError(f"BRAIN support SSO failed (HTTP {response.get('status_code')})")
        self.session.cookies.update(self.brain.session.cookies)
        for redirect_index in range(10):
            parsed = urlsplit(location)
            if parsed.scheme != "https" or parsed.hostname not in SSO_HOSTS or parsed.port not in (None, 443) or parsed.username or parsed.password:
                raise CommunityError(f"BRAIN support SSO returned an unexpected redirect origin: {parsed.scheme}://{parsed.hostname}")
            try:
                reply = self.session.get(location, timeout=self.timeout, allow_redirects=False, headers={"Accept": "text/html,application/xhtml+xml"})
                if reply.status_code == 403 and parsed.path.startswith("/hc/"):
                    reply = self.session.get(location, timeout=self.timeout, allow_redirects=False, headers={"Accept": "text/html,application/xhtml+xml"})
            except requests.RequestException as error:
                raise CommunityError(f"Support SSO transport failed: {type(error).__name__}") from None
            if reply.status_code in (301, 302, 303, 307, 308):
                target = reply.headers.get("Location")
                if not target:
                    raise CommunityError("Support SSO redirect is missing Location")
                location = urljoin(location, target)
                continue
            if reply.status_code != 200:
                raise CommunityError(f"Support SSO failed at {parsed.hostname} (HTTP {reply.status_code}); normal browser login may be required")
            self.authenticated = True
            context = browser_write_context(reply.text)
            self.csrf_token = context.get("csrf_token")
            self.brand_id = context.get("brand_id")
            return
        raise CommunityError("Support SSO exceeded its redirect limit")

    def write_context(self) -> dict[str, str]:
        if not self.authenticated:
            self.authenticate()
        if not self.csrf_token or not self.brand_id:
            try:
                reply = self.session.get(SUPPORT_ORIGIN + "/hc/zh-cn/community/posts/new", timeout=self.timeout,
                                         allow_redirects=False, headers={"Accept": "text/html,application/xhtml+xml"})
            except requests.RequestException as error:
                raise CommunityError("Forum write context read failed: " + type(error).__name__) from None
            if reply.status_code != 200:
                raise CommunityError(f"Forum write context failed (HTTP {reply.status_code})", status_code=reply.status_code)
            context = browser_write_context(reply.text)
            self.csrf_token = context.get("csrf_token")
            self.brand_id = context.get("brand_id")
        if not self.csrf_token or not self.brand_id:
            raise CommunityError("Forum page did not provide the shared CSRF token and brand required for writes")
        return {"csrf_token": self.csrf_token, "brand_id": self.brand_id}

    def post_page(self, address: str, post_id: str) -> requests.Response:
        parsed = urlsplit(address)
        expected = r"/hc/[a-z-]+/community/posts/" + re.escape(str(post_id)) + r"(?:-[^/]*)?"
        if (parsed.scheme != "https" or parsed.hostname != "support.worldquantbrain.com"
                or parsed.port not in (None, 443) or parsed.username or parsed.password or parsed.query or parsed.fragment
                or re.fullmatch(expected, parsed.path) is None):
            raise ValueError("Post verification must read the saved post on the forum origin")
        if not self.authenticated:
            self.authenticate()
        try:
            return self.session.get(address, timeout=self.timeout, allow_redirects=False, headers={"Accept": "text/html"})
        except requests.RequestException as error:
            raise CommunityError("Post page verification failed: " + type(error).__name__) from None

    def _delay(self, reply: requests.Response | None, attempt: int) -> float:
        header = reply.headers.get("Retry-After") if reply is not None else None
        if header:
            try:
                return max(0.0, float(header))
            except ValueError:
                try:
                    deadline = parsedate_to_datetime(header)
                    return max(0.0, (deadline - datetime.now(timezone.utc)).total_seconds())
                except (TypeError, ValueError):
                    pass
        return min(30.0, float(2 ** attempt))

    def call(self, method: str, path: str, *, params: dict[str, Any] | None = None, json_body: Any = None) -> dict[str, Any]:
        method = method.upper()
        address = community_url(path)
        if method not in {"GET", "POST", "PUT", "DELETE"}:
            raise ValueError("Unsupported community HTTP method")
        mutating = method in MUTATING_METHODS
        if not self.authenticated:
            self.authenticate()
        headers = {"Accept": "application/json"}
        if mutating:
            if self.csrf_token is None:
                self.write_context()
            headers.update({"X-CSRF-Token": self.csrf_token, "Origin": SUPPORT_ORIGIN, "Referer": SUPPORT_ORIGIN + "/hc/zh-cn/community"})
        waited = 0.0
        retries = 0
        refreshed = False
        while True:
            try:
                reply = self.session.request(method, address, params=params, json=json_body, headers=headers, timeout=self.timeout, allow_redirects=False)
            except requests.RequestException as error:
                if mutating:
                    raise CommunityError(f"Community write outcome is unknown ({type(error).__name__}); inspect the target before retrying") from None
                delay = self._delay(None, retries)
                if retries >= self.max_retries or waited + delay > self.max_wait_seconds:
                    raise CommunityError(f"Community read transport failed: {type(error).__name__}") from None
                self.sleeper(delay)
                waited += delay
                retries += 1
                continue
            if not mutating and reply.status_code in (401, 403, 302) and not refreshed:
                self.authenticate()
                refreshed = True
                continue
            if not mutating and reply.status_code in (429, 500, 502, 503, 504):
                delay = self._delay(reply, retries)
                if retries < self.max_retries and waited + delay <= self.max_wait_seconds:
                    self.sleeper(delay)
                    waited += delay
                    retries += 1
                    continue
            break
        try:
            body = reply.json() if reply.content else None
        except ValueError:
            body = {"error": "non_json_response", "content_type": reply.headers.get("Content-Type", "").split(";")[0]}
        ok = 200 <= reply.status_code < 300 and (body is None or not isinstance(body, dict) or body.get("error") != "non_json_response")
        return {
            "ok": ok,
            "request": {"method": method, "url": address, "params": params or {}, "mutating": mutating},
            "response": {"status_code": reply.status_code, "body": body, "retry_after": reply.headers.get("Retry-After"), "retries": retries, "wait_seconds": waited},
        }

    def get_json(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        result = self.call("GET", path, params=params)
        response = result["response"]
        if not result["ok"] or not isinstance(response["body"], dict):
            raise CommunityError(f"Community read failed (HTTP {response['status_code']})", status_code=response["status_code"])
        return response["body"]

    def comments(self, post_id: str) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
        address = community_url(f"/api/v2/community/posts/{post_id}/comments.json")
        params: dict[str, Any] | None = {"page[size]": 100, "include": "users"}
        seen_pages: set[str] = set()
        comments: dict[str, dict[str, Any]] = {}
        users: dict[str, dict[str, Any]] = {}
        while address:
            if address in seen_pages:
                raise CommunityError("Forum comment pagination repeated a page")
            seen_pages.add(address)
            body = self.get_json(address, params=params)
            if not isinstance(body.get("comments"), list):
                raise CommunityError("Forum comments response is missing its comments array")
            for comment in body["comments"]:
                if str(comment.get("post_id")) != str(post_id):
                    raise CommunityError("Forum comment belongs to an unexpected post")
                comments[str(comment["id"])] = comment
            users.update({str(user["id"]): user for user in body.get("users", [])})
            address = next_page_url(body)
            if address and community_resource(address) != f"/api/v2/community/posts/{post_id}/comments":
                raise CommunityError("Forum comments next page changed resource")
            params = None
        return list(comments.values()), users


def prepare_community_request(
    registry: EndpointRegistry, method: str, path: str, *, path_vars: dict[str, Any] | None = None, params: dict[str, Any] | None = None, json_body: Any = None
) -> dict[str, Any]:
    endpoint = registry.get(path)
    method = method.upper()
    if method not in endpoint.methods:
        raise ValueError(f"{method} is not registered for {path}")
    resolved = path
    for name in endpoint.variables:
        value = str((path_vars or {}).get(name, ""))
        if not value or not (value.isdecimal() or name == "user_id" and value == "me"):
            raise ValueError(f"A valid {name} is required")
        resolved = resolved.replace("{" + name + "}", value)
    return {"method": method, "url": community_url(resolved), "params": params or {}, "json": json_body, "mutating": method in MUTATING_METHODS}
