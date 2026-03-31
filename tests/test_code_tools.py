"""Tests for code_tools (read/write/edit/grep/glob/bash)."""

import os
import pytest
from miniagent.tools.code_tools import read, write, edit, grep, glob, bash


@pytest.fixture
def tmp_workspace(tmp_path):
    """Create a temporary workspace with sample files."""
    (tmp_path / "hello.py").write_text("print('hello')\nprint('world')\n")
    (tmp_path / "data.txt").write_text("line1\nline2\nline3\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "nested.py").write_text("import os\n")
    original = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original)


class TestRead:
    def test_read_file(self, tmp_workspace):
        result = read(str(tmp_workspace / "hello.py"))
        assert "print('hello')" in result

    def test_read_with_offset_limit(self, tmp_workspace):
        result = read(str(tmp_workspace / "data.txt"), offset=2, limit=1)
        assert "line2" in result
        assert "line1" not in result

    def test_read_nonexistent(self, tmp_workspace):
        result = read(str(tmp_workspace / "nope.txt"))
        assert "Error" in result or "error" in result or "not found" in result.lower() or "No such" in result


class TestWrite:
    def test_write_new_file(self, tmp_workspace):
        result = write(str(tmp_workspace / "new.txt"), "hello world")
        assert result  # write returns "ok" or similar success string
        assert (tmp_workspace / "new.txt").read_text() == "hello world"

    def test_write_creates_dirs(self, tmp_workspace):
        path = str(tmp_workspace / "a" / "b" / "c.txt")
        write(path, "deep")
        assert os.path.exists(path)


class TestEdit:
    def test_edit_replace(self, tmp_workspace):
        result = edit(str(tmp_workspace / "hello.py"), "hello", "hi")
        assert "hi" in (tmp_workspace / "hello.py").read_text()

    def test_edit_not_found(self, tmp_workspace):
        result = edit(str(tmp_workspace / "hello.py"), "nonexistent_string_xyz", "replacement")
        assert "not found" in result.lower() or "error" in result.lower() or "no match" in result.lower()


class TestGlob:
    def test_glob_py(self, tmp_workspace):
        result = glob("**/*.py", str(tmp_workspace))
        assert len(result) >= 2  # hello.py and sub/nested.py

    def test_glob_no_match(self, tmp_workspace):
        result = glob("*.xyz", str(tmp_workspace))
        assert len(result) == 0


class TestGrep:
    def test_grep_pattern(self, tmp_workspace):
        result = grep("print", str(tmp_workspace))
        assert len(result) >= 1
        assert any("hello.py" in r["file"] for r in result)

    def test_grep_no_match(self, tmp_workspace):
        result = grep("zzzznonexistent", str(tmp_workspace))
        assert len(result) == 0


class TestBash:
    def test_echo(self, tmp_workspace):
        result = bash("echo hello")
        assert result["exit_code"] == 0
        assert result["stdout"] == "hello"

    def test_failing_command(self, tmp_workspace):
        result = bash("false")
        assert result["exit_code"] != 0

    def test_timeout(self, tmp_workspace):
        result = bash("sleep 10", timeout=1)
        assert result["exit_code"] == 1
        assert "timed out" in result["stderr"].lower()
