# QwenPaw Extension SDK 使用指南

本文档描述当前精简后的 Extension SDK。SDK 只保留业务确实需要的低侵入扩展面，已移除日志配置、插件策略、CLI 命令扩展、FastAPI 路由扩展、LLM Provider 扩展、Skill 服务入口、Control command 扩展、环境变量前缀替换。

## 一、架构设计

Extension SDK 以 `ExtensionRegistry` 为核心保存运行时扩展状态：

```text
业务项目
  manifest.yaml / extension.py
        |
        v
qwenpaw.extensions.loader.load_extensions()
        |
        v
ExtensionRegistry
  product      -> 产品名、CLI 名、用户目录、前端资源、Agent prompt 文件
  features     -> 功能禁用、channel 禁用
  channels     -> 内置 channel 注册、替换、custom channel source
  runner       -> AgentRunner query handler 托管和 query stream hooks
```

QwenPaw 原生代码只在少量稳定入口读取 registry：

| 入口 | 作用 |
| --- | --- |
| `qwenpaw.constant` | 读取产品名、模块名、目录配置 |
| CLI 根命令 | 读取产品名、CLI 名、版本、skill CLI alias |
| channel registry | 读取内置 channel 和 custom channel source |
| AgentRunner | 执行 query handler 托管与 query stream hooks |
| console static | 读取 `ProductSpec.console_static_dir` |

## 二、功能清单

| 功能 | 做什么 | 模块 / 类 | 使用方式 |
| --- | --- | --- | --- |
| 产品配置 | 定制产品名、模块名、CLI 名、版本、用户目录、前端目录、Agent prompt 文件 | `specs.py` / `ProductSpec` | manifest、API、声明式、装饰器 |
| 功能开关 | 禁用通用功能、禁用 channel | `specs.py` / `FeaturePolicy` | manifest、API、声明式、装饰器 |
| 内置 channel | 注册、替换、禁用产品内置 channel | `channels.py` / `BuiltinChannelSpec` | API、声明式、装饰器 |
| custom channel source | 增加 custom channel 搜索目录 | `channels.py` / `ExtensionAdapters.custom_channel_source` | API、装饰器 |
| AgentRunner query handler 托管 | 业务完全接管 `AgentRunner.query_handler` | `runner.py` / `RunnerQueryContext` | API、声明式、装饰器 |
| AgentRunner query stream hooks | 观察 QwenPaw 原生最终流式输出 | `runner.py` / `RunnerQueryContext` | API、声明式、装饰器 |
| 前端静态资源替换 | 指定业务 console 静态资源目录 | `app.py` / `resolve_console_static_dir` | manifest、API、声明式 |
| 品牌化文案 | 替换常见 QwenPaw 产品名、模块名、用户目录文案 | `branding.py` | 自动、API |

## 三、manifest.yaml

推荐业务项目通过包内 manifest 提供静态配置。

`pyproject.toml`：

```toml
[project.entry-points."qwenpaw.extension_manifests"]
my_product = "my_product:manifest.yaml"

[project.entry-points."qwenpaw.extensions"]
my_product = "my_product.extension:extension"
```

`manifest.yaml`：

```yaml
product:
  name: MyProduct
  version: 2.0.0
  module_alias: my_product
  cli_name: myproduct
  skill_cli_name: myproduct-skills
  working_dir: ~/.myproduct
  secret_dir: ~/.myproduct.secret
  console_static_dir: ./console
  agent_prompt_files:
    - MY_PRODUCT.md
    - AGENTS.md

features:
  disabled_features:
    - builtin_qa_agent
  disabled_channels:
    - discord
```

manifest 使用增量覆盖语义：后加载的 manifest 只更新显式声明字段，不会清空已经加载的其他字段。相对路径相对于 manifest 文件所在目录解析。

### product 字段

| YAML 字段 | `ProductSpec` 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | `product_name` | string | `QwenPaw` | 产品显示名 |
| `version` | `product_version` | string 或 null | `None` | 产品版本 |
| `module_alias` | `module_alias` | string | `qwenpaw` | 模块别名，用于部分文案和内部文件名 |
| `cli_name` | `cli_name` | string | `qwenpaw` | CLI 根命令名 |
| `skill_cli_name` | `skill_cli_name` | string 或 null | `None` | skills 命令别名 |
| `working_dir` | `working_dir` | path | `~/.qwenpaw` | 用户工作目录 |
| `secret_dir` | `secret_dir` | path | `~/.qwenpaw.secret` | secret 目录 |
| `backup_dir` | `backup_dir` | path 或 null | `<working_dir>/backups` | 备份目录 |
| `plugins_dir` | `plugins_dir` | path 或 null | `<working_dir>/plugins` | 原生插件目录 |
| `custom_channels_dir` | `custom_channels_dir` | path 或 null | `<working_dir>/custom_channels` | custom channel 目录 |
| `media_dir` | `media_dir` | path 或 null | `<working_dir>/media` | 媒体目录 |
| `local_provider_dir` | `local_provider_dir` | path 或 null | `<working_dir>/local_models` | 本地模型目录 |
| `console_static_dir` | `console_static_dir` | path 或 null | `None` | 业务前端静态资源目录 |
| `agent_prompt_files` | `agent_prompt_files` | string list | `["AGENTS.md", "SOUL.md", "PROFILE.md"]` | Agent 人设文件列表 |

### features 字段

| YAML 字段 | `FeaturePolicy` 字段 | 类型 | 说明 |
| --- | --- | --- | --- |
| `disabled_features` | `disabled_features` | string list | 禁用通用功能，例如 `builtin_qa_agent`、`plugins`、`builtin_channels`、`custom_channels` |
| `disabled_channels` | `disabled_channels` | string list | 禁用指定 channel |

## 四、Python API

### 产品配置

实现方式一：manifest（推荐）

适合产品名、目录、前端目录等静态配置。

实现方式二：增量 API（适合动态版本号）

```python
from my_product.__version__ import __version__

def extension(registry):
    registry.adapters.product_version(__version__)
    registry.adapters.product(module_alias="my_product")
```

实现方式三：装饰器

```python
from qwenpaw.extensions import ProductSpec, qwenpaw_extension

extension = qwenpaw_extension("my_product")

@extension.product
def product():
    return ProductSpec(
        product_name="MyProduct",
        cli_name="myproduct",
        working_dir="~/.myproduct",
    )
```

### 功能开关

```python
from qwenpaw.extensions import FeaturePolicy, qwenpaw_extension

extension = qwenpaw_extension("my_product")

@extension.features
def features():
    return FeaturePolicy(
        disabled_features={"builtin_qa_agent"},
        disabled_channels={"discord"},
    )
```

也可以使用 adapter：

```python
def extension(registry):
    registry.adapters.disable_feature("builtin_qa_agent")
    registry.adapters.disable_channel("discord")
```

### 内置 channel

```python
from qwenpaw.extensions import BuiltinChannelSpec, qwenpaw_extension
from my_product.channels.workchat import WorkChatChannel, WorkChatConfig

extension = qwenpaw_extension("my_product")

@extension.configure
def configure(context):
    context.adapters.builtin_channel(
        BuiltinChannelSpec(
            key="workchat",
            factory=WorkChatChannel,
            config_model=WorkChatConfig,
            default_enabled=True,
            display_name="Work Chat",
        )
    )
    context.adapters.custom_channel_source("~/.myproduct/custom_channels")
```

### AgentRunner query handler 托管

该 hook 在 QwenPaw 原生 `AgentRunner.query_handler` 之前执行。第一个返回非 `None` 的 hook 会完全接管本次 query。

```python
from qwenpaw.extensions import RunnerQueryContext, qwenpaw_extension

extension = qwenpaw_extension("my_product")

@extension.query_handler_hook
async def handle_query(context: RunnerQueryContext):
    if getattr(context.request, "channel", "") != "my_channel":
        return None

    async def stream():
        yield "business message", False
        yield "done", True

    return stream()
```

返回值可以是 `None`、async iterable、sync iterable，或单个 `(msg, last)` tuple。业务完全托管后，query stream hooks 不会自动观察业务输出，业务需要自行统计。

### AgentRunner query stream hooks

这组三段式 hook 只观察 QwenPaw 原生最终流式输出：`run_mission_phase1`、`run_mission_phase2`、`_stream_printing_messages_interruptible`。

```python
from qwenpaw.extensions import RunnerQueryContext, qwenpaw_extension

extension = qwenpaw_extension("my_product")

@extension.before_query_stream_hook
async def before_stream(context: RunnerQueryContext):
    context.state["tracker"] = await start_query_stats(
        request=context.request,
        agent=context.agent,
        workspace=context.workspace,
    )

@extension.query_stream_message_hook
async def on_stream_message(context: RunnerQueryContext, msg, last):
    await context.state["tracker"].observe_message(msg, last)

@extension.after_query_stream_hook
async def after_stream(context: RunnerQueryContext, error):
    await context.state["tracker"].finish(error=error)
```

`RunnerQueryContext` 字段：

| 字段 | 说明 |
| --- | --- |
| `request` | `query_handler` 的 request 入参 |
| `runner` | 当前 `AgentRunner` |
| `agent` | 当前 query 内创建的 `QwenPawAgent` |
| `workspace` | 当前 workspace |
| `msgs` | 原始消息 |
| `kwargs` | 原始 kwargs 的只读映射 |
| `state` | 同一次 query stream hooks 共享的 dict |

`after_query_stream_hook(context, error)` 中 `error=None` 表示正常结束。

## 五、完整 Demo

目录结构：

```text
my_product/
  pyproject.toml
  src/my_product/
    __init__.py
    __version__.py
    manifest.yaml
    extension.py
    channels/workchat.py
    console/index.html
```

`src/my_product/__version__.py`：

```python
__version__ = "2.0.0"
```

`src/my_product/manifest.yaml`：

```yaml
product:
  name: MyProduct
  module_alias: my_product
  cli_name: myproduct
  skill_cli_name: myproduct-skills
  working_dir: ~/.myproduct
  secret_dir: ~/.myproduct.secret
  console_static_dir: ./console

features:
  disabled_features:
    - builtin_qa_agent
  disabled_channels:
    - discord
```

`src/my_product/extension.py`：

```python
from qwenpaw.extensions import BuiltinChannelSpec, qwenpaw_extension
from my_product.__version__ import __version__
from my_product.channels.workchat import WorkChatChannel, WorkChatConfig

extension = qwenpaw_extension("my_product")

@extension.configure
def configure(context):
    api = context.adapters
    api.product_version(__version__)
    api.builtin_channel(
        BuiltinChannelSpec(
            key="workchat",
            factory=WorkChatChannel,
            config_model=WorkChatConfig,
            default_enabled=True,
        )
    )

@extension.before_query_stream_hook
async def before_stream(context):
    context.state["tracker"] = await start_query_stats(request=context.request)

@extension.query_stream_message_hook
async def on_stream_message(context, msg, last):
    await context.state["tracker"].observe_message(msg, last)

@extension.after_query_stream_hook
async def after_stream(context, error):
    await context.state["tracker"].finish(error=error)
```

`pyproject.toml`：

```toml
[project.scripts]
myproduct = "my_product.cli:main"

[project.entry-points."qwenpaw.extension_manifests"]
my_product = "my_product:manifest.yaml"

[project.entry-points."qwenpaw.extensions"]
my_product = "my_product.extension:extension"
```

## 六、已移除能力

以下能力不再由 Extension SDK 提供：

| 已移除能力 | 替代建议 |
| --- | --- |
| 日志配置 | 使用 QwenPaw 原生日志行为或业务进程外日志采集 |
| 插件策略 | 使用 QwenPaw 原生插件目录和插件机制 |
| CLI 命令增删改 | 业务项目提供自己的 entry point 脚本 |
| FastAPI 路由扩展 | 业务通过独立服务或完全托管入口实现 |
| LLM Provider 增删改 | 使用 QwenPaw 原生 provider 配置能力 |
| Skill 服务入口 | 业务不要通过 Extension SDK 直接访问内部 service |
| Control command | 使用 QwenPaw 原生控制命令机制 |
| 环境变量前缀替换 | 固定使用 `QWENPAW_*`，保留 `COPAW_*` 作为 legacy fallback |
