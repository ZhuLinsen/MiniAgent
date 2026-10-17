<p align="center">
  <img src="docs/assets/miniagent-banner.svg" width="800" alt="MiniAgent — 极简 Python Agent + Harness">
</p>

<p align="center"><strong>极简 Python Agent + Harness。</strong><br>几百行核心代码。读得懂，改得动，终端里直接用。</p>

<p align="center">
  <a href="https://github.com/ZhuLinsen/MiniAgent/actions/workflows/ci.yml"><img src="https://github.com/ZhuLinsen/MiniAgent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB" alt="Python 3.11+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue" alt="Apache 2.0"></a>
  <img src="https://img.shields.io/badge/status-alpha-ff815c" alt="Alpha">
</p>

<p align="center"><a href="README_EN.md">English</a> · <a href="#快速开始">快速开始</a> · <a href="#搭建自己的-agent">Python API</a> · <a href="#读懂核心">读源码</a></p>

**598 行核心代码，一个能读代码、改文件、跑测试的 Agent。** MiniAgent 既是开箱可用的终端编程助手，也是可以嵌入 Python 的小型 Harness：模型、工具、插件和会话，由你组合。

## 为什么选择 MiniAgent？

- **小而透明**：核心只有 4 个 Python 文件，模型调用、工具循环和插件生命周期都能顺着源码读懂。
- **拿来就用**：6 个编程工具、多轮对话、流式回答、会话恢复，覆盖日常代码阅读、修改和验证。
- **容易扩展**：用插件挂载工具和服务，用 Skills 定制任务，用 MCP 接入外部能力，搭出自己的 Agent。

## 快速开始

需要 **Python 3.11+**，在虚拟环境中从源码安装：

```bash
git clone https://github.com/ZhuLinsen/MiniAgent.git
cd MiniAgent
python -m pip install -e ".[credentials]"
miniagent
```

首次启动按提示选择模型、输入密钥，即可开始。之后可用 `/connect` 配置连接、`/models` 切换模型；环境变量与自定义接口见 [模型配置](docs/model-connections.md)。

先让它看看你的项目：

```bash
miniagent --policy readonly --prompt "阅读项目结构，找出主要入口和测试命令"
```

## 直接当编程 Agent 用

| 能力 | 你可以用它做什么 |
| --- | --- |
| 六个编程工具 | `read` / `grep` / `glob` 找代码，`write` / `edit` 改文件，`bash` 跑命令和测试 |
| 多轮执行 | 模型调用工具、读取结果、继续处理任务；支持流式回答和工具进度 |
| 会话恢复 | 保存对话与工具记录，用 `--session <path>` 接着处理；长对话自动压缩上下文 |
| Skills 与 MCP | 切换任务提示和工具范围，连接自己的 MCP 工具服务 |

默认在修改文件或执行 Shell 前询问。输入 `/help` 查看命令，`/skills reviewer` 切换到代码审查角色，`/session` 查看当前会话。

<details>
<summary>看一次实际运行：读代码 → 修复函数 → 跑测试</summary>

![MiniAgent 读取代码、修改函数并运行测试](docs/assets/coding-session.png)

[完整记录与复现步骤](docs/demo.md)

</details>

## 搭建自己的 Agent

Harness 管理模型调用、工具执行和插件生命周期。把它当作普通 Python 库，在脚本或应用里组合：

```python
from miniagent import Harness
from miniagent.plugins import coding_tools
from miniagent.policy import Policy

app = Harness(model="provider:model-id", policy=Policy(mode="readonly"))
app.use(coding_tools())
print(app.run("阅读项目结构，说明主要入口"))
```

将 `provider:model-id` 换为你的模型，并配置对应凭据；也可通过 `load_config()` 复用 CLI 的连接配置。已有异步应用中使用 `async with app` 和 `await app.arun(...)`。

用 `Plugin` 组合自己的能力：

| 插件入口 | 用途 |
| --- | --- |
| `ctx.tool(...)` | 挂载自定义工具，复用参数校验、权限和 Skill 限制 |
| `ctx.service(...)` | 提供供其他插件使用的服务 |
| `ctx.on(...)` | 订阅模型与工具事件，接入进度展示或日志 |
| `ctx.cleanup(...)` | 注册退出与失败时的资源清理 |

插件支持依赖顺序、失败回滚和逆序清理。自定义工具、MCP、Skills 与持久会话示例见 [使用指南](docs/lean-harness.md)。

## 读懂核心

从这 4 个文件开始：

| 文件 | 职责 |
| --- | --- |
| [agent.py](miniagent/agent.py) | 模型 → 工具 → 模型的任务循环 |
| [harness.py](miniagent/harness.py) | 插件、服务、事件与生命周期 |
| [llm.py](miniagent/llm.py) | 模型调用与流式响应 |
| [registry.py](miniagent/tools/registry.py) | 工具注册、参数校验与授权入口 |

四文件核心合计 **598 行**；CLI、工具、配置与旧版兼容代码另计。 统计包含注释和空行，不含第三方依赖；运行 `python scripts/source_stats.py` 可复核，完整口径见 [代码量说明](docs/project-status.md)。

## 文档

[使用指南](docs/lean-harness.md) · [模型配置](docs/model-connections.md) · [版本变化](docs/CHANGELOG.md) · [开发约束](AGENTS.md)

当前为 Alpha。Shell、插件和 MCP 服务是可信代码，工具授权不提供容器沙箱。

[Apache License 2.0](LICENSE)
