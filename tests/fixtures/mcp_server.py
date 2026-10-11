"""Local real-SDK stdio server used by integration tests (stdout is protocol)."""
import os
from typing import TypedDict
from mcp.server.mcpserver import MCPServer

app = MCPServer("test")


class AddResult(TypedDict):
    sum: int
    pid: int


@app.tool(structured_output=True)
def add(a: int, b: int) -> AddResult:
    return {"sum": a + b, "pid": os.getpid()}


app.run(transport="stdio")
