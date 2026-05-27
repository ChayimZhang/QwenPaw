"""Feature and plugin policy helpers."""

from __future__ import annotations

from dataclasses import dataclass

from qwenpaw.extensions.registry import ExtensionRegistry, get_extension_registry


@dataclass(frozen=True)
class ExtensionFeature:
    key: str
    description: str


EXTENSION_FEATURES: tuple[ExtensionFeature, ...] = (
    ExtensionFeature("builtin_qa_agent", "Create the packaged QA agent"),
    ExtensionFeature("plugins", "Discover and load plugins"),
    ExtensionFeature("builtin_channels", "Register non-required built-in channels"),
    ExtensionFeature("custom_channels", "Discover channels from custom source dirs"),
)


def _registry_or_current(
    registry: ExtensionRegistry | None = None,
) -> ExtensionRegistry:
    return registry or get_extension_registry()


def is_feature_enabled(
    key: str,
    registry: ExtensionRegistry | None = None,
) -> bool:
    return _registry_or_current(registry).features.is_feature_enabled(key)


def should_create_builtin_qa_agent(
    registry: ExtensionRegistry | None = None,
) -> bool:
    return is_feature_enabled("builtin_qa_agent", registry)


def should_load_builtin_channel(
    registry: ExtensionRegistry | None,
    channel_key: str,
    *,
    required: bool = False,
) -> bool:
    target = _registry_or_current(registry)
    if required:
        return True
    return is_feature_enabled("builtin_channels", target) and (
        target.features.is_channel_enabled(channel_key)
    )


def should_load_custom_channels(
    registry: ExtensionRegistry | None = None,
) -> bool:
    return is_feature_enabled("custom_channels", registry)
