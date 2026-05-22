"""Decorator-style extension registration APIs."""

from __future__ import annotations

from dataclasses import dataclass
from inspect import signature
from typing import Any, Callable

from qwenpaw.extensions.registry import ExtensionRegistry, get_extension_registry
from qwenpaw.extensions.specs import FeaturePolicy, ProductSpec


@dataclass(frozen=True)
class ExtensionContext:
    name: str
    registry: ExtensionRegistry

    @property
    def adapters(self):
        return self.registry.adapters


class ExtensionDecorator:
    def __init__(
        self,
        name: str,
        registry: ExtensionRegistry | None = None,
    ) -> None:
        if not name:
            raise ValueError("extension name is required")
        self.name = name
        self.registry = registry
        self._product_factories: list[Callable[..., ProductSpec]] = []
        self._feature_factories: list[Callable[..., FeaturePolicy]] = []
        self._configurators: list[Callable[..., Any]] = []

    def product(
        self,
        func: Callable[..., ProductSpec],
    ) -> Callable[..., ProductSpec]:
        self._product_factories.append(func)
        return func

    def features(
        self,
        func: Callable[..., FeaturePolicy],
    ) -> Callable[..., FeaturePolicy]:
        self._feature_factories.append(func)
        return func

    def configure(self, func: Callable[..., Any]) -> Callable[..., Any]:
        self._configurators.append(func)
        return func

    def apply(
        self,
        registry: ExtensionRegistry | None = None,
    ) -> ExtensionRegistry:
        target = registry or self.registry or get_extension_registry()
        context = ExtensionContext(name=self.name, registry=target)
        target.extensions.setdefault(self.name, self)
        for factory in self._product_factories:
            target.configure_product(self._invoke(factory, context))
        for factory in self._feature_factories:
            target.configure_features(self._invoke(factory, context))
        for configurator in self._configurators:
            self._invoke(configurator, context)
        return target

    def __call__(
        self,
        registry: ExtensionRegistry | None = None,
    ) -> ExtensionRegistry:
        return self.apply(registry)

    @staticmethod
    def _invoke(func: Callable[..., Any], context: ExtensionContext) -> Any:
        if not signature(func).parameters:
            return func()
        return func(context)


def qwenpaw_extension(
    name: str,
    registry: ExtensionRegistry | None = None,
) -> ExtensionDecorator:
    return ExtensionDecorator(name, registry)
