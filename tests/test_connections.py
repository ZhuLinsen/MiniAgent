import asyncio
import io
import json
import sys
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, Mock

import pytest
from rich.console import Console

from miniagent import connections as c
from miniagent.config import load_config
from tests.test_cli_runtime import options


@pytest.fixture
def console():
    return Console(file=io.StringIO(), width=180)


def answers(monkeypatch, values):
    values = iter(values)
    calls = []
    def ask(label, **kwargs):
        calls.append((label, kwargs))
        return next(values)
    monkeypatch.setattr(c.Prompt, "ask", ask)
    return calls


def test_custom_connect_no_plaintext_secret_and_restart_metadata(monkeypatch, console):
    calls = answers(monkeypatch, ["custom", "myapi", "https://gateway.invalid/v6", "fixture-secret", "selected"])
    monkeypatch.setattr(c, "_vault", Mock(side_effect=RuntimeError))
    monkeypatch.setattr(c, "discover", AsyncMock(return_value=[]))
    assert asyncio.run(c.connect(console, load_config())) == "myapi:selected"
    text = (c.home() / "connections.json").read_text()
    assert "fixture-secret" not in text and "fixture-secret" not in console.file.getvalue()
    assert any(kwargs.get("password") for _, kwargs in calls)
    cfg = load_config()
    assert cfg.llm.model == "myapi:selected" and cfg.llm.api_key == "fixture-secret"
    assert cfg.providers["myapi"]["base_url"] == "https://gateway.invalid/v6"
    c._secrets.clear()  # simulate restart with no OS vault
    assert load_config().llm.api_key is None
    assert "only in this process" in console.file.getvalue()


def test_env_profile_json_cli_precedence(monkeypatch, tmp_path):
    c.save_model("deepseek", "saved")
    monkeypatch.setenv("LLM_MODEL", "openai:environment")
    assert load_config().llm.model == "openai:environment"
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"llm": {"model": "anthropic:file"}}))
    assert load_config(str(path)).llm.model == "anthropic:file"
    assert load_config(str(path), model_override="dashscope:cli").llm.model == "dashscope:cli"


def test_os_vault_persistence_and_env_override(monkeypatch):
    vault = NS(set_password=Mock(), get_password=Mock(return_value="vault-secret"))
    monkeypatch.setattr(c, "_vault", lambda: vault)
    assert c.store_credential("DEEPSEEK_API_KEY", "typed-secret")
    vault.set_password.assert_called_once_with("miniagent", "DEEPSEEK_API_KEY", "typed-secret")
    c._secrets.clear()
    c.save_model("deepseek", "saved")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("LLM_MODEL", "deepseek:saved")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert load_config().llm.api_key == "vault-secret"
    monkeypatch.setenv("DEEPSEEK_API_KEY", "environment-secret")
    assert load_config().llm.api_key == "environment-secret"


def test_reject_insecure_vault(monkeypatch):
    class Plaintext:
        pass
    Plaintext.__module__ = "keyrings.alt.file"
    monkeypatch.setitem(sys.modules, "keyring", NS(get_keyring=lambda: Plaintext()))
    with pytest.raises(RuntimeError, match="No supported"):
        c._vault()


@pytest.mark.parametrize("base", ["https://key:password@host/v1", "https://host/v1?key=secret",
                                 "https://host/v1#secret", "file:///tmp/api", "https://host/\nsecret"])
def test_reject_credential_bearing_or_invalid_urls(base):
    with pytest.raises(ValueError):
        c._base(base)


def test_cancel_and_invalid_models_leave_no_profile(monkeypatch, console):
    monkeypatch.setattr(c.Prompt, "ask", Mock(side_effect=EOFError))
    with pytest.raises(EOFError):
        asyncio.run(c.connect(console, load_config()))
    assert not (c.home() / "connections.json").exists()
    with pytest.raises(ValueError):
        c.save_model("deepseek", "")


def test_profile_rejects_secret_fields_and_preserves_corrupt_file():
    path = c.home() / "connections.json"
    path.parent.mkdir(parents=True)
    original = '{"api_key":"should-not-be-accepted"}'
    path.write_text(original)
    with pytest.raises(ValueError, match="Invalid connections"):
        c.save_model("openai", "model")
    assert path.read_text() == original


def test_model_discovery_timeout_fallback_and_cleanup(monkeypatch, console):
    async def listing():
        raise TimeoutError
    raw = NS(close=AsyncMock())
    client = NS(alist_models=listing, client=raw)
    monkeypatch.setattr(c, "provider_client", lambda *a, **kw: client)
    assert asyncio.run(c.discover(console, "openai", providers={}, api_key="not-printed")) == []
    raw.close.assert_awaited_once()
    assert "not-printed" not in console.file.getvalue()


def test_listing_filters_credentials(monkeypatch, console):
    raw = NS(close=AsyncMock())
    client = NS(alist_models=AsyncMock(return_value=[NS(id="safe"), NS(id="private-key")]), client=raw)
    monkeypatch.setattr(c, "provider_client", lambda *a, **kw: client)
    assert asyncio.run(c.discover(console, "openai", providers={}, api_key="private-key")) == ["safe"]


def test_models_selects_and_remembers_manual_model(monkeypatch, console):
    c.save_model("deepseek", "saved")
    monkeypatch.setenv("LLM_MODEL", "deepseek:saved")
    answers(monkeypatch, ["1", "manual"])
    monkeypatch.setattr(c, "discover", AsyncMock(return_value=[]))
    assert asyncio.run(c.select_model(console, load_config())) == "deepseek:manual"
    assert c.read_profiles()["models"]["deepseek"] == ["manual", "saved"]


def test_first_run_guide_and_explicit_config_exit(monkeypatch, tmp_path, console):
    from miniagent import cli_runtime
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(cli_runtime, "connect", AsyncMock(return_value="openai:chosen"))
    monkeypatch.setattr(cli_runtime, "Harness", Mock(side_effect=AssertionError("No client for configuration only")))
    assert asyncio.run(cli_runtime.cli_run(options(tmp_path, model=None, connect=True), console=console)) == 0


def test_first_run_without_model_enters_guide(monkeypatch, tmp_path, console):
    from miniagent import cli_runtime
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    guide = AsyncMock(side_effect=EOFError)
    monkeypatch.setattr(cli_runtime, "connect", guide)
    assert asyncio.run(cli_runtime.cli_run(options(tmp_path, model=None, prompt=None), console=console)) == 130
    guide.assert_awaited_once()


def test_noninteractive_connect_never_prompts(monkeypatch, tmp_path, console):
    from miniagent import cli_runtime
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    guide = AsyncMock(side_effect=AssertionError("Do not prompt"))
    monkeypatch.setattr(cli_runtime, "connect", guide)
    assert asyncio.run(cli_runtime.cli_run(options(tmp_path, connect=True), console=console)) == 2
    guide.assert_not_called()


def test_switch_commands_close_clients_and_reset_session(monkeypatch, tmp_path, console):
    from miniagent import cli_runtime
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    answers(monkeypatch, ["/connect", "first", "/models", "second", "/q"])
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-key")
    monkeypatch.setattr(cli_runtime, "connect", AsyncMock(return_value="openai:first"))
    monkeypatch.setattr(cli_runtime, "select_model", AsyncMock(return_value="openai:second"))
    records = []
    class Backend:
        temperature = 0
        def __init__(self, model, **kwargs):
            self.model = model
        async def complete(self, messages, tools, stream):
            records.append((self.model, [m["content"] for m in messages if m["role"] == "user"]))
            return {"role": "assistant", "content": "ok"}
        async def aclose(self):
            records.append((self.model, "closed"))
    monkeypatch.setattr(cli_runtime, "LLMBackend", Backend)
    assert asyncio.run(cli_runtime.cli_run(options(tmp_path, prompt=None), console=console,
                                          backend=Backend("initial"))) == 0
    assert records == [("openai:first", ["first"]), ("openai:first", "closed"),
                       ("openai:second", ["second"]), ("openai:second", "closed")]


def test_provider_client_listing_uses_real_sdk_protocol(monkeypatch, console):
    import httpx
    from openai import AsyncOpenAI
    from miniagent.llm import provider_client
    requests = []
    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"object": "list", "data": [
            {"id": "listed-model", "object": "model", "created": 1, "owned_by": "fixture"}]})
    async def scenario():
        client = provider_client("fixture", providers={"fixture": {"type": "openai-compatible",
            "base_url": "https://fixture.invalid/v6", "api_key_env": "FIXTURE_API_KEY"}}, api_key="fixture-key")
        await client.client.close()
        transport = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        client.client = AsyncOpenAI(api_key="fixture-key", base_url="https://fixture.invalid/v6", http_client=transport)
        monkeypatch.setattr(c, "provider_client", lambda *a, **kw: client)
        assert await c.discover(console, "fixture", providers={}, api_key="fixture-key") == ["listed-model"]
        assert requests[0].method == "GET" and requests[0].url.path == "/v6/models"
        assert transport.is_closed
    asyncio.run(scenario())


def test_errors_redact_credentials(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "environment-secret")
    c._secrets["OTHER_KEY"] = "typed-secret"
    message = c.error_text(RuntimeError("environment-secret typed-secret explicit-secret"), "explicit-secret")
    assert message.count("[REDACTED]") == 3


def test_credential_cannot_be_saved_as_a_model(monkeypatch, console):
    answers(monkeypatch, ["deepseek", "secret-fixture", "secret-fixture"])
    monkeypatch.setattr(c, "discover", AsyncMock(return_value=[]))
    with pytest.raises(ValueError, match="Credential must not appear"):
        asyncio.run(c.connect(console, load_config()))
    assert not (c.home() / "connections.json").exists()


@pytest.mark.parametrize("env", ["GEMINI_API_KEY", "GOOGLE_API_KEY"])
def test_gemini_connect_keeps_existing_alias_and_models_reuses_it(monkeypatch, console, env):
    for name in ("LLM_API_KEY", "LLM_MODEL", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(env, "gemini-fixture-secret")
    monkeypatch.setattr(c.AnyLLM, "get_provider_class", lambda name: NS(
        ENV_API_KEY_NAME="GEMINI_API_KEY/GOOGLE_API_KEY"))
    listing = AsyncMock(return_value=[])
    monkeypatch.setattr(c, "discover", listing)
    answers(monkeypatch, ["gemini", "", "first"])
    assert asyncio.run(c.connect(console, load_config())) == "gemini:first"
    assert load_config().llm.api_key == "gemini-fixture-secret"
    answers(monkeypatch, ["gemini", "second"])
    assert asyncio.run(c.select_model(console, load_config())) == "gemini:second"
    assert listing.call_args.kwargs["api_key"] == "gemini-fixture-secret"


def test_gemini_typed_key_survives_restart_in_canonical_vault_account(monkeypatch, console):
    for name in ("LLM_API_KEY", "LLM_MODEL", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    stored = {}
    vault = NS(set_password=lambda service, name, value: stored.update({name: value}),
               get_password=lambda service, name: stored.get(name))
    monkeypatch.setattr(c, "_vault", lambda: vault)
    monkeypatch.setattr(c.AnyLLM, "get_provider_class", lambda name: NS(
        ENV_API_KEY_NAME="GEMINI_API_KEY/GOOGLE_API_KEY"))
    monkeypatch.setattr(c, "discover", AsyncMock(return_value=[]))
    answers(monkeypatch, ["gemini", "new-gemini-secret", "selected"])
    asyncio.run(c.connect(console, load_config()))
    assert stored == {"GEMINI_API_KEY": "new-gemini-secret"}
    c._secrets.clear()
    assert load_config().llm.api_key == "new-gemini-secret"
    assert "new-gemini-secret" not in (c.home() / "connections.json").read_text()
    assert "new-gemini-secret" not in console.file.getvalue()


def test_models_rejects_credential_without_changing_saved_profile(monkeypatch, console):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("LLM_MODEL", "deepseek:original")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fixture-private-secret")
    c.save_model("deepseek", "original")
    path = c.home() / "connections.json"
    before = path.read_bytes()
    monkeypatch.setattr(c, "discover", AsyncMock(return_value=[]))
    answers(monkeypatch, ["deepseek", "fixture-private-secret"])
    with pytest.raises(ValueError, match="Credential must not appear"):
        asyncio.run(c.select_model(console, load_config()))
    assert path.read_bytes() == before
    assert "fixture-private-secret" not in console.file.getvalue()


def test_explicit_home_does_not_require_system_home(monkeypatch, tmp_path):
    explicit = tmp_path / "explicit-home"
    monkeypatch.setenv("MINIAGENT_HOME", str(explicit))
    monkeypatch.setattr(c.Path, "home", Mock(side_effect=RuntimeError("No system home")))
    assert c.home() == explicit
    c.save_model("deepseek", "fixture")
    assert load_config().llm.model == "deepseek:fixture"


def test_gemini_legacy_combined_vault_account_still_loads(monkeypatch):
    for name in ("LLM_API_KEY", "LLM_MODEL", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    c.save_model("gemini", "fixture")
    vault = NS(get_password=lambda service, name:
               "legacy-fixture-secret" if name == "GEMINI_API_KEY/GOOGLE_API_KEY" else None)
    monkeypatch.setattr(c, "_vault", lambda: vault)
    assert load_config().llm.api_key == "legacy-fixture-secret"


def test_configuration_failure_keeps_actionable_reason_without_key(monkeypatch, tmp_path, console):
    from miniagent import cli_runtime
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setenv("LLM_API_KEY", "fixture-private-secret")
    monkeypatch.setattr(cli_runtime, "connect", AsyncMock(side_effect=ValueError(
        "Set GEMINI_API_KEY; rejected fixture-private-secret")))
    assert asyncio.run(cli_runtime.cli_run(options(tmp_path, connect=True), console=console)) == 2
    text = console.file.getvalue()
    assert "Set GEMINI_API_KEY" in text and "fixture-private-secret" not in text


def test_provider_menu_has_friendly_rows_without_color(console):
    from unittest.mock import patch
    with patch.object(c.Prompt, "ask", return_value="2"):
        assert c.choose(console, "Provider", ["deepseek", "dashscope"], labels=c.PROVIDERS) == "dashscope"
    text = console.file.getvalue()
    assert "01  DeepSeek · deepseek" in text and "02  Qwen / DashScope · dashscope" in text
    assert "\x1b[" not in text
