"""Tests for config loading."""

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
        monkeypatch.setenv("LLM_MODEL", "openai:fixture-model")

        config = load_config()
        assert config.llm.api_key == "openai-fallback-key"

    def test_gemini_api_key_fallback(self, monkeypatch):
        """Gemini provider keys should work without copying them to LLM_API_KEY."""
        for key in ("LLM_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "gemini-fallback-key")
        monkeypatch.setenv("LLM_MODEL", "gemini:fixture-model")

        config = load_config()
        assert config.llm.api_key == "gemini-fallback-key"

    def test_google_api_base_does_not_guess_model(self, monkeypatch):
        monkeypatch.delenv("LLM_MODEL", raising=False)
        monkeypatch.setenv("LLM_API_KEY", "k")
        monkeypatch.setenv("LLM_API_BASE", "https://generativelanguage.googleapis.com/v1beta/openai/")

        config = load_config()
        assert config.llm.model == ""
        assert config.llm.api_key is None

    def test_default_values(self, monkeypatch):
        """With minimal env, config should still load with defaults."""
        monkeypatch.setenv("LLM_API_KEY", "k")
        config = load_config()
        assert config.llm.temperature >= 0
        assert config.llm.model is not None





    def test_no_api_key_at_all(self, monkeypatch):
        """Config should still load when no API key is set."""
        for key in (
            "LLM_API_KEY",
            "OPENAI_API_KEY",
            "DEEPSEEK_API_KEY",
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "ANTHROPIC_API_KEY",
            "AZURE_OPENAI_API_KEY",
        ):
            monkeypatch.delenv(key, raising=False)
        config = load_config()
        assert config.llm.api_key is None or config.llm.api_key == ""


@pytest.mark.parametrize("section,values", [
    ("agent", {"enable_reflection": True}), ("agent", {"default_tools": ["calculator"]}),
    ("llm", {"max_tokens": 10}), ("llm", {"max_retries": 3}),
])
def test_retired_or_unsupported_json_settings_fail_explicitly(tmp_path, section, values):
    import json
    path = tmp_path / "old.json"
    data = {"llm": values} if section == "llm" else values
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Unsupported settings"):
        load_config(str(path))


def test_temperature_uses_advertised_environment_and_json_override(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_TEMPERATURE", "0.25")
    assert load_config().llm.temperature == 0.25
    path = tmp_path / "config.json"
    path.write_text('{"llm":{"temperature":0.5}}')
    assert load_config(str(path)).llm.temperature == 0.5


def test_invalid_temperature_has_actionable_error(monkeypatch):
    monkeypatch.setenv("LLM_TEMPERATURE", "not-a-number")
    with pytest.raises(ValueError, match="temperature must be a"):
        load_config()


@pytest.mark.parametrize("value", ["", "not-a-number"])
def test_json_temperature_overrides_invalid_environment(value, tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_TEMPERATURE", value)
    path = tmp_path / "config.json"
    path.write_text('{"llm":{"temperature":0.5}}')
    assert load_config(str(path)).llm.temperature == 0.5


def test_empty_temperature_environment_uses_default(monkeypatch):
    monkeypatch.setenv("LLM_TEMPERATURE", "")
    assert load_config().llm.temperature == 0.7


def test_cli_temperature_overrides_invalid_lower_priority_values(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_TEMPERATURE", "not-a-number")
    path = tmp_path / "config.json"
    path.write_text('{"llm":{"temperature":"invalid"}}')
    assert load_config(str(path), temperature_override=0.25).llm.temperature == 0.25


@pytest.mark.parametrize("value", ['"invalid"', '{}', 'true', '"nan"', '"inf"'])
def test_invalid_effective_json_temperature_is_rejected(value, tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"llm":{"temperature":' + value + '}}')
    with pytest.raises(ValueError, match="temperature must be a"):
        load_config(str(path))


def test_null_json_temperature_keeps_provider_default(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_TEMPERATURE", "not-a-number")
    path = tmp_path / "config.json"
    path.write_text('{"llm":{"temperature":null}}')
    assert load_config(str(path)).llm.temperature is None
