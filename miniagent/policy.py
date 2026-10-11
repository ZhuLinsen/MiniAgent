"""Authorization for managed tools; arbitrary shell/plugins are not isolated."""
import inspect
from pathlib import Path


class Policy:
    def __init__(self, workspace=None, mode="confirm", approve=None):
        if mode not in {"readonly", "confirm", "trusted"}:
            raise ValueError("Policy must be readonly, confirm or trusted")
        self.workspace = Path(workspace or Path.cwd()).resolve()
        self.mode, self.approve = mode, approve

    def path(self, value):
        path = Path(value).expanduser()
        path = (path if path.is_absolute() else self.workspace / path).resolve()
        if not path.is_relative_to(self.workspace):
            raise PermissionError("Path is outside workspace")
        return path

    async def authorize(self, tool, arguments):
        if tool.access in {"read", "write"}:
            arguments["path"] = str(self.path(arguments.get("path", ".")))
        if tool.access == "read":
            return
        if self.mode == "readonly":
            raise PermissionError("Read-only policy")
        if self.mode == "trusted":
            return
        accepted = self.approve(tool.name, dict(arguments)) if self.approve else False
        if inspect.isawaitable(accepted):
            accepted = await accepted
        if accepted is not True:
            raise PermissionError("Tool execution denied")
