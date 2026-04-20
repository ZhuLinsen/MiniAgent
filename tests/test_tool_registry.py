"""Tests for the tool registration system."""

import pytest
from miniagent.tools import (
    register_tool, get_registered_tools, get_tool,
    get_tool_description, get_tool_meta, clear_tools, _TOOLS, _TOOL_META,
)


def test_register_and_get():
    """Registered tools appear in the global registry."""
    @register_tool
    def _test_dummy(x: str) -> str:
        """A dummy tool."""
        return x

    assert "_test_dummy" in get_registered_tools()
    assert get_tool("_test_dummy") is _test_dummy

    # cleanup
    del _TOOLS["_test_dummy"]
    del _TOOL_META["_test_dummy"]


def test_get_tool_description_types():
    """get_tool_description extracts types and required fields correctly."""
    @register_tool
    def _test_desc(name: str, count: int = 5) -> str:
        """Search by name.\n\nArgs:\n    name: The name\n    count: Limit"""
        return ""

    desc = get_tool_description(_test_desc)
    assert desc["name"] == "_test_desc"
    assert "Search by name" in desc["description"]
    props = desc["parameters"]["properties"]
    assert props["name"]["type"] == "string"
    assert props["count"]["type"] == "integer"
    assert "name" in desc["parameters"]["required"]
    assert "count" not in desc["parameters"]["required"]

    del _TOOLS["_test_desc"]
    del _TOOL_META["_test_desc"]


def test_get_nonexistent_tool():
    assert get_tool("nonexistent_tool_xyz") is None


def test_builtin_tools_loaded():
    """Core tools should be auto-loaded on import."""
    tools = get_registered_tools()
    for name in ["calculator", "read", "write", "edit", "grep", "glob", "bash"]:
        assert name in tools, f"Built-in tool '{name}' not found in registry"


def test_builtin_tool_metadata_marks_source():
    meta = get_tool_meta("read")
    assert meta is not None
    assert meta.source == "builtin"
    assert meta.pack_name == "builtin"
    assert meta.module == "miniagent.tools.code_tools"


def test_runtime_tool_metadata_records_module():
    @register_tool
    def _test_runtime_meta(x: str) -> str:
        return x

    meta = get_tool_meta("_test_runtime_meta")
    assert meta is not None
    assert meta.source == "runtime"
    assert meta.module == __name__

    del _TOOLS["_test_runtime_meta"]
    del _TOOL_META["_test_runtime_meta"]


def test_register_tool_duplicate_raises():
    @register_tool
    def _test_duplicate_tool(x: str) -> str:
        return x

    with pytest.raises(ValueError, match="already registered"):
        register_tool(_test_duplicate_tool)

    del _TOOLS["_test_duplicate_tool"]
    del _TOOL_META["_test_duplicate_tool"]


def test_register_tool_allow_override_updates_metadata():
    @register_tool
    def _test_override_tool(x: str) -> str:
        return x

    @register_tool(allow_override=True)
    def _test_override_tool(x: str) -> str:
        return x.upper()

    assert get_tool("_test_override_tool")("a") == "A"
    meta = get_tool_meta("_test_override_tool")
    assert meta is not None
    assert meta.source == "runtime"

    del _TOOLS["_test_override_tool"]
    del _TOOL_META["_test_override_tool"]
