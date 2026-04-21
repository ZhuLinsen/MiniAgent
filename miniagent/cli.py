"""MiniAgent CLI.

Implements an interactive terminal interface similar in spirit to nanocode.
"""

from __future__ import annotations

# Enable CLI mode BEFORE importing anything else that uses logging
from .logger import set_cli_mode
set_cli_mode(True)

import argparse
import os
import re
import threading
from typing import Any, Callable, Dict, List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.status import Status

from . import __version__
from .agent import MiniAgent
from .config import load_config
from .control_server import AgentBusyError, ControlPlaneHandle, start_control_server
from .logger import get_logger
from .memory import Memory
from .resolver import RuntimeOverride, resolve_runtime

logger = get_logger(__name__)

console = Console()


def _looks_like_tool_call_stream(partial: str) -> bool:
    """Best-effort detection for streamed tool-call text that should be suppressed."""
    return any(marker in partial for marker in (
        "TOOL:",
        "Tool:",
        "工具:",
        "<|tool",
        "<｜tool",
        "function<|tool_sep|>",
        "function<｜tool▁sep｜>",
    ))


def _build_status_event(status_text: str) -> Dict[str, Any]:
    """Normalize agent status text into a structured event."""

    match = re.search(r"Iteration\s+(\d+)", status_text)
    if match:
        return {"type": "assistant.thinking", "iteration": int(match.group(1)), "text": status_text}
    return {"type": "assistant.status", "text": status_text}


class AgentSession:
    """Shared CLI session state used by both REPL and the HTTP control plane."""

    def __init__(
        self,
        agent: MiniAgent,
        memory: Memory,
        bootstrap_report: Any,
        strict_mode: bool,
        use_streaming: bool,
        run_mode: str,
    ):
        self.agent = agent
        self.memory = memory
        self.bootstrap_report = bootstrap_report
        self.strict_mode = strict_mode
        self.use_streaming = use_streaming
        self.run_mode = run_mode
        self.history: List[Dict[str, str]] = []
        self.control_http: Optional[str] = None
        self._state_lock = threading.RLock()
        self._request_lock = threading.Lock()

    def set_control_http(self, address: str) -> None:
        """Record the active HTTP control plane address for introspection."""

        with self._state_lock:
            self.control_http = address

    def clear_history(self) -> None:
        """Clear the in-memory conversation history."""

        with self._state_lock:
            self.history.clear()

    def get_history(self, limit: int = 20) -> List[Dict[str, str]]:
        """Return a copy of recent message history."""

        with self._state_lock:
            recent = self.history if limit == 0 else self.history[-limit:]
            return [dict(message) for message in recent]

    def get_session_info(self) -> Dict[str, Any]:
        """Return lightweight session metadata for the control plane."""

        with self._state_lock:
            return {
                "ok": True,
                "model": self.agent.model,
                "profile": self.bootstrap_report.selected_profile,
                "skill": self.bootstrap_report.selected_skill,
                "tools": [tool["name"] for tool in self.agent.tools],
                "history_length": len(self.history),
                "streaming_default": self.use_streaming,
                "mode": self.run_mode,
                "control_http": self.control_http,
            }

    def process_message(
        self,
        user_text: str,
        *,
        mode: Optional[str] = None,
        use_streaming: Optional[bool] = None,
        capture_events: bool = False,
        event_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        tool_callback: Optional[Any] = None,
        status_callback: Optional[Any] = None,
        stream_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Execute one user turn and optionally capture structured events."""

        if not self._request_lock.acquire(blocking=False):
            raise AgentBusyError("MiniAgent session is busy")

        events: Optional[List[Dict[str, Any]]] = [] if capture_events else None

        def _emit_event(event: Dict[str, Any]) -> None:
            if events is not None:
                events.append(event)
            if event_callback is not None:
                event_callback(event)

        def _tool_callback_proxy(event: str, name: str, payload: Dict[str, Any]) -> None:
            if event == "start":
                _emit_event({
                    "type": "tool.start",
                    "name": name,
                    "arguments": payload.get("arguments", {}),
                })
            elif event == "end":
                structured = {"type": "tool.end", "name": name}
                if "result" in payload:
                    structured["result"] = payload["result"]
                if "error" in payload:
                    structured["error"] = payload["error"]
                _emit_event(structured)

            if tool_callback:
                tool_callback(event, name, payload)

        def _status_callback_proxy(status_text: str) -> None:
            _emit_event(_build_status_event(status_text))
            if status_callback:
                status_callback(status_text)

        def _stream_callback_proxy(token: str) -> None:
            _emit_event({"type": "assistant.delta", "delta": token})
            if stream_callback:
                stream_callback(token)

        active_mode = mode or self.run_mode
        active_streaming = self.use_streaming if use_streaming is None else use_streaming

        with self._state_lock:
            self.history.append({"role": "user", "content": user_text})
            self.memory.push("user", user_text)
            query = _format_history(self.history) + user_text

        try:
            try:
                if active_mode == "native":
                    response = self.agent.run_with_native_tools(
                        query,
                        tool_callback=_tool_callback_proxy,
                        status_callback=_status_callback_proxy,
                    )
                else:
                    response = self.agent.run_with_tools(
                        query,
                        tool_callback=_tool_callback_proxy,
                        status_callback=_status_callback_proxy,
                        stream_callback=_stream_callback_proxy if active_streaming else None,
                    )
            except TypeError:
                response = self.agent.run(query, mode=active_mode)
            except Exception:
                raise

            with self._state_lock:
                self.history.append({"role": "assistant", "content": response})
                self.memory.push("assistant", response)

            _emit_event({"type": "assistant.final", "content": response})
            return {"content": response, "events": events or []}
        finally:
            self._request_lock.release()

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
    parser.add_argument("--control-http", help="Enable the local HTTP control plane on [HOST:]PORT")
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
    
    session = AgentSession(
        agent=agent,
        memory=memory,
        bootstrap_report=bootstrap_report,
        strict_mode=strict_mode,
        use_streaming=os.environ.get("MINIAGENT_STREAM", "1") != "0",
        run_mode="text",
    )

    control_handle: Optional[ControlPlaneHandle] = None
    if args.control_http:
        try:
            control_handle = start_control_server(session, args.control_http)
        except Exception as e:
            console.print(f"[red]error:[/red] failed to start control-http: {e}")
            return 1
        session.set_control_http(control_handle.address)
        console.print(f"[dim]control-http:[/dim] {control_handle.address}")

    try:
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
                session.clear_history()
                console.print(f"[dim]cleared[/dim]")
                continue
            if user_text == "/stream":
                session.use_streaming = not session.use_streaming
                console.print(f"[dim]streaming {'on' if session.use_streaming else 'off'}[/dim]")
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
                session.run_mode = "native" if session.run_mode == "text" else "text"
                console.print(f"[dim]mode: {session.run_mode}[/dim]")
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
                    f"\n[dim]model: {agent.model} | mode: {session.run_mode} | streaming: {'on' if session.use_streaming else 'off'} | "
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

            # Prepare streaming callback
            _stream_chunks: List[str] = []
            _stream_has_tool_call = False

            def _stream_callback(token: str) -> None:
                """Print streaming tokens, but suppress if it's a tool call block."""
                nonlocal _stream_has_tool_call, _stream_chunks
                _stream_chunks.append(token)
                partial = "".join(_stream_chunks)
                if _looks_like_tool_call_stream(partial):
                    _stream_has_tool_call = True
                    return
                if not _stream_has_tool_call:
                    console.print(token, end="", highlight=False)

            try:
                with console.status("[dim]Thinking...[/dim]", spinner="dots") as status:
                    global _current_status
                    _current_status = status
                    try:
                        result = session.process_message(
                            user_text,
                            mode=session.run_mode,
                            use_streaming=session.use_streaming,
                            tool_callback=_tool_callback,
                            status_callback=_status_callback,
                            stream_callback=_stream_callback if session.use_streaming else None,
                        )
                        response = result["content"]
                    finally:
                        _current_status = None
            except Exception as e:
                console.print(f"[red]error:[/red] {type(e).__name__}: {str(e)[:200]}")
                continue

            if session.use_streaming and _stream_chunks and not _stream_has_tool_call:
                console.print()
                continue

            display_response = response
            if len(response) > 2000:
                lines = response.split('\n')
                if len(lines) > 50:
                    display_response = '\n'.join(lines[:20]) + f'\n\n... ({len(lines) - 40} lines omitted) ...\n\n' + '\n'.join(lines[-20:])
                else:
                    display_response = response[:1000] + f'\n\n... ({len(response) - 2000} chars omitted) ...\n\n' + response[-1000:]

            console.print(Panel(Markdown(display_response), title="assistant", style="green", border_style="green"))
    finally:
        if control_handle:
            control_handle.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
