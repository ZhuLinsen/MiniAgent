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
