"""
Utility functions for handling LLM API responses.
These functions help extract content and tool calls from different LLM providers.
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def truncate_message_content(content: str, max_length: int = 100) -> str:
    """
    Truncate message content for logging purposes
    
    Args:
        content: Message content
        max_length: Maximum length
        
    Returns:
        Truncated content
    """
    if not content:
        return ""
        
    if len(content) <= max_length:
        return content
        
    return content[:max_length] + "..."

def extract_content(response: Any) -> str:
    """
    Extract content from LLM API response
    
    Args:
        response: LLM API response
        
    Returns:
        Content text
    """
    if response is None:
        return ""
    
    try:
        # Handle OpenAI API response object
        if hasattr(response, "choices") and hasattr(response.choices[0], "message"):
            message = response.choices[0].message
            return message.content or ""
        
        # Handle dictionary response (e.g., from DeepSeek API)
        if isinstance(response, dict):
            if "choices" in response:
                choices = response["choices"]
                if choices and isinstance(choices, list) and len(choices) > 0:
                    message = choices[0].get("message", {})
                    return message.get("content", "")
        
        # Log warning for unknown response format
        logger.warning(f"Unknown response format: {truncate_message_content(str(response))}")
        return ""
    except Exception as e:
        logger.error(f"Error extracting content from response: {e}")
        return ""

def extract_tool_calls(response: Any) -> List[Dict[str, Any]]:
    """
    Extract tool calls from LLM API response
    
    Args:
        response: LLM API response
        
    Returns:
        List of tool calls
    """
    if response is None:
        return []
    
    tool_calls = []
    
    try:
        # Handle OpenAI API response object
        if hasattr(response, "choices") and hasattr(response.choices[0], "message"):
            message = response.choices[0].message
            if hasattr(message, "tool_calls") and message.tool_calls:
                for tc in message.tool_calls:
                    if hasattr(tc, "function"):
                        try:
                            arguments = json.loads(tc.function.arguments)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse tool call arguments: {tc.function.arguments}")
                            arguments = {}
                            
                        tool_calls.append({
                            "id": tc.id,
                            "name": tc.function.name,
                            "arguments": arguments
                        })
        
        # Handle dictionary response (e.g., from DeepSeek API)
        elif isinstance(response, dict):
            if "choices" in response:
                choices = response["choices"]
                if choices and isinstance(choices, list) and len(choices) > 0:
                    message = choices[0].get("message", {})
                    if "tool_calls" in message and message["tool_calls"]:
                        for tc in message["tool_calls"]:
                            if isinstance(tc, dict) and "function" in tc:
                                function_data = tc["function"]
                                try:
                                    if isinstance(function_data.get("arguments"), str):
                                        arguments = json.loads(function_data["arguments"])
                                    else:
                                        arguments = function_data.get("arguments", {})
                                except json.JSONDecodeError:
                                    logger.warning(f"Failed to parse tool call arguments: {function_data.get('arguments')}")
                                    arguments = {}
                                    
                                tool_calls.append({
                                    "id": tc.get("id", f"call_{len(tool_calls)}"),
                                    "name": function_data.get("name", ""),
                                    "arguments": arguments
                                })
        
        # Handle string response with JSON tool call
        elif isinstance(response, str) and (response.strip().startswith("{") and response.strip().endswith("}")):
            try:
                data = json.loads(response)
                if "tool" in data and "parameters" in data:
                    tool_calls.append({
                        "id": f"call_{len(tool_calls)}",
                        "name": data["tool"],
                        "arguments": data["parameters"]
                    })
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse tool call from response string: {truncate_message_content(response)}")
                
        return tool_calls
    except Exception as e:
        logger.error(f"Error extracting tool calls from response: {e}")
        return [] 