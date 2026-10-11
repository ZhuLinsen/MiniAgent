"""Instance-owned tools. The decorator registry is only a declaration catalog."""
import inspect
from dataclasses import dataclass
from typing import Callable

from jsonschema import Draft202012Validator


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    executor: Callable
    access: str = "external"

    def schema(self):
        return {"type": "function", "function": {
            "name": self.name, "description": self.description,
            "parameters": self.parameters,
        }}


class Registry:
    def __init__(self):
        self.tools = {}
        self.allowed = None

    def add(self, tool):
        if tool.name in self.tools:
            raise ValueError(f"Duplicate tool: {tool.name}")
        Draft202012Validator.check_schema(tool.parameters)
        self.tools[tool.name] = tool

    def get(self, name):
        if self.allowed is not None and name not in self.allowed:
            raise PermissionError(f"Skill disallows tool: {name}")
        if name not in self.tools:
            raise LookupError(f"Unknown tool: {name}")
        return self.tools[name]

    def schemas(self):
        return [t.schema() for n, t in self.tools.items()
                if self.allowed is None or n in self.allowed]

    async def execute(self, name, arguments, policy, on_start=None):
        tool = self.get(name)
        Draft202012Validator(tool.parameters).validate(arguments)
        arguments = dict(arguments)
        await policy.authorize(tool, arguments)
        if on_start:
            on_start()
        result = tool.executor(**arguments)
        return await result if inspect.isawaitable(result) else result
