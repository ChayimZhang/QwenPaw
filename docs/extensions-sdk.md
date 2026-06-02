# QwenPaw Extension SDK 使用指南

本文面向希望在不深度定制 QwenPaw 源码的前提下做业务扩展的团队。当前 Extension SDK 已收缩为轻量扩展入口，只保留对 QwenPaw 原源码侵入较小、业务仍需要的能力：

- 功能开关：禁用内置 QA agent、内置 channel 加载、custom channel 加载，或禁用指定 channel。
- channel 扩展：注册或替换内置 channel，增加 custom channel 搜索目录。
- AgentRunner hook：托管 `query_handler`，或观察 QwenPaw 原生最终 query stream 阶段。
- 扩展加载：通过 manifest、Python API、entry point、装饰器、声明式对象加载扩展。

以下能力已从 SDK 中移除：产品配置、console 静态资源替换、日志配置、插件策略、CLI 命令扩展、FastAPI 路由扩展、LLM Provider 扩展、skill 服务扩展、Control command 扩展、环境变量前缀替换。

## 架构设计

Extension SDK 以 `ExtensionRegistry` 作为统一注册中心。业务可以通过 manifest、Python API、声明式对象或装饰器把扩展注册到 registry；QwenPaw 原生代码只在少量入口读取 registry。

```text
业务项目
  ├─ manifest.yaml / pyproject.toml entry point
  └─ extension.py / decorators / ExtensionSpec
        │
        ▼
qwenpaw.extensions.ExtensionRegistry
  ├─ features: FeaturePolicy
  ├─ channels: ChannelExtensionRegistry
  └─ runner: RunnerExtensionRegistry
        │
        ▼
QwenPaw 原生入口
  ├─ channel registry 读取内置 channel 与 custom channel source
  ├─ migration 读取 builtin_qa_agent 功能开关
  └─ AgentRunner.query_handler 读取托管 hook 与 stream lifecycle hooks
```

## 功能清单

| 能力 | 用途 | 主要模块 / 类 | 支持方式 |
| --- | --- | --- | --- |
| 功能开关 | 禁用 SDK 支持的通用功能，或禁用指定 channel | `specs.py` / `FeaturePolicy` | manifest、API、声明式、装饰器、Builder |
| 内置 channel 注册 | 注册新的内置 channel，或替换已有内置 channel | `specs.py` / `BuiltinChannelSpec`、`channels.py` | API、声明式、装饰器 |
| custom channel source | 增加业务 custom channel 搜索目录 | `adapters.py`、`channels.py` | API、装饰器 |
| query handler 托管 | 业务完全接管一次 `AgentRunner.query_handler` 的输出逻辑 | `runner.py` / `RunnerQueryContext` | API、声明式、装饰器 |
| query stream lifecycle hooks | 观察 QwenPaw 原生最终流式输出，适合统计、埋点、审计 | `runner.py` / `RunnerQueryContext` | API、声明式、装饰器 |
| manifest 加载 | 从包内资源、项目目录或环境变量加载静态 feature 配置 | `loader.py`、`config.py` | entry point、自动发现、显式 API |

## 加载方式

### 方式一：包内 manifest entry point（推荐）

适合把稳定的功能开关放在业务 wheel 中。manifest 应作为包内资源打包，避免安装后多个项目都使用根目录同名文件造成冲突。

```toml
[project.entry-points."qwenpaw.extension_manifests"]
my_product = "my_product:manifest.yaml"
```

`my_product = "my_product:manifest.yaml"` 表示从 Python 包 `my_product` 内读取 `manifest.yaml`。

### 方式二：Python extension entry point（推荐用于动态扩展）

适合注册 channel、runner hooks，或执行需要 Python 代码表达的配置。

```toml
[project.entry-points."qwenpaw.extensions"]
my_product = "my_product.extension:extension"
```

`qwenpaw.extensions` entry point 可以指向以下对象：

| 对象类型 | 说明 |
| --- | --- |
| `ExtensionDecorator` | `qwenpaw_extension("name")` 创建的装饰器对象，加载时自动调用。 |
| `Callable[[ExtensionRegistry], object]` | 注册函数。可直接修改传入 registry，返回 `None`。 |
| `ExtensionSpec` | 声明式扩展对象。 |
| `Iterable[ExtensionSpec]` | 多个声明式扩展对象。 |

### 方式三：自动发现 manifest

`load_extensions()` 默认会从当前目录和启动脚本路径向上查找以下文件：

| 文件名 |
| --- |
| `manifest.yaml` |
| `manifest.yml` |
| `extension.yaml` |
| `extension.yml` |
| `qwenpaw-extension.yaml` |
| `qwenpaw-extension.yml` |

只有 YAML 根节点包含 `features` 时才会被识别为 Extension manifest。仅包含 `product` 的 manifest 不再会被 SDK 自动发现。

### 方式四：环境变量指定 manifest

| 环境变量 | 说明 |
| --- | --- |
| `QWENPAW_EXTENSION_CONFIG` | 指向一个 extension manifest 文件。 |
| `COPAW_EXTENSION_CONFIG` | 兼容入口，指向一个 extension manifest 文件。 |

当前 SDK 不支持业务自定义环境变量前缀替换，因此不会自动识别业务前缀的 `*_EXTENSION_CONFIG`。

### 加载顺序

`load_extensions()` 默认加载顺序：

1. `qwenpaw.extension_manifests` entry points。
2. 环境变量或自动发现得到的 manifest。
3. `qwenpaw.extensions` Python entry points。

manifest 可以和 Python API 一起使用。推荐把静态 feature 开关放在 manifest，把 channel、runner hook 等动态内容放在 Python extension 中。

## manifest.yaml

manifest 当前只支持 `features` 根节点。

```yaml
features:
  disabled_features:
    - "builtin_qa_agent"
  disabled_channels:
    - "discord"
```

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

`disabled_channels` 只影响 channel key。`BuiltinChannelSpec(required=True)` 的内置 channel 不会被 `builtin_channels` 或 `disabled_channels` 禁用。

## Python API

### ExtensionAdapters

`ExtensionAdapters` 是业务最常用的命令式入口，可通过 `registry.adapters` 或装饰器 `context.adapters` 获取。

| 方法 | 作用 | 示例 |
| --- | --- | --- |
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

装饰器适合把业务扩展拆成多个函数，代码可读性更强，也便于测试。`extension` 对象本身可以作为 `qwenpaw.extensions` entry point 暴露。

```python
from qwenpaw.extensions import (
    BuiltinChannelSpec,
    FeaturePolicy,
    qwenpaw_extension,
)

extension = qwenpaw_extension("my_product")


@extension.features
def features():
    return FeaturePolicy(
        disabled_features={"builtin_qa_agent"},
        disabled_channels={"discord"},
    )


@extension.configure
def configure(context):
    context.adapters.builtin_channel(
        BuiltinChannelSpec(
            key="workchat",
            factory=WorkChatChannel,
            default_enabled=True,
        )
    )
    context.adapters.custom_channel_source("channels")
```

`qwenpaw_extension(name)` 返回 `ExtensionDecorator`，支持的方法：

| 方法 | 用途 | 函数签名 |
| --- | --- | --- |
| `@extension.features` | 注册功能开关 | `() -> FeaturePolicy` 或 `(context) -> FeaturePolicy` |
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

### 声明式 ExtensionSpec

声明式对象适合把配置作为数据集中维护。

```python
from qwenpaw.extensions import BuiltinChannelSpec, ExtensionSpec, FeaturePolicy

extension = ExtensionSpec(
    name="my_product",
    features=FeaturePolicy(disabled_features={"builtin_qa_agent"}),
    builtin_channels=(
        BuiltinChannelSpec(key="workchat", factory=WorkChatChannel),
    ),
)
```

`ExtensionSpec` 字段：

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `name` | `str` | 必填 | extension 标识。 |
| `features` | `FeaturePolicy` | `FeaturePolicy()` | 功能和 channel 禁用策略。 |
| `runner_patch` | `RunnerPatch` | `RunnerPatch()` | runner hooks 声明式注册。 |
| `builtin_channels` | `tuple[BuiltinChannelSpec, ...]` | `()` | 要注册的内置 channel。 |

### Builder 用法

Builder 适合极简命令式配置。

```python
from qwenpaw.extensions import ExtensionRegistry

registry = ExtensionRegistry()
registry.extension("my_product") \
    .disable_features("builtin_qa_agent") \
    .disable_channels("discord")
```

当前 Builder 支持：

| 方法 | 说明 |
| --- | --- |
| `disable_features(*names)` | 禁用一个或多个 feature。 |
| `disable_channels(*keys)` | 禁用一个或多个 channel。 |

## Channel 扩展

### BuiltinChannelSpec 字段

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `key` | `str` | 必填 | channel key，不能为空。 |
| `factory` | `Callable[..., Any]` | 必填 | channel 类或工厂函数。 |
| `config_model` | `type[Any] \| None` | `None` | channel 配置模型；没有独立配置类时可以不填。 |
| `required` | `bool` | `False` | 是否为不可被 feature policy 禁用的必需 channel。 |
| `default_enabled` | `bool` | `False` | 是否默认启用。 |
| `route_hook` | `Callable[..., Any] \| None` | `None` | 可选路由挂载钩子。 |
| `display_name` | `str \| None` | `None` | 展示名称。 |
| `metadata` | `dict[str, Any]` | `{}` | 业务自定义元数据。 |

### 注册新内置 channel

```python
from qwenpaw.extensions import BuiltinChannelSpec, qwenpaw_extension

extension = qwenpaw_extension("my_product")


@extension.configure
def configure(context):
    context.adapters.builtin_channel(
        BuiltinChannelSpec(
            key="workchat",
            factory=WorkChatChannel,
            config_model=WorkChatConfig,
            default_enabled=True,
        )
    )
```

只有 channel class、没有 channel config 类时，也可以注册：

```python
context.adapters.builtin_channel(
    BuiltinChannelSpec(key="workchat", factory=WorkChatChannel)
)
```

### 替换已有内置 channel

```python
context.adapters.replace_builtin_channel(
    BuiltinChannelSpec(key="discord", factory=MyDiscordChannel)
)
```

### 增加 custom channel source

```python
context.adapters.custom_channel_source("my_product/channels")
```

如果 `custom_channels` feature 被禁用，custom channel source 不会被加载。

## AgentRunner Hooks

### query handler 托管 hook

`query_handler_hook` 用于让业务完全托管 `AgentRunner.query_handler` 的输出逻辑。hook 会收到 `RunnerQueryContext`，可以读取原始 request、runner、agent 等上下文。如果 hook 返回一个 async iterable，QwenPaw 会直接使用它作为 `query_handler` 的结果。

```python
@extension.query_handler_hook
def handle_query(context):
    request = context.request
    agent = context.agent

    async def stream():
        async for msg, last in my_business_query(agent, request):
            yield msg, last

    return stream()
```

当业务完全托管后，QwenPaw 原生 query stream lifecycle hooks 不会再观察这段业务流；业务应在自己的托管逻辑中自行统计或埋点。

### query stream lifecycle hooks

这组 hook 只观察 QwenPaw 原生 query handler 中最终执行 `run_mission_phase` / `_stream_printing_messages_interruptible` 的流式输出阶段。它不会观察前面准备阶段的 yield。

典型迁移前代码：

```python
async with track_query_stats(xxx) as tracker:
    async for msg, last in _stream_printing_messages_interruptible(
        agents=[agent],
        coroutine_task=agent(msgs),
    ):
        tracker.observe_message(msg, last)
        yield msg, last
```

迁移为 SDK hook：

```python
@extension.before_query_stream_hook
async def before_stream(context):
    tracker = track_query_stats(context.request)
    context.state["tracker_cm"] = tracker
    context.state["tracker"] = await tracker.__aenter__()


@extension.query_stream_message_hook
async def observe_message(context, msg, last):
    context.state["tracker"].observe_message(msg, last)


@extension.after_query_stream_hook
async def after_stream(context, error):
    tracker_cm = context.state.pop("tracker_cm", None)
    if tracker_cm is not None:
        await tracker_cm.__aexit__(
            type(error) if error else None,
            error,
            error.__traceback__ if error else None,
        )
```

`RunnerQueryContext` 常用字段：

| 字段 | 说明 |
| --- | --- |
| `request` | `AgentRunner.query_handler` 入参 request。 |
| `runner` | 当前 AgentRunner / runner 对象。 |
| `agent` | 当前执行 query 的 agent。 |
| `state` | 业务 hook 共享状态字典，适合在 before/message/after 之间传递 tracker。 |
| `metadata` | SDK 注入的额外上下文。 |

## 完整 Demo 示例

`manifest.yaml`：

```yaml
features:
  disabled_features:
    - builtin_qa_agent
  disabled_channels:
    - discord
```

`pyproject.toml`：

```toml
[project.entry-points."qwenpaw.extension_manifests"]
my_product = "my_product:manifest.yaml"

[project.entry-points."qwenpaw.extensions"]
my_product = "my_product.extension:extension"
```

`my_product/extension.py`：

```python
from qwenpaw.extensions import BuiltinChannelSpec, qwenpaw_extension

extension = qwenpaw_extension("my_product")


@extension.configure
def configure(context):
    context.adapters.builtin_channel(
        BuiltinChannelSpec(
            key="workchat",
            factory=WorkChatChannel,
            default_enabled=True,
        )
    )
    context.adapters.custom_channel_source("my_product/channels")


@extension.before_query_stream_hook
async def before_stream(context):
    tracker_cm = track_query_stats(context.request)
    context.state["tracker_cm"] = tracker_cm
    context.state["tracker"] = await tracker_cm.__aenter__()


@extension.query_stream_message_hook
async def observe_message(context, msg, last):
    context.state["tracker"].observe_message(msg, last)


@extension.after_query_stream_hook
async def after_stream(context, error):
    tracker_cm = context.state.pop("tracker_cm", None)
    if tracker_cm is not None:
        await tracker_cm.__aexit__(
            type(error) if error else None,
            error,
            error.__traceback__ if error else None,
        )
```

这个示例把静态 feature 开关放在 manifest 中，把 channel 注册和 query stream 观察放在 Python extension 中。两者会共同生效。
