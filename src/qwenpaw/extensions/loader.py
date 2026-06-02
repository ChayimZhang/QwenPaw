"""Extension discovery and bootstrap."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable
from importlib.metadata import entry_points
from pathlib import Path
from weakref import WeakSet

import yaml

from qwenpaw.extensions.config import apply_manifest, apply_manifest_resource
from qwenpaw.extensions.registry import ExtensionRegistry, get_extension_registry
from qwenpaw.extensions.specs import ExtensionSpec

_LOADED_REGISTRIES: WeakSet[ExtensionRegistry] = WeakSet()

_EXTENSION_MANIFEST_ENTRY_POINT_GROUP = "qwenpaw.extension_manifests"
_AUTO_MANIFEST_NAMES = (
    "manifest.yaml",
    "manifest.yml",
    "extension.yaml",
    "extension.yml",
    "qwenpaw-extension.yaml",
    "qwenpaw-extension.yml",
)
_MANIFEST_ROOT_KEYS = {"features"}


def _iter_manifest_search_dirs(search_paths: Iterable[str | Path] | None) -> Iterable[Path]:
    seen: set[Path] = set()

    def _yield_upwards(path: Path) -> Iterable[Path]:
        if path.is_file():
            path = path.parent
        for candidate in (path, *path.parents):
            if candidate not in seen:
                seen.add(candidate)
                yield candidate

    if search_paths is None:
        current = Path.cwd().resolve()
        yield from _yield_upwards(current)
        executable = Path(sys.argv[0]).expanduser()
        if executable:
            if not executable.is_absolute():
                executable = (current / executable).resolve()
            yield from _yield_upwards(executable)
        return

    for item in search_paths:
        path = Path(item).expanduser().resolve()
        yield from _yield_upwards(path)


def _looks_like_extension_manifest(path: Path) -> bool:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError, UnicodeDecodeError):
        return False
    return isinstance(data, dict) and bool(_MANIFEST_ROOT_KEYS.intersection(data))


def discover_extension_manifest(
    search_paths: Iterable[str | Path] | None = None,
) -> Path | None:
    """Find the nearest extension manifest in the current project tree."""

    for directory in _iter_manifest_search_dirs(search_paths):
        for name in _AUTO_MANIFEST_NAMES:
            candidate = directory / name
            if candidate.is_file() and _looks_like_extension_manifest(candidate):
                return candidate
    return None


def _bootstrap_config_path(target: ExtensionRegistry) -> str | None:
    _ = target
    for name in ("QWENPAW_EXTENSION_CONFIG", "COPAW_EXTENSION_CONFIG"):
        value = os.environ.get(name)
        if value:
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


def _apply_manifest_entry_points(target: ExtensionRegistry) -> None:
    for entry_point in entry_points(group=_EXTENSION_MANIFEST_ENTRY_POINT_GROUP):
        package = entry_point.module
        resource = entry_point.attr or "manifest.yaml"
        apply_manifest_resource(target, package, resource)


def _apply_python_entry_points(target: ExtensionRegistry) -> None:
    for entry_point in entry_points(group="qwenpaw.extensions"):
        register = entry_point.load()
        if isinstance(register, ExtensionSpec):
            _apply_entry_point_result(target, register)
        elif callable(register):
            _apply_entry_point_result(target, register(target))
        else:
            _apply_entry_point_result(target, register)


def load_extensions(
    *,
    registry: ExtensionRegistry | None = None,
    config_path: str | Path | None = None,
    auto_discover: bool = True,
    manifest_search_paths: Iterable[str | Path] | None = None,
    include_entry_points: bool = True,
    force: bool = False,
) -> ExtensionRegistry:
    target = registry or get_extension_registry()
    if target in _LOADED_REGISTRIES and not force:
        return target

    resolved_config_path = config_path
    if resolved_config_path is None:
        resolved_config_path = _bootstrap_config_path(target)
    if resolved_config_path is None and auto_discover:
        resolved_config_path = discover_extension_manifest(manifest_search_paths)
    if include_entry_points:
        _apply_manifest_entry_points(target)

    if resolved_config_path:
        apply_manifest(target, resolved_config_path)

    if include_entry_points:
        _apply_python_entry_points(target)

    _LOADED_REGISTRIES.add(target)
    return target
