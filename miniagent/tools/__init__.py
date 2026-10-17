"""Pure callable metadata. Tool ownership belongs to each Harness Registry."""
import inspect
from typing import Any, Callable, Dict

ToolFunction = Callable[..., Any]


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
