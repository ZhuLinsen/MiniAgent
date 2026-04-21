"""Tests for agent text-based tool call parsing."""

import pytest
from miniagent.agent import MiniAgent


@pytest.fixture
def agent():
    """Create a MiniAgent instance (LLM calls will not be made in these tests)."""
    return MiniAgent(
        model="test-model",
        api_key="test-key",
        base_url="http://localhost:9999",  # won't be called
    )


class TestParseToolCall:
    def test_standard_format(self, agent):
        content = 'Let me help you.\nTOOL: calculator\nARGS: {"expression": "2 + 2"}'
        result = agent._parse_tool_call(content)
        assert result is not None
        assert result["name"] == "calculator"
        assert result["arguments"]["expression"] == "2 + 2"

    def test_relaxed_format(self, agent):
        content = 'Tool: bash\nArgs: {"cmd": "ls -la"}'
        result = agent._parse_tool_call(content)
        assert result is not None
        assert result["name"] == "bash"
        assert result["arguments"]["cmd"] == "ls -la"

    def test_chinese_format(self, agent):
        content = '工具: calculator\n参数: {"expression": "1+1"}'
        result = agent._parse_tool_call(content)
        assert result is not None
        assert result["name"] == "calculator"

    def test_no_tool_call(self, agent):
        content = "This is just a regular response with no tool calls."
        result = agent._parse_tool_call(content)
        assert result is None

    def test_write_tool(self, agent):
        content = 'TOOL: write\nARGS: {"path": "test.py", "content": "print(\'hello\')"}'
        result = agent._parse_tool_call(content)
        assert result is not None
        assert result["name"] == "write"
        assert result["arguments"]["path"] == "test.py"

    def test_multiline_json(self, agent):
        content = '''TOOL: write
ARGS: {
    "path": "hello.py",
    "content": "line1\\nline2"
}'''
        result = agent._parse_tool_call(content)
        assert result is not None
        assert result["name"] == "write"

    def test_special_tool_token_format(self, agent):
        content = (
            "I'll compute that using the calculator tool:"
            "<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>function<｜tool▁sep｜>calculator\n"
            "```json\n"
            "{\"expression\": \"2 + 42\"}\n"
            "```"
        )
        result = agent._parse_tool_call(content)
        assert result is not None
        assert result["name"] == "calculator"
        assert result["arguments"]["expression"] == "2 + 42"


class TestExtractBalancedJson:
    def test_simple(self, agent):
        result = agent._extract_balanced_json('{"a": 1}')
        assert result == '{"a": 1}'

    def test_nested(self, agent):
        result = agent._extract_balanced_json('{"a": {"b": 2}}')
        assert result == '{"a": {"b": 2}}'

    def test_with_prefix(self, agent):
        result = agent._extract_balanced_json('some text {"key": "val"} more text')
        assert result == '{"key": "val"}'

    def test_no_json(self, agent):
        result = agent._extract_balanced_json('no json here')
        assert result is None
