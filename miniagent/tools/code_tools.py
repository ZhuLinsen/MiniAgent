"""Code editing tools for MiniAgent.

These tools are intentionally small, dependency-free, and suitable for open-source use.
They are designed to be used by the agent via the existing text-based tool calling format.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import register_tool
from ..logger import get_logger

logger = get_logger(__name__)


def _resolve_path(path: str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    return p


def _read_text_file(path: Path) -> List[str]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


def _write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _iter_files(root: Path) -> List[Path]:
    if root.is_file():
        return [root]
    if not root.exists():
        return []
    return [p for p in root.rglob("*") if p.is_file()]


@register_tool
def read(path: str, offset: int = 1, limit: int = 200) -> str:
    """Read file content with line numbers.

    Args:
        path: File path.
        offset: 1-based start line number.
        limit: Max number of lines to return.

    Returns:
        A string containing the selected lines with line numbers.
    """
    file_path = _resolve_path(path)
    if not file_path.exists() or not file_path.is_file():
        return f"error: file not found: {file_path}"

    lines = _read_text_file(file_path)
    total = len(lines)

    if limit <= 0:
        return "error: limit must be > 0"

    start = max(1, int(offset))
    end = min(total, start + int(limit) - 1)

    if start > total:
        return f"ok: 0 lines (file has {total} lines)"

    width = len(str(end))
    body = "\n".join(
        f"{str(i).rjust(width)}| {lines[i-1]}" for i in range(start, end + 1)
    )
    return f"path: {file_path}\nlines: {start}-{end}/{total}\n{body}"


@register_tool
def write(path: str, content: str) -> str:
    """Write content to a file.

    Args:
        path: File path.
        content: File content.

    Returns:
        "ok" or an error string.
    """
    file_path = _resolve_path(path)
    try:
        _write_text_file(file_path, content)
        return "ok"
    except Exception as e:
        logger.exception("write failed")
        return f"error: {e}"


@register_tool
def edit(path: str, old: str, new: str, all: bool = False) -> str:  # noqa: A002
    """Edit a file via string replacement.

    Args:
        path: File path.
        old: Substring to replace.
        new: Replacement substring.
        all: Replace all occurrences if True, else only first.

    Returns:
        "ok" or an error string.
    """
    file_path = _resolve_path(path)
    if not file_path.exists() or not file_path.is_file():
        return f"error: file not found: {file_path}"

    try:
        original = file_path.read_text(encoding="utf-8", errors="replace")
        if old not in original:
            return "error: 'old' text not found"

        updated = original.replace(old, new) if all else original.replace(old, new, 1)
        _write_text_file(file_path, updated)
        return "ok"
    except Exception as e:
        logger.exception("edit failed")
        return f"error: {e}"


@register_tool
def glob(pattern: str, path: str = ".") -> List[str]:  # noqa: A002
    """File pattern matching.

    Args:
        pattern: Glob pattern, e.g. "**/*.py".
        path: Root directory (default: current working directory).

    Returns:
        List of matched file paths.
    """
    root = _resolve_path(path)
    if not root.exists():
        return []
    try:
        matches = root.glob(pattern)
        return [str(p.resolve()) for p in matches]
    except Exception as e:
        logger.exception("glob failed")
        return [f"error: {e}"]


@register_tool
def grep(pattern: str, path: str = ".") -> List[Dict[str, Any]]:  # noqa: A002
    """Regex search in files.

    Args:
        pattern: Regex pattern.
        path: Root directory or file.

    Returns:
        List of matches: {"file": str, "line": int, "text": str}.
    """
    root = _resolve_path(path)
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return [{"error": f"invalid regex: {e}"}]

    results: List[Dict[str, Any]] = []
    for file_path in _iter_files(root):
        try:
            lines = _read_text_file(file_path)
        except Exception:
            continue

        for idx, line in enumerate(lines, start=1):
            if regex.search(line):
                results.append({
                    "file": str(file_path),
                    "line": idx,
                    "text": line,
                })

    return results


@register_tool
def bash(cmd: str, timeout: int = 30) -> Dict[str, Any]:
    """Execute a shell command.

    Args:
        cmd: Shell command string.
        timeout: Maximum execution time in seconds (default 30).

    Returns:
        Dict containing exit_code, stdout, stderr.
    """
    MAX_OUTPUT = 10000
    try:
        completed = subprocess.run(
            cmd,
            shell=True,
            text=True,
            capture_output=True,
            cwd=os.getcwd(),
            env=os.environ.copy(),
            timeout=timeout,
        )
        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()
        if len(stdout) > MAX_OUTPUT:
            stdout = stdout[:MAX_OUTPUT] + f"\n... [truncated, {len(stdout)} chars total]"
        if len(stderr) > MAX_OUTPUT:
            stderr = stderr[:MAX_OUTPUT] + f"\n... [truncated, {len(stderr)} chars total]"
        return {
            "exit_code": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": 1, "stdout": "", "stderr": f"Command timed out after {timeout}s"}
    except Exception as e:
        logger.exception("bash failed")
        return {"exit_code": 1, "stdout": "", "stderr": str(e)}
