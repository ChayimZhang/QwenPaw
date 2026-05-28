# QwenPaw Extension SDK 使用指南

本文档面向基于 QwenPaw 做产品封装的业务团队，说明当前 Extension SDK 保留的全部扩展能力、字段含义、加载方式和推荐用法。

当前 SDK 的定位是“轻量产品封装层”：尽量少改 QwenPaw 原生代码，只开放产品配置、功能开关、channel 注册、AgentRunner hook、console 静态资源替换等通用能力。日志配置、插件策略、CLI 命令扩展、FastAPI 通用路由扩展、LLM Provider 扩展、skill 服务扩展、Control command 扩展、环境变量前缀替换等能力已经从 SDK 中移除。

## 架构设计

Extension SDK 以 `ExtensionRegistry` 为统一注册中心。业务可以通过 manifest、Python API、声明式对象或装饰器把扩展注册进 registry；QwenPaw 原生代码只在少量入口读取 registry 中的配置。

```text
业务项目
  ├─ manifest.yaml / pyproject.toml entry point
  └─ extension.py / decorators / ExtensionSpec
        │
        ▼
qwenpaw.extensions.ExtensionRegistry
  ├─ product: ProductSpec
  ├─ features: FeaturePolicy
  ├─ channels: ChannelExtensionRegistry
  └─ runner: RunnerExtensionRegistry
        │
        ▼
QwenPaw 原生入口
  ├─ qwenpaw.constant 读取产品名、CLI 名、目录、console 路径等
  ├─ channel 加载逻辑读取内置 channel 与 custom channel source
  ├─ AgentRunner.query_handler 读取 query 托管与 query stream hooks
  └─ console 静态资源入口读取 console_static_dir
```

### 当前保留能力清单

| 能力 | 用途 | 主要模块 / 类 | 支持方式 |
| --- | --- | --- | --- |
| 产品配置 | 配置产品名、模块别名、CLI 名、版本、用户目录、配置目录、console 目录、Agent prompt 文件等 | `specs.py` / `ProductSpec` | manifest、API、声明式、装饰器、Builder |
| 功能开关 | 禁用 SDK 目前支持的通用功能，或禁用指定 channel | `specs.py` / `FeaturePolicy` | manifest、API、声明式、装饰器、Builder |
| 内置 channel 注册 | 注册新的内置 channel，或替换已有内置 channel | `specs.py` / `BuiltinChannelSpec`、`channels.py` | API、声明式、装饰器 |
| custom channel source | 增加业务 custom channel 搜索目录 | `adapters.py`、`channels.py` | API、装饰器 |
| AgentRunner query 托管 | 业务完全接管一次 `AgentRunner.query_handler` 的输出逻辑 | `runner.py` / `RunnerQueryContext` | API、声明式、装饰器 |
| AgentRunner query stream hooks | 观察 QwenPaw 原生最终流式输出，适合统计、埋点、审计 | `runner.py` / `RunnerQueryContext` | API、声明式、装饰器 |
| console 静态资源替换 | 指定业务自己的前端静态资源目录；不指定时使用 QwenPaw 原生 console | `app.py`、`ProductSpec.console_static_dir` | manifest、API、声明式、装饰器、Builder |
| manifest 自动发现 | 通过包内资源、项目根目录或环境变量发现配置 | `loader.py` | pyproject entry point、自动发现、显式 API |

## 加载与发现

QwenPaw 启动时会调用 `load_extensions()`。业务通常不需要手动调用；如果是独立测试或嵌入式使用，也可以显式调用。

### 推荐方式：包内 manifest entry point

把 `manifest.yaml` 作为包内资源打进 wheel，并在 `pyproject.toml` 中声明：

```toml
[project.entry-points."qwenpaw.extension_manifests"]
my_product = "my_product:manifest.yaml"

[project.entry-points."qwenpaw.extensions"]
my_product = "my_product.extension:extension"
```

含义：

| entry point | 作用 | 适合内容 |
| --- | --- | --- |
| `qwenpaw.extension_manifests` | 从已安装包中读取 manifest 资源 | 产品名、目录、功能开关、console 路径等静态配置 |
| `qwenpaw.extensions` | 加载 Python 注册函数、装饰器对象或 `ExtensionSpec` | channel、runner hook、动态版本号等需要代码表达的配置 |

`my_product = "my_product:manifest.yaml"` 表示从 Python 包 `my_product` 内读取 `manifest.yaml`。推荐把 manifest 放进包内，而不是依赖安装后的当前工作目录，避免多个产品都叫 `manifest.yaml` 时发生路径冲突。

### 自动发现 manifest

SDK 也支持从当前目录或启动脚本路径向上查找以下文件：

| 文件名 |
| --- |
| `manifest.yaml` |
| `manifest.yml` |
| `extension.yaml` |
| `extension.yml` |
| `qwenpaw-extension.yaml` |
| `qwenpaw-extension.yml` |

只有 YAML 根节点包含 `product` 或 `features` 时才会被当作 Extension manifest。这个机制适合源码调试；正式 wheel 推荐使用包内资源 entry point。

### 环境变量指定 manifest

可以通过以下环境变量指定 manifest 路径：

| 环境变量 | 说明 |
| --- | --- |
| `QWENPAW_EXTENSION_CONFIG` | 指向一个 extension manifest 文件 |
| `COPAW_EXTENSION_CONFIG` | 兼容入口，指向一个 extension manifest 文件 |

当前 SDK 已经移除“业务环境变量前缀替换”能力，因此这里不会自动识别业务自定义前缀。

### 加载顺序

`load_extensions()` 的默认加载顺序如下：

1. 读取 `qwenpaw.extension_manifests` entry points。
2. 读取环境变量或自动发现得到的 manifest。
3. 读取 `qwenpaw.extensions` Python entry points。

因此推荐把简单静态配置放在 manifest 中，把需要覆盖 manifest 或需要动态计算的内容放在 Python entry point 中。Python API 会在后面执行，可以对 manifest 配置做增量更新。

## manifest.yaml

manifest 是最推荐的基础配置方式，适合产品名、目录、版本、console 静态目录、功能开关等稳定配置。

```yaml
product:
  name: "MyProduct"
  version: "1.2.3"
  module_alias: "my_product"
  cli_name: "myproduct"
  working_dir: "~/.myproduct"
  secret_dir: "~/.myproduct.secret"
  backup_dir: "~/.myproduct/backups"
  plugins_dir: "~/.myproduct/plugins"
  custom_channels_dir: "~/.myproduct/custom_channels"
  media_dir: "~/.myproduct/media"
  local_provider_dir: "~/.myproduct/local_models"
  console_static_dir: "console/dist"
  agent_prompt_files:
    - "AGENTS.md"
    - "SOUL.md"
    - "PROFILE.md"

features:
  disabled_features:
    - "builtin_qa_agent"
  disabled_channels:
    - "discord"
```

manifest 中的路径字段支持相对路径。相对路径会按 manifest 文件所在目录解析，适合包内资源或业务项目内资源。`agent_prompt_files` 表示工作目录内需要维护的 Agent prompt 文件名或路径，当前不会按 manifest 所在目录重写。

### product 字段

| manifest 字段 | `ProductSpec` 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | `product_name` | `str` | `QwenPaw` | 产品显示名。会影响 CLI 帮助中的主说明、产品常量等产品级显示。 |
| `version` | `product_version` | `str \| null` | `None` | 产品版本。可以不写，在 Python entry point 中从 `__version__` 动态注入。 |
| `module_alias` | `module_alias` | `str` | `qwenpaw` | 产品模块别名，用于产品级常量和部分模块身份配置；不再承担全量文案品牌替换职责。 |
| `cli_name` | `cli_name` | `str` | `qwenpaw` | 产品 CLI 名称，例如业务脚本入口 `myproduct`。 |
| `working_dir` | `working_dir` | `str \| Path` | `~/.qwenpaw` | 产品工作目录。未显式配置子目录时，子目录会跟随它派生。 |
| `secret_dir` | `secret_dir` | `str \| Path` | `~/.qwenpaw.secret` | 产品密钥目录。 |
| `backup_dir` | `backup_dir` | `str \| Path \| null` | `<working_dir>/backups` | 备份目录常量。 |
| `plugins_dir` | `plugins_dir` | `str \| Path \| null` | `<working_dir>/plugins` | 原生插件目录常量。SDK 不再提供插件策略扩展能力。 |
| `custom_channels_dir` | `custom_channels_dir` | `str \| Path \| null` | `<working_dir>/custom_channels` | custom channel 默认目录。 |
| `media_dir` | `media_dir` | `str \| Path \| null` | `<working_dir>/media` | 媒体文件目录常量。 |
| `local_provider_dir` | `local_provider_dir` | `str \| Path \| null` | `<working_dir>/local_models` | 本地模型目录常量。SDK 不再提供 LLM Provider 注册或品牌化能力。 |
| `console_static_dir` | `console_static_dir` | `str \| Path \| null` | `None` | 业务 console 静态资源目录。不配置时使用 QwenPaw 自带 console。 |
| `agent_prompt_files` | `agent_prompt_files` | `list[str]` | `["AGENTS.md", "SOUL.md", "PROFILE.md"]` | Agent 人设相关 prompt 文件列表。 |

`ProductSpec` 是不可变 dataclass。通过 `registry.update_product()` 或 `adapters.product()` 增量更新时，如果只更新 `working_dir`，且子目录仍是旧 `working_dir` 派生出的默认值，SDK 会自动把这些默认子目录迁移到新的 `working_dir` 下；已经显式配置过的子目录会被保留。

### features 字段

| manifest 字段 | `FeaturePolicy` 字段 | 类型 | 说明 |
| --- | --- | --- | --- |
| `disabled_features` | `disabled_features` | `list[str]` | 禁用 SDK 支持的通用功能。 |
| `disabled_channels` | `disabled_channels` | `list[str]` | 禁用指定 channel key。 |

当前可配置的 `disabled_features`：

| feature key | 作用 |
| --- | --- |
| `builtin_qa_agent` | 禁用 QwenPaw 初始化时内置 QA agent workspace 的创建。 |
| `builtin_channels` | 禁用非 required 的内置 channel 加载。 |
| `custom_channels` | 禁用 custom channel source 加载。 |

注意：`disabled_channels` 只影响 channel key；`BuiltinChannelSpec(required=True)` 的内置 channel 不会被 `builtin_channels` 或 `disabled_channels` 禁用。

## Python API 总览

业务可以组合使用 manifest 与 Python API。推荐原则是：静态配置写 manifest；需要代码、动态计算或注册函数的能力写 Python extension。

### ExtensionAdapters 方法清单

`ExtensionAdapters` 是业务最常用的命令式入口，可以通过 `registry.adapters` 或装饰器 context 获取。

| 方法 | 作用 | 示例 |
| --- | --- | --- |
| `product(**changes)` | 增量更新 `ProductSpec` 字段 | `adapters.product(product_version=__version__)` |
| `product_version(version)` | 只更新产品版本 | `adapters.product_version(__version__)` |
| `agent_prompt_files(*paths)` | 更新 Agent prompt 文件列表 | `adapters.agent_prompt_files("AGENTS.md")` |
| `disable_feature(name)` | 增量禁用一个 feature | `adapters.disable_feature("builtin_qa_agent")` |
| `disable_channel(key)` | 增量禁用一个 channel | `adapters.disable_channel("discord")` |
| `builtin_channel(spec)` | 注册一个新的内置 channel；已有同 key 时不覆盖 | `adapters.builtin_channel(spec)` |
| `replace_builtin_channel(spec)` | 替换一个内置 channel；已有同 key 时覆盖 | `adapters.replace_builtin_channel(spec)` |
| `custom_channel_source(path)` | 增加 custom channel 搜索目录 | `adapters.custom_channel_source("channels")` |
| `query_handler_hook(hook)` | 注册 query handler 托管 hook | `adapters.query_handler_hook(handle_query)` |
| `before_query_stream_hook(hook)` | 注册原生 query stream 前置 hook | `adapters.before_query_stream_hook(before)` |
| `query_stream_message_hook(hook)` | 注册原生 query stream 消息观察 hook | `adapters.query_stream_message_hook(observe)` |
| `after_query_stream_hook(hook)` | 注册原生 query stream 收尾 hook | `adapters.after_query_stream_hook(after)` |

### 装饰器用法

装饰器适合把业务扩展拆成多个函数，可读性强，也便于测试。`extension` 对象本身可以作为 `qwenpaw.extensions` entry point 暴露。

`qwenpaw_extension(name)` 返回 `ExtensionDecorator`，支持的方法：

| 方法 | 用途 | 函数返回值或签名 |
| --- | --- | --- |
| `@extension.product` | 注册产品配置 | `() -> ProductSpec` |
| `@extension.features` | 注册功能开关 | `() -> FeaturePolicy` |
| `@extension.configure` | 执行命令式配置 | `(context: ExtensionContext) -> Any` |
| `@extension.query_handler_hook` | 注册 query handler 托管 hook | `(context: RunnerQueryContext) -> Any` |
| `@extension.before_query_stream_hook` | 注册原生 query stream 前置 hook | `(context: RunnerQueryContext) -> Any` |
| `@extension.query_stream_message_hook` | 注册原生 query stream 消息 hook | `(context, msg, last) -> Any` |
| `@extension.after_query_stream_hook` | 注册原生 query stream 收尾 hook | `(context, error) -> Any` |

`ExtensionContext` 字段：

| 字段 / 属性 | 类型 | 说明 |
| --- | --- | --- |
| `name` | `str` | 当前 extension 名称。 |
| `registry` | `ExtensionRegistry` | 当前注册中心。 |
| `adapters` | `ExtensionAdapters` | 命令式适配器入口，等价于 `registry.adapters`。 |

```python
from qwenpaw.extensions import ProductSpec, FeaturePolicy, qwenpaw_extension

extension = qwenpaw_extension("my_product")


@extension.product
def product():
    return ProductSpec(
        product_name="MyProduct",
        module_alias="my_product",
        cli_name="myproduct",
        working_dir="~/.myproduct",
        secret_dir="~/.myproduct.secret",
    )


@extension.features
def features():
    return FeaturePolicy(
        disabled_features={"builtin_qa_agent"},
        disabled_channels={"discord"},
    )
```

### configure 装饰器

`@extension.configure` 适合集中调用 `ExtensionAdapters`，尤其是注册 channel 或从业务模块读取动态版本号。

```python
from ._version import __version__
from qwenpaw.extensions import qwenpaw_extension

extension = qwenpaw_extension("my_product")


@extension.configure
def configure(context):
    context.adapters.product_version(__version__)
    context.adapters.disable_channel("discord")
```

### 声明式 ExtensionSpec

声明式对象适合把完整扩展能力作为一个对象返回，尤其适合希望减少装饰器状态、便于单元测试的场景。

```python
from qwenpaw.extensions import (
    ExtensionSpec,
    ProductSpec,
    FeaturePolicy,
    RunnerPatch,
)


def before_stream(context):
    return {"request_id": getattr(context.request, "request_id", None)}


extension = ExtensionSpec(
    name="my_product",
    product=ProductSpec(product_name="MyProduct", cli_name="myproduct"),
    features=FeaturePolicy(disabled_features={"builtin_qa_agent"}),
    runner_patch=RunnerPatch(before_query_stream_hooks=(before_stream,)),
)
```

也可以在 entry point 函数中返回一个或多个 `ExtensionSpec`。

```python
def extension(registry):
    return [
        ExtensionSpec(
            name="my_product",
            product=ProductSpec(product_name="MyProduct"),
        )
    ]
```

### Builder 用法

Builder 是轻量链式 API，适合简单测试或启动脚本内快速配置。

```python
from qwenpaw.extensions import get_extension_registry

registry = get_extension_registry()
registry.extension("my_product") \
    .product("MyProduct", version="1.2.3", cli_name="myproduct") \
    .working_dir("~/.myproduct") \
    .secret_dir("~/.myproduct.secret") \
    .console_static_dir("console/dist") \
    .disable_features("builtin_qa_agent") \
    .disable_channels("discord")
```

### 低层 registry API

低层 API 适合测试或嵌入式场景：

```python
from qwenpaw.extensions import (
    ExtensionRegistry,
    ProductSpec,
    FeaturePolicy,
    use_extension_registry,
)

registry = ExtensionRegistry()
registry.configure_product(ProductSpec(product_name="MyProduct"))
registry.configure_features(FeaturePolicy(disabled_channels={"discord"}))

with use_extension_registry(registry):
    # 这里运行的 QwenPaw 代码会读取这个临时 registry。
    ...
```

## 内置 Channel 与 Custom Channel

### BuiltinChannelSpec 字段

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `key` | `str` | 必填 | channel 唯一 key。为空会抛出 `ValueError`。 |
| `factory` | `Callable[..., Any]` | 必填 | 创建 channel 实例的工厂函数或类。 |
| `config_model` | `type[Any] \| None` | `None` | channel 配置模型。 |
| `required` | `bool` | `False` | 是否必需。为 `True` 时不会被 `builtin_channels` 或 `disabled_channels` 禁用。 |
| `default_enabled` | `bool` | `False` | 是否默认启用。 |
| `route_hook` | `Callable[..., Any] \| None` | `None` | channel 自己的路由挂载 hook，仅用于该 channel 的原生集成，不是通用 FastAPI 扩展入口。 |
| `display_name` | `str \| None` | `None` | channel 展示名称。 |
| `metadata` | `dict[str, Any]` | `{}` | 业务自定义元数据。 |

### ChannelExtensionRegistry 方法

多数业务不需要直接操作 `ChannelExtensionRegistry`，推荐使用 `ExtensionAdapters`。如果需要低层控制，可以通过 `get_extension_registry().channels` 访问。

| 方法 | 作用 |
| --- | --- |
| `register_builtin(spec)` | 注册内置 channel；同 key 已存在时保留原有 spec。 |
| `replace_builtin(spec)` | 注册或替换内置 channel；同 key 已存在时覆盖。 |
| `disable_builtin(key)` | 禁用指定内置 channel key，本质上写入 `disabled_channels`。 |
| `add_custom_source(path)` | 增加 custom channel 搜索目录。 |
| `apply_policy(policy)` | 根据 `FeaturePolicy` 过滤内置 channel，返回可加载的 spec 字典。 |

### 注册新的内置 channel

```python
from qwenpaw.extensions import BuiltinChannelSpec, qwenpaw_extension

extension = qwenpaw_extension("my_product")


@extension.configure
def configure(context):
    context.adapters.builtin_channel(
        BuiltinChannelSpec(
            key="my_channel",
            factory=MyChannel,
            config_model=MyChannelConfig,
            default_enabled=True,
            display_name="My Channel",
            metadata={"owner": "business-team"},
        )
    )
```

`builtin_channel()` 只在 key 不存在时注册；如果要替换 QwenPaw 已有内置 channel，请使用 `replace_builtin_channel()`。

```python
@extension.configure
def configure(context):
    context.adapters.replace_builtin_channel(
        BuiltinChannelSpec(
            key="dingtalk",
            factory=MyDingTalkChannel,
            config_model=MyDingTalkConfig,
            default_enabled=True,
        )
    )
```

### 增加 custom channel source

```python
@extension.configure
def configure(context):
    context.adapters.custom_channel_source("channels")
```

如果 `features.disabled_features` 中包含 `custom_channels`，custom channel source 不会被加载。

## AgentRunner Hook

AgentRunner 相关 hook 分为两类：

1. `query_handler_hook`：业务完全托管 `AgentRunner.query_handler`。一旦某个 hook 返回非 `None`，QwenPaw 原生 query_handler 后续逻辑不会执行。
2. query stream 组合 hook：只观察 QwenPaw 原生最终执行流，也就是 `run_mission_phase` / `_stream_printing_messages_interruptible` 这段产生的 `(msg, last)`，适合统计和审计。

### RunnerQueryContext 字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `request` | `Any` | `query_handler` 入参 request。 |
| `runner` | `Any` | 当前 `AgentRunner` 实例。 |
| `agent` | `Any` | 当前 agent。`query_handler_hook` 阶段还未进入原生 agent 构造时可能为 `None`。 |
| `workspace` | `Any` | 当前 workspace。 |
| `msgs` | `Any` | 当前消息列表或上下文消息。 |
| `kwargs` | `MappingProxyType` | 额外参数的只读映射。 |
| `state` | `dict[str, Any]` | hook 间共享状态。`before_query_stream_hook` 返回 dict 时会合并到这里。 |

### RunnerPatch 字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `query_handler_hooks` | `tuple[Callable, ...]` | query handler 托管 hook 列表。 |
| `before_query_stream_hooks` | `tuple[Callable, ...]` | 原生 query stream 开始前执行。 |
| `query_stream_message_hooks` | `tuple[Callable, ...]` | 每个原生流式消息执行一次，参数为 `(context, msg, last)`。 |
| `after_query_stream_hooks` | `tuple[Callable, ...]` | 原生 query stream 结束或异常后执行，参数为 `(context, error)`。 |

### 完全托管 query_handler

适合业务需要自己实现 query_handler 全部逻辑的场景。hook 可以是同步函数或异步函数；返回第一个非 `None` 结果后，后续 hook 与 QwenPaw 原生逻辑都不会继续托管这次请求。

```python
from qwenpaw.extensions import RunnerQueryContext, qwenpaw_extension

extension = qwenpaw_extension("my_product")


@extension.query_handler_hook
async def handle_query(context: RunnerQueryContext):
    request = context.request
    workspace = context.workspace

    async def stream():
        yield {"role": "assistant", "content": f"Handled by {workspace}"}, True

    return stream()
```

`query_handler_hook` 返回值支持：

| 返回值 | 说明 |
| --- | --- |
| `None` | 不托管，交给下一个 hook 或 QwenPaw 原生逻辑。 |
| async iterable | 异步产出 `(msg, last)`。 |
| iterable | 同步产出 `(msg, last)`。 |
| `(msg, last)` | 单条结果，`last` 必须是 `bool`。 |
| `[msg, last]` | 单条结果，`last` 必须是 `bool`。 |

如果业务完全托管 query handler，业务需要自己实现统计或观察逻辑；SDK 不会再对业务托管流做 query stream 组合 hook。

### 观察原生 query stream

这是业务之前源码改造中类似下面逻辑的 SDK 化表达：

```python
async with track_query_stats(xxx) as tracker:
    async for msg, last in _stream_printing_messages_interruptible(...):
        tracker.observe_message(msg, last)
        yield msg, last
```

用 SDK 可以改成：

```python
from qwenpaw.extensions import RunnerQueryContext, qwenpaw_extension

extension = qwenpaw_extension("my_product")


@extension.before_query_stream_hook
async def open_tracker(context: RunnerQueryContext):
    tracker_cm = track_query_stats(context.request)
    tracker = await tracker_cm.__aenter__()
    return {"tracker_cm": tracker_cm, "tracker": tracker}


@extension.query_stream_message_hook
async def observe_message(context: RunnerQueryContext, msg, last: bool):
    tracker = context.state.get("tracker")
    if tracker is not None:
        tracker.observe_message(msg, last)


@extension.after_query_stream_hook
async def close_tracker(context: RunnerQueryContext, error: BaseException | None):
    tracker_cm = context.state.get("tracker_cm")
    if tracker_cm is not None:
        await tracker_cm.__aexit__(
            type(error) if error else None,
            error,
            error.__traceback__ if error else None,
        )
```

这组 hook 只观察 QwenPaw 原生最终流式输出，不观察 query handler 前面提前 `yield` 的内容，也不观察业务 `query_handler_hook` 完全托管后的内容。

## Console 静态资源替换

如果业务配置了 `console_static_dir`，QwenPaw FastAPI app 会优先使用业务目录作为 console 静态资源：

```yaml
product:
  console_static_dir: "console/dist"
```

或者：

```python
@extension.configure
def configure(context):
    context.adapters.product(console_static_dir="console/dist")
```

不配置 `console_static_dir` 时，启动后应使用 QwenPaw 自带 console。业务 wheel 中如果需要携带自己的 console，请把静态目录作为包内资源打包，并在 manifest 中使用相对路径指向它。

## 辅助 API Reference

这些 API 已经从 `qwenpaw.extensions` 导出，适合测试、嵌入式启动或高级集成使用。

### manifest 与加载 API

| API | 作用 | 常见场景 |
| --- | --- | --- |
| `load_extensions(...)` | 按 entry point、manifest、Python extension 加载扩展 | 启动时显式加载，或测试时加载指定 registry |
| `discover_extension_manifest(search_paths=None)` | 从目录向上查找 extension manifest | 源码调试或自定义启动器 |
| `apply_manifest(registry, path)` | 从文件路径读取并应用 manifest | 测试或命令行工具 |
| `apply_manifest_data(registry, data, base_dir=None)` | 从 dict 数据应用 manifest | 单元测试或动态生成配置 |
| `apply_manifest_resource(registry, package, resource)` | 从包内资源读取并应用 manifest | wheel 安装后的包内 manifest |

`load_extensions()` 重要参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `registry` | `None` | 指定 registry；不传时使用全局 registry。 |
| `config_path` | `None` | 显式 manifest 路径，优先级高于自动发现。 |
| `auto_discover` | `True` | 是否启用当前目录 / 启动脚本路径向上查找。 |
| `manifest_search_paths` | `None` | 指定自动发现的起点路径。 |
| `include_entry_points` | `True` | 是否加载 package entry points。 |
| `force` | `False` | 是否强制重复加载同一个 registry。 |

### registry API

| API | 作用 |
| --- | --- |
| `get_extension_registry()` | 获取全局 `ExtensionRegistry`。 |
| `extension_registry` | 全局 registry 的 lazy proxy。 |
| `use_extension_registry(registry)` | 临时切换当前上下文 registry，常用于测试。 |
| `ExtensionRegistry.configure_product(spec)` | 替换当前产品配置。 |
| `ExtensionRegistry.update_product(**changes)` | 增量更新产品配置。 |
| `ExtensionRegistry.configure_features(policy)` | 合并功能禁用策略。 |
| `ExtensionRegistry.apply_spec(spec)` | 应用一个 `ExtensionSpec`。 |
| `ExtensionRegistry.extension(name)` | 创建链式 `ExtensionBuilder`。 |
| `ExtensionRegistry.adapters` | 获取 `ExtensionAdapters`。 |

### feature 辅助函数

这些函数用于 QwenPaw 原生代码或业务测试中判断当前功能是否启用。

| API | 作用 |
| --- | --- |
| `EXTENSION_FEATURES` | SDK 当前支持的 feature key 清单。 |
| `ExtensionFeature` | feature 描述 dataclass，字段为 `key`、`description`、`default_enabled`。 |
| `is_feature_enabled(key, registry=None)` | 判断指定 feature 是否启用。 |
| `should_create_builtin_qa_agent(registry=None)` | 判断是否创建内置 QA agent workspace。 |
| `should_load_builtin_channel(key, required=False, registry=None)` | 判断指定内置 channel 是否加载。 |
| `should_load_custom_channels(registry=None)` | 判断是否加载 custom channel source。 |

### RunnerExtensionRegistry 方法

业务通常通过装饰器或 adapters 注册 runner hook；低层方法如下：

| 方法 | 作用 |
| --- | --- |
| `add_query_handler_hook(hook)` | 注册 query handler 托管 hook。 |
| `add_before_query_stream_hook(hook)` | 注册原生 query stream 前置 hook。 |
| `add_query_stream_message_hook(hook)` | 注册原生 query stream 消息 hook。 |
| `add_after_query_stream_hook(hook)` | 注册原生 query stream 收尾 hook。 |
| `get_query_handler_result(...)` | 执行托管 hook，返回第一个非 `None` 结果。 |
| `iter_query_handler_result(result)` | 把托管 hook 返回值规范化为 `(msg, last)` async 迭代。 |
| `query_stream_lifecycle(...)` | 原生 query stream 三段式 hook 的 async context manager。 |

## 完整 Demo 示例

以下示例展示 manifest 与 Python API 组合使用：manifest 负责静态产品配置，Python extension 负责动态版本号、channel 注册和 AgentRunner hook。

### 包结构

```text
my_product/
  pyproject.toml
  src/
    my_product/
      __init__.py
      _version.py
      manifest.yaml
      extension.py
      console/
        dist/
          index.html
```

### `_version.py`

```python
__version__ = "1.2.3"
```

### `manifest.yaml`

```yaml
product:
  name: "MyProduct"
  module_alias: "my_product"
  cli_name: "myproduct"
  working_dir: "~/.myproduct"
  secret_dir: "~/.myproduct.secret"
  console_static_dir: "console/dist"
  agent_prompt_files:
    - "AGENTS.md"
    - "SOUL.md"
    - "PROFILE.md"

features:
  disabled_features:
    - "builtin_qa_agent"
  disabled_channels:
    - "discord"
```

### `extension.py`

```python
from ._version import __version__
from qwenpaw.extensions import BuiltinChannelSpec, qwenpaw_extension

extension = qwenpaw_extension("my_product")


@extension.configure
def configure(context):
    context.adapters.product_version(__version__)
    context.adapters.builtin_channel(
        BuiltinChannelSpec(
            key="my_channel",
            factory=MyChannel,
            config_model=MyChannelConfig,
            default_enabled=True,
            display_name="My Channel",
        )
    )


@extension.before_query_stream_hook
async def before_stream(context):
    tracker_cm = track_query_stats(context.request)
    tracker = await tracker_cm.__aenter__()
    return {"tracker_cm": tracker_cm, "tracker": tracker}


@extension.query_stream_message_hook
async def observe_stream_message(context, msg, last):
    tracker = context.state.get("tracker")
    if tracker is not None:
        tracker.observe_message(msg, last)


@extension.after_query_stream_hook
async def after_stream(context, error):
    tracker_cm = context.state.get("tracker_cm")
    if tracker_cm is not None:
        await tracker_cm.__aexit__(
            type(error) if error else None,
            error,
            error.__traceback__ if error else None,
        )
```

### `pyproject.toml`

```toml
[project]
name = "my-product"
dynamic = ["version"]

[tool.setuptools.dynamic]
version = {attr = "my_product._version.__version__"}

[project.scripts]
myproduct = "my_product.cli:main"

[project.entry-points."qwenpaw.extension_manifests"]
my_product = "my_product:manifest.yaml"

[project.entry-points."qwenpaw.extensions"]
my_product = "my_product.extension:extension"

[tool.setuptools.package-data]
my_product = [
  "manifest.yaml",
  "console/dist/**",
]
```

## 已移除或不再由 SDK 提供的能力

以下能力当前不属于 Extension SDK 扩展面。如果业务需要，应在业务项目外层自行封装，或后续重新评估是否作为通用能力引入。

| 能力 | 当前状态 |
| --- | --- |
| 日志配置能力 | 已移除。使用 QwenPaw 原生日志行为。 |
| 插件策略能力 | 已移除。SDK 只保留 `plugins_dir` 产品路径常量，不提供插件增删改策略。 |
| CLI 命令增删改能力 | 已移除。业务可以通过自己的 console script 封装入口，但 SDK 不再注册/删除/改写 Click 命令。 |
| Skill CLI 名称替换 | 已移除。SDK 不再替换 skills 命令名或 skill 服务入口。 |
| FastAPI 通用路由扩展能力 | 已移除。`BuiltinChannelSpec.route_hook` 只服务于内置 channel 自身挂载，不是通用路由扩展 API。 |
| LLM Provider 增删改能力 | 已移除。SDK 只保留 `local_provider_dir` 产品路径常量。 |
| Control command 扩展能力 | 已移除。 |
| 环境变量前缀替换能力 | 已移除。QwenPaw 原有环境变量名仍保持原生行为。 |
| 品牌化文案 / click.echo 全量替换 | 已移除。SDK 不再扫描替换所有 QwenPaw 文案。 |
| restore lock / restore artifact 文件名品牌化 | 已移除。保留 QwenPaw 原生 restore 文件命名。 |
