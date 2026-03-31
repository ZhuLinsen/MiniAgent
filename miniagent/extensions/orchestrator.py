"""Agent orchestrator for MiniAgent.

Provides a simple orchestrator that decomposes complex tasks into sub-tasks
and delegates them to specialized worker agents using the Skill system.

Usage:
    from miniagent.orchestrator import Orchestrator

    orch = Orchestrator(
        model="deepseek-chat",
        api_key="...",
        base_url="https://api.deepseek.com/v1",
    )
    result = orch.run("Research Python async patterns, then write a demo script and test it")
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from ..agent import MiniAgent
from ..skills import get_skill, list_skills, Skill
from ..logger import get_logger

logger = get_logger(__name__)


class Orchestrator:
    """
    Agent orchestrator that decomposes complex tasks into sub-tasks.
    
    Uses a planner agent to break down the task, then spawns worker agents
    for each sub-task. Workers are configured via the Skill system — each
    worker loads a skill that defines its prompt, tool whitelist, and params.
    """

    # Fallback prompts for roles without a registered skill
    _FALLBACK_PROMPTS = {
        "researcher": "You are a research assistant. Summarize findings clearly.",
        "coder": "You are a coding assistant. Write clean, well-tested code.",
        "tester": "You are a QA engineer. Write and run tests using bash.",
        "reviewer": "You are a code reviewer. Provide constructive feedback.",
    }

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        worker_roles: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        """
        Args:
            model: LLM model name
            api_key: API key
            base_url: API base URL
            temperature: Model temperature
            worker_roles: Optional custom role->prompt mapping. Merged with defaults.
        """
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.kwargs = kwargs

        # Build role map: prefer registered skills, fall back to defaults
        self.roles = {**self._FALLBACK_PROMPTS}
        if worker_roles:
            self.roles.update(worker_roles)

    def _create_worker(self, role: str, system_prompt: Optional[str] = None) -> MiniAgent:
        """Create a worker agent for a specific role.
        
        If a Skill is registered for the role, loads it (prompt + tool filter).
        Otherwise falls back to the role prompt string.
        """
        prompt = system_prompt or self.roles.get(role, self.roles["coder"])
        agent = MiniAgent(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=self.temperature,
            system_prompt=prompt,
            **self.kwargs,
        )
        # Load all available tools
        for tool_name in agent.get_available_tools():
            agent.load_builtin_tool(tool_name)
        
        # Apply skill if one is registered for this role (overrides prompt & filters tools)
        if not system_prompt and get_skill(role):
            agent.load_skill(role)
        
        return agent

    def plan(self, task: str) -> List[Dict[str, str]]:
        """
        Use the planner agent to decompose a task into ordered sub-tasks.
        
        Returns:
            List of {"role": "coder", "task": "implement X"} dicts
        """
        planner = MiniAgent(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=0.3,  # lower temp for planning
            system_prompt=f"""You are a task planner. Break down the user's complex task into 2-5 sequential sub-tasks.
            
Available worker roles: {', '.join(self.roles.keys())}

Respond ONLY with a JSON array. Each element must have "role" and "task" keys.
Example: [{{"role": "researcher", "task": "Find best practices for X"}}, {{"role": "coder", "task": "Implement X based on research"}}]

Keep it simple. Don't over-decompose.""",
        )

        try:
            response = planner._call_llm([
                {"role": "system", "content": planner.system_prompt},
                {"role": "user", "content": task},
            ])
        except Exception as e:
            logger.error(f"LLM call for planning failed: {e}")
            return [{"role": list(self.roles.keys())[0] if self.roles else "coder", "task": task}]

        # Parse the plan from response
        try:
            # Try to extract JSON array from response
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                plan = json.loads(response[start:end])
                if isinstance(plan, list) and all("role" in s and "task" in s for s in plan):
                    logger.info(f"Plan created with {len(plan)} sub-tasks")
                    return plan
        except json.JSONDecodeError:
            pass

        # Fallback: single coder task
        logger.warning("Could not parse plan, falling back to single task")
        return [{"role": "coder", "task": task}]

    def run(
        self,
        task: str,
        max_iterations: int = 10,
        callback: Optional[Callable[[str, str, str], None]] = None,
    ) -> str:
        """
        Run multi-agent workflow.
        
        Args:
            task: The complex task description
            max_iterations: Max iterations per worker
            callback: Optional callback(role, task, result) called after each sub-task
            
        Returns:
            Combined results from all workers
        """
        plan = self.plan(task)
        results = []
        context = ""  # Accumulated context passed to subsequent workers

        for i, step in enumerate(plan):
            role = step["role"]
            sub_task = step["task"]
            logger.info(f"Step {i+1}/{len(plan)}: [{role}] {sub_task}")

            worker = self._create_worker(role)

            # Include context from previous steps
            full_query = sub_task
            if context:
                full_query = f"Previous steps context:\n{context}\n\nYour task: {sub_task}"

            result = worker.run_with_tools(full_query, max_iterations=max_iterations)
            results.append({"role": role, "task": sub_task, "result": result})

            # Build context for next worker (truncated)
            context += f"\n[{role}] {sub_task} → Result: {result[:500]}\n"

            if callback:
                callback(role, sub_task, result)

        # Compile final summary
        summary_parts = []
        for r in results:
            summary_parts.append(f"**[{r['role']}]** {r['task']}\n{r['result']}")

        return "\n\n---\n\n".join(summary_parts)
