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

from dataclasses import dataclass
from typing import Dict, List, Optional
from .registration import (
    RegistryMeta,
    build_registry_meta,
    get_registration_scope,
    infer_caller_module,
    registration_scope,
)

# Global skill registry
_SKILLS: Dict[str, "Skill"] = {}
_SKILL_META: Dict[str, RegistryMeta] = {}


@dataclass
class Skill:
    """A reusable agent configuration."""
    name: str
    prompt: str
    tools: Optional[List[str]] = None  # None = use all loaded tools
    temperature: Optional[float] = None
    max_iterations: Optional[int] = None
    description: str = ""


def register_skill(skill: Skill, *, allow_override: bool = False) -> Skill:
    """Register a skill in the global registry.
    
    Can be used as a plain call:
        register_skill(Skill(name="writer", prompt="..."))
    
    Args:
        skill: Skill instance to register.
        
    Returns:
        The registered Skill (for chaining).
    """
    if not allow_override and skill.name in _SKILLS:
        raise ValueError(f"Skill '{skill.name}' is already registered")

    _SKILLS[skill.name] = skill
    scope = get_registration_scope()
    module_name = infer_caller_module(
        __name__,
        "miniagent",
        "miniagent.registration",
    )
    if scope.source == "builtin" and scope.module:
        module_name = scope.module
    elif not module_name:
        module_name = scope.module
    _SKILL_META[skill.name] = build_registry_meta(
        skill.name,
        module=module_name,
    )
    return skill


def get_skill(name: str) -> Optional[Skill]:
    """Look up a registered skill by name."""
    return _SKILLS.get(name)


def get_skill_meta(name: str) -> Optional[RegistryMeta]:
    """Look up registration metadata for a skill."""
    return _SKILL_META.get(name)


def list_skills() -> List[str]:
    """Return names of all registered skills."""
    return list(_SKILLS.keys())


def get_registered_skill_meta() -> Dict[str, RegistryMeta]:
    """Return metadata for all registered skills."""
    return _SKILL_META


# ---------------------------------------------------------------------------
# Built-in skills
# ---------------------------------------------------------------------------

with registration_scope(source="builtin", pack_name="builtin", module=__name__):
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
