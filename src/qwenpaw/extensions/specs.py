"""Extension SDK dataclass specifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable


def _normalize_str_set(values: Iterable[str] | None) -> set[str]:
    if values is None:
        return set()
    return {str(value).strip() for value in values if str(value).strip()}


@dataclass(frozen=True)
class FeaturePolicy:
    """Feature and channel allow/deny policy."""

    disabled_features: Iterable[str] | None = field(default_factory=set)
    disabled_channels: Iterable[str] | None = field(default_factory=set)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "disabled_features",
            _normalize_str_set(self.disabled_features),
        )
        object.__setattr__(
            self,
            "disabled_channels",
            _normalize_str_set(self.disabled_channels),
        )

    def is_feature_enabled(self, key: str) -> bool:
        return key not in self.disabled_features

    def is_channel_enabled(self, key: str) -> bool:
        return key not in self.disabled_channels


@dataclass(frozen=True)
class RunnerPatch:
    """Agent runner extension hooks."""

    query_handler_hooks: tuple[Callable[..., Any], ...] = ()
    before_query_stream_hooks: tuple[Callable[..., Any], ...] = ()
    query_stream_message_hooks: tuple[Callable[..., Any], ...] = ()
    after_query_stream_hooks: tuple[Callable[..., Any], ...] = ()


@dataclass(frozen=True)
class BuiltinChannelSpec:
    """Built-in channel registration spec."""

    key: str
    factory: Callable[..., Any]
    config_model: type[Any] | None = None
    required: bool = False
    default_enabled: bool = False
    route_hook: Callable[..., Any] | None = None
    display_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("key is required")


@dataclass(frozen=True)
class ExtensionSpec:
    """Top-level extension SDK spec."""

    name: str
    features: FeaturePolicy = field(default_factory=FeaturePolicy)
    runner_patch: RunnerPatch = field(default_factory=RunnerPatch)
    builtin_channels: tuple[BuiltinChannelSpec, ...] = ()
