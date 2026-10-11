"""Authorization for managed tools; arbitrary shell/plugins are not isolated."""
import inspect
from pathlib import Path


class Policy:
    def __init__(self, workspace=None, mode="confirm", approve=None, *, allow_sensitive_files=False):
        if mode not in {"readonly", "confirm", "trusted"}:
            raise ValueError("Policy must be readonly, confirm or trusted")
        self.workspace = Path(workspace or Path.cwd()).resolve()
        self.mode, self.approve = mode, approve
        self.allow_sensitive_files = allow_sensitive_files

    def path(self, value):
        path = Path(value).expanduser()
        path = (path if path.is_absolute() else self.workspace / path).resolve()
        if not path.is_relative_to(self.workspace):
            raise PermissionError("Path is outside workspace")
        parts = [p.lower() for p in path.relative_to(self.workspace).parts]
        sensitive = any(p == ".git" or (p.startswith(".env") and p != ".env.example")
                        or p.endswith((".pem", ".key", ".p12", ".pfx")) for p in parts)
        if sensitive and not self.allow_sensitive_files:
            raise PermissionError("Sensitive file access requires explicit opt-in")
        return path

    def visible(self, path):
        try:
            self.path(path)
            return True
        except PermissionError:
            return False

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
