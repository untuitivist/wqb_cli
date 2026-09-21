from __future__ import annotations

from typing import Any


def is_region_agnostic(payload: Any) -> bool:
    return isinstance(payload, dict) and (
        str(payload.get("type", "")).upper() == "REGION_AGNOSTIC"
        or (isinstance(payload.get("settings"), dict) and payload["settings"].get("region") == "ALL")
    )


def validate_region_agnostic_payload(payload: Any) -> None:
    if isinstance(payload, list):
        if any(is_region_agnostic(item) for item in payload):
            raise ValueError("BRAIN does not support REGION_AGNOSTIC/ALL in batch requests; send one object")
        return
    if not is_region_agnostic(payload):
        return
    settings = payload.get("settings")
    if payload.get("type") != "REGION_AGNOSTIC" or not isinstance(settings, dict):
        raise ValueError("Region ALL requires type REGION_AGNOSTIC and settings")
    if settings.get("region") != "ALL" or settings.get("delay") != 1:
        raise ValueError("REGION_AGNOSTIC requires region ALL and delay 1")
    if settings.get("universe") not in {"LARGE", "MEDIUM", "SMALL"}:
        raise ValueError("ALL universe must be LARGE, MEDIUM or SMALL")
    expression = payload.get("regular")
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("REGION_AGNOSTIC requires a nonempty regular expression")


def region_agnostic_child_ids(detail: dict[str, Any], alpha_id: str | None) -> list[str]:
    children = detail.get("children")
    if (
        detail.get("id") != alpha_id or detail.get("type") != "RA_PARENT"
        or not isinstance(children, list) or len(children) < 2
        or any(not isinstance(child, str) or not child or child == alpha_id for child in children)
    ):
        raise ValueError("RA_PARENT must identify at least two distinct child Alphas")
    if len(set(children)) != len(children):
        raise ValueError("RA_PARENT contains duplicate child Alpha IDs")
    return children
