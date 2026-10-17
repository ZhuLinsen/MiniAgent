# Lean Harness implementation

Six stacked PRs: baseline and targeted fixes; async runtime and policy;
any-llm; durable sessions; Skills and official MCP; CLI and release checks.
Each PR targets its predecessor. Merge in order; revert in reverse order.

## Contracts

The runtime is async; use `await app.arun()` in an existing event loop.
`app.run()` is a script convenience. One task per Harness/Session at a time.
Plugins change only while idle. Startup dependency sorting, rollback and
reverse cleanup are supported; automatic dependency recovery is deferred.
Tools pass through one validation/authorization entry point.

Python plugins and MCP servers are trusted software. Workspace checks cover
managed file tools, not arbitrary shell execution. Shell/MCP require explicit
authorization; this is not a sandbox. Noninteractive approval defaults to deny.
Provider keys are isolated. Tool arguments and key prefixes must not be logged.

Sessions preserve original events and do not replay uncertain side effects.
Compaction changes only the model view. Dynamic plugins, Subagent and long-term
Memory are deferred. Source line counts are observations, not release gates.

## Validation

Run `python -m pytest tests -q` and `python scripts/source_stats.py`.
Real-provider smoke tests are opt-in and must report provider/model/SDK version;
mock tests do not establish live compatibility. No provider credential is
required for deterministic regression tests.

Windows baseline: 189 passed, 2 failures caused by Unix-only `sleep` in timeout
tests. Those tests now invoke the running Python interpreter on every platform.
Original commit `4d61483d039e802f6d34fb6b42d6e2a99b1b6a1c`: 20 files,
4,009 physical lines, 3,288 nonempty lines.

## Models

Python >=3.11; validated SDK: any-llm-sdk 1.33.0. SDK HTTP normalization and
stream assembly are tested without a remote service. Real DeepSeek/Qwen/Claude
calls have not been validated without explicit test credentials.
Use `Harness(model="provider:model-id")` with the provider's environment key.
Custom JSON configuration:

```json
{"llm": {"model": "gateway:model-id"}, "providers": {"gateway": {
  "type": "openai-compatible", "base_url": "https://example.com/v1",
  "api_key_env": "GATEWAY_API_KEY"
}}}
```

Pass `providers=cfg.providers` to Harness. Empty key configuration is supported
only for explicitly configured keyless custom endpoints. Base URL overrides
use compatibility mode. Native provider clients retain SDK retry behavior;
custom endpoints disable retries. The loop never retries tools or interrupted
streams. `temperature=None` leaves provider defaults unchanged.
Run live tests with `MINIAGENT_TEST_MODEL` and `python -m pytest -m live -v`.

## Sessions

Pass `Session(path)` to Harness. JSONL events have version/sequence fields;
unsupported versions and corrupt complete lines fail explicitly. An incomplete
last line is discarded under an OS writer lock. Original messages and effects
remain on disk; protect Session files as sensitive user data.

Interrupted started tools are uncertain: inspect their actual effects, then use
`session.open(); session.resolve(call_id, verified_result); session.close()`.
The runtime refuses new turns until uncertainty is resolved, and never replays
tools during restore. Calls not yet started get an interrupted result.

`MINIAGENT_CONTEXT_BUDGET` includes schemas and output reserve. UTF-8 bytes are
used as a conservative token estimate, not an exact provider tokenizer.
Compaction retains whole recent turns, summarizes old data with no tools, and
falls back to an explicit omission notice. An oversized current turn errors
instead of splitting a tool group. Long-term Memory remains legacy-only.

## Skills and MCP migration

`app.apply_skill(get_skill("reviewer"))` limits schema visibility AND execution.
Switching skills or `app.apply_skill()` restores the tool catalog.
`read_skill(path)` supports scalar name/description and allowed-tools
(space-separated names or a JSON list) plus Markdown body. This is a limited
frontmatter format, not full YAML or automatic discovery.

Install `miniagent[mcp]` (validated MCP SDK 2.3.0), then:

```python
from miniagent.extensions.mcp_plugin import mcp_plugin
app.use(mcp_plugin("local", command, args, cwd=workspace))
```

Use an explicit executable and argument list, not a shell command string.
Tools are namespaced as local__tool. All calls require policy approval even
if the server declares read-only annotations. The connection has a dedicated
owner task to close its context in the same task that entered it.
Discovery failure rolls back tools/services; unload closes the process.
Remote names are closure-bound: a payload field such as `_name` is forwarded as
data and cannot change the approved tool route or bypass the Skill whitelist.
Old MCPClient and load_mcp_tools APIs fail with an actionable migration message.
Streamable HTTP is deferred.
