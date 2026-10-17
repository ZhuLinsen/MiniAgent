# MiniAgent 项目状态与 DSH 对照

核对日期：2026-10-17。主线基准：[`64c1fcb`](https://github.com/ZhuLinsen/MiniAgent/commit/64c1fcbcb0b3168168d969a74b6c85e5ec4fa429)。本分支集成展示 PR #15 与运行时 PR #13；表中主线能力仍按此基准区分，后续状态请重新核对，不能把快照当成自动更新的能力承诺。

## 定位

**Python 原生的迷你 Harness + 编程 Agent。小内核、插件组合、终端直接用。**

受 DSH 的插件思路启发，用 Python 实现常用 Agent 工作流，提供可阅读、可嵌入的运行时和可直接使用的 CLI。主要用户是需要定制自己的 Coding Agent、学习 Harness 或做轻量自动化的 Python 开发者。

推荐 GitHub About：

> A Python-native mini harness + coding agent. Small core, composable plugins, MCP, Skills & resumable sessions.

短版：`A small Python harness for practical coding agents.`

包描述在 `pyproject.toml` 同步更新。GitHub About 文案在此供维护者确认；本 PR 不修改仓库设置。

DSH 本身已有 Python SDK，其 Python 客户端启动打包的 DSH 运行时；MiniAgent 的区别在于运行时自身用 Python 编写。依据：[DSH 架构 / Application launch](https://github.com/deepseek-ai/deepseek-harness/blob/1600d8a1e140dcde43a1a0941940a0480712c011/docs/architecture.md)。因此采用“受 DSH 启发的 Python 原生 Harness”，避免用户把它理解成官方 SDK 或协议兼容移植。

## 主要 PR 是否真正进入主线

| PR | 核对结果 | 说明 |
| --- | --- | --- |
| #7 | 已合入 | 异步 Harness、静态插件依赖、统一工具授权 |
| #8 / #14 | 已进入主线 | #8 合到父分支后，经 #14 接入 main；不能只看 #8 的 merged 标记 |
| #9 | 已合入 | 会话日志、执行恢复与压缩 |
| #10 | 已合入 | 官方 MCP stdio、Skill 工具白名单 |
| #11 | 已合入 | 默认 CLI 接线、恢复安全、交付验证 |
| #12 | 已合入 | 连接向导、模型选择、凭据管理 |
| [#13](https://github.com/ZhuLinsen/MiniAgent/pull/13) | 本分支已集成，待合入 main | 响应式生命周期、服务注入与可替换 Loop；基于 #15 组合验证，顺序为 #15 → #13 |

## 常用能力矩阵

参照固定版本的 [DSH 架构](https://github.com/deepseek-ai/deepseek-harness/blob/1600d8a1e140dcde43a1a0941940a0480712c011/docs/architecture.md) 与 [Agent Loop](https://github.com/deepseek-ai/deepseek-harness/blob/1600d8a1e140dcde43a1a0941940a0480712c011/packages/core/agent-loop/README.md)，按场景核对，未用菜单数量或包数量计算覆盖率。

| 场景 | 当前主线 | 证据 / 差异 |
| --- | --- | --- |
| 模型 → 工具 → 模型循环 | 已有 | `agent.py`、`llm.py`；真实读 → 改 → 测任务见 [Demo](demo.md) |
| 多 Provider 和流式工具调用 | 已有 | `test_llm.py`、`test_provider_protocols.py`；原生供应商协议用本地 HTTP 测试，真实 Anspire 验收单独记录 |
| Context、Service、插件清理、事件 | 已有轻量实现 | `test_harness.py`；静态插件依赖、失败回滚、逆序清理，不是 Cordis Fiber 树 |
| 缺依赖等待、失活与恢复 | #13 待合入 | 主线缺依赖会报错；#13 显式启用 reactive 后在启动/下一次任务边界协调，无后台监听 |
| 可替换 Agent Loop | #13 待合入 | 主线固定调用原生 Loop；#13 将它注册为服务 |
| 代码搜索、文件编辑、命令执行 | 已有 | `test_code_tools.py`、`test_tool_registry.py`、`test_runtime_recovery.py` |
| 工具 Schema、授权与工作区检查 | 已有 | Policy 和 Skill 的执行入口统一；Shell/MCP/插件仍为可信代码，未提供容器沙箱 |
| 持久会话、压缩、取消与异常恢复 | 已有 | `test_session.py`、`test_runtime_recovery.py`；未知副作用不自动重放，需核实后 resolve |
| Usage / Cost | 部分 | 模型返回的用量通过事件和 CLI 展示；尚无统一费用计价或跨会话费用账本，不把 tokens 当成已核实金额 |
| Skills / MCP | 已有受限实现 | Skill 标量 frontmatter + 工具白名单；MCP 仅 stdio；本地真实服务测试在 `test_mcp_skills.py` |
| 首次连接、模型选择、终端反馈 | 已有，本 PR 改善展示 | `test_connections.py`、`test_cli_runtime.py`；平台凭据库的真实覆盖仍不完整 |
| 子 Agent、后台任务、Web/Desktop、HMR、插件市场 | 未实现相应产品能力 | 旧 Orchestrator 不等于原生 Harness 的子 Agent；这些不纳入当前轻量 CLI 的完成声明 |

结论：已经覆盖选定的日常 CLI Coding Agent 工作流。插件完全可替换的目标还差 #13；完整 DSH 功能与体验仍有明显差距，不能宣称“DSH 80% 已完成”或产品等价。

## 代码简单与数量

统计命令：`python scripts/source_stats.py`。物理行包含注释和空行；全部包统计包括旧教学、扩展与兼容代码，不包含测试、脚本和第三方依赖。

| 口径 | 主线基准 | 本次变更 | 差额 |
| --- | ---: | ---: | ---: |
| 四文件核心 | 531 | 598 | +67 |
| 含 Policy / 工具插件 / Session 的运行机制 | 833 | 900 | +67 |
| 全部官方包 Python | 5,056 | 5,148 | +92 |

92 行增量中，23 行在 `cli_runtime.py` 改善展示，69 行来自 #13 的响应式依赖与可替换 Loop；#13 相对 #15 的核心增量为 67 行。没有新增运行时依赖，也没有把代码移出统计边界。演示录制脚本服务于可复现媒体，不承载 Agent 运行逻辑。

核心在 500–700 行目标内；全部包尚未达到 2,000–2,800 行目标。两条旧入口合计 1,169 行，旧基础工具 682 行，文本解析 304 行，反思 197 行，旧编排 194 行，是优先评估的维护成本。它们与公共导入及旧用户耦合，不能直接相减当作已完成精简。

下一步应按 [迁移门槛](legacy-migration.md) 收敛旧文本工具链和教学入口，保留可用迁移路径，再以实际构建、安装和任务测试证明代码减少；不要用压行或修改统计口径完成指标。

## 本次验证与剩余验收

- 主线基准离线测试：278 通过，3 项 live 排除。
- #15 本地（Windows / Python 3.12）：280 通过，3 项 live 排除；#13 与 #15 的组合验证以本 PR 检查记录为准。
- 两个展示回归覆盖终端路径摘要、帮助语义、字面提示和重复输出；已有非 TTY / NO_COLOR、取消、连接失败与切换用例继续保留。
- 本次真实 Anspire 修复任务通过；这是一个刻意缩小的函数修复，不能代表大型仓库任务成功率、原生多 Provider 验收或性能比较。
- Linux / macOS 外观、macOS/Linux 系统凭据库、首次使用者观察、长会话和真实复杂仓库任务尚缺实测。
- 静态截图证明实际输出和布局；易用、美观与传播效果仍需维护者和用户反馈。

## 合入与回滚

展示 PR #15 基于 main，运行时 PR #13 基于 #15 组合验证；按 #15 → #13 合入，更新父分支后重新核对差异和 CI。README 和本表中的状态需要跟随实际合入结果更新。

本 PR 不修改模型协议、工具权限或会话格式。回滚本 PR 的提交可恢复之前 CLI 展示、首页和包描述，已有会话文件继续保留。
