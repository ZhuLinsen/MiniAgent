"""Small Rich CLI; one async runtime owns clients for the whole REPL."""
import os
import json
import sys
import time
from uuid import uuid4

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from .config import load_config
from .connections import PROVIDERS, connect, error_text, home, select_model
from .harness import Harness
from .llm import LLMBackend
from .plugins import coding_tools
from .policy import Policy
from .session import Session
from .skills import get_skill, list_skills, read_skill


def new_session():
    return Session(home() / "sessions" / f"{uuid4().hex}.jsonl")


async def cli_run(args, *, console=None, backend=None):
    console = console or Console()
    try:
        cfg = load_config(args.config, model_override=args.model, base_override=args.base_url,
                          temperature_override=args.temperature)
    except ValueError as error:
        console.print(Text(f"Configuration error: {error}", style="red"))
        return 2
    model = cfg.llm.model
    provider = model.partition(":")[0] if ":" in model else "openai"
    custom = cfg.providers.get(provider, {})
    needs_key = bool(custom.get("api_key_env")) if custom else provider in PROVIDERS
    needs_config = not model or (needs_key and not (args.api_key or cfg.llm.api_key))
    explicit_connect = getattr(args, "connect", False)
    if explicit_connect or (backend is None and needs_config and args.prompt is None and sys.stdin.isatty()):
        if not sys.stdin.isatty():
            console.print(Text("Interactive model configuration requires a TTY.", style="red"))
            return 2
        try:
            model = await connect(console, cfg)
            if explicit_connect:
                return 0
            cfg = load_config(args.config, model_override=model, base_override=args.base_url,
                              temperature_override=args.temperature)
        except (EOFError, KeyboardInterrupt):
            return 130
        except Exception as error:
            console.print(Text(f"Configuration failed: {error_text(error, cfg.llm.api_key, args.api_key)}", style="red"))
            return 2
    elif backend is None and needs_config:
        console.print(Text("Model is required. Set LLM_MODEL=provider:model-id, llm.model in JSON, or --model provider:model-id. A provider key alone does not select a model." if not model else
                           "Credential is required for the selected model. Export its provider key or use miniagent --connect.", style="red"))
        return 2
    def approve(name, arguments):
        if not sys.stdin.isatty():
            return False
        console.print(Text(f"Authorize {name}: {arguments}", style="yellow"))
        try:
            return Prompt.ask("Allow?", choices=["y", "n"], default="n", console=console) == "y"
        except (EOFError, KeyboardInterrupt):
            return False
    app = Harness(backend, model=None if backend else model, providers=cfg.providers,
                  api_key=args.api_key or cfg.llm.api_key, base_url=args.base_url or cfg.llm.api_base,
                  temperature=cfg.llm.temperature,
                  policy=Policy(args.workspace, mode=args.policy, approve=approve,
                                allow_sensitive_files=getattr(args, "allow_sensitive_files", False)),
                  session=Session(args.session) if args.session else new_session(),
                  context_budget=cfg.context_budget, system_prompt=cfg.system_prompt)
    app.use(coding_tools())
    for name, server in cfg.mcp_servers.items():
        from .extensions.mcp_plugin import mcp_plugin
        app.use(mcp_plugin(name, server["command"], server.get("args", []),
                           env=server.get("env"), cwd=str(app.policy.workspace)))
    if args.skill:
        skill = get_skill(args.skill) or read_skill(args.skill)
        app.apply_skill(skill)
    streaming = not args.no_stream and os.environ.get("MINIAGENT_STREAM", "1") != "0"
    starts, chunks = {}, []
    from .harness import Plugin
    def display(ctx):
        def start(event):
            starts[event["call_id"]] = time.monotonic()
            try:
                arguments = json.loads(event.get("arguments", "{}"))
                details = [f"{key}={str(value)[:120]!r}" if key in {"path", "pattern", "offset", "limit"}
                           else f"{key}=<{len(str(value))} chars>" for key, value in arguments.items()]
            except (ValueError, AttributeError):
                details = ["invalid arguments"]
            console.print(Text(f"  • {event['name']} {' '.join(details)[:240]}", style="cyan"))
        def end(event):
            elapsed = time.monotonic() - starts.pop(event["call_id"], time.monotonic())
            symbol = "failed" if event["error"] else "done"
            console.print(Text(f"  {symbol} {event['name']} · {elapsed:.2f}s", style="red" if event["error"] else "green"))
        ctx.on("tool.start", start)
        ctx.on("tool.end", end)
        ctx.on("llm.request", lambda event: chunks.clear())
        def response(event):
            if chunks:
                console.print()
            usage = event.get("usage") or {}
            if usage:
                console.print(Text(f"  usage: {usage.get('total_tokens', 'unavailable')} tokens", style="dim"))
        ctx.on("llm.response", response)
    app.use(Plugin("cli", display))
    def stream(token):
        chunks.append(token)
        console.print(Text(token), end="", highlight=False)
    async def ask(query):
        if console.is_terminal and args.prompt is not None:
            console.print(Panel(Text(query), title="You", border_style="bright_black"))
        answer = await app.arun(query, stream=stream if streaming else None)
        if not chunks:
            console.print(Markdown(answer) if console.is_terminal else Text(answer))
    async def switch_model(next_model):
        nonlocal model, cfg
        next_cfg = load_config(args.config, model_override=next_model, base_override=args.base_url,
                               temperature_override=args.temperature)
        candidate = LLMBackend(next_model, providers=next_cfg.providers,
                               api_key=args.api_key or next_cfg.llm.api_key, base_url=next_cfg.llm.api_base,
                               temperature=next_cfg.llm.temperature)
        try:
            if "llm" in app.plugins:
                await app.unuse("llm")
        except BaseException:
            await candidate.aclose()
            raise
        def install(ctx):
            ctx.cleanup(candidate.aclose)
            ctx.service("llm", candidate)
        app.use(Plugin("llm", install))
        await app.start()
        app.backend = None
        cfg, model, app.session, app.messages = next_cfg, next_model, new_session(), []
        app._base_temperature = candidate.temperature
        app.apply_skill(app.skill)
    try:
        async with app:
            if console.is_terminal:
                welcome = Text("MiniAgent", style="bold green")
                welcome.append("  /  Python harness + agent\n", style="dim")
                welcome.append(f"{model}  ·  {args.policy}\n", style="cyan")
                welcome.append(f"Workspace: {app.policy.workspace.name}  ·  Session: {app.session.path.stem[:8]}", style="dim")
                if args.prompt is None:
                    welcome.append("\n/help commands  ·  /connect models  ·  /q exit", style="dim")
                console.print(Panel(welcome, border_style="green", padding=(1, 2)))
            else:
                console.print(Text(f"MiniAgent · {model} · {app.policy.workspace}\nSession: {app.session.path}", style="dim"))
            if args.prompt is not None:
                await ask(args.prompt)
                return 0
            while True:
                try:
                    text = (Prompt.ask("❯", console=console) if sys.stdin.isatty() else sys.stdin.readline()).strip()
                    if not text:
                        if not sys.stdin.isatty():
                            break
                        continue
                    if text in {"/q", "/quit", "/exit"}:
                        break
                    if text == "/help":
                        commands = Table(box=None, padding=(0, 2), show_header=False)
                        for command, purpose in (
                            ("/connect", "Connect a provider"), ("/models", "Choose a model"),
                            ("/model [provider:model]", "Show or switch model; starts a new session"),
                            ("/plugins", "List active plugins"), ("/skills [name|path|off]", "List or switch Skills"),
                            ("/session [new]", "Inspect or start a session"),
                            ("/session resolve ID verified-result", "Record a verified result before resuming"),
                            ("/stream", "Toggle streaming"), ("/q", "Exit"),
                        ):
                            commands.add_row(Text(command, style="cyan"), Text(purpose))
                        console.print(commands)
                    elif text == "/plugins":
                        console.print(Text(", ".join(app.active)))
                    elif text.startswith("/skills"):
                        name = text.partition(" ")[2].strip()
                        if name:
                            app.apply_skill(None if name == "off" else get_skill(name) or read_skill(name))
                        console.print(Text(", ".join(list_skills())))
                    elif text.startswith("/session"):
                        command = text.split(" ", 3)
                        if len(command) > 1 and command[1] == "new":
                            app.session = new_session()
                            app.messages = []
                        else:
                            app.session.open()
                            try:
                                if len(command) == 4 and command[1] == "resolve":
                                    app.session.resolve(command[2], command[3])
                                console.print(Text(f"Uncertain calls: {sorted(app.session.uncertain)}"))
                            finally:
                                app.session.close()
                        console.print(Text(str(app.session.path)))
                    elif text in {"/connect", "/models"}:
                        if not sys.stdin.isatty():
                            raise ValueError("Interactive model configuration requires a TTY")
                        next_model = await (connect(console, cfg) if text == "/connect" else select_model(console, cfg))
                        await switch_model(next_model)
                    elif text == "/model" or text.startswith("/model "):
                        next_model = text.partition(" ")[2].strip()
                        if next_model:
                            await switch_model(next_model)
                        console.print(Text(model))
                    elif text == "/stream":
                        streaming = not streaming
                        console.print(Text(f"streaming: {streaming}"))
                    elif text.startswith("/"):
                        console.print(Text("Unknown command; use /help"))
                    else:
                        await ask(text)
                except EOFError:
                    break
                except Exception as error:
                    console.print(Text(f"Error: {error_text(error, cfg.llm.api_key, args.api_key)}", style="red"))
            return 0
    except Exception as error:
        console.print(Text(f"Error: {error_text(error, cfg.llm.api_key, args.api_key)}", style="red"))
        return 1
