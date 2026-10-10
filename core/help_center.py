from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlsplit

import requests

from .community_client import CommunityClient, CommunityError, SUPPORT_LOCALE, community_resource, next_page_url
from .paths import RESOURCES_ROOT
from .registry import EndpointRegistry


HELP_CENTER_REGISTRY = RESOURCES_ROOT / "help_center_api" / "api_inventory.json"


def load_help_center_registry() -> EndpointRegistry:
    return EndpointRegistry.load(str(HELP_CENTER_REGISTRY))


def help_center_locale(value: str | None) -> str:
    locale = (value or "en-us").lower()
    if SUPPORT_LOCALE.fullmatch(locale) is None:
        raise ValueError("Use a valid Help Center locale, for example en-us or zh-cn")
    return locale


def article_reference(reference: str, locale: str | None = None) -> dict[str, str]:
    if re.fullmatch(r"[0-9]+", reference) is not None and int(reference) > 0:
        return {"article_id": reference, "locale": help_center_locale(locale)}
    parsed = urlsplit(reference)
    match = re.fullmatch(r"/hc/([a-z]{2,3}(?:-[a-z0-9]{2,8})*)/articles/([0-9]+)(?:-[^/]+)?/?", parsed.path)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "support.worldquantbrain.com"
        or parsed.port not in (None, 443)
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or match is None
        or int(match.group(2)) <= 0
    ):
        raise ValueError("Use a positive article ID or an HTTPS support.worldquantbrain.com/hc/<locale>/articles/<id> URL")
    return {"article_id": match.group(2), "locale": help_center_locale(locale or match.group(1))}


def collect_help_center_pages(
    client: CommunityClient, prepared: dict[str, Any], *, collection: str, max_pages: int
) -> dict[str, Any]:
    if max_pages < 1:
        raise ValueError("max-pages must be positive")
    address = prepared["url"]
    resource = community_resource(address)
    params = prepared["params"]
    initial_url = requests.Request("GET", address, params=params).prepare().url
    fixed_query = {
        key: values for key, values in parse_qs(urlsplit(initial_url).query, keep_blank_values=True).items()
        if key not in {"page", "per_page"} and not key.startswith("page[")
    }
    seen: set[str] = set()
    pages: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    reason = "max_pages"
    while address and len(pages) < max_pages:
        page_url = requests.Request("GET", address, params=params).prepare().url
        if page_url in seen:
            raise CommunityError("Help Center pagination repeated a page", stage="help_center_pagination")
        seen.add(page_url)
        result = client.call("GET", address, params=params)
        pages.append(result)
        if not result["ok"]:
            reason = "request_failed"
            break
        body = result["response"]["body"]
        if not isinstance(body, dict) or not isinstance(body.get(collection), list):
            raise CommunityError(f"Help Center response is missing its {collection} array", stage="help_center_pagination")
        items.extend(body[collection])
        address = next_page_url(body)
        if address and community_resource(address) != resource:
            raise CommunityError("Help Center next page changed resource", stage="help_center_pagination")
        if address:
            next_query = parse_qs(urlsplit(address).query, keep_blank_values=True)
            if any(next_query.get(key) != values for key, values in fixed_query.items()):
                raise CommunityError("Help Center next page changed query filters or locale", stage="help_center_pagination")
        params = None
        if not address:
            reason = "complete"
    return {
        "ok": reason == "complete",
        "request": prepared,
        "collection": collection,
        "items": items,
        "count": len(items),
        "pages": pages,
        "complete": reason == "complete",
        "stop_reason": reason,
        "next_page": address,
    }
