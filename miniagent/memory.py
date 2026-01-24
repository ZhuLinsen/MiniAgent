"""Minimal memory module for MiniAgent.

Stores user preferences, facts, and recent conversation history in a JSON file.
Designed to be small and dependency-free.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .logger import get_logger

logger = get_logger(__name__)


def _default_memory_path() -> Path:
    base = Path(os.environ.get("MINIAGENT_HOME", "~/.miniagent")).expanduser()
    base.mkdir(parents=True, exist_ok=True)
    return base / "memory.json"


@dataclass
class Memory:
    path: Path = field(default_factory=_default_memory_path)
    max_messages: int = 40

    preferences: Dict[str, Any] = field(default_factory=dict)
    facts: Dict[str, Any] = field(default_factory=dict)
    messages: List[Dict[str, str]] = field(default_factory=list)

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.preferences = data.get("preferences", {}) or {}
            self.facts = data.get("facts", {}) or {}
            self.messages = data.get("messages", []) or []
        except Exception:
            logger.exception("Failed to load memory")

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "updated_at": int(time.time()),
                "preferences": self.preferences,
                "facts": self.facts,
                "messages": self.messages[-self.max_messages :],
            }
            self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            logger.exception("Failed to save memory")

    def set_preference(self, key: str, value: Any) -> None:
        self.preferences[key] = value
        self.save()

    def set_fact(self, key: str, value: Any) -> None:
        self.facts[key] = value
        self.save()

    def push(self, role: str, content: str) -> None:
        if not content:
            return
        self.messages.append({"role": role, "content": content})
        self.messages = self.messages[-self.max_messages :]
        self.save()

    def context(self) -> str:
        """Generate a compact memory context string for the LLM."""
        parts: List[str] = []
        if self.preferences:
            prefs = ", ".join(f"{k}={v}" for k, v in sorted(self.preferences.items()))
            parts.append(f"User preferences: {prefs}")
        if self.facts:
            facts = ", ".join(f"{k}={v}" for k, v in sorted(self.facts.items()))
            parts.append(f"User facts: {facts}")
        if self.messages:
            recent = self.messages[-10:]
            convo = "\n".join(f"{m['role']}: {m['content']}" for m in recent)
            parts.append("Recent conversation:\n" + convo)
        return "\n\n".join(parts).strip()
