"""Manifest parsing for QwenPaw extensions."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml

from qwenpaw.extensions.registry import ExtensionRegistry
from qwenpaw.extensions.specs import (
    FeaturePolicy,
    PluginPolicy,
)


_PRODUCT_PATH_KEYS = {
    "working_dir",
    "secret_dir",
    "backup_dir",
    "plugins_dir",
    "custom_channels_dir",
    "media_dir",
    "local_provider_dir",
    "console_static_dir",
}
_PRODUCT_FIELD_MAP = {
    "name": "product_name",
    "version": "product_version",
    "module_alias": "module_alias",
    "cli_name": "cli_name",
    "skill_cli_name": "skill_cli_name",
    "env_prefixes": "env_prefixes",
    "working_dir": "working_dir",
    "secret_dir": "secret_dir",
    "backup_dir": "backup_dir",
    "plugins_dir": "plugins_dir",
    "custom_channels_dir": "custom_channels_dir",
    "media_dir": "media_dir",
    "local_provider_dir": "local_provider_dir",
    "console_static_dir": "console_static_dir",
    "agent_prompt_files": "agent_prompt_files",
}
_LOGGING_FIELD_MAP = {
    "namespace": "namespace",
    "file_path": "file_path",
    "format": "format",
    "level": "level",
}


def _resolve_manifest_relative_path(value: Any, base_dir: Path) -> Any:
    if not isinstance(value, (str, Path)):
        return value
    raw = str(value)
    if not raw or raw.startswith("~"):
        return value
    path = Path(raw)
    if path.is_absolute():
        return value
    return base_dir / path


def _resolve_manifest_relative_paths(data: dict[str, Any], base_dir: Path) -> None:
    product = data.get("product") or {}
    for key in _PRODUCT_PATH_KEYS:
        if key in product:
            product[key] = _resolve_manifest_relative_path(product[key], base_dir)

    logging = data.get("logging") or {}
    if "file_path" in logging:
        logging["file_path"] = _resolve_manifest_relative_path(
            logging["file_path"],
            base_dir,
        )

    plugins = data.get("plugins") or {}
    if "extra_search_paths" in plugins:
        plugins["extra_search_paths"] = [
            _resolve_manifest_relative_path(path, base_dir)
            for path in plugins["extra_search_paths"]
        ]


def apply_manifest_data(
    registry: ExtensionRegistry,
    data: dict[str, Any],
    *,
    base_dir: str | Path | None = None,
) -> None:
    if base_dir is not None:
        _resolve_manifest_relative_paths(data, Path(base_dir).expanduser().resolve())
    product = data.get("product") or {}
    logging = data.get("logging") or {}
    features = data.get("features") or {}
    plugins = data.get("plugins") or {}

    if product:
        product_changes = {
            target: product[source]
            for source, target in _PRODUCT_FIELD_MAP.items()
            if source in product
        }
        if "env_prefixes" in product_changes:
            product_changes["env_prefixes"] = tuple(product_changes["env_prefixes"])
        if "agent_prompt_files" in product_changes:
            product_changes["agent_prompt_files"] = tuple(
                product_changes["agent_prompt_files"]
            )
        registry.update_product(**product_changes)

    if logging:
        registry.update_logging(
            **{
                target: logging[source]
                for source, target in _LOGGING_FIELD_MAP.items()
                if source in logging
            }
        )

    if features:
        registry.configure_features(
            FeaturePolicy(
                disabled_features=features.get("disabled_features"),
                disabled_channels=features.get("disabled_channels"),
                disabled_providers=features.get("disabled_providers"),
                disabled_plugins=features.get("disabled_plugins"),
                allowed_plugins=features.get("allowed_plugins"),
            )
        )

    if plugins:
        registry.configure_plugins(
            PluginPolicy(
                disabled_plugins=plugins.get("disabled_plugins"),
                allowed_plugins=plugins.get("allowed_plugins"),
                extra_search_paths=plugins.get("extra_search_paths"),
            )
        )


def apply_manifest(registry: ExtensionRegistry, path: str | Path) -> None:
    manifest_path = Path(path).expanduser().resolve()
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    apply_manifest_data(registry, data, base_dir=manifest_path.parent)


def apply_manifest_resource(
    registry: ExtensionRegistry,
    package: str,
    resource: str = "manifest.yaml",
) -> None:
    resource_path = files(package).joinpath(*resource.replace("\\", "/").split("/"))
    data = yaml.safe_load(resource_path.read_text(encoding="utf-8")) or {}
    apply_manifest_data(registry, data, base_dir=Path(str(resource_path.parent)))
