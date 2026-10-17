"""Migration guard for the former handwritten MCP transport."""
from .mcp_plugin import mcp_plugin


def load_mcp_tools(command, env=None):
    """Old implicit process ownership cannot be safely retained."""
    raise RuntimeError("MCP API migrated: use app.use(mcp_plugin(name, command, args, env=env)); see docs/lean-harness.md")


class MCPClient:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("Use the official SDK through mcp_plugin; see docs/lean-harness.md")
