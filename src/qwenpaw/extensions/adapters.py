"""Unified facade over QwenPaw extension surfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from qwenpaw.extensions.registry import ExtensionRegistry, get_extension_registry
from qwenpaw.extensions.specs import BuiltinChannelSpec, FeaturePolicy


class ExtensionAdapters:
    def __init__(self, registry: ExtensionRegistry | None = None) -> None:
        self.registry = registry or get_extension_registry()

    def builtin_channel(self, spec: BuiltinChannelSpec) -> None:
        self.registry.channels.register_builtin(spec)

    def replace_builtin_channel(self, spec: BuiltinChannelSpec) -> None:
        self.registry.channels.replace_builtin(spec)

    def custom_channel_source(self, path: str | Path) -> None:
        self.registry.channels.add_custom_source(path)

    def disable_feature(self, name: str) -> None:
        self.registry.configure_features(FeaturePolicy(disabled_features={name}))

    def disable_channel(self, key: str) -> None:
        self.registry.configure_features(FeaturePolicy(disabled_channels={key}))

    def agent_prompt_files(self, *paths: str | Path) -> None:
        self.registry.update_product(agent_prompt_files=tuple(paths))

    def product_version(self, version: str | None) -> None:
        self.registry.update_product(product_version=version)

    def product(self, **changes: Any) -> None:
        self.registry.update_product(**changes)

    def before_query_stream_hook(self, hook: Any) -> None:
        self.registry.runner.add_before_query_stream_hook(hook)

    def query_stream_message_hook(self, hook: Any) -> None:
        self.registry.runner.add_query_stream_message_hook(hook)

    def after_query_stream_hook(self, hook: Any) -> None:
        self.registry.runner.add_after_query_stream_hook(hook)

    def query_handler_hook(self, hook: Any) -> None:
        self.registry.runner.add_query_handler_hook(hook)
