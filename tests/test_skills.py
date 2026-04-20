"""Tests for the Skill system in miniagent/skills.py."""

import pytest
from dataclasses import fields as dataclass_fields
from unittest.mock import MagicMock, patch

from miniagent.skills import (
    Skill,
    register_skill,
    get_skill,
    get_skill_meta,
    list_skills,
    _SKILLS,
    _SKILL_META,
)


class TestSkillDataclass:
    def test_skill_has_correct_fields(self):
        names = {f.name for f in dataclass_fields(Skill)}
        assert names == {"name", "prompt", "tools", "temperature", "max_iterations", "description"}

    def test_skill_defaults(self):
        s = Skill(name="x", prompt="p")
        assert s.tools is None
        assert s.temperature is None
        assert s.max_iterations is None
        assert s.description == ""

    def test_skill_custom_values(self):
        s = Skill(name="a", prompt="p", tools=["t1"], temperature=0.5,
                  max_iterations=3, description="desc")
        assert s.tools == ["t1"]
        assert s.temperature == 0.5
        assert s.max_iterations == 3
        assert s.description == "desc"


class TestSkillRegistry:
    def test_register_skill(self):
        s = Skill(name="__test_reg__", prompt="p")
        result = register_skill(s)
        assert result is s
        assert get_skill("__test_reg__") is s

    def test_get_skill_existing(self):
        skill = get_skill("coder")
        assert skill is not None
        assert skill.name == "coder"

    def test_get_skill_missing(self):
        assert get_skill("nonexistent_skill_xyz") is None

    def test_get_skill_metadata_existing(self):
        meta = get_skill_meta("coder")
        assert meta is not None
        assert meta.source == "builtin"
        assert meta.pack_name == "builtin"
        assert meta.module == "miniagent.skills"

    def test_list_skills_contains_builtins(self):
        names = list_skills()
        for expected in ("coder", "researcher", "reviewer", "tester"):
            assert expected in names

    def test_builtin_coder_tools(self):
        coder = get_skill("coder")
        assert coder is not None
        assert "read" in coder.tools
        assert "bash" in coder.tools

    def test_register_skill_duplicate_raises(self):
        skill = Skill(name="__test_duplicate_skill__", prompt="p")
        register_skill(skill)

        with pytest.raises(ValueError, match="already registered"):
            register_skill(skill)

        del _SKILLS[skill.name]
        del _SKILL_META[skill.name]

    def test_register_skill_allow_override_updates_skill(self):
        original = Skill(name="__test_override_skill__", prompt="p1")
        replacement = Skill(name="__test_override_skill__", prompt="p2")
        register_skill(original)
        register_skill(replacement, allow_override=True)

        assert get_skill("__test_override_skill__") is replacement
        meta = get_skill_meta("__test_override_skill__")
        assert meta is not None
        assert meta.source == "runtime"
        assert meta.module == __name__

        del _SKILLS[replacement.name]
        del _SKILL_META[replacement.name]


class TestAgentLoadSkill:
    def test_load_skill_changes_prompt_and_filters_tools(self):
        from miniagent.agent import MiniAgent

        with patch.object(MiniAgent, '_init_llm_client'):
            agent = MiniAgent(model="test", api_key="fake", system_prompt="original")
            agent.client = MagicMock()
            agent.tools = [
                {"name": "read", "description": "read", "parameters": {}, "executor": lambda: None},
                {"name": "bash", "description": "bash", "parameters": {}, "executor": lambda: None},
                {"name": "calculator", "description": "calc", "parameters": {}, "executor": lambda: None},
            ]
            result = agent.load_skill("coder")

            assert result is True
            assert agent.system_prompt != "original"
            remaining = {t["name"] for t in agent.tools}
            assert remaining == {"read", "bash"}

    def test_load_skill_returns_false_for_unknown(self):
        from miniagent.agent import MiniAgent

        with patch.object(MiniAgent, '_init_llm_client'):
            agent = MiniAgent(model="test", api_key="fake")
            agent.client = MagicMock()
            assert agent.load_skill("nonexistent_xyz") is False

    def test_load_skill_updates_temperature(self):
        from miniagent.agent import MiniAgent

        with patch.object(MiniAgent, '_init_llm_client'):
            agent = MiniAgent(model="test", api_key="fake", temperature=0.9)
            agent.client = MagicMock()
            agent.tools = []
            agent.load_skill("coder")
            assert agent.temperature == 0.3
