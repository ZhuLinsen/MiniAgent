# 原生版迁移 / Native 0.3 migration

本分支为 **0.3.0a1 候选**，尚未发版。按维护者明确选择，新版集中原生 Harness API，旧版单独保留，不在新包内复制旧实现。

## 旧版在哪里

旧版分支：[codex/legacy-pre-harness](https://github.com/ZhuLinsen/MiniAgent/tree/codex/legacy-pre-harness)，固定创建自 `b437298d60e93899f7b47964267e8513df6fd3f7`：这是 PR #7 合入提交的第一父提交，包含 #6 修复。分支内容与当时提交一致，没有用新版本覆盖旧版。

```bash
git clone --branch codex/legacy-pre-harness --single-branch https://github.com/ZhuLinsen/MiniAgent.git MiniAgent-legacy
```

在独立虚拟环境中按旧分支说明安装。旧分支是历史快照；原有模型与供应商服务是否仍可用，需要按该分支环境验证。0.2 过渡实现和完整测试仍可在本 PR 基线 `9f17af6` 的 Git 历史查看。

## 公开入口迁移

| 旧入口 | 原生版路径 | 变化 |
| --- | --- | --- |
| `MiniAgent`、`run(mode="text")`、`--legacy` | `Harness`、`app.run()` / `await app.arun()`、默认 CLI | 只使用原生工具调用，不再解析 TOOL/ARGS 文本；旧入口明确提示迁移 |
| `Memory` / `memory.json` | 显式 `Session(path)` / CLI JSONL 会话 | 保留旧文件，不自动转换；长期事实记忆暂不新增 |
| `Orchestrator` | 旧编排继续使用旧分支；原生版可用 Python 调用 Harness 并组合 Plugin | 没有内置编排器等价替代，本轮不新增子 Agent 或可替换 Loop 接口 |
| `register_tool`、全局工具目录、`load_tools` | `ctx.tool(Tool(...))`、`coding_tools()` | 工具归属各 Harness；导入文件工具不会写入全局注册表 |
| 同步 `code_tools.bash()` | `miniagent.plugins.shell()` 或 `coding_tools()` 中的 bash | 统一异步进程、超时、取消和输出上限；直接调用 shell 时超时抛异常 |
| `MCPClient` / `load_mcp_tools` | `mcp_plugin`、`miniagent[mcp]` | 官方 SDK stdio 生命周期与统一授权 |
| 内置系统、浏览器、搜索、环境变量、docx 工具 | 显式自定义 Plugin 或 MCP 服务 | 不再作为内置能力提供；原实现保留在旧分支 |
| Reflection / 文本 JSON 容错解析 | 原生模型消息和显式插件 | 移除自动反思和文本工具协议，不静默模拟旧行为 |

包顶层的 `from miniagent import MiniAgent` 等旧入口会报迁移提示；已删除的子模块（如 `miniagent.legacy`、`miniagent.memory`）和 `miniagent.agent.MiniAgent` 不再提供导入兼容。升级前应检查项目中的这些导入，而不只是替换启动命令。

## 最小 Python 迁移

```python
from miniagent import Harness, Policy, Session
from miniagent.plugins import coding_tools

app = Harness(model="provider:model-id", policy=Policy(mode="readonly"),
              session=Session("task.jsonl"))
app.use(coding_tools())
print(app.run("Inspect the project and explain its entry points"))
```

已有事件循环使用 `async with app` 和 `await app.arun(...)`。脚本用的 `app.run()` 会关闭本次运行的插件资源；会话数据保留。工具、授权、Skill 白名单、静态依赖检查与不确定副作用守卫继续有效。

## 配置迁移

JSON agent 顶层接受：`llm`、`providers`、`mcp_servers`、`system_prompt`、`context_budget`。`llm` 接受：`model`、`api_key`、`api_base`、`temperature`。未支持的字段明确报错，不继续悄悄忽略。

- 给模型补全 `provider:model-id`；未带前缀的 ID 统一归 OpenAI，不根据 URL 猜供应商。
- `LLM_TEMPERATURE` 现在实际生效，JSON `llm.temperature` 可覆盖。CLI 覆盖优先级保持不变。
- 旧 `default_tools`、`output_format`、`enable_reflection`、反思参数及未实际接线的 `llm.max_tokens` / `timeout` / `max_retries` 等需从 JSON 删除。
- `BASH_TIMEOUT`、`BASH_MAX_OUTPUT`、`TOOL_RESULT_LIMIT` 仍通过环境生效；不再在 AgentConfig 中保留无效镜像字段。
- `MAX_CONTEXT_MESSAGES` 改用 `context_budget` / `MINIAGENT_CONTEXT_BUDGET`。授权改用 `--policy`；所有 Shell/MCP 调用经过策略，不只匹配危险命令正则。
- `legacy`、`docx` 安装 extra 已退役；开发测试使用 `.[dev,mcp,credentials]`。进程检查依赖 psutil 仅属于测试，不是生产运行依赖。

支持的连接配置和系统凭据库未迁移格式，见 [连接指南](model-connections.md)。

## 数据与回滚

现有原生 JSONL 会话可继续打开，版本校验、写锁和 resolve 语义保留。旧 Memory JSON 不自动导入或删除；需要时在旧环境读取。未知副作用始终先检查再 resolve，不自动重放。

回滚原生版 PR 可恢复 0.2 过渡实现；切换到旧快照使用独立环境，保留所有数据文件。此 PR 不打 tag、不发版、不合入 main。

## 测试与代码量

本 PR 直接基于 main `9f17af6`，不依赖 #13 的响应式插件和可替换 Loop，也不包含 #15 的 CLI 展示改动。相对该基线：四文件核心 **531 → 524**，运行机制 **833 → 827**，全部包 **5056 → 2031**。删除的是已退役实现，没有把它们挪到统计边界之外。

旧文本协议、系统工具、Memory、Orchestrator 和旧入口的专用测试随能力退役。主线的原生 Harness、模型协议、授权、会话恢复、真实本地 MCP 和连接套件保留；Skill/工具案例迁移至原生 API，文本截断边界测试继续保留，并增加退役入口、包内容、配置拒绝和示例导入回归。测试数减少不作为质量提升的证据。
