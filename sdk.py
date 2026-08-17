from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, Protocol

from .core.auth import session_from_cookies
from .core.client import WqbClient
from .core.io import write_json
from .core.registry import EndpointRegistry


class CliPlugin(Protocol):
    """Public command plugin contract for wqb-cli extensions."""

    name: str

    def register(self, subparsers: Any) -> argparse.ArgumentParser:
        """Register the plugin command and return its root parser."""

    def handle(self, args: argparse.Namespace, context: "PluginContext") -> int:
        """Execute a parsed plugin command and return a process exit code."""


@dataclass(frozen=True)
class PluginContext:
    """Stable services exposed to plugins without leaking credentials."""

    registry_path: str | None
    cookies_path: str | None

    def load_registry(self) -> EndpointRegistry:
        return EndpointRegistry.load(self.registry_path)

    def new_client(self, registry: EndpointRegistry | None = None) -> WqbClient:
        resolved_registry = registry or self.load_registry()
        return WqbClient(resolved_registry, session_from_cookies(self.cookies_path))

    def write_json(self, payload: Any, output: str | None = None) -> None:
        write_json(payload, output)


__all__ = ["CliPlugin", "PluginContext"]
