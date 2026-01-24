# MiniAgent

🚀 **5分钟手搓一个 AI Coding 助手 + 命令行版 Manus！** | [English](README_EN.md)

<div align="center">
  <img src="resouce/miniagent_word.gif" alt="Word Creation Demo" width="600"/>
  <img src="resouce/miniagent_chrome.gif" alt="Browser Automation Demo" width="600"/>
</div>

## 为什么选择 MiniAgent？

**仅用 400 行 Python 代码，复刻 Claude Code 的编程能力 + Manus 的系统操控能力！**

MiniAgent 是一个**极简的 CLI Agent 框架**，它证明了强大的 Agent 不需要复杂的架构：

- 🧠 **Code Agent**: 像 Claude Code 一样写代码、修 Bug、跑测试
- 🦾 **OS Agent**: 像 Manus 一样操控浏览器、编辑文档、管理应用
- ⚡ **极简实现**: 核心逻辑仅单文件，零黑盒，完全透明可控

别再当工具的使用者，成为工具的创造者。

MiniAgent 具备以下核心特性：

- 🖥️ **CLI 交互**：像 Claude Code 一样的终端体验，支持流式输出与思考过程展示
- 🛠️ **Code Tools**：文件读写、代码搜索、Shell 命令执行，轻松搞定编程任务
- 🦾 **OS 能力**：**命令行版 Manus**（低配但核心），支持**打开浏览器搜索、启动 App、操作 Word/剪贴板**
- 🧠 **模型无关**：支持 DeepSeek、OpenAI、Claude 等任意 LLM
- ⚡ **极简依赖**：无重框架，纯 Python 实现，零黑盒

## 特色功能

- **极简核心**：`agent.py` 仅 ~400 行，适合学习和魔改
- **Claude Code 风格**：清爽的终端输出，实时显示思考过程
- **强大工具集**：
  - **Coding**: `read`/`write`/`edit`/`grep`/`glob`/`bash`
  - **OS Ops**: `browser_search`/`open_app`/`create_docx`/`clipboard` 
- **完全开源**：零黑盒，所有代码透明可控

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

## 内置工具

| 类别 | 工具 | 描述 |
|---|---|---|
| **Coding** | `read` | 读取文件内容 |
| | `write` | 创建/覆盖文件 |
| | `edit` | 编辑文件指定行 |
| | `grep` | 搜索文件内容 |
| | `glob` | 列出匹配的文件 |
| | `bash` | 执行 Shell 命令 |
| **OS** | `open_browser` | 打开网页或搜索 |
| | `open_app` | 启动本地应用 (calc, notepad...) |
| | `create_docx` | 创建 Word 文档 |
| | `clipboard_copy`| 复制到剪贴板 |
| **Misc** | `calculator` | 数学计算 |

## 项目结构

```
miniagent/
├── agent.py      # 核心 Agent (~400行)
├── cli.py        # 命令行界面
├── config.py     # 配置管理
├── tools/        # 工具集
│   ├── code_tools.py   # 代码工具
│   └── basic_tools.py  # 基础工具
└── utils/        # 工具函数
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

## 许可证

[Apache License 2.0](LICENSE)

---

⭐ 如果这个项目对你有帮助，请给个 Star！
