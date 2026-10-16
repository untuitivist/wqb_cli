from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping, Sequence

from .models import EVIDENCE_SCHEMA_VERSION, EvidenceRecord


def canonical_json(value: Any) -> str:
    """Serialize JSON data deterministically for hashing and replay."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _record_integrity_payload(record: EvidenceRecord) -> dict[str, Any]:
    payload = record.to_dict()
    payload.pop("evidence_id", None)
    return payload


def build_evidence_record(
    *,
    provider: str,
    query_type: str,
    request: Any,
    raw_response: Any,
    normalized_response: Any = None,
    retrieved_at: str | None = None,
    entity_ids: Mapping[str, str] | None = None,
    as_of: str | None = None,
    period: Mapping[str, str] | None = None,
    units: Mapping[str, str] | None = None,
    provider_sources: Sequence[str] = (),
    update_dates: Sequence[str] = (),
    warnings: Sequence[Any] = (),
    completeness: str | None = None,
    provider_contract_version: str | None = None,
    supports: Sequence[str] = (),
    limitations: Sequence[str] = (),
) -> EvidenceRecord:
    provider = provider.strip()
    query_type = query_type.strip()
    if not provider:
        raise ValueError("provider must be non-empty")
    if not query_type:
        raise ValueError("query_type must be non-empty")

    resolved_retrieved_at = retrieved_at or utc_now_iso()
    request_json = canonical_json(request)
    raw_response_json = canonical_json(raw_response)
    raw_sha256 = hashlib.sha256(raw_response_json.encode("utf-8")).hexdigest()
    normalized_json = (
        canonical_json(normalized_response) if normalized_response is not None else None
    )
    provisional = EvidenceRecord(
        schema_version=EVIDENCE_SCHEMA_VERSION,
        evidence_id="",
        provider=provider,
        query_type=query_type,
        request_json=request_json,
        retrieved_at=resolved_retrieved_at,
        raw_sha256=raw_sha256,
        raw_response_json=raw_response_json,
        normalized_response_json=normalized_json,
        entity_ids=tuple(sorted((str(k), str(v)) for k, v in (entity_ids or {}).items())),
        as_of=as_of,
        period=tuple(sorted((str(k), str(v)) for k, v in (period or {}).items())),
        units=tuple(sorted((str(k), str(v)) for k, v in (units or {}).items())),
        provider_sources=tuple(sorted({str(item) for item in provider_sources if str(item)})),
        update_dates=tuple(sorted({str(item) for item in update_dates if str(item)})),
        warnings_json=tuple(canonical_json(item) for item in warnings),
        completeness=completeness,
        provider_contract_version=provider_contract_version,
        supports=tuple(str(item) for item in supports),
        limitations=tuple(str(item) for item in limitations),
    )
    evidence_id = hashlib.sha256(
        canonical_json(_record_integrity_payload(provisional)).encode("utf-8")
    ).hexdigest()[:24]
    return EvidenceRecord(
        **{**provisional.__dict__, "evidence_id": evidence_id}
    )


def verify_evidence_record(record: EvidenceRecord) -> tuple[bool, tuple[str, ...]]:
    problems: list[str] = []
    if record.schema_version != EVIDENCE_SCHEMA_VERSION:
        problems.append(
            f"unsupported_schema:{record.schema_version};expected:{EVIDENCE_SCHEMA_VERSION}"
        )

    actual_raw_sha = hashlib.sha256(record.raw_response_json.encode("utf-8")).hexdigest()
    if actual_raw_sha != record.raw_sha256:
        problems.append("raw_sha256_mismatch")

    expected_id = hashlib.sha256(
        canonical_json(_record_integrity_payload(record)).encode("utf-8")
    ).hexdigest()[:24]
    if expected_id != record.evidence_id:
        problems.append("evidence_id_mismatch")

    return (not problems, tuple(problems))
