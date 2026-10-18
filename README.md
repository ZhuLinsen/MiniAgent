<p align="center">
  <img src="docs/assets/miniagent-banner.svg" width="480" alt="MiniAgent">
</p>

<p align="center"><strong>🚀 五分钟上手 Harness / Agent，打造自己的命令行 Manus。</strong></p>

<p align="center">
  <a href="https://github.com/ZhuLinsen/MiniAgent/actions/workflows/ci.yml"><img src="https://github.com/ZhuLinsen/MiniAgent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB" alt="Python 3.11+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue" alt="Apache 2.0"></a>
  <img src="https://img.shields.io/badge/status-alpha-ff815c" alt="Alpha">
</p>

<p align="center"><a href="README_EN.md">English</a> · <a href="#核心特性">核心特性</a> · <a href="#快速开始">快速开始</a> · <a href="#作为-python-调用">Python API</a> · <a href="#演示">演示</a> · <a href="#项目结构">项目结构</a></p>

MiniAgent 是一个**超轻量、常用功能齐备的 Python Agent / Harness**，核心仅 **591 行代码**。支持工具调用、会话记忆、上下文管理与插件扩展等主流 Agent 常用能力，**可以直接使用，也适合快速入门学习、定制修改和二次开发。**

## 核心特性

- 🧠 **功能齐备**：原生工具调用、流式输出、会话记忆、上下文压缩、Skills、MCP、插件管理与权限控制，组成可运行的 Agent / Harness。
- 🚀 **直接使用**：连接模型后即可通过 CLI 执行编程与自动化任务，也能通过 Python API 嵌入现有项目。
- 📖 **快速入门**：核心仅 **591 行、4 个文件**，从模型调用、工具执行到插件管理，适合通过阅读和运行源码理解 Agent / Harness 的工作原理。
- 🧩 **定制开发**：修改提示词与 Skills，通过 Plugin 接入自己的工具和服务；复用已有的会话与权限机制，开发自己的 Agent。

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

## 作为 Python 调用

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

## 演示

**修改代码，运行测试** · 修复 calculator.py 的加法函数，不改测试文件。

![MiniAgent 读取文件、修复函数并运行测试的终端回放](docs/assets/coding-replay.gif)

由真实 CLI 记录生成，压缩了播放间隔；终端样式来自展示分支。[静态图](docs/assets/coding-session.png) · [完整记录与复现](docs/demo.md)

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

## 项目结构

核心集中在 [agent.py](miniagent/agent.py)、[harness.py](miniagent/harness.py)、[llm.py](miniagent/llm.py) 和 [tools/registry.py](miniagent/tools/registry.py)，会话、Skills 与 MCP 各自独立。

```text
miniagent/
├── agent.py          # Agent 循环 · 65 行
├── harness.py        # 插件、服务与生命周期 · 256 行
├── llm.py            # 模型调用与流式输出 · 149 行
├── tools/
│   ├── registry.py   # 工具注册与执行检查 · 54 行
│   └── code_tools.py # 文件与代码工具
├── plugins.py       # 内置工具与 Shell 插件
├── session.py       # 会话持久化与上下文压缩
├── skills.py        # Skills 加载与配置
├── policy.py        # 执行权限与文件访问检查
├── extensions/      # MCP 接入
└── cli.py           # 命令行入口
```

四文件核心 **591 行**；全部官方包 Python **2,135 行**。行数包含注释和空行，不含第三方依赖。运行 `python scripts/source_stats.py` 可复核。[统计脚本](scripts/source_stats.py)

## 文档与贡献

[使用指南](docs/lean-harness.md) · [模型配置](docs/model-connections.md) · [演示说明](docs/demo.md) · [更新记录](docs/CHANGELOG.md) · [旧版迁移](docs/legacy-migration.md)

欢迎提交问题、使用案例和 PR。开发前请阅读 [AGENTS.md](AGENTS.md)。当前为 Alpha 版本；Shell、插件和 MCP 在本机执行，权限确认不等于沙箱隔离。

[Apache License 2.0](LICENSE)
