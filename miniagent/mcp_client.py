"""Lightweight MCP (Model Context Protocol) client for MiniAgent.

Connects to MCP-compatible tool servers via stdio or SSE transport,
discovers their tools, and registers them as regular MiniAgent tools.

Usage:
    from miniagent.mcp_client import load_mcp_tools
    
    tools = load_mcp_tools("npx @anthropic/mcp-server-filesystem /tmp")
    for tool in tools:
        agent.add_tool(tool)
"""

from __future__ import annotations

import json
import subprocess
import threading
import uuid
from typing import Any, Callable, Dict, List, Optional

from .logger import get_logger

logger = get_logger(__name__)


class MCPClient:
    """A minimal MCP client using stdio (JSON-RPC over stdin/stdout)."""

    def __init__(self, command: str, env: Optional[Dict[str, str]] = None):
        """
        Args:
            command: Shell command to start the MCP server (e.g. "npx @anthropic/mcp-server-filesystem /tmp").
            env: Optional environment variables for the server process.
        """
        self.command = command
        self.env = env
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._responses: Dict[str, Any] = {}
        self._reader_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the MCP server process."""
        import os
        merged_env = {**os.environ, **(self.env or {})}
        self._process = subprocess.Popen(
            self.command,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=merged_env,
        )
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()

        # Initialize the MCP session
        self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "miniagent", "version": "0.1.0"},
        })
        # Send initialized notification
        self._send_notification("notifications/initialized", {})
        logger.info(f"MCP server started: {self.command}")

    def stop(self) -> None:
        """Stop the MCP server process."""
        if self._process:
            self._process.terminate()
            self._process.wait(timeout=5)
            self._process = None
        logger.info("MCP server stopped")

    def list_tools(self) -> List[Dict[str, Any]]:
        """Discover available tools from the MCP server."""
        result = self._send_request("tools/list", {})
        return result.get("tools", []) if result else []

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server."""
        result = self._send_request("tools/call", {
            "name": name,
            "arguments": arguments,
        })
        if not result:
            return {"error": "No response from MCP server"}

        # MCP returns content as a list of {type, text} objects
        contents = result.get("content", [])
        texts = [c.get("text", "") for c in contents if c.get("type") == "text"]
        return "\n".join(texts) if texts else str(result)

    def _send_request(self, method: str, params: Dict[str, Any]) -> Optional[Dict]:
        """Send a JSON-RPC request and wait for response."""
        req_id = str(uuid.uuid4())[:8]
        message = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }
        self._write(message)

        # Wait for response (simple polling, max 30s)
        import time
        for _ in range(300):
            with self._lock:
                if req_id in self._responses:
                    resp = self._responses.pop(req_id)
                    if "error" in resp:
                        logger.error(f"MCP error: {resp['error']}")
                        return None
                    return resp.get("result")
            time.sleep(0.1)

        logger.error(f"MCP request timed out: {method}")
        return None

    def _send_notification(self, method: str, params: Dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no id, no response expected)."""
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        self._write(message)

    def _write(self, message: Dict) -> None:
        """Write a JSON-RPC message to the server's stdin."""
        if not self._process or not self._process.stdin:
            return
        content = json.dumps(message)
        # MCP uses Content-Length header framing
        frame = f"Content-Length: {len(content)}\r\n\r\n{content}"
        try:
            self._process.stdin.write(frame)
            self._process.stdin.flush()
        except (BrokenPipeError, OSError):
            logger.error("MCP server stdin broken")

    def _read_loop(self) -> None:
        """Background thread: read JSON-RPC responses from stdout."""
        if not self._process or not self._process.stdout:
            return

        while self._process and self._process.poll() is None:
            try:
                # Read Content-Length header
                header_line = self._process.stdout.readline()
                if not header_line:
                    break
                header_line = header_line.strip()
                if not header_line.startswith("Content-Length:"):
                    continue
                content_length = int(header_line.split(":")[1].strip())

                # Read blank line separator
                self._process.stdout.readline()

                # Read content
                content = self._process.stdout.read(content_length)
                if not content:
                    break

                msg = json.loads(content)
                msg_id = msg.get("id")
                if msg_id:
                    with self._lock:
                        self._responses[msg_id] = msg
            except Exception:
                logger.debug("MCP read error", exc_info=True)
                break


def load_mcp_tools(command: str, env: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """
    Start an MCP server and convert its tools into MiniAgent tool dicts.
    
    Args:
        command: Shell command to start the MCP server.
        env: Optional environment variables.
        
    Returns:
        List of tool dicts compatible with agent.add_tool().
    """
    client = MCPClient(command, env)
    try:
        client.start()
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        return []

    mcp_tools = client.list_tools()
    agent_tools = []

    for t in mcp_tools:
        tool_name = t["name"]
        # Create a closure that captures the client and tool name
        def _make_executor(c: MCPClient, n: str) -> Callable:
            def executor(**kwargs: Any) -> Any:
                return c.call_tool(n, kwargs)
            executor.__name__ = n
            executor.__doc__ = t.get("description", n)
            return executor

        agent_tools.append({
            "name": tool_name,
            "description": t.get("description", tool_name),
            "parameters": t.get("inputSchema", {"type": "object", "properties": {}}),
            "executor": _make_executor(client, tool_name),
            "_mcp_client": client,  # keep reference so GC doesn't kill the process
        })

    logger.info(f"Loaded {len(agent_tools)} tools from MCP server: {command}")
    return agent_tools
