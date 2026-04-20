"""Tests for external pack loading."""

import importlib
import sys
import textwrap
import uuid

from miniagent.diagnostics import BootstrapReport
from miniagent.pack_loader import clear_loaded_packs, load_pack
from miniagent.skills import _SKILLS, _SKILL_META, get_skill, get_skill_meta
from miniagent.tools import _TOOLS, _TOOL_META, get_tool, get_tool_meta


def _cleanup_loaded_entries(result):
    for name in result.tools:
        _TOOLS.pop(name, None)
        _TOOL_META.pop(name, None)
    for name in result.skills:
        _SKILLS.pop(name, None)
        _SKILL_META.pop(name, None)


def _create_pack(tmp_path, monkeypatch):
    suffix = uuid.uuid4().hex[:8]
    package_name = "temp_pack_%s" % suffix
    tool_name = "temp_tool_%s" % suffix
    skill_name = "temp_skill_%s" % suffix
    package_dir = tmp_path / package_name
    package_dir.mkdir()

    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "pack.py").write_text(textwrap.dedent(
        """
        PACK_NAME = "temp_pack"
        PACK_VERSION = "0.1.0"

        def register():
            from . import tools, skills
            return {"name": PACK_NAME, "version": PACK_VERSION}
        """
    ), encoding="utf-8")
    (package_dir / "tools.py").write_text(textwrap.dedent(
        """
        from miniagent.tools import register_tool

        @register_tool
        def {tool_name}(value: str) -> str:
            return value.upper()
        """.format(tool_name=tool_name)
    ), encoding="utf-8")
    (package_dir / "skills.py").write_text(textwrap.dedent(
        """
        from miniagent.skills import Skill, register_skill

        register_skill(Skill(
            name="{skill_name}",
            prompt="temporary prompt",
            tools=["{tool_name}"],
            temperature=0.2,
        ))
        """.format(skill_name=skill_name, tool_name=tool_name)
    ), encoding="utf-8")

    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    return package_name, tool_name, skill_name


def test_load_pack_registers_tools_skills_and_metadata(tmp_path, monkeypatch):
    clear_loaded_packs()
    package_name, tool_name, skill_name = _create_pack(tmp_path, monkeypatch)
    report = BootstrapReport()
    result = None

    try:
        result = load_pack(package_name, report=report)

        assert result.pack_name == "temp_pack"
        assert result.version == "0.1.0"
        assert tool_name in result.tools
        assert skill_name in result.skills
        assert get_tool(tool_name)("abc") == "ABC"
        assert get_skill(skill_name) is not None

        tool_meta = get_tool_meta(tool_name)
        assert tool_meta is not None
        assert tool_meta.source == "pack"
        assert tool_meta.pack_name == "temp_pack"
        assert tool_meta.module == "%s.tools" % package_name

        skill_meta = get_skill_meta(skill_name)
        assert skill_meta is not None
        assert skill_meta.source == "pack"
        assert skill_meta.pack_name == "temp_pack"
        assert skill_meta.module == "%s.skills" % package_name

        assert report.packs_requested == []
        assert report.packs_loaded == [package_name]
    finally:
        if result is not None:
            _cleanup_loaded_entries(result)
        clear_loaded_packs()
        for module_name in list(sys.modules):
            if module_name == package_name or module_name.startswith("%s." % package_name):
                sys.modules.pop(module_name, None)


def test_load_pack_duplicate_emits_warning(tmp_path, monkeypatch):
    clear_loaded_packs()
    package_name, tool_name, skill_name = _create_pack(tmp_path, monkeypatch)
    report = BootstrapReport()
    result = None

    try:
        result = load_pack(package_name, report=report)
        repeated = load_pack(package_name, report=report)

        assert repeated is result
        assert any(item.code == "R012" for item in report.diagnostics)
    finally:
        if result is not None:
            _cleanup_loaded_entries(result)
        clear_loaded_packs()
        for module_name in list(sys.modules):
            if module_name == package_name or module_name.startswith("%s." % package_name):
                sys.modules.pop(module_name, None)


def test_load_missing_pack_records_diagnostic():
    clear_loaded_packs()
    report = BootstrapReport()

    result = load_pack("nonexistent_pack_for_tests_xyz", report=report)

    assert result.pack_name == "nonexistent_pack_for_tests_xyz"
    assert any(item.code == "R003" for item in report.diagnostics)
