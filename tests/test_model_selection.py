"""Model selection precedes provider credential resolution and client startup."""
import asyncio
import io
import json

import pytest
from rich.console import Console

from miniagent.config import load_config
from tests.test_cli_runtime import options


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    import os
    for name in list(os.environ):
        if name.endswith(("_API_KEY", "_API_BASE", "_ENDPOINT")) or name == "LLM_MODEL":
            monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize("provider", ["deepseek", "dashscope", "anthropic", "openai"])
@pytest.mark.parametrize("model", [None, "  "])
def test_key_alone_cannot_select_model_or_start_client(provider, model, monkeypatch, tmp_path):
    from miniagent import cli_runtime
    monkeypatch.setenv(provider.upper() + "_API_KEY", "private-fixture-key")
    cfg = load_config()
    assert cfg.llm.model == "" and cfg.llm.api_key is None
    def unexpected(*args, **kwargs):
        pytest.fail("Missing model must fail before Harness/client/session creation")
    monkeypatch.setattr(cli_runtime, "Harness", unexpected)
    output = io.StringIO()
    assert asyncio.run(cli_runtime.cli_run(options(tmp_path, model=model),
        console=Console(file=output, width=160))) == 2
    assert "Model is required" in output.getvalue()
    assert "private-fixture-key" not in output.getvalue()
    assert not (tmp_path / "session").exists()


def test_final_model_controls_json_and_cli_credentials(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"llm": {"model": "anthropic:fixture"}}))
    monkeypatch.setenv("LLM_MODEL", "openai:fixture")
    for provider in ("openai", "anthropic", "deepseek"):
        monkeypatch.setenv(provider.upper() + "_API_KEY", provider + "-key")
        monkeypatch.setenv(provider.upper() + "_API_BASE", "https://" + provider + ".invalid")
    cfg = load_config(str(path))
    assert (cfg.llm.model, cfg.llm.api_key, cfg.llm.api_base) == (
        "anthropic:fixture", "anthropic-key", "https://anthropic.invalid")
    cfg = load_config(str(path), model_override="deepseek:fixture")
    assert (cfg.llm.model, cfg.llm.api_key, cfg.llm.api_base) == (
        "deepseek:fixture", "deepseek-key", "https://deepseek.invalid")


def test_unprefixed_model_does_not_borrow_unrelated_key(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "unrelated-key")
    monkeypatch.setenv("LLM_MODEL", "fixture")
    assert load_config().llm.api_key is None


def test_explicit_compatibility_credentials_are_preserved(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "gateway-key")
    cfg = load_config(model_override="openai:fixture", base_override="https://gateway.invalid/v6")
    assert cfg.llm.api_key == "gateway-key"
    assert cfg.llm.api_base == "https://gateway.invalid/v6"


def test_invalid_and_blank_models(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"llm": {"model": 42}}))
    with pytest.raises(ValueError, match="model must be a string"):
        load_config(str(path))
    assert load_config(model_override="  ").llm.model == ""


def test_legacy_missing_model_fails_before_client(tmp_path, monkeypatch):
    from miniagent import legacy_cli
    monkeypatch.setenv("DEEPSEEK_API_KEY", "private-fixture-key")
    with pytest.raises(SystemExit) as error:
        legacy_cli._build_agent(options(tmp_path, model=None))
    assert error.value.code == 2
