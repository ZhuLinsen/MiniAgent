"""Tests for the tool registration system."""

import pytest
from miniagent.tools import (
    register_tool, get_registered_tools, get_tool,
    get_tool_description, clear_tools, _TOOLS,
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


def test_get_nonexistent_tool():
    assert get_tool("nonexistent_tool_xyz") is None


def test_builtin_tools_loaded():
    """Core tools should be auto-loaded on import."""
    tools = get_registered_tools()
    for name in ["calculator", "read", "write", "edit", "grep", "glob", "bash"]:
        assert name in tools, f"Built-in tool '{name}' not found in registry"
