from __future__ import annotations

from importlib import metadata
from typing import Any, Iterable

from ..sdk import CliPlugin


PLUGIN_ENTRY_POINT_GROUP = "wqb_cli.plugins"


class PluginLoadError(RuntimeError):
    pass


def discover_plugins(builtin: Iterable[CliPlugin] = ()) -> list[CliPlugin]:
    """Load built-in and installed command plugins in deterministic order."""

    plugins = list(builtin)
    entry_points = metadata.entry_points()
    selected = entry_points.select(group=PLUGIN_ENTRY_POINT_GROUP)
    for entry_point in sorted(selected, key=lambda item: item.name):
        try:
            loaded = entry_point.load()
            plugin = loaded() if isinstance(loaded, type) else loaded
        except Exception as exc:
            raise PluginLoadError(
                f"Failed to load plugin {entry_point.name!r}: {type(exc).__name__}: {exc}"
            ) from exc
        plugins.append(plugin)
    _validate_plugins(plugins)
    return plugins


def register_plugins(subparsers: Any, plugins: Iterable[CliPlugin]) -> None:
    """Register plugins and bind their handlers to parsed namespaces."""

    resolved = list(plugins)
    _validate_plugins(resolved)
    for plugin in resolved:
        root_parser = plugin.register(subparsers)
        root_parser.set_defaults(_wqb_plugin=plugin)


def _validate_plugins(plugins: Iterable[CliPlugin]) -> None:
    names: set[str] = set()
    for plugin in plugins:
        name = getattr(plugin, "name", None)
        if not isinstance(name, str) or not name.strip():
            raise PluginLoadError("Plugin must expose a non-empty string name")
        if name in names:
            raise PluginLoadError(f"Duplicate plugin name: {name}")
        if not callable(getattr(plugin, "register", None)):
            raise PluginLoadError(f"Plugin {name!r} has no register() method")
        if not callable(getattr(plugin, "handle", None)):
            raise PluginLoadError(f"Plugin {name!r} has no handle() method")
        names.add(name)


__all__ = [
    "PLUGIN_ENTRY_POINT_GROUP",
    "PluginLoadError",
    "discover_plugins",
    "register_plugins",
]
