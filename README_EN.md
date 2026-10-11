# MiniAgent

**Tiny Core. Real Agent Capabilities.** A plugin-first Python Agent Harness that combines models, tools, Skills, MCP and resumable sessions.

[中文](README.md) · [Runtime and migration guide](docs/lean-harness.md) · [Changelog](docs/CHANGELOG.md) · [CI](https://github.com/ZhuLinsen/MiniAgent/actions/workflows/ci.yml)

Requires **Python 3.11+**. Version **0.2.0a1** is for evaluating the architecture and developing plugins. Two models passed live Anspire gateway acceptance; native multi-provider acceptance and the total-source reduction target remain incomplete. See the [acceptance evidence](docs/acceptance-2026-10-11.md).

## Get started

```bash
git clone https://github.com/ZhuLinsen/MiniAgent.git
cd MiniAgent
python -m pip install .
```

Create `.env` in the project and fill in your provider key and model ID. Replace `<model-id>` below. For Qwen use `dashscope:<model-id>` and `DASHSCOPE_API_KEY`; for Claude use `anthropic:<model-id>` and `ANTHROPIC_API_KEY`.

Select a model explicitly. A key or API URL alone causes the CLI to report a missing model before creating a client. `--model` takes precedence over JSON `llm.model`, then `LLM_MODEL`.

```dotenv
DEEPSEEK_API_KEY=your-provider-key
LLM_MODEL=deepseek:<model-id>
```

```bash
miniagent --policy readonly --prompt "Inspect the project structure and explain its entry points"
miniagent
```

Writes, Shell and MCP calls require confirmation by default. Noninteractive confirmation denies execution. Use `--policy trusted` for automation you explicitly trust. Managed file tools hide `.env*` (except `.env.example`), `.git` and private-key files unless `--allow-sensitive-files` is explicitly supplied. Shell, Python plugins and MCP servers are trusted code outside the managed file boundary.

## Capabilities

- Native tool calls and streamed text; one async model boundary with provider credential isolation.
- Instance-owned tool registry; plugin dependency ordering, activation rollback and reverse cleanup.
- `read / write / edit / grep / glob / bash` with workspace checks and authorization.
- JSONL sessions, context compaction that preserves whole tool groups, and inspection before resuming uncertain effects.
- Reversible Skill execution whitelists and optional official MCP SDK stdio integration.

CLI commands: `/help`, `/model`, `/plugins`, `/skills`, `/session`, `/stream`. `/plugins` currently lists loaded plugins. `--session <path>` resumes a session; `/session new` creates one. Switching models creates a fresh session.

## Python API

```python
from miniagent import Harness
from miniagent.plugins import coding_tools
from miniagent.policy import Policy
from miniagent.session import Session

app = Harness(model="deepseek:<model-id>", policy=Policy(mode="readonly"),
              session=Session("task.jsonl"))
app.use(coding_tools())
print(app.run("Inspect the project structure"))
```

In an existing event loop use `await app.arun(...)` and `async with app` for resource ownership. One task per Harness; plugins and Skills change only while idle.

## A custom plugin

```python
from miniagent import Harness, Plugin
from miniagent.policy import Policy
from miniagent.tools.registry import Tool

def calculator(ctx):
    ctx.tool(Tool("add_one", "Add one", {"type": "object",
                  "properties": {"n": {"type": "integer"}}, "required": ["n"]},
                  lambda n: n + 1))

app = Harness(model="deepseek:<model-id>", policy=Policy(mode="trusted"))
app.use(Plugin("calculator", calculator))
print(app.run("Use add_one to add 1 to 2"))
```

This example explicitly trusts the custom tool. The [runtime guide](docs/lean-harness.md) covers model configuration, MCP installation and plugins, Skill switching, recovery and compatibility.

## Validation and version boundaries

CI covers Windows/Linux, Python 3.11/3.12, offline regression, native-runtime static checks, dependency audit, builds and installed-wheel verification without MCP/Legacy extras. Local HTTP fixtures exercise OpenAI, DeepSeek, DashScope/Qwen and Anthropic SDK multi-turn tool protocols. They do not establish live API compatibility.

`python scripts/source_stats.py` reports the four-file core, runtime mechanisms including Policy/tool plugin/Session, and **all official Python source** separately. Teaching and extension compatibility code remains; the 2000–2800 total-line target is not achieved. No live model task screenshot or performance comparison is claimed; simulated output is not presented as a real demo.

Use `miniagent --legacy` for the teaching CLI and install `miniagent[legacy]` for basic/system tools. The old implicit MCP API was removed; migrate to `mcp_plugin` as documented. Automatic dependency recovery, long-term Memory and Streamable HTTP are outside this alpha delivery.

## Acknowledgments and license

Coding tools are inspired by [nanocode](https://github.com/1rgs/nanocode). Licensed under [Apache License 2.0](LICENSE).
