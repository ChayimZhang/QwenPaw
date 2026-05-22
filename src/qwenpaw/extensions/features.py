"""Feature and plugin policy helpers."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from qwenpaw.extensions.registry import ExtensionRegistry, get_extension_registry


def _registry_or_current(
    registry: ExtensionRegistry | None = None,
) -> ExtensionRegistry:
    return registry or get_extension_registry()


def should_create_builtin_qa_agent(
    registry: ExtensionRegistry | None = None,
) -> bool:
    return _registry_or_current(registry).features.is_feature_enabled(
        "builtin_qa_agent",
    )


def should_load_plugin(
    registry: ExtensionRegistry | None,
    plugin_id: str,
) -> bool:
    return _registry_or_current(registry).features.is_plugin_enabled(plugin_id)


def iter_plugin_search_paths(
    registry: ExtensionRegistry | None = None,
) -> Iterable[Path]:
    yield from _registry_or_current(registry).plugins.extra_search_paths
