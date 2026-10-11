"""Native agent loop; the legacy teaching API is a compatibility import."""
import json
import os

from .utils.text_utils import smart_truncate


def __getattr__(name):
    if name in {"MiniAgent", "_DANGEROUS_RE"}:
        from . import legacy
        return getattr(legacy, name)
    raise AttributeError(name)


async def agent_loop(app, query, *, max_steps=10, stream=None):
    """Native loop shared by the Harness; messages never contain SDK objects."""
    if max_steps < 1:
        raise ValueError("max_steps must be positive")
    backend = app.backend or app.services.get("llm")
    if backend is None:
        raise ValueError("An LLM backend is required")
    if not app.messages:
        app.record({"role": "system", "content": app.system_prompt})
    app.record({"role": "user", "content": query})
    for step in range(max_steps):
        await app.emit("agent.step", step=step)
        await app.emit("llm.request", step=step)
        from .session import context_view
        view = await context_view(app, backend)
        message = await backend.complete(view, app.registry.schemas(), stream)
        await app.emit("llm.response", usage=getattr(backend, "usage", {}))
        calls = message.get("tool_calls") or []
        previous = {c["id"] for m in app.messages for c in m.get("tool_calls", [])}
        current = set()
        for call in calls:
            identifier = call.get("id")
            function = call.get("function") or {}
            if not identifier or identifier in previous or identifier in current:
                raise ValueError("Missing or reused tool call ID")
            if not isinstance(function.get("name"), str) or not isinstance(function.get("arguments"), str):
                raise ValueError("Malformed tool call")
            current.add(identifier)
        app.record(message)
        if not calls:
            return message.get("content") or ""
        for call in calls:
            name = call["function"]["name"]
            await app.emit("tool.start", name=name, call_id=call["id"], arguments=call["function"]["arguments"])
            started_effect = False
            uncertain = False
            try:
                args = json.loads(call["function"]["arguments"])
                if not isinstance(args, dict):
                    raise ValueError("Tool arguments must be an object")
                def started():
                    nonlocal started_effect
                    started_effect = app.registry.get(name).access != "read"
                    app._started_calls.add(call["id"])
                    if app.session:
                        app.session.append("tool_started", call_id=call["id"])
                result = await app.registry.execute(name, args, app.policy, started)
                content = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)
                error = isinstance(result, dict) and bool(result.get("isError") or result.get("error") or result.get("exit_code", 0))
            except Exception as exc:
                content, error = f"Tool failed: {type(exc).__name__}: {exc}", True
                uncertain = started_effect
            content = smart_truncate(content, int(os.environ.get("TOOL_RESULT_LIMIT", "16000")))
            app.record({"role": "tool", "tool_call_id": call["id"], "content": content}, tool=True, uncertain=uncertain)
            await app.emit("tool.end", name=name, call_id=call["id"], error=error)
            if uncertain:
                raise RuntimeError("Tool result is uncertain; inspect effects and resolve before continuing")
    raise RuntimeError("Agent reached max_steps before a final answer")
