#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MiniAgent Simple Example Script
Demonstrates how to initialize and use basic MiniAgent functionality
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
import traceback

# Add project root directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import MiniAgent main class and configuration
from miniagent.agent import MiniAgent
from miniagent.tools import register_tool, get_tool
from miniagent.logger import get_logger

# Configure logging using MiniAgent's logger
logger = get_logger("example_script")

def main():
    """
    Simple example using MiniAgent
    Demonstrates how to initialize, load tools and execute queries
    """
    try:
        # Load environment variables from .env file
        env_path = Path(__file__).parent.parent / '.env'
        if not env_path.exists():
            logger.error(f"Environment file not found at {env_path}")
            logger.info("Please create a .env file based on .env.example")
            return
            
        load_dotenv(env_path)
        
        # Get API key from environment variables
        api_key = os.environ.get("LLM_API_KEY")
        if not api_key:
            logger.error("LLM_API_KEY not found in environment variables")
            return

        # Initialize MiniAgent with environment variables
        logger.info("Initializing MiniAgent...")
        agent = MiniAgent(
            model=os.environ.get("LLM_MODEL", "deepseek-chat"),
            api_key=api_key,
            base_url=os.environ.get("LLM_API_BASE", "https://api.deepseek.com/v1"),
            temperature=float(os.environ.get("LLM_TEMPERATURE", "0.7")),
            system_prompt="You are a helpful assistant that can use tools to answer questions. When you need information, use the appropriate tools.",
            use_reflector=True
        )
        
        # Load tools
        logger.info("Loading tools...")
        # Explicitly load each required tool
        agent.tools = []  # Clear existing tools
        agent.load_builtin_tool("calculator")
        agent.load_builtin_tool("get_current_time")
        agent.load_builtin_tool("system_info")
        
        # Print loaded tools
        logger.info(f"Loaded tools: {[tool['name'] for tool in agent.tools]}")
        
        # Prepare user query
        user_query = "What is the current time? Please provide a system information overview."
        logger.info(f"User query: {user_query}")
        
        # Execute query using the run method
        print("\n" + "-"*50)
        print("MiniAgent Example - Using Tools")
        print("-"*50)
        print("User query:", user_query)
        print("-"*50)
        
        # Use run method for tool execution with formatted text approach
        response = agent.run(user_query)
        
        # Log response
        logger.info(f"Agent response: {response}")
        
        # Print response results
        print("Agent response:")
        print(response)
        print("-"*50)
        
    except Exception as e:
        logger.error(f"Error during execution: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 