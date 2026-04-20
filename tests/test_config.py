"""Tests for config loading."""

import json
import os
import pytest
from miniagent.config import ProfileConfig, load_config


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

    def test_confirm_dangerous_true(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "k")
        monkeypatch.setenv("CONFIRM_DANGEROUS", "true")
        config = load_config()
        assert config.confirm_dangerous is True

    def test_confirm_dangerous_false(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "k")
        monkeypatch.setenv("CONFIRM_DANGEROUS", "false")
        config = load_config()
        assert config.confirm_dangerous is False

    def test_no_api_key_at_all(self, monkeypatch):
        """Config should still load when no API key is set."""
        for key in ("LLM_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        config = load_config()
        assert config.llm.api_key is None or config.llm.api_key == ""

    def test_profile_env_override(self, monkeypatch):
        monkeypatch.setenv("MINIAGENT_PROFILE", "crm_prod")
        config = load_config()
        assert config.profile == "crm_prod"

    def test_strict_resolution_env_override(self, monkeypatch):
        monkeypatch.setenv("STRICT_RESOLUTION", "true")
        config = load_config()
        assert config.strict_resolution is True

    def test_load_profiles_and_packs_from_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "k")
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "packs": ["miniagent_crm_pack"],
            "profile": "crm_prod",
            "default_skill": "crm_operator",
            "strict_resolution": True,
            "profiles": {
                "crm_prod": {
                    "packs": ["miniagent_crm_pack"],
                    "tools": ["crm_query_customer", "read"],
                    "skill": "crm_operator",
                    "system_prompt": "custom profile prompt",
                    "temperature": 0.2,
                }
            }
        }), encoding="utf-8")

        config = load_config(str(config_path))

        assert config.packs == ["miniagent_crm_pack"]
        assert config.profile == "crm_prod"
        assert config.default_skill == "crm_operator"
        assert config.strict_resolution is True
        assert isinstance(config.profiles["crm_prod"], ProfileConfig)
        assert config.profiles["crm_prod"].tools == ["crm_query_customer", "read"]
        assert config.profiles["crm_prod"].temperature == 0.2
