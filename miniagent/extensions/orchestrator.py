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
from ..config import AgentConfig, LLMConfig
from ..diagnostics import BootstrapReport
from ..logger import get_logger
from ..resolver import resolve_runtime

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
        packs: Optional[List[str]] = None,
        strict_resolution: bool = False,
        **kwargs,
    ):
        """
        Args:
            model: LLM model name
            api_key: API key
            base_url: API base URL
            temperature: Model temperature
            worker_roles: Optional custom role->prompt mapping. Merged with defaults.
            packs: Optional external pack modules loaded for worker resolution.
            strict_resolution: Whether missing pack/tool/skill issues should stop worker bootstrap.
        """
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.packs = list(packs or [])
        self.strict_resolution = strict_resolution
        self.kwargs = kwargs

        # Build role map: prefer registered skills, fall back to defaults
        self.roles = {**self._FALLBACK_PROMPTS}
        if worker_roles:
            self.roles.update(worker_roles)

    def _log_bootstrap_report(self, role: str, report: BootstrapReport) -> None:
        """Forward resolver diagnostics to logs for orchestrated workers."""

        for item in report.diagnostics:
            message = f"[{role}] {item.code}: {item.message}"
            if item.level == "error":
                logger.error(message)
            elif item.level == "warning":
                logger.warning(message)
            else:
                logger.info(message)

    def _create_worker(self, role: str, system_prompt: Optional[str] = None) -> MiniAgent:
        """Create a worker agent for a specific role.
        
        If a Skill is registered for the role, resolver applies it as the worker's
        final capability boundary. Otherwise falls back to the role prompt string.
        """
        prompt = system_prompt or self.roles.get(role, self.roles["coder"])
        resolved = resolve_runtime(AgentConfig(
            llm=LLMConfig(temperature=self.temperature),
            system_prompt=prompt,
            packs=list(self.packs),
            default_skill=None if system_prompt else role,
            strict_resolution=self.strict_resolution,
        ))
        self._log_bootstrap_report(role, resolved.report)
        if resolved.report.has_errors():
            raise ValueError(
                "Worker bootstrap failed for role '%s': %s" % (
                    role,
                    resolved.report.render_text("developer") or "unknown bootstrap error",
                )
            )

        agent = MiniAgent(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=resolved.temperature,
            system_prompt=resolved.system_prompt,
            **self.kwargs,
        )
        for tool_name in resolved.tool_names:
            agent.load_builtin_tool(tool_name)

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
