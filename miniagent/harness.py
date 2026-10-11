"""Plugin runtime with instance ownership, async cleanup and opt-in reconciliation."""
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
    inject: tuple = ()


class Scope:
    def __init__(self, app):
        self.app, self.stack = app, AsyncExitStack()
        self.provided, self.setting_up, self.closed = set(), True, False

    def _registration(self):
        if self.closed:
            raise RuntimeError("Plugin scope is closed")
        if not self.setting_up:
            self.app._idle()

    def service(self, name, value):
        self._registration()
        if name in self.app.services:
            raise ValueError(f"Duplicate service: {name}")
        self.app.services[name] = value
        self.provided.add(name)
        self.stack.callback(self.app.services.pop, name)

    def get(self, name):
        return self.app.services[name]

    def tool(self, tool):
        self._registration()
        self.app.registry.add(tool)
        self.stack.callback(self.app.registry.tools.pop, tool.name)

    def on(self, event, callback):
        self._registration()
        listeners = self.app.events.setdefault(event, [])
        listeners.append(callback)
        self.stack.callback(listeners.remove, callback)

    def cleanup(self, callback, *args):
        self._registration()
        async def invoke():
            result = callback(*args)
            if inspect.isawaitable(result):
                await result
        self.stack.push_async_callback(invoke)


class Harness:
    def __init__(self, backend=None, *, model=None, providers=None, api_key=None,
                 base_url=None, temperature=None, policy=None,
                 session=None, context_budget=32768, reactive=False,
                 system_prompt="You are a helpful assistant."):
        self.services, self.events, self.plugins, self.active = {}, {}, {}, {}
        self.registry = Registry()
        self.policy = policy or Policy()
        self.system_prompt, self.backend = system_prompt, backend
        self.messages = []
        self._started_calls, self._uncertain = set(), set()
        self.busy = False
        self.session, self.context_budget = session, context_budget
        self._base_prompt = system_prompt
        self._base_temperature = temperature
        self.skill = None
        self.reactive = reactive
        from .agent import loop_plugin
        self.use(loop_plugin())
        if model:
            from .llm import llm_plugin
            self.use(llm_plugin(model, providers=providers, api_key=api_key,
                                base_url=base_url, temperature=temperature))

    def apply_skill(self, skill=None):
        self._idle()
        self.registry.allowed = set(skill.tools) if skill and skill.tools is not None else None
        self.system_prompt = self._base_prompt + ("\n\n" + skill.prompt if skill else "")
        self.skill = skill
        if self.messages:
            # Prompt is a per-run view; original Session records remain intact.
            self.messages = [m for m in self.messages if m["role"] != "system"]
            self.messages.insert(0, {"role": "system", "content": self.system_prompt})
        backend = self.backend or self.services.get("llm")
        if backend and hasattr(backend, "temperature"):
            backend.temperature = skill.temperature if skill and skill.temperature is not None else self._base_temperature

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
        self.busy = True
        try:
            await self._start()
        finally:
            self.busy = False

    async def _start(self):
        self._check_cycles()
        pending = {n: p for n, p in self.plugins.items() if n not in self.active}
        added = []
        try:
            while pending:
                ready = [p for p in pending.values() if all(n in self.active for n in p.requires)
                         and all(n in self.services for n in p.inject)]
                if not ready:
                    if self.reactive:
                        break  # Registered dependents wait for a later start/provider change.
                    raise ValueError("Missing or cyclic plugin dependency")
                for plugin in ready:
                    scope = Scope(self)
                    try:
                        result = plugin.setup(scope)
                        if inspect.isawaitable(result):
                            await result
                    except BaseException as failure:
                        scope.closed = True
                        try:
                            await scope.stack.aclose()
                        except BaseException as error:
                            raise BaseExceptionGroup("Plugin setup and cleanup failed", [failure, error])
                        raise
                    finally:
                        scope.setting_up = False
                    self.active[plugin.name] = scope
                    added.append(plugin.name)
                    pending.pop(plugin.name)
        except BaseException as failure:
            errors = [failure, *await self._close_scopes(reversed(added))]
            if len(errors) > 1:
                raise BaseExceptionGroup("Plugin activation and rollback failed", errors)
            raise

    @property
    def states(self):
        return {name: "ACTIVE" if name in self.active else "PENDING" for name in self.plugins}

    def _check_cycles(self):
        visited = set()
        def visit(name, path):
            if name in path:
                raise ValueError("Cyclic plugin dependency")
            if name not in visited:
                for dependency in self.plugins[name].requires:
                    if dependency in self.plugins:
                        visit(dependency, path | {name})
                visited.add(name)
        for name in self.plugins:
            visit(name, set())

    async def _close_scopes(self, names):
        errors = []
        for name in names:
            scope = self.active.pop(name)
            scope.closed = True
            try:
                await scope.stack.aclose()
            except BaseException as error:
                errors.append(error)
        return errors

    async def unuse(self, name):
        self._idle()
        if name not in self.plugins:
            raise KeyError(name)
        removed, services = {name}, set()
        while True:
            services.update(s for n in removed if n in self.active for s in self.active[n].provided)
            dependents = {n for n in self.active if set(self.plugins[n].requires) & removed
                          or set(self.plugins[n].inject) & services}
            if dependents <= removed:
                break
            removed.update(dependents)
        if not self.reactive and removed != {name}:
            raise ValueError("Plugin has active dependents")
        self.busy = True
        try:
            errors = await self._close_scopes(n for n in reversed(tuple(self.active)) if n in removed)
            self.plugins.pop(name)
            if errors:
                raise BaseExceptionGroup("Plugin cleanup failures", errors)
            if self.reactive:
                await self._start()
        finally:
            self.busy = False

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
        self.busy = True
        try:
            errors = await self._close_scopes(reversed(tuple(self.active)))
            if errors:
                raise BaseExceptionGroup("Plugin cleanup failures", errors)
        finally:
            self.busy = False

    async def arun(self, query, *, max_steps=None, stream=None):
        self._idle()
        self.busy = True
        try:
            if self.session:
                self.session.open()
                if self.session.uncertain:
                    raise RuntimeError("Session has uncertain tool results; inspect and resolve them first")
                self.messages = self.session.messages
            if self.uncertain:
                raise RuntimeError("Harness has uncertain tool results; inspect and resolve them first")
            await self._start()
            if self.skill:
                backend = self.backend or self.services.get("llm")
                if backend and hasattr(backend, "temperature") and self.skill.temperature is not None:
                    backend.temperature = self.skill.temperature
            loop = self.services.get("agent_loop")
            if loop is None:
                raise ValueError("An active agent_loop service is required")
            if max_steps is None:
                max_steps = self.skill.max_iterations if self.skill and self.skill.max_iterations is not None else 10
            return await loop(self, query, max_steps=max_steps, stream=stream)
        finally:
            try:
                if not self.session or self.session.lock is not None:
                    completed = {m.get("tool_call_id") for m in self.messages if m["role"] == "tool"}
                    for message in tuple(self.messages):
                        for call in message.get("tool_calls") or []:
                            if call["id"] not in completed:
                                unknown = call["id"] in self._started_calls
                                self.record({"role": "tool", "tool_call_id": call["id"], "content":
                                    "Interrupted tool; inspect effects before resolving." if unknown else
                                    "Interrupted before execution; tool was not replayed."}, tool=True, uncertain=unknown)
                                completed.add(call["id"])
            finally:
                self._started_calls.clear()
                self.busy = False
                if self.session:
                    self.session.close()

    @property
    def uncertain(self):
        return self.session.uncertain if self.session else set(self._uncertain)

    def resolve(self, call_id, content):
        """Resolve a result only after the caller has inspected actual effects."""
        self._idle()
        if self.session:
            self.session.open()
            try:
                self.session.resolve(call_id, content)
                self.messages = self.session.messages
            finally:
                self.session.close()
        else:
            if call_id not in self._uncertain:
                raise ValueError("Call is not uncertain")
            for message in self.messages:
                if message.get("tool_call_id") == call_id:
                    message["content"] = content
            self._uncertain.remove(call_id)

    def record(self, message, *, tool=False, uncertain=False):
        if self.session:
            self.session.append("tool_completed" if tool else "message", message=message,
                                **({"uncertain": True} if uncertain else {}))
        elif uncertain:
            self._uncertain.add(message["tool_call_id"])
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
