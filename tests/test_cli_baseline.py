from unittest.mock import Mock

from miniagent import cli


def test_current_user_is_not_duplicated(monkeypatch):
    agent, memory = Mock(), Mock()
    agent.model, agent.tools = "test", []
    agent.run_with_tools.return_value = "done"
    monkeypatch.setattr(cli, "_build_agent", lambda args: (agent, memory))
    entries = iter(["unique current request", "/q"])
    monkeypatch.setattr(cli.Prompt, "ask", lambda *a, **k: next(entries))
    monkeypatch.setenv("MINIAGENT_STREAM", "0")
    assert cli.main([]) == 0
    query = agent.run_with_tools.call_args.args[0]
    assert query.count("unique current request") == 1


def test_key_prefix_is_not_logged():
    import inspect
    from miniagent.agent import MiniAgent
    assert "api_key[:" not in inspect.getsource(MiniAgent._call_llm)
