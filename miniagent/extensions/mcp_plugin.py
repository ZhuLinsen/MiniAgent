"""Official MCP SDK integration; its context lives in one owner task."""
import asyncio

from ..harness import Plugin
from ..tools.registry import Tool


def mcp_plugin(name, command, args=(), *, env=None, cwd=None, timeout=30):
    async def setup(ctx):
        try:
            from mcp import Client, StdioServerParameters
        except ImportError as error:
            raise ImportError("Install miniagent[mcp] to use MCP") from error
        stop = asyncio.Event()
        ready = asyncio.get_running_loop().create_future()
        async def owner():
            try:
                parameters = StdioServerParameters(command=command, args=list(args), env=env, cwd=cwd)
                async with Client(parameters, read_timeout_seconds=timeout) as client:
                    ready.set_result(client)
                    await stop.wait()
            except BaseException as error:
                if not ready.done():
                    ready.set_exception(error)
                else:
                    raise
        task = asyncio.create_task(owner(), name=f"mcp:{name}")
        async def close():
            stop.set()
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout)
            except TimeoutError:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                raise
        ctx.cleanup(close)
        client = await asyncio.wait_for(asyncio.shield(ready), timeout)
        ctx.service(f"mcp:{name}", client)
        cursor = None
        seen = set()
        while True:
            page = await client.list_tools(cursor=cursor)
            for remote in page.tools:
                async def executor(_name=remote.name, **arguments):
                    if task.done():
                        raise ConnectionError("MCP connection is closed")
                    result = await client.call_tool(_name, arguments)
                    return result.model_dump(mode="json", exclude_none=True, by_alias=True)
                ctx.tool(Tool(f"{name}__{remote.name}", remote.description or remote.name,
                              remote.input_schema, executor, "external"))
            cursor = page.next_cursor
            if cursor is None:
                break
            if cursor in seen:
                raise ValueError("MCP repeated tool-list cursor")
            seen.add(cursor)
    return Plugin(f"mcp:{name}", setup)
