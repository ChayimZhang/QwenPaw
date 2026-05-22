"""Extension registry and scoped registry management."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Iterator

from qwenpaw.extensions.specs import (
    FeaturePolicy,
    LoggingSpec,
    PluginPolicy,
    ProductSpec,
)


class ExtensionRegistry:
    """In-process extension state shared by SDK adapters."""

    def __init__(self) -> None:
        from qwenpaw.extensions.app import AppExtensionRegistry
        from qwenpaw.extensions.cli import CliRegistry

        self.product = ProductSpec()
        self.logging = LoggingSpec.from_product(self.product)
        self.features = FeaturePolicy()
        self.plugins = PluginPolicy()
        self.app = AppExtensionRegistry()
        self.cli = CliRegistry()
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

    def extension(self, name: str) -> "ExtensionBuilder":
        if not name:
            raise ValueError("extension name is required")
        self.extensions.setdefault(name, object())
        return ExtensionBuilder(self, name)


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
    ) -> "ExtensionBuilder":
        self._product_kwargs.update(
            {
                "product_name": name,
                "product_version": version,
                "cli_name": cli_name or self.registry.product.cli_name,
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


@contextmanager
def use_extension_registry(registry: ExtensionRegistry) -> Iterator[ExtensionRegistry]:
    token = _CURRENT_REGISTRY.set(registry)
    try:
        yield registry
    finally:
        _CURRENT_REGISTRY.reset(token)
