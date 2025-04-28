"""Main module of MiniAgent, providing core Agent functionality"""

import os
import json
import time
import logging
import traceback
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
import openai
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_random_exponential
import importlib
import sys
from pathlib import Path

from .config import AgentConfig, load_config
from .tools import get_registered_tools, get_tool, execute_tool, get_tool_description
from .utils.json_utils import parse_json, extract_tool_call, format_tool_response, truncate_message_content, extract_tool_calls, extract_content
from .utils.reflector import Reflector
from .logger import get_logger
from .utils.llm_utils import extract_content, extract_tool_calls, truncate_message_content

# Configure logger using the consistent approach
logger = get_logger(__name__)

# Default reflector configuration
DEFAULT_REFLECTOR_CONFIG = {
    "max_iterations": 3,
    "system_prompt": "You are a helpful assistant that analyzes and improves response quality."
}

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
        use_reflector: bool = False,
        reflector_config: Dict[str, Any] = None,
        system_prompt: str = "You are a helpful assistant that can use tools to get information and perform tasks.",
        **kwargs
    ):
        """
        Initialize MiniAgent
        
        Args:
            model: Model name, e.g. "gpt-3.5-turbo", "deepseek-chat"
            api_key: API key for the model provider
            base_url: Base URL for the model provider
            temperature: Model temperature
            use_reflector: Whether to use the reflector
            reflector_config: Configuration for the reflector
            system_prompt: System prompt to use for the agent
            **kwargs: Additional parameters for the OpenAI client
        """
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.use_reflector = use_reflector
        self.reflector_config = reflector_config or DEFAULT_REFLECTOR_CONFIG
        self.system_prompt = system_prompt
        self.tools = []
        self.client = None
        
        # Initialize the LLM client
        self._init_llm_client()
        
        # Initialize the reflector if enabled
        self.reflector = None
        if self.use_reflector:
            self._init_reflector()
        
        logger.info(f"MiniAgent initialized, model: {model}, base URL: {base_url or 'default'}, temperature: {temperature}")
    
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
    
    def _init_reflector(self):
        """Initialize reflector if enabled"""
        try:
            from .utils.reflector import Reflector
            self.reflector = Reflector(
                client=self.client,
                model=self.model,
                config=self.reflector_config
            )
            logger.info("Initialized Reflector")
        except ImportError as e:
            logger.warning(f"Failed to import Reflector: {e}")
            self.use_reflector = False
    
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
    
    def _prepare_tools_for_api(self) -> List[Dict[str, Any]]:
        """
        Prepare tools in the format expected by LLM API
        
        Returns:
            API-formatted tool definition list
        """
        api_tools = []
        for tool in self.tools:
            api_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                }
            }
            
            if "parameters" in tool:
                api_tool["function"]["parameters"] = tool["parameters"]
            else:
                # Provide default parameter schema
                api_tool["function"]["parameters"] = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
                
            api_tools.append(api_tool)
            
        return api_tools
    
    def run(self, query: str, max_iterations: int = 10) -> str:
        """
        Run the agent with a user query.
        
        Args:
            query: User query text
            max_iterations: Maximum number of tool execution iterations
            
        Returns:
            Final response text
        """
        start_time = time.time()
        logger.info(f"Starting query processing: {query}")
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": query}
        ]
        
        api_tools = self._prepare_tools_for_api()
        
        # If no tools are available, simply return the model response
        if not api_tools:
            logger.info("No available tools, returning model response directly")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature
            )
            return response.choices[0].message.content
        
        iteration = 0
        while iteration < max_iterations:
            logger.info(f"Iteration {iteration + 1}/{max_iterations}")
            
            # Get model response with tool calls
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=api_tools,
                tool_choice="auto",
                temperature=self.temperature
            )
            
            message = response.choices[0].message
            messages.append(message)
            
            # If no tool calls, we're done
            if not message.tool_calls:
                logger.info("No tool calls in response, returning final answer")
                return message.content
            
            # Process each tool call
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                
                # Find and execute the tool
                tool = next((t for t in self.tools if t["name"] == tool_name), None)
                if not tool:
                    logger.error(f"Tool not found: {tool_name}")
                    continue
                    
                try:
                    result = tool["executor"](**tool_args)
                    tool_response = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": str(result)
                    }
                    messages.append(tool_response)
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    tool_response = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": f"Error: {str(e)}"
                    }
                    messages.append(tool_response)
            
            iteration += 1
        
        logger.warning(f"Reached maximum iterations ({max_iterations})")
        return messages[-1]["content"] 