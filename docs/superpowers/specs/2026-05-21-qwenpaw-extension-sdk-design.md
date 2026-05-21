# QwenPaw Extension SDK Design

## 背景

QwenPaw 是一个开源个人 Agent 助手，后端基于 Python、FastAPI、Click，前端基于 TypeScript。目标是在合规约束下把 QwenPaw 当作依赖库使用，或只对 QwenPaw 做通用扩展能力修改，再由业务产品通过公开 API 完成定制。

本设计采用“QwenPaw 内置通用 extension 层 + 业务侧独立 SDK 包”的方案。QwenPaw 仓库只暴露通用能力，不写任何业务线逻辑；业务产品通过独立 Python 包、配置文件、环境变量、entry point 注册自己的产品能力。

命名约定：避免使用定制类英文命名。公共 API、包名和文件名统一使用 `extension`、`ExtensionRegistry`、`ExtensionSpec` 等开发语义。

## 源码观察

当前代码已经有一些可复用基础：

- `src/qwenpaw/plugins/` 已支持插件注册 provider、tool、FastAPI router、startup/shutdown hook、control command。
- `src/qwenpaw/app/channels/registry.py` 支持从 `WORKING_DIR/custom_channels` 发现自定义 channel。
- `src/qwenpaw/app/_app.py` 已支持通过 `QWENPAW_CONSOLE_STATIC_DIR` 替换前端静态资源。
- Agent 人设主要来自 workspace 中的 `AGENTS.md`、`SOUL.md`、`PROFILE.md`，由 `src/qwenpaw/agents/prompt.py` 拼装。
- 工具启用状态已经可以通过 `agent.json` 中的 `tools.builtin_tools` 控制。
- 多 Agent profile 已有 `enabled` 字段，`MultiAgentManager.start_all_configured_agents()` 只启动 enabled agent。

当前仍偏硬编码的点：

- `src/qwenpaw/constant.py` 在 import 阶段读取 `QWENPAW_*`、`WORKING_DIR`、`SECRET_DIR`、`PROJECT_NAME`、QA Agent 常量。
- `src/qwenpaw/cli/main.py` 的 Click command 表是静态字典，CLI 名称主要靠 `pyproject.toml` 的 script entry。
- `src/qwenpaw/providers/provider_manager.py` 的内置 provider 通过 `_init_builtins()` 硬编码逐个 `_add_builtin()`。
- `src/qwenpaw/app/_app.py` 的 FastAPI app、lifespan、router include 顺序、console static fallback 多数在模块加载时固定。
- `src/qwenpaw/app/migration.py` 会默认创建 builtin QA agent。
- `src/qwenpaw/utils/logging.py` 根据 `PROJECT_NAME.lower()` 生成日志 namespace 和文件名。

## 方案选择

### 方案 A：QwenPaw 内置 extension 层 + 业务侧 SDK 包

在 QwenPaw 中新增 `src/qwenpaw/extensions/`，提供稳定的 registry、spec、config loader、entry point 加载、hook 调度。现有硬编码入口改为查询 extension registry。业务侧发布独立包，例如 `gdeclaw-qwenpaw-sdk` 或 `gdeclaw-qwenpaw-extension`，通过 entry point 或启动代码注册能力。

优点：

- 对开源代码侵入小，修改集中在少数入口。
- 通用能力沉淀在 QwenPaw，多个产品线可复用。
- 业务逻辑不进入 QwenPaw 仓库，符合合规约束。
- 后续合并上游主分支时冲突集中，主要发生在入口文件。

缺点：

- 需要在 QwenPaw 仓库新增通用 extension API。
- import-time 常量需要谨慎迁移，避免破坏现有默认行为。

### 方案 B：完全外部 monkey patch

业务包 import QwenPaw 后重写类、函数、变量、Click command、FastAPI app。

优点：

- 不改 QwenPaw 仓库。

缺点：

- QwenPaw 很多行为在 import 阶段确定，后置 patch 容易失效。
- CLI script、uvicorn app 字符串、日志 namespace、内置 QA 创建、provider 单例初始化都不稳定。
- 上游代码变化后 patch 很难测试覆盖。

### 方案 C：产品侧 fork 深度定制

直接在 QwenPaw 分支内改业务逻辑。

优点：

- 短期交付最快。

缺点：

- 合规风险高。
- 合主分支成本高。
- 多产品线复用差。

结论：采用方案 A。

## 总体架构

新增内部包：

```text
src/qwenpaw/extensions/
  __init__.py
  config.py
  env.py
  registry.py
  specs.py
  loader.py
  hooks.py
  cli.py
  app.py
  providers.py
  channels.py
  features.py
  logging.py
```

核心对象：

- `ExtensionRegistry`：全局 registry，持有产品规格、feature policy、CLI patch、FastAPI patch、provider/channel/plugin/tool/agent template 注册信息。
- `ProductSpec`：产品名、版本、模块别名、CLI 名、环境变量前缀、工作目录、secret 目录、backup 目录、console static 目录。
- `EnvSpec`：环境变量解析规则，支持 `GDECLAW_*` 主前缀、`QWENPAW_*` 兼容前缀、`COPAW_*` legacy 前缀。
- `LoggingSpec`：日志 namespace、日志文件路径、日志格式、handler factory。
- `FeaturePolicy`：功能启停清单，例如 `builtin_qa_agent`、`telemetry`、`market`、`backup`、`local_models`、`cron`、`mcp`、`acp`、`voice`。
- `CliPatch`：Click 命令增删改、别名、隐藏原命令、替换 command group。
- `AppPatch`：FastAPI router 增删改、startup/shutdown hook、middleware hook、lifespan hook、console static dir。
- `ProviderPatch`：禁用、替换、注册 provider。
- `ChannelPatch`：禁用、替换、注册 channel。
- `AgentTemplatePatch`：注册 agent template、覆盖默认 prompt 文件、禁用 builtin QA。
- `PluginPolicy`：禁用插件、允许插件、增加插件搜索目录。

## 业务侧使用方式

业务包通过 entry point 注册：

```toml
[project.entry-points."qwenpaw.extensions"]
gdeclaw = "gdeclaw_qwenpaw_extension:register"
```

业务注册函数：

```python
from qwenpaw.extensions import ProductSpec, FeaturePolicy


def register(registry):
    registry.configure_product(
        ProductSpec(
            product_name="GdeClaw",
            product_version="2.0.0",
            module_alias="gdeclaw",
            cli_name="gdeclaw",
            env_prefixes=("GDECLAW", "QWENPAW", "COPAW"),
            working_dir="~/.gdeclaw",
            secret_dir="~/.gdeclaw.secret",
            backup_dir="~/.gdeclaw.backups",
            console_static_dir="/opt/gdeclaw/console",
        )
    )

    registry.configure_features(
        FeaturePolicy(
            disabled_features={"builtin_qa_agent", "telemetry"},
            disabled_channels={"wechat", "qq", "voice"},
            disabled_providers={"openrouter", "gemini"},
            disabled_plugins={"qwenpaw-pet"},
        )
    )
```

也支持配置文件：

```yaml
product:
  name: GdeClaw
  version: 2.0.0
  cli_name: gdeclaw
  env_prefixes: [GDECLAW, QWENPAW, COPAW]
  working_dir: ~/.gdeclaw
  secret_dir: ~/.gdeclaw.secret
  console_static_dir: /opt/gdeclaw/console

features:
  disabled:
    - builtin_qa_agent
    - telemetry
  disabled_channels:
    - wechat
    - qq
  disabled_providers:
    - openrouter
    - gemini
  disabled_plugins:
    - qwenpaw-pet
```

默认配置路径由环境变量指定：

- `QWENPAW_EXTENSION_CONFIG`
- 或业务前缀等价变量，例如 `GDECLAW_EXTENSION_CONFIG`

## 数据流

启动时的推荐顺序：

1. `qwenpaw.__init__` 或 `qwenpaw.constant` 早期调用 `load_extension_registry()`。
2. loader 从 entry point、显式配置文件、环境变量加载 extension。
3. `constant.py` 通过 registry 解析产品名、工作目录、secret 目录、env 前缀、文件名。
4. CLI 创建时从 registry 读取命令 patch。
5. FastAPI app 创建前后应用 app hooks、middleware hooks、router patches。
6. ProviderManager 初始化内置 provider 前应用 provider policy。
7. Channel registry 返回前应用 channel policy。
8. migration 创建 default/QA agent 前检查 feature policy。
9. plugin loader 发现和加载插件前应用 plugin policy。

## 关键设计

### 环境变量

新增 `EnvResolver`，统一替换当前 `_get_env()`：

- `resolver.get("WORKING_DIR")` 会按前缀顺序查找 `GDECLAW_WORKING_DIR`、`QWENPAW_WORKING_DIR`、`COPAW_WORKING_DIR`。
- 现有 `EnvVarLoader.get_str("QWENPAW_XXX")` 保持兼容，但内部转为 canonical key 解析。
- 对已有环境变量不破坏：默认前缀仍为 `("QWENPAW", "COPAW")`。
- 业务 extension 可以把 `GDECLAW` 放在第一优先级。

### 产品和路径

`ProductSpec` 控制：

- `PROJECT_NAME`
- `WORKING_DIR`
- `SECRET_DIR`
- `BACKUP_DIR`
- `PLUGINS_DIR`
- `CUSTOM_CHANNELS_DIR`
- `DEFAULT_MEDIA_DIR`
- `DEFAULT_LOCAL_PROVIDER_DIR`
- `CONSOLE_STATIC_DIR`

如果没有 extension，所有默认值保持当前行为。

### CLI

`src/qwenpaw/cli/main.py` 的 `lazy_subcommands` 改为从 `get_cli_registry().build_lazy_subcommands(defaults)` 生成。

能力：

- 增加命令：`registry.cli.add_command("foo", "pkg.mod", "cmd")`
- 删除命令：`registry.cli.disable_command("doctor")`
- 覆盖命令：`registry.cli.replace_command("models", "gdeclaw.cli.models", "models_group")`
- 别名命令：`registry.cli.alias_command("skill", "skills")`
- 改 version 名称：`prog_name=product.product_name`

命令行可执行名仍由安装包 entry point 决定。业务包应声明：

```toml
[project.scripts]
gdeclaw = "qwenpaw.cli.main:cli"
```

### FastAPI

`AppExtensionRegistry` 提供：

- `before_app_create`
- `after_app_create`
- `before_include_routers`
- `after_include_routers`
- `startup_hooks`
- `shutdown_hooks`
- `middleware_hooks`
- `console_static_dir`

路由注册遵循现有插件路由的原则：业务路由应挂在 `/api` 下，并在 SPA catch-all 之前注册。

### Provider

`ProviderManager._init_builtins()` 改为遍历默认 provider 列表并应用 policy：

- disabled provider 不加入 `builtin_providers`。
- replacement provider 覆盖同 id。
- additional provider 作为 builtin-like provider 注册。

已有 plugin provider 机制保留。

### Channel

`get_channel_registry()` 返回前应用 policy：

- 删除 disabled channel。
- replacement channel 覆盖同 key。
- additional channel 合并进入 registry。

`get_available_channels()` 仍支持环境变量过滤，但改用 `EnvResolver` 支持业务前缀。

### Agent 人设和 QA Agent

Agent 人设的推荐扩展方式：

- 业务侧创建自有 agent template。
- 或通过配置指定默认 prompt source 目录。
- 或在 workspace 初始化时复制业务自己的 `AGENTS.md`、`SOUL.md`、`PROFILE.md`。

`builtin_qa_agent` 作为 feature，可禁用。禁用后 `ensure_qa_agent_exists()` 不创建 QA agent。已有配置中的 QA agent 不强制删除，但可通过 feature policy 在启动时自动标记 disabled，避免破坏用户数据。

### 日志

`LoggingSpec` 支持：

- `namespace`
- `file_path`
- `file_basename`
- `console_format`
- `file_format`
- `handler_factory`

默认行为保持 `PROJECT_NAME.lower()` 和 `WORKING_DIR / "{namespace}.log"`。

### 插件

保留现有 plugin 系统，增加 policy 层：

- `disabled_plugins`
- `enabled_plugins` 白名单
- `additional_plugin_dirs`
- `plugin_config_overrides`

plugin loader discover 后、load 前应用 policy。

### 前端替换

统一使用 `ProductSpec.console_static_dir`，环境变量仍支持：

- 业务前缀：`GDECLAW_CONSOLE_STATIC_DIR`
- 默认前缀：`QWENPAW_CONSOLE_STATIC_DIR`
- legacy：`COPAW_CONSOLE_STATIC_DIR`

如果业务提供完整前端资源目录，只要包含 `index.html` 即可替换整体控制台。

## 14 项诉求覆盖

1. 模块名称：通过业务包 entry point、`module_alias`、CLI script 提供外部模块名。
2. 产品名称/版本：`ProductSpec.product_name`、`product_version`。
3. 工作目录/配置路径：`ProductSpec` + `EnvResolver`。
4. Agent 人设：`AgentTemplatePatch`、prompt source、workspace prompt 文件。
5. Skill CLI 名称：`CliPatch` alias/replace。
6. 日志名称/路径/格式：`LoggingSpec`。
7. 环境变量名称：`EnvResolver` 多前缀解析。
8. Click 命令增删改：`CliPatch`。
9. channel 增删改：`ChannelPatch`。
10. 禁用功能：`FeaturePolicy` 配置文件。
11. provider 增删改：`ProviderPatch`。
12. 插件增删改：`PluginPolicy` + 现有 plugin API。
13. FastAPI 路由和生命周期：`AppPatch`。
14. 前端整体替换：`ProductSpec.console_static_dir`。

## 错误处理

- extension 加载失败时默认不阻塞 QwenPaw 启动，记录 error 日志；可配置 `strict=True` 让启动失败。
- 配置文件格式错误时给出路径、字段和错误原因。
- 禁用 required channel，例如 `console`，默认拒绝并记录错误；除非 extension 显式设置 `allow_disable_required=True`。
- 禁用 active provider 时，如果 active model 指向被禁用 provider，API 返回明确错误，并在 doctor 中提示。
- 路由 prefix 冲突时抛出 `ValueError`，避免后注册覆盖先注册。
- CLI command 冲突默认报错；可指定策略 `replace` 或 `alias`。

## 测试策略

单元测试：

- `EnvResolver` 多前缀优先级和 legacy fallback。
- `ProductSpec` 默认值兼容当前 `QWENPAW_*` 行为。
- CLI registry 的 add/disable/replace/alias。
- Provider registry 禁用/替换/新增。
- Channel registry 禁用/替换/新增。
- Feature policy 禁用 builtin QA agent。
- LoggingSpec 生成 namespace 和 log path。

集成测试：

- 使用临时工作目录启动 FastAPI，验证 `GDECLAW_WORKING_DIR` 生效。
- 安装一个测试 extension entry point，验证 `/api/version`、console static、provider list、channel types。
- 使用 `gdeclaw = qwenpaw.cli.main:cli` 测试 CLI 命令别名。
- 禁用 QA agent 后启动，验证不会新建 QA profile。

兼容性测试：

- 不安装任何 extension 时，现有测试应保持通过。
- 只设置原 `QWENPAW_*` 环境变量时行为不变。
- 只设置 legacy `COPAW_*` 时继续 fallback。

## 实施边界

本阶段只建设通用 extension SDK 框架和必要接入点，不实现任何具体业务产品逻辑。

不在 QwenPaw 中写入 `GdeClaw` 专有逻辑。`GDECLAW_*` 只作为示例和测试 fixture 出现，不作为默认行为。

不重命名 Python 包 `qwenpaw` 本身。模块名称的业务可见层通过业务 SDK 包、console 文案、CLI script 和 product spec 实现。

不删除已有用户数据。禁用功能只影响启动、展示和新建行为；已有配置保留，必要时标记 disabled。

## 开放问题

- 业务侧最终包名倾向 `gdeclaw-qwenpaw-extension` 还是 `gdeclaw-qwenpaw-sdk`。本设计不强制。
- 是否需要为 extension 配置提供 JSON Schema，便于产品线在 IDE 中校验。
- 是否要求 doctor 输出 extension 诊断信息，例如当前产品名、env 前缀、禁用功能清单、加载的 extension 包。
