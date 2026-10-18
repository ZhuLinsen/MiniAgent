# Plugin lifecycle and replaceable Agent Loop

MiniAgent keeps the small async runtime. It does not implement a Fiber tree,
HMR, a plugin market or configuration hot reload.

## Strict and reactive modes

The default `Harness()` preserves strict startup: unresolved dependencies are
errors; a provider with active dependents cannot be unloaded until the caller
explicitly unloads those dependents. `Harness(reactive=True)` opts into waiting
and transitive cleanup instead. This flag is an API option, not a new CLI default.

`Plugin.requires` names plugins; `Plugin.inject` names services. Declare every
service consumed by a plugin. Scope service ownership tracks which provider
must outlive each consumer. `Scope.get()` reads services; it does not infer hidden
dependencies. Direct mutation of `app.services` bypasses these contracts and
is unsupported. Plugins, custom loops and cleanup callbacks are trusted Python.

```python
from miniagent import Harness, Plugin

app = Harness(reactive=True)
seen = []
app.use(Plugin("consumer", lambda ctx: seen.append(ctx.get("value")),
               inject=("value",)))
await app.start()  # consumer is PENDING
app.use(Plugin("provider", lambda ctx: ctx.service("value", 1)))
await app.start()  # consumer becomes ACTIVE
await app.unuse("provider")  # consumer is cleaned up and returns to PENDING
app.use(Plugin("replacement", lambda ctx: ctx.service("value", 2)))
await app.start()  # the same registered consumer activates with the new service
assert seen == [1, 2]
await app.aclose()
```

Examples with `await` belong inside an async function or notebook event loop.
`use()` registers synchronously. `start()` or the next `arun()` reconciles the
graph; `unuse()` reconciles after successful cleanup. Consumers do not need to
be re-registered. `app.states` reports `ACTIVE` or `PENDING`; the latter means
registered but inactive, including after rollback. PENDING does not mean a
background worker is polling or retrying.

Known cycles in `requires` fail before setup, even in reactive mode. Missing
plugins/services can wait. Service-production cycles cannot be inferred from
arbitrary setup functions and remain PENDING; inspect declarations to resolve them.

## Ownership, failure and cancellation

Unloading a provider computes all transitive plugin/service consumers, closes
them in reverse activation order, then closes the provider. Their registrations
remain PENDING; only the explicitly unloaded provider registration is removed.
Tools, event listeners and services are released by their owning Scope.

Setup failure closes its partial Scope and rolls back every plugin added in that
activation batch. Previously active plugins remain intact. A cleanup failure
does not stop the remaining Scope cleanup; errors are reported as exception
groups and automatic activation stops for that operation. Failure does not
promise external resources closed successfully: inspect reported cleanup errors
before calling `start()` to retry. If setup and cleanup both fail, both causes survive.

Lifecycle operations and active Scope resource registrations reject changes while
a task is running. Setup may register resources; a closed Scope may not. Cancellation
rolls back activation and clears the busy guard. A custom Loop cancellation also
closes the Session lock; the existing complete-tool-batch recovery guard remains.

## Replace the Loop

Every Harness registers `agent-loop`, which provides the async `agent_loop`
service. `/plugins` therefore also lists this default plugin. `arun()` resolves
that service rather than directly calling the core loop. There is no fallback to
the default Loop if its plugin was removed or is PENDING.

```python
from miniagent import loop_plugin
from miniagent.agent import agent_loop

async def measured_loop(app, query, *, max_steps, stream):
    await app.emit("custom.loop", query_length=len(query))
    return await agent_loop(app, query, max_steps=max_steps, stream=stream)

# Given an app with a configured backend:
await app.unuse("agent-loop")
app.use(loop_plugin(measured_loop))
answer = await app.arun("Inspect the project")
```

`loop_plugin` can declare `requires` and `inject`. Replacing a Loop obeys the
same idle-only rules; injected dependencies may leave it PENDING. Harness still
holds run exclusivity, opens/closes sessions, rejects unresolved effects and
repairs known interrupted tool batches. A completely custom Loop must itself
use Registry authorization and record messages/tool starts/results correctly;
it is trusted control flow, not a way to automatically sandbox arbitrary code.
Delegating to `agent_loop` preserves the native tool protocol and event behavior.

## Validation and rollback

Tests cover missing-dependency waiting, reactivation with a replacement service
provider, transitive resource cleanup, strict-mode refusal, cycles, failed
activation preserving old scopes, setup/cleanup error groups, busy guards,
cancelled activation and persistent Session cancellation with a custom Loop.
Real local MCP stdio call/denial/process cleanup still passes.

Rollback this PR restores the fixed native Loop and strict plugin lifecycle.
Callers using `inject`, `reactive` or `loop_plugin` must remove those new options
or explicitly unload/reload their dependents first. Session format is unchanged;
preserve session files and resolve uncertain effects without replaying tools.
