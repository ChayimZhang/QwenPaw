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


def _normalize_path_tuple(values: Iterable[str | Path]) -> tuple[Path, ...]:
    return tuple(_normalize_path(value) for value in values)


def _normalize_optional_path_or_none(value: str | Path | None) -> Path | None:
    if value is None:
        return None
    return _normalize_path(value)


def _normalize_str_set(values: Iterable[str]) -> set[str]:
    return set(values)


@dataclass
class ProductSpec:
    """Product-level extension settings."""

    product_name: str = "QwenPaw"
    module_alias: str = "qwenpaw"
    cli_name: str = "qwenpaw"
    env_prefixes: tuple[str, ...] = ("QWENPAW", "COPAW")
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
        if not self.env_prefixes:
            raise ValueError("env_prefixes must contain at least one prefix")
        for prefix in self.env_prefixes:
            if not isinstance(prefix, str) or not prefix or prefix.upper() != prefix:
                raise ValueError("env_prefixes must be non-empty uppercase strings")

        working_dir = _normalize_path(self.working_dir)
        self.working_dir = working_dir
        self.secret_dir = _normalize_path(self.secret_dir)
        self.env_prefixes = tuple(self.env_prefixes)
        self.backup_dir = _normalize_optional_path(
            self.backup_dir,
            working_dir / "backups",
        )
        self.plugins_dir = _normalize_optional_path(
            self.plugins_dir,
            working_dir / "plugins",
        )
        self.custom_channels_dir = _normalize_optional_path(
            self.custom_channels_dir,
            working_dir / "custom_channels",
        )
        self.media_dir = _normalize_optional_path(self.media_dir, working_dir / "media")
        self.local_provider_dir = _normalize_optional_path(
            self.local_provider_dir,
            working_dir / "local_models",
        )
        self.console_static_dir = _normalize_optional_path_or_none(
            self.console_static_dir,
        )
        self.agent_prompt_files = tuple(self.agent_prompt_files)


@dataclass
class LoggingSpec:
    """Logging configuration exposed to extensions."""

    namespace: str
    file_path: str | Path
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    level: str = "INFO"
    handler_factory: Callable[..., Any] | None = None

    def __post_init__(self) -> None:
        self.file_path = _normalize_path(self.file_path)

    @classmethod
    def from_product(cls, product: ProductSpec) -> "LoggingSpec":
        namespace = product.product_name.lower().replace(" ", "")
        return cls(namespace=namespace, file_path=product.working_dir / f"{namespace}.log")


@dataclass
class FeaturePolicy:
    """Feature, channel, provider, and plugin allow/deny policy."""

    disabled_features: Iterable[str] = field(default_factory=set)
    disabled_channels: Iterable[str] = field(default_factory=set)
    disabled_providers: Iterable[str] = field(default_factory=set)
    disabled_plugins: Iterable[str] = field(default_factory=set)
    allowed_plugins: Iterable[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.disabled_features = _normalize_str_set(self.disabled_features)
        self.disabled_channels = _normalize_str_set(self.disabled_channels)
        self.disabled_providers = _normalize_str_set(self.disabled_providers)
        self.disabled_plugins = _normalize_str_set(self.disabled_plugins)
        self.allowed_plugins = _normalize_str_set(self.allowed_plugins)

    def is_feature_enabled(self, key: str) -> bool:
        return key not in self.disabled_features

    def is_channel_enabled(self, key: str) -> bool:
        return key not in self.disabled_channels

    def is_provider_enabled(self, key: str) -> bool:
        return key not in self.disabled_providers

    def is_plugin_enabled(self, key: str) -> bool:
        if key in self.disabled_plugins:
            return False
        if self.allowed_plugins and key not in self.allowed_plugins:
            return False
        return True


@dataclass
class PluginPolicy:
    """Plugin discovery and enablement policy."""

    disabled_plugins: Iterable[str] = field(default_factory=set)
    allowed_plugins: Iterable[str] = field(default_factory=set)
    extra_search_paths: Iterable[str | Path] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        self.disabled_plugins = _normalize_str_set(self.disabled_plugins)
        self.allowed_plugins = _normalize_str_set(self.allowed_plugins)
        self.extra_search_paths = _normalize_path_tuple(self.extra_search_paths)


@dataclass
class CliCommandPatch:
    """Describes one CLI command extension."""

    name: str
    module: str
    attribute: str


@dataclass
class CliPatch:
    """CLI extension patch set."""

    add: tuple[CliCommandPatch, ...] = ()
    replace: tuple[CliCommandPatch, ...] = ()
    disable: tuple[str, ...] = ()
    aliases: dict[str, str] = field(default_factory=dict)


@dataclass
class AppPatch:
    """Application extension hooks."""

    routers: tuple[Any, ...] = ()
    startup_hooks: tuple[Callable[..., Any], ...] = ()
    shutdown_hooks: tuple[Callable[..., Any], ...] = ()
    middleware_hooks: tuple[Callable[..., Any], ...] = ()
    before_include_routers: tuple[Callable[..., Any], ...] = ()
    after_include_routers: tuple[Callable[..., Any], ...] = ()


@dataclass
class ProviderPatch:
    """Provider registration patch."""

    provider_id: str
    provider_cls: type[Any]
    replace: bool = False


@dataclass
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


@dataclass
class ExtensionSpec:
    """Top-level extension SDK spec."""

    name: str
    product: ProductSpec | None = None
    logging: LoggingSpec | None = None
    features: FeaturePolicy = field(default_factory=FeaturePolicy)
    plugin_policy: PluginPolicy = field(default_factory=PluginPolicy)
    cli_patch: CliPatch = field(default_factory=CliPatch)
    app_patch: AppPatch = field(default_factory=AppPatch)
    provider_patches: tuple[ProviderPatch, ...] = ()
    builtin_channels: tuple[BuiltinChannelSpec, ...] = ()

    def __post_init__(self) -> None:
        if self.logging is None and self.product is not None:
            self.logging = LoggingSpec.from_product(self.product)
