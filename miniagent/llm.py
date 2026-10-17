"""Provider SDK boundary: reusable async client, plain messages and full streams."""
import inspect
import os

from any_llm import AnyLLM

from .harness import Plugin


class LLMBackend:
    def __init__(self, model, *, providers=None, api_key=None, base_url=None,
                 temperature=None, timeout=60, client=None):
        provider, separator, model_id = model.partition(":")
        if not separator:
            provider, model_id = "openai", model
        if not model_id:
            raise ValueError("Model ID is required")
        self.model, self.provider = model_id, provider
        self.temperature, self.timeout, self.usage = temperature, timeout, {}
        if client is not None:
            self.client = client
            return
        custom = (providers or {}).get(provider)
        if custom:
            if custom.get("type") != "openai-compatible" or not custom.get("base_url"):
                raise ValueError("Custom provider requires type and base_url")
            env = custom.get("api_key_env")
            if env and not api_key and not os.environ.get(env):
                raise ValueError(f"Missing provider credential environment: {env}")
            self.client = AnyLLM.create_openai_compatible(
                name=provider, api_base=custom["base_url"],
                api_key=api_key or (os.environ.get(env) if env else "local-no-key"),
                unified_exceptions=True, max_retries=0,
            )
        elif base_url:
            # An explicitly configured compatibility endpoint owns its explicit key.
            env = AnyLLM.get_provider_class(provider).ENV_API_KEY_NAME
            key = api_key or os.environ.get(env)
            if not key:
                raise ValueError(f"Missing credential: {env}")
            self.client = AnyLLM.create_openai_compatible(
                name=provider, api_base=base_url, api_key=key,
                unified_exceptions=True, max_retries=0,
            )
        else:
            self.client = AnyLLM.create(provider, api_key=api_key, unified_exceptions=True)

    async def complete(self, messages, tools, stream=None):
        options = {"model": self.model, "messages": messages, "timeout": self.timeout,
                   "stream": stream is not None}
        if tools:
            options["tools"] = tools
        if self.temperature is not None:
            options["temperature"] = self.temperature
        response = await self.client.acompletion(**options)
        self.usage = {}
        if stream is None:
            self.usage = response.usage.model_dump() if response.usage else {}
            return response.choices[0].message.model_dump(exclude_none=True)
        content, calls, reasoning, finish = [], {}, [], None
        try:
            async for chunk in response:
                if chunk.usage:
                    self.usage = chunk.usage.model_dump()
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                finish = choice.finish_reason or finish
                delta = choice.delta
                if delta.content:
                    content.append(delta.content)
                    result = stream(delta.content)
                    if inspect.isawaitable(result):
                        await result
                if getattr(delta, "reasoning_content", None):
                    reasoning.append(delta.reasoning_content)
                for part in delta.tool_calls or []:
                    call = calls.setdefault(part.index, {"id": "", "type": "function",
                        "function": {"name": "", "arguments": ""}})
                    if part.id:
                        call["id"] += part.id
                    if part.function:
                        for field in ("name", "arguments"):
                            call["function"][field] += getattr(part.function, field) or ""
            if finish not in {"stop", "tool_calls"}:
                raise RuntimeError("Incomplete LLM stream; no tools executed")
            result = {"role": "assistant", "content": "".join(content) or None}
            if calls:
                ordered = [calls[i] for i in sorted(calls)]
                if any(not c["id"] or not c["function"]["name"] for c in ordered):
                    raise ValueError("Incomplete streamed tool call")
                if len({c["id"] for c in ordered}) != len(ordered):
                    raise ValueError("Duplicate tool call IDs")
                result["tool_calls"] = ordered
            if reasoning:
                result["reasoning_content"] = "".join(reasoning)
            return result
        finally:
            close = getattr(response, "aclose", None)
            if close:
                await close()

    async def aclose(self):
        raw = getattr(self.client, "client", None)
        close = getattr(raw, "aclose", None) or getattr(raw, "close", None)
        if close:
            result = close()
            if inspect.isawaitable(result):
                await result


def llm_plugin(model, **options):
    def setup(ctx):
        backend = LLMBackend(model, **options)
        ctx.cleanup(backend.aclose)
        ctx.service("llm", backend)
    return Plugin("llm", setup)
