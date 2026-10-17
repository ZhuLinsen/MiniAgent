<p align="center">
  <img src="docs/assets/miniagent-banner.svg" width="480" alt="MiniAgent">
</p>

<p align="center"><strong>小型 Python Agent + Harness</strong></p>

<p align="center">
  <a href="https://github.com/ZhuLinsen/MiniAgent/actions/workflows/ci.yml"><img src="https://github.com/ZhuLinsen/MiniAgent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB" alt="Python 3.11+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue" alt="Apache 2.0"></a>
  <img src="https://img.shields.io/badge/status-alpha-ff815c" alt="Alpha">
</p>

<p align="center"><a href="README_EN.md">English</a> · <a href="#快速开始">快速开始</a> · <a href="#演示">演示</a> · <a href="#作为-python-harness-使用">Python API</a> · <a href="#读源码">源码</a></p>

MiniAgent 可以读代码、改文件、运行测试，也可以调用本机程序处理浏览器、文档等任务。在终端里直接使用，或作为 **Harness** 嵌入自己的 Python 项目。核心 **598 行、4 个文件**，[从这里读源码](#读源码)。

## 演示

**修改代码，运行测试** · 修复 calculator.py 的加法函数，不改测试文件。

![MiniAgent 读取文件、修复函数并运行测试的终端回放](docs/assets/coding-replay.gif)

由真实 CLI 记录生成，压缩了播放间隔。[静态图](docs/assets/coding-session.png) · [完整记录与复现](docs/demo.md)

### Windows 自动化

<table>
<tr><th width="50%">打开浏览器并搜索</th><th width="50%">生成 Word 文档</th></tr>
<tr><td align="center">打开浏览器，搜索 MiniAgent 的 GitHub 仓库。</td><td align="center">写一篇 AI Agent 介绍，保存为 Word 文档并排版。</td></tr>
<tr>
<td width="50%"><a href="resource/miniagent_chrome.gif"><img src="resource/miniagent_chrome.gif" width="400" alt="Windows 浏览器搜索演示"></a></td>
<td width="50%"><a href="resource/miniagent_word.gif"><img src="resource/miniagent_word.gif" width="400" alt="Windows Word 文档演示"></a></td>
</tr>
</table>

这两段保留项目原版录屏，点击可看大图。当前版本通过 Shell / Python 或 MCP 完成本机自动化，见 [Windows 案例与环境准备](docs/demo.md#windows-案例)。

## 快速开始

需要 Python 3.11+，建议在虚拟环境中安装。

```bash
git clone https://github.com/ZhuLinsen/MiniAgent.git
cd MiniAgent
python -m pip install -e ".[credentials]"
miniagent
```

第一次启动时，按提示连接模型，然后直接输入任务。默认在修改文件和执行 Shell 前询问是否允许。

也可以从命令行传入任务：

```bash
miniagent --policy readonly --prompt "看看这个项目是做什么的，主要代码和测试在哪里"
```

`/help` 查看命令，`/models` 切换模型，`/skills reviewer` 切换到代码审查角色，`/session` 查看会话。[模型配置](docs/model-connections.md)

## Agent 能做什么

- **写代码**：用 `read`、`write`、`edit`、`grep`、`glob`、`bash` 读写文件、查找代码、执行命令。
- **操作本机**：通过 Shell 调用 Python 和已安装的软件，处理网页、文档和文件；桌面交互可接入自动化脚本或 MCP。
- **接着上次做**：保存和恢复会话，压缩较长的上下文；支持流式回答和切换模型。
- **接入自己的工具**：用 Plugin 注册工具和服务，用 Skills 设置任务提示与工具范围，用 MCP 连接外部工具。

## 作为 Python Harness 使用

在程序里创建一个 Agent，挂上工具，然后交给它任务：

```python
from miniagent import Harness
from miniagent.plugins import coding_tools
from miniagent.policy import Policy

app = Harness(model="provider:model-id", policy=Policy(mode="readonly"))
app.use(coding_tools())
print(app.run("看看项目的目录结构，说明主要入口"))
```

将 `provider:model-id` 换成自己的模型，并配置对应凭据。异步调用使用 `async with app` 和 `await app.arun(...)`。

Harness 负责模型与工具之间的循环、插件启动和清理，以及会话管理。自己的工具、共享服务和事件监听都通过 `Plugin` 接入。[插件与完整示例 →](docs/lean-harness.md)

## 读源码

从这 4 个文件开始，就能看到一次任务的主要执行过程：

| 文件 | 行数 | 做什么 |
| --- | ---: | --- |
| [agent.py](miniagent/agent.py) | 81 | 调用模型 → 执行工具 → 返回结果 |
| [harness.py](miniagent/harness.py) | 314 | 插件、服务、事件和生命周期 |
| [llm.py](miniagent/llm.py) | 149 | 模型接口与流式响应 |
| [registry.py](miniagent/tools/registry.py) | 54 | 工具注册、参数校验与权限检查 |

核心合计 **598 行**；CLI、工具、配置和旧版兼容代码另计。 行数包含注释和空行，不含第三方依赖。运行 `python scripts/source_stats.py` 可复核。[详细统计](docs/project-status.md)

## 文档与贡献

[使用指南](docs/lean-harness.md) · [模型配置](docs/model-connections.md) · [演示说明](docs/demo.md) · [更新记录](docs/CHANGELOG.md)

欢迎提交问题、使用案例和 PR。开发前请阅读 [AGENTS.md](AGENTS.md)。当前为 Alpha 版本；Shell、插件和 MCP 在本机执行，权限确认不等于沙箱隔离。

[Apache License 2.0](LICENSE)
