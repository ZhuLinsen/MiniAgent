import asyncio
import json

import pytest

from miniagent import Harness, Plugin
from miniagent.policy import Policy
from miniagent.session import Session, compact
from miniagent.tools.registry import Tool


def call(identifier):
    return {"role": "assistant", "content": None, "tool_calls": [{"id": identifier,
        "type": "function", "function": {"name": "write", "arguments": "{}"}}]}


def test_lock_tail_recovery_and_unknown_resolution(tmp_path):
    path = tmp_path / "session.jsonl"
    session = Session(path).open()
    session.append("message", message={"role": "user", "content": "change"})
    session.append("message", message=call("one"))
    session.append("tool_started", call_id="one")
    with pytest.raises(OSError):
        Session(path).open()
    session.close()
    with open(path, "ab") as file:
        file.write(b'{"interrupted":')
    restored = Session(path).open()
    assert restored.uncertain == {"one"}
    assert restored.messages[-1]["tool_call_id"] == "one"
    restored.resolve("one", "Verified file change exists; do not repeat")
    assert not restored.uncertain
    assert restored.messages[-1]["content"].startswith("Verified")
    restored.close()
    again = Session(path).open()
    assert len(again.messages) == 3
    assert not again.uncertain
    again.close()


def test_unstarted_calls_not_replayed(tmp_path):
    session = Session(tmp_path / "session").open()
    session.append("message", message=call("one"))
    session.close()
    session.open()
    assert not session.uncertain
    assert "not replayed" in session.messages[-1]["content"]
    session.close()


def test_corruption_is_not_silently_ignored(tmp_path):
    path = tmp_path / "session"
    path.write_text('{"version": 99, "sequence": 0, "type": "message"}\n')
    with pytest.raises(ValueError):
        Session(path).open()
    path.write_text('bad json\n')
    with pytest.raises(json.JSONDecodeError):
        Session(path).open()


def test_compaction_preserves_tool_groups_and_originals():
    messages = [{"role": "system", "content": "sys"}]
    for i in range(15):
        messages += [{"role": "user", "content": "x" * 200}, call(str(i)),
                     {"role": "tool", "tool_call_id": str(i), "content": "result" * 30}]
    before = json.dumps(messages)
    view = compact(messages, 4096)
    assert len(view) < len(messages)
    assert json.dumps(messages) == before
    ids = set()
    for message in view:
        ids.update(c["id"] for c in message.get("tool_calls", []))
        if message["role"] == "tool":
            assert message["tool_call_id"] in ids
    with pytest.raises(ValueError):
        compact([{ "role": "user", "content": "x" * 10000}], 2048)


def test_session_continuity_and_no_duplicate_users(tmp_path):
    class Backend:
        async def complete(self, messages, tools, stream):
            return {"role": "assistant", "content": "done"}
    session = Session(tmp_path / "session")
    first = Harness(Backend(), session=session)
    assert first.run("first") == "done"
    second = Harness(Backend(), session=Session(session.path))
    assert second.run("second") == "done"
    assert [m["content"] for m in second.messages if m["role"] == "user"] == ["first", "second"]


def test_cancellation_cannot_replay_side_effect(tmp_path):
    async def scenario():
        began = asyncio.Event()
        count = []
        async def effect():
            count.append(1)
            began.set()
            await asyncio.sleep(30)
        class Backend:
            async def complete(self, messages, tools, stream):
                return call("one")
        app = Harness(Backend(), policy=Policy(mode="trusted"), session=Session(tmp_path / "s"))
        app.use(Plugin("tools", lambda ctx: ctx.tool(Tool("write", "effect", {"type": "object"}, effect))))
        task = asyncio.create_task(app.arun("go"))
        await began.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        with pytest.raises(RuntimeError, match="uncertain"):
            await app.arun("resume")
        assert count == [1]
        await app.aclose()
    asyncio.run(scenario())
