"""Extension registry and scoped registry management."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from qwenpaw.extensions.specs import (
    ExtensionSpec,
    FeaturePolicy,
    RunnerPatch,
)


class ExtensionRegistry:
    """In-process extension state shared by SDK adapters."""

    def __init__(self) -> None:
        from qwenpaw.extensions.channels import ChannelExtensionRegistry
        from qwenpaw.extensions.runner import RunnerExtensionRegistry

        self.features = FeaturePolicy()
        self.channels = ChannelExtensionRegistry()
        self.runner = RunnerExtensionRegistry()
        self.extensions: dict[str, object] = {}

    def configure_features(self, policy: FeaturePolicy) -> None:
        self.features = FeaturePolicy(
            disabled_features=self.features.disabled_features | policy.disabled_features,
            disabled_channels=self.features.disabled_channels | policy.disabled_channels,
        )

    def apply_spec(self, spec: ExtensionSpec) -> None:
        """Apply a declarative extension spec to all extension surfaces."""
        self.extensions[spec.name] = spec

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


class ExtensionBuilder:
    """Fluent extension configuration helper."""

    def __init__(self, registry: ExtensionRegistry, name: str) -> None:
        self.registry = registry
        self.name = name

    def disable_features(self, *names: str) -> "ExtensionBuilder":
        self.registry.configure_features(FeaturePolicy(disabled_features=set(names)))
        return self

    def disable_channels(self, *keys: str) -> "ExtensionBuilder":
        self.registry.configure_features(FeaturePolicy(disabled_channels=set(keys)))
        return self


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
