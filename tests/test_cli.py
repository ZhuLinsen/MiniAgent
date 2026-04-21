"""Tests for CLI bootstrap behavior."""

from unittest.mock import patch

from miniagent import cli


@patch("miniagent.agent.MiniAgent._init_llm_client")
def test_main_strict_resolution_flag_exits_on_bootstrap_errors(_mock_init, monkeypatch):
    monkeypatch.setenv("MINIAGENT_HOME", "/tmp/miniagent-test-cli")

    exit_code = cli.main(["--api-key", "fake-key", "--strict-resolution"])

    assert exit_code == 1


def test_stream_tool_detection_handles_special_tool_tokens():
    assert cli._looks_like_tool_call_stream(
        "I'll compute that<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>function<｜tool▁sep｜>calculator"
    ) is True
