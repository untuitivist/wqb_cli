from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import CandidateSpec, SimulationManifest


SUPPORTED_ENRICHMENT_PROFILES = {"basic"}


def load_manifest(path: str) -> SimulationManifest:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return parse_manifest(payload, source_name=Path(path).stem)


def parse_manifest(payload: Any, *, source_name: str = "simulation-run") -> SimulationManifest:
    if isinstance(payload, list):
        raw_candidates = payload
        run_payload: dict[str, Any] = {}
        metadata: dict[str, Any] = {}
    elif isinstance(payload, dict):
        raw_candidates = payload.get("candidates")
        if raw_candidates is None and _looks_like_candidate(payload):
            raw_candidates = [payload]
        if not isinstance(raw_candidates, list):
            raise ValueError("Manifest must contain a candidates array")
        if "run" in payload and not isinstance(payload["run"], dict):
            raise ValueError("Manifest run must be an object")
        if "metadata" in payload and not isinstance(payload["metadata"], dict):
            raise ValueError("Manifest metadata must be an object")
        run_payload = payload.get("run") if isinstance(payload.get("run"), dict) else {}
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    else:
        raise ValueError("Manifest root must be an object or array")

    name = str(run_payload.get("name") or source_name)
    profile = str(run_payload.get("enrichment_profile") or "basic").lower()
    if profile not in SUPPORTED_ENRICHMENT_PROFILES:
        supported = ", ".join(sorted(SUPPORTED_ENRICHMENT_PROFILES))
        raise ValueError(f"Unsupported enrichment profile {profile!r}; expected one of: {supported}")

    candidates = tuple(_parse_candidate(item, index) for index, item in enumerate(raw_candidates))
    if not candidates:
        raise ValueError("Manifest must contain at least one candidate")
    requested_run_id = run_payload.get("id")
    return SimulationManifest(
        name=name,
        enrichment_profile=profile,
        candidates=candidates,
        metadata=dict(metadata),
        requested_run_id=str(requested_run_id) if requested_run_id else None,
    )


def _parse_candidate(raw: Any, index: int) -> CandidateSpec:
    if not isinstance(raw, dict):
        raise ValueError(f"Candidate {index} must be an object")
    payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else raw
    simulation_type = str(payload.get("type") or "REGULAR").upper()
    settings = payload.get("settings")
    if not isinstance(settings, dict):
        raise ValueError(f"Candidate {index} must contain settings")
    settings = dict(settings)
    language = raw.get("language") or payload.get("language")
    if language and not settings.get("language"):
        settings["language"] = str(language).upper()
    settings.setdefault("language", "FASTEXPR")

    normalized: dict[str, Any] = {"type": simulation_type, "settings": settings}
    if simulation_type == "REGULAR":
        expression = payload.get("regular", raw.get("expression"))
        if isinstance(expression, dict):
            expression = expression.get("code")
        if not isinstance(expression, str) or not expression.strip():
            raise ValueError(f"Candidate {index} REGULAR payload must contain regular or expression")
        normalized["regular"] = expression
    elif simulation_type == "SUPER":
        combo = payload.get("combo")
        selection = payload.get("selection")
        if not isinstance(combo, str) or not isinstance(selection, str):
            raise ValueError(f"Candidate {index} SUPER payload must contain combo and selection")
        normalized["combo"] = combo
        normalized["selection"] = selection
    else:
        raise ValueError(f"Candidate {index} has unsupported type: {simulation_type}")

    if "metadata" in raw and not isinstance(raw["metadata"], dict):
        raise ValueError(f"Candidate {index} metadata must be an object")
    metadata = dict(raw.get("metadata") or {})
    excluded = {
        "payload",
        "type",
        "settings",
        "regular",
        "expression",
        "combo",
        "selection",
        "language",
        "priority",
        "metadata",
    }
    metadata.update({key: value for key, value in raw.items() if key not in excluded})
    try:
        priority = int(raw.get("priority") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Candidate {index} priority must be an integer") from exc
    return CandidateSpec(
        payload=normalized,
        metadata=metadata,
        priority=priority,
    )


def _looks_like_candidate(payload: dict[str, Any]) -> bool:
    return "settings" in payload and any(
        key in payload for key in ("regular", "expression", "combo", "selection")
    )
