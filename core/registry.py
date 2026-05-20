from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parent
DEFAULT_REGISTRY_PATHS = [
    PACKAGE_ROOT / "resources" / "api_inventory" / "api_inventory_complete.json",
    PACKAGE_ROOT / "resources" / "api_inventory" / "api_inventory.json",
    PACKAGE_ROOT / "api_inventory" / "api_inventory_complete.json",
    PACKAGE_ROOT / "api_inventory" / "api_inventory.json",
    REPO_ROOT / "api_inventory" / "api_inventory_complete.json",
    REPO_ROOT / "api_inventory" / "api_inventory.json",
]


@dataclass(frozen=True)
class Endpoint:
    path: str
    methods: tuple[str, ...]
    description: str
    params: dict[str, Any]
    request_body: Any
    source: tuple[str, ...]
    raw: dict[str, Any]

    @property
    def variables(self) -> list[str]:
        return re.findall(r"{([^{}]+)}", self.path)


class EndpointRegistry:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.base_url = payload.get("base_url", "https://api.worldquantbrain.com")
        endpoints = payload.get("endpoints") or []
        self._endpoints = {
            item["path"]: Endpoint(
                path=item["path"],
                methods=tuple(item.get("methods") or []),
                description=item.get("description") or "",
                params=item.get("params") or {},
                request_body=item.get("request_body"),
                source=tuple(item.get("source") or []),
                raw=item,
            )
            for item in endpoints
        }

    @classmethod
    def load(cls, path: str | None = None) -> "EndpointRegistry":
        candidates = [Path(path)] if path else DEFAULT_REGISTRY_PATHS
        for candidate in candidates:
            if candidate.exists():
                return cls(json.loads(candidate.read_text(encoding="utf-8")))
        searched = ", ".join(str(item) for item in candidates)
        raise FileNotFoundError(f"No API registry found. Searched: {searched}")

    def list(self, prefix: str | None = None) -> list[Endpoint]:
        endpoints = sorted(self._endpoints.values(), key=lambda item: item.path)
        if prefix:
            endpoints = [item for item in endpoints if item.path.startswith(prefix)]
        return endpoints

    def get(self, path: str) -> Endpoint:
        try:
            return self._endpoints[path]
        except KeyError as exc:
            raise KeyError(f"Unknown endpoint path: {path}") from exc

    def stats(self) -> dict[str, Any]:
        method_counts: dict[str, int] = {}
        for endpoint in self._endpoints.values():
            for method in endpoint.methods:
                method_counts[method] = method_counts.get(method, 0) + 1
        return {
            "base_url": self.base_url,
            "endpoint_count": len(self._endpoints),
            "method_counts": dict(sorted(method_counts.items())),
        }
