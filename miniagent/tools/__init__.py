"""
Tools module for MiniAgent.

This module provides a set of tools that can be used by the agent to interact with the world.
"""

import importlib
import inspect
from typing import Any, Callable, Dict, List, Optional, Union

from ..logger import get_logger
from ..registration import RegistryMeta, build_registry_meta, registration_scope

logger = get_logger(__name__)

# Tool function type
ToolFunction = Callable[..., Any]

__all__ = [
    'register_tool',
    'get_registered_tools',
    'get_registered_tool_meta',
    'get_tool',
    'get_tool_meta',
    'clear_tools',
    'execute_tool',
    'load_tool_from_module',
    'load_builtin_tools',
    'get_tool_description',
    'get_tools_description',
    'load_tools'
]

# Dictionary to store registered tools
_TOOLS: Dict[str, ToolFunction] = {}
_TOOL_META: Dict[str, RegistryMeta] = {}

def register_tool(
    func: Optional[ToolFunction] = None,
    *,
    allow_override: bool = False,
) -> Union[ToolFunction, Callable[[ToolFunction], ToolFunction]]:
    """
    Decorator to register a function as a tool.
    
    Args:
        func: Function to register as a tool
        allow_override: Whether to replace an existing tool with the same name
        
    Returns:
        The registered function or a decorator wrapper
    """
    def decorator(tool_func: ToolFunction) -> ToolFunction:
        name = tool_func.__name__
        if not allow_override and name in _TOOLS:
            raise ValueError(f"Tool '{name}' is already registered")

        _TOOLS[name] = tool_func
        _TOOL_META[name] = build_registry_meta(name, module=tool_func.__module__)
        return tool_func

    if func is None:
        return decorator

    return decorator(func)

def get_registered_tools() -> Dict[str, ToolFunction]:
    """
    Get all registered tools.
    
    Returns:
        Dictionary of tool name to function mapping
    """
    return _TOOLS

def get_registered_tool_meta() -> Dict[str, RegistryMeta]:
    """
    Get metadata for all registered tools.
    
    Returns:
        Dictionary of tool name to registration metadata
    """
    return _TOOL_META

def get_tool(name: str) -> Optional[ToolFunction]:
    """
    Get a tool by name.
    
    Args:
        name: Name of the tool
        
    Returns:
        Tool function or None if not found
    """
    return _TOOLS.get(name)

def get_tool_meta(name: str) -> Optional[RegistryMeta]:
    """
    Get registration metadata for a tool by name.
    
    Args:
        name: Name of the tool
        
    Returns:
        Registry metadata or None if not found
    """
    return _TOOL_META.get(name)

def clear_tools() -> None:
    """
    Clear all registered tools.
    """
    _TOOLS.clear()
    _TOOL_META.clear()

def execute_tool(name: str, **kwargs) -> Any:
    """
    Execute a tool by name.
    
    Args:
        name: Name of the tool
        **kwargs: Arguments to pass to the tool
        
    Returns:
        Result of the tool execution
    """
    logger.info(f"Executing tool: {name} with arguments: {kwargs}")
    
    tool = get_tool(name)
    if not tool:
        error_msg = f"Tool '{name}' not found"
        logger.error(error_msg)
        return {"error": error_msg}
    
    try:
        return tool(**kwargs)
    except Exception as e:
        error_msg = f"Error executing tool '{name}': {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

def load_tool_from_module(module_name: str) -> List[str]:
    """
    Load tools from a module.
    
    Args:
        module_name: Name of the module
        
    Returns:
        List of loaded tool names
    """
    try:
        # Import the module
        module = importlib.import_module(module_name)
        
        # Get all functions in the module
        loaded_tools = []
        for name, obj in inspect.getmembers(module):
            # Check if the object is a function
            if inspect.isfunction(obj):
                # Check if the function is decorated with @register_tool
                if obj.__name__ in module.__dict__ and obj.__name__ in _TOOLS:
                    loaded_tools.append(obj.__name__)
        
        logger.info(f"Loaded tools from module '{module_name}': {loaded_tools}")
        return loaded_tools
    except Exception as e:
        logger.error(f"Error loading tools from module '{module_name}': {str(e)}")
        return []

def load_builtin_tools(tools: Union[List[str], str, None] = None) -> List[str]:
    """
    Load built-in tools.
    
    Args:
        tools: List of tool names or a single tool name
        
    Returns:
        List of loaded tool names
    """
    if tools is None:
        return []
    
    if isinstance(tools, str):
        tools = [tools]
    
    loaded_tools = []
    for tool_name in tools:
        module_path = f"miniagent.tools.{tool_name}"
        loaded = load_tool_from_module(module_path)
        loaded_tools.extend(loaded)
    
    return loaded_tools

def get_tool_description(tool: ToolFunction) -> Dict[str, Any]:
    """
    Get description of a tool.
    
    Args:
        tool: Tool function
        
    Returns:
        Dictionary with tool description
    """
    # Get function signature
    sig = inspect.signature(tool)
    
    # Get docstring
    doc = inspect.getdoc(tool) or ""
    
    # Get parameters
    properties = {}
    required = []
    for name, param in sig.parameters.items():
        if name == "self":
            continue
            
        param_desc = {"type": "string"}  # Default type
        
        # Check if parameter has a type annotation
        if param.annotation != inspect.Parameter.empty:
            # Convert type annotation to string
            # Check compound types (List, Dict) BEFORE simple types
            # to avoid e.g. List[str] matching "str" first
            type_str = str(param.annotation)
            if "List" in type_str or "list" in type_str:
                param_desc["type"] = "array"
            elif "Dict" in type_str or "dict" in type_str:
                param_desc["type"] = "object"
            elif "bool" in type_str:
                param_desc["type"] = "boolean"
            elif "int" in type_str:
                param_desc["type"] = "integer"
            elif "float" in type_str:
                param_desc["type"] = "number"
            elif "str" in type_str:
                param_desc["type"] = "string"
        
        # Check if parameter has a default value
        if param.default != inspect.Parameter.empty:
            param_desc["default"] = param.default
        else:
            # Required parameter
            required.append(name)
        
        properties[name] = param_desc
    
    return {
        "name": tool.__name__,
        "description": doc,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required
        }
    }

def get_tools_description(tools: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Get descriptions for all tools or specified tools.
    
    Args:
        tools: List of tool names or None for all
        
    Returns:
        List of tool descriptions
    """
    registered_tools = get_registered_tools()
    
    if tools:
        # Filter tools by name
        tool_funcs = {name: func for name, func in registered_tools.items() if name in tools}
    else:
        tool_funcs = registered_tools
    
    return [get_tool_description(func) for func in tool_funcs.values()]

# Try to import built-in tools, handle import errors gracefully
try:
    with registration_scope(source="builtin", pack_name="builtin", module=__name__):
        from .basic_tools import (
            calculator, get_current_time, system_info, file_stats,
            disk_usage, process_list, system_load, web_search, http_request,
            open_browser, open_app, clipboard_copy, clipboard_read,
            create_docx, env_get, env_set
        )
    logger.debug("Imported all tools from basic_tools")
except ImportError as e:
    logger.warning(f"Failed to import some tools: {e}")

# Code tools (optional import so the package remains robust)
try:
    with registration_scope(source="builtin", pack_name="builtin", module=__name__):
        from .code_tools import read, write, edit, glob, grep, bash
    logger.debug("Imported all tools from code_tools")
except ImportError as e:
    logger.warning(f"Failed to import code tools: {e}")

def load_tools(tools: Union[List[str], str, None] = None) -> List[str]:
    """
    Load specified tools or all available tools.
    
    Args:
        tools: List of tool names or a single tool name or None for all
        
    Returns:
        List of loaded tool names
    """
    if tools is None:
        # Load all available tools
        tools = [
            "calculator", "get_current_time", "system_info", "file_stats",
            "disk_usage", "process_list", "system_load", "web_search", "http_request",
            "open_browser", "open_app", "clipboard_copy", "clipboard_read",
            "create_docx", "env_get", "env_set",
            "read", "write", "edit", "glob", "grep", "bash"
        ]
    
    if isinstance(tools, str):
        tools = [tools]
    
    loaded_tools = []
    for tool_name in tools:
        if tool_name in _TOOLS:
            loaded_tools.append(tool_name)
        else:
            logger.warning(f"Tool '{tool_name}' not found")
    
    return loaded_tools 
