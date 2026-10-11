"""MiniAgent: eager Harness/Skills exports; legacy and extensions load on demand."""

from __future__ import annotations

from typing import Any

from .harness import Harness, Plugin
from .agent import loop_plugin
from .skills import Skill, register_skill, get_skill, list_skills

__version__ = "0.2.0a1"

__all__ = [
    "MiniAgent",
    "Harness",
    "Plugin",
    "loop_plugin",
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
    if name == "MiniAgent":
        from .legacy import MiniAgent
        return MiniAgent
    if name == "Orchestrator":
        from .orchestrator import Orchestrator
        return Orchestrator
    if name == "load_mcp_tools":
        from .mcp_client import load_mcp_tools
        return load_mcp_tools
    raise AttributeError(name)
