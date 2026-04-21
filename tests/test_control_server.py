"""Tests for the HTTP control plane."""

from __future__ import annotations

import json
import threading
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener
from queue import Empty, Queue

import pytest

from miniagent.cli import AgentSession
from miniagent.control_server import AgentBusyError, parse_control_http_address, start_control_server
from miniagent.diagnostics import BootstrapReport
from miniagent.memory import Memory


_DIRECT_OPENER = build_opener(ProxyHandler({}))


class _FakeRuntime:
    def __init__(self):
        self.calls = []

    def get_session_info(self):
        return {
            "ok": True,
            "model": "fake-model",
            "profile": "demo_profile",
            "skill": "demo_skill",
            "tools": ["calculator"],
            "history_length": 2,
            "streaming_default": False,
            "mode": "text",
            "control_http": "127.0.0.1:0",
        }

    def get_history(self, limit=20):
        items = [
            {"role": "user", "content": "compute 2+42"},
            {"role": "assistant", "content": "44"},
        ]
        return items[-limit:] if limit else items

    def process_message(
        self,
        text,
        *,
        mode=None,
        use_streaming=None,
        capture_events=False,
        event_callback=None,
    ):
        self.calls.append({
            "text": text,
            "mode": mode,
            "use_streaming": use_streaming,
            "capture_events": capture_events,
        })

        if text == "busy":
            raise AgentBusyError("busy")

        if text == "explode":
            raise RuntimeError("boom")

        events = [
            {"type": "assistant.thinking", "iteration": 1, "text": "Thinking (Iteration 1)..."},
            {"type": "tool.start", "name": "calculator", "arguments": {"expression": "2 + 42"}},
            {"type": "tool.end", "name": "calculator", "result": {"expression": "2 + 42", "result": 44}},
        ]
        if use_streaming:
            events.extend([
                {"type": "assistant.delta", "delta": "The result is "},
                {"type": "assistant.delta", "delta": "44."},
            ])
        events.append({"type": "assistant.final", "content": "The result is 44."})

        if event_callback is not None:
            for event in events:
                event_callback(event)

        return {
            "content": "The result is 44.",
            "events": events,
        }


class _BlockingStubAgent:
    def __init__(self):
        self.model = "stub-model"
        self.tools = [{"name": "calculator", "description": "Calculate an expression"}]
        self.tool_started = threading.Event()
        self.allow_finish = threading.Event()

    def run_with_tools(self, query, tool_callback=None, status_callback=None, stream_callback=None):
        if status_callback:
            status_callback("Thinking (Iteration 1)...")
        if tool_callback:
            tool_callback("start", "calculator", {"arguments": {"expression": "2 + 42"}})

        self.tool_started.set()
        assert self.allow_finish.wait(timeout=5), "test timed out waiting to release the stub agent"

        if tool_callback:
            tool_callback("end", "calculator", {"result": {"expression": "2 + 42", "result": 44}})
        if stream_callback:
            stream_callback("The result is ")
            stream_callback("44.")
        return "The result is 44."


def _get_json(url: str, headers=None):
    request = Request(url, headers=headers or {})
    with _DIRECT_OPENER.open(request) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload, headers=None):
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with _DIRECT_OPENER.open(request) as response:
        return json.loads(response.read().decode("utf-8"))


def _stream_json_lines(url: str, payload, headers=None):
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with _DIRECT_OPENER.open(request) as response:
        return [
            json.loads(line.decode("utf-8"))
            for line in response.readlines()
            if line.strip()
        ]


def test_parse_control_http_address_supports_port_only():
    assert parse_control_http_address("8765") == ("127.0.0.1", 8765)


def test_control_server_endpoints(monkeypatch):
    monkeypatch.delenv("MINIAGENT_CONTROL_TOKEN", raising=False)

    runtime = _FakeRuntime()
    handle = start_control_server(runtime, "127.0.0.1:0")
    base_url = f"http://{handle.address}"

    try:
        assert _get_json(f"{base_url}/healthz") == {"ok": True}

        session = _get_json(f"{base_url}/v1/session")
        assert session["model"] == "fake-model"
        assert session["tools"] == ["calculator"]

        history = _get_json(f"{base_url}/v1/history?limit=1")
        assert history["messages"] == [{"role": "assistant", "content": "44"}]

        result = _post_json(
            f"{base_url}/v1/message",
            {"text": "compute 2+42", "stream": False, "mode": "text", "request_id": "req-1"},
        )
        assert result["ok"] is True
        assert result["content"] == "The result is 44."
        assert result["events"][0] == {"type": "request.accepted", "request_id": "req-1"}
        assert result["events"][-1] == {"type": "request.complete", "ok": True, "request_id": "req-1"}
        assert runtime.calls[0]["capture_events"] is True
        assert runtime.calls[0]["use_streaming"] is False
    finally:
        handle.close()


def test_control_server_streams_ndjson_events(monkeypatch):
    monkeypatch.delenv("MINIAGENT_CONTROL_TOKEN", raising=False)

    runtime = _FakeRuntime()
    handle = start_control_server(runtime, "127.0.0.1:0")
    base_url = f"http://{handle.address}"

    try:
        events = _stream_json_lines(
            f"{base_url}/v1/message",
            {"text": "compute 2+42", "stream": True, "request_id": "req-stream"},
        )
        assert events[0] == {"type": "request.accepted", "request_id": "req-stream"}
        assert any(event["type"] == "tool.start" for event in events)
        assert any(event["type"] == "tool.end" for event in events)
        assert any(event["type"] == "assistant.delta" for event in events)
        assert events[-1] == {"type": "request.complete", "ok": True, "request_id": "req-stream"}
        assert runtime.calls[0]["use_streaming"] is True
        assert runtime.calls[0]["capture_events"] is False
    finally:
        handle.close()


def test_control_server_enforces_token_when_configured(monkeypatch):
    monkeypatch.setenv("MINIAGENT_CONTROL_TOKEN", "secret-token")

    runtime = _FakeRuntime()
    handle = start_control_server(runtime, "127.0.0.1:0")
    base_url = f"http://{handle.address}"

    try:
        with pytest.raises(HTTPError) as exc_info:
            _get_json(f"{base_url}/v1/session")
        assert exc_info.value.code == 401

        session = _get_json(
            f"{base_url}/v1/session",
            headers={"Authorization": "Bearer secret-token"},
        )
        assert session["skill"] == "demo_skill"
    finally:
        handle.close()


def test_control_server_streaming_is_incrementally_readable(tmp_path, monkeypatch):
    monkeypatch.delenv("MINIAGENT_CONTROL_TOKEN", raising=False)

    agent = _BlockingStubAgent()
    report = BootstrapReport(selected_tools=["calculator"])
    memory = Memory(path=tmp_path / "memory.json")
    session = AgentSession(
        agent=agent,
        memory=memory,
        bootstrap_report=report,
        strict_mode=False,
        use_streaming=True,
        run_mode="text",
    )

    handle = start_control_server(session, "127.0.0.1:0")
    base_url = f"http://{handle.address}"
    events = Queue()
    errors = Queue()

    def _reader():
        body = json.dumps({
            "text": "compute 2+42",
            "stream": True,
            "mode": "text",
            "request_id": "req-live",
        }).encode("utf-8")
        request = Request(
            f"{base_url}/v1/message",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with _DIRECT_OPENER.open(request, timeout=5) as response:
                for raw_line in response:
                    if raw_line.strip():
                        events.put(json.loads(raw_line.decode("utf-8")))
        except Exception as exc:  # pragma: no cover - test failure path
            errors.put(exc)
        finally:
            events.put(None)

    reader = threading.Thread(target=_reader, daemon=True)
    reader.start()

    try:
        first = events.get(timeout=5)
        second = events.get(timeout=5)
        third = events.get(timeout=5)

        assert first == {"type": "request.accepted", "request_id": "req-live"}
        assert second["type"] == "assistant.thinking"
        assert third["type"] == "tool.start"

        assert agent.tool_started.wait(timeout=5)

        with pytest.raises(Empty):
            events.get(timeout=0.2)

        agent.allow_finish.set()
        reader.join(timeout=5)
        assert not reader.is_alive()
        assert errors.empty()

        remaining = []
        while True:
            item = events.get(timeout=5)
            if item is None:
                break
            remaining.append(item)

        assert any(event["type"] == "tool.end" for event in remaining)
        assert any(event["type"] == "assistant.delta" for event in remaining)
        assert any(event["type"] == "assistant.final" for event in remaining)
        assert remaining[-1] == {"type": "request.complete", "ok": True, "request_id": "req-live"}
    finally:
        agent.allow_finish.set()
        handle.close()
