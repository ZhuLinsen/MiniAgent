<p align="center">
  <img src="docs/assets/miniagent-banner.svg" width="480" alt="MiniAgent">
</p>

<p align="center"><strong>A small Python Agent + Harness</strong></p>

<p align="center">
  <a href="https://github.com/ZhuLinsen/MiniAgent/actions/workflows/ci.yml"><img src="https://github.com/ZhuLinsen/MiniAgent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB" alt="Python 3.11+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue" alt="Apache 2.0"></a>
  <img src="https://img.shields.io/badge/status-alpha-ff815c" alt="Alpha">
</p>

<p align="center"><a href="README.md">中文</a> · <a href="#quick-start">Quick start</a> · <a href="#demos">Demos</a> · <a href="#use-it-as-a-python-harness">Python API</a> · <a href="#read-the-source">Source</a></p>

MiniAgent reads code, edits files, runs tests and calls local programs for browser and document tasks. Use it in your terminal, or embed its **Harness** in your own Python project. The core is **591 lines across 4 files**. [Read the source](#read-the-source).

## Demos

**Edit code and run tests** · Fix calculator.py while leaving the tests unchanged.

![Terminal replay of MiniAgent reading files, fixing a function and running tests](docs/assets/coding-replay.gif)

Rendered from a real CLI recording with condensed playback timing. [Still image](docs/assets/coding-session.png) · [Full recording and reproduction](docs/demo.md)

### Windows automation

<table>
<tr><th width="50%">Open a browser and search</th><th width="50%">Create a Word document</th></tr>
<tr><td align="center">Open a browser and search for the MiniAgent GitHub repository.</td><td align="center">Write an overview of AI agents, save it as a Word document and format it.</td></tr>
<tr>
<td width="50%"><a href="resource/miniagent_chrome.gif"><img src="resource/miniagent_chrome.gif" width="400" alt="Windows browser search demo"></a></td>
<td width="50%"><a href="resource/miniagent_word.gif"><img src="resource/miniagent_word.gif" width="400" alt="Windows Word document demo"></a></td>
</tr>
</table>

These recordings are from the original version; click either to enlarge. The current version uses Shell / Python or MCP for local automation. See [Windows examples and setup](docs/demo.md#windows-案例).

## Quick start

Requires Python 3.11+. A virtual environment is recommended.

```bash
git clone https://github.com/ZhuLinsen/MiniAgent.git
cd MiniAgent
python -m pip install -e ".[credentials]"
miniagent
```

The first launch guides you through connecting a model. Then enter a task. File changes and Shell calls require confirmation by default.

You can also pass a task on the command line:

```bash
miniagent --policy readonly --prompt "Explain this project and find its main code and tests"
```

Use `/help` for commands, `/models` to switch models, `/skills reviewer` for code review and `/session` to inspect the session. [Model setup](docs/model-connections.md)

## What the agent can do

- **Work on code**: `read`, `write`, `edit`, `grep`, `glob` and `bash` cover file operations, code search and command execution.
- **Use local programs**: call Python and installed software through Shell for web, document and file tasks. Desktop interactions can use automation scripts or MCP.
- **Continue earlier work**: save and resume sessions, compact longer context, stream answers and switch models.
- **Use your tools**: register tools and services with Plugin, set task instructions and tool access with Skills, and connect external tools through MCP.

## Use it as a Python Harness

Create an agent, attach its tools and give it a task:

```python
from miniagent import Harness
from miniagent.plugins import coding_tools
from miniagent.policy import Policy

app = Harness(model="provider:model-id", policy=Policy(mode="readonly"))
app.use(coding_tools())
print(app.run("Read the project structure and explain its entry points"))
```

Replace `provider:model-id` with your model and configure its credential. For async use, call `await app.arun(...)` inside `async with app`.

Harness manages the model/tool loop, plugin setup and cleanup, and sessions. Register your tools, shared services and event listeners through `Plugin`. [Plugins and complete examples →](docs/lean-harness.md)

## Read the source

These 4 files cover the main execution path:

| File | Lines | Responsibility |
| --- | ---: | --- |
| [agent.py](miniagent/agent.py) | 74 | Call the model → execute tools → return results |
| [harness.py](miniagent/harness.py) | 314 | Plugins, services, events and lifecycles |
| [llm.py](miniagent/llm.py) | 149 | Model interface and streamed responses |
| [registry.py](miniagent/tools/registry.py) | 54 | Tool registration, validation and authorization |

The core totals **591 lines**; all first-party package Python totals **2,122 lines**. Counts include comments and blank lines and exclude third-party dependencies. Run `python scripts/source_stats.py` to verify. [Detailed counts](docs/project-status.md)

## Docs and contributing

[Guide](docs/lean-harness.md) · [Model setup](docs/model-connections.md) · [Demo notes](docs/demo.md) · [Changelog](docs/CHANGELOG.md) · [Legacy migration](docs/legacy-migration.md)

Issues, task examples and pull requests are welcome. Read [AGENTS.md](AGENTS.md) before contributing. Currently Alpha; Shell, plugins and MCP run on the host, and permission prompts do not provide sandbox isolation.

[Apache License 2.0](LICENSE)
