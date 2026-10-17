<p align="center">
  <img src="docs/assets/miniagent-banner.svg" width="800" alt="MiniAgent">
</p>

<p align="center"><strong>Python Agent + Harness. A 598-line core.</strong></p>

<p align="center">
  <a href="https://github.com/ZhuLinsen/MiniAgent/actions/workflows/ci.yml"><img src="https://github.com/ZhuLinsen/MiniAgent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB" alt="Python 3.11+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue" alt="Apache 2.0"></a>
  <img src="https://img.shields.io/badge/status-alpha-ff815c" alt="Alpha">
</p>

<p align="center"><a href="README.md">中文</a> · <a href="#quick-start">Quick start</a> · <a href="#demos">Demos</a> · <a href="#python-api">Python API</a></p>

MiniAgent is a Python agent for reading and editing code, running tests and using local programs through Shell. It can also work on browser, document and file-management tasks.

Use it from the terminal, or embed its Harness in Python to manage models, tools, plugins and sessions. The core is 598 lines, with the model calls, tool loop and plugin lifecycle available to read and change.

## Features

- **Code and files**: six tools — `read`, `write`, `edit`, `grep`, `glob`, `bash` — for inspecting code, changing files and running commands.
- **Local automation**: run Python scripts or installed programs through Shell to open pages, generate documents and organize files. Desktop operations can use additional scripts or MCP servers.
- **Models and sessions**: model connections, streamed answers, saved sessions, resume and context compaction.
- **Plugins**: register tools and shared services, subscribe to model/tool events, and manage resource setup and cleanup.
- **Skills / MCP**: switch task instructions and tool access, and connect external MCP tools.

## Quick start

Requires Python 3.11+. Install in a virtual environment:

```bash
git clone https://github.com/ZhuLinsen/MiniAgent.git
cd MiniAgent
python -m pip install -e ".[credentials]"
miniagent
```

The first launch guides you through model and credential setup. Then enter a task. File changes and Shell calls require confirmation by default.

Start with a read-only inspection:

```bash
miniagent --policy readonly --prompt "Explain this project and find its main code and tests"
```

Use `/help` for commands, `/models` to switch models, `/skills reviewer` for code review and `/session` for the current session. See [model setup](docs/model-connections.md) for environment variables and custom endpoints.

## Demos

### Windows: browser search

> Open the browser, then search for the MiniAgent GitHub repository on Google.

<img src="resource/miniagent_chrome.gif" alt="Windows browser automation demo" width="100%"/>

### Windows: create a Word document

> Write a 500-word overview of AI agents in Word and format it.

<img src="resource/miniagent_word.gif" alt="Windows Word automation demo" width="100%"/>

These two recordings are from the original Windows version. The current version uses Shell / Python or MCP for local automation; see [Windows setup and dependencies](docs/demo.md#windows-案例).

### Edit code and run tests

> Fix the addition function in calculator.py, leave the test file unchanged, then run the tests.

![MiniAgent editing a function and running tests](docs/assets/coding-session.png)

[Full recording and reproduction steps](docs/demo.md)

## Python API

Call Harness directly without the terminal interface:

```python
from miniagent import Harness
from miniagent.plugins import coding_tools
from miniagent.policy import Policy

app = Harness(model="provider:model-id", policy=Policy(mode="readonly"))
app.use(coding_tools())
print(app.run("Read the project structure and explain its entry points"))
```

Replace `provider:model-id` with your model and configure its credential. In an async application, use `async with app` and `await app.arun(...)`.

Use `Plugin` to register tools, services, events and cleanup callbacks. Plugins start in dependency order, roll back failed startup and clean up in reverse order. See [Harness and plugins](docs/lean-harness.md).

## Source

The core lives in 4 files:

| File | Contents |
| --- | --- |
| [agent.py](miniagent/agent.py) | Agent loop: call the model, execute tools and return results |
| [harness.py](miniagent/harness.py) | Plugins, services, events and lifecycles |
| [llm.py](miniagent/llm.py) | Model calls and streamed responses |
| [registry.py](miniagent/tools/registry.py) | Tool registration, argument validation and authorization |

The core totals **598 lines**. CLI, tools, configuration and legacy compatibility code are counted separately. Counts include comments and blank lines and exclude third-party dependencies. Run `python scripts/source_stats.py` to verify. [Counting details](docs/project-status.md)

## Docs and contributing

[Guide](docs/lean-harness.md) · [Model setup](docs/model-connections.md) · [Demo notes](docs/demo.md) · [Changelog](docs/CHANGELOG.md)

Issues, task examples and pull requests are welcome. Read [AGENTS.md](AGENTS.md) before contributing. Currently Alpha. Shell, plugins and MCP servers can operate on the host; permission prompts do not provide sandbox isolation.

[Apache License 2.0](LICENSE)
