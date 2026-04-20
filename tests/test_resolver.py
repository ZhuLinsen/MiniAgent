"""Tests for runtime resolution and bootstrap diagnostics."""

import importlib
import sys
import textwrap
import uuid

from miniagent.config import AgentConfig, ProfileConfig
from miniagent.pack_loader import clear_loaded_packs
from miniagent.resolver import resolve_runtime
from miniagent.skills import _SKILLS, _SKILL_META
from miniagent.tools import _TOOLS, _TOOL_META


def _cleanup_loaded_entries(result):
    for name in result.report.selected_tools:
        if name.startswith("resolver_temp_tool_"):
            _TOOLS.pop(name, None)
            _TOOL_META.pop(name, None)

    skill_name = result.active_skill
    if skill_name and skill_name.startswith("resolver_temp_skill_"):
        _SKILLS.pop(skill_name, None)
        _SKILL_META.pop(skill_name, None)


def _create_pack(tmp_path, monkeypatch):
    suffix = uuid.uuid4().hex[:8]
    package_name = "resolver_pack_%s" % suffix
    tool_name = "resolver_temp_tool_%s" % suffix
    skill_name = "resolver_temp_skill_%s" % suffix
    package_dir = tmp_path / package_name
    package_dir.mkdir()

    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "pack.py").write_text(textwrap.dedent(
        """
        PACK_NAME = "resolver_pack"
        PACK_VERSION = "0.1.0"

        def register():
            from . import tools, skills
        """
    ), encoding="utf-8")
    (package_dir / "tools.py").write_text(textwrap.dedent(
        """
        from miniagent.tools import register_tool

        @register_tool
        def {tool_name}(value: str) -> str:
            return value
        """.format(tool_name=tool_name)
    ), encoding="utf-8")
    (package_dir / "skills.py").write_text(textwrap.dedent(
        """
        from miniagent.skills import Skill, register_skill

        register_skill(Skill(
            name="{skill_name}",
            prompt="resolver pack prompt",
            tools=["{tool_name}"],
            temperature=0.1,
        ))
        """.format(skill_name=skill_name, tool_name=tool_name)
    ), encoding="utf-8")

    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    return package_name, tool_name, skill_name


def test_resolve_runtime_uses_skill_tools_when_no_explicit_tools():
    config = AgentConfig(default_skill="reviewer")

    resolved = resolve_runtime(config)

    assert resolved.active_skill == "reviewer"
    assert resolved.tool_names == ["read", "grep", "glob"]
    assert any(item.code == "R001" for item in resolved.report.diagnostics)


def test_resolve_runtime_warns_when_falling_back_to_all_registered_tools():
    config = AgentConfig()

    resolved = resolve_runtime(config)

    assert "read" in resolved.tool_names
    assert any(item.code == "R002" for item in resolved.report.diagnostics)


def test_resolve_runtime_filters_tools_by_skill_whitelist():
    config = AgentConfig(
        profiles={
            "review_profile": ProfileConfig(
                tools=["read", "write", "calculator"],
                skill="reviewer",
            )
        },
        profile="review_profile",
    )

    resolved = resolve_runtime(config)

    assert resolved.active_profile == "review_profile"
    assert resolved.active_skill == "reviewer"
    assert resolved.tool_names == ["read"]
    assert any(item.code == "R007" for item in resolved.report.diagnostics)
    assert any(item.code == "R008" for item in resolved.report.diagnostics)
    assert any(item.code == "R009" for item in resolved.report.diagnostics)


def test_resolve_runtime_reports_missing_requested_tools():
    config = AgentConfig(default_tools=["missing_tool_xyz"])

    resolved = resolve_runtime(config)

    assert resolved.tool_names == []
    assert any(item.code == "R005" for item in resolved.report.diagnostics)


def test_resolve_runtime_reports_missing_skill():
    config = AgentConfig(default_skill="missing_skill_xyz")

    resolved = resolve_runtime(config)

    assert resolved.active_skill is None
    assert any(item.code == "R004" for item in resolved.report.diagnostics)


def test_resolve_runtime_falls_back_to_default_profile_with_warning():
    config = AgentConfig(
        profile="missing_profile_xyz",
        profiles={
            "default": ProfileConfig(tools=["read"]),
        },
    )

    resolved = resolve_runtime(config)

    assert resolved.active_profile == "default"
    assert resolved.tool_names == ["read"]
    assert any(item.code == "R010" for item in resolved.report.diagnostics)


def test_resolve_runtime_strict_mode_upgrades_filter_warning_to_error():
    config = AgentConfig(
        strict_resolution=True,
        profiles={
            "strict_profile": ProfileConfig(
                tools=["read", "write"],
                skill="reviewer",
            )
        },
        profile="strict_profile",
    )

    resolved = resolve_runtime(config)

    assert resolved.report.has_errors() is True
    assert any(item.code == "R007" and item.level == "error" for item in resolved.report.diagnostics)


def test_resolve_runtime_loads_external_pack_from_config(tmp_path, monkeypatch):
    clear_loaded_packs()
    package_name, tool_name, skill_name = _create_pack(tmp_path, monkeypatch)
    config = AgentConfig(
        packs=[package_name],
        default_skill=skill_name,
    )

    resolved = None
    try:
        resolved = resolve_runtime(config)

        assert resolved.active_skill == skill_name
        assert resolved.tool_names == [tool_name]
        assert package_name in resolved.report.packs_loaded
        assert any(item.code == "R001" for item in resolved.report.diagnostics)
    finally:
        if resolved is not None:
            _cleanup_loaded_entries(resolved)
        clear_loaded_packs()
        for module_name in list(sys.modules):
            if module_name == package_name or module_name.startswith("%s." % package_name):
                sys.modules.pop(module_name, None)
