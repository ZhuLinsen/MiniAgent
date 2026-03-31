"""Backward-compatible re-export. Real implementation in extensions/mcp_client.py."""
from .extensions.mcp_client import MCPClient, load_mcp_tools  # noqa: F401

__all__ = ["MCPClient", "load_mcp_tools"]
