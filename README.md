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
git clone https://github.com/yourusername/MiniAgent.git
cd MiniAgent

# 安装依赖
pip install -r requirements.txt
```

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

## 创建你自己的Agent

```python
from miniagent import MiniAgent
from miniagent.tools import load_tools, register_tool

# 定义自定义工具（可选）
@register_tool
def calculator(expression: str) -> float:
    """计算数学表达式的结果"""
    return eval(expression)

# 创建Agent, 使用.env中的配置
agent = MiniAgent()

# 加载工具
tools = load_tools(["calculator", "get_current_time"])

# 运行Agent
response = agent.run(
    query="现在几点了？同时计算123 × 456。",
    tools=tools
)

print(response)
```

## 示例

查看`examples/`目录获取更多详细示例：

- `simple_example.py`：与任何LLM的基本用法
- `custom_tools_example.py`：使用自定义工具

## 许可证

[Apache License 2.0](LICENSE)

## Star历史

[![Star History Chart](https://api.star-history.com/svg?repos=ZhuLinsen/MiniAgent&type=Date)](https://www.star-history.com/#ZhuLinsen/MiniAgent&Date)

