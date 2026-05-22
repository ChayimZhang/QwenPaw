"""Extension registry and scoped registry management."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Iterator

from qwenpaw.extensions.specs import (
    AppPatch,
    CliPatch,
    ExtensionSpec,
    FeaturePolicy,
    LoggingSpec,
    PluginPolicy,
    ProductSpec,
    ProviderPatch,
)


class ExtensionRegistry:
    """In-process extension state shared by SDK adapters."""

    def __init__(self) -> None:
        from qwenpaw.extensions.app import AppExtensionRegistry
        from qwenpaw.extensions.channels import ChannelExtensionRegistry
        from qwenpaw.extensions.cli import CliRegistry
        from qwenpaw.extensions.providers import ProviderExtensionRegistry

        self.product = ProductSpec()
        self.logging = LoggingSpec.from_product(self.product)
        self.features = FeaturePolicy()
        self.plugins = PluginPolicy()
        self.app = AppExtensionRegistry()
        self.channels = ChannelExtensionRegistry()
        self.cli = CliRegistry()
        self.providers = ProviderExtensionRegistry()
        self.extensions: dict[str, object] = {}

    def configure_product(self, spec: ProductSpec) -> None:
        self.product = spec
        self.logging = LoggingSpec.from_product(spec)

    def configure_logging(self, spec: LoggingSpec) -> None:
        self.logging = spec

    def configure_features(self, policy: FeaturePolicy) -> None:
        self.features = FeaturePolicy(
            disabled_features=self.features.disabled_features | policy.disabled_features,
            disabled_channels=self.features.disabled_channels | policy.disabled_channels,
            disabled_providers=self.features.disabled_providers | policy.disabled_providers,
            disabled_plugins=self.features.disabled_plugins | policy.disabled_plugins,
            allowed_plugins=self.features.allowed_plugins | policy.allowed_plugins,
        )

    def configure_plugins(self, policy: PluginPolicy) -> None:
        self.plugins = PluginPolicy(
            disabled_plugins=self.plugins.disabled_plugins | policy.disabled_plugins,
            allowed_plugins=self.plugins.allowed_plugins | policy.allowed_plugins,
            extra_search_paths=(
                *self.plugins.extra_search_paths,
                *policy.extra_search_paths,
            ),
        )
        self.configure_features(
            FeaturePolicy(
                disabled_plugins=self.plugins.disabled_plugins,
                allowed_plugins=self.plugins.allowed_plugins,
            )
        )

    def apply_spec(self, spec: ExtensionSpec) -> None:
        """Apply a declarative extension spec to all extension surfaces."""
        self.extensions[spec.name] = spec

        if spec.product is not None:
            self.configure_product(spec.product)
        if spec.logging is not None:
            self.configure_logging(spec.logging)

        self.configure_features(spec.features)
        self.configure_plugins(spec.plugin_policy)
        self._apply_cli_patch(spec.cli_patch)
        self._apply_app_patch(spec.app_patch)
        for patch in spec.provider_patches:
            self._apply_provider_patch(patch)
        for channel in spec.builtin_channels:
            self.channels.register_builtin(channel)

    def extension(self, name: str) -> "ExtensionBuilder":
        if not name:
            raise ValueError("extension name is required")
        self.extensions.setdefault(name, object())
        return ExtensionBuilder(self, name)

    @property
    def adapters(self):
        from qwenpaw.extensions.adapters import ExtensionAdapters

        return ExtensionAdapters(self)

    def _apply_cli_patch(self, patch: CliPatch) -> None:
        for name, command in patch.add.items():
            self.cli.add_command(name, command.module, command.attribute)
        for name, command in patch.replace.items():
            self.cli.replace_command(name, command.module, command.attribute)
        for name in patch.disable:
            self.cli.disable_command(name)
        for existing, alias in patch.aliases.items():
            self.cli.alias_command(existing, alias)

    def _apply_app_patch(self, patch: AppPatch) -> None:
        for router in patch.routers:
            self.app.add_router(router)
        for hook in patch.startup_hooks:
            self.app.add_startup_hook(hook)
        for hook in patch.shutdown_hooks:
            self.app.add_shutdown_hook(hook)
        for hook in patch.middleware_hooks:
            self.app.add_middleware_hook(hook)
        for hook in patch.before_include_routers:
            self.app.add_before_include_routers_hook(hook)
        for hook in patch.after_include_routers:
            self.app.add_after_include_routers_hook(hook)

    def _apply_provider_patch(self, patch: ProviderPatch) -> None:
        if patch.replace:
            self.providers.replace_provider(patch.provider_id, patch.provider_cls)
        else:
            self.providers.register_provider(patch.provider_id, patch.provider_cls)


class ExtensionBuilder:
    """Fluent extension configuration helper."""

    def __init__(self, registry: ExtensionRegistry, name: str) -> None:
        self.registry = registry
        self.name = name
        self._product_kwargs: dict[str, object] = {
            "product_name": registry.product.product_name,
            "product_version": registry.product.product_version,
            "module_alias": name,
            "cli_name": registry.product.cli_name,
            "skill_cli_name": registry.product.skill_cli_name,
            "env_prefixes": registry.product.env_prefixes,
            "working_dir": registry.product.working_dir,
            "secret_dir": registry.product.secret_dir,
            "console_static_dir": registry.product.console_static_dir,
            "agent_prompt_files": registry.product.agent_prompt_files,
        }

    def product(
        self,
        *,
        name: str,
        version: str | None = None,
        cli_name: str | None = None,
        skill_cli_name: str | None = None,
    ) -> "ExtensionBuilder":
        self._product_kwargs.update(
            {
                "product_name": name,
                "product_version": version,
                "cli_name": cli_name or self.registry.product.cli_name,
                "skill_cli_name": (
                    skill_cli_name
                    if skill_cli_name is not None
                    else self.registry.product.skill_cli_name
                ),
            }
        )
        self._apply_product()
        return self

    def env_prefix(self, prefix: str) -> "ExtensionBuilder":
        normalized = prefix.strip().upper()
        fallback = tuple(
            item for item in self.registry.product.env_prefixes if item != normalized
        )
        self._product_kwargs["env_prefixes"] = (normalized, *fallback)
        self._apply_product()
        return self

    def working_dir(self, path: str | Path) -> "ExtensionBuilder":
        self._product_kwargs["working_dir"] = path
        self._apply_product()
        return self

    def secret_dir(self, path: str | Path) -> "ExtensionBuilder":
        self._product_kwargs["secret_dir"] = path
        self._apply_product()
        return self

    def console_static_dir(self, path: str | Path) -> "ExtensionBuilder":
        self._product_kwargs["console_static_dir"] = path
        self._apply_product()
        return self

    def skill_cli_name(self, name: str) -> "ExtensionBuilder":
        self._product_kwargs["skill_cli_name"] = name
        self._apply_product()
        return self

    def disable_features(self, *names: str) -> "ExtensionBuilder":
        self.registry.configure_features(FeaturePolicy(disabled_features=set(names)))
        return self

    def disable_channels(self, *keys: str) -> "ExtensionBuilder":
        self.registry.configure_features(FeaturePolicy(disabled_channels=set(keys)))
        return self

    def disable_providers(self, *provider_ids: str) -> "ExtensionBuilder":
        self.registry.configure_features(
            FeaturePolicy(disabled_providers=set(provider_ids))
        )
        return self

    def cli_command(
        self,
        name: str,
        module: str,
        attribute: str,
    ) -> "ExtensionBuilder":
        self.registry.cli.add_command(name, module, attribute)
        return self

    def _apply_product(self) -> None:
        self.registry.configure_product(ProductSpec(**self._product_kwargs))


_DEFAULT_REGISTRY = ExtensionRegistry()
_CURRENT_REGISTRY: ContextVar[ExtensionRegistry] = ContextVar(
    "qwenpaw_extension_registry",
    default=_DEFAULT_REGISTRY,
)


def get_extension_registry() -> ExtensionRegistry:
    return _CURRENT_REGISTRY.get()


class LazyRegistryProxy:
    def __getattr__(self, name: str):
        return getattr(get_extension_registry(), name)


extension_registry = LazyRegistryProxy()


@contextmanager
def use_extension_registry(registry: ExtensionRegistry) -> Iterator[ExtensionRegistry]:
    token = _CURRENT_REGISTRY.set(registry)
    try:
        yield registry
    finally:
        _CURRENT_REGISTRY.reset(token)
