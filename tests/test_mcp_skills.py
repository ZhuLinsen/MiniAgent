import asyncio
from pathlib import Path
import sys

import pytest
import psutil

from miniagent import Harness
from miniagent.extensions.mcp_plugin import mcp_plugin
from miniagent.plugins import coding_tools
from miniagent.policy import Policy
from miniagent.skills import get_skill, read_skill


def test_skill_switch_restores_tools_and_enforces_execution(tmp_path):
    async def scenario():
        app = Harness(policy=Policy(tmp_path, mode="trusted")).use(coding_tools())
        await app.start()
        app.apply_skill(get_skill("reviewer"))
        with pytest.raises(PermissionError):
            await app.registry.execute("write", {"path": "file", "content": "secret"}, app.policy)
        app.apply_skill(get_skill("coder"))
        assert await app.registry.execute("write", {"path": "file", "content": "ok"}, app.policy) == "ok"
        app.apply_skill()
        assert len(app.registry.schemas()) == 6
        await app.aclose()
    asyncio.run(scenario())


def test_skill_file(tmp_path):
    path = tmp_path / "SKILL.md"
    path.write_text('---\nname: test\nallowed-tools: ["read", "grep"]\n---\nRead before changing.')
    skill = read_skill(path)
    assert skill.tools == ["read", "grep"]
    assert skill.prompt == "Read before changing."


def test_mcp_real_stdio_denial_call_cleanup():
    pytest.importorskip("mcp")
    async def scenario():
        app = Harness(policy=Policy(mode="confirm"))
        app.use(mcp_plugin("local", sys.executable, [str(Path(__file__).parent / "fixtures/mcp_server.py")]))
        await app.start()
        assert "local__add" in app.registry.tools
        with pytest.raises(PermissionError):
            await app.registry.execute("local__add", {"a": 2, "b": 3}, app.policy)
        app.policy.mode = "trusted"
        result = await app.registry.execute("local__add", {"a": 2, "b": 3}, app.policy)
        assert result["structuredContent"]["sum"] == 5
        pid = result["structuredContent"]["pid"]
        # Enter and exit from separate tasks: SDK context remains in its owner task.
        await asyncio.create_task(app.unuse("mcp:local"))
        assert not app.registry.tools and not app.services
        assert not psutil.pid_exists(pid)
    asyncio.run(scenario())
