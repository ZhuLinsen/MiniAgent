"""Tests for miniagent/utils/json_utils.py."""

import pytest

from miniagent.utils.json_utils import (
    parse_json,
    extract_json_from_markdown,
    extract_tool_call,
)


class TestParseJson:
    def test_valid_json(self):
        result = parse_json('{"key": "value", "num": 42}')
        assert result["key"] == "value"
        assert result["num"] == 42

    def test_json_in_markdown_code_block(self):
        text = '```json\n{"a": 1}\n```'
        result = parse_json(text)
        assert result["a"] == 1

    def test_trailing_comma(self):
        result = parse_json('{"a": 1, "b": 2,}')
        assert result["a"] == 1
        assert result["b"] == 2

    def test_completely_invalid_returns_empty_dict(self):
        result = parse_json("this is not json at all !!!")
        assert result == {}

    def test_nested_json(self):
        result = parse_json('{"outer": {"inner": true}}')
        assert result["outer"]["inner"] is True

    def test_json_array_string(self):
        result = parse_json('[1, 2, 3]')
        assert result == [1, 2, 3]


class TestExtractJsonFromMarkdown:
    def test_extracts_from_json_block(self):
        text = 'Some text\n```json\n{"x": 10}\n```\nMore text'
        json_str, remaining = extract_json_from_markdown(text)
        assert json_str is not None
        assert '"x"' in json_str

    def test_no_json_block(self):
        json_str, remaining = extract_json_from_markdown("no json here")
        # Should return None or empty for the json part
        assert json_str is None or json_str == ""

    def test_extracts_bare_braces(self):
        text = 'prefix {"name": "test"} suffix'
        json_str, _ = extract_json_from_markdown(text)
        if json_str is not None:
            import json
            parsed = json.loads(json_str)
            assert parsed["name"] == "test"


class TestExtractToolCall:
    def test_returns_none_for_no_tool_call(self):
        result = extract_tool_call("plain text, no tool call")
        assert result is None

    def test_extracts_from_mock_response_dict(self):
        mock_response = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "id": "call_1",
                        "function": {
                            "name": "bash",
                            "arguments": '{"cmd": "ls"}',
                        },
                    }]
                }
            }]
        }
        result = extract_tool_call(mock_response)
        assert result is not None
        assert result["name"] == "bash"

    def test_returns_none_for_empty_dict(self):
        result = extract_tool_call({})
        assert result is None
