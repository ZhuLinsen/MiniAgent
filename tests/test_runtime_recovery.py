"""Regressions for interrupted effects, paired history and command status."""
import asyncio
import sys
from pathlib import Path

import pytest

from miniagent import Harness, Plugin
from miniagent.plugins import coding_tools, shell
from miniagent.policy import Policy
from miniagent.session import Session
from miniagent.tools.registry import Tool


def calls(*names):
    return {"role": "assistant", "content": None, "tool_calls": [
        {"id": name, "type": "function", "function": {"name": name, "arguments": "{}"}}
        for name in names]}


class Backend:
    def __init__(self, first):
        self.first, self.count = first, 0

    async def complete(self, messages, tools, stream):
        self.count += 1
        if self.count == 1:
            return self.first
        requested = {c["id"] for m in messages for c in m.get("tool_calls", [])}
        answered = {m["tool_call_id"] for m in messages if m["role"] == "tool"}
        assert requested == answered
        return {"role": "assistant", "content": "done"}


@pytest.mark.parametrize("persistent", [False, True])
def test_timeout_after_effect_blocks_remaining_tools_and_resume(tmp_path, persistent):
    async def scenario():
        marker = tmp_path / "effect"
        backend = Backend(calls("write", "later"))
        app = Harness(backend, policy=Policy(tmp_path, mode="trusted"),
                      session=Session(tmp_path / "session") if persistent else None)
        async def effect():
            command = f'"{sys.executable}" -c "from pathlib import Path; import time; Path(\'effect\').write_text(\'applied\'); time.sleep(30)"'
            return await shell(command, cwd=str(tmp_path), timeout=1)
        def later():
            pytest.fail("An uncertain effect must stop the rest of the tool batch")
        def setup(ctx):
            ctx.tool(Tool("write", "effect", {"type": "object"}, effect))
            ctx.tool(Tool("later", "later", {"type": "object"}, later))
        app.use(Plugin("tools", setup))
        with pytest.raises(RuntimeError, match="uncertain"):
            await app.arun("go")
        assert marker.read_text() == "applied"
        assert app.uncertain == {"write"}
        assert {m["tool_call_id"] for m in app.messages if m["role"] == "tool"} == {"write", "later"}
        with pytest.raises(RuntimeError, match="uncertain"):
            await app.arun("resume")
        assert backend.count == 1
        app.resolve("write", "Verified applied; do not repeat")
        assert await app.arun("continue") == "done"
        await app.aclose()
    asyncio.run(scenario())


@pytest.mark.parametrize("persistent", [False, True])
def test_cancelled_batch_is_paired_and_requires_resolution(tmp_path, persistent):
    async def scenario():
        began = asyncio.Event()
        async def effect():
            began.set()
            await asyncio.sleep(30)
        app = Harness(Backend(calls("write", "later")), policy=Policy(mode="trusted"),
                      session=Session(tmp_path / "session") if persistent else None)
        def setup(ctx):
            ctx.tool(Tool("write", "write", {"type": "object"}, effect))
            ctx.tool(Tool("later", "later", {"type": "object"}, lambda: None))
        app.use(Plugin("tools", setup))
        task = asyncio.create_task(app.arun("go"))
        await began.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert app.uncertain == {"write"}
        assert len([m for m in app.messages if m["role"] == "tool"]) == 2
        with pytest.raises(RuntimeError, match="uncertain"):
            await app.arun("resume")
        app.resolve("write", "Inspected effects")
        assert await app.arun("continue") == "done"
        await app.aclose()
    asyncio.run(scenario())


def test_denied_effect_does_not_require_resolution(tmp_path):
    async def scenario():
        app = Harness(Backend(calls("write")), policy=Policy(tmp_path, mode="readonly"))
        app.use(Plugin("tools", lambda ctx: ctx.tool(Tool("write", "write", {"type": "object"}, lambda: pytest.fail("Denied")))))
        assert await app.arun("go") == "done"
        assert not app.uncertain
        await app.aclose()
    asyncio.run(scenario())


def test_nonzero_shell_exit_emits_failed_status(tmp_path):
    async def scenario():
        import json
        message = calls("bash")
        message["tool_calls"][0]["function"]["arguments"] = json.dumps({"cmd": f'"{sys.executable}" -c "raise SystemExit(7)"'})
        app = Harness(Backend(message), policy=Policy(tmp_path, mode="trusted"))
        app.use(coding_tools())
        events = []
        app.use(Plugin("observer", lambda ctx: ctx.on("tool.end", events.append)))
        assert await app.arun("test") == "done"
        assert events[-1]["error"] is True
        assert not app.uncertain  # A nonzero exit is a known failure, not an interruption.
        await app.aclose()
    asyncio.run(scenario())


def test_added_tools_respect_and_survive_skill_switch():
    from miniagent.skills import get_skill
    async def scenario():
        app = Harness()
        app.use(Plugin("tools", lambda ctx: ctx.tool(Tool("read", "read", {"type": "object"}, lambda: None))))
        async with app:
            app.apply_skill(get_skill("reviewer"))
            app.active["tools"].tool(Tool("write", "write", {"type": "object"}, lambda: None))
            assert [t["function"]["name"] for t in app.registry.schemas()] == ["read"]
            app.apply_skill(get_skill("coder"))
            assert [t["function"]["name"] for t in app.registry.schemas()] == ["read", "write"]
            app.apply_skill(get_skill("reviewer"))
            assert [t["function"]["name"] for t in app.registry.schemas()] == ["read"]
    asyncio.run(scenario())


def test_sensitive_files_are_hidden_from_managed_read_search_and_glob(tmp_path):
    async def scenario():
        (tmp_path / ".env").write_text("secret=hidden")
        (tmp_path / ".env.production").write_text("secret=hidden")
        (tmp_path / ".env.example").write_text("example=safe")
        (tmp_path / "private.pem").write_text("secret=hidden")
        (tmp_path / "normal.txt").write_text("normal=safe")
        app = Harness(policy=Policy(tmp_path, mode="trusted")).use(coding_tools())
        async with app:
            for name in (".env", ".env.production", "private.pem"):
                with pytest.raises(PermissionError, match="Sensitive"):
                    await app.registry.execute("read", {"path": name}, app.policy)
            found = await app.registry.execute("grep", {"pattern": "secret"}, app.policy)
            assert found == []
            paths = await app.registry.execute("glob", {"pattern": "*"}, app.policy)
            assert {Path(p).name for p in paths} == {".env.example", "normal.txt"}
            app.policy.allow_sensitive_files = True
            assert "secret=hidden" in await app.registry.execute("read", {"path": ".env"}, app.policy)
    asyncio.run(scenario())


def test_file_tool_errors_are_explicit(tmp_path):
    async def scenario():
        app = Harness(policy=Policy(tmp_path)).use(coding_tools())
        async with app:
            result = await app.registry.execute("read", {"path": "missing"}, app.policy)
            assert result["isError"] is True
            assert result["content"].startswith("error:")
    asyncio.run(scenario())


def test_skill_iteration_limit_and_explicit_override():
    from miniagent.skills import Skill
    async def scenario():
        app = Harness(Backend(calls("add")), policy=Policy(mode="trusted"))
        app.use(Plugin("tools", lambda ctx: ctx.tool(Tool("add", "add", {"type": "object"}, lambda: 1))))
        app.apply_skill(Skill("limited", "Be concise", max_iterations=1))
        with pytest.raises(RuntimeError, match="max_steps"):
            await app.arun("go")
        app.backend = Backend(calls("next"))
        app.registry.add(Tool("next", "next", {"type": "object"}, lambda: 2))
        assert await app.arun("go", max_steps=2) == "done"
        await app.aclose()
    asyncio.run(scenario())
