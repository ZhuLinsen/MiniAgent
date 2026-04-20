"""MiniAgent CLI.

Implements an interactive terminal interface similar in spirit to nanocode.
"""

from __future__ import annotations

# Enable CLI mode BEFORE importing anything else that uses logging
from .logger import set_cli_mode
set_cli_mode(True)

import argparse
import os
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.status import Status

from . import __version__
from .agent import MiniAgent
from .config import load_config
from .logger import get_logger
from .memory import Memory
from .resolver import RuntimeOverride, resolve_runtime

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


def _build_agent(args: argparse.Namespace) -> tuple[MiniAgent, Memory, Any, bool]:
    cfg = load_config(args.config)
    if getattr(args, "strict_resolution", False):
        cfg.strict_resolution = True

    model = args.model or cfg.llm.model
    api_key = args.api_key or cfg.llm.api_key
    base_url = args.base_url or cfg.llm.api_base

    if not api_key:
        console.print("[bold red]❌ Missing API Key[/bold red]")
        console.print("\n[bold]Quick setup:[/bold]")
        console.print("  1. Copy the example: [cyan]cp .env.example .env[/cyan]")
        console.print("  2. Edit with your key: [cyan]nano .env[/cyan]")
        console.print("\n[bold]Required variables:[/bold]")
        console.print("  [dim]LLM_API_KEY[/dim]   = your API key")
        console.print("  [dim]LLM_MODEL[/dim]    = model name  (e.g. deepseek-chat, gpt-4o)")
        console.print("  [dim]LLM_API_BASE[/dim] = endpoint URL (e.g. https://api.deepseek.com/v1)")
        console.print("\n[dim]Or pass on command line: miniagent --api-key sk-xxx --model gpt-4o[/dim]")
        raise SystemExit(1)

    memory = Memory()
    memory.load()

    resolved = resolve_runtime(
        cfg,
        RuntimeOverride(
            packs=args.pack,
            profile=args.profile,
            tools=args.tool,
            skill=args.skill,
            temperature=args.temperature,
        ),
    )
    system_prompt = resolved.system_prompt
    mem_ctx = memory.context()
    if mem_ctx:
        system_prompt = system_prompt.rstrip() + "\n\n" + mem_ctx

    def _confirm_dangerous(cmd: str) -> bool:
        """Rich-formatted confirmation for dangerous commands."""
        console.print(f"\n  [bold red]⚠️  Dangerous command detected:[/bold red]")
        console.print(f"  [yellow]{cmd}[/yellow]")
        answer = Prompt.ask("  [bold]Allow execution?[/bold]", choices=["y", "n"], default="n")
        return answer.lower() == "y"

    agent = MiniAgent(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=resolved.temperature,
        system_prompt=system_prompt,
        use_reflector=cfg.enable_reflection,
        confirm_dangerous=cfg.confirm_dangerous,
        confirm_callback=_confirm_dangerous,
    )

    agent.tools = []
    for tool_name in resolved.tool_names:
        agent.load_builtin_tool(tool_name)

    return agent, memory, resolved.report, cfg.strict_resolution


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for the ``miniagent`` CLI.
    
    Parses arguments, initialises the agent, and runs the interactive REPL.
    Environment variables (LLM_API_KEY, LLM_MODEL, LLM_API_BASE) can be set
    in a ``.env`` file or exported directly.
    """
    parser = argparse.ArgumentParser(prog="miniagent", description="MiniAgent - Minimalist CLI Agent Framework")
    parser.add_argument("--version", "-V", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--config", help="Path to config JSON")
    parser.add_argument("--model", help="Override model name")
    parser.add_argument("--api-key", help="Override API key")
    parser.add_argument("--base-url", help="Override base URL")
    parser.add_argument("--temperature", type=float, help="Override temperature")
    parser.add_argument("--profile", help="Select a configured deployment profile")
    parser.add_argument("--skill", help="Override the active skill")
    parser.add_argument("--pack", action="append", help="Add an external pack module")
    parser.add_argument("--tool", action="append", help="Explicitly enable a tool")
    parser.add_argument("--strict-resolution", action="store_true", help="Fail startup when bootstrap diagnostics contain errors")
    args = parser.parse_args(argv)

    try:
        agent, memory, bootstrap_report, strict_mode = _build_agent(args)
        if bootstrap_report.has_errors():
            report_text = bootstrap_report.render_text("user")
            if report_text:
                console.print(Panel(report_text, title="Bootstrap Errors", border_style="red"))
            return 1
    except SystemExit:
        raise
    except Exception as e:
        console.print(f"[red]error:[/red] {e}")
        return 1

    startup_bits = [
        f"[dim]model:[/dim] {agent.model}",
        f"[dim]tools:[/dim] {len(agent.tools)}",
    ]
    if bootstrap_report.selected_profile:
        startup_bits.append(f"[dim]profile:[/dim] {bootstrap_report.selected_profile}")
    if bootstrap_report.selected_skill:
        startup_bits.append(f"[dim]skill:[/dim] {bootstrap_report.selected_skill}")
    startup_bits.append("[dim]type /help for commands[/dim]")
    console.print("  ".join(startup_bits))

    report_text = bootstrap_report.render_text("user")
    if report_text:
        border = "yellow" if bootstrap_report.diagnostics else "blue"
        title = "Bootstrap Warnings" if bootstrap_report.diagnostics else "Bootstrap"
        console.print(Panel(report_text, title=title, border_style=border))
    
    # Streaming flag — can be toggled with /stream
    use_streaming = os.environ.get("MINIAGENT_STREAM", "1") != "0"
    # Tool calling mode — "text" (default) or "native"
    run_mode = "text"

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
        if user_text == "/stream":
            use_streaming = not use_streaming
            console.print(f"[dim]streaming {'on' if use_streaming else 'off'}[/dim]")
            continue
        if user_text == "/model":
            console.print(f"[dim]current model:[/dim] {agent.model}")
            try:
                new_model = Prompt.ask("[dim]new model (enter to keep)[/dim]", default=agent.model)
                if new_model != agent.model:
                    agent.model = new_model
                    console.print(f"[green]✓[/green] switched to {new_model}")
            except (EOFError, KeyboardInterrupt):
                pass
            continue
        if user_text == "/mode":
            run_mode = "native" if run_mode == "text" else "text"
            console.print(f"[dim]mode: {run_mode}[/dim]")
            continue
        if user_text in ("/help", "help"):
            console.print("[bold]Commands:[/bold]")
            console.print("  /help    show this help")
            console.print("  /bootstrap  show startup profile/skill/tool diagnostics")
            console.print("  /c       clear conversation history")
            console.print("  /stream  toggle streaming output")
            console.print("  /model   switch LLM model")
            console.print("  /mode    toggle text/native FC mode")
            console.print("  /tools   list loaded tools")
            console.print("  /q       quit")
            console.print(
                f"\n[dim]model: {agent.model} | mode: {run_mode} | streaming: {'on' if use_streaming else 'off'} | "
                f"strict: {'on' if strict_mode else 'off'} | tools: {len(agent.tools)}[/dim]"
            )
            continue
        if user_text == "/bootstrap":
            console.print(Panel(
                bootstrap_report.render_text("user") or "No bootstrap diagnostics.",
                title="Bootstrap",
                border_style="blue",
            ))
            continue
        if user_text == "/tools":
            console.print(f"[bold]Loaded Tools ({len(agent.tools)}):[/bold]")
            for t in agent.tools:
                desc = t['description'].split('\n')[0][:70]
                console.print(f"  [cyan]{t['name']:<18}[/cyan] {desc}")
            continue

        history.append({"role": "user", "content": user_text})
        memory.push("user", user_text)

        query = _format_history(history) + user_text
        
        # Prepare streaming callback
        _stream_chunks: List[str] = []
        _stream_has_tool_call = False
        
        def _stream_callback(token: str) -> None:
            """Print streaming tokens, but suppress if it's a tool call block."""
            nonlocal _stream_has_tool_call, _stream_chunks
            _stream_chunks.append(token)
            # Detect tool call patterns early and stop printing
            partial = "".join(_stream_chunks)
            if "TOOL:" in partial or "Tool:" in partial or "工具:" in partial:
                _stream_has_tool_call = True
                return
            if not _stream_has_tool_call:
                console.print(token, end="", highlight=False)

        try:
            # Show thinking indicator
            with console.status("[dim]Thinking...[/dim]", spinner="dots") as status:
                global _current_status
                _current_status = status
                try:
                    if run_mode == "native":
                        response = agent.run_with_native_tools(
                            query,
                            tool_callback=_tool_callback,
                            status_callback=_status_callback,
                        )
                    else:
                        response = agent.run_with_tools(
                            query, 
                            tool_callback=_tool_callback,
                            status_callback=_status_callback,
                            stream_callback=_stream_callback if use_streaming else None,
                        )
                finally:
                    _current_status = None
        except TypeError:
            # Backward compatibility if tool_callback not available.
            response = agent.run(query, mode=run_mode)
        except Exception as e:
            console.print(f"[red]error:[/red] {type(e).__name__}: {str(e)[:200]}")
            continue

        history.append({"role": "assistant", "content": response})
        memory.push("assistant", response)

        # If streaming printed the final answer already, just add a newline
        if use_streaming and _stream_chunks and not _stream_has_tool_call:
            console.print()  # newline after streamed output
            continue

        # Truncate overly long responses for display (keep full in history)
        display_response = response
        if len(response) > 2000:
            # Count lines and truncate if too long
            lines = response.split('\n')
            if len(lines) > 50:
                display_response = '\n'.join(lines[:20]) + f'\n\n... ({len(lines) - 40} lines omitted) ...\n\n' + '\n'.join(lines[-20:])
            else:
                display_response = response[:1000] + f'\n\n... ({len(response) - 2000} chars omitted) ...\n\n' + response[-1000:]
        
        console.print(Panel(Markdown(display_response), title="assistant", style="green", border_style="green"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
