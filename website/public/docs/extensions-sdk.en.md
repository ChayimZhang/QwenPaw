# QwenPaw Extension SDK

The Extension SDK lets a product use QwenPaw as a Python dependency while exposing product-level extension points through a small, upstream-friendly API surface. Product teams can ship an independent extension package for branding, paths, commands, routes, channels, providers, plugins, and feature policies instead of deeply modifying QwenPaw itself.

`MyProduct`, `MYPRODUCT`, and `myproduct` in this guide are placeholders. The SDK does not hardcode any business keyword. Real product names, environment prefixes, paths, and command names should come from your extension package or manifest.

## Design Goals

- Keep QwenPaw upstream-friendly: the core only contains generic hooks, registries, policies, and loaders.
- Ship product behavior separately: load it from Python entry points or a manifest.
- Prefer business environment prefixes: every existing `QWENPAW_*` variable can be overridden by a product prefix, then falls back to `QWENPAW_*` and legacy `COPAW_*`.
- Separate built-in channels from custom channels: product-owned built-ins use `BuiltinChannelSpec`; file-system custom channels still use custom channel source directories.
- Use one extension entry point: decorators, the fluent builder, `ExtensionAdapters`, YAML manifests, and `PluginApi.extensions` all target the same registry.

## Loading Extensions

The recommended packaging model is a separate Python distribution, for example `my_product_qwenpaw_extension`, with an entry point in `pyproject.toml`:

```toml
[project.entry-points."qwenpaw.extensions"]
my_product = "my_product_qwenpaw_extension.extension:extension"
```

The entry point can point to any callable. The object returned by `qwenpaw_extension()` is callable, so it can be used directly. A plain function also works:

```python
from qwenpaw.extensions import ExtensionRegistry


def register(registry: ExtensionRegistry) -> None:
    registry.extension("my_product").product(name="MyProduct")
```

QwenPaw calls `load_extensions()` during startup. Tests, scripts, or host products can call it directly:

```python
from qwenpaw.extensions import load_extensions

load_extensions(config_path="/etc/my-product/qwenpaw-extension.yaml")
```

If `config_path` is omitted, the loader looks for the `EXTENSION_CONFIG` suffix. When the active product prefix is `MYPRODUCT`, the lookup order is:

```text
MYPRODUCT_EXTENSION_CONFIG
QWENPAW_EXTENSION_CONFIG
COPAW_EXTENSION_CONFIG
```

## Minimal Decorator Example

Decorators are the easiest API for product teams: they keep product, policy, and runtime hooks declarative and close together.

```python
from pathlib import Path

from fastapi import APIRouter
from qwenpaw.extensions import (
    BuiltinChannelSpec,
    FeaturePolicy,
    ProductSpec,
    qwenpaw_extension,
)

from my_product.channels.workchat import WorkChatChannel, WorkChatConfig
from my_product.llm import MyProductProvider

extension = qwenpaw_extension("my_product")


@extension.product
def product() -> ProductSpec:
    return ProductSpec(
        product_name="MyProduct",
        product_version="2.0.0",
        module_alias="my_product",
        cli_name="myproduct",
        skill_cli_name="myproduct-skills",
        env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"),
        working_dir="~/.myproduct",
        secret_dir="~/.myproduct.secret",
        console_static_dir="/opt/myproduct/console",
        agent_prompt_files=("MY_PRODUCT.md", "AGENTS.md"),
    )


@extension.features
def feature_policy() -> FeaturePolicy:
    return FeaturePolicy(
        disabled_features={"builtin_qa_agent"},
        disabled_channels={"discord"},
        disabled_providers={"ollama"},
        disabled_plugins={"community-demo"},
    )


@extension.configure
def configure(context) -> None:
    api = context.adapters

    router = APIRouter()

    @router.get("/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    api.router(router, prefix="/api/my-product", tags=["my-product"])
    api.cli_command("diagnose", "my_product.cli", "diagnose")
    api.provider("my-cloud", MyProductProvider)
    api.replace_provider("openai", MyProductProvider)
    api.plugin_search_path(Path("/opt/myproduct/plugins"))

    api.builtin_channel(
        BuiltinChannelSpec(
            key="workchat",
            factory=WorkChatChannel,
            config_model=WorkChatConfig,
            default_enabled=True,
            display_name="Work Chat",
        )
    )
```

## Manifest Configuration

YAML manifests are best for no-code or low-code policy, especially feature disabling, product identity, paths, and logging. They cannot register Python callables, so CLI commands, providers, FastAPI routers, and built-in channels should still live in a Python extension package.

```yaml
product:
  name: MyProduct
  version: 2.0.0
  module_alias: my_product
  cli_name: myproduct
  skill_cli_name: myproduct-skills
  env_prefixes: [MYPRODUCT, QWENPAW, COPAW]
  working_dir: ~/.myproduct
  secret_dir: ~/.myproduct.secret
  backup_dir: ~/.myproduct/backups
  plugins_dir: ~/.myproduct/plugins
  custom_channels_dir: ~/.myproduct/custom_channels
  media_dir: ~/.myproduct/media
  local_provider_dir: ~/.myproduct/local_models
  console_static_dir: /opt/myproduct/console
  agent_prompt_files:
    - MY_PRODUCT.md
    - AGENTS.md

logging:
  namespace: myproduct
  file_path: ~/.myproduct/logs/runtime.log
  format: "%(asctime)s %(levelname)s [%(name)s] %(message)s"
  level: INFO

features:
  disabled_features:
    - builtin_qa_agent
  disabled_channels:
    - discord
  disabled_providers:
    - ollama
  disabled_plugins:
    - community-demo
  allowed_plugins:
    - my-product-console

plugins:
  extra_search_paths:
    - /opt/myproduct/plugins
```

## Environment Variable Prefixes

`ProductSpec.env_prefixes` controls lookup order for all QwenPaw environment variables. Put the business prefix first:

```python
ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
```

When QwenPaw reads the suffix `WORKING_DIR`, it checks:

```text
MYPRODUCT_WORKING_DIR
QWENPAW_WORKING_DIR
COPAW_WORKING_DIR
```

The same rule applies to existing suffixes such as `LOG_LEVEL`, `SECRET_DIR`, `EXTENSION_CONFIG`, provider keys, and API settings. Once a business-prefixed value is found, the default QwenPaw value cannot override it.

Extensions can use the same resolver:

```python
from qwenpaw.extensions import EnvResolver, get_extension_registry

product = get_extension_registry().product
resolver = EnvResolver(product)
value = resolver.get("WORKING_DIR")
```

## Product Identity And Paths

`ProductSpec` supports these product-level fields:

| Field | Purpose |
| --- | --- |
| `product_name` | User-facing product name for UI, logs, and FastAPI metadata |
| `product_version` | Business product version; `/api/version` returns it as `product_version` |
| `module_alias` | Business module alias; exposed as `qwenpaw.constant.MODULE_NAME` |
| `cli_name` | Root CLI name for Click help and wrappers |
| `skill_cli_name` | Adds a product alias for the original `skills` command |
| `working_dir` / `secret_dir` | Default working and secret directories |
| `backup_dir` / `plugins_dir` / `custom_channels_dir` / `media_dir` / `local_provider_dir` | Derived resource directories |
| `console_static_dir` | Replaces the entire frontend static directory |
| `agent_prompt_files` | Agent persona file lookup order |

## Logging

Configure logging in code:

```python
from qwenpaw.extensions import LoggingSpec, get_extension_registry

registry = get_extension_registry()
registry.configure_logging(
    LoggingSpec(
        namespace="myproduct",
        file_path="~/.myproduct/logs/runtime.log",
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        level="INFO",
    )
)
```

If your product already owns logging handlers, provide a `handler_factory`:

```python
def handler_factory(namespace, file_path, fmt, level):
    return [build_company_handler(namespace=namespace, level=level)]

registry.configure_logging(LoggingSpec(handler_factory=handler_factory))
```

## CLI And Skill CLI

The root command name comes from `ProductSpec.cli_name`. Product packages usually expose their own console script that points to the QwenPaw Click root:

```toml
[project.scripts]
myproduct = "qwenpaw.cli.main:main"
```

Add, replace, disable, or alias Click subcommands:

```python
def configure(context) -> None:
    api = context.adapters
    api.cli_command("diagnose", "my_product.cli", "diagnose")
    api.replace_cli_command("models", "my_product.cli", "models")
    api.disable_cli_command("update")
    api.cli_alias("skills", "abilities")
```

For the skill command, `skill_cli_name` is the simplest option:

```python
ProductSpec(skill_cli_name="myproduct-skills")
```

This keeps the original `skills` command and adds the product alias.

## Agent Persona

Persona file lookup is controlled by `ProductSpec.agent_prompt_files`. QwenPaw remains compatible with `AGENTS.md`, `SOUL.md`, and `PROFILE.md`, while products can put their own file first:

```python
ProductSpec(agent_prompt_files=("MY_PRODUCT.md", "AGENTS.md"))
```

Migration, default agent creation, and config defaults all use this order. Disable the built-in QA Agent with:

```python
FeaturePolicy(disabled_features={"builtin_qa_agent"})
```

## Channels

Built-in channels and custom channels are different extension surfaces:

- Built-in channels are registered by extension package code and are suitable for first-class product integrations.
- Custom channels are discovered from directories and are suitable for local or team-level file-based extensions.

Register a product-owned built-in channel:

```python
from qwenpaw.extensions import BuiltinChannelSpec


def register_routes(app) -> None:
    app.include_router(router, prefix="/api/workchat")


api.builtin_channel(
    BuiltinChannelSpec(
        key="workchat",
        factory=WorkChatChannel,
        config_model=WorkChatConfig,
        default_enabled=True,
        route_hook=register_routes,
        display_name="Work Chat",
    )
)
```

Replace or disable channels:

```python
api.replace_builtin_channel(BuiltinChannelSpec(key="wechat", factory=MyWeChat))
api.disable_channel("discord")
```

Add a custom channel source directory:

```python
api.custom_channel_source("/opt/myproduct/custom_channels")
```

## LLM Providers

Add, replace, or disable providers:

```python
api.provider("my-cloud", MyProductProvider)
api.replace_provider("openai", MyProductProvider)
api.disable_provider("ollama")
```

`FeaturePolicy.disabled_providers` and manifest `features.disabled_providers` are applied when the provider manager builds the provider map.

## Plugins

The Extension SDK does not replace the existing plugin system. It exposes plugin search paths and policy through the same product extension entry point:

```python
api.plugin_search_path("/opt/myproduct/plugins")
api.disable_plugin("community-demo")
api.allow_plugin("my-product-console")
```

Plugins can continue through the same adapters via `PluginApi.extensions`:

```python
from qwenpaw.plugins.api import PluginApi


def activate(api: PluginApi) -> None:
    api.extensions.router(router, prefix="/api/my-plugin")
```

## FastAPI And Frontend Assets

Register FastAPI routers, lifecycle hooks, and middleware:

```python
api.router(router, prefix="/api/my-product", tags=["my-product"])
api.startup_hook(on_startup)
api.shutdown_hook(on_shutdown)
api.middleware_hook(add_middleware)
```

Replace the entire frontend static directory:

```python
ProductSpec(console_static_dir="/opt/myproduct/console")
```

The directory should contain built frontend assets such as `index.html` and asset files. QwenPaw uses this directory first when it is configured.

## Fluent Builder

For small extensions, the fluent API can be enough:

```python
def register(registry):
    (
        registry.extension("my_product")
        .product(name="MyProduct", version="2.0.0", cli_name="myproduct")
        .env_prefix("MYPRODUCT")
        .working_dir("~/.myproduct")
        .secret_dir("~/.myproduct.secret")
        .console_static_dir("/opt/myproduct/console")
        .skill_cli_name("myproduct-skills")
        .disable_features("builtin_qa_agent")
        .disable_channels("discord")
        .disable_providers("ollama")
        .cli_command("diagnose", "my_product.cli", "diagnose")
    )
```

## Testing Extensions

Product extension packages should test with a scoped registry:

```python
from qwenpaw.extensions import ExtensionRegistry, use_extension_registry
from my_product_qwenpaw_extension.extension import extension


def test_extension_registers_product():
    registry = ExtensionRegistry()
    extension(registry)

    assert registry.product.product_name == "MyProduct"
    assert registry.features.is_feature_enabled("builtin_qa_agent") is False


def test_runtime_with_scoped_registry():
    registry = ExtensionRegistry()
    extension(registry)

    with use_extension_registry(registry):
        from qwenpaw.extensions import get_extension_registry

        assert get_extension_registry().product.cli_name == "myproduct"
```

## Capability Map

| Requirement | SDK Entry |
| --- | --- |
| Module name | `ProductSpec.module_alias` / `qwenpaw.constant.MODULE_NAME` |
| Product name and version | `ProductSpec.product_name` / `ProductSpec.product_version` |
| Working directory and config path | `ProductSpec.*_dir` / `*_EXTENSION_CONFIG` |
| Agent persona | `ProductSpec.agent_prompt_files` |
| Skill CLI name | `ProductSpec.skill_cli_name` |
| Log name, file path, and format | `LoggingSpec` / manifest `logging` |
| Environment variable names | `ProductSpec.env_prefixes` / `EnvResolver` |
| Click command add/replace/disable | `registry.cli` / `ExtensionAdapters.cli_*` |
| Built-in channel add/replace/disable | `BuiltinChannelSpec` / `ExtensionAdapters.builtin_channel` |
| Disable original features | `FeaturePolicy.disabled_features` / manifest `features` |
| LLM provider add/replace/disable | `registry.providers` / `ExtensionAdapters.provider` |
| Plugin add/remove/policy | `PluginPolicy` / `PluginApi.extensions` |
| FastAPI routes and lifecycle | `registry.app` / `ExtensionAdapters.router/startup_hook` |
| Full frontend replacement | `ProductSpec.console_static_dir` |

