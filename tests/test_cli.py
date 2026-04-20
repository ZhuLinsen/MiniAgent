"""Tests for CLI bootstrap behavior."""

from unittest.mock import patch

from miniagent import cli


@patch("miniagent.agent.MiniAgent._init_llm_client")
def test_main_strict_resolution_flag_exits_on_bootstrap_errors(_mock_init, monkeypatch):
    monkeypatch.setenv("MINIAGENT_HOME", "/tmp/miniagent-test-cli")

    exit_code = cli.main(["--api-key", "fake-key", "--strict-resolution"])

    assert exit_code == 1
