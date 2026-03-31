# MiniAgent

🚀 **Build an AI Coding Assistant + CLI-based Manus in 5 Minutes!** | [中文版本](README.md)

<div align="center">
  <img src="resource/miniagent.png" alt="MiniAgent" width="400"/>
</div>

## 💡 Core Features

**~400 lines of core Python functions to replicate Claude Code's coding capabilities + Manus's OS control capabilities!**

MiniAgent is a **minimalist, transparent, and powerful CLI Agent framework** that rejects bloated dependencies and complex architectures:

- 🧠 **Code Agent**: Write code, fix bugs, and run tests like Claude Code.
- 🦾 **OS Agent**: Control browsers, edit documents, and manage apps like Manus.
- ⚡ **Minimalist**: Core logic (`agent.py`) is ~400 lines of core functions. Fully transparent and hackable.
- 🤖 **Model Agnostic**: Perfectly supports DeepSeek, OpenAI, Claude, and any OpenAI-compatible models.
- 🔌 **High Extensibility**: Simple decorator pattern—add custom tools in just 3 lines of code.
- 🔄 **Dual Tool Calling**: Text parsing mode (transparent, educational) + Native Function Calling mode (reliable).
- 🛡️ **Safety Guards**: Auto-detect and confirm dangerous commands before execution.
- 💬 **Streaming Output**: Real-time token-by-token output with auto context compression.
- 🔗 **MCP Protocol**: Connect to MCP tool servers to access the community ecosystem.
- 🤝 **Multi-Agent**: Built-in orchestrator for task decomposition and role-based collaboration.

## Design Philosophy

> **MiniAgent doesn't ship 100 built-in tools. Instead, it uses 6 code tools + bash to achieve unlimited capabilities.**

- Need a screenshot? The LLM will `bash: python -c "from mss import mss; mss().shot()"`
- Need mouse control? The LLM will `bash: python -c "import pyautogui; pyautogui.click(100,200)"`
- Need web scraping? The LLM will `bash: curl ... | python -c "..."`

That's the power of minimalism: let the LLM do what it does best — **think and compose**.

## ⚡ Examples

### 1. Browser Automation
> Prompt: "Open the browser, then search for 'zhulinsen/miniagent' on Google."

<img src="resource/miniagent_chrome.gif" alt="Browser Automation Demo" width="100%"/>

### 2. Office Automation (Word)
> Prompt: "Write a 500-word overview of AI agents in Word and format"

<img src="resource/miniagent_word.gif" alt="Word Creation Demo" width="100%"/>

### 3. Code Generation
> Prompt: "Create a ppo.py implementation and perform testing"

<img src="resource/miniagent_coding.png" alt="Coding Demo" width="100%"/>

## Quick Start

### Installation

```bash
git clone https://github.com/ZhuLinsen/MiniAgent.git
cd MiniAgent
pip install -r requirements.txt
pip install -e .  # Install miniagent command
```

### Configuration

Create a `.env` file:

```bash
LLM_API_KEY=your_api_key_here
LLM_MODEL=deepseek-chat
LLM_API_BASE=https://api.deepseek.com/v1
```

### Run

```bash
miniagent          # or python -m miniagent
```

## Built-in Tools

| Category | Tool | Description |
|---|---|---|
| **Coding** | `read` | Read file content |
| | `write` | Create/Overwrite file |
| | `edit` | Edit specific lines in file |
| | `grep` | Search file content |
| | `glob` | List matching files |
| | `bash` | Execute Shell commands (with timeout) |
| **OS** | `open_browser` | Open web page or search |
| | `open_app` | Launch local apps (calc, notepad...) |
| | `create_docx` | Create Word documents |
| | `clipboard_copy`| Copy to clipboard |
| | `clipboard_read`| Read clipboard content |
| **System** | `system_info` | System information |
| | `system_load` | CPU/memory/disk load |
| | `process_list` | Process listing |
| **Misc** | `calculator` | Math (AST-safe evaluation) |
| | `get_current_time` | Current time |

## Dual Tool Calling Modes

MiniAgent supports two tool calling modes for learning and comparison:

### Text Mode (Default)
The LLM outputs structured text in its response, and the Agent parses it — **fully transparent, best for learning**:
```python
agent.run("Calculate 2+2")  # default text mode
```

### Native Function Calling Mode
Uses OpenAI-compatible `tools` parameter — **more reliable, supports parallel tool calls**:
```python
agent.run("Calculate 2+2", mode="native")  # native FC mode
```

## Comparison with Similar Projects

| Feature | MiniAgent | nanocode | LangChain |
|---------|-----------|---------|-----------|
| Core Code | ~400 line functions | ~271 line single file | 100K+ lines |
| Tool Calling | Text + Native FC dual mode | Native FC only | Multi-layer abstraction |
| Readability | ⭐⭐⭐⭐⭐ Beginner-friendly | ⭐⭐⭐⭐ Compact | ⭐⭐ Complex |
| OS Control | Universal bash + dedicated tools | bash only | Needs plugins |
| Learning Value | Best Agent textbook | Too compact | Too complex |

## License

[Apache License 2.0](LICENSE)

---

⭐ If this project helps you, please give it a Star!
