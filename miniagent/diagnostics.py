"""Bootstrap diagnostics for pack loading and runtime resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class Diagnostic:
    """Single diagnostic entry emitted during bootstrap or resolution."""

    code: str
    level: str
    audience: str
    message: str


@dataclass
class BootstrapReport:
    """Structured bootstrap report that can be logged or shown in the CLI."""

    packs_requested: List[str] = field(default_factory=list)
    packs_loaded: List[str] = field(default_factory=list)
    selected_profile: Optional[str] = None
    selected_skill: Optional[str] = None
    selected_tools: List[str] = field(default_factory=list)
    diagnostics: List[Diagnostic] = field(default_factory=list)

    def add(self, code: str, level: str, audience: str, message: str) -> Diagnostic:
        """Append a diagnostic entry and return it."""

        diagnostic = Diagnostic(
            code=code,
            level=level,
            audience=audience,
            message=message,
        )
        self.diagnostics.append(diagnostic)
        return diagnostic

    def has_errors(self) -> bool:
        """Return True when the report contains at least one error."""

        return any(item.level == "error" for item in self.diagnostics)

    def render_text(self, audience: Optional[str] = None) -> str:
        """Render diagnostics into a human-readable text block."""

        lines: List[str] = []
        if self.selected_profile:
            lines.append("profile: %s" % self.selected_profile)
        if self.selected_skill:
            lines.append("skill: %s" % self.selected_skill)
        if self.selected_tools:
            lines.append("tools: %s" % ", ".join(self.selected_tools))

        filtered = [
            item for item in self.diagnostics
            if audience in (None, "both") or item.audience in (audience, "both")
        ]
        if filtered:
            if lines:
                lines.append("")
            lines.append("Diagnostics:")
            for item in filtered:
                lines.append("- [%s] %s" % (item.code, item.message))

        return "\n".join(lines)
