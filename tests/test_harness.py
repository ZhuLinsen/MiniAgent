import asyncio
import sys

import pytest

from miniagent import Harness, Plugin
from miniagent.policy import Policy
from miniagent.plugins import coding_tools, shell
from miniagent.tools.registry import Tool


def run(coro):
    return asyncio.run(coro)


def tool(name="add", executor=lambda n: n + 1):
    return Tool(name, "add", {"type": "object", "properties": {"n": {"type": "integer"}},
                             "required": ["n"], "additionalProperties": False}, executor)


def test_rollback_and_instance_isolation():
    async def scenario():
        first, second = Harness(), Harness()
        first.use(Plugin("base", lambda c: c.service("value", 1)))
        def broken(c):
            c.tool(tool())
            c.on("test", lambda e: None)
            raise RuntimeError("broken")
        first.use(Plugin("broken", broken, ("base",)))
        with pytest.raises(RuntimeError):
            await first.start()
        assert not first.services and not first.registry.tools and not first.active
        assert first.events["test"] == []
        second.use(Plugin("base", lambda c: c.service("value", 2)))
        await second.start()
        assert second.services["value"] == 2
        assert not first.services
        await second.aclose()
    run(scenario())


def test_dependency_order_cycle_and_unload():
    async def scenario():
        order = []
        app = Harness()
        app.use(Plugin("child", lambda c: order.append(c.get("value")), ("base",)))
        app.use(Plugin("base", lambda c: c.service("value", 42)))
        await app.start()
        assert order == [42]
        with pytest.raises(ValueError):
            await app.unuse("base")
        await app.unuse("child")
        await app.unuse("base")
        app.use(Plugin("a", lambda c: None, ("b",)))
        app.use(Plugin("b", lambda c: None, ("a",)))
        with pytest.raises(ValueError):
            await app.start()
    run(scenario())


def test_cleanup_continues_after_failure():
    async def scenario():
        cleaned = []
        app = Harness()
        app.use(Plugin("good", lambda c: c.cleanup(cleaned.append, "good")))
        def bad(c):
            c.service("x", 1)
            def fail():
                raise ValueError("cleanup")
            c.cleanup(fail)
        app.use(Plugin("bad", bad))
        await app.start()
        with pytest.raises(BaseExceptionGroup):
            await app.aclose()
        assert cleaned == ["good"] and not app.services
    run(scenario())


def test_policy_denial_validation_and_whitelist():
    async def scenario():
        app = Harness()
        app.registry.add(tool())
        with pytest.raises(PermissionError):
            await app.registry.execute("add", {"n": 1}, app.policy)
        app.registry.allowed = set()
        with pytest.raises(PermissionError):
            await app.registry.execute("add", {"n": 1}, Policy(mode="trusted"))
        app.registry.allowed = None
        from jsonschema import ValidationError
        with pytest.raises(ValidationError):
            await app.registry.execute("add", {"n": "bad"}, Policy(mode="trusted"))
    run(scenario())


def test_workspace_escape_and_symlink(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret").write_text("secret")
    root = tmp_path / "root"
    root.mkdir()
    policy = Policy(root)
    with pytest.raises(PermissionError):
        policy.path("../outside/new")
    try:
        (root / "link").symlink_to(outside, target_is_directory=True)
    except OSError:
        return  # Windows may require symlink privilege; traversal remains covered.
    async def scenario():
        app = Harness(policy=policy).use(coding_tools())
        await app.start()
        found = await app.registry.execute("grep", {"pattern": "secret"}, policy)
        assert not found
        await app.aclose()
    run(scenario())


def test_async_loop_busy_and_tool_results():
    class Backend:
        async def complete(self, messages, tools, stream):
            await asyncio.sleep(0)
            if messages[-1]["role"] == "user":
                return {"role": "assistant", "content": None, "tool_calls": [{
                    "id": "call1", "type": "function", "function": {"name": "add", "arguments": '{"n": 1}'}}]}
            assert messages[-1]["tool_call_id"] == "call1"
            return {"role": "assistant", "content": messages[-1]["content"]}
    async def scenario():
        app = Harness(Backend(), policy=Policy(mode="trusted"))
        app.use(Plugin("math", lambda c: c.tool(tool())))
        task = asyncio.create_task(app.arun("go"))
        await asyncio.sleep(0)
        with pytest.raises(RuntimeError):
            app.use(Plugin("other", lambda c: None))
        with pytest.raises(RuntimeError):
            await app.arun("again")
        assert await task == "2"
        with pytest.raises(RuntimeError):
            app.run("go")
        await app.aclose()
    run(scenario())


def test_shell_timeout_and_cancel(tmp_path):
    async def scenario():
        command = f'"{sys.executable}" -c "import time; time.sleep(30)"'
        with pytest.raises(TimeoutError):
            await shell(command, cwd=str(tmp_path), timeout=.1)
        task = asyncio.create_task(shell(command, cwd=str(tmp_path)))
        await asyncio.sleep(.1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    run(scenario())


def test_shell_output_is_bounded_while_draining(tmp_path, monkeypatch):
    monkeypatch.setenv("BASH_MAX_OUTPUT", "1000")
    command = f'"{sys.executable}" -c "print(\'x\' * 1000000); print(\'END\')"'
    result = run(shell(command, cwd=str(tmp_path)))
    assert result["exit_code"] == 0
    assert len(result["stdout"]) <= 1000 and "END" in result["stdout"]
