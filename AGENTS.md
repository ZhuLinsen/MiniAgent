# AGENTS.md — MiniAgent 开发与审查约束

## 每次 Codex 运行必读

这是本仓库 AI 协作规则的唯一真源。进入本仓库开发、审查、修复或继续旧任务时，先读取本文件和受影响的现有代码；在其他工作目录操作 MiniAgent 时也应先读取本文件。用户明确指令优先。

每次变更都要落实四项原则：**核心简单、DSH 常用能力、易用美观、便于传播**。它们用于取舍、实现、测试和交付，不是宣传口号。CLAUDE.md 只链接本文件，不维护第二份规则。

## 项目定位与能力目标

MiniAgent 是以插件为核心的轻量 Python Agent Harness。目标是用容易读懂的小内核覆盖 DSH 常用 Agent 场景：模型调用、工具循环、Context/Service、插件生命周期与清理、事件、Skills、MCP 和可恢复会话。

能力必须有可运行示例、测试或真实任务证据。未逐项验证时，不宣称“已实现 DSH 大部分功能”、完整兼容或稳定发布。完整 Fiber 树、HMR、市场、Web 管理台等按实际需求单独评估，避免为对标数量扩大内核。

## 四项设计原则

### 核心简单

- 内核只负责 Agent 循环、插件/服务生命周期、统一工具入口与必要运行守卫。模型协议交给 any-llm，传输交给官方 SDK。
- 优先复用现有函数和配置入口。修复问题先补缺失边界，避免新建平行实现或引入通用框架。
- CLI、连接配置、显示、低频工具及专题集成放在外围；新能力优先作为插件组合。插件和 Shell 是可信代码，权限检查不等于沙箱。
- 易读比少几行更重要。禁止压行、藏逻辑、删安全检查或把代码挪到统计之外来满足预算。
- 四文件核心目标 500–700 物理行；全部官方包 Python 目标 2000–2800 行，超过 3000 行须在 PR 解释差额和迁移计划。现有总量超标是待解决问题，不能改口径宣称完成。
- 运行 `python scripts/source_stats.py`，分别报告 core、runtime mechanisms、全部包代码的变更前后差额。脚本定义统计边界，不复制另一套计数实现。

### DSH 常用能力

- 用 Context/Service、依赖声明和插件清理解决实际 Agent 任务；响应式依赖与可替换 Loop 按独立需求评估，不作为原生 API 精简的前置条件。新增生命周期行为必须说明等待、激活、失活、恢复和异常回滚。
- 默认优先稳定和显式语义；兼容性变化要说明迁移路径。运行中的任务禁止生命周期变更。
- 工具仍经 Schema、Policy 和 Skill 检查；会话保留原记录，不重放未知副作用。新能力不得破坏这些守卫。
- 自定义插件/Loop 的责任和可信边界必须写清楚，不把 Mock 或菜单选项当作真实远端兼容验收。

### 易用美观

- 首次成功路径要短：少量清晰选择即可配置模型并开始任务。自动化保持无交互，报错给出可执行提示。
- 复用 Rich 和既有 CLI 组件；菜单名称、编号、对齐、错误/成功状态保持一致，减少重复标题和冗长日志。不为简单交互新增大型 UI 依赖。
- 显示内容有界；非 TTY/NO_COLOR 输出可读。秘密不进入日志、报告或连接 JSON；无系统凭据库时明确告知仅在当前进程保留。
- 用户可见流程改变时验证首次使用、取消、失败降级、模型切换及旧配置行为中受影响的路径。

### 便于传播

- README 只保留定位、短快速开始、核心入口和最小示例；详细边界、排障、协议与迁移放 docs/ 专题文档。
- 中英文 README 同步评估；不更新其中一份时说明原因。截图、Demo 和性能数字必须可复现，标注版本、环境与局限。
- 每个能力优先提供一条容易复制的命令或一个短示例；使用明确占位符，不写死密钥、模型 ID、用户路径、端口或环境差异。
- 推广用语服从证据：alpha、剩余目标和未覆盖平台写清楚，不承诺“能力无限”或未经验证的产品等价。

## 目录边界与真源

- miniagent/agent.py、harness.py、llm.py、tools/registry.py：四文件核心；以统计脚本清单为准。
- policy.py、plugins.py、session.py：外围运行机制；连接配置在 connections.py，CLI 在 cli.py / cli_runtime.py。
- extensions/：可选集成；旧文本 API、系统工具与编排器保存在 codex/legacy-pre-harness 历史分支，原生版不重新引入，迁移见 docs/legacy-migration.md。
- tests/：确定性回归与显式 opt-in live 测试；scripts/：验证与构建；docs/：专题说明；.claude/reviews/：本地审查产物。
- 以可执行代码、脚本和工作流为准，发现相关文档漂移要顺手修正。AGENTS.md 不复制完整架构或过期实现。

## 每次工作顺序

1. 确认任务与影响边界，读取实现、配置、测试、CI 和必要文档；审查先看当前提交的 CI，再补缺口。
2. 对照四项原则选择最小可行改动；不夹带无关重构、依赖迁移或能力扩张。
3. 对真实缺陷先复现，再修复，补覆盖实际边界的回归；不写只镜像实现的测试。
4. 验证对应路径，核对源码差额、配置/凭据边界、用户流程与文档。轻量治理校验不能替代正确性、易用性或代码审查。
5. 交付说明改了什么、为什么、测试/CI、未验证项、风险和回滚；用户需要的是可审查结果，不是只给计划。

## 验证与协作资产

```bash
python -m pytest tests -q -m "not live"
python -m compileall -q miniagent
python scripts/source_stats.py
python scripts/check_ai_assets.py
```

按改动面使用 .github/workflows/ci.yml 的 Ruff、锁定依赖审计、构建及最小独立安装检查。真实 Provider 验收只在明确选择模型和凭据后 opt-in，不输出秘密，不把离线测试算作真实通过。

修改 AGENTS.md、CLAUDE.md 或 PR 模板时执行 `python scripts/check_ai_assets.py`。CLAUDE.md 必须是指向 AGENTS.md 的 Git 软链接；Windows 不支持实体链接时允许 checkout 的链接占位文件，但 Git 模式仍须为 120000。

## Git 与 PR

- 未经用户明确授权不 commit/tag/push；已授权的修复与 PR 更新继续推进。禁止直接 push main，合并需 maintainer 审核同意。
- 分支默认 codex/；提交用英文 Conventional Commits，不加 Co-Authored-By；PR 标题描述实际变更。
- PR 按必要性、相关性、描述/验证证据、正确性、合入条件审查；标题不是单独阻断项。
- 修复 PR 说明原问题、根因、修复点、回归风险；遵循 .github/PULL_REQUEST_TEMPLATE.md。
- 行为/配置变更同步专题文档和 docs/CHANGELOG.md。新增环境配置更新 .env.example。Unreleased 条目采用扁平 `- [类型] 描述`，不加三级分类标题。
- stacked PR 保留依赖顺序，优先 merge commit；更新父分支后同步后继分支并复核 diff。回滚逆序进行，保留会话数据。
- 不自动发版或打 tag。密钥、用户目录、模型、端口均通过现有配置/参数传递。
