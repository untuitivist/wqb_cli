from __future__ import annotations

import zlib
from pathlib import Path
from typing import Any

import msgpack

from .paths import DEFAULT_SCOPE_ALL_DATA_PATH, DEFAULT_SCOPE_INFO_PATH


def load_scope_info(path: str | None = None) -> dict[str, Any]:
    target = Path(path) if path else DEFAULT_SCOPE_INFO_PATH
    if not target.exists():
        raise FileNotFoundError(f"Scope info file not found: {target}")
    return msgpack.unpackb(zlib.decompress(target.read_bytes()), raw=False)


def load_scope_pickle(path: str | None = None) -> dict[str, Any]:
    target = Path(path) if path else DEFAULT_SCOPE_ALL_DATA_PATH
    if not target.exists():
        raise FileNotFoundError(f"Scope pickle file not found: {target}")
    import pickle

    with target.open("rb") as handle:
        data = pickle.load(handle)
    if not isinstance(data, dict):
        raise TypeError(f"Expected dict in scope pickle, got {type(data).__name__}")
    return data


def scope_files(info_path: str | None = None, all_data_path: str | None = None) -> dict[str, Any]:
    info = Path(info_path) if info_path else DEFAULT_SCOPE_INFO_PATH
    all_data = Path(all_data_path) if all_data_path else DEFAULT_SCOPE_ALL_DATA_PATH
    return {
        "info_data": _file_status(info),
        "all_data": _file_status(all_data),
        "meaning": {
            "info_data": "Compressed msgpack quick index for scope summaries and ranking.",
            "all_data": "Large pickle with per-scope alpha base/settings/IS/OS dataframes.",
        },
    }


def pickle_scope_summary(data: dict[str, Any], scope: str, *, sample: int) -> dict[str, Any]:
    frames = _scope_frames(data, scope)
    return {
        "scope": scope,
        "tables": {
            name: _frame_summary(frame, sample=sample)
            for name, frame in zip(_TABLE_NAMES, frames, strict=True)
        },
    }


def pickle_alpha_rows(
    data: dict[str, Any],
    scope: str,
    *,
    table: str,
    limit: int,
    offset: int,
    datafield: str | None,
    dataset: str | None,
    columns: list[str] | None,
) -> dict[str, Any]:
    frames = dict(zip(_TABLE_NAMES, _scope_frames(data, scope), strict=True))
    selected_ids = _matching_ids(frames["base"], datafield=datafield, dataset=dataset)
    frame = frames[table]
    if selected_ids is not None and "id" in frame.columns:
        frame = frame[frame["id"].isin(selected_ids)]
    if columns:
        keep = [column for column in columns if column in frame.columns]
        if keep:
            frame = frame[keep]
    total = int(len(frame))
    page = frame.iloc[max(0, offset) : max(0, offset) + max(1, limit)]
    return {
        "scope": scope,
        "table": table,
        "total": total,
        "offset": max(0, offset),
        "limit": max(1, limit),
        "filters": {"datafield": datafield, "dataset": dataset},
        "columns": list(page.columns),
        "rows": [_jsonable_record(record) for record in page.to_dict(orient="records")],
    }


def list_scopes(info: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for scope in sorted(info):
        item = info[scope]
        isos = item.get("isos") or {}
        rows.append(
            {
                "scope": scope,
                "region": scope.rsplit("_", 1)[0],
                "delay": _parse_delay(scope),
                "sub_beg_time": item.get("sub_beg_time"),
                "sub_end_time": item.get("sub_end_time"),
                "total_count": isos.get("total_count"),
                "mean": isos.get("mean"),
                "datafield_count": len(isos.get("datafield") or {}),
                "dataset_count": len(isos.get("dataset") or {}),
                "category_count": len(isos.get("category") or {}),
                "neutralization_count": len((item.get("neutralization") or {}).get("mean") or {}),
            }
        )
    return rows


def show_scope(info: dict[str, Any], scope: str) -> dict[str, Any]:
    item = _scope_item(info, scope)
    isos = item.get("isos") or {}
    neutralization = item.get("neutralization") or {}
    return {
        "scope": scope,
        "region": scope.rsplit("_", 1)[0],
        "delay": _parse_delay(scope),
        "sub_beg_time": item.get("sub_beg_time"),
        "sub_end_time": item.get("sub_end_time"),
        "total_count": isos.get("total_count"),
        "mean": isos.get("mean"),
        "dimensions": {
            "datafield": len(isos.get("datafield") or {}),
            "dataset": len(isos.get("dataset") or {}),
            "category": len(isos.get("category") or {}),
            "neutralization": len(neutralization.get("mean") or {}),
        },
        "neutralization_mean": neutralization.get("mean"),
    }


def top_scope_items(
    info: dict[str, Any],
    scope: str,
    *,
    group: str,
    metric: str,
    limit: int,
    min_count: int,
    descending: bool = True,
) -> list[dict[str, Any]]:
    source = (_scope_item(info, scope).get("isos") or {}).get(group) or {}
    rows = [_flat_metric_row(name, value) for name, value in source.items()]
    rows = [row for row in rows if row.get("count", 0) >= min_count and row.get(metric) is not None]
    rows.sort(key=lambda row: row.get(metric), reverse=descending)
    return rows[: max(1, limit)]


def search_scope_items(
    info: dict[str, Any],
    scope: str,
    *,
    group: str,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    source = (_scope_item(info, scope).get("isos") or {}).get(group) or {}
    needle = query.lower()
    rows = [_flat_metric_row(name, value) for name, value in source.items() if needle in name.lower()]
    rows.sort(key=lambda row: (row.get("count", 0), row.get("sharpe_ratio") or -999999), reverse=True)
    return rows[: max(1, limit)]


def neutralization_rows(
    info: dict[str, Any],
    scope: str,
    *,
    group: str,
    name: str | None,
    metric: str,
    limit: int,
    min_count: int,
) -> list[dict[str, Any]]:
    neutralization = _scope_item(info, scope).get("neutralization") or {}
    source = neutralization.get("mean") if group == "mean" else (neutralization.get(group) or {}).get(name or "")
    if not source:
        return []
    rows = [_flat_metric_row(neutralization_name, value) for neutralization_name, value in source.items()]
    rows = [row for row in rows if row.get("count", 0) >= min_count and row.get(metric) is not None]
    rows.sort(key=lambda row: row.get(metric), reverse=True)
    return rows[: max(1, limit)]


def _scope_item(info: dict[str, Any], scope: str) -> dict[str, Any]:
    try:
        return info[scope]
    except KeyError as exc:
        raise KeyError(f"Unknown scope: {scope}. Available: {', '.join(sorted(info))}") from exc


def _flat_metric_row(name: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"name": name, "value": value}
    return {"name": name, **value}


def _parse_delay(scope: str) -> int | None:
    try:
        return int(scope.rsplit("_", 1)[1])
    except Exception:
        return None


def _file_status(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() else None,
    }


_TABLE_NAMES = ("base", "settings", "is", "os")


def _scope_frames(data: dict[str, Any], scope: str) -> list[Any]:
    try:
        frames = data[scope]
    except KeyError as exc:
        raise KeyError(f"Unknown scope: {scope}. Available: {', '.join(sorted(data))}") from exc
    if not isinstance(frames, list) or len(frames) != len(_TABLE_NAMES):
        raise ValueError(f"Scope {scope} should contain {len(_TABLE_NAMES)} tables: {', '.join(_TABLE_NAMES)}")
    return frames


def _frame_summary(frame: Any, *, sample: int) -> dict[str, Any]:
    return {
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "sample": [_jsonable_record(record) for record in frame.head(max(0, sample)).to_dict(orient="records")],
    }


def _matching_ids(base_frame: Any, *, datafield: str | None, dataset: str | None) -> set[str] | None:
    if not datafield and not dataset:
        return None
    mask = None
    if datafield:
        mask = base_frame["datafield"].apply(lambda values: _contains_item(values, datafield))
    if dataset:
        dataset_mask = base_frame["dataset"].apply(lambda values: _contains_item(values, dataset))
        mask = dataset_mask if mask is None else (mask & dataset_mask)
    if mask is None:
        return None
    return set(base_frame.loc[mask, "id"].astype(str))


def _contains_item(values: Any, target: str) -> bool:
    if isinstance(values, (list, tuple, set)):
        return target in values
    return values == target


def _jsonable_record(record: dict[str, Any]) -> dict[str, Any]:
    return {key: _jsonable_value(value) for key, value in record.items()}


def _jsonable_value(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    if isinstance(value, float) and value != value:
        return None
    if isinstance(value, (list, tuple)):
        return [_jsonable_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable_value(item) for key, item in value.items()}
    return value
