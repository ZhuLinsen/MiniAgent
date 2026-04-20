"""Runtime resolution for packs, profiles, skills, and active tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .config import AgentConfig, ProfileConfig
from .diagnostics import BootstrapReport
from .logger import get_logger
from .pack_loader import load_packs
from .skills import Skill, get_skill
from .tools import get_registered_tools

logger = get_logger(__name__)


@dataclass
class RuntimeOverride:
    """Explicit runtime overrides passed by CLI or embedding code."""

    packs: Optional[List[str]] = None
    profile: Optional[str] = None
    tools: Optional[List[str]] = None
    skill: Optional[str] = None
    temperature: Optional[float] = None


@dataclass
class ResolvedAgentConfig:
    """Final runtime configuration after loading packs and applying profiles."""

    system_prompt: str
    temperature: float
    tool_names: List[str]
    active_skill: Optional[str]
    active_profile: Optional[str]
    report: BootstrapReport


def _emit(report: BootstrapReport, code: str, level: str, message: str) -> None:
    """Log and record a resolver diagnostic."""

    if level == "error":
        logger.error(message)
    elif level == "warning":
        logger.warning(message)
    else:
        logger.info(message)

    report.add(code, level, "both", message)


def _dedupe(items: List[str]) -> List[str]:
    """Preserve order while removing duplicates."""

    seen = set()
    result: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _pick_profile(config: AgentConfig, overrides: RuntimeOverride, report: BootstrapReport) -> Optional[ProfileConfig]:
    """Resolve the active profile from overrides and config."""

    profile_name = overrides.profile or config.profile
    selected = None
    if profile_name:
        selected = config.profiles.get(profile_name)
        if selected is None:
            _emit(
                report,
                "R010",
                "error" if config.strict_resolution else "warning",
                "Profile '%s' was not found; continuing without it." % profile_name,
            )
            profile_name = None

    if profile_name is None and "default" in config.profiles:
        profile_name = "default"
        selected = config.profiles["default"]

    report.selected_profile = profile_name
    return selected


def _resolve_skill(
    config: AgentConfig,
    profile: Optional[ProfileConfig],
    overrides: RuntimeOverride,
    report: BootstrapReport,
) -> Optional[Skill]:
    """Resolve the active skill and record diagnostics for missing skills."""

    skill_name = overrides.skill
    if skill_name is None and profile and profile.skill:
        skill_name = profile.skill
    if skill_name is None:
        skill_name = config.default_skill

    report.selected_skill = skill_name
    if not skill_name:
        return None

    skill = get_skill(skill_name)
    if not skill:
        _emit(
            report,
            "R004",
            "error" if config.strict_resolution else "warning",
            "Skill '%s' was requested but is not registered." % skill_name,
        )
        return None

    return skill


def _resolve_explicit_tools(
    config: AgentConfig,
    profile: Optional[ProfileConfig],
    overrides: RuntimeOverride,
) -> Optional[List[str]]:
    """Return explicitly requested tools if present."""

    if overrides.tools is not None:
        return list(overrides.tools)
    if profile and profile.tools:
        return list(profile.tools)
    if config.default_tools:
        return list(config.default_tools)
    return None


def resolve_runtime(
    config: AgentConfig,
    overrides: Optional[RuntimeOverride] = None,
) -> ResolvedAgentConfig:
    """Resolve the final runtime configuration for one agent session."""

    overrides = overrides or RuntimeOverride()
    report = BootstrapReport()
    profile = _pick_profile(config, overrides, report)

    requested_packs = _dedupe(
        list(config.packs)
        + (list(profile.packs) if profile and profile.packs else [])
        + (list(overrides.packs) if overrides.packs else [])
    )
    if requested_packs:
        load_packs(requested_packs, strict=config.strict_resolution, report=report)

    skill = _resolve_skill(config, profile, overrides, report)
    available_tools = get_registered_tools()
    tool_names = _resolve_explicit_tools(config, profile, overrides)
    if not tool_names:
        if skill and skill.tools is not None:
            tool_names = list(skill.tools)
            _emit(
                report,
                "R001",
                "warning",
                "No explicit tools were configured; using skill '%s' tool whitelist." % skill.name,
            )
        else:
            tool_names = list(available_tools.keys())
            _emit(
                report,
                "R002",
                "error" if config.strict_resolution else "warning",
                "No explicit tools or skill whitelist were configured; using all registered tools.",
            )

    tool_names = _dedupe(tool_names)
    missing_requested = [name for name in tool_names if name not in available_tools]
    if missing_requested:
        _emit(
            report,
            "R005",
            "error" if config.strict_resolution else "warning",
            "Requested tools are not registered: %s." % ", ".join(missing_requested),
        )
        tool_names = [name for name in tool_names if name in available_tools]

    if skill and skill.tools is not None:
        missing_skill_tools = [name for name in skill.tools if name not in available_tools]
        if missing_skill_tools:
            _emit(
                report,
                "R006",
                "error" if config.strict_resolution else "warning",
                "Skill '%s' references unregistered tools: %s." % (
                    skill.name,
                    ", ".join(missing_skill_tools),
                ),
            )

        allowed = set(skill.tools)
        filtered_out = [name for name in tool_names if name not in allowed]
        if filtered_out:
            _emit(
                report,
                "R007",
                "error" if config.strict_resolution else "warning",
                "Skill '%s' filtered out tools not in its whitelist: %s." % (
                    skill.name,
                    ", ".join(filtered_out),
                ),
            )
            tool_names = [name for name in tool_names if name in allowed]

    system_prompt = config.system_prompt
    if profile and profile.system_prompt is not None:
        system_prompt = profile.system_prompt

    temperature = config.llm.temperature
    if profile and profile.temperature is not None:
        temperature = profile.temperature

    if skill:
        if skill.prompt != system_prompt:
            _emit(
                report,
                "R008",
                "warning",
                "Skill '%s' replaced the configured system_prompt." % skill.name,
            )
        system_prompt = skill.prompt

        if (
            overrides.temperature is None
            and skill.temperature is not None
            and skill.temperature != temperature
        ):
            _emit(
                report,
                "R009",
                "warning",
                "Skill '%s' replaced the configured temperature." % skill.name,
            )
            temperature = skill.temperature

    if overrides.temperature is not None:
        temperature = overrides.temperature

    report.selected_tools = list(tool_names)
    return ResolvedAgentConfig(
        system_prompt=system_prompt,
        temperature=temperature,
        tool_names=tool_names,
        active_skill=skill.name if skill else None,
        active_profile=report.selected_profile,
        report=report,
    )
