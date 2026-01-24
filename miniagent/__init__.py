"""MiniAgent - A lightweight Agent framework.

This package keeps imports lightweight: importing `miniagent` should not
automatically import LLM clients unless you actually use `MiniAgent`.
"""

from __future__ import annotations

from typing import Any

__version__ = "0.1.0"

__all__ = ["MiniAgent", "__version__"]


def __getattr__(name: str) -> Any:
	if name == "MiniAgent":
		from .agent import MiniAgent  # local import (lazy)

		return MiniAgent
	raise AttributeError(name)