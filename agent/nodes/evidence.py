from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from ..models.base import ModelRequest
from ..runner import RunnerError
from ..schemas import validate_model_output
from ..types import ModelRole, NodeResult, WorkflowNode


DATA_SOURCE_MISSING = "DATA_SOURCE_MISSING"
_EVIDENCE_CLASSES = ("community", "official_docs", "platform", "paper")
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_FASTEXPR_WORDS = frozenset({"true", "false", "null", "nan"})
_BASE_PRICE_VOLUME_FIELDS = frozenset(
    {"close", "open", "high", "low", "volume", "returns"}
)


@dataclass(frozen=True)
class FieldScreenResult:
    candidate_fields: tuple[dict[str, Any], ...]
    banned_fields: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceCoverage:
    complete: bool
    missing_sources: tuple[str, ...]


class EvidenceError(ValueError):
    """Raised when collected evidence is not a trustworthy command result."""


def screen_fields(
    *,
    platform_fields: object,
    used_fields: object,
    poor_os_fields: object,
    used_datasets: object,
) -> FieldScreenResult:
    """Apply deterministic field exclusions before either model sees the pool."""

    if not isinstance(platform_fields, (list, tuple)):
        raise TypeError("platform_fields must be a list")
    used = _normalized_names(used_fields, "used_fields")
    poor = _normalized_names(poor_os_fields, "poor_os_fields")
    datasets = _normalized_names(used_datasets, "used_datasets")
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in platform_fields:
        if not isinstance(item, Mapping):
            raise EvidenceError("platform field entries must be objects")
        identifier = item.get("id")
        if type(identifier) is not str or not identifier.strip():
            raise EvidenceError("platform field has invalid id")
        field_id = identifier.strip().lower()
        if field_id in seen:
            raise EvidenceError(f"duplicate platform field: {field_id}")
        seen.add(field_id)
        dataset = item.get("dataset")
        dataset_id = ""
        if isinstance(dataset, Mapping) and type(dataset.get("id")) is str:
            dataset_id = dataset["id"].strip().lower()
        elif type(item.get("dataset_id")) is str:
            dataset_id = item["dataset_id"].strip().lower()
        if not dataset_id:
            raise EvidenceError(f"platform field lacks dataset: {field_id}")
        if field_id in used | poor or dataset_id in datasets:
            continue
        copied = dict(item)
        copied["id"] = field_id
        candidates.append(copied)
    banned = tuple(sorted(used | poor))
    return FieldScreenResult(tuple(candidates), banned)


def evidence_coverage(lessons: object) -> EvidenceCoverage:
    if not isinstance(lessons, (list, tuple)):
        raise TypeError("lessons must be a list")
    present: set[str] = set()
    for lesson in lessons:
        if not isinstance(lesson, Mapping):
            raise EvidenceError("evidence lesson must be an object")
        source_class = lesson.get("source_class")
        source_id = lesson.get("source_id", lesson.get("artifact_id"))
        if source_class not in _EVIDENCE_CLASSES:
            raise EvidenceError("evidence lesson has invalid source_class")
        if type(source_id) is not str or not source_id.startswith("artifact:"):
            raise EvidenceError("evidence lesson must reference an artifact")
        present.add(source_class)
    missing = tuple(name for name in _EVIDENCE_CLASSES if name not in present)
    return EvidenceCoverage(not missing, missing)


class EvidenceNodes:
    """Nodes F and G: collect command-owned facts and evidence artifacts."""

    def __init__(self, *, runner: Any, router: Any, store: Any, artifacts: Any | None = None) -> None:
        if not callable(getattr(runner, "run", None)):
            raise TypeError("runner must provide run")
        if not callable(getattr(router, "invoke", None)):
            raise TypeError("router must provide invoke")
        self._runner = runner
        self._router = router
        self._store = store
        self._artifacts = artifacts if artifacts is not None else getattr(runner, "artifacts", None)

    def run_f(
        self,
        run_id: str,
        scope: Mapping[str, Any],
        target_tower: Mapping[str, Any],
        *,
        local_data_root: Path | None = None,
    ) -> NodeResult:
        normalized_scope = _scope(scope)
        scope_key = f"{normalized_scope['region']}_{normalized_scope['delay']}"
        files_result = self._run(
            run_id, WorkflowNode.F, ("scope", "files"), "scope_files.json"
        )
        files_payload = self._payload(files_result)
        if _missing_local_source(files_payload):
            return self._data_source_missing(run_id, (files_result,), scope_key)
        files_body = self._body(files_payload, "scope files", local=True)
        if not _scope_files_present(files_body):
            return self._data_source_missing(run_id, (files_result,), scope_key)

        local_commands = (
            (("scope", "list"), "scope_list.json"),
            (("scope", "show", scope_key), "scope_data_all.json"),
            (("scope", "top", scope_key, "--group", "datafield", "--min-count", "5", "--limit", "100"), "scope_top.json"),
        )
        remaining_local_results = [
            self._run(run_id, WorkflowNode.F, argv, name)
            for argv, name in local_commands
        ]
        remaining_local_bodies = [
            self._body(self._payload(result), name, local=True)
            for result, (_, name) in zip(remaining_local_results, local_commands, strict=True)
        ]
        local_results = [files_result, *remaining_local_results]
        if not _has_required_scope_data(
            remaining_local_bodies[0], remaining_local_bodies[1], scope_key=scope_key
        ):
            raise EvidenceError("scope list/show responses do not contain the locked scope")
        top_body = remaining_local_bodies[2]
        top_rows = _top_field_rows(top_body, scope_key)

        remote_commands = (
            (("data", "fields", "--region", normalized_scope["region"], "--delay", str(normalized_scope["delay"]), "--universe", normalized_scope["universe"], "--category", normalized_scope["category"], "--limit", "100", "--offset", "0"), "data_fields.json"),
            (("data", "datasets", "--region", normalized_scope["region"], "--delay", str(normalized_scope["delay"]), "--universe", normalized_scope["universe"], "--category", normalized_scope["category"], "--limit", "100", "--offset", "0"), "data_datasets.json"),
            (("alpha", "list", "--type", "REGULAR", "--settings-region", normalized_scope["region"], "--settings-delay", str(normalized_scope["delay"]), "--settings-instrument-type", "EQUITY", "--limit", "100", "--offset", "0", "--order=-dateSubmitted", "--status", "ACTIVE", "--tag", f"{normalized_scope['region']}/D{normalized_scope['delay']}/{normalized_scope['category'].upper()}"), "tag_alphas.json"),
        )
        remote_results = [
            self._run(run_id, WorkflowNode.F, argv, name)
            for argv, name in remote_commands
        ]
        remote_bodies = [
            self._body(self._payload(result), name)
            for result, (_, name) in zip(remote_results, remote_commands, strict=True)
        ]
        alpha_results: list[Any] = []
        tag_rows = _record_page(remote_bodies[2], "tag alpha search")
        if not tag_rows:
            for page in range(20):
                offset = page * 100
                argv = (
                    "alpha", "list",
                    "--settings-region", normalized_scope["region"],
                    "--settings-delay", str(normalized_scope["delay"]),
                    "--settings-instrument-type", "EQUITY",
                    "--limit", "100", "--offset", str(offset),
                    "--order=-dateSubmitted", "--status", "ACTIVE",
                )
                result = self._run(
                    run_id, WorkflowNode.F, argv,
                    f"scope_alphas_page{page + 1}.json",
                )
                body = self._body(self._payload(result), "scope alpha search")
                alpha_results.append(result)
                rows = _record_page(body, "scope alpha search")
                if _page_is_complete(body, offset, len(rows)):
                    break
            else:
                raise EvidenceError("scope alpha pagination exceeds the page limit")
        alpha_row_results: list[Any] = []
        poor_os: set[str] = set()
        for field_id in [row["name"] for row in top_rows]:
            result = self._run(
                run_id,
                WorkflowNode.F,
                (
                    "scope", "alpha-rows", scope_key, "--table", "os",
                    "--datafield", field_id, "--limit", "20", "--columns",
                    "id,sharpe,fitness,turnover,margin",
                ),
                f"field_os_rows__{field_id}.json",
            )
            body = self._body(
                self._payload(result), f"OS rows for {field_id}", local=True
            )
            if _is_poor_os_page(body, field_id, scope_key):
                poor_os.add(field_id.lower())
            alpha_row_results.append(result)

        results = [*local_results, *remote_results, *alpha_results, *alpha_row_results]
        fields = _field_rows(remote_bodies[0])
        datasets = _dataset_ids(remote_bodies[1])
        used = _used_fields(target_tower)
        field_datasets = _field_dataset_index(fields)
        used_datasets = {
            field_datasets[field_id]
            for field_id in used
            if field_id in field_datasets and field_datasets[field_id] in datasets
        }
        base_fields = sorted(used & _BASE_PRICE_VOLUME_FIELDS)
        screened = screen_fields(
            platform_fields=fields, used_fields=used, poor_os_fields=poor_os, used_datasets=used_datasets,
        )
        experiences = self._search_experience(normalized_scope)
        candidate_ids = [field["id"] for field in screened.candidate_fields]
        authoritative = {
            "scope": normalized_scope,
            "target_tower_id": _tower_id(target_tower),
            "candidate_fields": candidate_ids,
            "banned_fields": list(screened.banned_fields),
            "used_datafields": sorted(used),
            "base_price_volume_fields": base_fields,
            "used_dataset_ids": sorted(used_datasets),
            "poor_os_fields": sorted(poor_os),
            "experience_failures": experiences[:20],
            "artifact_ids": list(self._artifact_ids(*results)),
        }
        operator = self._invoke(
            ModelRole.OPERATOR, WorkflowNode.F,
            "Organize the supplied screened field facts only. Do not choose fields, commands, scope, or a plan.",
            authoritative,
        )
        planner = self._invoke(
            ModelRole.PLANNER, WorkflowNode.F,
            "Define additional evidence requirements using only the supplied screened fields and artifact references. Do not alter scope or select expressions.",
            {"screened_fields": candidate_ids, "target_tower_id": authoritative["target_tower_id"], "operator_summary": _model_summary(operator), "artifact_ids": authoritative["artifact_ids"]},
        )
        artifact_ids = self._artifact_ids(*results)
        artifact_ids += self._write_json(run_id, WorkflowNode.F, "screened_fields.json", authoritative)
        summary = {"candidate_field_count": len(candidate_ids), "banned_fields": list(screened.banned_fields), "planner": _model_summary(planner)}
        return NodeResult(WorkflowNode.F, summary, artifact_ids, next_node=WorkflowNode.G, payload={**authoritative, "evidence_requirements": dict(planner.get("evidence_requirements", {}))})

    def _data_source_missing(
        self, run_id: str, results: tuple[Any, ...], scope_key: str
    ) -> NodeResult:
        setup_paths = (
            "local/data_all/info_data.bin",
            "local/data_all/all_data.pickle",
            "wqb scope files",
            f"wqb scope show {scope_key}",
        )
        return NodeResult(
            WorkflowNode.F,
            {"failure_class": DATA_SOURCE_MISSING, "setup_paths": setup_paths},
            self._artifact_ids(*results),
            next_node=WorkflowNode.F,
            payload={"failure_class": DATA_SOURCE_MISSING, "setup_paths": list(setup_paths)},
        )

    def run_g(
        self, run_id: str, mechanism_keywords: Iterable[str], *, arxiv_available: bool | None = None
    ) -> NodeResult:
        keywords = _keywords(mechanism_keywords)
        lessons: list[dict[str, str]] = []
        artifacts: list[str] = []
        paper_unavailable = False
        for keyword in keywords:
            community = self._run(
                run_id, WorkflowNode.G, ("community", "search", keyword),
                f"{keyword}_community_search.json",
            )
            community_body = self._body(self._payload(community), "community search", local=True)
            community_artifacts = self._artifact_ids(community)
            artifacts.extend(community_artifacts)
            lesson = _lesson(
                "community",
                community_artifacts[0] if community_artifacts else None,
                community_body,
                keyword,
            )
            if lesson is not None:
                lessons.append(lesson)

            docs = self._run(
                run_id, WorkflowNode.G, ("docs", "list"),
                f"{keyword}_docs_list.json",
            )
            docs_body = self._body(self._payload(docs), "docs list", local=True)
            docs_artifacts = self._artifact_ids(docs)
            artifacts.extend(docs_artifacts)
            document_id = _document_id(docs_body)
            if document_id is not None:
                shown = self._run(
                    run_id, WorkflowNode.G, ("docs", "show", document_id),
                    f"{keyword}_docs_show.json",
                )
                shown_body = self._body(self._payload(shown), "docs show", local=True)
                shown_artifacts = self._artifact_ids(shown)
                artifacts.extend(shown_artifacts)
                lesson = _lesson(
                    "official_docs",
                    shown_artifacts[0] if shown_artifacts else None,
                    shown_body,
                    keyword,
                )
                if lesson is not None:
                    lessons.append(lesson)

            platform = self._run(
                run_id, WorkflowNode.G, ("search", keyword),
                f"{keyword}_platform_search.json",
            )
            platform_body = self._body(self._payload(platform), "platform search")
            platform_artifacts = self._artifact_ids(platform)
            artifacts.extend(platform_artifacts)
            lesson = _lesson(
                "platform",
                platform_artifacts[0] if platform_artifacts else None,
                platform_body,
                keyword,
            )
            if lesson is not None:
                lessons.append(lesson)

            external = getattr(self._runner, "run_external", None)
            if arxiv_available is False or not callable(external):
                paper_unavailable = True
                continue
            try:
                result = external(
                    run_id, WorkflowNode.G,
                    ("arxiv", "search", "query", keyword),
                    f"{keyword}_papers.json",
                )
            except RunnerError:
                paper_unavailable = True
                continue
            body = self._body(self._payload(result), "papers", local=True)
            artifact_id = self._artifact_ids(result)
            artifacts.extend(artifact_id)
            lesson = _lesson("paper", artifact_id[0] if artifact_id else None, body, keyword)
            if lesson is None:
                paper_unavailable = True
            else:
                lessons.append(lesson)
        coverage = evidence_coverage(lessons)
        evidence_artifacts = self._write_json(run_id, WorkflowNode.G, "evidence_lessons.json", {"lessons": lessons, "coverage": list(coverage.missing_sources)})
        artifacts.extend(evidence_artifacts)
        summary = {"lesson_count": len(lessons), "missing_sources": list(coverage.missing_sources), "paper_source_unavailable": paper_unavailable}
        return NodeResult(
            WorkflowNode.G, summary, tuple(artifacts),
            next_node=WorkflowNode.H if coverage.complete else WorkflowNode.G,
            payload={"lessons": lessons, "missing_sources": list(coverage.missing_sources), "paper_source_unavailable": paper_unavailable},
        )

    def _run(self, run_id: str, node: WorkflowNode, argv: tuple[str, ...], name: str) -> Any:
        return self._runner.run(run_id, node, argv, name)

    @staticmethod
    def _payload(result: Any) -> dict[str, Any]:
        payload = getattr(result, "payload", None)
        if type(payload) is not dict:
            raise EvidenceError("runner result has no valid payload")
        return payload

    @staticmethod
    def _body(payload: dict[str, Any], label: str, *, local: bool = False) -> dict[str, Any]:
        if local:
            if payload.get("ok") is not True or "response" in payload:
                raise EvidenceError(f"{label} did not return a successful local response")
            return {key: value for key, value in payload.items() if key != "ok"}
        response = payload.get("response")
        if payload.get("ok") is not True or type(response) is not dict:
            raise EvidenceError(f"{label} did not return a successful response")
        status = response.get("status_code")
        body = response.get("body")
        if type(status) is not int or not 200 <= status <= 299 or type(body) is not dict:
            raise EvidenceError(f"{label} did not return a successful response body")
        return body

    @staticmethod
    def _artifact_ids(*results: Any) -> tuple[str, ...]:
        ids: list[str] = []
        for result in results:
            artifact = getattr(result, "artifact", None)
            identifier = getattr(artifact, "id", None)
            if type(identifier) is int and identifier > 0:
                ids.append(f"artifact:{identifier}")
        return tuple(ids)

    def _invoke(self, role: ModelRole, node: WorkflowNode, instructions: str, context: dict[str, Any]) -> dict[str, Any]:
        result = self._router.invoke(
            ModelRequest(
                role=role,
                node=node,
                instructions=instructions,
                context=_bounded_context(context),
            )
        )
        value = getattr(result, "value", None)
        if type(value) is not dict:
            raise EvidenceError("model response has no valid value")
        return validate_model_output(role, node, value)

    def _search_experience(self, scope: dict[str, Any]) -> list[dict[str, Any]]:
        search = getattr(self._store, "search_experience", None)
        if not callable(search):
            return []
        records = search(scope["region"], scope["delay"], scope["category"], limit=20)
        if not isinstance(records, list):
            raise EvidenceError("experience store returned invalid results")
        return [{"failure_class": getattr(row, "failure_class", None), "field_ids": list(getattr(row, "field_ids", ())), "expression_fingerprint": getattr(row, "expression_fingerprint", None)} for row in records]

    def _write_json(self, run_id: str, node: WorkflowNode, name: str, value: dict[str, Any]) -> tuple[str, ...]:
        if not callable(getattr(self._artifacts, "write_json", None)):
            return ()
        artifact = self._artifacts.write_json(run_id, node, name, value)
        identifier = getattr(artifact, "id", None)
        return (f"artifact:{identifier}",) if type(identifier) is int and identifier > 0 else ()

def _normalized_names(values: object, label: str) -> set[str]:
    if not isinstance(values, (set, frozenset, list, tuple)):
        raise TypeError(f"{label} must be a collection of field names")
    result: set[str] = set()
    for value in values:
        if type(value) is not str or not value.strip():
            raise EvidenceError(f"{label} contains an invalid name")
        result.add(value.strip().lower())
    return result


def _scope(value: Mapping[str, Any]) -> dict[str, Any]:
    required = ("region", "delay", "universe", "neutralization", "category")
    if not isinstance(value, Mapping):
        raise TypeError("scope must be a mapping")
    result: dict[str, Any] = {}
    for key in required:
        item = value.get(key)
        if key == "delay":
            if type(item) is not int or item not in {0, 1}:
                raise EvidenceError("scope delay is invalid")
        elif type(item) is not str or not item.strip():
            raise EvidenceError(f"scope {key} is invalid")
        result[key] = item.strip() if type(item) is str else item
    return result


def _records(body: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("results", "items", "alphas", "fields", "files"):
        value = body.get(key)
        if isinstance(value, list) and all(isinstance(item, dict) for item in value):
            return [dict(item) for item in value]
    return []


def _record_page(body: dict[str, Any], label: str) -> list[dict[str, Any]]:
    rows = body.get("results")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise EvidenceError(f"{label} response has invalid results")
    return [dict(row) for row in rows]


def _page_is_complete(body: dict[str, Any], offset: int, page_size: int) -> bool:
    count = body.get("count")
    next_page = body.get("next")
    if "next" in body and next_page is None:
        return True
    if type(count) is int and count >= 0:
        return offset + page_size >= count
    return page_size < 100


def _field_rows(body: dict[str, Any]) -> list[dict[str, Any]]:
    rows = body.get("results", body.get("fields"))
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise EvidenceError("data fields response has invalid fields")
    return [dict(row) for row in rows]


def _dataset_ids(body: dict[str, Any]) -> set[str]:
    rows = body.get("results", body.get("datasets"))
    if not isinstance(rows, list):
        raise EvidenceError("data datasets response has invalid datasets")
    identifiers = set()
    for row in rows:
        if not isinstance(row, Mapping) or type(row.get("id")) is not str or not row["id"].strip():
            raise EvidenceError("data datasets entry has invalid id")
        identifiers.add(row["id"].strip().lower())
    return identifiers


def _has_required_scope_data(
    list_body: dict[str, Any], show_body: dict[str, Any], *, scope_key: str,
) -> bool:
    scopes = list_body.get("scopes")
    shown = show_body.get("scope")
    if not isinstance(scopes, list) or not all(isinstance(row, Mapping) for row in scopes):
        raise EvidenceError("scope list response has invalid scopes")
    identifiers = []
    for row in scopes:
        identifier = row.get("scope")
        if type(identifier) is not str or not identifier.strip():
            raise EvidenceError("scope list entry has invalid scope")
        identifiers.append(identifier.strip())
    return scope_key in identifiers and shown == scope_key


def _missing_local_source(payload: dict[str, Any]) -> bool:
    if payload.get("ok") is not False:
        return False
    reason = payload.get("reason")
    return type(reason) is str and "not_found" in reason.lower()


def _scope_files_present(body: dict[str, Any]) -> bool:
    info = body.get("info_data")
    all_data = body.get("all_data")
    if not isinstance(info, Mapping) or not isinstance(all_data, Mapping):
        raise EvidenceError("scope files response has invalid file statuses")
    return info.get("exists") is True and all_data.get("exists") is True


def _top_field_rows(body: dict[str, Any], scope_key: str) -> list[dict[str, Any]]:
    if body.get("scope") != scope_key or body.get("group") not in {None, "datafield"}:
        raise EvidenceError("scope top response identity does not match locked scope")
    rows = body.get("results")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise EvidenceError("scope top response has invalid results")
    copied: list[dict[str, Any]] = []
    for row in rows:
        name = row.get("name")
        if type(name) is not str or not name.strip():
            raise EvidenceError("scope top entry has invalid name")
        copied.append(dict(row, name=name.strip().lower()))
    return copied


def _is_poor_os_page(body: dict[str, Any], field_id: str, scope_key: str) -> bool:
    filters = body.get("filters")
    rows = body.get("rows")
    if (
        body.get("scope") != scope_key
        or body.get("table") != "os"
        or not isinstance(filters, Mapping)
        or filters.get("datafield") != field_id
        or not isinstance(rows, list)
        or not all(isinstance(row, Mapping) for row in rows)
    ):
        raise EvidenceError("scope alpha-rows response identity or shape is invalid")
    if not rows:
        return False
    return not any(
        _finite_metric(row.get("sharpe"), 1.58)
        and _finite_metric(row.get("fitness"), 1.0)
        and _bounded_metric(row.get("turnover"), 0.01, 0.70)
        and _finite_metric(row.get("margin"), 0.001)
        for row in rows
    )


def _finite_metric(value: object, threshold: float) -> bool:
    return type(value) in {int, float} and value > threshold


def _bounded_metric(value: object, lower: float, upper: float) -> bool:
    return type(value) in {int, float} and lower < value < upper


def _field_dataset_index(fields: list[dict[str, Any]]) -> dict[str, str]:
    index: dict[str, str] = {}
    for field in fields:
        dataset = field.get("dataset")
        if isinstance(dataset, Mapping) and type(dataset.get("id")) is str:
            index[field["id"].strip().lower()] = dataset["id"].strip().lower()
    return index


def _used_fields(tower: Mapping[str, Any]) -> set[str]:
    code = tower.get("code", tower.get("expression")) if isinstance(tower, Mapping) else None
    if code is None and isinstance(tower.get("regular"), Mapping):
        regular = tower["regular"]
        code = regular.get("code", regular.get("expression"))
    if type(code) is not str or not code.strip():
        raise EvidenceError("target tower has no parseable code")
    without_strings = re.sub(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"", "", code)
    operators = {match.group(1).lower() for match in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(", without_strings)}
    return {token.lower() for token in _IDENTIFIER.findall(without_strings) if token.lower() not in operators | _FASTEXPR_WORDS}


def _tower_id(tower: Mapping[str, Any]) -> str:
    value = tower.get("alpha_id", tower.get("id")) if isinstance(tower, Mapping) else None
    if type(value) is not str or not value.strip():
        raise EvidenceError("target tower has invalid id")
    return value.strip()


def _keywords(values: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if type(value) is not str or not value.strip():
            raise EvidenceError("mechanism keyword is invalid")
        normalized = value.strip().lower()
        if normalized not in result:
            result.append(normalized)
    if not result:
        raise EvidenceError("at least one mechanism keyword is required")
    return tuple(result[:8])


def _lesson(source_class: str, artifact_id: str | None, body: dict[str, Any], keyword: str) -> dict[str, str] | None:
    if artifact_id is None:
        return None
    if source_class == "platform":
        return platform_search_lesson(body, artifact_id, keyword)
    rows = _records(body)
    if not rows:
        for key in ("documents", "papers"):
            value = body.get(key)
            if isinstance(value, list) and all(isinstance(item, Mapping) for item in value):
                rows = [dict(item) for item in value]
                break
    if not rows and source_class == "community":
        for key in ("forum_topics", "forum_comments", "docs_articles"):
            value = body.get(key)
            if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
                raise EvidenceError("community search response has invalid result lists")
            rows.extend(dict(item) for item in value)
    row = rows[0] if rows else body
    statement = row.get("extracted_statement", row.get("text", row.get("summary", row.get("title"))))
    if type(statement) is not str or not statement.strip():
        return None
    return {"source_class": source_class, "source_id": artifact_id, "extracted_statement": statement.strip()[:2_000], "applicability": keyword}


def platform_search_lesson(
    body: Mapping[str, Any], artifact_id: str, keyword: str
) -> dict[str, str] | None:
    query = body.get("query")
    if not isinstance(query, list) or not all(type(item) is str for item in query):
        raise EvidenceError("platform search response has invalid query inventory")
    statement = next((item.strip() for item in query if item.strip()), None)
    if statement is None:
        return None
    if type(artifact_id) is not str or not artifact_id.startswith("artifact:"):
        raise EvidenceError("platform search lesson requires an artifact source")
    return {
        "source_class": "platform",
        "source_id": artifact_id,
        "extracted_statement": statement[:2_000],
        "applicability": keyword,
    }


def _document_id(body: dict[str, Any]) -> str | None:
    rows = body.get("nodes", body.get("documents", body.get("results", [])))
    if not isinstance(rows, list):
        raise EvidenceError("docs list response has invalid documents")
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        path = row.get("readme", row.get("id"))
        if type(path) is str and path.strip():
            return path.strip()
    return None


def _model_summary(value: dict[str, Any]) -> dict[str, Any]:
    return {key: value[key] for key in ("decision", "reasoning_summary", "evidence_refs", "confidence") if key in value}


def _bounded_context(value: dict[str, Any]) -> dict[str, Any]:
    def copy(item: object, depth: int, string_limit: int, item_limit: int) -> object:
        if item is None or type(item) in {bool, int, float}:
            return item
        if type(item) is str:
            return item[:string_limit]
        if depth >= 8:
            return "[truncated]"
        if isinstance(item, Mapping):
            return {
                key[:128]: copy(child, depth + 1, string_limit, item_limit)
                for key, child in list(item.items())[:item_limit]
                if type(key) is str
            }
        if isinstance(item, (list, tuple)):
            return [copy(child, depth + 1, string_limit, item_limit) for child in list(item)[:item_limit]]
        return "[unsupported]"

    for string_limit, item_limit in ((1_000, 32), (256, 12), (96, 8)):
        bounded = copy(value, 0, string_limit, item_limit)
        if isinstance(bounded, dict) and len(json.dumps(bounded, ensure_ascii=False, sort_keys=True, separators=(",", ":"))) <= 20_000:
            return bounded
    raise EvidenceError("model context exceeds the bounded input limit")
