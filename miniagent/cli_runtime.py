"""Small Rich CLI; one async runtime owns clients for the whole REPL."""
import os
import json
import sys
import time
from pathlib import Path
from uuid import uuid4

from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.text import Text

from .config import load_config
from .harness import Harness
from .llm import LLMBackend
from .plugins import coding_tools
from .policy import Policy
from .session import Session
from .skills import get_skill, list_skills, read_skill


def new_session():
    home = Path(os.environ.get("MINIAGENT_HOME", str(Path.home() / ".miniagent")))
    return Session(home / "sessions" / f"{uuid4().hex}.jsonl")


async def cli_run(args, *, console=None, backend=None):
    console = console or Console()
    cfg = load_config(args.config, model_override=args.model, base_override=args.base_url)
    model = args.model or cfg.llm.model
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
                  temperature=args.temperature if args.temperature is not None else cfg.llm.temperature,
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
            console.print(Text(f"  {symbol} {event['name']} · {elapsed:.2f}s"))
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
        answer = await app.arun(query, stream=stream if streaming else None)
        if not chunks:
            console.print(Markdown(answer) if console.is_terminal else Text(answer))
    try:
        async with app:
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
                        console.print(Text("/model provider:model · /plugins · /skills [name|path|off]\n/session [new|resolve ID verified-result] · /stream · /help · /q"))
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
                    elif text.startswith("/model"):
                        next_model = text.partition(" ")[2].strip()
                        if next_model:
                            next_cfg = load_config(args.config, model_override=next_model)
                            candidate = LLMBackend(next_model, providers=next_cfg.providers,
                                                   api_key=next_cfg.llm.api_key, base_url=next_cfg.llm.api_base,
                                                   temperature=next_cfg.llm.temperature)
                            try:
                                await app.unuse("llm")
                            except BaseException:
                                await candidate.aclose()
                                raise
                            def install(ctx):
                                ctx.cleanup(candidate.aclose)
                                ctx.service("llm", candidate)
                            app.use(Plugin("llm", install))
                            await app.start()
                            model, app.session, app.messages = next_model, new_session(), []
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
                    console.print(Text(f"Error: {type(error).__name__}: {error}", style="red"))
            return 0
    except Exception as error:
        console.print(Text(f"Error: {type(error).__name__}: {error}", style="red"))
        return 1
