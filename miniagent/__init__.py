"""Python-native mini harness and coding agent."""
from .harness import Harness, Plugin
from .agent import loop_plugin
from .policy import Policy
from .session import Session
from .tools.registry import Tool
from .skills import Skill, register_skill, get_skill, list_skills

__version__ = "0.3.0a1"
__all__ = [
    "Harness", "Plugin", "loop_plugin", "Policy", "Session", "Tool",
    "Skill", "register_skill", "get_skill", "list_skills", "__version__",
]


def __getattr__(name):
    if name in {"MiniAgent", "Memory", "Orchestrator", "load_mcp_tools"}:
        raise ImportError(f"{name} was retired in MiniAgent 0.3. Use Harness, Session, Plugin or mcp_plugin; see docs/legacy-migration.md and codex/legacy-pre-harness.")
    raise AttributeError(name)
