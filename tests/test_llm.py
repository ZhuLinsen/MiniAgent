import asyncio
import json
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import httpx
import pytest
from any_llm import AnyLLM

from miniagent.llm import LLMBackend


def test_custom_endpoint_and_native_response():
    async def scenario():
        requests = []
        async def reply(request):
            requests.append(request)
            return httpx.Response(200, json={"id": "r", "object": "chat.completion", "created": 1,
                "model": "test", "choices": [{"index": 0, "finish_reason": "stop",
                "message": {"role": "assistant", "content": "hello"}}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3}})
        provider = AnyLLM.create_openai_compatible("mock", "https://test.invalid/v1", api_key="test")
        await provider.client.close()
        from openai import AsyncOpenAI
        provider.client = AsyncOpenAI(api_key="test", base_url="https://test.invalid/v1",
                                     http_client=httpx.AsyncClient(transport=httpx.MockTransport(reply)))
        backend = LLMBackend("mock:test", client=provider)
        result = await backend.complete([{"role": "user", "content": "hi"}], [], None)
        assert result["content"] == "hello" and backend.usage["total_tokens"] == 3
        assert requests[0].url.path == "/v1/chat/completions"
        await backend.aclose()
        assert provider.client.is_closed()
    asyncio.run(scenario())


def test_stream_multiple_tool_calls_and_close():
    async def scenario():
        closed = []
        async def chunks():
            try:
                for i, args in [(0, '{"n":'), (1, '{"n":')]:
                    yield NS(usage=None, choices=[NS(finish_reason=None, delta=NS(content=None,
                        tool_calls=[NS(index=i, id=f"id{i}", function=NS(name="add", arguments=args))]))])
                for i in (0, 1):
                    yield NS(usage=None, choices=[NS(finish_reason=None, delta=NS(content=None,
                        tool_calls=[NS(index=i, id=None, function=NS(name=None, arguments="2}"))]))])
                yield NS(usage=None, choices=[NS(finish_reason="tool_calls", delta=NS(content=None, tool_calls=[]))])
            finally:
                closed.append(True)
        backend = LLMBackend("mock:test", client=NS(acompletion=AsyncMock(return_value=chunks())))
        result = await backend.complete([], [], lambda text: None)
        assert [json.loads(c["function"]["arguments"]) for c in result["tool_calls"]] == [{"n": 2}, {"n": 2}]
        assert closed
    asyncio.run(scenario())


def test_incomplete_stream_cannot_execute():
    async def chunks():
        yield NS(usage=None, choices=[NS(finish_reason=None, delta=NS(content="partial", tool_calls=[]))])
    async def scenario():
        backend = LLMBackend("mock:test", client=NS(acompletion=AsyncMock(return_value=chunks())))
        with pytest.raises(RuntimeError, match="Incomplete"):
            await backend.complete([], [], lambda text: None)
    asyncio.run(scenario())


def test_custom_provider_does_not_use_openai_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "wrong")
    monkeypatch.delenv("CUSTOM_KEY", raising=False)
    with pytest.raises(ValueError, match="CUSTOM_KEY"):
        LLMBackend("custom:test", providers={"custom": {
            "type": "openai-compatible", "base_url": "https://test.invalid/v1", "api_key_env": "CUSTOM_KEY"}})


def test_stream_preserves_signed_provider_metadata():
    async def chunks():
        yield NS(usage=None, choices=[NS(finish_reason=None, delta=NS(content=None,
            reasoning=NS(content="reason"), extra_content={"anthropic": {"signature": "sig"}},
            tool_calls=[NS(index=0, id="one", function=NS(name="add", arguments="{}"),
                           extra_content={"google": {"thought_signature": "opaque"}})]))])
        yield NS(usage=None, choices=[NS(finish_reason="tool_calls", delta=NS(content=None,
            extra_content={"anthropic": {"signature": "nature"}}, tool_calls=[]))])
    async def scenario():
        backend = LLMBackend("mock:test", client=NS(acompletion=AsyncMock(return_value=chunks())))
        result = await backend.complete([], [], lambda text: None)
        assert result["reasoning_content"] == "reason"
        assert result["extra_content"]["anthropic"]["signature"] == "signature"
        assert result["tool_calls"][0]["extra_content"]["google"]["thought_signature"] == "opaque"
    asyncio.run(scenario())


def test_provider_resolution_isolated(monkeypatch):
    from miniagent.config import load_config
    monkeypatch.setenv("LLM_MODEL", "anthropic:test")
    monkeypatch.setenv("OPENAI_API_KEY", "wrong")
    for key in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE"):
        monkeypatch.delenv(key, raising=False)
    assert load_config().llm.api_key is None


@pytest.mark.live
def test_live_provider():
    import os
    model = os.environ.get("MINIAGENT_TEST_MODEL")
    if not model:
        pytest.skip("Set MINIAGENT_TEST_MODEL and provider credentials for a live smoke test")
    async def scenario():
        backend = LLMBackend(model)
        try:
            result = await backend.complete([{"role": "user", "content": "Say hello."}], [])
            assert result.get("content")
        finally:
            await backend.aclose()
    asyncio.run(scenario())


@pytest.mark.live
@pytest.mark.parametrize("streaming", [False, True])
def test_live_multi_turn_tool_call(streaming):
    import os
    from miniagent import Harness, Plugin
    from miniagent.policy import Policy
    from miniagent.tools.registry import Tool
    model = os.environ.get("MINIAGENT_TEST_MODEL")
    if not model:
        pytest.skip("Set MINIAGENT_TEST_MODEL and provider credentials for live tool acceptance")
    async def scenario():
        backend = LLMBackend(model)
        app = Harness(backend, policy=Policy(mode="trusted"), system_prompt=
                      "Use the add_one tool with n=2 before answering. Report the tool result.")
        app.use(Plugin("tools", lambda ctx: ctx.tool(Tool("add_one", "Add one to an integer",
            {"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]}, lambda n: n + 1))))
        chunks = []
        try:
            result = await app.arun("Calculate 2 plus 1 using add_one.", stream=chunks.append if streaming else None)
            assert result and any(m["role"] == "tool" and m["content"] == "3" for m in app.messages)
            if streaming:
                assert chunks
        finally:
            await app.aclose()
            await backend.aclose()
    asyncio.run(scenario())
