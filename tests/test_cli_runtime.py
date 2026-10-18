import argparse
import asyncio
import io

from rich.console import Console

from miniagent.cli_runtime import cli_run


def options(tmp_path, **changes):
    values = dict(config=None, model="test:model", api_key=None, base_url=None,
                  temperature=None, workspace=str(tmp_path), policy="readonly",
                  session=str(tmp_path / "session"), skill=None, no_stream=True,
                  prompt="one")
    values.update(changes)
    return argparse.Namespace(**values)


class Backend:
    async def complete(self, messages, tools, stream):
        if stream:
            stream("[red]literal text[/red]")
        return {"role": "assistant", "content": "[red]literal text[/red]"}


def test_non_tty_literal_output_no_color(tmp_path, monkeypatch):
    output = io.StringIO()
    console = Console(file=output, force_terminal=False, width=80, no_color=True)
    monkeypatch.setenv("NO_COLOR", "1")
    assert asyncio.run(cli_run(options(tmp_path), console=console, backend=Backend())) == 0
    text = output.getvalue()
    assert "[red]literal text[/red]" in text and "\x1b[" not in text


def test_stream_does_not_duplicate_final_answer(tmp_path):
    output = io.StringIO()
    console = Console(file=output, force_terminal=False, width=80)
    assert asyncio.run(cli_run(options(tmp_path, no_stream=False), console=console, backend=Backend())) == 0
    assert output.getvalue().count("literal text") == 1


def test_cli_temperature_override_ignores_invalid_lower_priority_config(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_TEMPERATURE", "invalid")
    config = tmp_path / "config.json"
    config.write_text('{"llm":{"temperature":"invalid"}}')
    output = io.StringIO()
    args = options(tmp_path, config=str(config), temperature=0.25)
    assert asyncio.run(cli_run(args, console=Console(file=output), backend=Backend())) == 0
    assert "literal text" in output.getvalue()


def test_terminal_welcome_and_help_keep_paths_private(tmp_path, monkeypatch):
    import sys
    monkeypatch.setattr(sys, "stdin", io.StringIO("/help\n/q\n"))
    output = io.StringIO()
    console = Console(file=output, force_terminal=True, width=100, no_color=True)
    assert asyncio.run(cli_run(options(tmp_path, prompt=None), console=console, backend=Backend())) == 0
    text = output.getvalue()
    assert "Python harness + agent" in text and "readonly" in text
    assert "Choose a model" in text and "verified result" in text
    assert str(tmp_path) not in text


def test_terminal_one_shot_shows_literal_prompt_once(tmp_path):
    output = io.StringIO()
    console = Console(file=output, force_terminal=True, width=100, no_color=True)
    prompt = "[red]show this literally[/red]"
    assert asyncio.run(cli_run(options(tmp_path, prompt=prompt), console=console, backend=Backend())) == 0
    text = output.getvalue()
    assert text.count(prompt) == 1
    assert text.count("literal text") == 1


def test_repl_session_resume_and_commands(tmp_path, monkeypatch):
    import sys
    monkeypatch.setattr(sys, "stdin", io.StringIO("/help\n/plugins\n/skills reviewer\nfirst\n/session\n/q\n"))
    output = io.StringIO()
    assert asyncio.run(cli_run(options(tmp_path, prompt=None), console=Console(file=output), backend=Backend())) == 0
    assert "Uncertain calls" in output.getvalue()
    from miniagent.session import Session
    session = Session(tmp_path / "session").open()
    assert [m["content"] for m in session.messages if m["role"] == "user"] == ["first"]
    session.close()


def test_config_file_does_not_reuse_wrong_provider_key(tmp_path, monkeypatch):
    import json
    from miniagent.config import load_config
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"llm": {"model": "anthropic:test"}}))
    monkeypatch.setenv("OPENAI_API_KEY", "wrong")
    for key in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(key, raising=False)
    assert load_config(str(path)).llm.api_key is None


def test_cli_shows_failed_exit_and_bounded_parameters(tmp_path):
    import json
    import sys
    class Commands:
        count = 0
        async def complete(self, messages, tools, stream):
            self.count += 1
            if self.count == 1:
                return {"role": "assistant", "tool_calls": [{"id": "one", "type": "function", "function": {
                    "name": "bash", "arguments": json.dumps({"cmd": f'"{sys.executable}" -c "raise SystemExit(7)"'})}}]}
            return {"role": "assistant", "content": "Command failed"}
    output = io.StringIO()
    assert asyncio.run(cli_run(options(tmp_path, policy="trusted"), console=Console(file=output, width=80), backend=Commands())) == 0
    assert "failed bash" in output.getvalue()
    assert "cmd=<" in output.getvalue()
    assert "SystemExit" not in output.getvalue()
