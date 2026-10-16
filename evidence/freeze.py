from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .provenance import utc_now_iso


RESEARCH_FREEZE_SCHEMA = "wqb.wind-research-freeze.v1"


class ResearchFreezeError(ValueError):
    pass


@dataclass(frozen=True)
class ResearchFreeze:
    manifest_path: Path
    manifest_sha256: str
    run_id: str
    allowed_mechanism_ids: tuple[str, ...]
    allowed_datafield_ids: tuple[str, ...]
    mechanism_field_ids: tuple[tuple[str, tuple[str, ...]], ...]
    artifact_hashes: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RESEARCH_FREEZE_SCHEMA,
            "manifest_path": str(self.manifest_path),
            "manifest_sha256": self.manifest_sha256,
            "run_id": self.run_id,
            "allowed_mechanism_ids": list(self.allowed_mechanism_ids),
            "allowed_datafield_ids": list(self.allowed_datafield_ids),
            "mechanism_field_ids": {
                mechanism_id: list(field_ids)
                for mechanism_id, field_ids in self.mechanism_field_ids
            },
            "artifact_hashes": dict(self.artifact_hashes),
        }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise ResearchFreezeError(f"freeze artifact not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ResearchFreezeError(f"freeze artifact is not valid JSON: {path}: {exc}") from exc


def _candidate_collection(payload: Any) -> Sequence[Any]:
    if not isinstance(payload, Mapping):
        raise ResearchFreezeError(
            "candidate_datafields must be a frozen JSON object, not a bare collection"
        )
    freeze_status = str(payload.get("freeze_status") or "").strip().upper()
    if freeze_status != "FROZEN":
        raise ResearchFreezeError(
            f"candidate_datafields is not frozen: freeze_status={freeze_status or '<missing>'}"
        )
    if payload.get("complete") is not True:
        raise ResearchFreezeError("candidate_datafields must declare complete=true")
    if payload.get("scope_pending") is not False:
        raise ResearchFreezeError("candidate_datafields must declare scope_pending=false")
    for key in ("fields", "candidate_datafields", "candidates", "datafields", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    raise ResearchFreezeError("cannot identify candidate datafield collection")


def extract_candidate_datafield_ids(payload: Any) -> tuple[str, ...]:
    result: set[str] = set()
    for item in _candidate_collection(payload):
        if isinstance(item, str):
            field_id = item.strip()
        elif isinstance(item, Mapping):
            field_id = str(item.get("field_id") or item.get("id") or "").strip()
        else:
            raise ResearchFreezeError("candidate datafield entries must be strings or objects")
        if not field_id:
            raise ResearchFreezeError("candidate datafield entry missing id")
        result.add(field_id)
    if not result:
        raise ResearchFreezeError("candidate_datafields must contain at least one field")
    return tuple(sorted(result))


def _mechanism_collection(payload: Any) -> Sequence[Mapping[str, Any]]:
    if isinstance(payload, list):
        raw = payload
    elif isinstance(payload, Mapping):
        for key in ("mechanisms", "mechanism_contracts", "contracts"):
            value = payload.get(key)
            if isinstance(value, list):
                raw = value
                break
        else:
            if payload and all(isinstance(value, Mapping) for value in payload.values()):
                expanded: list[Mapping[str, Any]] = []
                for key, value in payload.items():
                    item = dict(value)
                    item.setdefault("mechanism_id", str(key))
                    expanded.append(item)
                raw = expanded
            else:
                raise ResearchFreezeError("cannot identify mechanism contract collection")
    else:
        raise ResearchFreezeError("mechanism contracts must be a list or mapping")

    result: list[Mapping[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise ResearchFreezeError("mechanism contract entries must be objects")
        result.append(item)
    return result


def extract_mechanism_field_ids(
    payload: Any,
    *,
    allowed_datafield_ids: Iterable[str],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    allowed = set(allowed_datafield_ids)
    result: dict[str, tuple[str, ...]] = {}
    for item in _mechanism_collection(payload):
        mechanism_id = str(item.get("mechanism_id") or "").strip()
        if not mechanism_id:
            raise ResearchFreezeError("mechanism contract missing mechanism_id")
        if mechanism_id in result:
            raise ResearchFreezeError(f"duplicate mechanism_id: {mechanism_id}")
        reality_refs = item.get("reality_evidence_refs") or ()
        if isinstance(reality_refs, str):
            reality_refs = [reality_refs]
        if any(str(value).strip() for value in reality_refs):
            raise ResearchFreezeError(
                f"baseline mechanism {mechanism_id} already contains Wind reality evidence"
            )
        raw_fields = item.get("field_ids") or ()
        if isinstance(raw_fields, str):
            raw_fields = [raw_fields]
        if not isinstance(raw_fields, (list, tuple)):
            raise ResearchFreezeError(
                f"mechanism {mechanism_id} field_ids must be a JSON array"
            )
        fields = tuple(sorted({str(value).strip() for value in raw_fields if str(value).strip()}))
        if not fields:
            raise ResearchFreezeError(f"mechanism {mechanism_id} has no field_ids")
        missing = sorted(set(fields) - allowed)
        if missing:
            raise ResearchFreezeError(
                f"mechanism {mechanism_id} uses fields absent from frozen F candidates: {missing}"
            )
        result[mechanism_id] = fields
    if not result:
        raise ResearchFreezeError("mechanism families must contain at least one mechanism")
    return tuple(sorted(result.items()))


def _snapshot_field_ids(payload: Any) -> tuple[str, ...]:
    if isinstance(payload, Mapping):
        # WQB CLI endpoint outputs are envelopes. Unwrap only the known response/body
        # layers so nested dataset/category ids cannot be mistaken for field ids.
        response = payload.get("response")
        if isinstance(response, Mapping) and "body" in response:
            return _snapshot_field_ids(response.get("body"))
        if "body" in payload and isinstance(payload.get("body"), (Mapping, list)):
            return _snapshot_field_ids(payload.get("body"))

        direct = str(payload.get("field_id") or payload.get("id") or "").strip()
        if direct:
            return (direct,)
        for key in ("fields", "datafields", "results", "candidates"):
            value = payload.get(key)
            if isinstance(value, list):
                return _snapshot_field_ids(value)
        if payload and all(isinstance(value, Mapping) for value in payload.values()):
            result: set[str] = set()
            for key, value in payload.items():
                field_id = str(value.get("field_id") or value.get("id") or key).strip()
                if field_id:
                    result.add(field_id)
            return tuple(sorted(result))
        return ()
    if isinstance(payload, list):
        result: set[str] = set()
        for item in payload:
            if isinstance(item, str):
                field_id = item.strip()
            elif isinstance(item, Mapping):
                field_id = str(item.get("field_id") or item.get("id") or "").strip()
            else:
                field_id = ""
            if field_id:
                result.add(field_id)
        return tuple(sorted(result))
    return ()


def _require_snapshot_coverage(
    snapshot_paths: Iterable[Path],
    *,
    candidate_ids: Iterable[str],
) -> None:
    covered: set[str] = set()
    for path in snapshot_paths:
        covered.update(_snapshot_field_ids(_load_json(path)))
    missing = sorted(set(candidate_ids) - covered)
    if missing:
        raise ResearchFreezeError(
            f"BRAIN field metadata snapshots do not cover frozen candidates: {missing}"
        )


def _artifact_entry(path: Path) -> dict[str, str]:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise ResearchFreezeError(f"freeze artifact not found: {resolved}")
    return {"path": str(resolved), "sha256": _sha256_file(resolved)}


def build_research_freeze_manifest(
    *,
    run_id: str,
    main_tower_path: str | Path,
    candidate_datafields_path: str | Path,
    mechanisms_path: str | Path,
    run_constraints_path: str | Path,
    brain_field_snapshots: Iterable[str | Path],
    non_wind_evidence: Iterable[str | Path] = (),
) -> dict[str, Any]:
    normalized_run_id = run_id.strip()
    if not normalized_run_id:
        raise ResearchFreezeError("run_id must be non-empty")

    main_tower = Path(main_tower_path).expanduser().resolve()
    candidates = Path(candidate_datafields_path).expanduser().resolve()
    mechanisms = Path(mechanisms_path).expanduser().resolve()
    constraints = Path(run_constraints_path).expanduser().resolve()

    tower_payload = _load_json(main_tower)
    if not isinstance(tower_payload, Mapping):
        raise ResearchFreezeError("main_tower must contain a JSON object")
    decision_status = str(tower_payload.get("decision_status") or "").strip().lower()
    if decision_status not in {"frozen", "frozen_d"}:
        raise ResearchFreezeError(
            f"main_tower is not frozen: decision_status={decision_status or '<missing>'}"
        )

    candidate_payload = _load_json(candidates)
    candidate_ids = extract_candidate_datafield_ids(candidate_payload)
    mechanism_payload = _load_json(mechanisms)
    mechanism_fields = extract_mechanism_field_ids(
        mechanism_payload, allowed_datafield_ids=candidate_ids
    )

    constraints_payload = _load_json(constraints)
    if not isinstance(constraints_payload, Mapping):
        raise ResearchFreezeError("run_constraints must contain a JSON object")

    snapshot_paths = tuple(Path(value).expanduser().resolve() for value in brain_field_snapshots)
    if not snapshot_paths:
        raise ResearchFreezeError("at least one BRAIN field metadata snapshot is required")
    _require_snapshot_coverage(snapshot_paths, candidate_ids=candidate_ids)
    evidence_paths = tuple(Path(value).expanduser().resolve() for value in non_wind_evidence)

    return {
        "schema_version": RESEARCH_FREEZE_SCHEMA,
        "status": "FROZEN",
        "created_at": utc_now_iso(),
        "run_id": normalized_run_id,
        "artifacts": {
            "main_tower": _artifact_entry(main_tower),
            "candidate_datafields": _artifact_entry(candidates),
            "mechanisms": _artifact_entry(mechanisms),
            "run_constraints": _artifact_entry(constraints),
            "brain_field_snapshots": [_artifact_entry(path) for path in snapshot_paths],
            "non_wind_evidence": [_artifact_entry(path) for path in evidence_paths],
        },
        "allowed_datafield_ids": list(candidate_ids),
        "allowed_mechanism_ids": [mechanism_id for mechanism_id, _ in mechanism_fields],
        "mechanism_field_ids": {
            mechanism_id: list(field_ids)
            for mechanism_id, field_ids in mechanism_fields
        },
    }


def _resolve_artifact_path(raw_path: Any, manifest_path: Path) -> Path:
    text = str(raw_path or "").strip()
    if not text:
        raise ResearchFreezeError("freeze artifact entry missing path")
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = manifest_path.parent / path
    return path.resolve()


def _verify_artifact_entry(
    name: str,
    entry: Any,
    *,
    manifest_path: Path,
) -> tuple[Path, str]:
    if not isinstance(entry, Mapping):
        raise ResearchFreezeError(f"freeze artifact {name} must be an object")
    path = _resolve_artifact_path(entry.get("path"), manifest_path)
    expected = str(entry.get("sha256") or "").strip().lower()
    if len(expected) != 64:
        raise ResearchFreezeError(f"freeze artifact {name} has invalid sha256")
    if not path.is_file():
        raise ResearchFreezeError(f"freeze artifact {name} not found: {path}")
    actual = _sha256_file(path)
    if actual != expected:
        raise ResearchFreezeError(
            f"freeze artifact hash mismatch for {name}: expected {expected}, got {actual}"
        )
    return path, actual


def load_research_freeze(manifest_path: str | Path) -> ResearchFreeze:
    path = Path(manifest_path).expanduser().resolve()
    payload = _load_json(path)
    if not isinstance(payload, Mapping):
        raise ResearchFreezeError("freeze manifest must contain a JSON object")
    if payload.get("schema_version") != RESEARCH_FREEZE_SCHEMA:
        raise ResearchFreezeError(
            f"unsupported freeze schema: {payload.get('schema_version')!r}"
        )
    if str(payload.get("status") or "").upper() != "FROZEN":
        raise ResearchFreezeError("freeze manifest status must be FROZEN")
    run_id = str(payload.get("run_id") or "").strip()
    if not run_id:
        raise ResearchFreezeError("freeze manifest missing run_id")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, Mapping):
        raise ResearchFreezeError("freeze manifest missing artifacts")

    verified: dict[str, tuple[Path, str]] = {}
    for name in ("main_tower", "candidate_datafields", "mechanisms", "run_constraints"):
        verified[name] = _verify_artifact_entry(name, artifacts.get(name), manifest_path=path)

    snapshots = artifacts.get("brain_field_snapshots")
    if not isinstance(snapshots, list) or not snapshots:
        raise ResearchFreezeError("freeze manifest requires BRAIN field metadata snapshots")
    for index, entry in enumerate(snapshots, 1):
        name = f"brain_field_snapshot[{index}]"
        verified[name] = _verify_artifact_entry(name, entry, manifest_path=path)

    non_wind = artifacts.get("non_wind_evidence") or []
    if not isinstance(non_wind, list):
        raise ResearchFreezeError("non_wind_evidence must be an array")
    for index, entry in enumerate(non_wind, 1):
        name = f"non_wind_evidence[{index}]"
        verified[name] = _verify_artifact_entry(name, entry, manifest_path=path)

    constraints_payload = _load_json(verified["run_constraints"][0])
    if not isinstance(constraints_payload, Mapping):
        raise ResearchFreezeError("run_constraints must contain a JSON object")

    candidate_payload = _load_json(verified["candidate_datafields"][0])
    candidate_ids = extract_candidate_datafield_ids(candidate_payload)
    snapshot_paths = tuple(
        artifact_path
        for name, (artifact_path, _) in verified.items()
        if name.startswith("brain_field_snapshot[")
    )
    _require_snapshot_coverage(snapshot_paths, candidate_ids=candidate_ids)
    manifest_candidate_ids = tuple(
        sorted({str(value).strip() for value in payload.get("allowed_datafield_ids") or () if str(value).strip()})
    )
    if candidate_ids != manifest_candidate_ids:
        raise ResearchFreezeError("allowed_datafield_ids do not match frozen candidate_datafields")

    mechanism_payload = _load_json(verified["mechanisms"][0])
    mechanism_fields = extract_mechanism_field_ids(
        mechanism_payload, allowed_datafield_ids=candidate_ids
    )
    mechanism_ids = tuple(mechanism_id for mechanism_id, _ in mechanism_fields)
    manifest_mechanism_ids = tuple(
        sorted({str(value).strip() for value in payload.get("allowed_mechanism_ids") or () if str(value).strip()})
    )
    if mechanism_ids != manifest_mechanism_ids:
        raise ResearchFreezeError("allowed_mechanism_ids do not match frozen mechanism families")

    raw_mapping = payload.get("mechanism_field_ids")
    if not isinstance(raw_mapping, Mapping):
        raise ResearchFreezeError("freeze manifest missing mechanism_field_ids")
    manifest_mapping = tuple(
        sorted(
            (
                str(mechanism_id),
                tuple(sorted({str(value).strip() for value in values if str(value).strip()})),
            )
            for mechanism_id, values in raw_mapping.items()
            if isinstance(values, (list, tuple))
        )
    )
    if mechanism_fields != manifest_mapping:
        raise ResearchFreezeError("mechanism_field_ids do not match frozen mechanism families")

    return ResearchFreeze(
        manifest_path=path,
        manifest_sha256=_sha256_file(path),
        run_id=run_id,
        allowed_mechanism_ids=mechanism_ids,
        allowed_datafield_ids=candidate_ids,
        mechanism_field_ids=mechanism_fields,
        artifact_hashes=tuple(sorted((name, digest) for name, (_, digest) in verified.items())),
    )


def require_research_freeze(
    freeze: ResearchFreeze | None,
    *,
    run_id: str,
    mechanism_ids: Iterable[str],
) -> ResearchFreeze:
    requested = {str(value).strip() for value in mechanism_ids if str(value).strip()}
    if not requested:
        raise ResearchFreezeError("research plan has no mechanism ids")
    if freeze is None:
        raise ResearchFreezeError("research plan requires a validated freeze manifest")
    if freeze.run_id != run_id:
        raise ResearchFreezeError(
            f"freeze run_id mismatch: expected {run_id!r}, got {freeze.run_id!r}"
        )
    missing = sorted(requested - set(freeze.allowed_mechanism_ids))
    if missing:
        raise ResearchFreezeError(
            f"research plan references mechanisms absent from frozen baseline: {missing}"
        )
    return freeze


__all__ = [
    "RESEARCH_FREEZE_SCHEMA",
    "ResearchFreeze",
    "ResearchFreezeError",
    "build_research_freeze_manifest",
    "extract_candidate_datafield_ids",
    "extract_mechanism_field_ids",
    "load_research_freeze",
    "require_research_freeze",
]
