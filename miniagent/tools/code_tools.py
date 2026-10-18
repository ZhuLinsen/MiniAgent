"""Code editing tools for MiniAgent.

File helpers are mounted by coding_tools() through Schema, Policy and Skill checks.
Shell execution is owned by miniagent.plugins.shell.
"""

from __future__ import annotations

import re
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, List

from ..logger import get_logger

logger = get_logger(__name__)
_workspace = ContextVar("miniagent_workspace", default=None)
_path_allowed = ContextVar("miniagent_path_allowed", default=lambda path: True)


def _resolve_path(path: str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    p = p.resolve()
    workspace = _workspace.get()
    if workspace is not None and not p.is_relative_to(workspace):
        raise PermissionError("Path is outside workspace")
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
        return [root] if _path_allowed.get()(root) else []
    if not root.exists():
        return []
    workspace = _workspace.get()
    return [p for p in root.rglob("*") if p.is_file()
            and _path_allowed.get()(p.resolve())
            and (workspace is None or p.resolve().is_relative_to(workspace))]


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
        workspace = _workspace.get()
        return [str(p.resolve()) for p in matches
                if (workspace is None or p.resolve().is_relative_to(workspace))
                and _path_allowed.get()(p.resolve())]
    except Exception as e:
        logger.exception("glob failed")
        return [f"error: glob failed: {e}"]


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
