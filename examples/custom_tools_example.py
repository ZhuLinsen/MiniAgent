#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Example demonstrating custom tool registration and usage
"""

import os
import sys
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import required modules
from miniagent import MiniAgent
from miniagent.tools import register_tool, get_tool_description
from miniagent.logger import get_logger

# Configure logging using MiniAgent's logger
logger = get_logger("custom_tools_example")

# Custom tool functions
@register_tool
def fibonacci_calculator(n: int) -> int:
    """
    Calculate the nth Fibonacci number (starting from 0)
    
    Args:
        n: The position in the sequence (starting from 0)
    """
    print(f"[Tool Call] Calculating {n}th Fibonacci number")
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b

@register_tool
def text_analyzer(text: str) -> Dict:
    """
    Analyze text content for character count, word count, sentence count and common words
    
    Args:
        text: The text content to analyze
    """
    print(f"[Tool Call] Analyzing text: {text[:50]}...")
    # Basic text analysis
    char_count = len(text)
    words = text.split()
    word_count = len(words)
    sentences = text.split('.')
    sentence_count = len([s for s in sentences if s.strip()])
    
    # Find common words (simple implementation)
    word_freq = {}
    for word in words:
        word = word.lower().strip('.,!?')
        if word:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    # Get top 5 common words
    common_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "character_count": char_count,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "common_words": dict(common_words)
    }

def main():
    """Main function"""
    
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
    
    # Create MiniAgent instance with environment variables
    agent = MiniAgent(
        model=os.environ.get("LLM_MODEL", "deepseek-chat"),
        api_key=api_key,
        base_url=os.environ.get("LLM_API_BASE", "https://api.deepseek.com/v1"),
        temperature=float(os.environ.get("LLM_TEMPERATURE", "0.7")),
        use_reflector=os.environ.get("ENABLE_REFLECTION", "false").lower() == "true"
    )
    
    # Register custom tools
    agent.tools = []
    for tool_func in [fibonacci_calculator, text_analyzer]:
        tool_desc = get_tool_description(tool_func)
        agent.tools.append({
            "name": tool_desc["name"],
            "description": tool_desc["description"],
            "parameters": tool_desc["parameters"],
            "executor": tool_func
        })
    
    # Add basic tools
    from miniagent.tools.basic_tools import calculator, get_current_time
    for tool_func in [calculator, get_current_time]:
        tool_desc = get_tool_description(tool_func)
        agent.tools.append({
            "name": tool_desc["name"],
            "description": tool_desc["description"],
            "parameters": tool_desc["parameters"],
            "executor": tool_func
        })
    
    logger.info(f"Loaded tools: {[tool['name'] for tool in agent.tools]}")
    
    # Test query
    query = """
    Let me test the custom tools:
    1. Calculate the 10th Fibonacci number
    2. Analyze this text: "The quick brown fox jumps over the lazy dog. This is a pangram that contains every letter of the alphabet."
    """
    
    print("\nUser Query:")
    print(query)
    print("-" * 50)
    
    # Run Agent
    try:
        response = agent.run(query=query)
        print("\nAgent Response:")
        print(response)
    except Exception as e:
        logger.error(f"Error running agent: {str(e)}")

if __name__ == "__main__":
    main() 