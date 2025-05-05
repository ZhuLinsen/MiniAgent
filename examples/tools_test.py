#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Example script to test all available tools
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import required modules
from miniagent.tools import load_tools
from miniagent.logger import get_logger

# Configure logging using MiniAgent's logger
logger = get_logger("tools_test")

def test_basic_tools():
    """Test basic tools"""
    print("\n=== Testing Basic Tools ===")
    
    # Test calculator
    from miniagent.tools.basic_tools import calculator
    result = calculator("123 * 456 + 789")
    print(f"Calculator test: 123 * 456 + 789 = {result}")
    
    # Test get current time
    from miniagent.tools.basic_tools import get_current_time
    time_info = get_current_time()
    print(f"Current time: {time_info['formatted']}")
    
    # Test system info
    from miniagent.tools.basic_tools import system_info
    sys_info = system_info()
    print(f"System info: {sys_info['platform']} {sys_info['platform_release']}")
    
    # Test file stats
    from miniagent.tools.basic_tools import file_stats
    stats = file_stats(".", "*.py")
    print(f"Python file stats: {stats['file_count']} files")

def test_network_tools():
    """Test network tools"""
    print("\n=== Testing Network Tools ===")
    
    # Test HTTP request
    from miniagent.tools.basic_tools import http_request
    response = http_request("https://api.github.com/zen")
    print(f"GitHub API response: {response['data']}")
    
    # Test web search (requires SERPAPI_KEY)
    from miniagent.tools.basic_tools import web_search
    try:
        results = web_search("Python programming", num_results=3)
        print(f"Search results: {len(results)} items")
    except Exception as e:
        print(f"Search test failed: {str(e)}")

def test_system_tools():
    """Test system tools"""
    print("\n=== Testing System Tools ===")
    
    # Test disk usage
    from miniagent.tools.basic_tools import disk_usage
    usage = disk_usage("/")
    print(f"Disk usage: {usage['percent_used']}%")
    
    # Test process list
    from miniagent.tools.basic_tools import process_list
    processes = process_list(limit=5)
    print("Top 5 processes by CPU usage:")
    for proc in processes:
        print(f"- {proc['name']}: {proc['cpu_percent']}%")
    
    # Test system load
    from miniagent.tools.basic_tools import system_load
    load = system_load()
    print(f"System load: CPU {load['cpu']['percent']}%, Memory {load['memory']['percent']}%")

def main():
    """Main function"""
    # Load environment variables
    load_dotenv()
    
    # Test all tools
    test_basic_tools()
    test_network_tools()
    test_system_tools()

if __name__ == "__main__":
    main() 