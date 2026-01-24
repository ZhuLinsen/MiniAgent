# MiniAgent

- 🚀「5分钟从零实现LLM Agent！」 |⚡️[English Version](README_EN.md)

<div align="center">
  <img src="miniagent.png" alt="MiniAgent" width="600"/>
</div>

## 为什么选择MiniAgent？


帮助初学者，快速理解Agent原理并实现一个Agent，直观了解LLM与工具交互的细节。

如果这个项目对你有帮助，请给我们一个⭐️！你的支持是我们持续改进的动力。


## 特色功能

MiniAgent是一个轻量级且易于使用的LLM Agent框架。以下是选择MiniAgent的理由：

- **快速学习**：快速学习LLM Agent工作原理,直观了解LLM与工具交互的细节
- **模型无关**：适用于任何LLM，即使没有原生函数调用能力，兼容OpenAI、DeepSeek、Anthropic等LLM
- **极简设计**：专注于核心功能的清晰、可读代码
- **轻量级**：无重依赖，易于集成和扩展
- **简单工具集成**：通过自然语言轻松注册和调用工具

## 快速开始

### 环境要求

- Python 3.8+
- 任何LLM的有效API密钥（OpenAI、DeepSeek等）

### 安装

```bash
# 克隆仓库
git clone https://github.com/ZhuLinsen/MiniAgent.git
cd MiniAgent

# 安装依赖
python -m pip install -r requirements.txt

# （推荐）把 miniagent/miniagent-gui 安装为命令
python -m pip install -e .
```

如果你不想安装命令，也可以直接用模块方式运行：

```bash
python -m miniagent
python -m miniagent.gui
```

注意：`miniagent` / `miniagent-gui` 会安装到“当前 Python 环境”的脚本目录里；如果你在用 conda/venv，请先激活对应环境后再运行命令。

### 配置

从`.env.example`文件创建项目根目录下的`.env`文件：

```bash
# API密钥
LLM_API_KEY=your_api_key_here

# 模型配置
LLM_MODEL=deepseek-chat
LLM_API_BASE=https://api.deepseek.com/v1
LLM_TEMPERATURE=0.7
```

### 验证LLM连接

在使用MiniAgent之前，请验证您的LLM设置：

```bash
# 快速验证
python validate_llm.py
```

### 基础示例

运行一个简单示例：

```bash
python examples/simple_example.py
```

## CLI 模式（新增）

安装后可直接运行交互式 CLI：

```bash
miniagent
```

如果提示 `miniagent: command not found`，说明还没执行 `python -m pip install -e .`（或当前环境的 PATH 未包含脚本目录）；你也可以用：

```bash
python -m miniagent
```

内置命令：`/help`、`/c`、`/q`。

## Desktop GUI（新增）

使用 Tkinter（零额外依赖）：

```bash
miniagent-gui
```

## 代码工具（新增）

新增 6 个 code tools：`read`/`write`/`edit`/`glob`/`grep`/`bash`（见 `miniagent/tools/code_tools.py`）。

## 创建你自己的Agent

```python
import os

from miniagent import MiniAgent
from miniagent.config import load_config

# 读取环境变量 / 配置文件（默认会从环境变量读取）
cfg = load_config()

agent = MiniAgent(
  model=cfg.llm.model,
  api_key=cfg.llm.api_key,
  base_url=cfg.llm.api_base,
  temperature=cfg.llm.temperature,
  system_prompt=cfg.system_prompt,
  use_reflector=cfg.enable_reflection,
)

# 加载内置工具（按需）
agent.tools = []
for name in ["calculator", "get_current_time", "read", "write", "grep"]:
  agent.load_builtin_tool(name)

print(agent.run("现在几点了？同时计算 123 * 456。"))
```

## 示例

查看`examples/`目录获取更多详细示例：

- `simple_example.py`：与任何LLM的基本用法
- `custom_tools_example.py`：使用自定义工具

## 许可证

[Apache License 2.0](LICENSE)

## Star历史

[![Star History Chart](https://api.star-history.com/svg?repos=ZhuLinsen/MiniAgent&type=Date)](https://www.star-history.com/#ZhuLinsen/MiniAgent&Date)

