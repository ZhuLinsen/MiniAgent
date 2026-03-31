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
