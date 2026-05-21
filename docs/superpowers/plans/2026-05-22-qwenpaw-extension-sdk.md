# QwenPaw Extension SDK Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a general `qwenpaw.extensions` SDK that lets downstream products brand, configure, disable, replace, and extend QwenPaw through stable APIs while keeping upstream-facing changes narrow.

**Architecture:** Add a focused internal extension layer under `src/qwenpaw/extensions/` and change existing hardcoded entry points to read from that layer. The SDK exposes explicit registry APIs, decorators, a fluent builder, manifest loading, scoped registry contexts, and adapters for existing plugin, skill, provider, channel, CLI, FastAPI, logging, environment, and frontend capabilities. Business identifiers are always supplied by `ProductSpec`, config files, environment variables, or entry points; the SDK never special-cases a downstream product name.

**Tech Stack:** Python 3.10-3.13, dataclasses, `importlib.metadata`, `contextvars`, PyYAML, Click, FastAPI, pytest, pytest monkeypatch fixtures.

---

## Scope

This plan implements the first production-ready extension SDK release inside QwenPaw. It keeps compatibility when no extension is installed and provides enough public API for downstream teams to build independent packages around QwenPaw.

The implementation covers:

- Product/module metadata, product version, CLI display name, workspace paths, config paths, backup paths, console static path, and agent prompt source configuration.
- Environment variable prefix resolution for every existing `QWENPAW_*` key, with downstream prefixes before `QWENPAW` and `COPAW`.
- Logging namespace, file path, format, level, and handler factory registration.
- Click command add, disable, replace, alias, and root command branding.
- Built-in channel registration and policy, separate from file-based custom channel discovery.
- Provider add, disable, replace, and policy.
- Plugin allow/deny/search-path policy and unified plugin APIs.
- FastAPI route, middleware, startup, shutdown, lifespan-adjacent hooks, and full frontend static replacement.
- Feature policy for built-in QA agent and other QwenPaw feature gates.
- Unified `ExtensionAdapters` facade for existing extension points.
- Decorators, fluent builder, manifest loading, context manager isolation, dependency injection, feature packs, and lazy proxies.
- SDK usage documentation in English and Chinese.

## File Structure

Create:

- `src/qwenpaw/extensions/__init__.py`: public SDK exports.
- `src/qwenpaw/extensions/specs.py`: dataclass specs and validation helpers.
- `src/qwenpaw/extensions/registry.py`: `ExtensionRegistry`, scoped registry management, and builder entry points.
- `src/qwenpaw/extensions/env.py`: canonical suffix environment resolver.
- `src/qwenpaw/extensions/config.py`: YAML manifest parsing and config merge.
- `src/qwenpaw/extensions/loader.py`: entry point loading, config loading, and idempotent bootstrap.
- `src/qwenpaw/extensions/decorators.py`: decorator facade returned by `qwenpaw_extension(name)`.
- `src/qwenpaw/extensions/cli.py`: CLI command patch model and lazy command builder.
- `src/qwenpaw/extensions/app.py`: FastAPI extension hooks and static-dir selection.
- `src/qwenpaw/extensions/channels.py`: built-in channel specs, external channel sources, and channel policy helpers.
- `src/qwenpaw/extensions/providers.py`: provider patch specs and provider policy helpers.
- `src/qwenpaw/extensions/features.py`: feature and plugin policy helpers.
- `src/qwenpaw/extensions/logging.py`: logging spec resolution.
- `src/qwenpaw/extensions/adapters.py`: unified facade over existing QwenPaw extension systems.
- `tests/unit/extensions/conftest.py`: isolated registry fixtures.
- `tests/unit/extensions/test_specs.py`: spec validation tests.
- `tests/unit/extensions/test_registry.py`: registry, builder, context manager tests.
- `tests/unit/extensions/test_env.py`: env prefix priority tests.
- `tests/unit/extensions/test_loader.py`: entry point and YAML manifest tests.
- `tests/unit/extensions/test_cli.py`: CLI patch tests.
- `tests/unit/extensions/test_app.py`: FastAPI hook and static path tests.
- `tests/unit/extensions/test_channels.py`: built-in channel registration and channel policy tests.
- `tests/unit/extensions/test_providers.py`: provider policy tests.
- `tests/unit/extensions/test_features.py`: feature and plugin policy tests.
- `tests/unit/extensions/test_adapters.py`: facade tests.
- `docs/extensions-sdk.md`: complete SDK reference and examples.
- `website/public/docs/extensions-sdk.zh.md`: Chinese SDK guide.
- `website/public/docs/extensions-sdk.en.md`: English SDK guide.

Modify:

- `pyproject.toml`: add `qwenpaw.extensions` entry point group documentation comments if needed and include docs in package data if the current include misses the new document path.
- `src/qwenpaw/constant.py`: replace `_get_env` and product/path constants with `EnvResolver` and `ProductSpec` defaults.
- `src/qwenpaw/envs/store.py`: protect canonical env suffixes instead of only literal `QWENPAW_*` names.
- `src/qwenpaw/utils/logging.py`: resolve namespace, file path, format, level, and handlers through `LoggingSpec`.
- `src/qwenpaw/utils/console_static.py`: resolve frontend static path through the extension layer if this helper owns static lookup.
- `src/qwenpaw/cli/main.py`: apply root CLI branding and lazy command patches.
- `src/qwenpaw/cli/channels_cmd.py`: display channel metadata from the extension-aware channel registry.
- `src/qwenpaw/app/_app.py`: apply app hooks, middleware hooks, router patches, plugin router insertion, static replacement, and product name.
- `src/qwenpaw/app/channels/registry.py`: build built-in channel specs from extension-aware registry and keep custom channel loading separate.
- `src/qwenpaw/config/utils.py`: apply channel policy to available channels.
- `src/qwenpaw/config/config.py`: keep generated default channel config aligned with extension-aware registry.
- `src/qwenpaw/providers/provider_manager.py`: apply provider policy during built-in provider initialization.
- `src/qwenpaw/app/migration.py`: check `FeaturePolicy` before creating the built-in QA agent.
- `src/qwenpaw/plugins/loader.py`: apply plugin policy before loading discovered plugins.
- `src/qwenpaw/plugins/api.py`: expose plugin APIs through `ExtensionAdapters` without breaking existing plugin API.

## Public API Contract

The first release must expose these imports:

```python
from qwenpaw.extensions import (
    AppPatch,
    BuiltinChannelSpec,
    CliPatch,
    EnvResolver,
    ExtensionAdapters,
    ExtensionContext,
    ExtensionRegistry,
    ExtensionSpec,
    FeaturePack,
    FeaturePolicy,
    LoggingSpec,
    PluginPolicy,
    ProductSpec,
    ProviderPatch,
    get_extension_registry,
    load_extensions,
    qwenpaw_extension,
    use_extension_registry,
)
```

Business usage must work through all three styles:

```python
from qwenpaw.extensions import ProductSpec


def register(registry):
    registry.configure_product(
        ProductSpec(
            product_name="MyProduct",
            product_version="2.0.0",
            module_alias="my_product",
            cli_name="myproduct",
            env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"),
            working_dir="~/.myproduct",
            secret_dir="~/.myproduct.secret",
        )
    )
```

```python
from qwenpaw.extensions import FeaturePolicy, ProductSpec, qwenpaw_extension

ext = qwenpaw_extension("my_product")


@ext.product
def product_spec():
    return ProductSpec(
        product_name="MyProduct",
        product_version="2.0.0",
        cli_name="myproduct",
        env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"),
    )


@ext.features
def feature_policy():
    return FeaturePolicy(
        disabled_features={"builtin_qa_agent"},
        disabled_channels={"wechat"},
    )
```

```python
def register(registry):
    (
        registry.extension("my_product")
        .product(name="MyProduct", version="2.0.0", cli_name="myproduct")
        .env_prefix("MYPRODUCT")
        .disable_features("builtin_qa_agent")
        .disable_channels("wechat")
        .disable_providers("openrouter")
        .console_static_dir("/opt/myproduct/console")
    )
```

Manifest usage must work with this exact shape:

```yaml
product:
  name: MyProduct
  version: 2.0.0
  module_alias: my_product
  cli_name: myproduct
  env_prefixes: [MYPRODUCT, QWENPAW, COPAW]
  working_dir: ~/.myproduct
  secret_dir: ~/.myproduct.secret
  console_static_dir: /opt/myproduct/console

features:
  disabled_features:
    - builtin_qa_agent
  disabled_channels:
    - wechat
  disabled_providers:
    - openrouter
  disabled_plugins:
    - qwenpaw-pet

plugins:
  extra_search_paths:
    - /opt/myproduct/plugins
```

## Task 1: Add Extension Specs

**Files:**

- Create: `src/qwenpaw/extensions/specs.py`
- Create: `src/qwenpaw/extensions/__init__.py`
- Test: `tests/unit/extensions/test_specs.py`
- Test: `tests/unit/extensions/conftest.py`

- [ ] **Step 1: Write spec validation tests**

Add `tests/unit/extensions/test_specs.py`:

```python
from pathlib import Path

import pytest

from qwenpaw.extensions import (
    BuiltinChannelSpec,
    FeaturePolicy,
    LoggingSpec,
    ProductSpec,
)


def test_product_spec_defaults_keep_qwenpaw_compatibility():
    spec = ProductSpec()

    assert spec.product_name == "QwenPaw"
    assert spec.cli_name == "qwenpaw"
    assert spec.env_prefixes == ("QWENPAW", "COPAW")
    assert spec.working_dir == Path("~/.qwenpaw").expanduser()
    assert spec.secret_dir == Path("~/.qwenpaw.secret").expanduser()


def test_product_spec_downstream_prefix_gets_first_priority(tmp_path):
    spec = ProductSpec(
        product_name="MyProduct",
        cli_name="myproduct",
        env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"),
        working_dir=tmp_path / "work",
        secret_dir=tmp_path / "secret",
    )

    assert spec.env_prefixes[0] == "MYPRODUCT"
    assert spec.working_dir == tmp_path / "work"
    assert spec.secret_dir == tmp_path / "secret"


def test_product_spec_rejects_empty_prefix():
    with pytest.raises(ValueError, match="env_prefixes"):
        ProductSpec(env_prefixes=("", "QWENPAW"))


def test_feature_policy_normalizes_sets():
    policy = FeaturePolicy(
        disabled_features=["builtin_qa_agent"],
        disabled_channels=["wechat"],
        disabled_providers=["openrouter"],
        disabled_plugins=["qwenpaw-pet"],
    )

    assert policy.is_feature_enabled("builtin_qa_agent") is False
    assert policy.is_channel_enabled("console") is True
    assert policy.is_provider_enabled("openrouter") is False
    assert policy.is_plugin_enabled("qwenpaw-pet") is False


def test_logging_spec_defaults_derive_from_product(tmp_path):
    product = ProductSpec(product_name="MyProduct", working_dir=tmp_path)
    logging_spec = LoggingSpec.from_product(product)

    assert logging_spec.namespace == "myproduct"
    assert logging_spec.file_path == tmp_path / "myproduct.log"
    assert "%(levelname)s" in logging_spec.format


def test_builtin_channel_spec_requires_key_and_factory():
    with pytest.raises(ValueError, match="key"):
        BuiltinChannelSpec(key="", factory=lambda: object())

    spec = BuiltinChannelSpec(
        key="my_channel",
        factory=lambda: object(),
        required=False,
        default_enabled=True,
        display_name="My Channel",
    )

    assert spec.key == "my_channel"
    assert spec.display_name == "My Channel"
```

Add `tests/unit/extensions/conftest.py`:

```python
import pytest

from qwenpaw.extensions import ExtensionRegistry, use_extension_registry


@pytest.fixture
def extension_registry():
    registry = ExtensionRegistry()
    with use_extension_registry(registry):
        yield registry
```

- [ ] **Step 2: Run spec tests to verify they fail**

Run: `pytest tests/unit/extensions/test_specs.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'qwenpaw.extensions'`.

- [ ] **Step 3: Implement dataclass specs and public exports**

Create `src/qwenpaw/extensions/specs.py` with these concrete classes:

```python
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _path(value: str | Path | None, default: str | Path) -> Path:
    raw = default if value is None else value
    return Path(raw).expanduser()


def _prefixes(value: Iterable[str]) -> tuple[str, ...]:
    prefixes = tuple(str(item).strip().upper() for item in value)
    if not prefixes or any(not item for item in prefixes):
        raise ValueError("env_prefixes must contain non-empty values")
    return prefixes


def _set(value: Iterable[str] | None) -> set[str]:
    return {str(item).strip() for item in (value or ()) if str(item).strip()}


@dataclass(frozen=True)
class ProductSpec:
    product_name: str = "QwenPaw"
    product_version: str | None = None
    module_alias: str = "qwenpaw"
    cli_name: str = "qwenpaw"
    skill_cli_name: str | None = None
    env_prefixes: tuple[str, ...] = ("QWENPAW", "COPAW")
    working_dir: str | Path = "~/.qwenpaw"
    secret_dir: str | Path = "~/.qwenpaw.secret"
    backup_dir: str | Path | None = None
    plugins_dir: str | Path | None = None
    custom_channels_dir: str | Path | None = None
    media_dir: str | Path | None = None
    local_provider_dir: str | Path | None = None
    console_static_dir: str | Path | None = None
    agent_prompt_files: tuple[str, ...] = ("AGENTS.md", "SOUL.md", "PROFILE.md")

    def __post_init__(self) -> None:
        object.__setattr__(self, "env_prefixes", _prefixes(self.env_prefixes))
        work = _path(self.working_dir, "~/.qwenpaw")
        secret = _path(self.secret_dir, "~/.qwenpaw.secret")
        object.__setattr__(self, "working_dir", work)
        object.__setattr__(self, "secret_dir", secret)
        object.__setattr__(self, "backup_dir", _path(self.backup_dir, work / "backups"))
        object.__setattr__(self, "plugins_dir", _path(self.plugins_dir, work / "plugins"))
        object.__setattr__(
            self,
            "custom_channels_dir",
            _path(self.custom_channels_dir, work / "custom_channels"),
        )
        object.__setattr__(self, "media_dir", _path(self.media_dir, work / "media"))
        object.__setattr__(
            self,
            "local_provider_dir",
            _path(self.local_provider_dir, work / "local_models"),
        )
        if self.console_static_dir is not None:
            object.__setattr__(self, "console_static_dir", _path(self.console_static_dir, work))


@dataclass(frozen=True)
class LoggingSpec:
    namespace: str = "qwenpaw"
    file_path: Path | None = None
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    level: str = "INFO"
    handler_factory: Callable[[str, Path | None, str, str], list[Any]] | None = None

    @classmethod
    def from_product(cls, product: ProductSpec) -> "LoggingSpec":
        namespace = product.product_name.lower().replace(" ", "")
        return cls(namespace=namespace, file_path=product.working_dir / f"{namespace}.log")


@dataclass(frozen=True)
class FeaturePolicy:
    disabled_features: Iterable[str] | None = None
    disabled_channels: Iterable[str] | None = None
    disabled_providers: Iterable[str] | None = None
    disabled_plugins: Iterable[str] | None = None
    allowed_plugins: Iterable[str] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "disabled_features", _set(self.disabled_features))
        object.__setattr__(self, "disabled_channels", _set(self.disabled_channels))
        object.__setattr__(self, "disabled_providers", _set(self.disabled_providers))
        object.__setattr__(self, "disabled_plugins", _set(self.disabled_plugins))
        object.__setattr__(self, "allowed_plugins", _set(self.allowed_plugins))

    def is_feature_enabled(self, name: str) -> bool:
        return name not in self.disabled_features

    def is_channel_enabled(self, key: str) -> bool:
        return key not in self.disabled_channels

    def is_provider_enabled(self, provider_id: str) -> bool:
        return provider_id not in self.disabled_providers

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        if self.allowed_plugins and plugin_name not in self.allowed_plugins:
            return False
        return plugin_name not in self.disabled_plugins


@dataclass(frozen=True)
class PluginPolicy:
    disabled_plugins: Iterable[str] | None = None
    allowed_plugins: Iterable[str] | None = None
    extra_search_paths: tuple[Path, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "disabled_plugins", _set(self.disabled_plugins))
        object.__setattr__(self, "allowed_plugins", _set(self.allowed_plugins))
        object.__setattr__(
            self,
            "extra_search_paths",
            tuple(Path(path).expanduser() for path in self.extra_search_paths),
        )


@dataclass(frozen=True)
class CliCommandPatch:
    name: str
    module: str
    attribute: str


@dataclass(frozen=True)
class CliPatch:
    add: Mapping[str, CliCommandPatch] = field(default_factory=dict)
    replace: Mapping[str, CliCommandPatch] = field(default_factory=dict)
    disable: frozenset[str] = frozenset()
    aliases: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AppPatch:
    routers: tuple[Any, ...] = ()
    startup_hooks: tuple[Callable[..., Any], ...] = ()
    shutdown_hooks: tuple[Callable[..., Any], ...] = ()
    middleware_hooks: tuple[Callable[..., Any], ...] = ()
    before_include_routers: tuple[Callable[..., Any], ...] = ()
    after_include_routers: tuple[Callable[..., Any], ...] = ()


@dataclass(frozen=True)
class ProviderPatch:
    provider_id: str
    provider_cls: type[Any]
    replace: bool = False


@dataclass(frozen=True)
class BuiltinChannelSpec:
    key: str
    factory: Callable[..., Any]
    config_model: type[Any] | None = None
    required: bool = False
    default_enabled: bool = False
    route_hook: Callable[..., Any] | None = None
    display_name: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("key is required")


@dataclass(frozen=True)
class ExtensionSpec:
    name: str
    product: ProductSpec | None = None
    logging: LoggingSpec | None = None
    features: FeaturePolicy = field(default_factory=FeaturePolicy)
```

Create `src/qwenpaw/extensions/__init__.py`:

```python
from .specs import (
    AppPatch,
    BuiltinChannelSpec,
    CliCommandPatch,
    CliPatch,
    ExtensionSpec,
    FeaturePolicy,
    LoggingSpec,
    PluginPolicy,
    ProductSpec,
    ProviderPatch,
)

__all__ = [
    "AppPatch",
    "BuiltinChannelSpec",
    "CliCommandPatch",
    "CliPatch",
    "ExtensionSpec",
    "FeaturePolicy",
    "LoggingSpec",
    "PluginPolicy",
    "ProductSpec",
    "ProviderPatch",
]
```

- [ ] **Step 4: Run spec tests**

Run: `pytest tests/unit/extensions/test_specs.py -v`

Expected: PASS for all tests in `test_specs.py`.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/qwenpaw/extensions/__init__.py src/qwenpaw/extensions/specs.py tests/unit/extensions/conftest.py tests/unit/extensions/test_specs.py
git commit -m "feat: add extension SDK specs"
```

Expected: commit succeeds.

## Task 2: Add Registry, Context Manager, and Builder

**Files:**

- Create: `src/qwenpaw/extensions/registry.py`
- Modify: `src/qwenpaw/extensions/__init__.py`
- Test: `tests/unit/extensions/test_registry.py`

- [ ] **Step 1: Write registry tests**

Add `tests/unit/extensions/test_registry.py`:

```python
from qwenpaw.extensions import (
    ExtensionRegistry,
    FeaturePolicy,
    PluginPolicy,
    ProductSpec,
    get_extension_registry,
    use_extension_registry,
)


def test_registry_default_product_is_qwenpaw():
    registry = ExtensionRegistry()

    assert registry.product.product_name == "QwenPaw"
    assert registry.product.cli_name == "qwenpaw"


def test_registry_configure_product_replaces_default(tmp_path):
    registry = ExtensionRegistry()
    spec = ProductSpec(
        product_name="MyProduct",
        cli_name="myproduct",
        env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"),
        working_dir=tmp_path / "work",
    )

    registry.configure_product(spec)

    assert registry.product.product_name == "MyProduct"
    assert registry.product.working_dir == tmp_path / "work"


def test_use_extension_registry_is_scoped():
    outer = get_extension_registry()
    inner = ExtensionRegistry()
    inner.configure_product(ProductSpec(product_name="ScopedProduct"))

    with use_extension_registry(inner):
        assert get_extension_registry().product.product_name == "ScopedProduct"

    assert get_extension_registry() is outer


def test_builder_configures_product_and_features(tmp_path):
    registry = ExtensionRegistry()

    (
        registry.extension("my_product")
        .product(name="MyProduct", version="2.0.0", cli_name="myproduct")
        .env_prefix("MYPRODUCT")
        .working_dir(tmp_path / "work")
        .disable_features("builtin_qa_agent")
        .disable_channels("wechat")
        .disable_providers("openrouter")
    )

    assert registry.product.product_name == "MyProduct"
    assert registry.product.env_prefixes == ("MYPRODUCT", "QWENPAW", "COPAW")
    assert registry.features.is_feature_enabled("builtin_qa_agent") is False
    assert registry.features.is_channel_enabled("wechat") is False
    assert registry.features.is_provider_enabled("openrouter") is False


def test_configure_features_merges_disabled_sets():
    registry = ExtensionRegistry()
    registry.configure_features(FeaturePolicy(disabled_features={"builtin_qa_agent"}))
    registry.configure_features(FeaturePolicy(disabled_channels={"wechat"}))

    assert registry.features.is_feature_enabled("builtin_qa_agent") is False
    assert registry.features.is_channel_enabled("wechat") is False


def test_configure_plugins_merges_plugin_policy(tmp_path):
    registry = ExtensionRegistry()
    registry.configure_plugins(
        PluginPolicy(
            disabled_plugins={"qwenpaw-pet"},
            extra_search_paths=(tmp_path / "plugins",),
        )
    )

    assert registry.features.is_plugin_enabled("qwenpaw-pet") is False
    assert registry.plugins.extra_search_paths == (tmp_path / "plugins",)
```

- [ ] **Step 2: Run registry tests to verify they fail**

Run: `pytest tests/unit/extensions/test_registry.py -v`

Expected: FAIL with `ImportError` for `ExtensionRegistry`.

- [ ] **Step 3: Implement registry and builder**

Create `src/qwenpaw/extensions/registry.py`:

```python
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Iterator

from .specs import FeaturePolicy, LoggingSpec, PluginPolicy, ProductSpec


class ExtensionRegistry:
    def __init__(self) -> None:
        self.product = ProductSpec()
        self.logging = LoggingSpec.from_product(self.product)
        self.features = FeaturePolicy()
        self.plugins = PluginPolicy()
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
            extra_search_paths=(*self.plugins.extra_search_paths, *policy.extra_search_paths),
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
    def __init__(self, registry: ExtensionRegistry, name: str) -> None:
        self.registry = registry
        self.name = name
        self._product_kwargs: dict[str, object] = {
            "module_alias": name,
            "env_prefixes": self.registry.product.env_prefixes,
            "working_dir": self.registry.product.working_dir,
            "secret_dir": self.registry.product.secret_dir,
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
        prefix = prefix.strip().upper()
        fallback = tuple(item for item in self.registry.product.env_prefixes if item != prefix)
        self._product_kwargs["env_prefixes"] = (prefix, *fallback)
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
        self.registry.configure_features(FeaturePolicy(disabled_providers=set(provider_ids)))
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
```

Update `src/qwenpaw/extensions/__init__.py`:

```python
from .registry import ExtensionRegistry, get_extension_registry, use_extension_registry
```

Add these names to `__all__`.

- [ ] **Step 4: Run registry tests**

Run: `pytest tests/unit/extensions/test_registry.py tests/unit/extensions/test_specs.py -v`

Expected: PASS for both files.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/qwenpaw/extensions/__init__.py src/qwenpaw/extensions/registry.py tests/unit/extensions/test_registry.py
git commit -m "feat: add extension registry"
```

Expected: commit succeeds.

## Task 3: Add Environment Resolver and Config Loading

**Files:**

- Create: `src/qwenpaw/extensions/env.py`
- Create: `src/qwenpaw/extensions/config.py`
- Create: `src/qwenpaw/extensions/loader.py`
- Modify: `src/qwenpaw/extensions/__init__.py`
- Test: `tests/unit/extensions/test_env.py`
- Test: `tests/unit/extensions/test_loader.py`

- [ ] **Step 1: Write env resolver tests**

Add `tests/unit/extensions/test_env.py`:

```python
from qwenpaw.extensions import EnvResolver, ProductSpec


def test_env_resolver_prefers_downstream_prefix(monkeypatch):
    monkeypatch.setenv("MYPRODUCT_WORKING_DIR", "/tmp/myproduct")
    monkeypatch.setenv("QWENPAW_WORKING_DIR", "/tmp/qwenpaw")
    resolver = EnvResolver(
        ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
    )

    assert resolver.get("WORKING_DIR") == "/tmp/myproduct"


def test_env_resolver_falls_back_to_qwenpaw(monkeypatch):
    monkeypatch.delenv("MYPRODUCT_WORKING_DIR", raising=False)
    monkeypatch.setenv("QWENPAW_WORKING_DIR", "/tmp/qwenpaw")
    resolver = EnvResolver(
        ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
    )

    assert resolver.get("WORKING_DIR") == "/tmp/qwenpaw"


def test_env_resolver_accepts_legacy_literal_key(monkeypatch):
    monkeypatch.setenv("MYPRODUCT_AUTH_ENABLED", "false")
    resolver = EnvResolver(
        ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
    )

    assert resolver.get("QWENPAW_AUTH_ENABLED") == "false"


def test_env_resolver_bool_and_int(monkeypatch):
    monkeypatch.setenv("MYPRODUCT_AUTH_ENABLED", "true")
    monkeypatch.setenv("MYPRODUCT_LLM_RATE_LIMIT_REQUESTS", "7")
    resolver = EnvResolver(
        ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
    )

    assert resolver.get_bool("AUTH_ENABLED") is True
    assert resolver.get_int("LLM_RATE_LIMIT_REQUESTS") == 7


def test_env_resolver_key_returns_highest_priority_name():
    resolver = EnvResolver(
        ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
    )

    assert resolver.key("WORKING_DIR") == "MYPRODUCT_WORKING_DIR"
```

- [ ] **Step 2: Write loader tests**

Add `tests/unit/extensions/test_loader.py`:

```python
from importlib.metadata import EntryPoint

from qwenpaw.extensions import ExtensionRegistry, load_extensions


def test_load_extensions_from_entry_point(monkeypatch):
    registry = ExtensionRegistry()

    def register(target):
        target.extension("my_product").product(name="MyProduct", cli_name="myproduct")

    entry_point = EntryPoint(
        name="my_product",
        value="tests.unit.extensions.test_loader:register",
        group="qwenpaw.extensions",
    )
    monkeypatch.setattr(
        "qwenpaw.extensions.loader.entry_points",
        lambda group=None: [entry_point] if group == "qwenpaw.extensions" else [],
    )
    globals()["register"] = register

    load_extensions(registry=registry)

    assert registry.product.product_name == "MyProduct"


def test_load_extensions_from_yaml_manifest(tmp_path):
    manifest = tmp_path / "extension.yaml"
    manifest.write_text(
        """
product:
  name: MyProduct
  version: 2.0.0
  cli_name: myproduct
  env_prefixes: [MYPRODUCT, QWENPAW, COPAW]
features:
  disabled_features:
    - builtin_qa_agent
  disabled_channels:
    - wechat
""".strip(),
        encoding="utf-8",
    )
    registry = ExtensionRegistry()

    load_extensions(registry=registry, config_path=manifest, include_entry_points=False)

    assert registry.product.product_name == "MyProduct"
    assert registry.features.is_feature_enabled("builtin_qa_agent") is False
    assert registry.features.is_channel_enabled("wechat") is False
```

- [ ] **Step 3: Run env and loader tests to verify they fail**

Run: `pytest tests/unit/extensions/test_env.py tests/unit/extensions/test_loader.py -v`

Expected: FAIL with missing `EnvResolver` and `load_extensions`.

- [ ] **Step 4: Implement `EnvResolver`**

Create `src/qwenpaw/extensions/env.py`:

```python
from __future__ import annotations

import os
from collections.abc import Mapping

from .specs import ProductSpec


class EnvResolver:
    def __init__(
        self,
        product: ProductSpec,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self.product = product
        self.environ = os.environ if environ is None else environ

    def suffix(self, key: str) -> str:
        key = key.strip().upper()
        for prefix in self.product.env_prefixes:
            marker = f"{prefix}_"
            if key.startswith(marker):
                return key[len(marker) :]
        return key

    def names(self, key: str) -> tuple[str, ...]:
        suffix = self.suffix(key)
        return tuple(f"{prefix}_{suffix}" for prefix in self.product.env_prefixes)

    def key(self, key: str) -> str:
        return self.names(key)[0]

    def get(self, key: str, default: str | None = None) -> str | None:
        for name in self.names(key):
            value = self.environ.get(name)
            if value is not None:
                return value
        return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.get(key)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    def get_int(self, key: str, default: int = 0) -> int:
        value = self.get(key)
        if value is None or value == "":
            return default
        return int(value)

    def get_float(self, key: str, default: float = 0.0) -> float:
        value = self.get(key)
        if value is None or value == "":
            return default
        return float(value)
```

- [ ] **Step 5: Implement manifest and entry point loader**

Create `src/qwenpaw/extensions/config.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .registry import ExtensionRegistry
from .specs import FeaturePolicy, PluginPolicy, ProductSpec


def apply_manifest(registry: ExtensionRegistry, path: str | Path) -> None:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    product = data.get("product") or {}
    features = data.get("features") or {}
    plugins = data.get("plugins") or {}

    if product:
        registry.configure_product(
            ProductSpec(
                product_name=product.get("name", "QwenPaw"),
                product_version=product.get("version"),
                module_alias=product.get("module_alias", "qwenpaw"),
                cli_name=product.get("cli_name", "qwenpaw"),
                skill_cli_name=product.get("skill_cli_name"),
                env_prefixes=tuple(product.get("env_prefixes", ("QWENPAW", "COPAW"))),
                working_dir=product.get("working_dir", "~/.qwenpaw"),
                secret_dir=product.get("secret_dir", "~/.qwenpaw.secret"),
                backup_dir=product.get("backup_dir"),
                plugins_dir=product.get("plugins_dir"),
                custom_channels_dir=product.get("custom_channels_dir"),
                media_dir=product.get("media_dir"),
                local_provider_dir=product.get("local_provider_dir"),
                console_static_dir=product.get("console_static_dir"),
            )
        )

    if features:
        registry.configure_features(
            FeaturePolicy(
                disabled_features=features.get("disabled_features"),
                disabled_channels=features.get("disabled_channels"),
                disabled_providers=features.get("disabled_providers"),
                disabled_plugins=features.get("disabled_plugins"),
                allowed_plugins=features.get("allowed_plugins"),
            )
        )

    if plugins:
        registry.configure_plugins(
            PluginPolicy(extra_search_paths=tuple(plugins.get("extra_search_paths") or ()))
        )
```

Create `src/qwenpaw/extensions/loader.py`:

```python
from __future__ import annotations

import os
from importlib.metadata import entry_points
from pathlib import Path

from .config import apply_manifest
from .registry import ExtensionRegistry, get_extension_registry

_LOADED_REGISTRY_IDS: set[int] = set()


def load_extensions(
    *,
    registry: ExtensionRegistry | None = None,
    config_path: str | Path | None = None,
    include_entry_points: bool = True,
    force: bool = False,
) -> ExtensionRegistry:
    target = registry or get_extension_registry()
    registry_id = id(target)
    if registry_id in _LOADED_REGISTRY_IDS and not force:
        return target

    if config_path is None:
        config_path = os.environ.get("QWENPAW_EXTENSION_CONFIG")
    if config_path:
        apply_manifest(target, config_path)

    if include_entry_points:
        for entry_point in entry_points(group="qwenpaw.extensions"):
            register = entry_point.load()
            register(target)

    _LOADED_REGISTRY_IDS.add(registry_id)
    return target
```

Update `src/qwenpaw/extensions/__init__.py`:

```python
from .env import EnvResolver
from .loader import load_extensions
```

Add both names to `__all__`.

- [ ] **Step 6: Run env and loader tests**

Run: `pytest tests/unit/extensions/test_env.py tests/unit/extensions/test_loader.py tests/unit/extensions/test_registry.py -v`

Expected: PASS for all listed tests.

- [ ] **Step 7: Commit**

Run:

```bash
git add src/qwenpaw/extensions tests/unit/extensions
git commit -m "feat: load extension configuration"
```

Expected: commit succeeds.

## Task 4: Integrate Product Paths and Environment Resolver

**Files:**

- Modify: `src/qwenpaw/constant.py`
- Modify: `src/qwenpaw/envs/store.py`
- Test: `tests/unit/extensions/test_env.py`
- Test: `tests/unit/extensions/test_product_constants.py`

- [ ] **Step 1: Add constant integration tests**

Add `tests/unit/extensions/test_product_constants.py`:

```python
import importlib

from qwenpaw.extensions import ExtensionRegistry, ProductSpec, use_extension_registry


def test_constant_uses_extension_product_paths(tmp_path, monkeypatch):
    registry = ExtensionRegistry()
    registry.configure_product(
        ProductSpec(
            product_name="MyProduct",
            env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"),
            working_dir=tmp_path / "work",
            secret_dir=tmp_path / "secret",
        )
    )

    with use_extension_registry(registry):
        import qwenpaw.constant as constant

        reloaded = importlib.reload(constant)

    assert reloaded.PROJECT_NAME == "MyProduct"
    assert reloaded.WORKING_DIR == tmp_path / "work"
    assert reloaded.SECRET_DIR == tmp_path / "secret"
    assert reloaded.CUSTOM_CHANNELS_DIR == tmp_path / "work" / "custom_channels"


def test_constant_env_prefix_priority(tmp_path, monkeypatch):
    monkeypatch.setenv("MYPRODUCT_WORKING_DIR", str(tmp_path / "business"))
    monkeypatch.setenv("QWENPAW_WORKING_DIR", str(tmp_path / "qwenpaw"))
    registry = ExtensionRegistry()
    registry.configure_product(
        ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
    )

    with use_extension_registry(registry):
        import qwenpaw.constant as constant

        reloaded = importlib.reload(constant)

    assert reloaded.WORKING_DIR == tmp_path / "business"
```

- [ ] **Step 2: Run constant tests to verify they fail**

Run: `pytest tests/unit/extensions/test_product_constants.py -v`

Expected: FAIL because `constant.py` still resolves only old defaults.

- [ ] **Step 3: Refactor `constant.py` to use registry and resolver**

In `src/qwenpaw/constant.py`, import these names near the top:

```python
from qwenpaw.extensions import EnvResolver, get_extension_registry, load_extensions
```

Replace the existing `_get_env` implementation with:

```python
load_extensions()
_EXTENSION_REGISTRY = get_extension_registry()
_PRODUCT = _EXTENSION_REGISTRY.product
_ENV = EnvResolver(_PRODUCT)


def _get_env(key: str, default: str | None = None) -> str | None:
    return _ENV.get(key, default)
```

Replace product/path defaults with registry-backed values:

```python
PROJECT_NAME = _PRODUCT.product_name
WORKING_DIR = Path(_get_env("WORKING_DIR") or _PRODUCT.working_dir)
SECRET_DIR = Path(_get_env("SECRET_DIR") or _PRODUCT.secret_dir)
BACKUP_DIR = Path(_get_env("BACKUP_DIR") or _PRODUCT.backup_dir)
PLUGINS_DIR = Path(_get_env("PLUGINS_DIR") or _PRODUCT.plugins_dir)
CUSTOM_CHANNELS_DIR = Path(_get_env("CUSTOM_CHANNELS_DIR") or _PRODUCT.custom_channels_dir)
DEFAULT_MEDIA_DIR = Path(_get_env("DEFAULT_MEDIA_DIR") or _PRODUCT.media_dir)
DEFAULT_LOCAL_PROVIDER_DIR = Path(
    _get_env("DEFAULT_LOCAL_PROVIDER_DIR") or _PRODUCT.local_provider_dir
)
```

For every existing `_get_env("QWENPAW_...")` call, keep the call valid because `_get_env` strips known prefixes. Prefer canonical suffix form for touched lines:

```python
AUTH_ENABLED = _get_env("AUTH_ENABLED", "false") == "true"
```

- [ ] **Step 4: Update protected persisted env keys**

In `src/qwenpaw/envs/store.py`, import the resolver:

```python
from qwenpaw.extensions import EnvResolver, get_extension_registry
```

Replace literal protected key checks with canonical suffix checks:

```python
_PROTECTED_SUFFIXES = {"WORKING_DIR", "SECRET_DIR"}


def _canonical_env_suffix(name: str) -> str:
    resolver = EnvResolver(get_extension_registry().product)
    return resolver.suffix(name)
```

Where the store rejects protected env writes, compare with `_canonical_env_suffix(name)`:

```python
if _canonical_env_suffix(name) in _PROTECTED_SUFFIXES:
    raise ValueError(f"{name} is protected and cannot be persisted")
```

- [ ] **Step 5: Audit direct env reads**

Run: `rg -n "os\\.environ\\.get\\(\"(QWENPAW|COPAW)_" src/qwenpaw`

Expected: either no matches, or matches only in `src/qwenpaw/extensions/env.py`, `src/qwenpaw/extensions/loader.py`, and compatibility comments. Migrate every other match through `EnvResolver`.

- [ ] **Step 6: Run tests**

Run: `pytest tests/unit/extensions/test_env.py tests/unit/extensions/test_product_constants.py -v`

Expected: PASS for both files.

- [ ] **Step 7: Commit**

Run:

```bash
git add src/qwenpaw/constant.py src/qwenpaw/envs/store.py tests/unit/extensions/test_env.py tests/unit/extensions/test_product_constants.py
git commit -m "feat: resolve product env prefixes"
```

Expected: commit succeeds.

## Task 5: Integrate Logging Spec

**Files:**

- Create: `src/qwenpaw/extensions/logging.py`
- Modify: `src/qwenpaw/extensions/__init__.py`
- Modify: `src/qwenpaw/utils/logging.py`
- Test: `tests/unit/extensions/test_logging.py`

- [ ] **Step 1: Write logging tests**

Add `tests/unit/extensions/test_logging.py`:

```python
import logging

from qwenpaw.extensions import ExtensionRegistry, LoggingSpec, ProductSpec, use_extension_registry
from qwenpaw.extensions.logging import resolve_logging_spec


def test_resolve_logging_spec_uses_product_namespace(tmp_path):
    registry = ExtensionRegistry()
    registry.configure_product(ProductSpec(product_name="MyProduct", working_dir=tmp_path))

    with use_extension_registry(registry):
        spec = resolve_logging_spec()

    assert spec.namespace == "myproduct"
    assert spec.file_path == tmp_path / "myproduct.log"


def test_configured_logging_spec_wins(tmp_path):
    registry = ExtensionRegistry()
    registry.configure_logging(
        LoggingSpec(
            namespace="business",
            file_path=tmp_path / "business.log",
            format="%(levelname)s:%(message)s",
            level="DEBUG",
        )
    )

    with use_extension_registry(registry):
        spec = resolve_logging_spec()

    assert spec.namespace == "business"
    assert spec.file_path == tmp_path / "business.log"
    assert spec.level == "DEBUG"


def test_handler_factory_is_used(tmp_path):
    created = []

    def handler_factory(namespace, file_path, fmt, level):
        created.append((namespace, file_path, fmt, level))
        return [logging.NullHandler()]

    registry = ExtensionRegistry()
    registry.configure_logging(
        LoggingSpec(namespace="business", file_path=tmp_path / "x.log", handler_factory=handler_factory)
    )

    with use_extension_registry(registry):
        spec = resolve_logging_spec()
        handlers = spec.create_handlers()

    assert len(handlers) == 1
    assert created[0][0] == "business"
```

- [ ] **Step 2: Run logging tests to verify they fail**

Run: `pytest tests/unit/extensions/test_logging.py -v`

Expected: FAIL because `qwenpaw.extensions.logging` is missing.

- [ ] **Step 3: Implement logging resolution**

Create `src/qwenpaw/extensions/logging.py`:

```python
from __future__ import annotations

import logging
from pathlib import Path

from .registry import get_extension_registry
from .specs import LoggingSpec


class ResolvedLoggingSpec(LoggingSpec):
    def create_handlers(self) -> list[logging.Handler]:
        if self.handler_factory is not None:
            return self.handler_factory(self.namespace, self.file_path, self.format, self.level)

        handlers: list[logging.Handler] = [logging.StreamHandler()]
        if self.file_path is not None:
            Path(self.file_path).parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(self.file_path, encoding="utf-8"))
        formatter = logging.Formatter(self.format)
        for handler in handlers:
            handler.setFormatter(formatter)
            handler.setLevel(self.level)
        return handlers


def resolve_logging_spec() -> ResolvedLoggingSpec:
    spec = get_extension_registry().logging
    return ResolvedLoggingSpec(
        namespace=spec.namespace,
        file_path=spec.file_path,
        format=spec.format,
        level=spec.level,
        handler_factory=spec.handler_factory,
    )
```

Update `src/qwenpaw/extensions/__init__.py` to export `resolve_logging_spec` if a public function is desired:

```python
from .logging import resolve_logging_spec
```

- [ ] **Step 4: Integrate `src/qwenpaw/utils/logging.py`**

Replace namespace/path/format constants with:

```python
from qwenpaw.extensions.logging import resolve_logging_spec

_LOGGING_SPEC = resolve_logging_spec()
LOG_NAMESPACE = _LOGGING_SPEC.namespace
LOG_FILE_PATH = _LOGGING_SPEC.file_path
LOG_FORMAT = _LOGGING_SPEC.format
```

Where handlers are created, use:

```python
for handler in _LOGGING_SPEC.create_handlers():
    logger.addHandler(handler)
```

- [ ] **Step 5: Run logging tests and a targeted existing test**

Run: `pytest tests/unit/extensions/test_logging.py tests/unit/workspace/test_agent_model.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/qwenpaw/extensions src/qwenpaw/utils/logging.py tests/unit/extensions/test_logging.py
git commit -m "feat: make logging extension-aware"
```

Expected: commit succeeds.

## Task 6: Add CLI Patch Registry and Root Branding

**Files:**

- Create: `src/qwenpaw/extensions/cli.py`
- Modify: `src/qwenpaw/extensions/registry.py`
- Modify: `src/qwenpaw/extensions/__init__.py`
- Modify: `src/qwenpaw/cli/main.py`
- Test: `tests/unit/extensions/test_cli.py`

- [ ] **Step 1: Write CLI tests**

Add `tests/unit/extensions/test_cli.py`:

```python
import click
from click.testing import CliRunner

from qwenpaw.extensions import ExtensionRegistry, ProductSpec, use_extension_registry
from qwenpaw.extensions.cli import CliRegistry


def test_cli_registry_add_disable_replace_and_alias():
    cli = CliRegistry()
    defaults = {
        "doctor": ("qwenpaw.cli.doctor_cmd", "doctor_group"),
        "models": ("qwenpaw.cli.models_cmd", "models_group"),
    }

    cli.disable_command("doctor")
    cli.replace_command("models", "my_product.cli.models", "models_group")
    cli.add_command("diagnose", "my_product.cli.diagnose", "diagnose_command")
    cli.alias_command("models", "llms")

    patched = cli.build_lazy_subcommands(defaults)

    assert "doctor" not in patched
    assert patched["models"] == ("my_product.cli.models", "models_group")
    assert patched["diagnose"] == ("my_product.cli.diagnose", "diagnose_command")
    assert patched["llms"] == ("my_product.cli.models", "models_group")


def test_root_click_uses_product_name_for_version(monkeypatch):
    registry = ExtensionRegistry()
    registry.configure_product(ProductSpec(product_name="MyProduct", cli_name="myproduct"))

    with use_extension_registry(registry):
        from qwenpaw.cli.main import cli

        result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "myproduct" in result.output or "MyProduct" in result.output
```

- [ ] **Step 2: Run CLI tests to verify they fail**

Run: `pytest tests/unit/extensions/test_cli.py -v`

Expected: FAIL because `CliRegistry` is missing and CLI is still hardcoded.

- [ ] **Step 3: Implement `CliRegistry`**

Create `src/qwenpaw/extensions/cli.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field

LazyCommandMap = dict[str, tuple[str, str]]


@dataclass
class CliRegistry:
    added: LazyCommandMap = field(default_factory=dict)
    replaced: LazyCommandMap = field(default_factory=dict)
    disabled: set[str] = field(default_factory=set)
    aliases: dict[str, str] = field(default_factory=dict)

    def add_command(self, name: str, module: str, attribute: str) -> None:
        self.added[name] = (module, attribute)

    def disable_command(self, name: str) -> None:
        self.disabled.add(name)

    def replace_command(self, name: str, module: str, attribute: str) -> None:
        self.replaced[name] = (module, attribute)

    def alias_command(self, existing: str, alias: str) -> None:
        self.aliases[alias] = existing

    def build_lazy_subcommands(self, defaults: LazyCommandMap) -> LazyCommandMap:
        commands = dict(defaults)
        for name in self.disabled:
            commands.pop(name, None)
        commands.update(self.replaced)
        commands.update(self.added)
        for alias, existing in self.aliases.items():
            if existing in commands:
                commands[alias] = commands[existing]
        return commands
```

In `ExtensionRegistry.__init__`, add:

```python
from .cli import CliRegistry

self.cli = CliRegistry()
```

Add convenience methods to `ExtensionBuilder`:

```python
def cli_command(self, name: str, module: str, attribute: str) -> "ExtensionBuilder":
    self.registry.cli.add_command(name, module, attribute)
    return self
```

- [ ] **Step 4: Integrate CLI main**

In `src/qwenpaw/cli/main.py`, load extensions before building the `LazyGroup`:

```python
from qwenpaw.extensions import get_extension_registry, load_extensions

load_extensions()
_EXTENSION_REGISTRY = get_extension_registry()
lazy_subcommands = _EXTENSION_REGISTRY.cli.build_lazy_subcommands(lazy_subcommands)
```

Replace the version option product name with:

```python
@click.version_option(__version__, prog_name=_EXTENSION_REGISTRY.product.product_name)
```

If the root group name is explicitly passed to Click, use:

```python
@click.group(cls=LazyGroup, lazy_subcommands=lazy_subcommands, name=_EXTENSION_REGISTRY.product.cli_name)
```

- [ ] **Step 5: Run CLI tests**

Run: `pytest tests/unit/extensions/test_cli.py tests/unit/workspace/test_cli_agent_id.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/qwenpaw/extensions/cli.py src/qwenpaw/extensions/registry.py src/qwenpaw/extensions/__init__.py src/qwenpaw/cli/main.py tests/unit/extensions/test_cli.py
git commit -m "feat: allow CLI extension patches"
```

Expected: commit succeeds.

## Task 7: Add FastAPI Extension Hooks and Frontend Static Replacement

**Files:**

- Create: `src/qwenpaw/extensions/app.py`
- Modify: `src/qwenpaw/extensions/registry.py`
- Modify: `src/qwenpaw/extensions/__init__.py`
- Modify: `src/qwenpaw/app/_app.py`
- Modify: `src/qwenpaw/utils/console_static.py`
- Test: `tests/unit/extensions/test_app.py`

- [ ] **Step 1: Write app extension tests**

Add `tests/unit/extensions/test_app.py`:

```python
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from qwenpaw.extensions import ExtensionRegistry, ProductSpec, use_extension_registry
from qwenpaw.extensions.app import AppExtensionRegistry, resolve_console_static_dir


def test_app_registry_includes_router_before_spa():
    app = FastAPI()
    registry = AppExtensionRegistry()
    router = APIRouter()

    @router.get("/health")
    def health():
        return {"status": "ok"}

    registry.add_router(router, prefix="/api/product", tags=["product"])
    registry.apply_routers(app)

    response = TestClient(app).get("/api/product/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_registry_runs_startup_and_shutdown_hooks():
    calls = []
    registry = AppExtensionRegistry()
    registry.add_startup_hook(lambda: calls.append("startup"))
    registry.add_shutdown_hook(lambda: calls.append("shutdown"))

    registry.run_startup_hooks()
    registry.run_shutdown_hooks()

    assert calls == ["startup", "shutdown"]


def test_console_static_dir_prefers_product_spec(tmp_path):
    static_dir = tmp_path / "console"
    registry = ExtensionRegistry()
    registry.configure_product(ProductSpec(console_static_dir=static_dir))

    with use_extension_registry(registry):
        assert resolve_console_static_dir() == static_dir
```

- [ ] **Step 2: Run app tests to verify they fail**

Run: `pytest tests/unit/extensions/test_app.py -v`

Expected: FAIL because app extension module is missing.

- [ ] **Step 3: Implement app registry**

Create `src/qwenpaw/extensions/app.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI

from .registry import get_extension_registry


@dataclass
class RouterRegistration:
    router: Any
    prefix: str = ""
    tags: list[str] | None = None


@dataclass
class AppExtensionRegistry:
    routers: list[RouterRegistration] = field(default_factory=list)
    startup_hooks: list[Callable[..., Any]] = field(default_factory=list)
    shutdown_hooks: list[Callable[..., Any]] = field(default_factory=list)
    middleware_hooks: list[Callable[[FastAPI], Any]] = field(default_factory=list)
    before_include_routers: list[Callable[[FastAPI], Any]] = field(default_factory=list)
    after_include_routers: list[Callable[[FastAPI], Any]] = field(default_factory=list)

    def add_router(self, router: Any, prefix: str = "", tags: list[str] | None = None) -> None:
        self.routers.append(RouterRegistration(router=router, prefix=prefix, tags=tags))

    def add_startup_hook(self, hook: Callable[..., Any]) -> None:
        self.startup_hooks.append(hook)

    def add_shutdown_hook(self, hook: Callable[..., Any]) -> None:
        self.shutdown_hooks.append(hook)

    def add_middleware_hook(self, hook: Callable[[FastAPI], Any]) -> None:
        self.middleware_hooks.append(hook)

    def apply_middleware(self, app: FastAPI) -> None:
        for hook in self.middleware_hooks:
            hook(app)

    def apply_routers(self, app: FastAPI) -> None:
        for item in self.routers:
            app.include_router(item.router, prefix=item.prefix, tags=item.tags)

    def run_startup_hooks(self) -> None:
        for hook in self.startup_hooks:
            hook()

    def run_shutdown_hooks(self) -> None:
        for hook in self.shutdown_hooks:
            hook()


def resolve_console_static_dir() -> Path | None:
    return get_extension_registry().product.console_static_dir
```

In `ExtensionRegistry.__init__`, add:

```python
from .app import AppExtensionRegistry

self.app = AppExtensionRegistry()
```

- [ ] **Step 4: Integrate `src/qwenpaw/app/_app.py`**

In app creation code, after `load_extensions()`:

```python
from qwenpaw.extensions import get_extension_registry, load_extensions

load_extensions()
_EXTENSION_REGISTRY = get_extension_registry()
```

Before built-in routers are included:

```python
for hook in _EXTENSION_REGISTRY.app.before_include_routers:
    hook(app)
```

After built-in routers and before SPA catch-all:

```python
_EXTENSION_REGISTRY.app.apply_routers(app)
for hook in _EXTENSION_REGISTRY.app.after_include_routers:
    hook(app)
```

In startup and shutdown lifecycle:

```python
_EXTENSION_REGISTRY.app.run_startup_hooks()
_EXTENSION_REGISTRY.app.run_shutdown_hooks()
```

For `AgentApp`, replace hardcoded product name with:

```python
agent_app = AgentApp(app_name=_EXTENSION_REGISTRY.product.product_name, ...)
```

- [ ] **Step 5: Integrate console static resolution**

Where `_CONSOLE_STATIC_ENV = "QWENPAW_CONSOLE_STATIC_DIR"` is used, replace direct env lookup with:

```python
from qwenpaw.extensions.app import resolve_console_static_dir

extension_static_dir = resolve_console_static_dir()
if extension_static_dir is not None:
    console_static_dir = extension_static_dir
```

If environment override must remain compatible, route it through `EnvResolver`:

```python
env_static_dir = EnvResolver(_EXTENSION_REGISTRY.product).get("CONSOLE_STATIC_DIR")
```

- [ ] **Step 6: Run app tests**

Run: `pytest tests/unit/extensions/test_app.py tests/integration/test_console_metadata.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add src/qwenpaw/extensions/app.py src/qwenpaw/extensions/registry.py src/qwenpaw/extensions/__init__.py src/qwenpaw/app/_app.py src/qwenpaw/utils/console_static.py tests/unit/extensions/test_app.py
git commit -m "feat: add FastAPI extension hooks"
```

Expected: commit succeeds.

## Task 8: Add Built-In Channel Registration and Policy

**Files:**

- Create: `src/qwenpaw/extensions/channels.py`
- Modify: `src/qwenpaw/extensions/registry.py`
- Modify: `src/qwenpaw/extensions/__init__.py`
- Modify: `src/qwenpaw/app/channels/registry.py`
- Modify: `src/qwenpaw/config/utils.py`
- Modify: `src/qwenpaw/config/config.py`
- Modify: `src/qwenpaw/cli/channels_cmd.py`
- Test: `tests/unit/extensions/test_channels.py`
- Test: `tests/integration/test_channels_config.py`

- [ ] **Step 1: Write channel extension tests**

Add `tests/unit/extensions/test_channels.py`:

```python
from qwenpaw.extensions import BuiltinChannelSpec, ExtensionRegistry, FeaturePolicy
from qwenpaw.extensions.channels import ChannelExtensionRegistry


class ExampleChannel:
    pass


def test_builtin_channel_registration_is_separate_from_custom_sources():
    registry = ChannelExtensionRegistry()
    registry.register_builtin(
        BuiltinChannelSpec(
            key="example",
            factory=ExampleChannel,
            required=False,
            default_enabled=True,
            display_name="Example",
        )
    )
    registry.add_custom_source("/tmp/custom_channels")

    assert "example" in registry.builtin_specs
    assert registry.custom_sources == ["/tmp/custom_channels"]


def test_channel_policy_filters_non_required_builtin():
    registry = ChannelExtensionRegistry()
    registry.register_builtin(BuiltinChannelSpec(key="console", factory=ExampleChannel, required=True))
    registry.register_builtin(BuiltinChannelSpec(key="wechat", factory=ExampleChannel))

    filtered = registry.apply_policy(FeaturePolicy(disabled_channels={"console", "wechat"}))

    assert "console" in filtered
    assert "wechat" not in filtered


def test_extension_registry_registers_builtin_channel():
    registry = ExtensionRegistry()
    registry.channels.register_builtin(BuiltinChannelSpec(key="example", factory=ExampleChannel))

    assert "example" in registry.channels.builtin_specs
```

- [ ] **Step 2: Run channel tests to verify they fail**

Run: `pytest tests/unit/extensions/test_channels.py -v`

Expected: FAIL because `ChannelExtensionRegistry` is missing.

- [ ] **Step 3: Implement channel registry**

Create `src/qwenpaw/extensions/channels.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field

from .specs import BuiltinChannelSpec, FeaturePolicy


@dataclass
class ChannelExtensionRegistry:
    builtin_specs: dict[str, BuiltinChannelSpec] = field(default_factory=dict)
    custom_sources: list[str] = field(default_factory=list)

    def register_builtin(self, spec: BuiltinChannelSpec) -> None:
        self.builtin_specs[spec.key] = spec

    def replace_builtin(self, spec: BuiltinChannelSpec) -> None:
        self.builtin_specs[spec.key] = spec

    def disable_builtin(self, key: str) -> None:
        self.builtin_specs.pop(key, None)

    def add_custom_source(self, path: str) -> None:
        self.custom_sources.append(path)

    def apply_policy(self, policy: FeaturePolicy) -> dict[str, BuiltinChannelSpec]:
        result: dict[str, BuiltinChannelSpec] = {}
        for key, spec in self.builtin_specs.items():
            if spec.required or policy.is_channel_enabled(key):
                result[key] = spec
        return result
```

In `ExtensionRegistry.__init__`, add:

```python
from .channels import ChannelExtensionRegistry

self.channels = ChannelExtensionRegistry()
```

- [ ] **Step 4: Convert existing built-in channels to specs**

In `src/qwenpaw/app/channels/registry.py`, keep the current `_BUILTIN_SPECS` source of truth but route it through the extension registry:

```python
from qwenpaw.extensions import BuiltinChannelSpec, get_extension_registry, load_extensions


def _register_default_builtin_channels() -> None:
    load_extensions()
    extension_registry = get_extension_registry()
    if extension_registry.channels.builtin_specs:
        return
    for key, spec in _BUILTIN_SPECS.items():
        extension_registry.channels.register_builtin(
            BuiltinChannelSpec(
                key=key,
                factory=spec.channel_cls,
                config_model=spec.config_model,
                required=key in _REQUIRED_CHANNEL_KEYS,
                default_enabled=key in DEFAULT_ENABLED_CHANNEL_KEYS,
                display_name=getattr(spec, "display_name", key),
            )
        )
```

Where built-in specs are read, use:

```python
_register_default_builtin_channels()
extension_registry = get_extension_registry()
active_specs = extension_registry.channels.apply_policy(extension_registry.features)
```

Convert `BuiltinChannelSpec` back to the existing local channel spec shape in one helper:

```python
def _to_channel_registry_spec(spec: BuiltinChannelSpec):
    return ChannelRegistrySpec(
        key=spec.key,
        channel_cls=spec.factory,
        config_model=spec.config_model,
        required=spec.required,
        default_enabled=spec.default_enabled,
    )
```

Keep existing custom channel file loading under `CUSTOM_CHANNELS_DIR` and append any `extension_registry.channels.custom_sources`.

- [ ] **Step 5: Apply channel policy to config helpers**

In `src/qwenpaw/config/utils.py`, replace direct use of `QWENPAW_ENABLED_CHANNELS` and `QWENPAW_DISABLED_CHANNELS` with `EnvResolver(get_extension_registry().product)` and apply `registry.features.is_channel_enabled(key)` before returning channels.

In `src/qwenpaw/config/config.py`, when default channel config is generated, use the extension-aware channel registry so registered built-in channels appear in config and disabled channels are absent unless required.

- [ ] **Step 6: Run channel tests**

Run: `pytest tests/unit/extensions/test_channels.py tests/integration/test_channels_config.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add src/qwenpaw/extensions/channels.py src/qwenpaw/extensions/registry.py src/qwenpaw/extensions/__init__.py src/qwenpaw/app/channels/registry.py src/qwenpaw/config/utils.py src/qwenpaw/config/config.py src/qwenpaw/cli/channels_cmd.py tests/unit/extensions/test_channels.py
git commit -m "feat: make channels extension-aware"
```

Expected: commit succeeds.

## Task 9: Add Provider Registration and Policy

**Files:**

- Create: `src/qwenpaw/extensions/providers.py`
- Modify: `src/qwenpaw/extensions/registry.py`
- Modify: `src/qwenpaw/extensions/__init__.py`
- Modify: `src/qwenpaw/providers/provider_manager.py`
- Test: `tests/unit/extensions/test_providers.py`

- [ ] **Step 1: Write provider tests**

Add `tests/unit/extensions/test_providers.py`:

```python
from qwenpaw.extensions import FeaturePolicy
from qwenpaw.extensions.providers import ProviderExtensionRegistry


class ExampleProvider:
    id = "example"


class ReplacementProvider:
    id = "openai"


def test_provider_registry_filters_disabled_provider():
    registry = ProviderExtensionRegistry()
    defaults = {"openai": object, "openrouter": object}

    result = registry.apply_policy(defaults, FeaturePolicy(disabled_providers={"openrouter"}))

    assert set(result) == {"openai"}


def test_provider_registry_adds_and_replaces_provider():
    registry = ProviderExtensionRegistry()
    registry.register_provider("example", ExampleProvider)
    registry.replace_provider("openai", ReplacementProvider)

    result = registry.apply_policy({"openai": object}, FeaturePolicy())

    assert result["example"] is ExampleProvider
    assert result["openai"] is ReplacementProvider
```

- [ ] **Step 2: Run provider tests to verify they fail**

Run: `pytest tests/unit/extensions/test_providers.py -v`

Expected: FAIL because provider extension module is missing.

- [ ] **Step 3: Implement provider extension registry**

Create `src/qwenpaw/extensions/providers.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .specs import FeaturePolicy


@dataclass
class ProviderExtensionRegistry:
    added: dict[str, type[Any]] = field(default_factory=dict)
    replaced: dict[str, type[Any]] = field(default_factory=dict)

    def register_provider(self, provider_id: str, provider_cls: type[Any]) -> None:
        self.added[provider_id] = provider_cls

    def replace_provider(self, provider_id: str, provider_cls: type[Any]) -> None:
        self.replaced[provider_id] = provider_cls

    def apply_policy(
        self,
        defaults: dict[str, type[Any]],
        policy: FeaturePolicy,
    ) -> dict[str, type[Any]]:
        providers = {
            provider_id: provider_cls
            for provider_id, provider_cls in defaults.items()
            if policy.is_provider_enabled(provider_id)
        }
        providers.update(self.replaced)
        providers.update(self.added)
        return providers
```

In `ExtensionRegistry.__init__`, add:

```python
from .providers import ProviderExtensionRegistry

self.providers = ProviderExtensionRegistry()
```

- [ ] **Step 4: Integrate provider manager**

In `src/qwenpaw/providers/provider_manager.py`, replace one-by-one hardcoded built-in additions with a default map:

```python
default_providers = {
    PROVIDER_OPENAI: OpenAIProvider,
    PROVIDER_OPENROUTER: OpenRouterProvider,
    PROVIDER_DASHSCOPE: DashScopeProvider,
    PROVIDER_GEMINI: GeminiProvider,
}
```

Then apply the extension policy:

```python
from qwenpaw.extensions import get_extension_registry, load_extensions

load_extensions()
extension_registry = get_extension_registry()
for provider_id, provider_cls in extension_registry.providers.apply_policy(
    default_providers,
    extension_registry.features,
).items():
    self._add_builtin(provider_id, provider_cls)
```

Keep existing plugin provider registration after built-ins so plugin provider behavior remains compatible.

- [ ] **Step 5: Run provider tests**

Run: `pytest tests/unit/extensions/test_providers.py tests/unit/local_models/test_local_model_manager.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/qwenpaw/extensions/providers.py src/qwenpaw/extensions/registry.py src/qwenpaw/extensions/__init__.py src/qwenpaw/providers/provider_manager.py tests/unit/extensions/test_providers.py
git commit -m "feat: make providers extension-aware"
```

Expected: commit succeeds.

## Task 10: Add Feature and Plugin Policy Integration

**Files:**

- Create: `src/qwenpaw/extensions/features.py`
- Modify: `src/qwenpaw/extensions/registry.py`
- Modify: `src/qwenpaw/app/migration.py`
- Modify: `src/qwenpaw/plugins/loader.py`
- Test: `tests/unit/extensions/test_features.py`

- [ ] **Step 1: Write feature policy tests**

Add `tests/unit/extensions/test_features.py`:

```python
from qwenpaw.extensions import ExtensionRegistry, FeaturePolicy, PluginPolicy
from qwenpaw.extensions.features import (
    iter_plugin_search_paths,
    should_create_builtin_qa_agent,
    should_load_plugin,
)


def test_builtin_qa_agent_policy_defaults_to_enabled():
    registry = ExtensionRegistry()

    assert should_create_builtin_qa_agent(registry) is True


def test_builtin_qa_agent_can_be_disabled():
    registry = ExtensionRegistry()
    registry.configure_features(FeaturePolicy(disabled_features={"builtin_qa_agent"}))

    assert should_create_builtin_qa_agent(registry) is False


def test_plugin_policy_disabled_name_wins():
    registry = ExtensionRegistry()
    registry.configure_features(FeaturePolicy(disabled_plugins={"qwenpaw-pet"}))

    assert should_load_plugin(registry, "qwenpaw-pet") is False


def test_plugin_policy_allowed_list_blocks_others():
    registry = ExtensionRegistry()
    registry.configure_features(FeaturePolicy(allowed_plugins={"core-plugin"}))

    assert should_load_plugin(registry, "core-plugin") is True
    assert should_load_plugin(registry, "other-plugin") is False


def test_plugin_policy_exposes_extra_search_paths(tmp_path):
    registry = ExtensionRegistry()
    registry.configure_plugins(PluginPolicy(extra_search_paths=(tmp_path / "plugins",)))

    assert list(iter_plugin_search_paths(registry)) == [tmp_path / "plugins"]
```

- [ ] **Step 2: Run feature tests to verify they fail**

Run: `pytest tests/unit/extensions/test_features.py -v`

Expected: FAIL because feature helper module is missing.

- [ ] **Step 3: Implement feature helpers**

Create `src/qwenpaw/extensions/features.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .registry import ExtensionRegistry, get_extension_registry


def should_create_builtin_qa_agent(registry: ExtensionRegistry | None = None) -> bool:
    target = registry or get_extension_registry()
    return target.features.is_feature_enabled("builtin_qa_agent")


def should_load_plugin(registry: ExtensionRegistry | None, plugin_name: str) -> bool:
    target = registry or get_extension_registry()
    return target.features.is_plugin_enabled(plugin_name)


def iter_plugin_search_paths(registry: ExtensionRegistry | None = None) -> Iterable[Path]:
    target = registry or get_extension_registry()
    yield from target.plugins.extra_search_paths
```

Confirm `ExtensionRegistry.configure_plugins()` from Task 2 is present. The feature helpers depend on `registry.plugins.extra_search_paths` and `registry.features.is_plugin_enabled(name)`.

- [ ] **Step 4: Integrate QA agent migration**

In `src/qwenpaw/app/migration.py`, before creating the built-in QA agent:

```python
from qwenpaw.extensions.features import should_create_builtin_qa_agent

if not should_create_builtin_qa_agent():
    return
```

Add the check at the top of `ensure_qa_agent_exists()` so disabled policy prevents file creation and startup mutation.

- [ ] **Step 5: Integrate plugin loader policy**

In `src/qwenpaw/plugins/loader.py`, before loading each discovered plugin:

```python
from qwenpaw.extensions import get_extension_registry, load_extensions
from qwenpaw.extensions.features import should_load_plugin

load_extensions()
extension_registry = get_extension_registry()
if not should_load_plugin(extension_registry, plugin_name):
    continue
```

Add extra plugin search paths:

```python
from qwenpaw.extensions.features import iter_plugin_search_paths

for path in iter_plugin_search_paths(extension_registry):
    if path:
        plugin_search_paths.append(Path(path))
```

Keep channel source directories out of plugin discovery; they are consumed only by the channel registry.

- [ ] **Step 6: Run feature tests**

Run: `pytest tests/unit/extensions/test_features.py tests/integration/test_agents.py tests/integration/test_console_metadata.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add src/qwenpaw/extensions/features.py src/qwenpaw/extensions/registry.py src/qwenpaw/app/migration.py src/qwenpaw/plugins/loader.py tests/unit/extensions/test_features.py
git commit -m "feat: add extension feature policy"
```

Expected: commit succeeds.

## Task 11: Add Decorators, Dependency Injection, Lazy Proxies, and Feature Packs

**Files:**

- Create: `src/qwenpaw/extensions/decorators.py`
- Modify: `src/qwenpaw/extensions/registry.py`
- Modify: `src/qwenpaw/extensions/__init__.py`
- Test: `tests/unit/extensions/test_decorators.py`

- [ ] **Step 1: Write decorator and advanced API tests**

Add `tests/unit/extensions/test_decorators.py`:

```python
from qwenpaw.extensions import (
    ExtensionContext,
    ExtensionRegistry,
    FeaturePack,
    FeaturePolicy,
    ProductSpec,
    qwenpaw_extension,
    use_extension_registry,
)


def test_decorator_product_and_features_register_on_registry():
    registry = ExtensionRegistry()
    ext = qwenpaw_extension("my_product", registry=registry)

    @ext.product
    def product_spec():
        return ProductSpec(product_name="MyProduct", cli_name="myproduct")

    @ext.features
    def feature_policy():
        return FeaturePolicy(disabled_features={"builtin_qa_agent"})

    ext.apply()

    assert registry.product.product_name == "MyProduct"
    assert registry.features.is_feature_enabled("builtin_qa_agent") is False


def test_dependency_injection_passes_extension_context():
    registry = ExtensionRegistry()
    ext = qwenpaw_extension("my_product", registry=registry)
    seen = []

    @ext.configure
    def configure(context: ExtensionContext):
        seen.append(context.registry)

    ext.apply()

    assert seen == [registry]


def test_feature_pack_applies_policy():
    registry = ExtensionRegistry()
    pack = FeaturePack(
        name="minimal_console",
        policy=FeaturePolicy(disabled_channels={"wechat"}, disabled_providers={"openrouter"}),
    )

    registry.apply_feature_pack(pack)

    assert registry.features.is_channel_enabled("wechat") is False
    assert registry.features.is_provider_enabled("openrouter") is False
```

- [ ] **Step 2: Run decorator tests to verify they fail**

Run: `pytest tests/unit/extensions/test_decorators.py -v`

Expected: FAIL because decorator API is missing.

- [ ] **Step 3: Add context and feature pack specs**

In `src/qwenpaw/extensions/specs.py`, add:

```python
@dataclass(frozen=True)
class FeaturePack:
    name: str
    policy: FeaturePolicy = field(default_factory=FeaturePolicy)
```

Create `ExtensionContext` in `src/qwenpaw/extensions/registry.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtensionContext:
    registry: ExtensionRegistry

    @property
    def product(self):
        return self.registry.product
```

Add to `ExtensionRegistry`:

```python
def apply_feature_pack(self, pack: FeaturePack) -> None:
    self.configure_features(pack.policy)
```

- [ ] **Step 4: Implement decorator facade**

Create `src/qwenpaw/extensions/decorators.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from inspect import signature
from typing import Any

from .registry import ExtensionContext, ExtensionRegistry, get_extension_registry
from .specs import FeaturePolicy, ProductSpec


class ExtensionDecorator:
    def __init__(self, name: str, registry: ExtensionRegistry | None = None) -> None:
        self.name = name
        self.registry = registry or get_extension_registry()
        self._product_factories: list[Callable[..., ProductSpec]] = []
        self._feature_factories: list[Callable[..., FeaturePolicy]] = []
        self._configurators: list[Callable[..., Any]] = []

    def product(self, func: Callable[..., ProductSpec]) -> Callable[..., ProductSpec]:
        self._product_factories.append(func)
        return func

    def features(self, func: Callable[..., FeaturePolicy]) -> Callable[..., FeaturePolicy]:
        self._feature_factories.append(func)
        return func

    def configure(self, func: Callable[..., Any]) -> Callable[..., Any]:
        self._configurators.append(func)
        return func

    def apply(self) -> None:
        context = ExtensionContext(self.registry)
        for factory in self._product_factories:
            self.registry.configure_product(self._invoke(factory, context))
        for factory in self._feature_factories:
            self.registry.configure_features(self._invoke(factory, context))
        for configurator in self._configurators:
            self._invoke(configurator, context)

    def _invoke(self, func: Callable[..., Any], context: ExtensionContext) -> Any:
        params = signature(func).parameters
        if not params:
            return func()
        return func(context)


def qwenpaw_extension(
    name: str,
    registry: ExtensionRegistry | None = None,
) -> ExtensionDecorator:
    return ExtensionDecorator(name, registry)
```

Update exports.

- [ ] **Step 5: Add lazy proxy accessors**

In `src/qwenpaw/extensions/registry.py`, add:

```python
class LazyRegistryProxy:
    def __getattr__(self, name: str):
        return getattr(get_extension_registry(), name)


registry_proxy = LazyRegistryProxy()
```

Export `registry_proxy` as `extension_registry`.

- [ ] **Step 6: Run decorator tests**

Run: `pytest tests/unit/extensions/test_decorators.py tests/unit/extensions/test_registry.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add src/qwenpaw/extensions src/qwenpaw/extensions/__init__.py tests/unit/extensions/test_decorators.py
git commit -m "feat: add extension decorator APIs"
```

Expected: commit succeeds.

## Task 12: Add Unified Adapters Facade

**Files:**

- Create: `src/qwenpaw/extensions/adapters.py`
- Modify: `src/qwenpaw/extensions/registry.py`
- Modify: `src/qwenpaw/extensions/__init__.py`
- Modify: `src/qwenpaw/plugins/api.py`
- Test: `tests/unit/extensions/test_adapters.py`

- [ ] **Step 1: Write facade tests**

Add `tests/unit/extensions/test_adapters.py`:

```python
from fastapi import APIRouter

from qwenpaw.extensions import BuiltinChannelSpec, ExtensionRegistry
from qwenpaw.extensions.adapters import ExtensionAdapters


class ExampleProvider:
    pass


class ExampleChannel:
    pass


def test_adapters_register_router_provider_channel_and_command():
    registry = ExtensionRegistry()
    adapters = ExtensionAdapters(registry)
    router = APIRouter()

    adapters.router(router, prefix="/api/product")
    adapters.provider("example", ExampleProvider)
    adapters.builtin_channel(BuiltinChannelSpec(key="example", factory=ExampleChannel))
    adapters.cli_command("diagnose", "my_product.cli", "diagnose")

    assert registry.app.routers[0].prefix == "/api/product"
    assert registry.providers.added["example"] is ExampleProvider
    assert registry.channels.builtin_specs["example"].factory is ExampleChannel
    assert registry.cli.added["diagnose"] == ("my_product.cli", "diagnose")
```

- [ ] **Step 2: Run facade tests to verify they fail**

Run: `pytest tests/unit/extensions/test_adapters.py -v`

Expected: FAIL because `ExtensionAdapters` is missing.

- [ ] **Step 3: Implement adapters**

Create `src/qwenpaw/extensions/adapters.py`:

```python
from __future__ import annotations

from typing import Any

from .registry import ExtensionRegistry, get_extension_registry
from .specs import BuiltinChannelSpec


class ExtensionAdapters:
    def __init__(self, registry: ExtensionRegistry | None = None) -> None:
        self.registry = registry or get_extension_registry()

    def router(self, router: Any, prefix: str = "", tags: list[str] | None = None) -> None:
        self.registry.app.add_router(router, prefix=prefix, tags=tags)

    def provider(self, provider_id: str, provider_cls: type[Any]) -> None:
        self.registry.providers.register_provider(provider_id, provider_cls)

    def replace_provider(self, provider_id: str, provider_cls: type[Any]) -> None:
        self.registry.providers.replace_provider(provider_id, provider_cls)

    def builtin_channel(self, spec: BuiltinChannelSpec) -> None:
        self.registry.channels.register_builtin(spec)

    def cli_command(self, name: str, module: str, attribute: str) -> None:
        self.registry.cli.add_command(name, module, attribute)

    def startup_hook(self, hook: Any) -> None:
        self.registry.app.add_startup_hook(hook)

    def shutdown_hook(self, hook: Any) -> None:
        self.registry.app.add_shutdown_hook(hook)
```

Update `ExtensionRegistry.__init__`:

```python
from .adapters import ExtensionAdapters

self.adapters = ExtensionAdapters(self)
```

If this import causes a cycle, create adapters lazily:

```python
@property
def adapters(self):
    from .adapters import ExtensionAdapters
    return ExtensionAdapters(self)
```

- [ ] **Step 4: Bridge existing plugin API**

In `src/qwenpaw/plugins/api.py`, add a property:

```python
from qwenpaw.extensions import get_extension_registry


@property
def extensions(self):
    return get_extension_registry().adapters
```

This lets existing plugins access the unified facade through `api.extensions` without losing current plugin API methods.

- [ ] **Step 5: Run facade tests**

Run: `pytest tests/unit/extensions/test_adapters.py tests/integration/test_console_metadata.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/qwenpaw/extensions/adapters.py src/qwenpaw/extensions/registry.py src/qwenpaw/extensions/__init__.py src/qwenpaw/plugins/api.py tests/unit/extensions/test_adapters.py
git commit -m "feat: expose unified extension adapters"
```

Expected: commit succeeds.

## Task 13: Complete Environment Variable Migration Audit

**Files:**

- Modify: files reported by the audit command under `src/qwenpaw/`
- Test: `tests/unit/extensions/test_env.py`

- [ ] **Step 1: Add exhaustive env suffix test**

Extend `tests/unit/extensions/test_env.py`:

```python
def test_all_known_qwenpaw_env_suffixes_support_downstream_prefix(monkeypatch):
    suffixes = [
        "WORKING_DIR",
        "SECRET_DIR",
        "CONSOLE_STATIC_DIR",
        "AUTH_ENABLED",
        "AUTH_PASSWORD",
        "CORS_ORIGINS",
        "OPENAPI_ENABLED",
        "BROWSER_HEADLESS",
        "TOOL_GUARD_ENABLED",
        "SKILL_HUB_ENABLED",
        "LLM_RATE_LIMIT_REQUESTS",
        "BACKUP_DIR",
    ]
    resolver = EnvResolver(
        ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
    )
    for suffix in suffixes:
        monkeypatch.setenv(f"MYPRODUCT_{suffix}", f"business-{suffix}")
        monkeypatch.setenv(f"QWENPAW_{suffix}", f"qwenpaw-{suffix}")
        assert resolver.get(suffix) == f"business-{suffix}"
```

- [ ] **Step 2: Run env tests**

Run: `pytest tests/unit/extensions/test_env.py -v`

Expected: PASS.

- [ ] **Step 3: Audit all literal env usage**

Run:

```bash
rg -n "\"QWENPAW_|'QWENPAW_|\"COPAW_|'COPAW_" src/qwenpaw
```

Expected: remaining matches are limited to:

- `src/qwenpaw/extensions/env.py`
- `src/qwenpaw/extensions/loader.py`
- compatibility comments or user-facing docs
- tests

For every production code match that reads environment values directly, replace with:

```python
from qwenpaw.extensions import EnvResolver, get_extension_registry

_env = EnvResolver(get_extension_registry().product)
value = _env.get("CANONICAL_SUFFIX")
```

- [ ] **Step 4: Run targeted tests**

Run: `pytest tests/unit/extensions/test_env.py tests/unit/extensions/test_product_constants.py tests/integration/test_console.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/qwenpaw tests/unit/extensions/test_env.py
git commit -m "feat: migrate qwenpaw env access to resolver"
```

Expected: commit succeeds.

## Task 14: Add SDK Documentation

**Files:**

- Create: `docs/extensions-sdk.md`
- Create: `website/public/docs/extensions-sdk.zh.md`
- Create: `website/public/docs/extensions-sdk.en.md`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write complete docs**

Create `docs/extensions-sdk.md` with these sections:

```markdown
# QwenPaw Extension SDK

## What This SDK Solves

The extension SDK lets a downstream product use QwenPaw as a Python dependency while changing product identity, paths, environment variable prefixes, CLI commands, built-in channels, providers, plugins, FastAPI routes, logging, agent persona files, and frontend assets through stable APIs.

## Installation Model

Downstream packages register through:

```toml
[project.entry-points."qwenpaw.extensions"]
my_product = "my_product_qwenpaw_extension:register"
```

## ProductSpec

```python
from qwenpaw.extensions import ProductSpec

ProductSpec(
    product_name="MyProduct",
    product_version="2.0.0",
    module_alias="my_product",
    cli_name="myproduct",
    skill_cli_name="myproduct-skill",
    env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"),
    working_dir="~/.myproduct",
    secret_dir="~/.myproduct.secret",
    console_static_dir="/opt/myproduct/console",
)
```

## Environment Variable Priority

For suffix `WORKING_DIR`, the resolver checks `MYPRODUCT_WORKING_DIR`, then `QWENPAW_WORKING_DIR`, then `COPAW_WORKING_DIR`. The same rule applies to every existing QwenPaw environment variable suffix.

## Registry API

```python
def register(registry):
    registry.configure_product(...)
    registry.configure_features(...)
    registry.cli.add_command("diagnose", "my_product.cli", "diagnose")
```

## Decorator API

```python
from qwenpaw.extensions import qwenpaw_extension

ext = qwenpaw_extension("my_product")
```

## Fluent Builder

```python
def register(registry):
    registry.extension("my_product").product(name="MyProduct").env_prefix("MYPRODUCT")
```

## Manifest API

```yaml
product:
  name: MyProduct
  env_prefixes: [MYPRODUCT, QWENPAW, COPAW]
```

## Built-In Channels

Use `BuiltinChannelSpec` for product-provided built-in channels. File-based custom channels remain separate and are loaded from configured source directories.

## Providers

Use `registry.providers.register_provider`, `replace_provider`, and `FeaturePolicy.disabled_providers`.

## Plugins and Existing QwenPaw Extensions

Use `registry.adapters` or `api.extensions` from existing plugins to access the unified facade.

## FastAPI

Use `registry.app.add_router`, startup hooks, shutdown hooks, and middleware hooks. Routers are included before the frontend catch-all route.

## Logging

Use `LoggingSpec` to set namespace, file path, format, level, or handler factory.

## Frontend Replacement

Set `ProductSpec.console_static_dir` or the highest-priority `*_CONSOLE_STATIC_DIR` environment variable.

## Feature Policy

Use `FeaturePolicy` to disable built-in QA agent, channels, providers, plugins, and other feature gates exposed by QwenPaw.

## Testing Extensions

Use `ExtensionRegistry` and `use_extension_registry` in pytest to isolate global state.
```

Create Chinese and English website docs with the same API examples. The Chinese document must state that product names and prefixes are examples only and are never hardcoded by the SDK.

- [ ] **Step 2: Include docs in package data if needed**

If `pyproject.toml` package data only includes `qwenpaw/docs/*.md`, add a packaging entry for repository docs only if the build process expects SDK docs in the wheel. Otherwise leave package data unchanged and keep the docs as repository documentation.

- [ ] **Step 3: Run documentation scans**

Run:

```bash
rg -n "MyProduct|MYPRODUCT" docs/extensions-sdk.md website/public/docs/extensions-sdk.zh.md website/public/docs/extensions-sdk.en.md
rg -n "GDE|gde" docs/extensions-sdk.md website/public/docs/extensions-sdk.zh.md website/public/docs/extensions-sdk.en.md
```

Expected: the first command finds example usage; the second command prints no matches.

- [ ] **Step 4: Commit**

Run:

```bash
git add docs/extensions-sdk.md website/public/docs/extensions-sdk.zh.md website/public/docs/extensions-sdk.en.md pyproject.toml
git commit -m "docs: add extension SDK guide"
```

Expected: commit succeeds.

## Task 15: Add End-to-End Extension Smoke Tests

**Files:**

- Create: `tests/integration/test_extension_sdk.py`
- Modify: `tests/conftest.py` if test app fixtures need registry isolation.

- [ ] **Step 1: Write integration smoke tests**

Add `tests/integration/test_extension_sdk.py`:

```python
from fastapi import APIRouter

from qwenpaw.extensions import (
    BuiltinChannelSpec,
    ExtensionRegistry,
    FeaturePolicy,
    ProductSpec,
    use_extension_registry,
)


class ProductChannel:
    pass


class ProductProvider:
    pass


def test_extension_sdk_smoke_registers_core_surfaces(tmp_path):
    registry = ExtensionRegistry()
    router = APIRouter()

    @router.get("/health")
    def health():
        return {"status": "ok"}

    registry.configure_product(
        ProductSpec(
            product_name="MyProduct",
            cli_name="myproduct",
            env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"),
            working_dir=tmp_path / "work",
            secret_dir=tmp_path / "secret",
            console_static_dir=tmp_path / "console",
        )
    )
    registry.configure_features(
        FeaturePolicy(
            disabled_features={"builtin_qa_agent"},
            disabled_channels={"wechat"},
            disabled_providers={"openrouter"},
        )
    )
    registry.app.add_router(router, prefix="/api/product")
    registry.channels.register_builtin(BuiltinChannelSpec(key="product", factory=ProductChannel))
    registry.providers.register_provider("product", ProductProvider)
    registry.cli.add_command("diagnose", "my_product.cli", "diagnose")

    with use_extension_registry(registry):
        assert registry.product.product_name == "MyProduct"
        assert registry.features.is_feature_enabled("builtin_qa_agent") is False
        assert "product" in registry.channels.builtin_specs
        assert registry.providers.added["product"] is ProductProvider
        assert registry.cli.added["diagnose"] == ("my_product.cli", "diagnose")
```

- [ ] **Step 2: Run smoke tests**

Run: `pytest tests/integration/test_extension_sdk.py -v`

Expected: PASS.

- [ ] **Step 3: Run extension unit suite**

Run: `pytest tests/unit/extensions -v`

Expected: PASS.

- [ ] **Step 4: Run focused existing regression suite**

Run:

```bash
pytest \
  tests/unit/workspace/test_cli_agent_id.py \
  tests/integration/test_channels_config.py \
  tests/integration/test_console_metadata.py \
  tests/integration/test_agents.py \
  -v
```

Expected: PASS.

- [ ] **Step 5: Run formatting and whitespace checks**

Run: `git diff --check`

Expected: no output and exit code 0.

- [ ] **Step 6: Commit**

Run:

```bash
git add tests/integration/test_extension_sdk.py tests/conftest.py
git commit -m "test: add extension SDK smoke coverage"
```

Expected: commit succeeds.

## Task 16: Final Self-Review and Release Notes

**Files:**

- Modify: `docs/extensions-sdk.md`
- Modify: `website/public/docs/extensions-sdk.zh.md`
- Modify: `website/public/docs/extensions-sdk.en.md`

- [ ] **Step 1: Verify requirement coverage**

Check every requested capability maps to an implemented surface:

- Module name: `ProductSpec.module_alias`
- Product name/version: `ProductSpec.product_name` and `product_version`
- Working/config paths: `ProductSpec` path fields and `EnvResolver`
- Agent persona: `ProductSpec.agent_prompt_files`
- Skill CLI name: `ProductSpec.skill_cli_name`
- Logging: `LoggingSpec`
- Env names: `EnvResolver`
- Click commands: `CliRegistry`
- Built-in channels: `BuiltinChannelSpec` and `ChannelExtensionRegistry`
- Feature disablement: `FeaturePolicy`
- LLM providers: `ProviderExtensionRegistry`
- Plugins: plugin policy and adapters
- FastAPI: `AppExtensionRegistry`
- Frontend replacement: `ProductSpec.console_static_dir` and `resolve_console_static_dir`

- [ ] **Step 2: Scan for accidental downstream hardcoding**

Run:

```bash
rg -n "GDE|gde" src/qwenpaw/extensions tests/unit/extensions tests/integration/test_extension_sdk.py docs/extensions-sdk.md website/public/docs/extensions-sdk.zh.md website/public/docs/extensions-sdk.en.md
```

Expected: no matches.

- [ ] **Step 3: Scan for deferred-work markers in implemented files**

Run:

```bash
python -c "from pathlib import Path; pats=['TB'+'D','TO'+'DO','implement '+'later']; paths=['src/qwenpaw/extensions','tests/unit/extensions','docs/extensions-sdk.md','website/public/docs/extensions-sdk.zh.md','website/public/docs/extensions-sdk.en.md']; hits=[]; [hits.append((str(p), i, pat)) for root in paths for p in ([Path(root)] if Path(root).is_file() else Path(root).rglob('*')) if p.is_file() for i,line in enumerate(p.read_text(encoding='utf-8', errors='ignore').splitlines(), 1) for pat in pats if pat in line]; print('\\n'.join(f'{p}:{i}:{pat}' for p,i,pat in hits)); raise SystemExit(1 if hits else 0)"
```

Expected: no matches.

- [ ] **Step 4: Run final test command**

Run:

```bash
pytest tests/unit/extensions tests/integration/test_extension_sdk.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit final doc refinements**

Run:

```bash
git add docs/extensions-sdk.md website/public/docs/extensions-sdk.zh.md website/public/docs/extensions-sdk.en.md
git commit -m "docs: finalize extension SDK coverage"
```

Expected: commit succeeds if files changed. If no files changed, skip the commit and record that docs already match the final API.

## Rollback Plan

Each task is committed separately. If a regression appears after one task, revert only that task's commit and keep earlier extension primitives intact. The most sensitive integration points are `constant.py`, `app/_app.py`, `provider_manager.py`, and `app/channels/registry.py`; verify those files with targeted tests before continuing after a revert.

## Verification Checklist

- [ ] `pytest tests/unit/extensions -v`
- [ ] `pytest tests/integration/test_extension_sdk.py -v`
- [ ] `pytest tests/unit/workspace/test_cli_agent_id.py -v`
- [ ] `pytest tests/integration/test_channels_config.py -v`
- [ ] `pytest tests/integration/test_console_metadata.py -v`
- [ ] `pytest tests/integration/test_agents.py -v`
- [ ] `git diff --check`

## Handoff Notes

- The extension SDK must remain product-neutral. Product identifiers in tests and docs are examples only.
- Do not replace the existing plugin API; expose it through `ExtensionAdapters` and keep old calls working.
- Built-in channels and file-based custom channels are different concepts. Register product-owned built-in channels through `BuiltinChannelSpec`; load file-based custom channels through configured source directories.
- Keep `QWENPAW_*` and `COPAW_*` compatible fallbacks. Downstream prefixes always win when present.
- Prefer adding small adapter calls at existing hardcoded entry points over moving large blocks of existing QwenPaw logic.
