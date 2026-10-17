"""Keep user connection profiles and ephemeral credentials out of test results."""
import pytest


@pytest.fixture(autouse=True)
def isolated_connection_home(tmp_path, monkeypatch):
    from miniagent.connections import _secrets
    monkeypatch.setenv("MINIAGENT_HOME", str(tmp_path / "agent-home"))
    _secrets.clear()
    yield
    _secrets.clear()
