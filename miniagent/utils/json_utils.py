"""JSON utilities module, providing parsing and validation functions for JSON"""

import json
import re
from typing import Dict, Any, Optional, Union, List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_json_from_markdown(text: str) -> Tuple[Optional[str], str]:
    """
    Extract JSON string from Markdown text
    
    Args:
        text: Markdown text containing JSON
        
    Returns:
        Tuple of extracted JSON string and remaining text
    """
    # Look for ```json ... ``` blocks
    json_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    matches = re.findall(json_pattern, text)
    
    if matches:
        return matches[0].strip(), text
    
    # Look for { ... } blocks
    brace_pattern = r"\{[\s\S]*?\}"
    matches = re.findall(brace_pattern, text)
    
    if matches:
        return matches[0], text
        
    return None, text

def clean_json_string(json_str: str) -> str:
    """
    Clean JSON string, removing comments, extra spaces, etc.
    
    Args:
        json_str: Original JSON string
        
    Returns:
        Cleaned JSON string
    """
    if not json_str:
        return ""
        
    # Remove comments (// and /* */)
    json_str = re.sub(r"//.*?$", "", json_str, flags=re.MULTILINE)
    json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)
    
    # Remove trailing commas
    json_str = re.sub(r",\s*([}\]])", r"\1", json_str)
    
    return json_str.strip()

def parse_json(json_str: str) -> Dict:
    """
    Parse JSON string, handling various error cases
    
    Args:
        json_str: JSON string
        
    Returns:
        Parsed dictionary
    """
    if not json_str:
        logger.warning("Received empty JSON string")
        return {}
    
    try:
        # First try direct parsing
        return json.loads(json_str)
    except json.JSONDecodeError:
        logger.warning(f"JSON parsing failed, attempting to fix: {truncate_message_content(json_str)}")
        
        # Try to fix common issues and parse again
        # 1. Try to extract JSON from text
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```|```([\s\S]*?)```|{[\s\S]*}', json_str)
        if json_match:
            extracted_json = json_match.group(1) or json_match.group(2) or json_match.group(0)
            try:
                return json.loads(extracted_json)
            except json.JSONDecodeError:
                logger.warning(f"Extracted JSON still cannot be parsed: {truncate_message_content(extracted_json)}")
                pass
        
        # 2. Try to fix quote issues
        fixed_json = json_str.replace("'", '"')
        try:
            return json.loads(fixed_json)
        except json.JSONDecodeError:
            pass
        
        # 3. Try to fix trailing comma issues
        fixed_json = re.sub(r',\s*}', '}', json_str)
        fixed_json = re.sub(r',\s*]', ']', fixed_json)
        try:
            return json.loads(fixed_json)
        except json.JSONDecodeError:
            logger.error(f"Unable to parse JSON: {truncate_message_content(json_str)}")
            return {}

def truncate_message_content(content: str, max_length: int = 100) -> str:
    """
    Truncate message content for log display
    
    Args:
        content: Message content
        max_length: Maximum length
        
    Returns:
        Truncated content
    """
    if not content or not isinstance(content, str):
        return str(content)
    if len(content) <= max_length:
        return content
    return content[:max_length] + "..."

def extract_content(response: Union[Dict, Any]) -> str:
    """
    Extract content from LLM response, compatible with different response formats
    
    Args:
        response: LLM response object
        
    Returns:
        Extracted content string
    """
    try:
        # Handle different response formats
        if hasattr(response, 'choices') and hasattr(response.choices[0], 'message'):
            # OpenAI-style API response
            return response.choices[0].message.content or ""
        elif isinstance(response, dict):
            # Dictionary format response
            if 'choices' in response:
                choices = response['choices']
                if isinstance(choices, list) and len(choices) > 0:
                    message = choices[0].get('message', {})
                    return message.get('content', "")
        
        # If unable to parse, log and return empty string
        logger.warning(f"Unable to extract content from response: {truncate_message_content(str(response))}")
        return ""
    except Exception as e:
        logger.error(f"Error extracting content: {str(e)}")
        return ""

def extract_tool_calls(response: Union[Dict, Any]) -> List[Dict]:
    """
    Extract tool calls from LLM response, compatible with different formats
    
    Args:
        response: LLM response object
        
    Returns:
        List of tool calls
    """
    try:
        # Handle different response formats
        if hasattr(response, 'choices') and hasattr(response.choices[0], 'message'):
            # OpenAI-style API response
            message = response.choices[0].message
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # Standardize tool call format
                return [
                    {
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "arguments": parse_json(tool_call.function.arguments)
                    }
                    for tool_call in message.tool_calls
                ]
            return []
        elif isinstance(response, dict):
            # Dictionary format response
            if 'choices' in response:
                choices = response['choices']
                if isinstance(choices, list) and len(choices) > 0:
                    message = choices[0].get('message', {})
                    tool_calls = message.get('tool_calls', [])
                    
                    # Standardize tool call format
                    return [
                        {
                            "id": tool_call.get('id', f"call_{i}"),
                            "name": tool_call.get('function', {}).get('name', ''),
                            "arguments": parse_json(tool_call.get('function', {}).get('arguments', '{}'))
                        }
                        for i, tool_call in enumerate(tool_calls)
                    ]
        
        # If unable to parse, log and return empty list
        return []
    except Exception as e:
        logger.error(f"Error extracting tool calls: {str(e)}")
        return []

def extract_tool_call(response: Union[Dict, Any]) -> Optional[Dict]:
    """
    Extract a tool call from LLM response
    
    Args:
        response: LLM response
        
    Returns:
        Tool call information, or None if not found
    """
    tool_calls = extract_tool_calls(response)
    return tool_calls[0] if tool_calls else None

def format_tool_response(tool_call: Dict, response: Any) -> Dict:
    """
    Format the response from a tool call
    
    Args:
        tool_call: Tool call information
        response: Tool execution response
        
    Returns:
        Formatted response
    """
    tool_name = tool_call.get("name")
    
    # Handle different response types
    if isinstance(response, (dict, list)):
        try:
            content = json.dumps(response, ensure_ascii=False)
        except Exception:
            content = str(response)
    else:
        content = str(response)
    
    return {
        "name": tool_name,
        "content": content
    } 