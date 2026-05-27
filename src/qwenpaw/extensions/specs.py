"""Extension SDK dataclass specifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable


def _normalize_path(value: str | Path) -> Path:
    return Path(value).expanduser()


def _normalize_optional_path(value: str | Path | None, default: Path) -> Path:
    if value is None:
        return default
    return _normalize_path(value)


def _normalize_optional_path_or_none(value: str | Path | None) -> Path | None:
    if value is None:
        return None
    return _normalize_path(value)


def _normalize_str_set(values: Iterable[str] | None) -> set[str]:
    if values is None:
        return set()
    return {str(value).strip() for value in values if str(value).strip()}


@dataclass(frozen=True)
class ProductSpec:
    """Product-level extension settings."""

    product_name: str = "QwenPaw"
    module_alias: str = "qwenpaw"
    cli_name: str = "qwenpaw"
    working_dir: str | Path = "~/.qwenpaw"
    secret_dir: str | Path = "~/.qwenpaw.secret"
    product_version: str | None = None
    skill_cli_name: str | None = None
    backup_dir: str | Path | None = None
    plugins_dir: str | Path | None = None
    custom_channels_dir: str | Path | None = None
    media_dir: str | Path | None = None
    local_provider_dir: str | Path | None = None
    console_static_dir: str | Path | None = None
    agent_prompt_files: tuple[str | Path, ...] = ("AGENTS.md", "SOUL.md", "PROFILE.md")

    def __post_init__(self) -> None:
        working_dir = _normalize_path(self.working_dir)
        object.__setattr__(self, "working_dir", working_dir)
        object.__setattr__(self, "secret_dir", _normalize_path(self.secret_dir))
        object.__setattr__(
            self,
            "backup_dir",
            _normalize_optional_path(self.backup_dir, working_dir / "backups"),
        )
        object.__setattr__(
            self,
            "plugins_dir",
            _normalize_optional_path(self.plugins_dir, working_dir / "plugins"),
        )
        object.__setattr__(
            self,
            "custom_channels_dir",
            _normalize_optional_path(
                self.custom_channels_dir,
                working_dir / "custom_channels",
            ),
        )
        object.__setattr__(
            self,
            "media_dir",
            _normalize_optional_path(self.media_dir, working_dir / "media"),
        )
        object.__setattr__(
            self,
            "local_provider_dir",
            _normalize_optional_path(
                self.local_provider_dir,
                working_dir / "local_models",
            ),
        )
        object.__setattr__(
            self,
            "console_static_dir",
            _normalize_optional_path_or_none(self.console_static_dir),
        )
        object.__setattr__(self, "agent_prompt_files", tuple(self.agent_prompt_files))


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
    product: ProductSpec | None = None
    features: FeaturePolicy = field(default_factory=FeaturePolicy)
    runner_patch: RunnerPatch = field(default_factory=RunnerPatch)
    builtin_channels: tuple[BuiltinChannelSpec, ...] = ()
