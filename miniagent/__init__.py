"""MiniAgent - A lightweight Agent framework.

Core classes are eagerly imported so ``dir(miniagent)`` and IDE
auto-complete work out of the box.  Extensions (MCP, Orchestrator)
are lazily loaded to keep ``import miniagent`` fast.
"""

from __future__ import annotations

from typing import Any

from .agent import MiniAgent
from .skills import Skill, register_skill, get_skill, list_skills

__version__ = "0.1.0"

__all__ = [
    "MiniAgent",
    "Orchestrator",
    "load_mcp_tools",
    "Skill",
    "register_skill",
    "get_skill",
    "list_skills",
    "__version__",
]


# Extensions stay lazy — they pull in heavier deps
def __getattr__(name: str) -> Any:
    if name == "Orchestrator":
        from .orchestrator import Orchestrator
        return Orchestrator
    if name == "load_mcp_tools":
        from .mcp_client import load_mcp_tools
        return load_mcp_tools
    raise AttributeError(name)
