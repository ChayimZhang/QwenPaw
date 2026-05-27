"""Extension registry and scoped registry management."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterator

from qwenpaw.extensions.specs import (
    ExtensionSpec,
    FeaturePolicy,
    ProductSpec,
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
        from qwenpaw.extensions.channels import ChannelExtensionRegistry
        from qwenpaw.extensions.runner import RunnerExtensionRegistry

        self.product = ProductSpec()
        self.features = FeaturePolicy()
        self.channels = ChannelExtensionRegistry()
        self.runner = RunnerExtensionRegistry()
        self.extensions: dict[str, object] = {}

    def configure_product(self, spec: ProductSpec) -> None:
        self.product = spec

    def update_product(self, **changes: Any) -> ProductSpec:
        """Incrementally update product fields."""
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

    def configure_features(self, policy: FeaturePolicy) -> None:
        self.features = FeaturePolicy(
            disabled_features=self.features.disabled_features | policy.disabled_features,
            disabled_channels=self.features.disabled_channels | policy.disabled_channels,
        )

    def apply_spec(self, spec: ExtensionSpec) -> None:
        """Apply a declarative extension spec to all extension surfaces."""
        self.extensions[spec.name] = spec

        if spec.product is not None:
            self.configure_product(spec.product)

        self.configure_features(spec.features)
        self._apply_runner_patch(spec.runner_patch)
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

    def _apply_runner_patch(self, patch: RunnerPatch) -> None:
        for hook in patch.query_handler_hooks:
            self.runner.add_query_handler_hook(hook)
        for hook in patch.before_query_stream_hooks:
            self.runner.add_before_query_stream_hook(hook)
        for hook in patch.query_stream_message_hooks:
            self.runner.add_query_stream_message_hook(hook)
        for hook in patch.after_query_stream_hooks:
            self.runner.add_after_query_stream_hook(hook)


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
