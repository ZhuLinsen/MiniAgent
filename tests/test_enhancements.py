"""Tests for new agent enhancements: streaming, context mgmt, dangerous cmd check."""

import os
import re
import pytest
from unittest.mock import MagicMock, patch

# Test the dangerous command patterns
from miniagent.agent import _DANGEROUS_RE, _smart_truncate, MiniAgent


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
        assert _smart_truncate("hello", 100) == "hello"

    def test_long_text_preserves_tail(self):
        text = "START" + "x" * 10000 + "END_MARKER"
        result = _smart_truncate(text, 500)
        assert "END_MARKER" in result
        assert "START" in result
        assert "truncated" in result


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
