"""Extension registry and scoped registry management."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterator

from qwenpaw.extensions.specs import (
    AppPatch,
    CliPatch,
    ExtensionSpec,
    FeaturePolicy,
    LoggingSpec,
    PluginPolicy,
    ProductSpec,
    ProviderPatch,
    RunnerPatch,
)


_PRODUCT_DERIVED_PATHS = {
    "backup_dir": "backups",
    "plugins_dir": "plugins",
    "custom_channels_dir": "custom_channels",
    "media_dir": "media",
    "local_provider_dir": "local_models",
}


class ExtensionRegistry:
    """In-process extension state shared by SDK adapters."""

    def __init__(self) -> None:
        from qwenpaw.extensions.app import AppExtensionRegistry
        from qwenpaw.extensions.channels import ChannelExtensionRegistry
        from qwenpaw.extensions.cli import CliRegistry
        from qwenpaw.extensions.providers import ProviderExtensionRegistry
        from qwenpaw.extensions.runner import RunnerExtensionRegistry

        self.product = ProductSpec()
        self.logging = LoggingSpec.from_product(self.product)
        self.features = FeaturePolicy()
        self.plugins = PluginPolicy()
        self.app = AppExtensionRegistry()
        self.channels = ChannelExtensionRegistry()
        self.cli = CliRegistry()
        self.providers = ProviderExtensionRegistry()
        self.runner = RunnerExtensionRegistry()
        self.extensions: dict[str, object] = {}

    def configure_product(self, spec: ProductSpec) -> None:
        self.product = spec
        self.logging = LoggingSpec.from_product(spec)

    def update_product(self, **changes: Any) -> ProductSpec:
        """Incrementally update product fields without resetting logging."""
        if not changes:
            return self.product
        product = self.product
        old_working_dir = product.working_dir
        next_changes = dict(changes)
        if "working_dir" in next_changes:
            for field_name, default_child in _PRODUCT_DERIVED_PATHS.items():
                if field_name in next_changes:
                    continue
                current = getattr(product, field_name)
                if current == old_working_dir / default_child:
                    next_changes[field_name] = None
        self.product = replace(product, **next_changes)
        return self.product

    def configure_logging(self, spec: LoggingSpec) -> None:
        self.logging = spec

    def update_logging(self, **changes: Any) -> LoggingSpec:
        """Incrementally update logging fields."""
        if not changes:
            return self.logging
        self.logging = replace(self.logging, **changes)
        return self.logging

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
        self._apply_runner_patch(spec.runner_patch)
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
        for item in patch.routers:
            router, prefix, tags = _normalize_router_patch(item)
            self.app.add_router(router, prefix=prefix, tags=tags)
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

    def _apply_runner_patch(self, patch: RunnerPatch) -> None:
        for hook in patch.query_handler_hooks:
            self.runner.add_query_handler_hook(hook)
        for hook in patch.before_query_stream_hooks:
            self.runner.add_before_query_stream_hook(hook)
        for hook in patch.query_stream_message_hooks:
            self.runner.add_query_stream_message_hook(hook)
        for hook in patch.after_query_stream_hooks:
            self.runner.add_after_query_stream_hook(hook)

    def _apply_provider_patch(self, patch: ProviderPatch) -> None:
        if patch.replace:
            self.providers.replace_provider(patch.provider_id, patch.provider_cls)
        else:
            self.providers.register_provider(patch.provider_id, patch.provider_cls)


def _normalize_router_patch(item: Any) -> tuple[Any, str, list[str] | None]:
    if hasattr(item, "router"):
        return (
            item.router,
            getattr(item, "prefix", "") or "",
            getattr(item, "tags", None),
        )
    if isinstance(item, tuple):
        if len(item) == 3:
            router, prefix, tags = item
            return router, prefix or "", list(tags) if tags is not None else None
        if len(item) == 2:
            router, prefix = item
            return router, prefix or "", None
    return item, "", None


def _explicit_product_path(path: Path, default: Path) -> Path | None:
    return None if path == default else path


class ExtensionBuilder:
    """Fluent extension configuration helper."""

    def __init__(self, registry: ExtensionRegistry, name: str) -> None:
        self.registry = registry
        self.name = name
        product = registry.product
        self._product_kwargs: dict[str, object] = {
            "product_name": product.product_name,
            "product_version": product.product_version,
            "module_alias": name,
            "cli_name": product.cli_name,
            "skill_cli_name": product.skill_cli_name,
            "env_prefixes": product.env_prefixes,
            "working_dir": product.working_dir,
            "secret_dir": product.secret_dir,
            "backup_dir": _explicit_product_path(
                product.backup_dir,
                product.working_dir / "backups",
            ),
            "plugins_dir": _explicit_product_path(
                product.plugins_dir,
                product.working_dir / "plugins",
            ),
            "custom_channels_dir": _explicit_product_path(
                product.custom_channels_dir,
                product.working_dir / "custom_channels",
            ),
            "media_dir": _explicit_product_path(
                product.media_dir,
                product.working_dir / "media",
            ),
            "local_provider_dir": _explicit_product_path(
                product.local_provider_dir,
                product.working_dir / "local_models",
            ),
            "console_static_dir": product.console_static_dir,
            "agent_prompt_files": product.agent_prompt_files,
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
