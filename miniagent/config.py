"""
Configuration module providing LLM API parameter setup and loading functionality.
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, fields
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
    temperature: float = 0.7

@dataclass
class AgentConfig:
    """Agent configuration"""
    
    llm: LLMConfig = field(default_factory=LLMConfig)
    system_prompt: str = "You are a helpful AI assistant."
    providers: Dict[str, Any] = field(default_factory=dict)
    mcp_servers: Dict[str, Any] = field(default_factory=dict)
    context_budget: int = 32768     # MINIAGENT_CONTEXT_BUDGET: conservative token budget

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
        "gemini": ("GEMINI_API_KEY/GOOGLE_API_KEY", "GEMINI_API_BASE"),
        "anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_API_BASE"),
        "azure": ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"),
    }

    try:
        config.llm.temperature = float(os.environ.get("LLM_TEMPERATURE", "0.7"))
    except ValueError:
        raise ValueError("LLM_TEMPERATURE must be a number") from None
        
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

    config.context_budget = _safe_int("MINIAGENT_CONTEXT_BUDGET", config.context_budget)
        
    if config_path:
        _load_file(config, config_path)
        if not isinstance(config.providers, dict) or not isinstance(config.mcp_servers, dict):
            raise ValueError("providers and mcp_servers must be JSON objects")
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
    persisted = provider in profile["models"]
    if provider in config.providers:
        env = config.providers[provider].get("api_key_env")
        if env:
            config.llm.api_key = config.llm.api_key or credential(env, persisted=persisted)
    else:
        key, base = aliases.get(provider, (provider.upper() + "_API_KEY", None))
        config.llm.api_key = config.llm.api_key or credential(key, persisted=persisted)
        config.llm.api_base = config.llm.api_base or (os.environ.get(base) if base else None)
    return config


def _load_file(config, config_path):
    """Apply file values before selecting credentials for the final model."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
            
    except (OSError, ValueError) as e:
        raise ValueError(f"Failed to load configuration from {config_path}") from e
    def apply(target, data):
        if not isinstance(data, dict):
            raise ValueError("Configuration sections must be JSON objects")
        allowed = {entry.name for entry in fields(target)}
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(f"Unsupported settings: {', '.join(sorted(unknown))}; see docs/legacy-migration.md")
        for key, value in data.items():
            setattr(target, key, value)
    if not isinstance(config_data, dict):
        raise ValueError("Configuration must be a JSON object")
    apply(config.llm, config_data.pop("llm", {}))
    apply(config, config_data)
    logger.info("Configuration loaded from %s", config_path)
