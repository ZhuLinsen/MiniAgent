# Native Harness guide — 0.3.0a1 candidate

MiniAgent is a Python-native mini harness + coding agent. The native runtime,
CLI, plugins, Skills, MCP and Session are the supported API. The original
teaching version lives on [codex/legacy-pre-harness](https://github.com/ZhuLinsen/MiniAgent/tree/codex/legacy-pre-harness).
See [breaking changes and migration](legacy-migration.md).

## Run and compose

```python
from miniagent import Harness, Policy, Session
from miniagent.plugins import coding_tools

app = Harness(model="provider:model-id", policy=Policy(mode="readonly"),
              session=Session("task.jsonl"))
app.use(coding_tools())
print(app.run("Inspect the project and explain its entry points"))
```

Choose a real model and configure its provider credential. In an existing event
loop use `await app.arun(...)` and `async with app`. `run()` is a script convenience
that closes plugin resources on return. One task per Harness/Session at a time;
plugin and Skill changes are allowed only while idle.

## Plugins, services and cleanup

```python
from miniagent import Plugin, Tool

def arithmetic(ctx):
    ctx.tool(Tool("add_one", "Add one", {"type": "object",
                  "properties": {"n": {"type": "integer"}}, "required": ["n"]},
                  lambda n: n + 1, access="read"))
    ctx.cleanup(lambda: print("arithmetic closed"))

app.use(Plugin("arithmetic", arithmetic))
```

`ctx.service(name, value)`, `ctx.get(name)`, `ctx.on(event, callback)` and
`ctx.cleanup(callback)` share the plugin's Scope. Registrations unwind on unload;
partial startup rolls back. Tools belong to the instance Registry, not an import
side effect or global decorator catalog.

Dependencies are static: `requires` names plugins, missing or cyclic dependencies
fail at startup, and an active dependency cannot be unloaded before its consumers.
Harness calls the native agent loop directly. Reactive dependencies and a public
replaceable Loop interface are separate proposals, not requirements of this version.

## Models and configuration

Model precedence: CLI `--model` > JSON `llm.model` > `LLM_MODEL` > saved default.
A key or endpoint alone never chooses a model. Unprefixed IDs use OpenAI;
use `provider:model-id` to select another adapter. Credentials resolve after the
final model; unrelated providers' keys are never borrowed. `LLM_API_KEY` and
`LLM_API_BASE` remain explicit gateway overrides.

First-run TTY guidance and `/connect`, `/models` reuse the same SDK client factory.
Native provider optional SDKs may require their any-llm extra. Discovery is not
evidence of model/tool compatibility. See [connections and vault behavior](model-connections.md).

```json
{"llm": {"model": "gateway:model-id"}, "providers": {"gateway": {
  "type": "openai-compatible", "base_url": "https://example.com/v1",
  "api_key_env": "GATEWAY_API_KEY"
}}}
```

Native JSON accepts llm, providers, mcp_servers, system_prompt and context_budget.
The llm section accepts model, api_key, api_base and temperature. Unsupported
settings fail with migration guidance. `LLM_TEMPERATURE` is supported; JSON can
override it. Shell/output limits stay environment settings in `.env.example`.

Python >=3.11; any-llm-sdk 1.33.0. Native adapters retain SDK retry behavior;
custom compatible endpoints disable retries. Tools and interrupted streams are
never automatically replayed. Four provider protocol fixtures are local HTTP
tests; live Anspire records are reported separately in [the demo](demo.md) and
[historical acceptance](acceptance-2026-10-11.md).

## Tools and authorization

`coding_tools()` mounts read, write, edit, grep, glob and bash. Every execution
passes Skill checks, JSON Schema and Policy before the executor starts. Shell
uses one async implementation with timeout, cancellation and bounded output.
Direct trusted integrations can call `await miniagent.plugins.shell(cmd, cwd=...)`.

`readonly` denies writes/Shell/MCP; `confirm` asks in a TTY and denies unattended
approval; `trusted` is for explicitly trusted automation. Managed file tools stay
inside the workspace and hide `.env*` (except `.env.example`), `.git`, `.pem`,
`.key`, `.p12` and `.pfx` paths unless `--allow-sensitive-files` is explicit.
Python plugins, Shell and MCP servers are trusted software outside these file
checks. Authorization is not a container sandbox.

## Skills and MCP

`app.apply_skill(get_skill("reviewer"))` filters both schemas and execution.
Switching Skill restores registered tools without replaying work. A Skill may
set temperature and a default max_iterations budget; explicit max_steps wins.
`read_skill(path)` reads trusted SKILL.md with scalar frontmatter and tool lists,
not arbitrary YAML. Long-term memory and subagents are deferred for this release.

Install `.[mcp]` and mount `mcp_plugin(name, command, args, ...)` from
`miniagent.extensions.mcp_plugin`. Tools are named `server__tool`. The official
SDK stdio connection is owned by a dedicated task and cleaned up on unload.
CLI JSON can supply mcp_servers entries with command, args and optional env.
Streamable HTTP is not implemented.

## Sessions and recovery

Pass `Session(path)` or CLI `--session <path>` to resume JSONL. Without a CLI path,
a new session is created under MINIAGENT_HOME/sessions. Session versions and
sequence numbers are checked; an incomplete trailing line is discarded under
the OS single-writer lock. Other corruption fails visibly.

Original events stay on disk. Context compaction preserves whole tool groups
and changes only the model view; UTF-8 bytes provide a conservative budget
estimate, not exact billing. Summary failure drops older complete turns safely.

If a non-read tool has started and then raises or times out, its result is
uncertain. The loop stops and pairs remaining unstarted calls without running
them. Cancellation repairs the complete batch too. Inspect actual effects, then
use `app.resolve(id, verified_result)` or `/session resolve ID verified-result`.
Until resolved, further turns are rejected. These guards also apply in memory.
Schema/authorization rejection and completed nonzero Shell exits are known
failures. Never resolve a result merely to bypass inspection.

## CLI and validation

Run `miniagent --help`; inside the REPL use `/help`. `/plugins` lists active
plugins. `/skills [name|path|off]`, `/stream`, `/session [new]` and model commands
operate on the current runtime. Model switching resolves the new credential,
closes the old client and starts a fresh Session while preserving old files.
Non-TTY output stays literal and NO_COLOR is respected.

```bash
python -m pip install -e ".[dev,mcp,credentials]"
python -m pytest tests -q -m "not live"
python scripts/source_stats.py
python scripts/check_ai_assets.py
```

CI covers Windows/Linux, Python 3.11/3.12, full native regression, lint, locked
production dependency audit, build and a minimum wheel install outside checkout.
Live tests require explicit MINIAGENT_TEST_MODEL and credentials. Run the
[source counter](../scripts/source_stats.py) for the current code size. Earlier
live recordings are historical evidence, not validation of this revised commit.
No stable release, universal provider compatibility or broad repository success
rate is claimed.
