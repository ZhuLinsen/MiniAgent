# MiniAgent

🚀 **Build an AI Coding Assistant + CLI-based Manus in 5 Minutes!** | [中文版本](README.md)

<div align="center">
  <img src="resource/miniagent.png" alt="MiniAgent" width="400"/>
</div>

## 💡 Core Features

**400 lines of Python code to replicate Claude Code's coding capabilities + Manus's OS control capabilities!**

MiniAgent is a **minimalist, transparent, and powerful CLI Agent framework** that rejects bloated dependencies and complex architectures:

- 🧠 **Code Agent**: Write code, fix bugs, and run tests like Claude Code.
- 🦾 **OS Agent**: Control browsers, edit documents, and manage apps like Manus.
- ⚡ **Minimalist**: Core logic (`agent.py`) is only ~400 lines. Fully transparent and hackable.
- 🤖 **Model Agnostic**: Perfectly supports DeepSeek, OpenAI, Claude, and any OpenAI-compatible models.
- 🔌 **High Extensibility**: Simple decorator pattern—add custom tools in just 3 lines of code.

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
| | `bash` | Execute Shell commands |
| **OS** | `open_browser` | Open web page or search |
| | `open_app` | Launch local apps (calc, notepad...) |
| | `create_docx` | Create Word documents |
| | `clipboard_copy`| Copy to clipboard |
| **Misc** | `calculator` | Mathematical context |

## License

[Apache License 2.0](LICENSE)

---

⭐ If this project helps you, please give it a Star!
