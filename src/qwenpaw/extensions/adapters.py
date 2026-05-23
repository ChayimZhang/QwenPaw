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

    def agent_prompt_files(self, *paths: str | Path) -> None:
        self.registry.update_product(agent_prompt_files=tuple(paths))

    def product_version(self, version: str | None) -> None:
        self.registry.update_product(product_version=version)

    def product(self, **changes: Any) -> None:
        self.registry.update_product(**changes)

    def logging(self, **changes: Any) -> None:
        self.registry.update_logging(**changes)

    def skill_service(self, workspace_dir: str | Path):
        from qwenpaw.agents.skill_system.workspace_service import SkillService

        return SkillService(Path(workspace_dir))

    def skill_pool_service(self):
        from qwenpaw.agents.skill_system.pool_service import SkillPoolService

        return SkillPoolService()

    def control_command(
        self,
        handler: Any,
        *,
        priority: str | None = None,
        priority_level: int | None = None,
        priority_registry: Any | None = None,
    ) -> None:
        from qwenpaw.app.runner.control_commands import register_command

        register_command(handler)
        if priority_registry is not None and (
            priority is not None or priority_level is not None
        ):
            command_name = str(handler.command_name)
            command_prefix = (
                command_name if command_name.startswith("/") else f"/{command_name}"
            )
            priority_registry.register_command(
                command_prefix,
                priority=priority,
                priority_level=priority_level,
            )

    def unregister_control_command(
        self,
        command_name: str,
        *,
        priority_registry: Any | None = None,
    ) -> bool:
        from qwenpaw.app.runner.control_commands import unregister_command

        removed = unregister_command(command_name)
        if priority_registry is not None:
            command_prefix = (
                command_name if command_name.startswith("/") else f"/{command_name}"
            )
            priority_registry.unregister_command(command_prefix)
        return removed
