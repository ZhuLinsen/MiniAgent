"""
Configuration module providing LLM API parameter setup and loading functionality.
"""

import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from .connections import credential, read_profiles

# Try to import dotenv if installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Ignore if dotenv is not installed

# Configure logging - use existing logger instead of initializing again
from .logger import get_logger
logger = get_logger(__name__)

@dataclass
class LLMConfig:
    """LLM configuration"""
    
    model: str = ""
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    organization: Optional[str] = None
    timeout: Optional[int] = 60
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None

@dataclass
class AgentConfig:
    """Agent configuration"""
    
    llm: LLMConfig = field(default_factory=LLMConfig)
    system_prompt: str = "You are a helpful AI assistant."
    default_tools: List[str] = field(default_factory=list)
    providers: Dict[str, Any] = field(default_factory=dict)
    mcp_servers: Dict[str, Any] = field(default_factory=dict)
    enable_reflection: bool = False
    reflection_system_prompt: Optional[str] = None
    reflection_max_iterations: int = 3
    
    # Tool execution limits (configurable via env vars)
    bash_timeout: int = 120          # BASH_TIMEOUT: bash default timeout in seconds
    bash_max_output: int = 50000     # BASH_MAX_OUTPUT: bash output truncation limit
    tool_result_limit: int = 16000   # TOOL_RESULT_LIMIT: tool result truncation limit
    max_context_messages: int = 20   # MAX_CONTEXT_MESSAGES: auto-compress conversation after N messages
    context_budget: int = 32768     # MINIAGENT_CONTEXT_BUDGET: conservative token budget
    confirm_dangerous: bool = True   # CONFIRM_DANGEROUS: require confirmation for dangerous commands

def load_config(config_path: Optional[str] = None, *, model_override=None, base_override=None) -> AgentConfig:
    """
    Load configuration from file
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Loaded configuration
    """
    # Default configuration
    profile = read_profiles()
    config = AgentConfig(providers=dict(profile["providers"]))
    
    # Explicit compatibility credentials belong to the selected endpoint.
    config.llm.api_key = os.environ.get("LLM_API_KEY")
    config.llm.api_base = base_override or os.environ.get("LLM_API_BASE")
    config.llm.model = os.environ.get("LLM_MODEL") or profile["model"]
    aliases = {
        "openai": ("OPENAI_API_KEY", "OPENAI_API_BASE"),
        "deepseek": ("DEEPSEEK_API_KEY", "DEEPSEEK_API_BASE"),
        "dashscope": ("DASHSCOPE_API_KEY", "DASHSCOPE_API_BASE"),
        "gemini": ("GEMINI_API_KEY", "GEMINI_API_BASE"),
        "anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_API_BASE"),
        "azure": ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"),
    }

    # Try to get organization from environment variables
    env_organization = os.environ.get("LLM_ORGANIZATION") or os.environ.get("OPENAI_ORGANIZATION")
    if env_organization:
        config.llm.organization = env_organization
        
    # Load tool execution limits from environment
    def _safe_int(key: str, default: int) -> int:
        val = os.environ.get(key, "")
        if not val:
            return default
        try:
            return int(val)
        except ValueError:
            logger.warning(f"Invalid integer for {key}={val!r}, using default {default}")
            return default

    config.bash_timeout = _safe_int("BASH_TIMEOUT", config.bash_timeout)
    config.bash_max_output = _safe_int("BASH_MAX_OUTPUT", config.bash_max_output)
    config.tool_result_limit = _safe_int("TOOL_RESULT_LIMIT", config.tool_result_limit)
    config.max_context_messages = _safe_int("MAX_CONTEXT_MESSAGES", config.max_context_messages)
    config.context_budget = _safe_int("MINIAGENT_CONTEXT_BUDGET", config.context_budget)
    if os.environ.get("CONFIRM_DANGEROUS") is not None:
        config.confirm_dangerous = os.environ["CONFIRM_DANGEROUS"].lower() not in ("0", "false", "no")
    if os.environ.get("ENABLE_REFLECTION") is not None:
        config.enable_reflection = os.environ["ENABLE_REFLECTION"].lower() not in ("0", "false", "no")
    if os.environ.get("REFLECTION_MAX_ITERATIONS"):
        config.reflection_max_iterations = _safe_int("REFLECTION_MAX_ITERATIONS", config.reflection_max_iterations)
        
    if config_path:
        _load_file(config, config_path)
        config.providers = {**profile["providers"], **config.providers}
    if model_override is not None:
        config.llm.model = model_override
    if base_override is not None:
        config.llm.api_base = base_override
    if not isinstance(config.llm.model, str):
        raise ValueError("LLM model must be a string: provider:model-id")
    config.llm.model = config.llm.model.strip()
    if not config.llm.model:
        # No endpoint may inherit an unrelated provider's key before a model is selected.
        config.llm.api_key = None
        return config
    provider = config.llm.model.partition(":")[0] if ":" in config.llm.model else "openai"
    if ":" not in config.llm.model and config.llm.api_base:
        # Compatibility for explicitly configured legacy endpoints, never key-only inference.
        base = config.llm.api_base.lower()
        provider = next((p for p in aliases if p in base), "openai")
        if "generativelanguage.googleapis.com" in base:
            provider = "gemini"
    persisted = provider in profile["models"]
    if provider in config.providers:
        env = config.providers[provider].get("api_key_env")
        if env:
            config.llm.api_key = config.llm.api_key or credential(env, persisted=persisted)
    else:
        key, base = aliases.get(provider, (provider.upper() + "_API_KEY", None))
        config.llm.api_key = config.llm.api_key or credential(key, persisted=persisted)
        config.llm.api_base = config.llm.api_base or (os.environ.get(base) if base else None)
        if provider == "gemini":
            config.llm.api_key = config.llm.api_key or os.environ.get("GOOGLE_API_KEY")
    return config


def _load_file(config, config_path):
    """Apply file values before selecting credentials for the final model."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
            
        # Load LLM configuration
        if "llm" in config_data:
            for key, value in config_data["llm"].items():
                if hasattr(config.llm, key):
                    setattr(config.llm, key, value)
                    
        # Load agent configuration
        for key, value in config_data.items():
            if key != "llm" and hasattr(config, key):
                setattr(config, key, value)
                
        logger.info(f"Configuration loaded from {config_path}")
    except Exception as e:
        raise ValueError(f"Failed to load configuration from {config_path}") from e
