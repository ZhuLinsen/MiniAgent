"""
Configuration module providing LLM API parameter setup and loading functionality.
"""

import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field

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
    
    model: str = "gpt-3.5-turbo"
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

def load_config(config_path: Optional[str] = None) -> AgentConfig:
    """
    Load configuration from file
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Loaded configuration
    """
    # Default configuration
    config = AgentConfig()
    
    # Explicit compatibility credentials belong to the selected endpoint.
    config.llm.api_key = os.environ.get("LLM_API_KEY")
    config.llm.api_base = os.environ.get("LLM_API_BASE")
    model = os.environ.get("LLM_MODEL", "")
    aliases = {
        "openai": ("OPENAI_API_KEY", "OPENAI_API_BASE"),
        "deepseek": ("DEEPSEEK_API_KEY", "DEEPSEEK_API_BASE"),
        "gemini": ("GEMINI_API_KEY", "GEMINI_API_BASE"),
        "anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_API_BASE"),
        "azure": ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"),
    }
    provider = model.partition(":")[0] if ":" in model else None
    if provider is None and config.llm.api_base:
        base = config.llm.api_base.lower()
        provider = next((p for p in aliases if p in base), None)
        if "generativelanguage.googleapis.com" in base:
            provider = "gemini"
    if provider is None and not config.llm.api_base:
        configured = [p for p, (key, base) in aliases.items()
                      if os.environ.get(key) or os.environ.get(base)]
        if len(configured) == 1 and not model:
            provider = configured[0]
        else:
            provider = "openai"
    if provider in aliases:
        key, base = aliases[provider]
        config.llm.api_key = config.llm.api_key or os.environ.get(key)
        config.llm.api_base = config.llm.api_base or os.environ.get(base)
        if provider == "gemini":
            config.llm.api_key = config.llm.api_key or os.environ.get("GOOGLE_API_KEY")

    # Try to get organization from environment variables
    env_organization = os.environ.get("LLM_ORGANIZATION") or os.environ.get("OPENAI_ORGANIZATION")
    if env_organization:
        config.llm.organization = env_organization
        
    # Try to get model from environment variables
    env_model = os.environ.get("LLM_MODEL")
    if env_model:
        config.llm.model = env_model
    
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
        
    # Determine likely provider based on API_BASE and set appropriate default model
    if config.llm.api_base:
        api_base_lower = config.llm.api_base.lower()
        if "deepseek" in api_base_lower and not env_model:
            config.llm.model = "deepseek-chat"
        elif ("generativelanguage.googleapis.com" in api_base_lower or "gemini" in api_base_lower) and not env_model:
            config.llm.model = "gemini-2.5-flash"
        elif "anthropic" in api_base_lower and not env_model:
            config.llm.model = "claude-3-sonnet-20240229"
        elif "azure" in api_base_lower and not env_model:
            # Azure OpenAI requires deployment name instead of model name
            deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")
            if deployment_name:
                config.llm.model = deployment_name
                
    # If no configuration file, return default configuration
    if not config_path:
        return config
        
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
        logger.error(f"Failed to load configuration from {config_path}: {e}")
        
    return config
