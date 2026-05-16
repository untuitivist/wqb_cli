from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any


def _decorator_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _alpha_decorator(fn: ast.FunctionDef) -> ast.Call | None:
    for deco in fn.decorator_list:
        if _decorator_name(deco) == "alpha":
            return deco if isinstance(deco, ast.Call) else None
    return None


def validate_source(source: str) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {"ok": False, "errors": [f"syntax error: {exc}"], "warnings": warnings}

    alpha_functions: list[tuple[ast.FunctionDef, ast.Call | None]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            deco = _alpha_decorator(node)
            if deco is not None:
                alpha_functions.append((node, deco))

    if len(alpha_functions) != 1:
        errors.append(f"expected exactly one @alpha function, found {len(alpha_functions)}")
        return {"ok": False, "errors": errors, "warnings": warnings}

    fn, deco = alpha_functions[0]
    arg_names = [arg.arg for arg in fn.args.args]
    if arg_names != ["data", "store"]:
        errors.append(f"alpha function args must be exactly ['data', 'store'], got {arg_names}")

    declared_fields: list[str] = []
    has_data_kw = False
    has_lookback_kw = False
    if deco is not None:
        for kw in deco.keywords:
            if kw.arg == "data":
                has_data_kw = True
                if isinstance(kw.value, ast.List):
                    for elt in kw.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            declared_fields.append(elt.value)
            if kw.arg == "lookback":
                has_lookback_kw = True
    if not has_data_kw:
        errors.append("@alpha(...) must declare data=[...]")
    if has_lookback_kw:
        errors.append("lookback must be in settings.lookback, not @alpha(..., lookback=...)")

    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "data":
            errors.append("use data.field attribute access, not data[...]")
            break

    source_flat = source.replace(" ", "")
    if ".astype(np.float32)" not in source_flat and ".astype(\"float32\")" not in source_flat:
        warnings.append("could not find explicit final .astype(np.float32) cast")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "declared_fields": declared_fields,
    }


def _iter_field_records(value: Any):
    if isinstance(value, list):
        for item in value:
            yield from _iter_field_records(item)
        return
    if not isinstance(value, dict):
        return
    if any(key in value for key in ("id", "field_id", "datafield_id")):
        yield value
    for key in ("datafields", "fields", "candidates", "available_datafields", "items"):
        nested = value.get(key)
        if isinstance(nested, (list, dict)):
            yield from _iter_field_records(nested)


def load_field_types(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    field_types: dict[str, str] = {}
    for record in _iter_field_records(payload):
        field_id = record.get("id") or record.get("field_id") or record.get("datafield_id")
        field_type = record.get("type") or record.get("data_type") or record.get("field_type")
        if field_id is not None and field_type is not None:
            field_types[str(field_id)] = str(field_type).upper()
    return field_types


def require_matrix_fields(report: dict[str, Any], field_types: dict[str, str]) -> None:
    errors = report.setdefault("errors", [])
    for field_id in report.get("declared_fields", []):
        if field_id == "universe":
            errors.append("do not include universe in @alpha(data=[...])")
            continue
        field_type = field_types.get(field_id)
        if field_type is None:
            errors.append(f"field {field_id!r} is not present in the allowed field library")
        elif field_type != "MATRIX":
            errors.append(f"field {field_id!r} has type {field_type}, expected MATRIX")
    report["ok"] = not errors


def load_source(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
        if isinstance(payload, dict) and isinstance(payload.get("regular"), str):
            return payload["regular"]
        raise SystemExit("JSON input must be an object with a string 'regular' field")
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a WQB REGULAR PYTHON alpha source string.")
    parser.add_argument("path", help="Path to a .py file or JSON candidate containing regular.")
    parser.add_argument(
        "--fields",
        help="Optional available_datafields.json path used to check declared field types.",
    )
    parser.add_argument(
        "--require-matrix-fields",
        action="store_true",
        help="Require every declared @alpha data field to be present and type MATRIX.",
    )
    args = parser.parse_args()

    report = validate_source(load_source(Path(args.path)))
    if args.require_matrix_fields:
        if not args.fields:
            raise SystemExit("--require-matrix-fields requires --fields")
        require_matrix_fields(report, load_field_types(Path(args.fields)))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
