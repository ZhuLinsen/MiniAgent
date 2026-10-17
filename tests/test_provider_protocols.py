"""Exercise native SDK protocol conversion offline; these are not live tests."""
import asyncio
import json

import httpx
import pytest
from any_llm import AnyLLM
from openai import AsyncOpenAI

from miniagent import Harness, Plugin
from miniagent.llm import LLMBackend
from miniagent.policy import Policy
from miniagent.tools.registry import Tool


@pytest.mark.parametrize("provider", ["openai", "deepseek", "dashscope", "anthropic"])
def test_native_provider_two_turn_tool_protocol(provider):
    async def scenario():
        requests = []
        async def reply(request):
            body = json.loads(request.content)
            requests.append((request.url.path, body))
            if provider == "anthropic":
                content = ([{"type": "tool_use", "id": "one", "name": "add", "input": {"n": 2}}]
                           if len(requests) == 1 else [{"type": "text", "text": "done"}])
                payload = {"id": "response", "type": "message", "role": "assistant", "model": "fixture-model",
                           "content": content, "stop_reason": "tool_use" if len(requests) == 1 else "end_turn",
                           "stop_sequence": None, "usage": {"input_tokens": 4, "output_tokens": 2}}
            else:
                message = ({"role": "assistant", "content": None, "tool_calls": [{"id": "one", "type": "function",
                            "function": {"name": "add", "arguments": '{"n":2}'}}]}
                           if len(requests) == 1 else {"role": "assistant", "content": "done"})
                payload = {"id": "response", "object": "chat.completion", "created": 1, "model": "fixture-model",
                           "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls" if len(requests) == 1 else "stop"}],
                           "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6}}
            return httpx.Response(200, json=payload)
        client = AnyLLM.create(provider, api_key="fixture-key")
        await client.client.close()
        transport = httpx.AsyncClient(transport=httpx.MockTransport(reply))
        if provider == "anthropic":
            from anthropic import AsyncAnthropic
            client.client = AsyncAnthropic(api_key="fixture-key", base_url="https://fixture.invalid", http_client=transport)
        else:
            client.client = AsyncOpenAI(api_key="fixture-key", base_url="https://fixture.invalid/v1", http_client=transport)
        backend = LLMBackend(f"{provider}:fixture-model", client=client)
        app = Harness(backend, policy=Policy(mode="trusted"))
        app.use(Plugin("tools", lambda ctx: ctx.tool(Tool("add", "add one", {"type": "object",
            "properties": {"n": {"type": "integer"}}, "required": ["n"]}, lambda n: n + 1))))
        try:
            assert await app.arun("add one to two") == "done"
            assert len(requests) == 2
            if provider == "anthropic":
                assert requests[0][0] == "/v1/messages"
                assert requests[0][1]["tools"][0]["input_schema"]["required"] == ["n"]
                result = requests[1][1]["messages"][-1]["content"][0]
                assert result["type"] == "tool_result" and result["tool_use_id"] == "one" and result["content"] == "3"
            else:
                assert requests[0][0] == "/v1/chat/completions"
                assert requests[1][1]["messages"][-1] == {"role": "tool", "tool_call_id": "one", "content": "3"}
            assert backend.usage["total_tokens"] == 6
        finally:
            await app.aclose()
            await backend.aclose()
        assert transport.is_closed
    asyncio.run(scenario())
