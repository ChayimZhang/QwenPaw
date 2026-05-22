# QwenPaw Extension SDK

Extension SDK 用来把 QwenPaw 当成 Python 依赖库使用，同时在少量通用接入点上开放产品级扩展能力。它的目标是让业务团队通过独立扩展包完成品牌、目录、命令、路由、channel、provider、插件和功能开关配置，而不是直接深度修改 QwenPaw 源码。

本文中的 `MyProduct`、`MYPRODUCT`、`myproduct` 都是占位示例。SDK 不会硬编码任何业务关键字；真实产品名、环境变量前缀、目录和命令名都应由业务扩展包或 manifest 提供。

## 设计原则

- QwenPaw 保持上游友好：核心代码只保留通用 hook、registry、policy 和 loader。
- 业务扩展独立发布：通过 Python entry point 或 manifest 加载。
- 业务前缀优先：所有原本 `QWENPAW_*` 环境变量都可以通过业务前缀覆盖，随后再回落到 `QWENPAW_*` 和 legacy `COPAW_*`。
- 内置 channel 与 custom channel 分开：产品级内置 channel 使用 `BuiltinChannelSpec` 注册，文件目录式 custom channel 仍使用 custom channel source。
- 扩展能力统一入口：业务扩展可以用 decorator、fluent builder、`ExtensionAdapters` 或 YAML manifest，插件内也能通过 `PluginApi.extensions` 访问同一套入口。

## 加载方式

最推荐的方式是业务侧创建一个独立 Python 包，例如 `my_product_qwenpaw_extension`，并在 `pyproject.toml` 注册 entry point：

```toml
[project.entry-points."qwenpaw.extensions"]
my_product = "my_product_qwenpaw_extension.extension:extension"
```

entry point 可以指向一个可调用对象。`qwenpaw_extension()` 返回的 decorator 对象本身就是 callable，因此可以直接作为入口。也可以指向一个普通函数：

```python
from qwenpaw.extensions import ExtensionRegistry


def register(registry: ExtensionRegistry) -> None:
    registry.extension("my_product").product(name="MyProduct")
```

QwenPaw 启动时会调用 `load_extensions()`。测试、脚本或宿主产品也可以手动调用：

```python
from qwenpaw.extensions import load_extensions

load_extensions(config_path="/etc/my-product/qwenpaw-extension.yaml")
```

如果没有显式传入 `config_path`，loader 会查找 `EXTENSION_CONFIG` 后缀对应的环境变量。当前产品前缀为 `MYPRODUCT` 时，优先级为：

```text
MYPRODUCT_EXTENSION_CONFIG
QWENPAW_EXTENSION_CONFIG
COPAW_EXTENSION_CONFIG
```

## 最小 Decorator 示例

Decorator 适合业务团队使用：声明式、集中、可读性强，也方便拆分多个函数。

```python
from pathlib import Path

from fastapi import APIRouter
from qwenpaw.extensions import (
    BuiltinChannelSpec,
    FeaturePolicy,
    LoggingSpec,
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

## Manifest 配置

YAML manifest 适合无代码或低代码开关，尤其适合禁用能力、替换产品名和路径、配置日志。它不能直接注册 Python callable，因此 CLI 命令、provider、FastAPI router、内置 channel 等仍建议放在 Python 扩展包中。

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

## 环境变量前缀

`ProductSpec.env_prefixes` 决定所有 QwenPaw 环境变量的查找顺序。业务前缀必须放在第一位：

```python
ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
```

当 QwenPaw 读取后缀 `WORKING_DIR` 时，会依次检查：

```text
MYPRODUCT_WORKING_DIR
QWENPAW_WORKING_DIR
COPAW_WORKING_DIR
```

这适用于现有的 QwenPaw 环境变量后缀，例如 `LOG_LEVEL`、`SECRET_DIR`、`EXTENSION_CONFIG`、provider key、API 配置等。业务环境变量命中后，默认 QwenPaw 变量不会再覆盖它。

如果业务扩展需要自己读取同一规则，可以使用：

```python
from qwenpaw.extensions import EnvResolver, get_extension_registry

product = get_extension_registry().product
resolver = EnvResolver(product)
value = resolver.get("WORKING_DIR")
```

## 产品信息与路径

`ProductSpec` 支持这些产品级字段：

| 字段 | 作用 |
| --- | --- |
| `product_name` | UI、日志提示、FastAPI app 名称等面向用户的产品名 |
| `product_version` | 业务产品版本；`/api/version` 会在 `product_version` 字段中返回 |
| `module_alias` | 业务模块别名；运行时通过 `qwenpaw.constant.MODULE_NAME` 暴露 |
| `cli_name` | 根 CLI 名称，影响 click 命令帮助与入口封装 |
| `skill_cli_name` | 给原 `skills` 命令增加一个产品侧别名 |
| `working_dir` / `secret_dir` | 默认工作目录与密钥目录 |
| `backup_dir` / `plugins_dir` / `custom_channels_dir` / `media_dir` / `local_provider_dir` | 派生资源目录 |
| `console_static_dir` | 整体替换前端静态资源目录 |
| `agent_prompt_files` | Agent 人设提示文件查找顺序 |

## 日志

代码方式：

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

如果业务已有 logging handler，可以传入 `handler_factory`：

```python
def handler_factory(namespace, file_path, fmt, level):
    return [build_company_handler(namespace=namespace, level=level)]

registry.configure_logging(LoggingSpec(handler_factory=handler_factory))
```

## CLI 与 Skill CLI

根命令名来自 `ProductSpec.cli_name`。业务包通常在自己的 console script 中调用 QwenPaw click root：

```toml
[project.scripts]
myproduct = "qwenpaw.cli.main:main"
```

增删改 click 子命令：

```python
def configure(context) -> None:
    api = context.adapters
    api.cli_command("diagnose", "my_product.cli", "diagnose")
    api.replace_cli_command("models", "my_product.cli", "models")
    api.disable_cli_command("update")
    api.cli_alias("skills", "abilities")
```

`skill_cli_name` 是更简单的 Skill CLI 名称配置：

```python
ProductSpec(skill_cli_name="myproduct-skills")
```

这会保留原 `skills` 命令，同时增加一个产品侧别名。

## Agent 人设

人设查找文件由 `ProductSpec.agent_prompt_files` 控制。默认仍兼容 QwenPaw 的 `AGENTS.md`、`SOUL.md`、`PROFILE.md`，业务产品可以把自己的文件放在前面：

```python
ProductSpec(agent_prompt_files=("MY_PRODUCT.md", "AGENTS.md"))
```

迁移、默认 Agent 创建和配置默认值都会使用这组文件顺序。禁用内置 QA Agent 可以配置：

```python
FeaturePolicy(disabled_features={"builtin_qa_agent"})
```

## Channel 扩展

内置 channel 与 custom channel 是两类能力：

- 内置 channel：由扩展包代码注册，适合产品长期维护的一等 channel。
- custom channel：从目录中发现 Python 文件，适合用户或团队局部扩展。

注册产品级内置 channel：

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

替换或禁用：

```python
api.replace_builtin_channel(BuiltinChannelSpec(key="wechat", factory=MyWeChat))
api.disable_channel("discord")
```

添加 custom channel 目录：

```python
api.custom_channel_source("/opt/myproduct/custom_channels")
```

## LLM Provider

新增、替换、禁用 provider：

```python
api.provider("my-cloud", MyProductProvider)
api.replace_provider("openai", MyProductProvider)
api.disable_provider("ollama")
```

`FeaturePolicy.disabled_providers` 与 manifest 中的 `features.disabled_providers` 会在 provider manager 构建内置 provider 映射时生效。

## 插件

扩展 SDK 不替代原插件系统，而是作为统一入口把插件发现与策略开放出来：

```python
api.plugin_search_path("/opt/myproduct/plugins")
api.disable_plugin("community-demo")
api.allow_plugin("my-product-console")
```

插件内部可以通过 `PluginApi.extensions` 继续访问同一套 adapters：

```python
from qwenpaw.plugins.api import PluginApi


def activate(api: PluginApi) -> None:
    api.extensions.router(router, prefix="/api/my-plugin")
```

## FastAPI 与前端资源

注册 FastAPI router、生命周期 hook 和 middleware：

```python
api.router(router, prefix="/api/my-product", tags=["my-product"])
api.startup_hook(on_startup)
api.shutdown_hook(on_shutdown)
api.middleware_hook(add_middleware)
```

替换整个前端资源目录：

```python
ProductSpec(console_static_dir="/opt/myproduct/console")
```

目录中应包含构建后的前端静态文件，例如 `index.html` 和 assets。QwenPaw 会优先使用该目录。

## Fluent Builder

如果扩展很简单，也可以使用 fluent API：

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

## 测试扩展包

业务扩展包建议使用独立 registry 做单元测试：

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

## 能力覆盖清单

| 诉求 | SDK 入口 |
| --- | --- |
| 模块名称 | `ProductSpec.module_alias` / `qwenpaw.constant.MODULE_NAME` |
| 产品名称、版本 | `ProductSpec.product_name` / `ProductSpec.product_version` |
| 工作目录、配置路径 | `ProductSpec.*_dir` / `*_EXTENSION_CONFIG` |
| Agent 人设 | `ProductSpec.agent_prompt_files` |
| Skill CLI 名称 | `ProductSpec.skill_cli_name` |
| 日志名称、路径、格式 | `LoggingSpec` / manifest `logging` |
| 环境变量名称 | `ProductSpec.env_prefixes` / `EnvResolver` |
| click 命令增删改 | `registry.cli` / `ExtensionAdapters.cli_*` |
| 内置 channel 增删改 | `BuiltinChannelSpec` / `ExtensionAdapters.builtin_channel` |
| 禁用原功能 | `FeaturePolicy.disabled_features` / manifest `features` |
| LLM Provider 增删改 | `registry.providers` / `ExtensionAdapters.provider` |
| 插件增删改 | `PluginPolicy` / `PluginApi.extensions` |
| FastAPI 路由和生命周期 | `registry.app` / `ExtensionAdapters.router/startup_hook` |
| 整体替换前端 | `ProductSpec.console_static_dir` |

