# MiniAgent

- 🚀「5分钟从零实现LLM Agent！」 ⚡️ Build an LLM agent from scratch in 5 minutes!

## Features

MiniAgent is designed to be a lightweight and easy-to-use framework for building LLM agents. Here's why you should choose MiniAgent:

- **Rapid Learning**: Perfect entry point for learning how LLM agents work
- **Model Agnostic**: Works with any LLM, even without function calling support
- **Minimalist Design**: Clean, readable code focused on core functionality
- **Lightweight**: No heavy dependencies, easy to integrate and extend

Key features include:

- **Multiple LLM Support**: Compatible with OpenAI, DeepSeek, Anthropic, and other LLMs
- **Simple Tool Integration**: Easy tool registration and invocation through natural language
- **No Function Calling Required**: Works with any LLM, even without native function calling capability
- **Response Reflection**: Optional mechanism to improve answer quality and reasoning
- **Environment-based Config**: Simple configuration via environment variables or dotfiles
- **Fast Learning Curve**: Perfect for learning LLM agent concepts and implementation
- **LLM Validation Tool**: Built-in script to verify API connections and capabilities

## Quick Start

### Requirements

- Python 3.8+
- A valid API key for any LLM (OpenAI, DeepSeek, etc.)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/MiniAgent.git
cd MiniAgent

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root from the `.env.example` file:

```bash
# API Keys
LLM_API_KEY=your_api_key_here

# Model Configuration
LLM_MODEL=deepseek-chat
LLM_API_BASE=https://api.deepseek.com/v1
LLM_TEMPERATURE=0.7
```

### Verify LLM Connection

Before using MiniAgent, verify your LLM setup:

```bash
# Quick validation
python validate_llm.py
```

### Basic Example

Run a simple example:

```bash
python examples/simple_example.py
```

## Creating Your Own Agent

```python
from miniagent import MiniAgent
from miniagent.tools import load_tools, register_tool

# Define custom tool (optional)
@register_tool
def calculator(expression: str) -> float:
    """Calculate the result of a mathematical expression"""
    return eval(expression)

# Create Agent
agent = MiniAgent(llm_config={
    "model": "gpt-3.5-turbo",  # Use any supported model
    "api_key": "your_api_key",
    "temperature": 0.7
})

# Load tools
tools = load_tools(["calculator", "web_search", "get_current_time"])

# Run Agent
response = agent.run(
    query="What's the current time? Also calculate 123 × 456.",
    tools=tools
)

print(response)
```

## Examples

See the `examples/` directory for more detailed examples:

- `simple_example.py`: Basic usage with any LLM
- `custom_tools_example.py`: Working with custom tools

## License

[Apache License 2.0](LICENSE)

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=ZhuLinsen/MiniAgent&type=Date)](https://www.star-history.com/#ZhuLinsen/MiniAgent&Date)
