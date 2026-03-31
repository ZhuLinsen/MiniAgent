# MiniAgent

🚀 **5分钟手搓一个 AI Coding 助手 + 命令行版 Manus！** | [English](README_EN.md)

<div align="center">
  <img src="resource/miniagent.png" alt="MiniAgent" width="400"/>
</div>

## 💡 核心特性

**仅用 ~400 行 Python 核心函数，复刻 Claude Code 的编程能力 + Manus 的系统操控能力！**

MiniAgent 是一个**极简、透明、强大的 CLI Agent 框架**，拒绝臃肿的依赖和复杂的架构：

- 🧠 **Code Agent**: 像 Claude Code 一样写代码、修 Bug、跑测试
- 🦾 **OS Agent**: 像 Manus 一样操控浏览器、编辑文档、管理应用
- ⚡ **极简实现**: 核心逻辑 (`agent.py`) ~400 行核心函数，完全透明可控，适合学习和魔改
- 🤖 **全模型支持**: 完美支持 DeepSeek、OpenAI、Claude 等所有兼容 OpenAI 接口的模型
- 🔌 **高扩展性**: 极简的装饰器模式，3行代码即可挂载自定义工具
- 🔄 **双模式工具调用**: 文本解析模式（透明可学习）+ 原生 Function Calling 模式（更可靠）

## 设计哲学

> **MiniAgent 不内置 100 个工具，而是用 6 个代码工具 + bash 实现无限可能。**

- 要截图？LLM 会 `bash: python -c "from mss import mss; mss().shot()"`
- 要控制鼠标？LLM 会 `bash: python -c "import pyautogui; pyautogui.click(100,200)"`
- 要爬网页？LLM 会 `bash: curl ... | python -c "..."`

这就是极简的力量：让 LLM 做它最擅长的事 — **思考和组合**。

## 快速开始

### 安装

```bash
git clone https://github.com/ZhuLinsen/MiniAgent.git
cd MiniAgent
pip install -r requirements.txt
pip install -e .  # 安装 miniagent 命令
```

### 配置

创建 `.env` 文件：

```bash
LLM_API_KEY=your_api_key_here
LLM_MODEL=deepseek-chat
LLM_API_BASE=https://api.deepseek.com/v1
```

### 运行

```bash
miniagent          # 或 python -m miniagent
```

## 使用示例

```
you: 帮我创建一个 hello.py 文件
  ● write hello.py (1 lines)
    → ok
🤖 已创建 hello.py 文件！

you: 运行一下
  ● bash python hello.py
    → Hello World!
🤖 运行成功！
```

## ⚡ 演示

### 1. 操控浏览器搜索
> Prompt: "Open the browser, then search for 'zhulinsen/miniagent' on Google."

<img src="resource/miniagent_chrome.gif" alt="Browser Automation Demo" width="100%"/>

### 2. 自动化办公 (Word)
> Prompt: "Write a 500-word overview of AI agents in Word and format"

<img src="resource/miniagent_word.gif" alt="Word Creation Demo" width="100%"/>

### 3. 代码生成 (Coding)
> Prompt: "Create a ppo.py implementation and perform testing"

<img src="resource/miniagent_coding.png" alt="Coding Demo" width="100%"/>

## 内置工具

| 类别 | 工具 | 描述 |
|---|---|---|
| **Coding** | `read` | 读取文件内容 |
| | `write` | 创建/覆盖文件 |
| | `edit` | 编辑文件指定行 |
| | `grep` | 搜索文件内容 |
| | `glob` | 列出匹配的文件 |
| | `bash` | 执行 Shell 命令（支持超时控制） |
| **OS** | `open_browser` | 打开网页或搜索 |
| | `open_app` | 启动本地应用 (calc, notepad...) |
| | `create_docx` | 创建 Word 文档 |
| | `clipboard_copy`| 复制到剪贴板 |
| | `clipboard_read`| 读取剪贴板内容 |
| **System** | `system_info` | 系统信息 |
| | `system_load` | CPU/内存/磁盘负载 |
| | `process_list` | 进程列表 |
| | `disk_usage` | 磁盘使用情况 |
| **Misc** | `calculator` | 数学计算（AST 安全求值） |
| | `get_current_time` | 当前时间 |
| | `web_search` | 网页搜索 |
| | `http_request` | HTTP 请求 |

## 项目结构

```
miniagent/
├── agent.py      # 核心 Agent（~400行核心函数）
├── cli.py        # 命令行界面
├── config.py     # 配置管理
├── memory.py     # 会话记忆
├── tools/        # 工具集
│   ├── code_tools.py   # 代码工具 (read/write/edit/grep/glob/bash)
│   └── basic_tools.py  # 基础工具 (calculator/browser/clipboard/docx...)
└── utils/        # 工具函数
```

## 双模式工具调用

MiniAgent 支持两种工具调用模式，便于学习和对比：

### 文本模式（默认）
LLM 在响应中输出结构化文本，Agent 解析执行 — **完全透明，最佳教学模式**：
```python
agent.run("计算 2+2")  # 默认文本模式
```

### 原生 Function Calling 模式
使用 OpenAI 兼容的 tools 参数 — **更可靠，支持并行工具调用**：
```python
agent.run("计算 2+2", mode="native")  # 原生 FC 模式
```

## 自定义工具

```python
from miniagent import MiniAgent
from miniagent.tools import register_tool

@register_tool
def my_tool(arg: str) -> str:
    """我的自定义工具"""
    return f"处理: {arg}"

agent = MiniAgent(...)
agent.load_builtin_tool("my_tool")
```

## 与同类项目对比

| 特点 | MiniAgent | nanocode | LangChain |
|------|-----------|---------|-----------|
| 核心代码 | ~400行核心函数 | ~271行单文件 | 10万+行 |
| 工具调用 | 文本解析 + 原生FC 双模式 | 仅原生FC | 多层抽象 |
| 可读性 | ⭐⭐⭐⭐⭐ 初学者友好 | ⭐⭐⭐⭐ 紧凑 | ⭐⭐ 复杂 |
| OS 控制 | bash 万能 + 专用工具 | 仅 bash | 需插件 |
| 教学价值 | 最好的 Agent 教科书 | 过于紧凑 | 过于复杂 |
| 模型支持 | 全模型兼容 | Claude 为主 | 全模型 |

## 致谢

MiniAgent 的 Code Tools 设计参考了 [nanocode](https://github.com/1rgs/nanocode) 项目，感谢其优雅的极简实现思路！

## 许可证

[Apache License 2.0](LICENSE)

---

⭐ 如果这个项目对你有帮助，请给个 Star！
