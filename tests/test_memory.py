"""Tests for miniagent/memory.py."""

import json
import pytest
from pathlib import Path

from miniagent.memory import Memory


class TestMemoryCreation:
    def test_default_path_is_set(self):
        m = Memory()
        assert m.path is not None
        assert isinstance(m.path, Path)

    def test_custom_path(self, tmp_path):
        p = tmp_path / "mem.json"
        m = Memory(path=p)
        assert m.path == p

    def test_empty_initial_state(self):
        m = Memory()
        assert m.messages == []
        assert m.preferences == {}
        assert m.facts == {}


class TestMemoryPush:
    def test_push_adds_message(self, tmp_path):
        m = Memory(path=tmp_path / "mem.json")
        m.push("user", "hello")
        assert len(m.messages) == 1
        assert m.messages[0]["role"] == "user"
        assert m.messages[0]["content"] == "hello"

    def test_push_trims_to_max(self, tmp_path):
        m = Memory(path=tmp_path / "mem.json", max_messages=3)
        for i in range(5):
            m.push("user", f"msg{i}")
        assert len(m.messages) == 3
        assert m.messages[0]["content"] == "msg2"


class TestMemoryPreferencesAndFacts:
    def test_set_preference(self, tmp_path):
        m = Memory(path=tmp_path / "mem.json")
        m.set_preference("theme", "dark")
        assert m.preferences["theme"] == "dark"

    def test_set_fact(self, tmp_path):
        m = Memory(path=tmp_path / "mem.json")
        m.set_fact("language", "python")
        assert m.facts["language"] == "python"


class TestMemorySaveLoad:
    def test_save_and_load_roundtrip(self, tmp_path):
        p = tmp_path / "mem.json"
        m = Memory(path=p)
        m.set_preference("editor", "vim")
        m.set_fact("os", "linux")
        m.push("user", "hi")
        m.save()

        m2 = Memory(path=p)
        m2.load()
        assert m2.preferences["editor"] == "vim"
        assert m2.facts["os"] == "linux"
        assert len(m2.messages) == 1
        assert m2.messages[0]["content"] == "hi"

    def test_load_missing_file_no_error(self, tmp_path):
        m = Memory(path=tmp_path / "nope.json")
        m.load()  # should not raise
        assert m.messages == []


class TestMemoryContext:
    def test_context_returns_string(self, tmp_path):
        m = Memory(path=tmp_path / "mem.json")
        m.set_preference("lang", "en")
        m.set_fact("name", "Alice")
        m.push("user", "hello")
        ctx = m.context()
        assert isinstance(ctx, str)
        assert "lang" in ctx or "en" in ctx
        assert "Alice" in ctx or "name" in ctx
