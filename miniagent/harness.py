"""Small static plugin runtime with instance ownership and async cleanup."""
import asyncio
import inspect
from contextlib import AsyncExitStack
from dataclasses import dataclass

from .policy import Policy
from .tools.registry import Registry


@dataclass
class Plugin:
    name: str
    setup: object
    requires: tuple = ()


class Scope:
    def __init__(self, app):
        self.app, self.stack = app, AsyncExitStack()

    def service(self, name, value):
        if name in self.app.services:
            raise ValueError(f"Duplicate service: {name}")
        self.app.services[name] = value
        self.stack.callback(self.app.services.pop, name)

    def get(self, name):
        return self.app.services[name]

    def tool(self, tool):
        self.app.registry.add(tool)
        self.stack.callback(self.app.registry.tools.pop, tool.name)

    def on(self, event, callback):
        listeners = self.app.events.setdefault(event, [])
        listeners.append(callback)
        self.stack.callback(listeners.remove, callback)

    def cleanup(self, callback, *args):
        if inspect.iscoroutinefunction(callback):
            self.stack.push_async_callback(callback, *args)
        else:
            self.stack.callback(callback, *args)


class Harness:
    def __init__(self, backend=None, *, model=None, providers=None, api_key=None,
                 base_url=None, temperature=None, policy=None,
                 session=None, context_budget=32768,
                 system_prompt="You are a helpful assistant."):
        self.services, self.events, self.plugins, self.active = {}, {}, {}, {}
        self.registry = Registry()
        self.policy = policy or Policy()
        self.system_prompt, self.backend = system_prompt, backend
        self.messages = []
        self.busy = False
        self.session, self.context_budget = session, context_budget
        if model:
            from .llm import llm_plugin
            self.use(llm_plugin(model, providers=providers, api_key=api_key,
                                base_url=base_url, temperature=temperature))

    def _idle(self):
        if self.busy:
            raise RuntimeError("Harness is running; plugin changes are disabled")

    def use(self, plugin):
        self._idle()
        if plugin.name in self.plugins:
            raise ValueError(f"Duplicate plugin: {plugin.name}")
        self.plugins[plugin.name] = plugin
        return self

    async def start(self):
        self._idle()
        await self._start()

    async def _start(self):
        pending = {n: p for n, p in self.plugins.items() if n not in self.active}
        added = []
        try:
            while pending:
                ready = [p for p in pending.values() if all(n in self.active for n in p.requires)]
                if not ready:
                    raise ValueError("Missing or cyclic plugin dependency")
                for plugin in ready:
                    scope = Scope(self)
                    try:
                        result = plugin.setup(scope)
                        if inspect.isawaitable(result):
                            await result
                    except BaseException:
                        await scope.stack.aclose()
                        raise
                    self.active[plugin.name] = scope
                    added.append(plugin.name)
                    pending.pop(plugin.name)
        except BaseException as failure:
            errors = [failure]
            for name in reversed(added):
                try:
                    await self.active.pop(name).stack.aclose()
                except BaseException as error:
                    errors.append(error)
            if len(errors) > 1:
                raise BaseExceptionGroup("Plugin activation and rollback failed", errors)
            raise

    async def unuse(self, name):
        self._idle()
        if any(name in self.plugins[n].requires for n in self.active if n != name):
            raise ValueError("Plugin has active dependents")
        scope = self.active.pop(name, None)
        if scope:
            await scope.stack.aclose()
        self.plugins.pop(name)

    async def emit(self, event, **payload):
        for callback in tuple(self.events.get(event, ())):
            try:
                result = callback(payload)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                # Observers do not control authorization or terminate the run.
                from .logger import get_logger
                get_logger(__name__).warning("Event observer failed: %s", event)

    async def aclose(self):
        self._idle()
        errors = []
        for name in reversed(tuple(self.active)):
            try:
                await self.active.pop(name).stack.aclose()
            except BaseException as error:
                errors.append(error)
        if errors:
            raise BaseExceptionGroup("Plugin cleanup failures", errors)

    async def arun(self, query, *, max_steps=10, stream=None):
        self._idle()
        self.busy = True
        try:
            if self.session:
                self.session.open()
                if self.session.uncertain:
                    raise RuntimeError("Session has uncertain tool results; inspect and resolve them first")
                self.messages = self.session.messages
            await self._start()
            from .agent import agent_loop
            return await agent_loop(self, query, max_steps=max_steps, stream=stream)
        finally:
            self.busy = False
            if self.session:
                self.session.close()

    def record(self, message, *, tool=False):
        if self.session:
            self.session.append("tool_completed" if tool else "message", message=message)
        self.messages.append(message)

    def run(self, query, **kwargs):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            async def once():
                try:
                    return await self.arun(query, **kwargs)
                finally:
                    await self.aclose()
            return asyncio.run(once())
        raise RuntimeError("Use await app.arun() inside an event loop")

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *exc):
        await self.aclose()
