# Lean Harness implementation

Six stacked PRs: baseline and targeted fixes; async runtime and policy;
any-llm; durable sessions; Skills and official MCP; CLI and release checks.
Each PR targets its predecessor. Merge in order; revert in reverse order.

## Contracts

The runtime is async; use `await app.arun()` in an existing event loop.
`app.run()` is a script convenience. One task per Harness/Session at a time.
Plugins change only while idle. Startup dependency sorting, rollback and
reverse cleanup are supported. `Harness(reactive=True)` opts into dependency
waiting, transitive deactivation and restoration on the next reconciliation;
the default remains strict. [Lifecycle and Loop contracts](plugin-lifecycle.md)
describe service injection and replacement of the default `agent-loop` plugin.
Tools pass through one validation/authorization entry point.

Python plugins and MCP servers are trusted software. Workspace checks cover
managed file tools, not arbitrary shell execution. Shell/MCP require explicit
authorization; this is not a sandbox. Noninteractive approval defaults to deny.
Provider keys are isolated. Tool arguments and key prefixes must not be logged.

Sessions preserve original events and do not replay uncertain side effects.
Compaction changes only the model view. Fiber trees, HMR, Subagent and long-term
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

Model selection is explicit: CLI `--model` > JSON `llm.model` > `LLM_MODEL` >
saved connection default. [Interactive connection setup](model-connections.md)
is available through `--connect`, `/connect` and `/models`.
There is no implicit model default. A provider key or API base alone cannot
select a model; noninteractive calls fail before client creation when it is missing.
The native CLI offers first-run guidance in a TTY; the legacy CLI keeps explicit setup.
Credentials are resolved after the final model, including JSON and CLI overrides.
Unprefixed IDs use OpenAI unless an explicit legacy compatibility endpoint is set;
prefer `provider:model-id`. `LLM_API_KEY`/`LLM_API_BASE` are intentional gateway
overrides. Provider-specific keys are never borrowed for an unrelated model.

Python >=3.11; validated SDK: any-llm-sdk 1.33.0. SDK HTTP normalization and
stream assembly are tested without a remote service. Real DeepSeek/Qwen/Claude
native calls remain unvalidated; two models have live Anspire gateway evidence
in [the acceptance report](acceptance-2026-10-11.md).
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
Exceptions after a non-read tool starts (including Shell/MCP timeouts) stop the
batch and immediately persist an uncertain result. Remaining calls get paired
unstarted results. The same guard applies without a persistent Session:
`app.uncertain` reports pending IDs; `app.resolve(id, verified_result)` clears a
result only after inspection. Cancellation also repairs the full tool batch.
Authorization/schema failures before execution are known failures; nonzero
Shell exit codes are known failed outcomes rather than interrupted results.

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
Scalar `temperature` and positive `max-iterations` are supported. The Skill's
iteration limit is the default `arun` budget; an explicit `max_steps` overrides it.

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

## CLI and compatibility

Source install: `python -m pip install -e ".[mcp]"` (Python >=3.11).
The native Harness is now the default CLI. Use provider:model-id and the selected
provider credential; config files accept llm, providers and mcp_servers.
An MCP entry has command (executable), args (list), and optional env (mapping).
CLI: --workspace, --policy readonly|confirm|trusted, --session <JSONL path>,
--skill <name|SKILL.md path>, --prompt, --no-stream.
Managed files exclude `.env*` except `.env.example`, `.git` and files ending in
`.pem`, `.key`, `.p12` or `.pfx`. Directory grep/glob also filter these paths.
Explicit `--allow-sensitive-files` or `Policy(allow_sensitive_files=True)` opts in.
This does not constrain explicitly trusted Shell/MCP/Python code or detect all
possible secrets; inspect results before sharing them with a remote model.
Existing Session files resume automatically. Without --session a new file is
created under MINIAGENT_HOME/sessions. Non-TTY uses plain literal text; NO_COLOR
is honored. /plugins lists active plugins; /skills changes the execution view;
/session shows uncertain calls; /session resolve ID verified-result resolves
one manually after inspection; /session new starts a fresh task history.
/model provider:model-id re-evaluates credentials and starts a new Session to
avoid replaying provider-specific reasoning metadata across models.

`miniagent --legacy` retains the text teaching CLI. MiniAgent remains a
compatibility import; its native mode delegates to the same loop. Legacy APIs
retain their prior permission behavior and are not the new policy boundary.
Native iteration exhaustion now raises instead of returning a tool result as
an answer. Legacy Reflection and long-term Memory are not part of Harness.
No automated dependency recovery, Subagent or remote control plane is added.

The release is 0.2.0a1, not a stable v0.3. Original optional tools and teaching
compatibility modules remain for migration, so the total-source budget is not
met. Core and total counts are reported separately by scripts/source_stats.py.
No line count claim is made for installed third-party dependencies.
CI covers Windows/Linux with Python 3.11/3.12 and the locked MCP extra. Merge
PRs 1 through 6 in order; revert in reverse order. No release tag is created.

Optional basic/system tools now require `miniagent[legacy]` and explicit loading.
The default runtime does not import legacy parsers or Reflection. README changes
are synchronized in Chinese and English; detailed migration remains here.

## Local acceptance evidence (snapshot `fccd011`)

Windows / Python 3.12: 249 deterministic tests passed (3 live cases excluded).
Two selected models separately passed the three live cases via Anspire.
Real local MCP stdio subprocess discovery/call/cleanup passed.
New runtime lint (Ruff F checks), compileall, pip check, wheel and sdist build
passed. Locked dependencies were upgraded after an audit finding; a repeat
pip-audit reports no known vulnerabilities. CI adds Linux/Python 3.11 checks;
those results must be read from the PR, not inferred from local Windows tests.
New core: 521 physical lines; core plus Policy/tool plugin/Session: 823 lines.
All official package Python: 4,770 lines, including
legacy teaching, optional tools, Reflection and Orchestrator. The 2,800-line
total budget is not achieved; compatibility removal requires a separate,
explicitly reviewed migration rather than silently deleting existing APIs.

## Review follow-up and remaining acceptance

The four reviewed interruption/status/Skill regressions have dedicated tests.
MCP route binding prevents payload fields overriding the registered remote name.
OpenAI, DeepSeek, DashScope/Qwen and Anthropic native SDK HTTP fixtures exercise
two-turn tool calls and response conversion; these are offline protocol tests.
The opt-in live suite now covers basic replies and multi-turn tool use both with
and without streaming. Run it separately for each configured provider with
`MINIAGENT_TEST_MODEL` and `python -m pytest -m live -v`; credentials are never
printed. Gateway passes are recorded separately from native-provider coverage.

Every stacked PR has Windows/Linux × Python 3.11/3.12 regression CI. The final
PR additionally locks dependencies, checks native-runtime Ruff F rules, audits
production dependencies and installs a built wheel without optional extras.
`python scripts/minimal_install_smoke.py` requires uv on PATH and one built wheel.

Both READMEs now document the native runtime, supported Python version, plugin
example and migration guide. CLI parameters have bounded summaries; command and
content values are hidden. Known Shell/file failures display failed status.
Logger configuration shares the file-handler implementation (206 → 86 lines),
preserving its API and cache semantics. Total source remains above the budget.

The [v0.3 migration proposal](legacy-migration.md) covers Legacy, optional tools
and the old text parser. Current installation/startup measurements and a real
read/edit/test demo are in [the acceptance report](acceptance-2026-10-11.md).
Before/after comparison and native-provider validation remain open.
Reactive dependency reconciliation is now opt-in; interactive plugin management,
Fiber trees and HMR remain deferred.
Review readiness is not a stable-release or complete-plan acceptance claim.
Merge #6 → #7 → #8 → #9 → #10 → #11; use merge commits to preserve stacked
ancestry, or explicitly retarget/rebase each successor after a squash. The safety
and product follow-ups are in #11, so intermediate PRs are migration steps rather
than standalone release candidates. Roll back dependent PRs in reverse order.
