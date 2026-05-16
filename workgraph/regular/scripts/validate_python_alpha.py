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

    has_data_kw = False
    has_lookback_kw = False
    if deco is not None:
        for kw in deco.keywords:
            if kw.arg == "data":
                has_data_kw = True
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

    return {"ok": not errors, "errors": errors, "warnings": warnings}


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
    args = parser.parse_args()

    report = validate_source(load_source(Path(args.path)))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
