"""Main module of MiniAgent, providing core Agent functionality"""

import os
import json
import re
import time
import logging
from typing import Any, Callable, Dict, List, Optional, Union
from tenacity import retry, stop_after_attempt, wait_random_exponential

from .logger import get_logger
from .utils.json_utils import parse_json
from .tools import get_registered_tools, get_tool, get_tool_description

logger = get_logger(__name__)

class MiniAgent:
    """
    Main MiniAgent class, providing core functionality for LLM interaction and tool calling
    """
    
    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        system_prompt: str = "You are a helpful assistant that can use tools to get information and perform tasks.",
        use_reflector: bool = False,
        **kwargs
    ):
        """
        Initialize MiniAgent
        
        Args:
            model: Model name, e.g. "gpt-3.5-turbo", "deepseek-chat"
            api_key: API key for the model provider
            base_url: Base URL for the model provider
            temperature: Model temperature
            system_prompt: System prompt to use for the agent
            use_reflector: Whether to use the Reflector to improve reasoning
            **kwargs: Additional parameters for the OpenAI client
        """
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.tools = []
        self.client = None
        self.use_reflector = use_reflector
        
        # Initialize the LLM client
        self._init_llm_client()
        
        # Initialize reflector if enabled
        if use_reflector:
            self.reflector = Reflector(self.client, self.model)
        else:
            self.reflector = None
        
        logger.info(f"MiniAgent initialized, model: {model}, base URL: {base_url or 'default'}, temperature: {temperature}, reflector: {use_reflector}")
    
    def _init_llm_client(self):
        """Initialize the LLM client (OpenAI-compatible for all providers)"""
        try:
            import openai as _openai
            self.client = _openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"LLM client initialized: model={self.model}, base_url={self.base_url or 'default'}")
        except ImportError:
            logger.error("OpenAI package not installed. Please install it with 'pip install openai'")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            raise
    
    def add_tool(self, tool: Dict[str, Any]) -> None:
        """
        Add a tool to the agent
        
        Args:
            tool: Tool definition, containing name, description, and executor
        """
        if not isinstance(tool, dict):
            raise TypeError("Tool must be a dictionary type")
            
        required_keys = ["name", "description", "executor"]
        for key in required_keys:
            if key not in tool:
                raise ValueError(f"Tool is missing a required field: {key}")
                
        self.tools.append(tool)
        logger.debug(f"Added tool: {tool['name']}")
    
    def load_builtin_tool(self, tool_name: str) -> bool:
        """
        Load a built-in tool
        
        Args:
            tool_name: Tool name
            
        Returns:
            Whether the load was successful
        """
        tool_func = get_tool(tool_name)
        if tool_func:
            # Create tool definition
            tool_desc = get_tool_description(tool_func)
            tool = {
                "name": tool_desc["name"],
                "description": tool_desc["description"],
                "parameters": tool_desc.get("parameters", {}),
                "executor": tool_func
            }
            self.add_tool(tool)
            logger.info(f"Loaded built-in tool: {tool_name}")
            return True
        else:
            logger.warning(f"Built-in tool not found: {tool_name}")
            return False
    
    def get_available_tools(self) -> List[str]:
        """
        Get all available built-in tool names
        
        Returns:
            List of tool names
        """
        return list(get_registered_tools().keys())
    
    def _build_tools_prompt(self) -> str:
        """
        Build the tools description for the system prompt
        
        Returns:
            Formatted tools description
        """
        tools_desc = []
        for tool in self.tools:
            params = tool.get("parameters", {})
            param_desc = []
            for name, schema in params.get("properties", {}).items():
                required = name in params.get("required", [])
                param_desc.append(f"    - {name}: {schema.get('description', '')} {'(required)' if required else ''}")
            
            desc = f"""
            Tool: {tool['name']}
            Description: {tool['description']}
            Parameters:
            {chr(10).join(param_desc)}
            """
            tools_desc.append(desc)
        return "\n".join(tools_desc)
    
    def _parse_tool_call(self, content: str) -> Optional[Dict]:
        """
        Parse tool call from LLM response.

        Supports two text patterns:
          1. TOOL: <name>  ARGS: {json}
          2. Tool/工具: <name>  Args/参数: {json}

        Args:
            content: LLM response content

        Returns:
            Tool call information or None
        """
        logger.debug(f"Parsing tool call from content (length={len(content)})")

        # Two clean patterns: strict and relaxed
        tool_name_patterns = [
            r"TOOL:\s*(\w+)\s*ARGS:\s*",
            r"(?:Tool|工具|USE TOOL|使用工具|工具名称|TOL):\s*(\w+)\s*(?:Args|参数|WITH ARGS|工具参数|Arguments):\s*",
        ]

        for pattern in tool_name_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                name = match.group(1)
                remaining = content[match.end():]

                # Extract balanced JSON using brace counting
                args_str = self._extract_balanced_json(remaining)
                if not args_str:
                    continue

                logger.debug(f"Matched tool '{name}', args length={len(args_str)}")

                # Try strict parse first, then loose
                try:
                    return {"name": name, "arguments": json.loads(args_str)}
                except json.JSONDecodeError:
                    args = parse_json(args_str)
                    if args:
                        logger.info(f"Parsed tool call: {name} with {len(args)} args")
                        return {"name": name, "arguments": args}

                logger.warning(f"Failed to parse tool arguments for {name}: {args_str[:100]}...")

        logger.debug("No tool call pattern matched")
        return None

    def _extract_balanced_json(self, text: str) -> Optional[str]:
        """
        Extract a balanced JSON object from text by counting braces.

        Args:
            text: Text starting near a JSON object

        Returns:
            Extracted JSON string or None
        """
        # Find the first opening brace
        start = text.find('{')
        if start == -1:
            return None

        brace_count = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return text[start:i+1]

        # If we didn't find balanced braces, return everything from start to end
        # This handles cases where the JSON might be truncated
        if brace_count > 0:
            logger.debug(f"Unbalanced braces (count={brace_count}), returning partial JSON")
            return None

        return None
    
    def _execute_tool(
        self,
        tool_call: Dict,
        tool_callback: Optional[Callable[[str, str, Dict[str, Any]], None]] = None,
    ) -> Any:
        """
        Execute a tool call
        
        Args:
            tool_call: Tool call information
            
        Returns:
            Tool execution result
        """
        tool = next((t for t in self.tools if t["name"] == tool_call["name"]), None)
        if not tool:
            return f"Error: Tool {tool_call['name']} not found"
        try:
            if tool_callback:
                tool_callback("start", tool_call["name"], {"arguments": tool_call.get("arguments", {})})
            result = tool["executor"](**tool_call["arguments"])
            if tool_callback:
                tool_callback("end", tool_call["name"], {"result": result})
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_call['name']}: {e}")
            if tool_callback:
                tool_callback("end", tool_call["name"], {"error": str(e)})
            return f"Error executing tool: {str(e)}"
    
    @retry(stop=stop_after_attempt(3), wait=wait_random_exponential(min=1, max=60))
    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """
        Call LLM with messages
        
        Args:
            messages: Conversation messages
            
        Returns:
            LLM response content
        """
        try:
            # Add debug logging
            logger.debug(f"Calling LLM with API key: {self.api_key[:6]}...")
            logger.debug(f"Base URL: {self.base_url or 'default OpenAI'}")
            logger.debug(f"Model: {self.model}")
            
            if not self.api_key:
                raise ValueError("API key is not set. Please check your environment variables.")
            
            # Apply reflection if enabled
            if self.use_reflector and len(messages) > 1 and self.reflector:
                messages = self.reflector.apply_reflection(messages)
                
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling LLM: {str(e)}")
            raise
    
    def run_with_tools(
        self,
        query: str,
        max_iterations: int = 10,
        tool_callback: Optional[Callable[[str, str, Dict[str, Any]], None]] = None,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Implement tool calling with formatted text
        
        This method uses specific text formats to represent tool calls, simulating native tools functionality.
        Suitable for scenarios requiring explicit tool calls, and can be used with models that don't support native tools.
        
        Args:
            query: User query text
            max_iterations: Maximum number of tool execution iterations
            tool_callback: Callback for tool execution events
            status_callback: Callback for status updates (e.g. "Thinking...", "Executing tool...")
            
        Returns:
            Final response text
        """
        start_time = time.time()
        logger.info(f"Starting query processing with tools: {query}")
        
        # Build system prompt with tools description
        tools_prompt = self._build_tools_prompt()
        system_prompt = f"""
        {self.system_prompt}
        
        You are a powerful AI assistant that can use various tools to complete tasks. Carefully analyze the user's request to determine if you need to use tools to solve the problem.
        
        Available tools:
        {tools_prompt}
        
        Important: When using tools, you must strictly follow this format:
        TOOL: <tool_name>
        ARGS: {{"parameter_name": "parameter_value"}}
        
        For example, when the user asks "Calculate 2 + 2", you should respond:
        TOOL: calculator
        ARGS: {{"expression": "2 + 2"}}
        
        For example, when the user asks "Create a file hello.py", you should respond:
        TOOL: write
        ARGS: {{"path": "hello.py", "content": "print('Hello World')"}}
        
        Note:
        1. You must use strict JSON format
        2. You must use double quotes for strings in JSON
        3. If the parameter value is a number, quotes are not needed
        4. After getting the tool execution result, explain the result in a concise and clear way
        5. When creating files, ALWAYS use the 'write' tool with 'path' and 'content' parameters
        6. For multi-line content, use \\n for newlines in JSON strings
        
        If you don't need to use tools, you can directly answer the user's question. If the question is outside the scope of the available tools, use your knowledge to answer directly.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        iteration = 0
        while iteration < max_iterations:
            logger.info(f"Iteration {iteration + 1}/{max_iterations}")
            
            # Status update: Thinking
            if status_callback:
                status_callback(f"Thinking (Iteration {iteration + 1})...")

            # Get model response
            response = self._call_llm(messages)
            messages.append({"role": "assistant", "content": response})
            
            # Parse tool call
            tool_call = self._parse_tool_call(response)
            if not tool_call:
                logger.info("No tool call in response, returning final answer")
                return response
            
            # Status update: Tool execution
            if status_callback:
                status_callback(f"Executing tool: {tool_call['name']}...")
            
            # Execute tool
            logger.info(f"Executing tool: {tool_call['name']} with args: {tool_call['arguments']}")
            result = self._execute_tool(tool_call, tool_callback=tool_callback)
            
            # Truncate long tool results to prevent token overflow
            result_str = str(result)
            if len(result_str) > 4000:
                result_str = result_str[:4000] + f"\n... [truncated, {len(result_str)} chars total]"
            
            # Add tool result to messages
            messages.append({
                "role": "user",
                "content": f"Tool execution result: {tool_call['name']} returned: {result_str}\nContinue answering the user's question, or call another tool if needed."
            })
            
            iteration += 1
        
        logger.warning(f"Reached maximum iterations ({max_iterations})")
        return messages[-1]["content"]

    def run_with_native_tools(
        self,
        query: str,
        max_iterations: int = 10,
        tool_callback: Optional[Callable[[str, str, Dict[str, Any]], None]] = None,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Run agent using OpenAI native function calling (tools parameter).
        
        This is the alternative to run_with_tools() for models that support native FC.
        More reliable parsing, supports parallel tool calls.
        
        Args:
            query: User query text
            max_iterations: Maximum number of tool execution iterations
            tool_callback: Callback for tool execution events
            status_callback: Callback for status updates
            
        Returns:
            Final response text
        """
        import openai as _openai
        
        logger.info(f"Starting native FC query: {query}")
        
        # Build OpenAI-format tool schemas
        tool_schemas = []
        for tool in self.tools:
            tool_schemas.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
                }
            })
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": query}
        ]
        
        iteration = 0
        while iteration < max_iterations:
            if status_callback:
                status_callback(f"Thinking (Iteration {iteration + 1})...")
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    tools=tool_schemas if tool_schemas else None,
                )
            except Exception as e:
                logger.error(f"Native FC LLM call failed: {e}")
                raise
            
            msg = response.choices[0].message
            
            # No tool calls — return final text
            if not msg.tool_calls:
                return msg.content or ""
            
            # Append assistant message with tool_calls
            messages.append(msg)
            
            # Execute each tool call
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    arguments = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    arguments = parse_json(tc.function.arguments) or {}
                
                if status_callback:
                    status_callback(f"Executing tool: {tool_name}...")
                
                tool_call_info = {"name": tool_name, "arguments": arguments}
                logger.info(f"Native FC executing: {tool_name} with {arguments}")
                result = self._execute_tool(tool_call_info, tool_callback=tool_callback)
                
                # Truncate long results
                result_str = str(result)
                if len(result_str) > 4000:
                    result_str = result_str[:4000] + f"\n... [truncated, {len(result_str)} chars total]"
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str,
                })
            
            iteration += 1
        
        logger.warning(f"Native FC reached max iterations ({max_iterations})")
        return messages[-1].get("content", "") if isinstance(messages[-1], dict) else ""

    def run(self, query: str, max_iterations: int = 10, mode: str = "text") -> str:
        """
        Execute the Agent with specified tool calling mode.
        
        Args:
            query: User query text
            max_iterations: Maximum number of iterations
            mode: Tool calling mode — "text" (default, transparent parsing) 
                  or "native" (OpenAI function calling)
            
        Returns:
            Agent response text
        """
        if mode == "native":
            return self.run_with_native_tools(query, max_iterations)
        return self.run_with_tools(query, max_iterations)