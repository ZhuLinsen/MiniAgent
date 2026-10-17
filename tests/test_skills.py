"""Tests for the Skill system in miniagent/skills.py."""

from dataclasses import fields as dataclass_fields
from types import SimpleNamespace

from miniagent.skills import Skill, register_skill, get_skill, list_skills


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

    def test_list_skills_contains_builtins(self):
        names = list_skills()
        for expected in ("coder", "researcher", "reviewer", "tester"):
            assert expected in names

    def test_builtin_coder_tools(self):
        coder = get_skill("coder")
        assert coder is not None
        assert "read" in coder.tools
        assert "bash" in coder.tools


class TestHarnessSkill:
    def test_skill_changes_prompt_and_filters_tools(self):
        from miniagent import Harness, Tool
        app = Harness(system_prompt="original")
        for name in ("read", "bash", "calculator"):
            app.registry.add(Tool(name, name, {"type": "object"}, lambda: None))
        app.apply_skill(get_skill("coder"))
        assert app.system_prompt != "original"
        assert {t["function"]["name"] for t in app.registry.schemas()} == {"read", "bash"}

    def test_skill_updates_temperature(self):
        from miniagent import Harness
        backend = SimpleNamespace(temperature=0.9)
        app = Harness(backend, temperature=0.9)
        app.apply_skill(get_skill("coder"))
        assert backend.temperature == 0.3
        app.apply_skill(None)
        assert backend.temperature == 0.9
