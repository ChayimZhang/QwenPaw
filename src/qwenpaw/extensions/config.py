"""Manifest parsing for QwenPaw extensions."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml

from qwenpaw.extensions.registry import ExtensionRegistry
from qwenpaw.extensions.specs import FeaturePolicy


def apply_manifest_data(
    registry: ExtensionRegistry,
    data: dict[str, Any],
    *,
    base_dir: str | Path | None = None,
) -> None:
    _ = base_dir
    features = data.get("features") or {}

    if features:
        registry.configure_features(
            FeaturePolicy(
                disabled_features=features.get("disabled_features"),
                disabled_channels=features.get("disabled_channels"),
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
