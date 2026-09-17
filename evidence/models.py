from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping


EVIDENCE_SCHEMA_VERSION = "1.0"


def _loads(value: str | None) -> Any:
    if value is None:
        return None
    return json.loads(value)


@dataclass(frozen=True)
class EvidenceRecord:
    """Immutable, replay-oriented external evidence envelope.

    Mutable request/response objects are stored as canonical JSON strings so the
    dataclass remains stable after construction. ``to_dict`` exposes ordinary
    JSON objects for workflow artifacts.
    """

    schema_version: str
    evidence_id: str
    provider: str
    query_type: str
    request_json: str
    retrieved_at: str
    raw_sha256: str
    raw_response_json: str
    normalized_response_json: str | None = None
    entity_ids: tuple[tuple[str, str], ...] = ()
    as_of: str | None = None
    period: tuple[tuple[str, str], ...] = ()
    units: tuple[tuple[str, str], ...] = ()
    provider_sources: tuple[str, ...] = ()
    update_dates: tuple[str, ...] = ()
    warnings_json: tuple[str, ...] = ()
    completeness: str | None = None
    provider_contract_version: str | None = None
    supports: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    @property
    def request(self) -> Any:
        return _loads(self.request_json)

    @property
    def raw_response(self) -> Any:
        return _loads(self.raw_response_json)

    @property
    def normalized_response(self) -> Any:
        return _loads(self.normalized_response_json)

    @property
    def warnings(self) -> list[Any]:
        return [_loads(item) for item in self.warnings_json]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "evidence_id": self.evidence_id,
            "provider": self.provider,
            "query_type": self.query_type,
            "request": self.request,
            "retrieved_at": self.retrieved_at,
            "raw_sha256": self.raw_sha256,
            "raw_response": self.raw_response,
            "normalized_response": self.normalized_response,
            "entity_ids": dict(self.entity_ids),
            "as_of": self.as_of,
            "period": dict(self.period),
            "units": dict(self.units),
            "provider_sources": list(self.provider_sources),
            "update_dates": list(self.update_dates),
            "warnings": self.warnings,
            "completeness": self.completeness,
            "provider_contract_version": self.provider_contract_version,
            "supports": list(self.supports),
            "limitations": list(self.limitations),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EvidenceRecord":
        from .provenance import canonical_json

        return cls(
            schema_version=str(payload.get("schema_version") or EVIDENCE_SCHEMA_VERSION),
            evidence_id=str(payload["evidence_id"]),
            provider=str(payload["provider"]),
            query_type=str(payload["query_type"]),
            request_json=canonical_json(payload.get("request")),
            retrieved_at=str(payload["retrieved_at"]),
            raw_sha256=str(payload["raw_sha256"]),
            raw_response_json=canonical_json(payload.get("raw_response")),
            normalized_response_json=(
                canonical_json(payload.get("normalized_response"))
                if payload.get("normalized_response") is not None
                else None
            ),
            entity_ids=tuple(sorted((str(k), str(v)) for k, v in (payload.get("entity_ids") or {}).items())),
            as_of=str(payload["as_of"]) if payload.get("as_of") is not None else None,
            period=tuple(sorted((str(k), str(v)) for k, v in (payload.get("period") or {}).items())),
            units=tuple(sorted((str(k), str(v)) for k, v in (payload.get("units") or {}).items())),
            provider_sources=tuple(str(item) for item in payload.get("provider_sources") or ()),
            update_dates=tuple(str(item) for item in payload.get("update_dates") or ()),
            warnings_json=tuple(canonical_json(item) for item in payload.get("warnings") or ()),
            completeness=(
                str(payload["completeness"])
                if payload.get("completeness") is not None
                else None
            ),
            provider_contract_version=(
                str(payload["provider_contract_version"])
                if payload.get("provider_contract_version") is not None
                else None
            ),
            supports=tuple(str(item) for item in payload.get("supports") or ()),
            limitations=tuple(str(item) for item in payload.get("limitations") or ()),
        )
