from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .paths import DEFAULT_CONFIG_PATH


DEFAULT_CONFIG: dict[str, Any] = {
    "auth": {
        "email": "",
        "keyring_service": "wqb-cli",
        "keyring_username": "",
    },
    "defaults": {
        "instrumentType": "EQUITY",
        "region": "USA",
        "universe": "TOP3000",
        "delay": 1,
        "language": "FASTEXPR",
    },
    "simulation": {
        "regular_concurrency_non_glb": 8,
        "regular_concurrency_glb": 4,
        "super_concurrency": 3,
        "fastexpr_multi_batch_non_glb": 10,
        "fastexpr_multi_batch_glb": 5,
        "max_wait_seconds": 900,
    },
}


def config_path(path: str | None = None) -> Path:
    return Path(path) if path else DEFAULT_CONFIG_PATH


def load_config(path: str | None = None) -> dict[str, Any]:
    target = config_path(path)
    config = deepcopy(DEFAULT_CONFIG)
    if not target.exists():
        return config
    loaded = json.loads(target.read_text(encoding="utf-8-sig"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Config file must contain a JSON object: {target}")
    return _deep_merge(config, loaded)


def save_config(config: dict[str, Any], path: str | None = None) -> Path:
    target = config_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def init_config(path: str | None = None, *, force: bool = False) -> dict[str, Any]:
    target = config_path(path)
    if target.exists() and not force:
        return {"created": False, "path": str(target), "config": load_config(path)}
    config = deepcopy(DEFAULT_CONFIG)
    save_config(config, path)
    return {"created": True, "path": str(target), "config": config}


def get_config_value(config: dict[str, Any], key: str) -> Any:
    current: Any = config
    for part in _split_key(key):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(key)
        current = current[part]
    return current


def set_config_value(config: dict[str, Any], key: str, value: Any) -> dict[str, Any]:
    parts = _split_key(key)
    current = config
    for part in parts[:-1]:
        child = current.get(part)
        if child is None:
            child = {}
            current[part] = child
        if not isinstance(child, dict):
            raise ValueError(f"Cannot set nested key below non-object: {part}")
        current = child
    current[parts[-1]] = value
    return config


def _split_key(key: str) -> list[str]:
    parts = [part for part in key.split(".") if part]
    if not parts:
        raise ValueError("Config key must not be empty")
    return parts


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def parse_config_value(text: str) -> Any:
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text

