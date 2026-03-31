"""Tests for config loading."""

import os
import pytest
from miniagent.config import load_config


class TestLoadConfig:
    def test_load_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "test-key-123")
        monkeypatch.setenv("LLM_MODEL", "gpt-4")
        monkeypatch.setenv("LLM_API_BASE", "https://api.openai.com/v1")

        config = load_config()
        assert config.llm.api_key == "test-key-123"
        assert config.llm.model == "gpt-4"
        assert config.llm.api_base == "https://api.openai.com/v1"

    def test_fallback_api_keys(self, monkeypatch):
        """LLM_API_KEY not set — should fallback to OPENAI_API_KEY."""
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "openai-fallback-key")

        config = load_config()
        assert config.llm.api_key == "openai-fallback-key"

    def test_default_values(self, monkeypatch):
        """With minimal env, config should still load with defaults."""
        monkeypatch.setenv("LLM_API_KEY", "k")
        config = load_config()
        assert config.llm.temperature >= 0
        assert config.llm.model is not None

    def test_configurable_limits_defaults(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "k")
        config = load_config()
        assert config.bash_timeout == 120
        assert config.bash_max_output == 50000
        assert config.tool_result_limit == 16000

    def test_configurable_limits_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "k")
        monkeypatch.setenv("BASH_TIMEOUT", "300")
        monkeypatch.setenv("BASH_MAX_OUTPUT", "100000")
        monkeypatch.setenv("TOOL_RESULT_LIMIT", "32000")
        config = load_config()
        assert config.bash_timeout == 300
        assert config.bash_max_output == 100000
        assert config.tool_result_limit == 32000
