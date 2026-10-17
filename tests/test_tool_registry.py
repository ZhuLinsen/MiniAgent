"""Native registries own tools; callable metadata has no global registration."""
import asyncio
import importlib.util
import pytest
from jsonschema import ValidationError
from miniagent import Harness, Policy, Tool
from miniagent.plugins import coding_tools
from miniagent.tools import get_tool_description
from miniagent.tools.registry import Registry


def test_callable_description_does_not_register_globally():
    def search(name: str, count: int = 5):
        """Search by name."""
    description = get_tool_description(search)
    assert description["name"] == "search"
    assert description["parameters"]["required"] == ["name"]
    assert description["parameters"]["properties"]["count"] == {"type": "integer", "default": 5}
    import miniagent.tools as tools
    assert not hasattr(tools, "_TOOLS")


def test_registries_allow_independent_same_named_tools():
    async def scenario():
        first, second = Registry(), Registry()
        first.add(Tool("same", "first", {"type": "object"}, lambda: 1))
        second.add(Tool("same", "second", {"type": "object"}, lambda: 2))
        assert await first.execute("same", {}, Policy(mode="trusted")) == 1
        assert await second.execute("same", {}, Policy(mode="trusted")) == 2
    asyncio.run(scenario())


def test_native_coding_tools_and_schema_validate_before_execution(tmp_path):
    async def scenario():
        app = Harness(policy=Policy(tmp_path, mode="trusted")).use(coding_tools())
        started = []
        async with app:
            assert set(app.registry.tools) == {"read", "write", "edit", "grep", "glob", "bash"}
            with pytest.raises(ValidationError):
                await app.registry.execute("bash", {"cmd": "exit 0", "timeout": -1}, app.policy,
                                           on_start=lambda: started.append(True))
            assert not app.uncertain and not started
    asyncio.run(scenario())


@pytest.mark.parametrize("name", ["MiniAgent", "Memory", "Orchestrator", "load_mcp_tools"])
def test_retired_public_entries_explain_migration(name):
    import miniagent
    with pytest.raises(ImportError, match="legacy-pre-harness"):
        getattr(miniagent, name)


@pytest.mark.parametrize("name", ["legacy", "legacy_cli", "memory", "orchestrator", "tools.basic_tools", "utils.json_utils"])
def test_retired_implementations_are_absent_from_native_package(name):
    assert importlib.util.find_spec("miniagent." + name) is None
