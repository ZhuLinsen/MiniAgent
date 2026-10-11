# MiniAgent

**小内核，实用 Agent。** 一个以插件为核心的 Python Agent Harness，组合模型、工具、Skills、MCP 和可恢复会话。

[English](README_EN.md) · [运行与迁移指南](docs/lean-harness.md) · [变更记录](docs/CHANGELOG.md) · [CI](https://github.com/ZhuLinsen/MiniAgent/actions/workflows/ci.yml)

需要 **Python 3.11+**。当前版本为 **0.2.0a1**：适合评估新架构和开发插件；真实多模型验收及总体源码精简仍未完成。

## 三步开始

```bash
git clone https://github.com/ZhuLinsen/MiniAgent.git
cd MiniAgent
python -m pip install .
```

在项目内创建 `.env`，填入自己的 Provider 密钥和模型 ID。下面的 `<model-id>` 必须替换；Qwen 使用 `dashscope:<model-id>` 和 `DASHSCOPE_API_KEY`，Claude 使用 `anthropic:<model-id>` 和 `ANTHROPIC_API_KEY`。

```dotenv
DEEPSEEK_API_KEY=your-provider-key
LLM_MODEL=deepseek:<model-id>
```

```bash
miniagent --policy readonly --prompt "检查当前项目结构，说明主要入口"
miniagent
```

默认需要确认文件修改、Shell 和 MCP 调用；非交互模式拒绝确认。`--policy trusted` 适用于你明确信任的自动化任务。托管文件工具默认隐藏 `.env*`（`.env.example` 除外）、`.git` 和私钥文件，只有显式使用 `--allow-sensitive-files` 才开放。Shell、Python 插件和 MCP 服务属于可信代码，不受文件工具边界隔离。

## 核心能力

- 原生工具调用和流式文本；统一异步模型边界及 Provider 密钥隔离。
- 实例独立的工具注册表；插件依赖排序、失败回滚和逆序资源清理。
- `read / write / edit / grep / glob / bash` 编程工具，支持工作区约束和授权。
- JSONL 会话、完整工具组的上下文压缩，以及异常副作用的人工核查恢复。
- 可切换的 Skill 执行白名单；官方 MCP SDK stdio 接入（可选安装）。

CLI 可用 `/help`、`/model`、`/plugins`、`/skills`、`/session`、`/stream`；`/plugins` 当前仅列出已加载插件。`--session <path>` 恢复已有会话，`/session new` 新建会话。模型切换会新建会话。

## Python API

```python
from miniagent import Harness
from miniagent.plugins import coding_tools
from miniagent.policy import Policy
from miniagent.session import Session

app = Harness(model="deepseek:<model-id>", policy=Policy(mode="readonly"),
              session=Session("task.jsonl"))
app.use(coding_tools())
print(app.run("检查项目结构"))
```

已有事件循环中使用 `await app.arun(...)`，并通过 `async with app` 管理资源。一个 Harness 同时只运行一个任务；插件和 Skill 仅在空闲时修改。

## 一个自定义插件

```python
from miniagent import Harness, Plugin
from miniagent.policy import Policy
from miniagent.tools.registry import Tool

def calculator(ctx):
    ctx.tool(Tool("add_one", "Add one", {"type": "object",
                  "properties": {"n": {"type": "integer"}}, "required": ["n"]},
                  lambda n: n + 1))

app = Harness(model="deepseek:<model-id>", policy=Policy(mode="trusted"))
app.use(Plugin("calculator", calculator))
print(app.run("调用 add_one 给 2 加 1"))
```

这是显式信任自定义工具的示例。更多模型配置、MCP 安装与插件示例、Skill 切换、恢复步骤和兼容边界见 [运行指南](docs/lean-harness.md)。

## 验证与版本边界

CI 覆盖 Windows/Linux、Python 3.11/3.12、离线回归、原生运行时静态检查、依赖审计、构建，以及不安装 MCP/Legacy 扩展的 wheel 验证。OpenAI、DeepSeek、DashScope/Qwen、Anthropic 的 SDK 多轮工具协议使用本地 HTTP 测试；它们不代表真实 API 验收。

`python scripts/source_stats.py` 分别报告四文件内核、含 Policy/工具插件/Session 的运行机制、以及**全部官方 Python 源码**。旧教学与扩展兼容代码仍保留，总体 2000～2800 行目标尚未达到。未提供真实模型任务截图或性能对比，不以模拟输出替代真实演示。

旧教学 CLI 使用 `miniagent --legacy`；基础/系统工具需安装 `miniagent[legacy]`。旧隐式 MCP API 已移除，按指南迁移到 `mcp_plugin`。动态依赖恢复、长期 Memory 和 Streamable HTTP 不属于本次 alpha 交付。

## 致谢与许可证

编程工具设计参考 [nanocode](https://github.com/1rgs/nanocode)。本项目使用 [Apache License 2.0](LICENSE)。
