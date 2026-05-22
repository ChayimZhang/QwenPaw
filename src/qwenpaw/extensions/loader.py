"""Extension discovery and bootstrap."""

from __future__ import annotations

import os
from collections.abc import Iterable
from importlib.metadata import entry_points
from pathlib import Path
from weakref import WeakSet

from qwenpaw.extensions.config import apply_manifest
from qwenpaw.extensions.env import EnvResolver
from qwenpaw.extensions.registry import ExtensionRegistry, get_extension_registry
from qwenpaw.extensions.specs import ExtensionSpec, ProductSpec

_LOADED_REGISTRIES: WeakSet[ExtensionRegistry] = WeakSet()

_EXTENSION_CONFIG_SUFFIX = "_EXTENSION_CONFIG"


def _bootstrap_config_path(target: ExtensionRegistry) -> str | None:
    if target.product != ProductSpec():
        return EnvResolver(target.product).get("EXTENSION_CONFIG")

    product_candidates: list[tuple[str, str]] = []
    fallback_candidates: list[tuple[str, str]] = []
    for name, value in os.environ.items():
        normalized = name.upper()
        if not normalized.endswith(_EXTENSION_CONFIG_SUFFIX) or not value:
            continue
        prefix = normalized[: -len(_EXTENSION_CONFIG_SUFFIX)]
        if prefix in target.product.env_prefixes:
            fallback_candidates.append((normalized, value))
        else:
            product_candidates.append((normalized, value))

    if product_candidates:
        return sorted(product_candidates)[0][1]

    for name in EnvResolver(target.product).names("EXTENSION_CONFIG"):
        for candidate_name, value in fallback_candidates:
            if candidate_name == name:
                return value
    return None


def _apply_entry_point_result(target: ExtensionRegistry, result: object) -> None:
    if result is None or result is target:
        return
    if isinstance(result, ExtensionSpec):
        target.apply_spec(result)
        return
    if isinstance(result, Iterable) and not isinstance(result, (str, bytes, dict)):
        for item in result:
            if isinstance(item, ExtensionSpec):
                target.apply_spec(item)


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
        resolved_config_path = _bootstrap_config_path(target)
    if resolved_config_path:
        apply_manifest(target, resolved_config_path)

    if include_entry_points:
        for entry_point in entry_points(group="qwenpaw.extensions"):
            register = entry_point.load()
            if isinstance(register, ExtensionSpec):
                _apply_entry_point_result(target, register)
            elif callable(register):
                _apply_entry_point_result(target, register(target))
            else:
                _apply_entry_point_result(target, register)

    _LOADED_REGISTRIES.add(target)
    return target
