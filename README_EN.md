<p align="center">
  <img src="docs/assets/miniagent-banner.svg" width="800" alt="MiniAgent — a minimal Python Agent + Harness">
</p>

<p align="center"><strong>A minimal Python Agent + Harness.</strong><br>A few hundred lines at the core. Read it, change it, run it in your terminal.</p>

<p align="center">
  <a href="https://github.com/ZhuLinsen/MiniAgent/actions/workflows/ci.yml"><img src="https://github.com/ZhuLinsen/MiniAgent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB" alt="Python 3.11+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue" alt="Apache 2.0"></a>
  <img src="https://img.shields.io/badge/status-alpha-ff815c" alt="Alpha">
</p>

<p align="center"><a href="README.md">中文</a> · <a href="#quick-start">Quick start</a> · <a href="#build-your-own-agent">Python API</a> · <a href="#read-the-core">Read the source</a></p>

**A 591-line core for an agent that reads code, edits files and runs tests.** MiniAgent is both a ready-to-use terminal coding assistant and a small Harness you can embed in Python. Compose your own models, tools, plugins and sessions.

## Why MiniAgent?

- **Small and readable**: just 4 Python files at the core. Follow the model calls, tool loop and plugin lifecycle in the source.
- **Ready to work**: 6 coding tools, multi-turn tasks, streamed answers and resumable sessions for everyday code inspection, editing and validation.
- **Easy to extend**: mount tools and services with plugins, specialize tasks with Skills, and connect external capabilities through MCP.

## Quick start

Requires **Python 3.11+**. Install from source in a virtual environment:

```bash
git clone https://github.com/ZhuLinsen/MiniAgent.git
cd MiniAgent
python -m pip install -e ".[credentials]"
miniagent
```

On the first launch, choose a model and enter its key. Use `/connect` to configure connections and `/models` to switch models. See [model setup](docs/model-connections.md) for environment variables and custom endpoints.

Let it inspect your project:

```bash
miniagent --policy readonly --prompt "Read the project structure and find its entry points and test commands"
```

## Use it as a coding Agent

| Capability | What you can do |
| --- | --- |
| Six coding tools | Find code with `read` / `grep` / `glob`, change files with `write` / `edit`, run commands and tests with `bash` |
| Multi-turn execution | The model calls tools, reads results and continues the task, with streamed answers and tool progress |
| Resumable sessions | Save conversations and tool records; continue with `--session <path>`; compact context as conversations grow |
| Skills & MCP | Switch task instructions and tool access; connect your own MCP tool servers |

File changes and Shell calls require confirmation by default. Type `/help` for commands, `/skills reviewer` to switch to code review and `/session` for the current session.

<details>
<summary>See an actual run: read code → fix a function → run tests</summary>

![MiniAgent reading code, editing a function and running tests](docs/assets/coding-session.png)

[Full recording and reproduction steps](docs/demo.md)

</details>

## Build your own Agent

Harness manages model calls, tool execution and plugin lifecycles. Use it as an ordinary Python library in your script or application:

```python
from miniagent import Harness
from miniagent.plugins import coding_tools
from miniagent.policy import Policy

app = Harness(model="provider:model-id", policy=Policy(mode="readonly"))
app.use(coding_tools())
print(app.run("Read the project structure and explain its entry points"))
```

Replace `provider:model-id` with your model and configure its credential. Use `load_config()` to reuse CLI connection settings. Inside an async application, use `async with app` and `await app.arun(...)`.

Compose your own capabilities with `Plugin`:

| Plugin API | Purpose |
| --- | --- |
| `ctx.tool(...)` | Mount tools with shared argument validation, authorization and Skill restrictions |
| `ctx.service(...)` | Provide services for other plugins |
| `ctx.on(...)` | Subscribe to model and tool events for progress displays or logging |
| `ctx.cleanup(...)` | Register resource cleanup for exit and failures |

Plugins support dependency ordering, startup rollback and reverse cleanup. See the [guide](docs/lean-harness.md) for custom tools, MCP, Skills and persistent sessions.

## Read the core

Start with these 4 files:

| File | Responsibility |
| --- | --- |
| [agent.py](miniagent/agent.py) | The model → tool → model task loop |
| [harness.py](miniagent/harness.py) | Plugins, services, events and lifecycles |
| [llm.py](miniagent/llm.py) | Model calls and streamed responses |
| [registry.py](miniagent/tools/registry.py) | Tool registration, argument validation and authorization |

The four-file core is **591 lines**; the entire Python package is **2,122 lines**, including CLI, tools and configuration. Counts include comments and blank lines and exclude third-party dependencies. Verify with `python scripts/source_stats.py`; see [counting details](docs/project-status.md).

## Docs

[Guide](docs/lean-harness.md) · [Model setup](docs/model-connections.md) · [Changelog](docs/CHANGELOG.md) · [Contributing rules](AGENTS.md)

Currently Alpha. Read the [migration guide](docs/legacy-migration.md) before upgrading from the old API. Shell, plugins and MCP servers are trusted code; tool authorization does not provide a container sandbox.

[Apache License 2.0](LICENSE)
