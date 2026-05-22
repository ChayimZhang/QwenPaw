"""Manifest parsing for QwenPaw extensions."""

from __future__ import annotations

from pathlib import Path

import yaml

from qwenpaw.extensions.registry import ExtensionRegistry
from qwenpaw.extensions.specs import (
    FeaturePolicy,
    LoggingSpec,
    PluginPolicy,
    ProductSpec,
)


def apply_manifest(registry: ExtensionRegistry, path: str | Path) -> None:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    product = data.get("product") or {}
    logging = data.get("logging") or {}
    features = data.get("features") or {}
    plugins = data.get("plugins") or {}

    if product:
        registry.configure_product(
            ProductSpec(
                product_name=product.get("name", "QwenPaw"),
                product_version=product.get("version"),
                module_alias=product.get("module_alias", "qwenpaw"),
                cli_name=product.get("cli_name", "qwenpaw"),
                skill_cli_name=product.get("skill_cli_name"),
                env_prefixes=tuple(product.get("env_prefixes", ("QWENPAW", "COPAW"))),
                working_dir=product.get("working_dir", "~/.qwenpaw"),
                secret_dir=product.get("secret_dir", "~/.qwenpaw.secret"),
                backup_dir=product.get("backup_dir"),
                plugins_dir=product.get("plugins_dir"),
                custom_channels_dir=product.get("custom_channels_dir"),
                media_dir=product.get("media_dir"),
                local_provider_dir=product.get("local_provider_dir"),
                console_static_dir=product.get("console_static_dir"),
                agent_prompt_files=tuple(
                    product.get(
                        "agent_prompt_files",
                        ("AGENTS.md", "SOUL.md", "PROFILE.md"),
                    )
                ),
            )
        )

    if logging:
        registry.configure_logging(
            LoggingSpec(
                namespace=logging.get("namespace", registry.logging.namespace),
                file_path=logging.get("file_path", registry.logging.file_path),
                format=logging.get("format", registry.logging.format),
                level=logging.get("level", registry.logging.level),
            )
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
