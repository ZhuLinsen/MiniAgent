"""Default Coding Tools composed as a plugin; shell explicitly authorized."""
import asyncio
import os
import signal
import subprocess

from .harness import Plugin
from .tools.registry import Tool
from .tools import code_tools, get_tool_description
from .utils.text_utils import smart_truncate


async def shell(cmd, *, cwd, timeout=0):
    timeout = timeout or int(os.environ.get("BASH_TIMEOUT", "120"))
    if timeout <= 0:
        raise ValueError("Shell timeout must be positive")
    limit = int(os.environ.get("BASH_MAX_OUTPUT", "50000"))
    if limit < 1:
        raise ValueError("Shell output limit must be positive")
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    process = await asyncio.create_subprocess_shell(
        cmd, cwd=cwd, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE, **options,
    )
    async def terminate():
        if os.name == "nt":
            killer = await asyncio.create_subprocess_exec(
                "taskkill", "/PID", str(process.pid), "/T", "/F",
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            )
            await killer.wait()
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        await process.wait()
    async def capture(pipe):
        head, tail, total = bytearray(), bytearray(), 0
        head_limit = max(1, int(limit * .7))
        tail_limit = limit - head_limit
        while chunk := await pipe.read(8192):
            total += len(chunk)
            missing = head_limit - len(head)
            head.extend(chunk[:max(0, missing)])
            tail.extend(chunk[max(0, missing):])
            if len(tail) > tail_limit:
                del tail[:len(tail) - tail_limit]
        marker = f"\n[truncated; {total} bytes total]\n".encode() if total > limit else b""
        return bytes(head) + marker + bytes(tail)
    try:
        out, err, _ = await asyncio.wait_for(asyncio.gather(
            capture(process.stdout), capture(process.stderr), process.wait()), timeout)
    except BaseException:
        await asyncio.shield(terminate())
        raise
    return {"exit_code": process.returncode,
            "stdout": smart_truncate(out.decode(errors="replace"), limit),
            "stderr": smart_truncate(err.decode(errors="replace"), limit)}


def coding_tools():
    def setup(ctx):
        for name in ("read", "write", "edit", "grep", "glob", "bash"):
            func = getattr(code_tools, name)
            description = get_tool_description(func)
            if name == "bash":
                async def executor(cmd, timeout=0):
                    return await shell(cmd, cwd=str(ctx.app.policy.workspace), timeout=timeout)
                access = "shell"
            else:
                def executor(_func=func, **kwargs):
                    token = code_tools._workspace.set(ctx.app.policy.workspace)
                    try:
                        return _func(**kwargs)
                    finally:
                        code_tools._workspace.reset(token)
                access = "write" if name in {"write", "edit"} else "read"
            ctx.tool(Tool(name, description["description"], description["parameters"], executor, access))
    return Plugin("tools", setup)
