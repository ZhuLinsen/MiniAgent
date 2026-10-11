"""Lifecycle transitions retain ownership, cleanup and busy/session protections."""
import asyncio

import pytest

from miniagent import Harness, Plugin, loop_plugin
from tests.test_harness import tool


def test_pending_plugin_recovers_without_reregistration():
    async def scenario():
        seen = []
        app = Harness(reactive=True)
        app.use(Plugin("consumer", lambda c: seen.append(c.get("value")), requires=("provider",)))
        await app.start()
        assert app.states["consumer"] == "PENDING" and seen == []
        app.use(Plugin("provider", lambda c: c.service("value", 1)))
        await app.start()
        assert seen == [1] and app.states["consumer"] == "ACTIVE"
        await app.unuse("provider")
        assert app.states["consumer"] == "PENDING" and "value" not in app.services
        app.use(Plugin("provider", lambda c: c.service("value", 2)))
        await app.start()
        assert seen == [1, 2]
        await app.aclose()
    asyncio.run(scenario())


def test_service_injection_transitive_cleanup_and_different_provider():
    async def scenario():
        cleaned, seen = [], []
        app = Harness(reactive=True)
        def base(ctx):
            ctx.service("inference", 1)
            ctx.service("other", 2)
            ctx.cleanup(cleaned.append, "base")
        def middle(ctx):
            seen.append(ctx.get("inference"))
            ctx.service("derived", 3)
            ctx.tool(tool())
            ctx.on("notice", lambda e: None)
            ctx.cleanup(cleaned.append, "middle")
        def leaf(ctx):
            ctx.cleanup(cleaned.append, "leaf")
        app.use(Plugin("leaf", leaf, inject=("derived",)))
        app.use(Plugin("middle", middle, inject=("inference",)))
        app.use(Plugin("base", base))
        await app.start()
        await app.unuse("base")
        assert cleaned == ["leaf", "middle", "base"]
        assert app.states["middle"] == app.states["leaf"] == "PENDING"
        assert not app.registry.tools and not app.events["notice"]
        assert set(app.services) == {"agent_loop"}
        app.use(Plugin("replacement", lambda c: c.service("inference", 42)))
        await app.start()
        assert seen == [1, 42] and app.states["leaf"] == "ACTIVE"
        await app.aclose()
    asyncio.run(scenario())


def test_static_service_dependents_require_explicit_unload():
    async def scenario():
        app = Harness()
        app.use(Plugin("provider", lambda c: c.service("value", 1)))
        app.use(Plugin("consumer", lambda c: None, inject=("value",)))
        await app.start()
        with pytest.raises(ValueError, match="active dependents"):
            await app.unuse("provider")
        assert app.services["value"] == 1 and app.states["consumer"] == "ACTIVE"
        await app.unuse("consumer")
        await app.unuse("provider")
        await app.aclose()
    asyncio.run(scenario())


def test_known_dependency_cycles_are_errors_even_in_reactive_mode():
    async def scenario():
        app = Harness(reactive=True)
        app.use(Plugin("a", lambda c: None, requires=("b",)))
        app.use(Plugin("b", lambda c: None, requires=("a",)))
        with pytest.raises(ValueError, match="Cyclic"):
            await app.start()
        assert not app.active and not app.services and not app.busy
    asyncio.run(scenario())


def test_reactivation_failure_rolls_back_new_batch_preserves_existing():
    async def scenario():
        app = Harness(reactive=True)
        app.use(Plugin("stable", lambda c: c.service("stable", "kept")))
        def broken(ctx):
            ctx.tool(tool())
            ctx.service("partial", 1)
            raise RuntimeError("setup failed")
        app.use(Plugin("dependent", broken, inject=("value",)))
        await app.start()
        app.use(Plugin("provider", lambda c: c.service("value", 2)))
        with pytest.raises(RuntimeError, match="setup failed"):
            await app.start()
        assert set(app.services) == {"agent_loop", "stable"}
        assert not app.registry.tools
        assert app.states["dependent"] == app.states["provider"] == "PENDING"
        assert app.states["stable"] == "ACTIVE" and not app.busy
        await app.unuse("dependent")
        assert app.states["provider"] == "ACTIVE"
        await app.aclose()
    asyncio.run(scenario())


def test_cleanup_failure_does_not_leave_transitive_consumers_running():
    async def scenario():
        app = Harness(reactive=True)
        cleaned = []
        def provider(ctx):
            ctx.service("value", 1)
            ctx.cleanup(cleaned.append, "provider")
        def consumer(ctx):
            def fail():
                cleaned.append("consumer")
                raise RuntimeError("cleanup failed")
            ctx.service("child", 2)
            ctx.cleanup(fail)
        app.use(Plugin("provider", provider))
        app.use(Plugin("consumer", consumer, inject=("value",)))
        app.use(Plugin("leaf", lambda c: c.cleanup(cleaned.append, "leaf"), inject=("child",)))
        await app.start()
        with pytest.raises(BaseExceptionGroup):
            await app.unuse("provider")
        assert cleaned == ["leaf", "consumer", "provider"]
        assert set(app.services) == {"agent_loop"}
        assert app.states["consumer"] == app.states["leaf"] == "PENDING"
        assert "provider" not in app.plugins and not app.busy
        await app.aclose()
    asyncio.run(scenario())


def test_setup_and_cleanup_failures_both_reported():
    async def scenario():
        app = Harness(reactive=True)
        def bad(ctx):
            def fail():
                raise ValueError("cleanup")
            ctx.service("temporary", 1)
            ctx.cleanup(fail)
            raise RuntimeError("setup")
        app.use(Plugin("bad", bad))
        with pytest.raises(BaseExceptionGroup) as captured:
            await app.start()
        assert {type(e) for e in captured.value.exceptions} == {RuntimeError, ValueError}
        assert not app.active and not app.services and not app.busy
    asyncio.run(scenario())


def test_replace_loop_keeps_harness_busy_and_uncertain_guards():
    async def scenario():
        app = Harness(reactive=True)
        entered, release = asyncio.Event(), asyncio.Event()
        async def custom(runtime, query, *, max_steps, stream):
            entered.set()
            await release.wait()
            return f"{query}:{max_steps}"
        await app.unuse("agent-loop")
        app.use(loop_plugin(custom))
        task = asyncio.create_task(app.arun("go", max_steps=3))
        await entered.wait()
        with pytest.raises(RuntimeError, match="running"):
            await app.unuse("agent-loop")
        with pytest.raises(RuntimeError, match="running"):
            await app.start()
        release.set()
        assert await task == "go:3"
        app.record({"role": "tool", "tool_call_id": "unknown", "content": "inspect effects"},
                   tool=True, uncertain=True)
        with pytest.raises(RuntimeError, match="uncertain"):
            await app.arun("again")
        await app.aclose()
    asyncio.run(scenario())


def test_cancelled_setup_rolls_back_resources_and_releases_busy():
    async def scenario():
        app = Harness(reactive=True)
        entered, release = asyncio.Event(), asyncio.Event()
        cleaned = []
        async def setup(ctx):
            ctx.service("partial", 1)
            ctx.cleanup(cleaned.append, "closed")
            entered.set()
            await release.wait()
        app.use(Plugin("slow", setup))
        task = asyncio.create_task(app.start())
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert cleaned == ["closed"] and not app.active and not app.services and not app.busy
    asyncio.run(scenario())


def test_custom_loop_cancellation_closes_persistent_session(tmp_path):
    from miniagent.session import Session
    async def scenario():
        app = Harness(session=Session(tmp_path / "session"))
        entered, release = asyncio.Event(), asyncio.Event()
        async def custom(runtime, query, **kwargs):
            runtime.record({"role": "user", "content": query})
            entered.set()
            await release.wait()
        await app.unuse("agent-loop")
        app.use(loop_plugin(custom))
        task = asyncio.create_task(app.arun("cancelled"))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not app.busy and app.session.lock is None
        restored = Session(app.session.path).open()
        assert restored.messages == [{"role": "user", "content": "cancelled"}]
        restored.close()
        await app.aclose()
    asyncio.run(scenario())


def test_loop_service_waits_for_injected_dependency():
    async def scenario():
        app = Harness(reactive=True)
        await app.unuse("agent-loop")
        async def custom(runtime, query, **kwargs):
            return str(runtime.services["value"])
        app.use(loop_plugin(custom, inject=("value",)))
        await app.start()
        with pytest.raises(ValueError, match="active agent_loop"):
            await app.arun("waiting")
        app.use(Plugin("provider", lambda c: c.service("value", 42)))
        assert await app.arun("ready") == "42"
        await app.unuse("provider")
        assert app.states["agent-loop"] == "PENDING"
        app.use(Plugin("new-provider", lambda c: c.service("value", 7)))
        assert await app.arun("restored") == "7"
        await app.aclose()
    asyncio.run(scenario())


def test_active_scope_cannot_register_resources_during_task_or_after_close():
    async def scenario():
        scopes = []
        app = Harness()
        app.use(Plugin("owner", lambda ctx: scopes.append(ctx)))
        await app.start()
        async def custom(runtime, query, **kwargs):
            with pytest.raises(RuntimeError, match="running"):
                scopes[0].service("late", 1)
            return "ok"
        await app.unuse("agent-loop")
        app.use(loop_plugin(custom))
        assert await app.arun("go") == "ok"
        await app.unuse("owner")
        with pytest.raises(RuntimeError, match="closed"):
            scopes[0].service("late", 1)
        await app.aclose()
    asyncio.run(scenario())
