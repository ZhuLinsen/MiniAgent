<p align="center">
  <img src="docs/assets/miniagent-banner.svg" width="800" alt="MiniAgent — Python 原生的迷你 Harness + Agent">
</p>

<p align="center"><strong>小内核，能干活。</strong><br>Python 原生的迷你 Harness + 编程 Agent。读得懂，改得动，终端里直接用。</p>

<p align="center">
  <a href="https://github.com/ZhuLinsen/MiniAgent/actions/workflows/ci.yml"><img src="https://github.com/ZhuLinsen/MiniAgent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB" alt="Python 3.11+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue" alt="Apache 2.0"></a>
  <img src="https://img.shields.io/badge/status-alpha-ff815c" alt="Alpha">
</p>

<p align="center"><a href="README_EN.md">English</a> · <a href="#快速开始">快速开始</a> · <a href="docs/lean-harness.md">使用指南</a> · <a href="docs/project-status.md">能力与代码量</a></p>

MiniAgent 把模型、工具循环、插件、Skills、MCP 和会话恢复组合成一个小型 Python Agent。你可以直接用它读代码、修改文件和运行测试，也可以把 Harness 嵌入自己的应用，用插件增加能力。

设计受 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 启发：小内核负责运行，能力通过插件组合。适合希望理解、定制和分享 Agent 的 Python 开发者。

## 看它完成一个任务

![MiniAgent 真实运行：读取代码、修复加法函数并执行测试](docs/assets/coding-session.png)

2026-10-17，Windows / Python 3.12，Anspire `qwen3.5-flash`：真实 API、真实文件工具、真实 Shell 测试。测试文件保持不变。图片由真实 CLI 输出导出渲染；这是一个小型修复任务，复现步骤与原始记录见 [演示说明](docs/demo.md)。

## 快速开始

需要 **Python 3.11+**，从当前源码安装：

```bash
git clone https://github.com/ZhuLinsen/MiniAgent.git
cd MiniAgent
python -m pip install ".[credentials]"
miniagent
```

第一次交互启动时，按提示选择服务商、填写密钥和模型 ID。密钥可保存在受支持的系统凭据库；不可用时仅保留在当前进程。已配置用户可以用 `/connect` 增加连接、`/models` 切换模型。详见 [连接配置](docs/model-connections.md)。

默认会询问是否允许修改文件或调用 Shell。开始前可先做只读检查：

```bash
miniagent --policy readonly --prompt "检查当前项目结构，说明主要入口"
```

自动化可以通过环境变量、JSON 或 CLI 明确配置模型；安装 MCP 使用 `python -m pip install ".[mcp]"`。更多选项运行 `miniagent --help`。

## 一个 Agent 需要的常用能力

| 能力 | MiniAgent 的用法 |
| --- | --- |
| 模型与工具循环 | 多 Provider、原生工具调用、流式文本 |
| 编程工具 | `read`、`write`、`edit`、`grep`、`glob`、`bash` |
| 插件组合 | Context/Service、依赖声明、事件、失败回滚和自动清理 |
| Skills 与 MCP | 切换提示和工具白名单，连接 MCP stdio 服务 |
| 可恢复会话 | JSONL 记录、上下文压缩，不确定副作用先核实再恢复 |
| 终端交互 | 模型连接向导、工具进度、Markdown 回答和会话命令 |

## 也可以写进 Python

```python
import asyncio
from miniagent import Harness
from miniagent.plugins import coding_tools
from miniagent.policy import Policy

async def main():
    async with Harness(model="provider:model-id", policy=Policy(mode="readonly")) as app:
        app.use(coding_tools())
        print(await app.arun("检查项目结构，说明主要入口"))

asyncio.run(main())
```

将 `provider:model-id` 换为你选择的模型，并配置对应凭据。自定义工具、服务和事件通过 `Plugin` 挂载，见 [插件示例与运行指南](docs/lean-harness.md)。

## 小到哪里，做到哪里

当前为 **0.2.0a1 / alpha**。主线基准核心 531 行、全部包源码 5,056 行；本次展示改进保持核心不变。旧教学 API 和兼容工具仍占较大比例，整体精简目标尚未达成。统计口径、DSH 对照、测试证据与后续工作见 [项目状态](docs/project-status.md)。

CLI 输入 `/help` 查看命令；`--session <path>` 恢复会话。Shell、Python 插件和 MCP 服务属于可信代码，工具授权不提供容器沙箱。权限、恢复和旧 API 的边界见 [使用与迁移指南](docs/lean-harness.md)。

## 参与和致谢

欢迎提交可复现的问题、短小插件和真实任务案例。开发约束见 [AGENTS.md](AGENTS.md)，版本变化见 [Changelog](docs/CHANGELOG.md)。

编程工具参考 [nanocode](https://github.com/1rgs/nanocode)，模型适配使用 [any-llm](https://github.com/mozilla-ai/any-llm)，MCP 使用官方 Python SDK。Logo 延续作者 [AlphaEvo](https://github.com/ZhuLinsen/alphaevo) 的终端视觉风格。

[Apache License 2.0](LICENSE)
