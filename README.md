# MiniAgent

🚀 **5分钟手搓一个 AI Coding 助手 + 命令行版 Manus！** | [English](README_EN.md)

<div align="center">
  <img src="resource/miniagent.png" alt="MiniAgent" width="400"/>
</div>

## 💡 核心特性

**仅用 400 行 Python 核心代码，复刻 Claude Code 的编程能力 + Manus 的系统操控能力！**

MiniAgent 是一个**极简、透明、强大的 CLI Agent 框架**，拒绝臃肿的依赖和复杂的架构：

- 🧠 **Code Agent**: 像 Claude Code 一样写代码、修 Bug、跑测试
- 🦾 **OS Agent**: 像 Manus 一样操控浏览器、编辑文档、管理应用
- ⚡ **极简实现**: 核心逻辑 (`agent.py`) 仅 400 行，完全透明可控，适合学习和魔改
- 🤖 **全模型支持**: 完美支持 DeepSeek、OpenAI、Claude 等所有兼容 OpenAI 接口的模型
- 🔌 **高扩展性**: 极简的装饰器模式，3行代码即可挂载自定义工具

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

## 致谢

MiniAgent 的 Code Tools 设计参考了 [nanocode](https://github.com/1rgs/nanocode) 项目，感谢其优雅的极简实现思路！

## 许可证

[Apache License 2.0](LICENSE)

---

⭐ 如果这个项目对你有帮助，请给个 Star！
