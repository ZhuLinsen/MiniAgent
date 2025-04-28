#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试所有可用工具的示例脚本
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入所需模块
from miniagent.tools import load_tools

def test_basic_tools():
    """测试基础工具"""
    print("\n=== 测试基础工具 ===")
    
    # 测试计算器
    from miniagent.tools.basic_tools import calculator
    result = calculator("123 * 456 + 789")
    print(f"计算器测试: 123 * 456 + 789 = {result}")
    
    # 测试获取当前时间
    from miniagent.tools.basic_tools import get_current_time
    time_info = get_current_time()
    print(f"当前时间: {time_info['formatted']}")
    
    # 测试系统信息
    from miniagent.tools.basic_tools import system_info
    sys_info = system_info()
    print(f"系统信息: {sys_info['platform']} {sys_info['platform_release']}")
    
    # 测试文件统计
    from miniagent.tools.basic_tools import file_stats
    stats = file_stats(".", "*.py")
    print(f"Python文件统计: {stats['file_count']}个文件")

def test_network_tools():
    """测试网络工具"""
    print("\n=== 测试网络工具 ===")
    
    # 测试HTTP请求
    from miniagent.tools.basic_tools import http_request
    response = http_request("https://api.github.com/zen")
    print(f"GitHub API响应: {response['data']}")
    
    # 测试网页搜索（需要SERPAPI_KEY）
    from miniagent.tools.basic_tools import web_search
    try:
        results = web_search("Python 编程", num_results=3)
        print(f"搜索结果: {len(results)}条")
    except Exception as e:
        print(f"搜索测试失败: {str(e)}")

def test_system_tools():
    """测试系统工具"""
    print("\n=== 测试系统工具 ===")
    
    # 测试磁盘使用情况
    from miniagent.tools.basic_tools import disk_usage
    usage = disk_usage("/")
    print(f"磁盘使用情况: {usage['percent_used']}%")
    
    # 测试进程列表
    from miniagent.tools.basic_tools import process_list
    processes = process_list(limit=5)
    print("CPU占用最高的5个进程:")
    for proc in processes:
        print(f"- {proc['name']}: {proc['cpu_percent']}%")
    
    # 测试系统负载
    from miniagent.tools.basic_tools import system_load
    load = system_load()
    print(f"系统负载: CPU {load['cpu']['percent']}%, 内存 {load['memory']['percent']}%")

def main():
    """主函数"""
    # 加载环境变量
    load_dotenv()
    
    # 测试所有工具
    test_basic_tools()
    test_network_tools()
    test_system_tools()

if __name__ == "__main__":
    main() 