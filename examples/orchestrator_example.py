#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Agent Orchestration Example — Multi-role Task Decomposition

The Orchestrator decomposes complex tasks into sub-tasks and assigns them
to specialized Workers (each driven by a Skill: coder, researcher, etc.).

Usage:
    pip install -e .  # install MiniAgent first
    python examples/orchestrator_example.py
"""

from miniagent import Orchestrator


def basic_orchestration():
    """Run a complex task with automatic planning and role assignment."""
    orch = Orchestrator(
        model="deepseek-chat",
        api_key="your_api_key",
        base_url="https://api.deepseek.com/v1",
        packs=["examples.miniagent_demo_pack"],  # optional external pack modules for worker bootstrap
    )

    # The orchestrator will automatically:
    # 1. Analyze the task and create a plan
    # 2. Assign sub-tasks to appropriate skills (researcher, coder, tester)
    # 3. Execute each sub-task with a specialized worker agent
    # 4. Collect and summarize results
    result = orch.run("Research Python async patterns, write a demo and test it")
    print("=== Orchestration Result ===")
    print(result)


if __name__ == "__main__":
    print("Agent Orchestration Example")
    print("=" * 40)
    print()
    print("This example requires a valid API key.")
    print("Set LLM_API_KEY in your .env file, then uncomment basic_orchestration().")
    print()
    # basic_orchestration()
