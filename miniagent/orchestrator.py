"""Backward-compatible re-export. Real implementation in extensions/orchestrator.py."""
from .extensions.orchestrator import Orchestrator  # noqa: F401

__all__ = ["Orchestrator"]
