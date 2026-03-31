"""MiniAgent - A lightweight Agent framework.

This package keeps imports lightweight: importing `miniagent` should not
automatically import LLM clients unless you actually use `MiniAgent`.
"""

from __future__ import annotations

from typing import Any

__version__ = "0.1.0"

__all__ = ["MiniAgent", "Orchestrator", "load_mcp_tools", "__version__"]


def __getattr__(name: str) -> Any:
	if name == "MiniAgent":
		from .agent import MiniAgent
		return MiniAgent
	if name == "Orchestrator":
		from .orchestrator import Orchestrator
		return Orchestrator
	if name == "load_mcp_tools":
		from .mcp_client import load_mcp_tools
		return load_mcp_tools
	raise AttributeError(name)