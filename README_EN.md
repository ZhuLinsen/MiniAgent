<p align="center">
  <img src="docs/assets/miniagent-banner.svg" width="800" alt="MiniAgent — a Python-native mini harness + agent">
</p>

<p align="center"><strong>Small core. Real work.</strong><br>A Python-native mini harness + coding agent. Read it, change it, run it in your terminal.</p>

<p align="center">
  <a href="https://github.com/ZhuLinsen/MiniAgent/actions/workflows/ci.yml"><img src="https://github.com/ZhuLinsen/MiniAgent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB" alt="Python 3.11+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue" alt="Apache 2.0"></a>
  <img src="https://img.shields.io/badge/status-alpha-ff815c" alt="Alpha">
</p>

<p align="center"><a href="README.md">中文</a> · <a href="#quick-start">Quick start</a> · <a href="docs/lean-harness.md">Guide</a> · <a href="docs/project-status.md">Capabilities & source size</a></p>

MiniAgent combines models, a tool loop, plugins, Skills, MCP and resumable sessions in a small Python agent. Use it to inspect code, edit files and run tests, or embed the Harness in your application and add capabilities through plugins.

Inspired by [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness): keep the runtime small and compose capabilities through plugins. Built for Python developers who want to understand, customize and share their agents.

## Watch it finish a task

![Actual MiniAgent run: read code, fix an addition function, run tests](docs/assets/coding-session.png)

2026-10-17, Windows / Python 3.12, Anspire `qwen3.5-flash`: a real API, file tools and Shell test run. The test file was unchanged. This image renders the actual recorded CLI output. It demonstrates a small repair task; see [the transcript and reproduction steps](docs/demo.md).

## Quick start

Requires **Python 3.11+**. Install from the current source:

```bash
git clone https://github.com/ZhuLinsen/MiniAgent.git
cd MiniAgent
python -m pip install ".[credentials]"
miniagent
```

On your first interactive launch, choose a provider, enter its key and select a model ID. Keys can use a supported OS credential vault; without one, they remain in memory for the current process. Use `/connect` to add connections and `/models` to switch models. See [connection setup](docs/model-connections.md).

Writes and Shell calls require confirmation by default. Start with a read-only inspection:

```bash
miniagent --policy readonly --prompt "Inspect the project structure and explain its entry points"
```

For automation, explicitly configure a model through environment variables, JSON or CLI arguments. Install MCP with `python -m pip install ".[mcp]"`. Run `miniagent --help` for options.

## The everyday agent toolkit

| Capability | In MiniAgent |
| --- | --- |
| Models & tool loop | Multiple providers, native tool calls and streamed text |
| Coding tools | `read`, `write`, `edit`, `grep`, `glob`, `bash` |
| Plugin composition | Context/Service, dependencies, events, rollback, cleanup, a replaceable Loop and opt-in reactive lifecycle |
| Skills & MCP | Switch prompts and tool allowlists; connect MCP stdio servers |
| Resumable sessions | JSONL history, context compaction, inspection before resuming uncertain effects |
| Terminal interface | Connection guide, tool progress, Markdown answers and session commands |

## Use it from Python

```python
import asyncio
from miniagent import Harness
from miniagent.plugins import coding_tools
from miniagent.policy import Policy

async def main():
    async with Harness(model="provider:model-id", policy=Policy(mode="readonly")) as app:
        app.use(coding_tools())
        print(await app.arun("Inspect the project structure and explain its entry points"))

asyncio.run(main())
```

Replace `provider:model-id` with your selected model and configure its credential. Mount custom tools, services and events with `Plugin`; see [examples and the runtime guide](docs/lean-harness.md).

## Size and scope

Current version: **0.2.0a1 / alpha**. This branch has a 598-line core and 5,148 lines across the package, including a replaceable Loop and opt-in reactive plugins. Teaching APIs and compatibility tools still contribute substantially, and the total-source reduction target remains open. See [project status](docs/project-status.md) for counting rules, a DSH comparison, evidence and next steps.

Type `/help` for commands; use `--session <path>` to resume. Shell, Python plugins and MCP servers are trusted code; tool authorization is not a container sandbox. See [runtime and migration guidance](docs/lean-harness.md) for permissions, recovery and legacy API boundaries.

## Contribute and credits

Reproducible issues, small plugins and real task examples are welcome. Read [AGENTS.md](AGENTS.md) for development principles and the [Changelog](docs/CHANGELOG.md) for changes.

Coding tools draw on [nanocode](https://github.com/1rgs/nanocode); model adapters use [any-llm](https://github.com/mozilla-ai/any-llm), and MCP uses its official Python SDK. The logo continues the terminal visual style of the author's [AlphaEvo](https://github.com/ZhuLinsen/alphaevo).

[Apache License 2.0](LICENSE)
