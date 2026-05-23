# QwenPaw Extension SDK 使用指南

Extension SDK 用来把 QwenPaw 当成 Python 依赖库使用，同时把产品名、目录、环境变量、CLI、FastAPI、channel、provider、插件、功能开关、前端静态资源等通用扩展点开放给业务产品。业务团队应优先通过独立 Python 包、包内 manifest、装饰器或声明式 spec 接入，而不是修改 QwenPaw 源码。

本文中的 `MyProduct`、`MYPRODUCT`、`myproduct` 都是占位示例。SDK 不硬编码任何业务关键字，真实产品名、环境变量前缀、目录、命令名都应由业务扩展包或 manifest 提供。

## 一、架构设计

Extension SDK 的核心设计是“统一注册中心 + 多种接入方式 + QwenPaw 运行时消费注册结果”。

```text
业务产品包
  pyproject.toml
    qwenpaw.extension_manifests -> 包内 manifest YAML
    qwenpaw.extensions          -> Python 扩展入口，可选
  manifest.yaml                 -> 产品、日志、功能、插件等声明式配置
  extension.py                  -> decorator / fluent / ExtensionSpec，可选
  console/                      -> 可替换前端静态资源，可选

QwenPaw Extension SDK
  loader.py       -> load_extensions，发现并加载 manifest 和 Python entry point
  config.py       -> 解析 manifest，写入 ExtensionRegistry
  registry.py     -> ExtensionRegistry，统一保存所有扩展状态
  specs.py        -> ProductSpec、LoggingSpec、FeaturePolicy、ExtensionSpec 等声明式模型
  adapters.py     -> ExtensionAdapters，给业务和插件使用的统一 API
  decorators.py   -> qwenpaw_extension 装饰器入口
  cli.py          -> Click 命令增删改别名
  app.py          -> FastAPI router、生命周期、静态资源目录
  channels.py     -> 内置 channel 和 custom channel source
  providers.py    -> LLM provider 增加、替换、禁用
  features.py     -> 功能开关、插件策略、channel/provider 策略判断
  env.py          -> 环境变量前缀解析
  logging.py      -> 日志配置解析
  branding.py     -> CLI 文案、输出、restore 文件名等产品品牌化

QwenPaw 运行时
  CLI / FastAPI / provider manager / channel registry / plugin loader / constants
  在启动时调用 load_extensions()，再读取 ExtensionRegistry 中的扩展状态
```

### 加载顺序

`load_extensions()` 会按以下顺序加载扩展：

1. 包内资源 manifest entry point：`qwenpaw.extension_manifests`
2. 显式 `config_path`、环境变量 `*_EXTENSION_CONFIG` 或自动发现的 manifest，覆盖包内默认配置
3. Python 扩展 entry point：`qwenpaw.extensions`，用于注册 callable 能力，例如 CLI、FastAPI router、provider、内置 channel

manifest 覆盖优先级为：

```text
显式 config_path
> *_EXTENSION_CONFIG 环境变量
> 自动发现的 manifest
> 包内资源 manifest entry point
```

### 推荐接入方式

多数业务产品推荐组合使用：

1. `qwenpaw.extension_manifests` + 包内 `manifest.yaml`：配置产品名、CLI 名、环境变量、目录、日志、功能开关、插件搜索路径、前端静态目录。
2. `qwenpaw.extensions` + `qwenpaw_extension()`：注册 CLI 命令、FastAPI router、provider、内置 channel、control command、复杂 Python callable。
3. `ExtensionSpec`：需要集中审计、跨产品线复用、或者用单一对象表达扩展时使用。
4. `ExtensionAdapters`：插件内部或普通 Python 扩展内部的统一 API。

## 二、功能总览清单

| 能力 | 用途 | 主要模块 | 主要类/函数 | 支持方式 |
| --- | --- | --- | --- | --- |
| 扩展加载 | 加载 manifest 和 Python entry point | `loader.py`、`config.py` | `load_extensions`、`apply_manifest`、`apply_manifest_resource` | 配置文件、包内资源、自动发现、API |
| 产品品牌与目录 | 定制产品名、版本、模块名、CLI 名、工作目录、密钥目录、前端目录、Agent prompt 文件 | `specs.py`、`registry.py`、`branding.py` | `ProductSpec`、`ExtensionBuilder.product`、`brand_text` | manifest、API、声明式、装饰器 |
| 环境变量前缀 | 让 `MYPRODUCT_*` 优先，回落到 `QWENPAW_*`、`COPAW_*` | `env.py` | `EnvResolver` | manifest、API |
| 日志配置 | 定制 logger namespace、日志文件、格式、级别、handler factory | `specs.py`、`logging.py` | `LoggingSpec`、`resolve_logging_spec`、`resolve_log_level` | manifest、API、声明式 |
| 功能开关 | 禁用 QA agent、插件、内置 channel、自定义 channel、FastAPI extension router | `features.py`、`specs.py` | `FeaturePolicy`、`EXTENSION_FEATURES` | manifest、API、声明式、装饰器 |
| 插件策略 | 禁用插件、允许列表、增加插件搜索路径 | `specs.py`、`features.py`、`adapters.py` | `PluginPolicy`、`iter_plugin_search_paths` | manifest、API、声明式 |
| CLI 命令 | 增加、替换、禁用、增加别名 | `cli.py`、`registry.py`、`adapters.py` | `CliRegistry`、`CliPatch`、`CliCommandPatch` | API、声明式、装饰器 |
| FastAPI 扩展 | 增加 router、startup/shutdown hook、middleware、include router 前后 hook | `app.py`、`registry.py`、`adapters.py` | `AppExtensionRegistry`、`AppPatch`、`RouterSpec` | API、声明式、装饰器 |
| 前端静态资源替换 | 替换 QwenPaw console 静态资源目录 | `app.py`、`specs.py` | `ProductSpec.console_static_dir`、`resolve_console_static_dir` | manifest、API、声明式 |
| 内置 channel | 注册、替换、禁用产品内置 channel | `channels.py`、`specs.py`、`adapters.py` | `BuiltinChannelSpec`、`ChannelExtensionRegistry` | API、声明式、装饰器 |
| custom channel source | 增加文件目录式 custom channel 来源 | `channels.py`、`adapters.py` | `custom_channel_source`、`add_custom_source` | API、装饰器 |
| LLM provider | 增加、替换、禁用 provider | `providers.py`、`specs.py`、`adapters.py` | `ProviderPatch`、`ProviderExtensionRegistry` | API、声明式、装饰器、manifest 禁用 |
| 插件统一入口 | 让插件内部也使用 Extension SDK 能力 | `plugins/api.py`、`adapters.py` | `PluginApi.extensions`、`ExtensionAdapters` | 插件 API |
| Skill 服务入口 | 业务或插件访问 SkillService、SkillPoolService | `adapters.py` | `skill_service`、`skill_pool_service` | API、插件 API |
| Control command | 注册或移除 runner control command | `adapters.py` | `control_command`、`unregister_control_command` | API、装饰器 |
| 品牌化运行时文案 | 自动替换 CLI help、click 输出、安全提示、provider 提示、restore 文件名 | `branding.py`、`cli/main.py`、`init_cmd.py`、`provider_manager.py` | `brand_text`、`brand_click_command`、`restore_artifact_name` | 自动、API |
| 测试隔离 | 在测试中切换 registry，避免污染全局状态 | `registry.py` | `use_extension_registry` | API |

## 三、扩展加载和项目接入

### 实现方式一：包内 manifest entry point（推荐）

适合产品默认配置。manifest 和前端资源作为 Python 包内资源发布，不会安装到环境根目录，也不会和其他包的同名文件冲突。

目录结构：

```text
my_product/
  pyproject.toml
  src/my_product/
    __init__.py
    cli.py
    manifest.yaml
    console/
      index.html
    extension.py
```

`pyproject.toml`：

```toml
[project.scripts]
myproduct = "my_product.cli:main"

[project.entry-points."qwenpaw.extension_manifests"]
my_product = "my_product:manifest.yaml"

[project.entry-points."qwenpaw.extensions"]
my_product = "my_product.extension:extension"

[tool.setuptools.package-data]
my_product = ["manifest.yaml", "console/**"]
```

`src/my_product/cli.py`：

```python
def main() -> None:
    from qwenpaw.extensions import load_extensions

    load_extensions(force=True)

    from qwenpaw.cli.main import cli

    cli()
```

### 实现方式二：显式配置文件（推荐用于部署覆盖）

适合线上环境、私有化部署、灰度环境临时覆盖默认配置。

```python
from qwenpaw.extensions import load_extensions

load_extensions(config_path="/etc/myproduct/qwenpaw-extension.yaml")
```

也可以通过环境变量覆盖：

```powershell
$env:MYPRODUCT_EXTENSION_CONFIG = "D:\config\myproduct-extension.yaml"
myproduct -h
```

如果 `ProductSpec.env_prefixes = ("MYPRODUCT", "QWENPAW", "COPAW")`，查找顺序为：

```text
MYPRODUCT_EXTENSION_CONFIG
QWENPAW_EXTENSION_CONFIG
COPAW_EXTENSION_CONFIG
```

### 实现方式三：自动发现 manifest（适合源码项目或本地调试）

当没有显式 `config_path`，也没有 `*_EXTENSION_CONFIG`，loader 会从当前工作目录和当前可执行文件路径向父目录查找：

```text
manifest.yaml
manifest.yml
extension.yaml
extension.yml
qwenpaw-extension.yaml
qwenpaw-extension.yml
```

自动发现只加载包含 `product`、`logging`、`features`、`plugins` 顶层字段的 YAML，避免误加载普通项目 manifest。

### 实现方式四：Python entry point（适合 callable 扩展）

`qwenpaw.extensions` 用于加载 Python 对象。entry point 可以返回或应用以下对象：

```toml
[project.entry-points."qwenpaw.extensions"]
my_product = "my_product.extension:extension"
```

`extension` 可以是：

1. 普通函数，签名为 `def extension(registry: ExtensionRegistry) -> None`
2. `qwenpaw_extension()` 返回的 decorator 对象
3. `ExtensionSpec`
4. `ExtensionSpec` 列表

## 四、Manifest YAML 字段完整说明

manifest 当前支持四个顶层字段：

```yaml
product: {}
logging: {}
features: {}
plugins: {}
```

相对路径规则：

1. 文件系统 manifest：相对路径按 manifest 文件所在目录解析。
2. 包内资源 manifest：相对路径按包内 manifest 所在目录解析。
3. `~` 开头路径按用户主目录解析。
4. 绝对路径保持不变。

### product 字段

| YAML 字段 | 对应 `ProductSpec` 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | `product_name` | string | `QwenPaw` | 产品展示名，用于 help、提示、日志默认 namespace 等 |
| `version` | `product_version` | string/null | `null` | 产品版本 |
| `module_alias` | `module_alias` | string | `qwenpaw` | 模块别名，用于品牌化文案和 restore 文件名，例如 `.myproduct_restore.lock` |
| `cli_name` | `cli_name` | string | `qwenpaw` | 主 CLI 名，例如 `myproduct` |
| `skill_cli_name` | `skill_cli_name` | string/null | `null` | skills 命令别名，例如 `myproduct-skills` |
| `env_prefixes` | `env_prefixes` | string list | `["QWENPAW", "COPAW"]` | 环境变量前缀，必须是非空大写字符串，越靠前优先级越高 |
| `working_dir` | `working_dir` | path | `~/.qwenpaw` | 工作目录 |
| `secret_dir` | `secret_dir` | path | `~/.qwenpaw.secret` | 密钥目录 |
| `backup_dir` | `backup_dir` | path/null | `<working_dir>/backups` | 备份目录 |
| `plugins_dir` | `plugins_dir` | path/null | `<working_dir>/plugins` | 插件目录 |
| `custom_channels_dir` | `custom_channels_dir` | path/null | `<working_dir>/custom_channels` | custom channel 目录 |
| `media_dir` | `media_dir` | path/null | `<working_dir>/media` | 媒体目录 |
| `local_provider_dir` | `local_provider_dir` | path/null | `<working_dir>/local_models` | 本地模型目录 |
| `console_static_dir` | `console_static_dir` | path/null | `null` | 前端静态资源目录，用于替换内置 console |
| `agent_prompt_files` | `agent_prompt_files` | path list | `["AGENTS.md", "SOUL.md", "PROFILE.md"]` | Agent 人设 prompt 文件读取顺序 |

### logging 字段

| YAML 字段 | 对应 `LoggingSpec` 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `namespace` | `namespace` | string | `qwenpaw` 或产品名小写 | logger namespace |
| `file_path` | `file_path` | path/null | `<working_dir>/<namespace>.log` | 日志文件路径 |
| `format` | `format` | string | `%(asctime)s - %(name)s - %(levelname)s - %(message)s` | Python logging format |
| `level` | `level` | string | `INFO` | handler 日志级别 |

说明：`handler_factory` 是 Python callable，不能通过 YAML 表达，需要用 API、声明式或装饰器配置。

### features 字段

| YAML 字段 | 对应 `FeaturePolicy` 字段 | 类型 | 说明 |
| --- | --- | --- | --- |
| `disabled_features` | `disabled_features` | string list | 禁用 SDK 暴露的通用功能 |
| `disabled_channels` | `disabled_channels` | string list | 禁用指定 channel key |
| `disabled_providers` | `disabled_providers` | string list | 禁用指定 provider id |
| `disabled_plugins` | `disabled_plugins` | string list | 禁用指定 plugin id |
| `allowed_plugins` | `allowed_plugins` | string list | 插件允许列表，非空时只允许列表内插件 |

当前可禁用的通用 feature：

| feature key | 说明 | 影响位置 |
| --- | --- | --- |
| `builtin_qa_agent` | 是否创建内置 QA agent workspace | `features.py`、`app/migration.py` |
| `plugins` | 是否发现和加载插件 | `features.py`、`plugins/loader.py` |
| `builtin_channels` | 是否注册非 required 的内置 channel | `features.py`、`app/channels/registry.py` |
| `custom_channels` | 是否加载目录式 custom channel | `features.py`、`app/channels/registry.py` |
| `fastapi_extension_routers` | 是否 include extension router | `features.py`、`app.py` |

### plugins 字段

| YAML 字段 | 对应 `PluginPolicy` 字段 | 类型 | 说明 |
| --- | --- | --- | --- |
| `disabled_plugins` | `disabled_plugins` | string list | 禁用插件 |
| `allowed_plugins` | `allowed_plugins` | string list | 允许列表 |
| `extra_search_paths` | `extra_search_paths` | path list | 额外插件搜索目录 |

### 完整 manifest 示例

```yaml
product:
  name: MyProduct
  version: 2.0.0
  module_alias: myproduct
  cli_name: myproduct
  skill_cli_name: myproduct-skills
  env_prefixes:
    - MYPRODUCT
    - QWENPAW
    - COPAW
  working_dir: ~/.myproduct
  secret_dir: ~/.myproduct.secret
  backup_dir: ~/.myproduct/backups
  plugins_dir: ~/.myproduct/plugins
  custom_channels_dir: ~/.myproduct/custom_channels
  media_dir: ~/.myproduct/media
  local_provider_dir: ~/.myproduct/local_models
  console_static_dir: ./console
  agent_prompt_files:
    - MY_PRODUCT.md
    - AGENTS.md
    - SOUL.md
    - PROFILE.md

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
    - my-product-plugin

plugins:
  extra_search_paths:
    - ~/.myproduct/plugins
```

## 五、产品品牌、目录和 Agent 人设

### 实现方式一：manifest（推荐）

适合产品名、CLI 名、环境变量、目录等稳定配置。

```yaml
product:
  name: MyProduct
  version: 2.0.0
  module_alias: myproduct
  cli_name: myproduct
  skill_cli_name: myproduct-skills
  env_prefixes: [MYPRODUCT, QWENPAW, COPAW]
  working_dir: ~/.myproduct
  secret_dir: ~/.myproduct.secret
  console_static_dir: ./console
  agent_prompt_files:
    - MY_PRODUCT.md
    - AGENTS.md
    - SOUL.md
    - PROFILE.md
```

### 实现方式二：Fluent Builder（简单 Python 配置）

适合只改少量产品字段。

```python
def extension(registry):
    (
        registry.extension("my_product")
        .product(name="MyProduct", version="2.0.0", cli_name="myproduct")
        .env_prefix("MYPRODUCT")
        .working_dir("~/.myproduct")
        .secret_dir("~/.myproduct.secret")
        .console_static_dir("/opt/myproduct/console")
        .skill_cli_name("myproduct-skills")
    )
```

### 实现方式三：装饰器（灵活、可读性强，方便拆分函数）

```python
from qwenpaw.extensions import ProductSpec, qwenpaw_extension

extension = qwenpaw_extension("my_product")

@extension.product
def product() -> ProductSpec:
    return ProductSpec(
        product_name="MyProduct",
        product_version="2.0.0",
        module_alias="myproduct",
        cli_name="myproduct",
        skill_cli_name="myproduct-skills",
        env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"),
        working_dir="~/.myproduct",
        secret_dir="~/.myproduct.secret",
        console_static_dir="/opt/myproduct/console",
        agent_prompt_files=("MY_PRODUCT.md", "AGENTS.md", "SOUL.md", "PROFILE.md"),
    )
```

### 实现方式四：声明式 `ExtensionSpec`（集中审计、适合复用）

```python
from qwenpaw.extensions import ExtensionSpec, ProductSpec

extension = ExtensionSpec(
    name="my_product",
    product=ProductSpec(
        product_name="MyProduct",
        module_alias="myproduct",
        cli_name="myproduct",
        env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"),
        working_dir="~/.myproduct",
        secret_dir="~/.myproduct.secret",
    ),
)
```

### `ProductSpec` 字段完整说明

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `product_name` | `str` | `QwenPaw` | 产品展示名 |
| `module_alias` | `str` | `qwenpaw` | 模块别名和 restore 文件名前缀 |
| `cli_name` | `str` | `qwenpaw` | 主 CLI 名 |
| `env_prefixes` | `tuple[str, ...]` | `("QWENPAW", "COPAW")` | 环境变量前缀，前者优先 |
| `working_dir` | `str | Path` | `~/.qwenpaw` | 工作目录 |
| `secret_dir` | `str | Path` | `~/.qwenpaw.secret` | 密钥目录 |
| `product_version` | `str | None` | `None` | 产品版本 |
| `skill_cli_name` | `str | None` | `None` | skills CLI 别名 |
| `backup_dir` | `str | Path | None` | `<working_dir>/backups` | 备份目录 |
| `plugins_dir` | `str | Path | None` | `<working_dir>/plugins` | 插件目录 |
| `custom_channels_dir` | `str | Path | None` | `<working_dir>/custom_channels` | custom channel 目录 |
| `media_dir` | `str | Path | None` | `<working_dir>/media` | 媒体目录 |
| `local_provider_dir` | `str | Path | None` | `<working_dir>/local_models` | 本地 provider 模型目录 |
| `console_static_dir` | `str | Path | None` | `None` | 前端静态资源目录 |
| `agent_prompt_files` | `tuple[str | Path, ...]` | `("AGENTS.md", "SOUL.md", "PROFILE.md")` | Agent 人设 prompt 文件 |

## 六、环境变量前缀

环境变量统一由 `EnvResolver` 处理。假设：

```python
ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
```

读取 `WORKING_DIR` 时会按顺序查找：

```text
MYPRODUCT_WORKING_DIR
QWENPAW_WORKING_DIR
COPAW_WORKING_DIR
```

### API 用法

```python
from qwenpaw.extensions import EnvResolver, get_extension_registry

resolver = EnvResolver(get_extension_registry().product)

working_dir = resolver.get("WORKING_DIR")
debug = resolver.get_bool("DEBUG", default=False)
port = resolver.get_int("PORT", default=8000)
temperature = resolver.get_float("TEMPERATURE", default=0.7)
canonical_name = resolver.key("WORKING_DIR")  # MYPRODUCT_WORKING_DIR
all_names = resolver.names("WORKING_DIR")
```

## 七、日志配置

### 实现方式一：manifest（推荐）

```yaml
logging:
  namespace: myproduct
  file_path: ~/.myproduct/logs/runtime.log
  format: "%(asctime)s %(levelname)s [%(name)s] %(message)s"
  level: INFO
```

### 实现方式二：API 或声明式（需要 handler_factory 时使用）

```python
from qwenpaw.extensions import LoggingSpec

def extension(registry):
    registry.configure_logging(
        LoggingSpec(
            namespace="myproduct",
            file_path="~/.myproduct/logs/runtime.log",
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            level="DEBUG",
        )
    )
```

自定义 handler：

```python
import logging
from qwenpaw.extensions import LoggingSpec

def handler_factory(namespace, file_path, fmt, level):
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt))
    return [handler]

extension = ExtensionSpec(
    name="my_product",
    logging=LoggingSpec(
        namespace="myproduct",
        level="INFO",
        handler_factory=handler_factory,
    ),
)
```

### `LoggingSpec` 字段完整说明

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `namespace` | `str` | `qwenpaw` | logger namespace |
| `file_path` | `str | Path | None` | `None` | 文件日志路径 |
| `format` | `str` | `%(asctime)s - %(name)s - %(levelname)s - %(message)s` | logging format |
| `level` | `str` | `INFO` | handler level |
| `handler_factory` | `Callable | None` | `None` | 自定义 handler 创建函数，只能通过 Python 配置 |

## 八、功能开关和插件策略

### 实现方式一：manifest（推荐）

```yaml
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
    - my-product-plugin

plugins:
  disabled_plugins:
    - old-plugin
  allowed_plugins:
    - my-product-plugin
  extra_search_paths:
    - ~/.myproduct/plugins
```

### 实现方式二：Fluent Builder（简单禁用）

```python
def extension(registry):
    (
        registry.extension("my_product")
        .disable_features("builtin_qa_agent")
        .disable_channels("discord")
        .disable_providers("ollama")
    )
```

### 实现方式三：装饰器（可读性强）

```python
from qwenpaw.extensions import FeaturePolicy, qwenpaw_extension

extension = qwenpaw_extension("my_product")

@extension.features
def features() -> FeaturePolicy:
    return FeaturePolicy(
        disabled_features={"builtin_qa_agent"},
        disabled_channels={"discord"},
        disabled_providers={"ollama"},
        disabled_plugins={"community-demo"},
        allowed_plugins={"my-product-plugin"},
    )
```

### 实现方式四：统一 API（插件或复杂扩展推荐）

```python
def extension(registry):
    api = registry.adapters
    api.disable_feature("builtin_qa_agent")
    api.disable_channel("discord")
    api.disable_provider("ollama")
    api.disable_plugin("community-demo")
    api.allow_plugin("my-product-plugin")
    api.plugin_search_path("~/.myproduct/plugins")
```

### `FeaturePolicy` 字段完整说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `disabled_features` | `Iterable[str] | None` | 禁用通用 feature |
| `disabled_channels` | `Iterable[str] | None` | 禁用 channel key |
| `disabled_providers` | `Iterable[str] | None` | 禁用 provider id |
| `disabled_plugins` | `Iterable[str] | None` | 禁用 plugin id |
| `allowed_plugins` | `Iterable[str] | None` | 插件允许列表，非空时只允许列表内插件 |

### `PluginPolicy` 字段完整说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `disabled_plugins` | `Iterable[str] | None` | 禁用 plugin id |
| `allowed_plugins` | `Iterable[str] | None` | 插件允许列表 |
| `extra_search_paths` | `Iterable[str | Path] | None` | 额外插件搜索路径 |

## 九、CLI 命令扩展

CLI 扩展通过懒加载命令实现，业务只声明模块路径和属性名。属性应是 Click command/group 对象。

### 实现方式一：统一 API（推荐，最直观）

```python
def extension(registry):
    api = registry.adapters
    api.cli_command("diagnose", "my_product.cli.diagnose", "diagnose")
    api.replace_cli_command("doctor", "my_product.cli.doctor", "doctor")
    api.disable_cli_command("update")
    api.cli_alias("models", "model")
```

### 实现方式二：Fluent Builder（适合少量新增命令）

```python
def extension(registry):
    registry.extension("my_product").cli_command(
        "diagnose",
        "my_product.cli.diagnose",
        "diagnose",
    )
```

### 实现方式三：声明式 `CliPatch`（集中声明）

```python
from qwenpaw.extensions import CliCommandPatch, CliPatch, ExtensionSpec

extension = ExtensionSpec(
    name="my_product",
    cli_patch=CliPatch(
        add={
            "diagnose": CliCommandPatch(
                name="diagnose",
                module="my_product.cli.diagnose",
                attribute="diagnose",
            )
        },
        replace={
            "doctor": CliCommandPatch(
                name="doctor",
                module="my_product.cli.doctor",
                attribute="doctor",
            )
        },
        disable=frozenset({"update"}),
        aliases={"models": "model"},
    ),
)
```

### Click 命令示例

```python
import click

@click.command()
def diagnose():
    click.echo("ok")
```

### CLI 相关字段

| 类 | 字段 | 类型 | 说明 |
| --- | --- | --- | --- |
| `CliCommandPatch` | `name` | `str` | 命令名 |
| `CliCommandPatch` | `module` | `str` | Python 模块路径 |
| `CliCommandPatch` | `attribute` | `str` | 模块中的 Click command 属性名 |
| `CliPatch` | `add` | `dict[str, CliCommandPatch]` | 新增命令 |
| `CliPatch` | `replace` | `dict[str, CliCommandPatch]` | 替换已有命令 |
| `CliPatch` | `disable` | `frozenset[str]` | 禁用命令 |
| `CliPatch` | `aliases` | `dict[str, str]` | 别名映射，key 是已有命令，value 是别名 |

## 十、FastAPI 扩展和生命周期

### 实现方式一：统一 API（推荐）

```python
from fastapi import APIRouter, FastAPI

router = APIRouter()

@router.get("/health")
async def health():
    return {"ok": True}

def install_middleware(app: FastAPI) -> None:
    app.state.my_product = True

def on_startup() -> None:
    print("startup")

def extension(registry):
    api = registry.adapters
    api.router(router, prefix="/api/my-product", tags=["my-product"])
    api.middleware_hook(install_middleware)
    api.startup_hook(on_startup)
```

### 实现方式二：声明式 `AppPatch`

```python
from qwenpaw.extensions import AppPatch, ExtensionSpec, RouterSpec

extension = ExtensionSpec(
    name="my_product",
    app_patch=AppPatch(
        routers=(RouterSpec(router, prefix="/api/my-product", tags=["my-product"]),),
        startup_hooks=(on_startup,),
        shutdown_hooks=(on_shutdown,),
        middleware_hooks=(install_middleware,),
        before_include_routers=(before_include,),
        after_include_routers=(after_include,),
    ),
)
```

### FastAPI 字段完整说明

| 类 | 字段 | 类型 | 说明 |
| --- | --- | --- | --- |
| `RouterSpec` | `router` | `Any` | FastAPI `APIRouter` |
| `RouterSpec` | `prefix` | `str` | include router 前缀 |
| `RouterSpec` | `tags` | `list[str] | None` | OpenAPI tags |
| `AppPatch` | `routers` | `tuple[Any, ...]` | router 或 `RouterSpec` 列表 |
| `AppPatch` | `startup_hooks` | `tuple[Callable, ...]` | app startup hook |
| `AppPatch` | `shutdown_hooks` | `tuple[Callable, ...]` | app shutdown hook |
| `AppPatch` | `middleware_hooks` | `tuple[Callable[[FastAPI], Any], ...]` | middleware 安装 hook |
| `AppPatch` | `before_include_routers` | `tuple[Callable[[FastAPI], Any], ...]` | QwenPaw include router 前 hook |
| `AppPatch` | `after_include_routers` | `tuple[Callable[[FastAPI], Any], ...]` | QwenPaw include router 后 hook |

## 十一、前端静态资源替换

前端静态资源由 `ProductSpec.console_static_dir` 控制。QwenPaw 会优先使用扩展提供的目录。

### 实现方式一：包内 manifest（推荐）

```yaml
product:
  console_static_dir: ./console
```

配合：

```toml
[tool.setuptools.package-data]
my_product = ["manifest.yaml", "console/**"]
```

### 实现方式二：API

```python
def extension(registry):
    registry.extension("my_product").console_static_dir("/opt/myproduct/console")
```

### 实现方式三：声明式

```python
from dataclasses import replace
from qwenpaw.extensions import get_extension_registry

registry = get_extension_registry()
registry.configure_product(
    replace(
        registry.product,
        console_static_dir="/opt/myproduct/console",
    )
)
```

如果产品配置全部由同一个 `ProductSpec` 声明，也可以直接写在完整的 `ProductSpec` 中：

```python
from qwenpaw.extensions import ExtensionSpec, ProductSpec

extension = ExtensionSpec(
    name="my_product",
    product=ProductSpec(
        product_name="MyProduct",
        module_alias="myproduct",
        cli_name="myproduct",
        env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"),
        working_dir="~/.myproduct",
        secret_dir="~/.myproduct.secret",
        console_static_dir="/opt/myproduct/console",
    ),
)
```

## 十二、内置 channel 和 custom channel

内置 channel 与 custom channel 是两种不同能力：

1. 内置 channel：产品通过 Python 注册一类 channel，像 QwenPaw 自带 channel 一样参与注册表。
2. custom channel：从目录中发现用户或业务放置的 channel 文件。

### 实现方式一：统一 API 注册内置 channel（推荐）

```python
from qwenpaw.extensions import BuiltinChannelSpec
from my_product.channels.workchat import WorkChatChannel, WorkChatConfig

def extension(registry):
    registry.adapters.builtin_channel(
        BuiltinChannelSpec(
            key="workchat",
            factory=WorkChatChannel,
            config_model=WorkChatConfig,
            required=False,
            default_enabled=True,
            display_name="Work Chat",
            metadata={"owner": "my-product"},
        )
    )
```

### 实现方式二：替换内置 channel

```python
def extension(registry):
    registry.adapters.replace_builtin_channel(
        BuiltinChannelSpec(
            key="discord",
            factory=MyDiscordChannel,
            config_model=MyDiscordConfig,
        )
    )
```

### 实现方式三：声明式

```python
from qwenpaw.extensions import BuiltinChannelSpec, ExtensionSpec

extension = ExtensionSpec(
    name="my_product",
    builtin_channels=(
        BuiltinChannelSpec(
            key="workchat",
            factory=WorkChatChannel,
            config_model=WorkChatConfig,
            default_enabled=True,
        ),
    ),
)
```

### 实现方式四：custom channel source

```python
def extension(registry):
    registry.adapters.custom_channel_source("~/.myproduct/custom_channels")
```

也可通过 manifest 设置默认目录：

```yaml
product:
  custom_channels_dir: ~/.myproduct/custom_channels
```

### `BuiltinChannelSpec` 字段完整说明

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `key` | `str` | 必填 | channel 唯一 key |
| `factory` | `Callable[..., Any]` | 必填 | channel 工厂或 channel 类 |
| `config_model` | `type[Any] | None` | `None` | 配置模型 |
| `required` | `bool` | `False` | 是否无视 `builtin_channels` feature 和禁用策略，始终注册 |
| `default_enabled` | `bool` | `False` | 默认是否启用 |
| `route_hook` | `Callable[..., Any] | None` | `None` | 路由挂载 hook |
| `display_name` | `str | None` | `None` | 展示名 |
| `metadata` | `dict[str, Any]` | `{}` | 扩展元数据 |

## 十三、LLM Provider 扩展

### 实现方式一：统一 API（推荐）

```python
from my_product.llm import MyProductProvider

def extension(registry):
    api = registry.adapters
    api.provider("my-cloud", MyProductProvider)
    api.replace_provider("openai", MyProductProvider)
    api.disable_provider("ollama")
```

### 实现方式二：manifest 禁用 provider

```yaml
features:
  disabled_providers:
    - ollama
    - openrouter
```

### 实现方式三：声明式

```python
from qwenpaw.extensions import ExtensionSpec, FeaturePolicy, ProviderPatch

extension = ExtensionSpec(
    name="my_product",
    features=FeaturePolicy(disabled_providers={"ollama"}),
    provider_patches=(
        ProviderPatch("my-cloud", MyProductProvider),
        ProviderPatch("openai", MyProductProvider, replace=True),
    ),
)
```

### `ProviderPatch` 字段完整说明

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `provider_id` | `str` | 必填 | provider id |
| `provider_cls` | `type[Any]` | 必填 | provider 类 |
| `replace` | `bool` | `False` | `False` 为新增，`True` 为替换 |

## 十四、插件扩展统一入口

插件内部可以通过 `PluginApi.extensions` 获取同一套 `ExtensionAdapters`，因此插件不用自己 import 内部 registry。

```python
def setup(api):
    ext = api.extensions
    ext.disable_plugin("community-demo")
    ext.plugin_search_path("~/.myproduct/plugins")
    ext.cli_command("plugin-diagnose", "my_plugin.cli", "diagnose")
```

插件策略可通过 manifest 配置：

```yaml
plugins:
  allowed_plugins:
    - my-product-plugin
  extra_search_paths:
    - ~/.myproduct/plugins
```

## 十五、Skill 服务和 Control Command

### Skill 服务

适合业务代码或插件复用 QwenPaw 的 skill 服务能力。

```python
def extension(registry):
    api = registry.adapters
    skill_service = api.skill_service("~/.myproduct/agents/default")
    pool_service = api.skill_pool_service()
```

### Control command

适合给 runner 注册新的控制命令。

```python
class PauseCommand:
    command_name = "pause"

    async def handle(self, *args, **kwargs):
        return "paused"

def extension(registry):
    api = registry.adapters
    api.control_command(PauseCommand())
```

移除命令：

```python
def extension(registry):
    registry.adapters.unregister_control_command("pause")
```

如果产品有额外的优先级注册表，也可以传入：

```python
api.control_command(
    PauseCommand(),
    priority="high",
    priority_registry=my_priority_registry,
)
```

## 十六、品牌化运行时文案和 restore 文件

这部分多数情况下自动生效。SDK 会根据 `ProductSpec` 做以下替换：

| 原内容 | 替换为 |
| --- | --- |
| `QwenPaw` | `product.product_name` |
| `qwenpaw` | `product.module_alias` |
| `QWENPAW` | `product.env_prefixes[0]` |
| `~/.qwenpaw` | `product.working_dir` 的友好显示 |

自动覆盖范围包括：

1. CLI group 和 subcommand help。
2. click 输出中的常见 QwenPaw 文案。
3. `init` 安全提示和 telemetry 提示。
4. Provider 提示中的本地 provider 名和 CLI 命令。
5. restore lock/state 等内部文件名，例如 `.myproduct_restore.lock`。

可手动使用的 API：

```python
from qwenpaw.extensions import (
    brand_text,
    cli_invocation,
    product_local_provider_name,
    restore_artifact_name,
)

brand_text("Run qwenpaw models config")
cli_invocation("models", "config")          # myproduct models config
product_local_provider_name()               # MyProduct Local
restore_artifact_name(".lock")              # .myproduct_restore.lock
```

## 十七、声明式 `ExtensionSpec` 完整说明

`ExtensionSpec` 适合把多个扩展能力集中成一个对象，便于审计、测试和跨产品复用。

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `name` | `str` | 必填 | 扩展名 |
| `product` | `ProductSpec | None` | `None` | 产品配置 |
| `logging` | `LoggingSpec | None` | `None` | 日志配置。若为空且有 product，会自动用 `LoggingSpec.from_product(product)` |
| `features` | `FeaturePolicy` | `FeaturePolicy()` | 功能开关 |
| `plugin_policy` | `PluginPolicy` | `PluginPolicy()` | 插件策略 |
| `cli_patch` | `CliPatch` | `CliPatch()` | CLI patch |
| `app_patch` | `AppPatch` | `AppPatch()` | FastAPI patch |
| `provider_patches` | `tuple[ProviderPatch, ...]` | `()` | Provider patch |
| `builtin_channels` | `tuple[BuiltinChannelSpec, ...]` | `()` | 内置 channel |

完整示例：

```python
from qwenpaw.extensions import (
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
    RouterSpec,
)

extension = ExtensionSpec(
    name="my_product",
    product=ProductSpec(
        product_name="MyProduct",
        module_alias="myproduct",
        cli_name="myproduct",
        env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"),
        working_dir="~/.myproduct",
        secret_dir="~/.myproduct.secret",
        console_static_dir="/opt/myproduct/console",
    ),
    logging=LoggingSpec(
        namespace="myproduct",
        file_path="~/.myproduct/logs/runtime.log",
    ),
    features=FeaturePolicy(
        disabled_features={"builtin_qa_agent"},
        disabled_channels={"discord"},
        disabled_providers={"ollama"},
    ),
    plugin_policy=PluginPolicy(extra_search_paths=("~/.myproduct/plugins",)),
    cli_patch=CliPatch(
        add={
            "diagnose": CliCommandPatch(
                name="diagnose",
                module="my_product.cli.diagnose",
                attribute="diagnose",
            )
        }
    ),
    app_patch=AppPatch(routers=(RouterSpec(router, prefix="/api/my-product"),)),
    provider_patches=(ProviderPatch("my-cloud", MyProductProvider),),
    builtin_channels=(BuiltinChannelSpec("workchat", WorkChatChannel),),
)
```

## 十八、测试和调试

### 使用独立 registry 测试

```python
from qwenpaw.extensions import ExtensionRegistry, ProductSpec, use_extension_registry

def test_product_config():
    registry = ExtensionRegistry()
    registry.configure_product(ProductSpec(product_name="MyProduct"))

    with use_extension_registry(registry):
        assert registry.product.product_name == "MyProduct"
```

### 手动加载 manifest

```python
from qwenpaw.extensions import ExtensionRegistry, load_extensions

registry = ExtensionRegistry()
load_extensions(
    registry=registry,
    config_path="tests/fixtures/myproduct.yaml",
    include_entry_points=False,
)
```

### 检查当前 registry

```python
from qwenpaw.extensions import get_extension_registry

registry = get_extension_registry()
print(registry.product)
print(registry.features)
print(registry.cli.added)
```

## 十九、完整 Demo 示例

下面示例展示一个业务产品如何把 manifest、包内前端资源、装饰器、CLI、FastAPI、provider、channel、插件策略串起来。

### 目录结构

```text
my_product/
  pyproject.toml
  src/my_product/
    __init__.py
    cli.py
    manifest.yaml
    extension.py
    console/
      index.html
    api.py
    commands.py
    llm.py
    channels/
      workchat.py
```

### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "my-product"
version = "2.0.0"
dependencies = ["qwenpaw==1.1.9b1"]

[project.scripts]
myproduct = "my_product.cli:main"

[project.entry-points."qwenpaw.extension_manifests"]
my_product = "my_product:manifest.yaml"

[project.entry-points."qwenpaw.extensions"]
my_product = "my_product.extension:extension"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
my_product = ["manifest.yaml", "console/**"]
```

### src/my_product/manifest.yaml

```yaml
product:
  name: MyProduct
  version: 2.0.0
  module_alias: myproduct
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
  console_static_dir: ./console
  agent_prompt_files:
    - MY_PRODUCT.md
    - AGENTS.md
    - SOUL.md
    - PROFILE.md

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

plugins:
  extra_search_paths:
    - ~/.myproduct/plugins
```

### src/my_product/cli.py

```python
def main() -> None:
    from qwenpaw.extensions import load_extensions

    load_extensions(force=True)

    from qwenpaw.cli.main import cli

    cli()
```

### src/my_product/api.py

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}
```

### src/my_product/commands.py

```python
import click

@click.command()
def diagnose() -> None:
    click.echo("MyProduct diagnose ok")
```

### src/my_product/llm.py

```python
class MyProductProvider:
    provider_id = "my-cloud"
```

实际 provider 类应实现 QwenPaw provider 所需接口。

### src/my_product/channels/workchat.py

```python
class WorkChatConfig:
    pass

class WorkChatChannel:
    pass
```

实际 channel 类应实现 QwenPaw channel 所需接口。

### src/my_product/extension.py

```python
from qwenpaw.extensions import BuiltinChannelSpec, qwenpaw_extension

from my_product.api import router
from my_product.channels.workchat import WorkChatChannel, WorkChatConfig
from my_product.llm import MyProductProvider

extension = qwenpaw_extension("my_product")

@extension.configure
def configure(context) -> None:
    api = context.adapters

    api.router(router, prefix="/api/my-product", tags=["my-product"])

    api.cli_command(
        "diagnose",
        "my_product.commands",
        "diagnose",
    )
    api.cli_alias("models", "model")
    api.disable_cli_command("update")

    api.provider("my-cloud", MyProductProvider)
    api.disable_provider("ollama")

    api.builtin_channel(
        BuiltinChannelSpec(
            key="workchat",
            factory=WorkChatChannel,
            config_model=WorkChatConfig,
            default_enabled=True,
            display_name="Work Chat",
        )
    )

    api.plugin_search_path("~/.myproduct/plugins")
```

### 构建和验证

```powershell
python -m pip wheel . -w dist --no-deps
python -m pip install dist\my_product-2.0.0-py3-none-any.whl

myproduct -h
myproduct init --defaults
myproduct app --host 0.0.0.0 --port 18789
```

预期效果：

1. CLI help 显示 `myproduct` 和 `MyProduct`。
2. 工作目录使用 `~/.myproduct`。
3. 环境变量优先读取 `MYPRODUCT_*`，再回落到 `QWENPAW_*` 和 `COPAW_*`。
4. 前端静态资源从包内 `my_product/console` 提供。
5. `diagnose` 命令可用，`update` 命令被禁用，`model` 是 `models` 的别名。
6. `my-cloud` provider 注册成功，`ollama` provider 被禁用。
7. `workchat` 内置 channel 注册成功。
8. restore lock 文件名使用 `.myproduct_restore.lock`。
