"""Skill system for MiniAgent.

A Skill is a reusable configuration that bundles:
- A specialized system prompt
- An optional tool whitelist (subset of loaded tools)
- Optional LLM parameters (temperature, max_iterations)

Skills let you create purpose-built agent personas without writing new code.

Example usage:
    from miniagent.skills import register_skill, get_skill

    @register_skill
    def code_reviewer():
        return Skill(
            name="code_reviewer",
            prompt="You are a senior code reviewer. Focus on bugs, security, and readability.",
            tools=["read", "grep", "glob"],
            temperature=0.3,
        )

    # Use in agent
    agent.load_skill("code_reviewer")
    agent.run("Review the changes in src/auth.py")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
import json
import shlex

# Global skill registry
_SKILLS: Dict[str, "Skill"] = {}


@dataclass
class Skill:
    """A reusable agent configuration."""
    name: str
    prompt: str
    tools: Optional[List[str]] = None  # None = use all loaded tools
    temperature: Optional[float] = None
    max_iterations: Optional[int] = None
    description: str = ""


def register_skill(skill: Skill) -> Skill:
    """Register a skill in the global registry.
    
    Can be used as a plain call:
        register_skill(Skill(name="writer", prompt="..."))
    
    Args:
        skill: Skill instance to register.
        
    Returns:
        The registered Skill (for chaining).
    """
    _SKILLS[skill.name] = skill
    return skill


def get_skill(name: str) -> Optional[Skill]:
    """Look up a registered skill by name."""
    return _SKILLS.get(name)


def list_skills() -> List[str]:
    """Return names of all registered skills."""
    return list(_SKILLS.keys())


def read_skill(path):
    """Read trusted local SKILL.md; simple scalar frontmatter and tool lists only."""
    file = Path(path)
    if file.is_dir():
        file = file / "SKILL.md"
    text = file.read_text(encoding="utf-8")
    meta, prompt = {}, text
    if text.startswith("---\n"):
        pieces = text.split("---\n", 2)
        if len(pieces) != 3:
            raise ValueError("Unclosed Skill frontmatter")
        for line in pieces[1].splitlines():
            key, separator, value = line.partition(":")
            if separator:
                meta[key.strip()] = value.strip().strip("\"'")
        prompt = pieces[2]
    tools = meta.get("allowed-tools", meta.get("tools"))
    if tools is not None:
        tools = json.loads(tools) if tools.startswith("[") else shlex.split(tools)
        if not isinstance(tools, list) or not all(isinstance(t, str) for t in tools):
            raise ValueError("Skill tools must be a list of names")
    limit = meta.get("max-iterations", meta.get("max_iterations"))
    limit = int(limit) if limit is not None else None
    if limit is not None and limit < 1:
        raise ValueError("Skill max_iterations must be positive")
    temperature = float(meta["temperature"]) if "temperature" in meta else None
    return Skill(name=meta.get("name", file.parent.name), prompt=prompt.strip(),
                 tools=tools, description=meta.get("description", ""),
                 max_iterations=limit, temperature=temperature)


# ---------------------------------------------------------------------------
# Built-in skills
# ---------------------------------------------------------------------------

register_skill(Skill(
    name="coder",
    prompt=(
        "You are an expert software engineer. Write clean, well-tested code. "
        "Use tools to read existing code before making changes. "
        "Always verify your changes compile/run correctly."
    ),
    tools=["read", "write", "edit", "bash", "grep", "glob"],
    temperature=0.3,
    description="Software engineering focused agent",
))

register_skill(Skill(
    name="researcher",
    prompt=(
        "You are a research assistant. Gather information thoroughly, "
        "verify facts from multiple sources, and present findings clearly."
    ),
    tools=["bash", "read", "grep", "glob"],
    temperature=0.5,
    description="Information gathering and analysis",
))

register_skill(Skill(
    name="reviewer",
    prompt=(
        "You are a senior code reviewer. Focus on bugs, security issues, "
        "performance problems, and readability. Be constructive and specific."
    ),
    tools=["read", "grep", "glob"],
    temperature=0.3,
    description="Code review specialist",
))

register_skill(Skill(
    name="tester",
    prompt=(
        "You are a QA engineer. Write comprehensive tests covering edge cases. "
        "Run tests and fix failures. Aim for high coverage of critical paths."
    ),
    tools=["read", "write", "edit", "bash", "grep", "glob"],
    temperature=0.3,
    description="Testing and quality assurance",
))
