"""
Tools module for MiniAgent.

This module provides a set of tools that can be used by the agent to interact with the world.
"""

import importlib
import inspect
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

# Configure logging
logger = logging.getLogger(__name__)

# Tool function type
ToolFunction = Callable[..., Any]

__all__ = [
    'register_tool',
    'get_registered_tools',
    'get_tool',
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

def register_tool(func: ToolFunction) -> ToolFunction:
    """
    Decorator to register a function as a tool.
    
    Args:
        func: Function to register as a tool
        
    Returns:
        The registered function
    """
    _TOOLS[func.__name__] = func
    return func

def get_registered_tools() -> Dict[str, ToolFunction]:
    """
    Get all registered tools.
    
    Returns:
        Dictionary of tool name to function mapping
    """
    return _TOOLS

def get_tool(name: str) -> Optional[ToolFunction]:
    """
    Get a tool by name.
    
    Args:
        name: Name of the tool
        
    Returns:
        Tool function or None if not found
    """
    return _TOOLS.get(name)

def clear_tools() -> None:
    """
    Clear all registered tools.
    """
    _TOOLS.clear()

def execute_tool(name: str, **kwargs) -> Any:
    """
    Execute a tool by name.
    
    Args:
        name: Name of the tool
        **kwargs: Arguments to pass to the tool
        
    Returns:
        Result of the tool execution
    """
    print(f"Executing tool: {name} with arguments: {kwargs}")
    
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
            type_str = str(param.annotation)
            if "str" in type_str:
                param_desc["type"] = "string"
            elif "int" in type_str:
                param_desc["type"] = "integer"
            elif "float" in type_str:
                param_desc["type"] = "number"
            elif "bool" in type_str:
                param_desc["type"] = "boolean"
            elif "List" in type_str or "list" in type_str:
                param_desc["type"] = "array"
            elif "Dict" in type_str or "dict" in type_str:
                param_desc["type"] = "object"
        
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
    from .basic_tools import (
        calculator, get_current_time, system_info, file_stats,
        disk_usage, process_list, system_load, web_search, http_request
    )
    logger.info("Imported all tools from basic_tools")
except ImportError as e:
    logger.warning(f"Failed to import some tools: {e}")

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
            "disk_usage", "process_list", "system_load", "web_search", "http_request"
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