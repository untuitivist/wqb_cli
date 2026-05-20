from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .paths import DEFAULT_ENV_PATH, LEGACY_ENV_PATH


def read_json_file(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def read_dotenv(path: str | None = None) -> dict[str, str]:
    dotenv = Path(path) if path else DEFAULT_ENV_PATH
    if not dotenv.exists() and path is None and LEGACY_ENV_PATH.exists():
        dotenv = LEGACY_ENV_PATH
    if not dotenv.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in dotenv.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def write_json(payload: Any, output: str | None = None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        return
    sys.stdout.buffer.write((text + "\n").encode("utf-8"))


def parse_key_values(items: list[str] | None) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in items or []:
        if "=" not in item:
            raise ValueError(f"Expected KEY=VALUE, got: {item}")
        key, value = item.split("=", 1)
        parsed[key] = value
    return parsed
