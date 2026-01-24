# MiniAgent

- 🚀「Build Your First LLM Agent in 5 Minutes!」 |⚡️[中文版本](README.md)

<div align="center">
  <img src="miniagent.png" alt="MiniAgent" width="600"/>
</div>

## Why Choose MiniAgent?

Help beginners quickly understand Agent principles and implement an Agent. Gain intuitive insights into the details of LLM interaction with tools without complex frameworks, tedious configurations, or steep learning curves.

If you find this project helpful, please give us a ⭐️! Your support drives us to keep improving.

## Features

MiniAgent is a lightweight and easy-to-use LLM Agent framework. Here's why you should choose MiniAgent:

- **Rapid Learning**: Quickly learn how LLM agents work and understand the details of LLM interaction with tools
- **Model Agnostic**: Works with any LLM, even without native function calling capability, compatible with OpenAI, DeepSeek, Anthropic, and other LLMs
- **Minimalist Design**: Clean, readable code focused on core functionality
- **Lightweight**: No heavy dependencies, easy to integrate and extend
- **Simple Tool Integration**: Easy tool registration and invocation through natural language

## Quick Start

### Requirements

- Python 3.8+
- A valid API key for any LLM (OpenAI, DeepSeek, etc.)

### Installation

```bash
# Clone repository
git clone https://github.com/ZhuLinsen/MiniAgent.git
cd MiniAgent

# Install dependencies
python -m pip install -r requirements.txt

# (Recommended) install CLI entry points
python -m pip install -e .
```

If you prefer not to install commands, you can run via modules:

```bash
python -m miniagent
python -m miniagent.gui
```

Note: `miniagent` / `miniagent-gui` are installed into the *current Python environment* scripts directory. If you're using conda/venv, activate that environment before running the commands.

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

## CLI Mode (New)

After installation, start the interactive CLI:

```bash
miniagent
```

If you see `miniagent: command not found`, you likely didn't run `python -m pip install -e .` (or your PATH doesn't include the scripts directory). You can also run:

```bash
python -m miniagent
```

Built-in commands: `/help`, `/c`, `/q`.

## Desktop GUI (New)

Tkinter-based (zero extra dependencies):

```bash
miniagent-gui
```

## Code Tools (New)

Added 6 code tools: `read`/`write`/`edit`/`glob`/`grep`/`bash` (see `miniagent/tools/code_tools.py`).

## Creating Your Own Agent

```python
from miniagent import MiniAgent
from miniagent.config import load_config

cfg = load_config()

agent = MiniAgent(
  model=cfg.llm.model,
  api_key=cfg.llm.api_key,
  base_url=cfg.llm.api_base,
  temperature=cfg.llm.temperature,
  system_prompt=cfg.system_prompt,
  use_reflector=cfg.enable_reflection,
)

agent.tools = []
for name in ["calculator", "get_current_time", "read", "write", "grep"]:
  agent.load_builtin_tool(name)

print(agent.run("What's the current time? Also calculate 123 * 456."))
```

## Examples

See the `examples/` directory for more detailed examples:

- `simple_example.py`: Basic usage with any LLM
- `custom_tools_example.py`: Working with custom tools

## License

[Apache License 2.0](LICENSE)

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=ZhuLinsen/MiniAgent&type=Date)](https://www.star-history.com/#ZhuLinsen/MiniAgent&Date) 