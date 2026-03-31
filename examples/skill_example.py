#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skill System Example — Reusable Agent Configurations

Skills bundle a system prompt + tool whitelist + parameters into a reusable config.
MiniAgent ships 4 built-in skills: coder, researcher, reviewer, tester.

Usage:
    pip install -e .  # install MiniAgent first
    python examples/skill_example.py
"""

from miniagent import MiniAgent, Skill, register_skill, get_skill, list_skills


def show_builtin_skills():
    """List all available skills."""
    print("=== Built-in Skills ===")
    for name in list_skills():
        skill = get_skill(name)
        tools = ", ".join(skill.tools) if skill.tools else "all"
        print(f"  {name}: tools=[{tools}], temperature={skill.temperature}")
    print()


def use_builtin_skill():
    """Load a built-in skill onto an agent."""
    agent = MiniAgent(
        model="deepseek-chat",
        api_key="your_api_key",
        base_url="https://api.deepseek.com/v1",
    )
    agent.load_all_tools()

    # Load "coder" skill — sets coding-focused prompt and filters tools
    agent.load_skill("coder")
    print(f"Loaded skill 'coder'. Agent now has {len(agent.tools)} tools.")
    print(f"Tools: {[t['name'] for t in agent.tools]}")
    print()


def register_custom_skill():
    """Register and use a custom skill."""
    register_skill(Skill(
        name="devops",
        prompt="You are a DevOps engineer. Focus on CI/CD, Docker, and infrastructure.",
        tools=["bash", "read", "write"],
        temperature=0.3,
    ))

    agent = MiniAgent(
        model="deepseek-chat",
        api_key="your_api_key",
        base_url="https://api.deepseek.com/v1",
    )
    agent.load_all_tools()
    agent.load_skill("devops")
    print(f"Loaded custom skill 'devops'. Agent now has {len(agent.tools)} tools.")
    print(f"Tools: {[t['name'] for t in agent.tools]}")


if __name__ == "__main__":
    show_builtin_skills()
    use_builtin_skill()
    register_custom_skill()
