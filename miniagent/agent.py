"""Main module of MiniAgent, providing core Agent functionality"""

import os
import json
import re
import time
import logging
from typing import Dict, List, Any, Optional, Union
import openai
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_random_exponential

from .config import AgentConfig, load_config
from .tools import get_registered_tools, get_tool, execute_tool, get_tool_description
from .logger import get_logger
from .utils.reflector import Reflector

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
        """Initialize the appropriate LLM client based on the model name"""
        if "gpt" in self.model.lower() or "openai" in self.model.lower():
            self._init_openai_client()
        elif "deepseek" in self.model.lower():
            self._init_deepseek_client()
        else:
            # Default to OpenAI for unknown models
            logger.warning(f"Unknown model type: {self.model}, defaulting to OpenAI client")
            self._init_openai_client()
    
    def _init_openai_client(self):
        """Initialize OpenAI client"""
        try:
            import openai
            
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"OpenAI client initialized with model: {self.model}")
        except ImportError:
            logger.error("OpenAI package not installed. Please install it with 'pip install openai'")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
    
    def _init_deepseek_client(self):
        """Initialize DeepSeek client"""
        try:
            import openai
            
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url or "https://api.deepseek.com/v1"
            )
            logger.info(f"DeepSeek client initialized with model: {self.model}")
        except ImportError:
            logger.error("OpenAI package not installed. Please install it with 'pip install openai'")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize DeepSeek client: {e}")
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
        Parse tool call from LLM response
        
        Args:
            content: LLM response content
            
        Returns:
            Tool call information or None
        """
        # Look for tool call patterns with multiple formats
        tool_patterns = [
            r"TOOL:\s*(\w+)\s*ARGS:\s*({.*?})",  # Standard format
            r"TOL:\s*(\w+)\s*ARGS:\s*({.*?})",   # Typo format (TOL)
            r"使用工具:\s*(\w+)\s*参数:\s*({.*?})",  # Chinese format
            r"USE TOOL:\s*(\w+)\s*WITH ARGS:\s*({.*?})",  # Alternative English format
            r"T\s*O\s*O\s*L\s*:\s*(\w+)\s*A\s*R\s*G\s*S\s*:\s*({.*?})",  # Format with spaces
            r"工具名称:\s*(\w+)\s*工具参数:\s*({.*?})",  # Alternative Chinese format
            r"Tool:\s*(\w+)\s*Args:\s*({.*?})",  # Capitalized format
            r"Tool:\s*(\w+)\s*Arguments:\s*({.*?})"  # Full Arguments format
        ]
        
        for pattern in tool_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                try:
                    return {
                        "name": match.group(1),
                        "arguments": json.loads(match.group(2))
                    }
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse tool arguments: {match.group(2)}")
                    continue  # Try next pattern
        
        return None
    
    def _execute_tool(self, tool_call: Dict) -> Any:
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
            result = tool["executor"](**tool_call["arguments"])
            # Log tool execution
            print(f"[Tool Execution] {tool_call['name']} with args: {tool_call['arguments']}")
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_call['name']}: {e}")
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
        except openai.APIConnectionError as e:
            logger.error(f"Connection error: {str(e)}")
            raise
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error calling LLM: {str(e)}")
            raise
    
    def run_with_tools(self, query: str, max_iterations: int = 10) -> str:
        """
        Implement tool calling with formatted text
        
        This method uses specific text formats to represent tool calls, simulating native tools functionality.
        Suitable for scenarios requiring explicit tool calls, and can be used with models that don't support native tools.
        
        Args:
            query: User query text
            max_iterations: Maximum number of tool execution iterations
            
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
        
        Note:
        1. You must use strict JSON format
        2. You must use double quotes for strings in JSON
        3. If the parameter value is a number, quotes are not needed
        4. After getting the tool execution result, explain the result in a concise and clear way
        
        If you don't need to use tools, you can directly answer the user's question. If the question is outside the scope of the available tools, use your knowledge to answer directly.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        iteration = 0
        while iteration < max_iterations:
            logger.info(f"Iteration {iteration + 1}/{max_iterations}")
            
            # Get model response
            response = self._call_llm(messages)
            messages.append({"role": "assistant", "content": response})
            
            # Parse tool call
            tool_call = self._parse_tool_call(response)
            if not tool_call:
                logger.info("No tool call in response, returning final answer")
                return response
            
            # Execute tool
            logger.info(f"Executing tool: {tool_call['name']} with args: {tool_call['arguments']}")
            result = self._execute_tool(tool_call)
            
            # Add tool result to messages
            messages.append({
                "role": "user",
                "content": f"Tool execution result: {tool_call['name']} returned: {result}\nContinue answering the user's question, or call another tool if needed."
            })
            
            iteration += 1
        
        logger.warning(f"Reached maximum iterations ({max_iterations})")
        return messages[-1]["content"]

    def run(self, query: str, max_iterations: int = 10) -> str:
        """
        Execute the default Agent tool calling method
        
        This is the main entry method for MiniAgent, using formatted text to implement tool calling.
        The method parses and executes tool call instructions from the model output.
        
        Args:
            query: User query text
            max_iterations: Maximum number of iterations
            
        Returns:
            Agent response text
        """
        return self.run_with_tools(query, max_iterations) 