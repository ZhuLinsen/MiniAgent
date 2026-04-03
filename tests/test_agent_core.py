"""Tests for core Agent functionality with mocked LLM."""

from unittest.mock import Mock, patch, MagicMock
import pytest

from miniagent.agent import MiniAgent


@pytest.fixture
def agent():
    """Create an agent with a mocked OpenAI client."""
    with patch("miniagent.agent.MiniAgent._init_llm_client"):
        a = MiniAgent(model="test-model", api_key="fake-key")
        a.client = Mock()
        # Give it a simple tool
        a.tools = [{
            "name": "calculator",
            "description": "Calculate an expression",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
            "executor": lambda expression: str(eval(expression)),
        }]
        return a


def test_execute_tool_success(agent):
    """_execute_tool should call the executor and return the result."""
    tool_call = {"name": "calculator", "arguments": {"expression": "2+3"}}
    result = agent._execute_tool(tool_call)
    assert result == "5"


def test_execute_tool_not_found(agent):
    """_execute_tool returns error string for unknown tool."""
    tool_call = {"name": "nonexistent", "arguments": {}}
    result = agent._execute_tool(tool_call)
    assert "not found" in result.lower()


def test_execute_tool_exception(agent):
    """_execute_tool returns error string when executor raises."""
    tool_call = {"name": "calculator", "arguments": {"expression": "1/0"}}
    result = agent._execute_tool(tool_call)
    assert "error" in result.lower()


def test_execute_tool_callback(agent):
    """_execute_tool fires start/end callbacks."""
    cb = Mock()
    tool_call = {"name": "calculator", "arguments": {"expression": "1+1"}}
    agent._execute_tool(tool_call, tool_callback=cb)
    assert cb.call_count == 2
    assert cb.call_args_list[0][0][0] == "start"
    assert cb.call_args_list[1][0][0] == "end"


def test_compress_if_needed_no_compress(agent):
    """Short message list should not be compressed."""
    msgs = [{"role": "user", "content": f"msg{i}"} for i in range(5)]
    result = agent._compress_if_needed(msgs, 20)
    assert len(result) == 5


def test_compress_if_needed_triggers(agent):
    """Long message list should be compressed."""
    msgs = [{"role": "system", "content": "sys"}]
    msgs += [{"role": "user", "content": f"msg{i}"} for i in range(25)]
    result = agent._compress_if_needed(msgs, 10)
    assert len(result) < len(msgs)


def test_check_dangerous_disabled(agent):
    """With confirm_dangerous=False, all commands pass."""
    agent.confirm_dangerous = False
    result = agent._check_dangerous({"name": "bash", "arguments": {"cmd": "rm -rf /"}})
    assert result is True


def test_check_dangerous_non_bash(agent):
    """Non-bash tools always pass danger check."""
    agent.confirm_dangerous = True
    result = agent._check_dangerous({"name": "calculator", "arguments": {}})
    assert result is True


def test_check_dangerous_safe_cmd(agent):
    """Safe bash commands pass danger check."""
    agent.confirm_dangerous = True
    result = agent._check_dangerous({"name": "bash", "arguments": {"cmd": "echo hello"}})
    assert result is True


def test_check_dangerous_blocked(agent):
    """Dangerous cmd is blocked when callback rejects."""
    agent.confirm_dangerous = True
    agent.confirm_callback = lambda cmd: False
    result = agent._check_dangerous({"name": "bash", "arguments": {"cmd": "rm -rf /"}})
    assert result is False


def test_check_dangerous_allowed(agent):
    """Dangerous cmd proceeds when callback approves."""
    agent.confirm_dangerous = True
    agent.confirm_callback = lambda cmd: True
    result = agent._check_dangerous({"name": "bash", "arguments": {"cmd": "rm -rf /"}})
    assert result is True


def test_build_tools_prompt(agent):
    """_build_tools_prompt should include registered tool names."""
    prompt = agent._build_tools_prompt()
    assert "calculator" in prompt
    assert "expression" in prompt


def test_parse_tool_call_valid(agent):
    """_parse_tool_call should extract TOOL and ARGS from text."""
    text = 'TOOL: calculator\nARGS: {"expression": "2+2"}'
    result = agent._parse_tool_call(text)
    assert result is not None
    assert result["name"] == "calculator"
    assert result["arguments"]["expression"] == "2+2"


def test_parse_tool_call_no_tool(agent):
    """_parse_tool_call returns None for plain text."""
    result = agent._parse_tool_call("Just a regular answer with no tool call.")
    assert result is None


def test_safe_execute_tool_rejected(agent):
    """_safe_execute_tool returns (None, True) when dangerous cmd is rejected."""
    agent.confirm_dangerous = True
    agent.confirm_callback = lambda cmd: False
    tc = {"name": "bash", "arguments": {"cmd": "rm -rf /"}}
    result, rejected = agent._safe_execute_tool(tc, None, None, 16000)
    assert rejected is True
    assert result is None


def test_detect_direct_endpoint_by_suffix():
    """A single POST endpoint should be treated as a direct chat endpoint."""
    with patch("miniagent.agent.MiniAgent._init_llm_client"):
        agent = MiniAgent(
            model="DeepSeek-R1",
            api_key="fake-key",
            base_url="https://example.com/publicService",
        )

    assert agent._use_direct_chat_endpoint() is True


def test_call_llm_direct_endpoint_uses_requests_post():
    """Direct endpoint mode should POST to the exact configured URL."""
    with patch("miniagent.agent.MiniAgent._init_llm_client"), patch("miniagent.agent.requests.post") as mock_post:
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "hello from gateway"}}]
        }
        mock_post.return_value = mock_response

        agent = MiniAgent(
            model="DeepSeek-R1",
            api_key="fake-key",
            base_url="https://example.com/publicService",
        )

        result = agent._call_llm([{"role": "user", "content": "hi"}])

    assert result == "hello from gateway"
    mock_post.assert_called_once()
    assert mock_post.call_args.args[0] == "https://example.com/publicService"
    assert mock_post.call_args.kwargs["headers"]["Authorization"] == "Bearer fake-key"
    assert mock_post.call_args.kwargs["json"]["model"] == "DeepSeek-R1"
    assert mock_post.call_args.kwargs["json"]["messages"][0]["content"] == "hi"


def test_call_llm_stream_direct_endpoint_yields_single_chunk():
    """Streaming should degrade gracefully when only a direct endpoint exists."""
    with patch("miniagent.agent.MiniAgent._init_llm_client"), patch("miniagent.agent.requests.post") as mock_post:
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "stream fallback"}}]
        }
        mock_post.return_value = mock_response

        agent = MiniAgent(
            model="DeepSeek-R1",
            api_key="fake-key",
            base_url="https://example.com/publicService",
        )

        chunks = list(agent._call_llm_stream([{"role": "user", "content": "hi"}]))

    assert chunks == ["stream fallback"]


def test_native_tools_fall_back_to_text_mode_for_direct_endpoint():
    """Native FC should fall back to text mode for single-endpoint gateways."""
    with patch("miniagent.agent.MiniAgent._init_llm_client"):
        agent = MiniAgent(
            model="DeepSeek-R1",
            api_key="fake-key",
            base_url="https://example.com/publicService",
        )

    agent.run_with_tools = Mock(return_value="fallback response")
    result = agent.run_with_native_tools("hi")

    assert result == "fallback response"
    agent.run_with_tools.assert_called_once()
