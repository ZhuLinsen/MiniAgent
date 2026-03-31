"""Tests for type annotation parsing in get_tool_description()."""

from typing import List, Dict, Optional
import pytest
from miniagent.tools import register_tool, get_tool_description, _TOOLS


def _cleanup(name):
    """Remove a tool from the registry after the test."""
    _TOOLS.pop(name, None)


def test_list_str_mapped_to_array():
    """List[str] parameters must map to JSON schema 'array', not 'string'."""
    @register_tool
    def _tt_list_str(items: List[str]) -> str:
        """Test tool.\n\nArgs:\n    items: A list of strings"""
        return ""

    desc = get_tool_description(_tt_list_str)
    assert desc["parameters"]["properties"]["items"]["type"] == "array"
    _cleanup("_tt_list_str")


def test_list_int_mapped_to_array():
    """List[int] parameters must map to 'array'."""
    @register_tool
    def _tt_list_int(nums: List[int]) -> str:
        """Test tool.\n\nArgs:\n    nums: Numbers"""
        return ""

    desc = get_tool_description(_tt_list_int)
    assert desc["parameters"]["properties"]["nums"]["type"] == "array"
    _cleanup("_tt_list_int")


def test_dict_str_mapped_to_object():
    """Dict[str, Any] parameters must map to 'object'."""
    @register_tool
    def _tt_dict(data: Dict[str, str]) -> str:
        """Test tool.\n\nArgs:\n    data: Key-value pairs"""
        return ""

    desc = get_tool_description(_tt_dict)
    assert desc["parameters"]["properties"]["data"]["type"] == "object"
    _cleanup("_tt_dict")


def test_bool_not_confused_with_str():
    """bool contains 'o' not 'str' — should map to 'boolean'."""
    @register_tool
    def _tt_bool(flag: bool) -> str:
        """Test tool.\n\nArgs:\n    flag: A flag"""
        return ""

    desc = get_tool_description(_tt_bool)
    assert desc["parameters"]["properties"]["flag"]["type"] == "boolean"
    _cleanup("_tt_bool")


def test_plain_str():
    """Plain str should still be 'string'."""
    @register_tool
    def _tt_str(name: str) -> str:
        """Test tool.\n\nArgs:\n    name: A name"""
        return ""

    desc = get_tool_description(_tt_str)
    assert desc["parameters"]["properties"]["name"]["type"] == "string"
    _cleanup("_tt_str")


def test_plain_int():
    """Plain int should map to 'integer'."""
    @register_tool
    def _tt_int(n: int) -> str:
        """Test tool.\n\nArgs:\n    n: Number"""
        return ""

    desc = get_tool_description(_tt_int)
    assert desc["parameters"]["properties"]["n"]["type"] == "integer"
    _cleanup("_tt_int")


def test_float_mapped():
    """float should map to 'number'."""
    @register_tool
    def _tt_float(val: float) -> str:
        """Test tool.\n\nArgs:\n    val: A value"""
        return ""

    desc = get_tool_description(_tt_float)
    assert desc["parameters"]["properties"]["val"]["type"] == "number"
    _cleanup("_tt_float")
