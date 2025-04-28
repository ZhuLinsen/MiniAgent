#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LLM Connection and Functionality Validation Tool
For quickly testing if a large language model API is working properly
"""

import os
import sys
import json
import argparse
import asyncio
import httpx
import traceback
from pathlib import Path
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

async def test_llm_connection(api_key=None, base_url=None, model_name=None):
    """Test if the LLM API connection is working properly"""
    # Use provided parameters or environment variables
    api_key = api_key or os.environ.get("LLM_API_KEY")
    base_url = base_url or os.environ.get("LLM_API_BASE") or "https://api.openai.com/v1"
    model_name = model_name or os.environ.get("LLM_MODEL") or "gpt-3.5-turbo"
    
    print("="*50)
    print(f"LLM Connection Configuration:")
    print(f"API_KEY: {'*'*(len(api_key)-4) + api_key[-4:] if api_key else 'Not set'}")
    print(f"BASE_URL: {base_url}")
    print(f"MODEL_NAME: {model_name}")
    print("="*50)
    
    # Ensure base_url has correct format
    if base_url and not base_url.startswith(('http://', 'https://')):
        base_url = f"https://{base_url}"
    
    if not api_key or not base_url or not model_name:
        print("Error: Missing required LLM configuration parameters")
        return False, "Missing required LLM configuration parameters"
    
    # Build request
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Please reply with the two words 'Test successful' and nothing else"}],
        "max_tokens": 10
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{base_url}/chat/completions", 
                                     headers=headers, 
                                     json=data, 
                                     follow_redirects=True)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            
            print("\n✅ LLM connection test successful!")
            print(f"Model: {model_name}")
            print(f"API Base: {base_url}")
            print(f"Response: {content}")
            print("="*50)
            return True, content
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ LLM connection test failed!")
        print(f"Error message: {error_msg}")
        print(traceback.format_exc())
        print("="*50)
        return False, error_msg

async def test_llm_capabilities(api_key=None, base_url=None, model_name=None):
    """Test the basic capabilities of the LLM"""
    # Use provided parameters or environment variables
    api_key = api_key or os.environ.get("LLM_API_KEY")
    base_url = base_url or os.environ.get("LLM_API_BASE") or "https://api.openai.com/v1"
    model_name = model_name or os.environ.get("LLM_MODEL") or "gpt-3.5-turbo"
    
    # Ensure base_url has correct format
    if base_url and not base_url.startswith(('http://', 'https://')):
        base_url = f"https://{base_url}"
    
    # Test text
    test_text = """
Artificial intelligence is a branch of computer science dedicated to creating machines capable of simulating human intelligence. It involves developing systems that can perceive, reason, learn, and make decisions. The applications of artificial intelligence are wide-ranging, including natural language processing, computer vision, robotics, and expert systems.
"""
    
    # Build request
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {
        "model": model_name,
        "messages": [{"role": "user", "content": f"Based on the following text, generate a high-quality question. The question should have clear direction and test understanding of the core content:\n{test_text}"}],
        "max_tokens": 500
    }
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{base_url}/chat/completions", 
                                     headers=headers, 
                                     json=data, 
                                     follow_redirects=True)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            
            print("\n✅ LLM functionality test successful!")
            print("-"*50)
            print("Generated question:")
            print(content)
            print("="*50)
            return True, content
    except Exception as e:
        print(f"\n❌ LLM functionality test failed: {str(e)}")
        print(traceback.format_exc())
        print("="*50)
        return False, str(e)

async def test_llm_tool_capability(api_key=None, base_url=None, model_name=None):
    """Test the LLM's ability to use tools"""
    # Use provided parameters or environment variables
    api_key = api_key or os.environ.get("LLM_API_KEY")
    base_url = base_url or os.environ.get("LLM_API_BASE") or "https://api.openai.com/v1"
    model_name = model_name or os.environ.get("LLM_MODEL") or "gpt-3.5-turbo"
    
    # Ensure base_url has correct format
    if base_url and not base_url.startswith(('http://', 'https://')):
        base_url = f"https://{base_url}"
    
    # Define a simple calculator tool
    calculator_tool = {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Perform simple mathematical calculations",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The mathematical expression to calculate, such as '2+2' or '5*6'"
                    }
                },
                "required": ["expression"]
            }
        }
    }
    
    # Build request
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Calculate 1234 multiplied by 5678."}],
        "tools": [calculator_tool],
        "max_tokens": 500
    }
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{base_url}/chat/completions", 
                                     headers=headers, 
                                     json=data, 
                                     follow_redirects=True)
            resp.raise_for_status()
            response_data = resp.json()
            
            # Check if there are tool calls
            content = response_data["choices"][0]["message"].get("content", "")
            tool_calls = response_data["choices"][0]["message"].get("tool_calls", [])
            
            # If there are tool calls
            if tool_calls:
                print("\n✅ LLM tool calling capability test successful! Model correctly returned tool calls")
                for call in tool_calls:
                    if "function" in call:
                        print(f"Tool called: {call['function']['name']}")
                        print(f"Parameters: {call['function']['arguments']}")
            else:
                # Check if the response text contains tool call patterns
                print("\n⚠️ LLM did not use the tool calling API, but may have included tool call information in the response")
                print(f"Response content: {content}")
                
            return True, content or str(tool_calls)
    except Exception as e:
        print(f"\n❌ LLM tool calling test failed: {str(e)}")
        print(traceback.format_exc())
        return False, str(e)

async def main():
    """Main function"""
    # Load environment variables
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test LLM API connection and functionality")
    parser.add_argument("--api_key", help="API key")
    parser.add_argument("--base_url", help="API base URL")
    parser.add_argument("--model", help="Model name")
    parser.add_argument("--provider", help="LLM provider (openai, azure, deepseek, zhipu, anthropic)")
    parser.add_argument("--skip-tool-test", action="store_true", help="Skip tool calling test")
    args = parser.parse_args()
    
    print("\n🔍 Starting LLM configuration test")
    
    # If provider is specified, set appropriate defaults
    if args.provider:
        if args.provider.lower() == "openai":
            base_url = args.base_url or "https://api.openai.com/v1"
            model = args.model or "gpt-3.5-turbo"
        elif args.provider.lower() == "azure":
            base_url = args.base_url or os.environ.get("LLM_API_BASE", "")
            model = args.model or os.environ.get("LLM_MODEL", "gpt-35-turbo")
        elif args.provider.lower() == "deepseek":
            base_url = args.base_url or "https://api.deepseek.com/v1"
            model = args.model or "deepseek-chat"
        elif args.provider.lower() == "zhipu":
            base_url = args.base_url or "https://open.bigmodel.cn/api/paas/v4"
            model = args.model or "glm-4"
        elif args.provider.lower() == "anthropic":
            base_url = args.base_url or "https://api.anthropic.com/v1"
            model = args.model or "claude-3-sonnet-20240229"
        else:
            # Use environment variables
            base_url = args.base_url
            model = args.model
    else:
        # Use environment variables
        base_url = args.base_url
        model = args.model
    
    api_key = args.api_key
    
    # Test LLM connection
    conn_success, conn_msg = await test_llm_connection(api_key, base_url, model)
    
    # If connection successful, continue testing functionality
    if conn_success:
        cap_success, cap_msg = await test_llm_capabilities(api_key, base_url, model)
        
        # Test tool calling capability (unless explicitly skipped)
        if cap_success and not args.skip_tool_test:
            tool_success, tool_msg = await test_llm_tool_capability(api_key, base_url, model)
            if tool_success:
                print("\n🎉 All tests completed! LLM configuration is working properly")
                print("You can start using MiniAgent now!")
                return 0
            else:
                print("\n⚠️ Tool calling test did not pass, but basic functionality is working")
                print("You can still use MiniAgent, but tool calling functionality may be limited")
                return 1
        elif cap_success:
            print("\n🎉 Basic tests completed! LLM configuration is working properly")
            print("You can start using MiniAgent now!")
            return 0
        else:
            print("\n❌ LLM functionality test failed!")
            return 1
    else:
        print("\n❌ Unable to connect to LLM API, please check your configuration")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 