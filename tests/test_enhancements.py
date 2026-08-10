"""Tests for new agent enhancements: streaming, context mgmt, dangerous cmd check."""

import os
import re
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# Test the dangerous command patterns
from miniagent.agent import _DANGEROUS_RE, MiniAgent
from miniagent.utils.text_utils import smart_truncate


class TestDangerousPatterns:
    def test_rm_rf(self):
        assert _DANGEROUS_RE.search("rm -rf /tmp/data")
    
    def test_rm_force(self):
        assert _DANGEROUS_RE.search("rm --force file.txt")

    def test_sudo(self):
        assert _DANGEROUS_RE.search("sudo apt install vim")

    def test_safe_ls(self):
        assert not _DANGEROUS_RE.search("ls -la /tmp")

    def test_safe_echo(self):
        assert not _DANGEROUS_RE.search("echo hello world")

    def test_safe_rm_single(self):
        assert not _DANGEROUS_RE.search("rm file.txt")

    def test_shutdown(self):
        assert _DANGEROUS_RE.search("shutdown -h now")

    def test_mkfs(self):
        assert _DANGEROUS_RE.search("mkfs.ext4 /dev/sda1")

    def test_dd(self):
        assert _DANGEROUS_RE.search("dd if=/dev/zero of=/dev/sda")


class TestContextManagement:
    def test_short_conversation_unchanged(self):
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        result = MiniAgent._summarize_messages(messages, keep_last=6)
        assert result == messages  # unchanged

    def test_long_conversation_compressed(self):
        messages = [{"role": "system", "content": "system prompt"}]
        for i in range(20):
            messages.append({"role": "user", "content": f"question {i}"})
            messages.append({"role": "assistant", "content": f"answer {i}"})
        
        result = MiniAgent._summarize_messages(messages, keep_last=6)
        # Should be: system + summary + last 6 messages = 8
        assert len(result) == 8
        assert result[0]["role"] == "system"
        assert "summary" in result[1]["content"].lower()
        assert result[-1]["content"] == "answer 19"

    def test_summary_preserves_recent(self):
        messages = [{"role": "system", "content": "sys"}]
        for i in range(30):
            messages.append({"role": "user", "content": f"q{i}"})
            messages.append({"role": "assistant", "content": f"a{i}"})
        
        result = MiniAgent._summarize_messages(messages, keep_last=4)
        # Last 4 messages should be q29, a29, ... or similar
        recent_content = [m["content"] for m in result[-4:]]
        assert "a29" in recent_content
        assert "q29" in recent_content


class TestSmartTruncate:
    def test_short_text_unchanged(self):
        assert smart_truncate("hello", 100) == "hello"

    def test_long_text_preserves_tail(self):
        text = "START" + "x" * 10000 + "END_MARKER"
        result = smart_truncate(text, 500)
        assert "END_MARKER" in result
        assert "START" in result
        assert "truncated" in result

    def test_very_small_limit(self):
        """smart_truncate with limit < 100 should not produce negative tail_size."""
        text = "A" * 200
        result = smart_truncate(text, 50)
        assert len(result) <= 54  # 50 + "..."
        assert result.endswith("...")

    def test_limit_exactly_100(self):
        text = "B" * 300
        result = smart_truncate(text, 100)
        assert "truncated" in result
        assert len(result) < 300


class TestCheckDangerous:
    @patch("miniagent.agent.MiniAgent._init_llm_client")
    def test_safe_command_passes(self, mock_init):
        agent = MiniAgent.__new__(MiniAgent)
        agent.confirm_dangerous = True
        agent.confirm_callback = None
        
        tool_call = {"name": "bash", "arguments": {"cmd": "ls -la"}}
        assert agent._check_dangerous(tool_call) is True

    @patch("miniagent.agent.MiniAgent._init_llm_client")
    def test_dangerous_rejected(self, mock_init):
        agent = MiniAgent.__new__(MiniAgent)
        agent.confirm_dangerous = True
        agent.confirm_callback = lambda cmd: False  # always reject
        
        tool_call = {"name": "bash", "arguments": {"cmd": "rm -rf /"}}
        assert agent._check_dangerous(tool_call) is False

    @patch("miniagent.agent.MiniAgent._init_llm_client")
    def test_dangerous_accepted(self, mock_init):
        agent = MiniAgent.__new__(MiniAgent)
        agent.confirm_dangerous = True
        agent.confirm_callback = lambda cmd: True  # always accept
        
        tool_call = {"name": "bash", "arguments": {"cmd": "sudo rm -rf /tmp/old"}}
        assert agent._check_dangerous(tool_call) is True

    @patch("miniagent.agent.MiniAgent._init_llm_client")
    def test_non_bash_always_passes(self, mock_init):
        agent = MiniAgent.__new__(MiniAgent)
        agent.confirm_dangerous = True
        agent.confirm_callback = lambda cmd: False
        
        tool_call = {"name": "read", "arguments": {"path": "/etc/passwd"}}
        assert agent._check_dangerous(tool_call) is True

    @patch("miniagent.agent.MiniAgent._init_llm_client")
    def test_disabled_always_passes(self, mock_init):
        agent = MiniAgent.__new__(MiniAgent)
        agent.confirm_dangerous = False
        agent.confirm_callback = None
        
        tool_call = {"name": "bash", "arguments": {"cmd": "rm -rf /"}}
        assert agent._check_dangerous(tool_call) is True


class _FakeToolCall:
    """Minimal stand-in for openai ChatCompletionMessageToolCall."""

    def __init__(self, call_id: str, name: str = "bash", arguments: str = "{}"):
        self.id = call_id
        self.type = "function"
        self.function = SimpleNamespace(name=name, arguments=arguments)


class _FakeMessage:
    """Minimal stand-in for openai.ChatCompletionMessage (attributes, not dict)."""

    def __init__(self, role: str, content: str, tool_calls=None):
        self.role = role
        self.content = content
        self.tool_calls = tool_calls


class TestContextManagementNativeFC:
    """Native FC mode appends OpenAI message objects (not dicts) to history.

    Context compression must handle both dicts and message objects without
    crashing when the conversation exceeds MAX_CONTEXT_MESSAGES.
    """

    def test_summarize_handles_mixed_dict_and_object_messages(self):
        messages = [{"role": "system", "content": "system prompt"}]
        for i in range(20):
            messages.append({"role": "user", "content": f"question {i}"})
            messages.append(_FakeMessage("assistant", f"answer {i}"))
            messages.append({"role": "tool", "content": f"result {i}"})

        result = MiniAgent._summarize_messages(messages, keep_last=6)
        # Compressed, system preserved, and no crash on message objects
        assert len(result) < len(messages)
        assert result[0]["role"] == "system"
        assert "summary" in result[1]["content"].lower()
        assert result[-1]["content"] == "result 19"

    def test_summarize_mixed_below_threshold_unchanged(self):
        messages = [{"role": "system", "content": "sys"}]
        messages.append({"role": "user", "content": "hi"})
        messages.append(_FakeMessage("assistant", "hello"))

        result = MiniAgent._summarize_messages(messages, keep_last=6)
        assert result is messages  # unchanged below threshold


def _assert_no_orphan_tool_messages(messages):
    """Every tool message must be preceded by the assistant(tool_calls) owning it."""
    open_ids = set()
    for m in messages:
        role = m["role"] if isinstance(m, dict) else m.role
        if role == "assistant":
            tool_calls = m.get("tool_calls") if isinstance(m, dict) else getattr(m, "tool_calls", None)
            open_ids = {tc.id for tc in (tool_calls or [])}
        elif role == "tool":
            call_id = m["tool_call_id"] if isinstance(m, dict) else m.tool_call_id
            assert call_id in open_ids, (
                f"orphaned tool message {call_id!r}: no preceding assistant(tool_calls) "
                f"in compressed history"
            )
        else:
            open_ids = set()


def _native_fc_turn(index: int, n_calls: int):
    """Build one realistic native FC turn.

    user -> assistant(tool_calls=[n parallel calls]) -> n tool responses
    """
    calls = [_FakeToolCall(f"call_{index}_{j}", name="bash") for j in range(n_calls)]
    turn = [
        {"role": "user", "content": f"question {index}"},
        _FakeMessage("assistant", None, tool_calls=calls),
    ]
    for tc in calls:
        turn.append({"role": "tool", "tool_call_id": tc.id, "content": f"result {tc.id}"})
    return turn


class TestNativeFCToolCallGroupIntegrity:
    """Compression must never split an assistant(tool_calls) -> tool responses group.

    The OpenAI API rejects a request containing a `tool` message that is not
    preceded by the `assistant` message with the matching `tool_calls`, so a
    truncation boundary landing inside a parallel tool-call group would break
    the very next request.
    """

    def test_parallel_tool_calls_not_orphaned(self):
        messages = [{"role": "system", "content": "system prompt"}]
        for i in range(6):
            messages.extend(_native_fc_turn(i, n_calls=3))

        # keep_last=3 lands the naive boundary inside the last group's tool
        # responses (group = 1 assistant + 3 tool messages).
        result = MiniAgent._summarize_messages(messages, keep_last=3)

        assert len(result) < len(messages)  # actually compressed
        _assert_no_orphan_tool_messages(result)
        # The boundary walked back to the assistant that owns the kept tools.
        first_after_summary = result[2]
        assert getattr(first_after_summary, "role", None) == "assistant"
        assert getattr(first_after_summary, "tool_calls", None)

    @pytest.mark.parametrize("keep_last", list(range(1, 13)))
    def test_no_orphans_for_any_boundary(self, keep_last):
        """Every boundary must produce a valid sequence, not just a lucky one."""
        messages = [{"role": "system", "content": "system prompt"}]
        for i in range(5):
            messages.extend(_native_fc_turn(i, n_calls=2))

        result = MiniAgent._summarize_messages(messages, keep_last=keep_last)
        _assert_no_orphan_tool_messages(result)
        assert result[0]["role"] == "system"

    @pytest.mark.parametrize("n_calls", [1, 2, 5])
    def test_group_kept_intact_for_varying_parallel_widths(self, n_calls):
        messages = [{"role": "system", "content": "sys"}]
        for i in range(5):
            messages.extend(_native_fc_turn(i, n_calls=n_calls))

        result = MiniAgent._summarize_messages(messages, keep_last=2)
        _assert_no_orphan_tool_messages(result)

        # All tool responses kept must belong to the assistant group kept with them.
        kept_tool_ids = {
            m["tool_call_id"] for m in result
            if isinstance(m, dict) and m.get("role") == "tool"
        }
        kept_call_ids = set()
        for m in result:
            for tc in (getattr(m, "tool_calls", None) or []):
                kept_call_ids.add(tc.id)
        assert kept_tool_ids <= kept_call_ids

    def test_summary_still_produced_when_boundary_moves(self):
        """Walking the boundary back must not disable compression entirely."""
        messages = [{"role": "system", "content": "sys"}]
        for i in range(8):
            messages.extend(_native_fc_turn(i, n_calls=3))

        result = MiniAgent._summarize_messages(messages, keep_last=3)
        assert result[0]["role"] == "system"
        assert "summary" in result[1]["content"].lower()

    def test_orphan_tool_messages_dropped_as_last_resort(self):
        """A tool message whose assistant parent is gone must be removed."""
        orphan_history = [
            {"role": "tool", "tool_call_id": "call_x", "content": "orphan result"},
            {"role": "user", "content": "next question"},
        ]
        cleaned = MiniAgent._drop_orphan_tool_messages(orphan_history)
        assert all(
            (m["role"] if isinstance(m, dict) else m.role) != "tool" for m in cleaned
        )
        _assert_no_orphan_tool_messages(cleaned)

    def test_text_mode_history_unaffected(self):
        """Plain user/assistant history keeps the exact keep_last window."""
        messages = [{"role": "system", "content": "sys"}]
        for i in range(20):
            messages.append({"role": "user", "content": f"q{i}"})
            messages.append({"role": "assistant", "content": f"a{i}"})

        result = MiniAgent._summarize_messages(messages, keep_last=6)
        assert len(result) == 8  # system + summary + 6
        assert result[-1]["content"] == "a19"


class TestCallLLMErrorHandling:
    @patch("miniagent.agent.MiniAgent._init_llm_client")
    def test_missing_api_key_raises_clear_error(self, mock_init):
        """Missing API key must raise a clear ValueError, not a TypeError."""
        agent = MiniAgent.__new__(MiniAgent)
        agent.api_key = None
        agent.model = "test-model"
        agent.base_url = None
        agent.temperature = 0.7
        agent.client = MagicMock()
        agent.use_reflector = False
        agent.reflector = None

        # Call the unwrapped function to avoid tenacity retry delays
        raw = getattr(MiniAgent._call_llm, "__wrapped__", MiniAgent._call_llm)
        with pytest.raises(ValueError, match="API key is not set"):
            raw(agent, [{"role": "user", "content": "hi"}])
