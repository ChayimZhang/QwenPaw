"""Extension discovery and bootstrap."""

from __future__ import annotations

from importlib.metadata import entry_points
from pathlib import Path
from weakref import WeakSet

from qwenpaw.extensions.config import apply_manifest
from qwenpaw.extensions.env import EnvResolver
from qwenpaw.extensions.registry import ExtensionRegistry, get_extension_registry

_LOADED_REGISTRIES: WeakSet[ExtensionRegistry] = WeakSet()


def load_extensions(
    *,
    registry: ExtensionRegistry | None = None,
    config_path: str | Path | None = None,
    include_entry_points: bool = True,
    force: bool = False,
) -> ExtensionRegistry:
    target = registry or get_extension_registry()
    if target in _LOADED_REGISTRIES and not force:
        return target

    resolved_config_path = config_path
    if resolved_config_path is None:
        resolved_config_path = EnvResolver(target.product).get("EXTENSION_CONFIG")
    if resolved_config_path:
        apply_manifest(target, resolved_config_path)

    if include_entry_points:
        for entry_point in entry_points(group="qwenpaw.extensions"):
            register = entry_point.load()
            register(target)

    _LOADED_REGISTRIES.add(target)
    return target
