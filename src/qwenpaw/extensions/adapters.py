"""Unified facade over QwenPaw extension surfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from qwenpaw.extensions.registry import ExtensionRegistry, get_extension_registry
from qwenpaw.extensions.specs import BuiltinChannelSpec, FeaturePolicy, PluginPolicy


class ExtensionAdapters:
    def __init__(self, registry: ExtensionRegistry | None = None) -> None:
        self.registry = registry or get_extension_registry()

    def router(
        self,
        router: Any,
        prefix: str = "",
        tags: list[str] | None = None,
    ) -> None:
        self.registry.app.add_router(router, prefix=prefix, tags=tags)

    def startup_hook(self, hook: Any) -> None:
        self.registry.app.add_startup_hook(hook)

    def shutdown_hook(self, hook: Any) -> None:
        self.registry.app.add_shutdown_hook(hook)

    def middleware_hook(self, hook: Any) -> None:
        self.registry.app.add_middleware_hook(hook)

    def provider(self, provider_id: str, provider: Any) -> None:
        self.registry.providers.register_provider(provider_id, provider)

    def replace_provider(self, provider_id: str, provider: Any) -> None:
        self.registry.providers.replace_provider(provider_id, provider)

    def builtin_channel(self, spec: BuiltinChannelSpec) -> None:
        self.registry.channels.register_builtin(spec)

    def replace_builtin_channel(self, spec: BuiltinChannelSpec) -> None:
        self.registry.channels.replace_builtin(spec)

    def custom_channel_source(self, path: str | Path) -> None:
        self.registry.channels.add_custom_source(path)

    def cli_command(
        self,
        name: str,
        module: str,
        attribute: str,
        label: str | None = None,
    ) -> None:
        self.registry.cli.add_command(name, module, attribute, label)

    def replace_cli_command(
        self,
        name: str,
        module: str,
        attribute: str,
        label: str | None = None,
    ) -> None:
        self.registry.cli.replace_command(name, module, attribute, label)

    def disable_cli_command(self, name: str) -> None:
        self.registry.cli.disable_command(name)

    def cli_alias(self, existing: str, alias: str) -> None:
        self.registry.cli.alias_command(existing, alias)

    def disable_feature(self, name: str) -> None:
        self.registry.configure_features(FeaturePolicy(disabled_features={name}))

    def disable_channel(self, key: str) -> None:
        self.registry.configure_features(FeaturePolicy(disabled_channels={key}))

    def disable_provider(self, provider_id: str) -> None:
        self.registry.configure_features(
            FeaturePolicy(disabled_providers={provider_id})
        )

    def disable_plugin(self, plugin_id: str) -> None:
        self.registry.configure_plugins(PluginPolicy(disabled_plugins={plugin_id}))

    def allow_plugin(self, plugin_id: str) -> None:
        self.registry.configure_plugins(PluginPolicy(allowed_plugins={plugin_id}))

    def plugin_search_path(self, path: str | Path) -> None:
        self.registry.configure_plugins(PluginPolicy(extra_search_paths=(path,)))
