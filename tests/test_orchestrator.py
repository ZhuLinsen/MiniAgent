"""Tests for orchestrator worker bootstrap."""

from unittest.mock import MagicMock, patch

from miniagent.extensions.orchestrator import Orchestrator


def test_create_worker_uses_resolved_skill_tool_boundary():
    with patch.object(Orchestrator, "plan"), patch("miniagent.agent.MiniAgent._init_llm_client"):
        orch = Orchestrator(
            model="test-model",
            api_key="fake-key",
        )

        worker = orch._create_worker("reviewer")
        worker.client = MagicMock()

    names = [tool["name"] for tool in worker.tools]
    assert names == ["read", "grep", "glob"]
    assert "write" not in names
    assert "code reviewer" in worker.system_prompt.lower()
    assert worker.temperature == 0.3


def test_create_worker_with_custom_prompt_skips_role_skill_filter():
    with patch("miniagent.agent.MiniAgent._init_llm_client"):
        orch = Orchestrator(
            model="test-model",
            api_key="fake-key",
        )

        worker = orch._create_worker("reviewer", system_prompt="Custom orchestrator prompt")
        worker.client = MagicMock()

    names = [tool["name"] for tool in worker.tools]
    assert "read" in names
    assert "write" in names
    assert worker.system_prompt == "Custom orchestrator prompt"
