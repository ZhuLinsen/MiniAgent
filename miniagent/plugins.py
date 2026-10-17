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
    try:
        out, err = await asyncio.wait_for(process.communicate(), timeout)
    except BaseException:
        await asyncio.shield(terminate())
        raise
    limit = int(os.environ.get("BASH_MAX_OUTPUT", "50000"))
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
