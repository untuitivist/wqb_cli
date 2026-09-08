from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence

from ...models import EvidenceRecord
from ...provenance import build_evidence_record
from .contract import WIND_PROVIDER_NAME, WIND_SERVER_TYPES


class WindResponseError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _parse_content_text(raw_response: Mapping[str, Any]) -> Any:
    content = raw_response.get("content")
    if not isinstance(content, list) or not content:
        return raw_response
    first = content[0]
    if not isinstance(first, Mapping) or "text" not in first:
        return raw_response
    text = first.get("text")
    if not isinstance(text, str):
        return text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _collect_metadata(payload: Any) -> tuple[dict[str, str], tuple[str, ...], tuple[str, ...]]:
    units: dict[str, str] = {}
    sources: set[str] = set()
    update_dates: set[str] = set()

    def walk(node: Any, path: str) -> None:
        if isinstance(node, Mapping):
            source = node.get("source")
            if source not in (None, ""):
                sources.add(str(source))
            update_date = node.get("updateDate")
            if update_date not in (None, ""):
                update_dates.add(str(update_date))
            unit = node.get("unit")
            if unit not in (None, "") and isinstance(unit, (str, int, float)):
                units[f"{path}.unit"] = str(unit)
            magnitude = node.get("magnitude")
            if magnitude not in (None, "") and isinstance(magnitude, (str, int, float)):
                units[f"{path}.magnitude"] = str(magnitude)
            for key, value in node.items():
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")

    walk(payload, "$normalized")
    return units, tuple(sorted(sources)), tuple(sorted(update_dates))



def infer_wind_request_semantics(
    *, server_type: str, tool_name: str, request: Mapping[str, Any]
) -> tuple[dict[str, str], str | None, dict[str, str]]:
    """Infer only request semantics that are explicit and replay-safe.

    Natural-language entity/date extraction is deliberately avoided except for exact
    Wind EDB codes, because guessing identifiers would weaken provenance. Explicit
    caller-supplied semantics can override these inferred values.
    """

    entity_ids: dict[str, str] = {}
    period: dict[str, str] = {}
    as_of: str | None = None

    windcode = request.get("windcode")
    if isinstance(windcode, str) and windcode.strip():
        entity_ids["windcode"] = windcode.strip()

    question = request.get("question")
    if server_type == "economic_data" and isinstance(question, str):
        stripped = question.strip()
        if re.fullmatch(r"M\d+(?:\s*,\s*M\d+)*", stripped, flags=re.IGNORECASE):
            entity_ids["edb_codes"] = ",".join(
                part.strip().upper() for part in stripped.split(",")
            )

    for key in ("begin_date", "begin", "beginDate"):
        value = request.get(key)
        if value not in (None, ""):
            period["begin"] = str(value)
            break
    for key in ("end_date", "end", "endDate"):
        value = request.get(key)
        if value not in (None, ""):
            period["end"] = str(value)
            break
    observation = request.get("observation")
    if observation not in (None, ""):
        period["observation"] = str(observation)
    aggregation = request.get("period")
    if aggregation not in (None, ""):
        period["aggregation"] = str(aggregation)

    # Exact single-date structured arguments are rare in current Wind contracts. Keep
    # this conservative and avoid mining natural-language question text for dates.
    for key in ("date", "trade_date", "report_date", "as_of"):
        value = request.get(key)
        if value not in (None, ""):
            as_of = str(value)
            break

    return entity_ids, as_of, period


def _has_stable_document_locator(payload: Any) -> bool:
    locator_keys = {
        "url",
        "sourceUrl",
        "source_url",
        "documentId",
        "document_id",
        "docId",
        "doc_id",
        "announcementId",
        "announcement_id",
        "newsId",
        "news_id",
    }

    def walk(node: Any) -> bool:
        if isinstance(node, Mapping):
            for key, value in node.items():
                if key in locator_keys and value not in (None, ""):
                    return True
                if walk(value):
                    return True
        elif isinstance(node, list):
            return any(walk(value) for value in node)
        return False

    return walk(payload)

def normalize_wind_evidence(
    *,
    server_type: str,
    tool_name: str,
    request: Mapping[str, Any],
    raw_response: Mapping[str, Any],
    provider_contract_version: str,
    retrieved_at: str | None = None,
    entity_ids: Mapping[str, str] | None = None,
    as_of: str | None = None,
    period: Mapping[str, str] | None = None,
    supports: Sequence[str] = (),
    limitations: Sequence[str] = (),
) -> EvidenceRecord:
    if server_type not in WIND_SERVER_TYPES:
        raise ValueError(f"unsupported Wind server_type: {server_type}")
    if not tool_name.strip():
        raise ValueError("tool_name must be non-empty")
    if not provider_contract_version.strip():
        raise ValueError("provider_contract_version must pin the Wind Skill commit/version")

    if raw_response.get("ok") is False:
        raise WindResponseError(
            str(raw_response.get("code") or "UNKNOWN"),
            str(raw_response.get("message") or "Wind call failed"),
        )

    normalized = _parse_content_text(raw_response)
    cli_meta = raw_response.get("cli_meta") if isinstance(raw_response.get("cli_meta"), Mapping) else {}
    returned_server = cli_meta.get("server_type")
    returned_tool = cli_meta.get("tool_name")
    if returned_server not in (None, server_type):
        raise WindResponseError(
            "ROUTE_MISMATCH",
            f"requested server_type={server_type} but Wind cli_meta returned {returned_server}",
        )
    if returned_tool not in (None, tool_name):
        raise WindResponseError(
            "ROUTE_MISMATCH",
            f"requested tool_name={tool_name} but Wind cli_meta returned {returned_tool}",
        )
    warnings = list(cli_meta.get("warnings") or [])
    completeness = cli_meta.get("completeness")
    units, provider_sources, update_dates = _collect_metadata(normalized)
    inferred_entities, inferred_as_of, inferred_period = infer_wind_request_semantics(
        server_type=server_type, tool_name=tool_name, request=request
    )
    resolved_entities = dict(inferred_entities)
    resolved_entities.update({str(k): str(v) for k, v in (entity_ids or {}).items()})
    resolved_period = dict(inferred_period)
    resolved_period.update({str(k): str(v) for k, v in (period or {}).items()})
    resolved_as_of = as_of or inferred_as_of

    resolved_limitations = list(limitations)
    if completeness in (None, "unknown", "not_asserted"):
        resolved_limitations.append(
            f"Wind cli_meta completeness is {completeness or 'not_provided'}; full result-set completeness is not independently asserted."
        )
    if not provider_sources:
        resolved_limitations.append(
            "Wind response did not expose an upstream source field; treat this as provider-level evidence, not a primary-source locator."
        )
    if server_type == "financial_docs" and not _has_stable_document_locator(normalized):
        resolved_limitations.append(
            "Wind financial_docs response did not expose a stable document URL/id locator; treat retrieved text as supporting evidence or a lead, not a reproducible primary-document citation."
        )

    return build_evidence_record(
        provider=WIND_PROVIDER_NAME,
        query_type=f"{server_type}.{tool_name}",
        request=request,
        raw_response=raw_response,
        normalized_response=normalized,
        retrieved_at=retrieved_at,
        entity_ids=resolved_entities,
        as_of=resolved_as_of,
        period=resolved_period,
        units=units,
        provider_sources=provider_sources,
        update_dates=update_dates,
        warnings=warnings,
        completeness=str(completeness) if completeness is not None else None,
        provider_contract_version=provider_contract_version,
        supports=supports,
        limitations=resolved_limitations,
    )
