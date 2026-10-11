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


def test_legacy_native_uses_core_loop():
    from types import SimpleNamespace as NS
    from unittest.mock import Mock, patch
    from miniagent import MiniAgent
    with patch.object(MiniAgent, "_init_llm_client"):
        agent = MiniAgent("test", "fake")
    call = NS(id="one", function=NS(name="add", arguments='{"n":2}'))
    first = NS(content=None, tool_calls=[call])
    last = NS(content="done", tool_calls=[])
    agent.client = Mock()
    agent.client.chat.completions.create.side_effect = [NS(choices=[NS(message=first)]), NS(choices=[NS(message=last)])]
    agent.add_tool({"name": "add", "description": "add", "executor": lambda n: n + 1})
    assert agent.run("go", mode="native") == "done"
    messages = agent.client.chat.completions.create.call_args.kwargs["messages"]
    assert any(m.get("tool_call_id") == "one" and m["content"] == "3" for m in messages)
