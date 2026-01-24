"""MiniAgent CLI.

Implements an interactive terminal interface similar in spirit to nanocode.
"""

from __future__ import annotations

# Enable CLI mode BEFORE importing anything else that uses logging
from .logger import set_cli_mode
set_cli_mode(True)

import argparse
import os
import sys
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.status import Status
from rich.style import Style
from rich.text import Text

from .agent import MiniAgent
from .config import load_config
from .logger import get_logger
from .memory import Memory

logger = get_logger(__name__)

console = Console()

def _format_history(history: List[Dict[str, str]], limit_turns: int = 10) -> str:
    if not history:
        return ""

    # Keep the last N user+assistant pairs (approx).
    recent = history[-(limit_turns * 2) :]
    lines = ["Conversation history (most recent last):"]
    for m in recent:
        role = m.get("role", "")
        content = (m.get("content", "") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) + "\n\n"


def _truncate_str(s: str, limit: int = 60) -> str:
    """Truncate a string for display."""
    if len(s) > limit:
        return s[:limit] + "…"
    return s


def _format_tool_args(name: str, args: Dict[str, Any]) -> str:
    """Format tool arguments for concise display (Claude Code style)."""
    if name == "bash":
        cmd = args.get("cmd", args.get("command", ""))
        return _truncate_str(cmd, 80)
    elif name == "read":
        path = args.get("path", "")
        offset = args.get("offset", 1)
        limit = args.get("limit", 50)
        return f"{path} (lines {offset}-{offset + limit - 1})"
    elif name == "write":
        path = args.get("path", "")
        content = args.get("content", "")
        lines = content.count("\n") + 1
        return f"{path} ({lines} lines)"
    elif name == "edit":
        path = args.get("path", "")
        return f"{path}"
    elif name in ("glob", "grep"):
        pattern = args.get("pattern", "")
        path = args.get("path", args.get("root", "."))
        return f"{pattern} in {path}"
    elif name == "calculator":
        return args.get("expression", str(args))
    else:
        # Generic: show first key-value pair
        if args:
            first_key = next(iter(args))
            return f"{first_key}={_truncate_str(str(args[first_key]), 50)}"
        return ""


def _format_tool_result(name: str, result: Any) -> str:
    """Format tool result for concise display."""
    if result is None:
        return "✓"
    if isinstance(result, dict):
        if "exit_code" in result:  # bash result
            code = result.get("exit_code", 0)
            if code == 0:
                stdout = result.get("stdout", "")
                lines = stdout.strip().split("\n") if stdout else []
                if len(lines) <= 3:
                    return "\n".join(lines) if lines else "✓"
                return f"{len(lines)} lines"
            else:
                return f"exit {code}"
        elif "error" in result:
            return f"✗ {_truncate_str(str(result['error']), 50)}"
    if isinstance(result, str):
        if len(result) > 100:
            lines = result.count("\n") + 1
            return f"{lines} lines" if lines > 3 else _truncate_str(result, 60)
        return _truncate_str(result, 60)
    return _truncate_str(str(result), 60)


# Global status for thinking indicator
_current_status: Optional[Status] = None


def _tool_callback(event: str, name: str, payload: Dict[str, Any]) -> None:
    """Callback for tool execution (Claude Code style output)."""
    global _current_status
    
    if event == "start":
        # Stop any existing status
        if _current_status:
            _current_status.stop()
            _current_status = None
        
        args = payload.get("arguments", {})
        args_str = _format_tool_args(name, args)
        
        # Print tool invocation line (dim, compact)
        icon = "●" 
        console.print(f"  [dim]{icon}[/dim] [cyan]{name}[/cyan] [dim]{args_str}[/dim]")
        
    elif event == "end":
        result = payload.get("result", payload.get("error"))
        result_str = _format_tool_result(name, result)
        
        # Only print result if it's meaningful and short
        if result_str and result_str != "✓" and len(result_str) < 100:
            # Indent result under the tool call
            for line in result_str.split("\n")[:3]:  # Max 3 lines
                console.print(f"    [dim]→ {line}[/dim]")
        
        # Restore status
        if _current_status:
           _current_status.start()


def _status_callback(status_text: str) -> None:
    """Callback for updating the status spinner text."""
    global _current_status
    if _current_status:
        _current_status.update(f"[dim]{status_text}[/dim]")


def _build_agent(args: argparse.Namespace) -> tuple[MiniAgent, Memory]:
    cfg = load_config(args.config)

    model = args.model or cfg.llm.model
    api_key = args.api_key or cfg.llm.api_key
    base_url = args.base_url or cfg.llm.api_base
    temperature = args.temperature if args.temperature is not None else cfg.llm.temperature

    if not api_key:
        raise SystemExit("Missing API key. Set LLM_API_KEY or pass --api-key.")

    memory = Memory()
    memory.load()

    system_prompt = cfg.system_prompt
    mem_ctx = memory.context()
    if mem_ctx:
        system_prompt = system_prompt.rstrip() + "\n\n" + mem_ctx

    agent = MiniAgent(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        system_prompt=system_prompt,
        use_reflector=cfg.enable_reflection,
    )

    # Load some default tools if configured, else fall back to all currently registered.
    agent.tools = []
    tools = cfg.default_tools or agent.get_available_tools()
    for tool_name in tools:
        agent.load_builtin_tool(tool_name)

    return agent, memory


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="miniagent", description="MiniAgent interactive CLI")
    parser.add_argument("--config", help="Path to config JSON")
    parser.add_argument("--model", help="Override model name")
    parser.add_argument("--api-key", help="Override API key")
    parser.add_argument("--base-url", help="Override base URL")
    parser.add_argument("--temperature", type=float, help="Override temperature")
    args = parser.parse_args(argv)

    try:
        agent, memory = _build_agent(args)
    except SystemExit:
        raise
    except Exception as e:
        console.print(f"[red]error:[/red] {e}")
        return 1

    console.print(f"[dim]cwd:[/dim] {os.getcwd()}")
    console.print(f"[dim]commands:[/dim] /help /c /q")

    history: List[Dict[str, str]] = []

    while True:
        try:
            user_text = Prompt.ask("[cyan]you[/cyan]")
            user_text = user_text.strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        if not user_text:
            continue

        if user_text in ("/q", "/quit", "/exit"):
            break
        if user_text in ("/c", "/clear"):
            history.clear()
            console.print(f"[dim]cleared[/dim]")
            continue
        if user_text in ("/help", "help"):
            console.print("/help  show help")
            console.print("/c     clear conversation")
            console.print("/q     quit")
            continue

        history.append({"role": "user", "content": user_text})
        memory.push("user", user_text)

        query = _format_history(history) + user_text

        try:
            # Show thinking indicator
            with console.status("[dim]Thinking...[/dim]", spinner="dots") as status:
                global _current_status
                _current_status = status
                try:
                    response = agent.run_with_tools(
                        query, 
                        tool_callback=_tool_callback,
                        status_callback=_status_callback
                    )
                finally:
                    _current_status = None
        except TypeError:
            # Backward compatibility if tool_callback not available.
            response = agent.run(query)
        except Exception as e:
            console.print(f"[red]error:[/red] {e}")
            continue

        history.append({"role": "assistant", "content": response})
        memory.push("assistant", response)

        console.print(Panel(Markdown(response), title="assistant", style="green", border_style="green"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
