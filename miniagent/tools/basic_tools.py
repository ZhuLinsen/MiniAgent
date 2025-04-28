"""
Basic tools module providing common utility functions.
"""

import requests
import json
import math
import re
import os
import platform
import subprocess
import datetime
import psutil
from typing import Dict, List, Any, Optional
from pathlib import Path

from . import register_tool
from ..logger import get_logger

logger = get_logger(__name__)

@register_tool
def calculator(expression: str) -> float:
    """
    Calculate the result of a mathematical expression.
    
    Args:
        expression: The mathematical expression to calculate, e.g., "2 + 2 * 3"
        
    Returns:
        The calculation result
    """
    print(f"[工具调用] 计算表达式: {expression}")
    # Replace mathematical function names with methods from the math module
    allowed_names = {
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'sqrt': math.sqrt,
        'pow': math.pow,
        'exp': math.exp,
        'log': math.log,
        'log10': math.log10,
        'pi': math.pi,
        'e': math.e
    }
    
    # For safety, clean unsafe characters from the expression
    expression = re.sub(r'[^\d+\-*/().a-zA-Z]', '', expression)
    
    # Execute calculation
    try:
        # Use eval to calculate the expression, providing a safe context
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return float(result)
    except Exception as e:
        raise ValueError(f"Failed to calculate expression '{expression}': {str(e)}")

@register_tool
def get_current_time() -> Dict[str, Any]:
    """
    Get current time information.
    
    Returns:
        Detailed information about the current time, including ISO format, year, month, day, etc.
    """
    print("[工具调用] 获取当前时间")
    now = datetime.datetime.now()
    return {
        "iso": now.isoformat(),
        "year": now.year,
        "month": now.month,
        "day": now.day,
        "hour": now.hour,
        "minute": now.minute,
        "second": now.second,
        "weekday": now.strftime("%A"),
        "formatted": now.strftime("%Y-%m-%d %H:%M:%S")
    }

@register_tool
def system_info() -> Dict[str, Any]:
    """
    Get detailed information about the system.
    
    Returns:
        Dictionary with system information like OS, version, architecture, etc.
    """
    print("[工具调用] 获取系统信息")
    try:
        info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
            "time": datetime.datetime.now().isoformat()
        }
        
        # Add more detailed information for specific platforms
        if platform.system() == "Linux":
            try:
                # Get distribution information
                import distro
                info["distribution"] = distro.name(pretty=True)
                info["distribution_version"] = distro.version()
                info["distribution_codename"] = distro.codename()
            except ImportError:
                # Fallback if distro module is not available
                try:
                    with open('/etc/os-release', 'r') as f:
                        os_release = dict(line.strip().split('=', 1) for line in f if '=' in line)
                    info["distribution"] = os_release.get('PRETTY_NAME', '').strip('"')
                except:
                    pass
                    
        return info
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        raise ValueError(f"Failed to get system information: {str(e)}")

@register_tool
def file_stats(directory: str = ".", pattern: str = "*") -> Dict[str, Any]:
    """
    Get statistics about files in a directory.
    
    Args:
        directory: Directory path to analyze, default is current directory
        pattern: File pattern to match, e.g., "*.py" for Python files
        
    Returns:
        Statistics about files including count, total size, extensions, etc.
    """
    print(f"[工具调用] 统计文件: {directory}/{pattern}")
    try:
        # Resolve the path to handle relative paths and symlinks
        path = Path(directory).resolve()
        
        if not path.exists():
            raise ValueError(f"Directory '{directory}' does not exist")
            
        if not path.is_dir():
            raise ValueError(f"'{directory}' is not a directory")
            
        # Get all files matching the pattern
        files = list(path.glob(pattern))
        
        # Check if we should only count files in the current directory or recursively
        if "**" not in pattern:
            files = [f for f in files if f.is_file()]
        else:
            files = [f for f in files if f.is_file()]
        
        # Calculate statistics
        total_size = sum(f.stat().st_size for f in files)
        
        # Count files by extension
        extensions = {}
        for file in files:
            ext = file.suffix.lower()
            if ext in extensions:
                extensions[ext] += 1
            else:
                extensions[ext] = 1
                
        # Get oldest and newest files
        if files:
            oldest_file = min(files, key=lambda f: f.stat().st_mtime)
            newest_file = max(files, key=lambda f: f.stat().st_mtime)
            oldest = {
                "path": str(oldest_file.relative_to(path.parent)),
                "modified": datetime.datetime.fromtimestamp(oldest_file.stat().st_mtime).isoformat()
            }
            newest = {
                "path": str(newest_file.relative_to(path.parent)),
                "modified": datetime.datetime.fromtimestamp(newest_file.stat().st_mtime).isoformat()
            }
        else:
            oldest = newest = None
            
        return {
            "directory": str(path),
            "pattern": pattern,
            "file_count": len(files),
            "total_size_bytes": total_size,
            "total_size_human": _format_size(total_size),
            "extensions": extensions,
            "oldest_file": oldest,
            "newest_file": newest,
            "analyzed_at": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error analyzing files: {str(e)}")
        raise ValueError(f"Failed to analyze files in '{directory}': {str(e)}")

def _format_size(size_bytes: int) -> str:
    """Helper function to format size in human-readable format"""
    if size_bytes == 0:
        return "0 B"
    size_names = ("B", "KB", "MB", "GB", "TB", "PB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

@register_tool
def web_search(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """
    Perform a web search using DuckDuckGo API.
    
    Args:
        query: Search query content
        num_results: Number of results to return, default is 5
        
    Returns:
        List of search results, each containing title, link, and snippet
    """
    print(f"[工具调用] 搜索: {query}")
    try:
        # DuckDuckGo search API endpoint
        url = "https://serpapi.com/search"
        
        # Get API key from environment
        api_key = os.environ.get("SERPAPI_KEY")
        if not api_key:
            raise ValueError("SERPAPI_KEY environment variable not set")
        
        # Parameters for the search
        params = {
            'engine': 'duckduckgo',
            'q': query,
            'api_key': api_key,
            'kl': 'us-en'  # Region and language
        }
        
        # Send request
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        # Parse the response
        data = response.json()
        
        # Extract organic results
        results = []
        if 'organic_results' in data:
            for result in data['organic_results'][:num_results]:
                results.append({
                    "title": result.get('title', ''),
                    "link": result.get('link', ''),
                    "snippet": result.get('snippet', '')
                })
        
        # Add knowledge graph if available
        if 'knowledge_graph' in data and len(results) < num_results:
            kg = data['knowledge_graph']
            results.append({
                "title": kg.get('title', ''),
                "link": kg.get('website', ''),
                "snippet": kg.get('description', '')
            })
        
        # Add related searches if needed
        if 'related_searches' in data and len(results) < num_results:
            for related in data['related_searches'][:num_results - len(results)]:
                results.append({
                    "title": f"Related: {related.get('query', '')}",
                    "link": related.get('link', ''),
                    "snippet": "Related search suggestion"
                })
        
        return results[:num_results]
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise ValueError(f"Failed to execute search '{query}': {str(e)}")

@register_tool
def http_request(
    url: str, 
    method: str = "GET", 
    headers: Optional[Dict[str, str]] = None, 
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Send an HTTP request and return the response.
    
    Args:
        url: Request URL
        method: Request method, default is "GET"
        headers: Request headers, default is None
        data: Request data, default is None
        
    Returns:
        HTTP response data including status code, headers, and body
    """
    print(f"[工具调用] HTTP请求: {method} {url}")
    try:
        # Prepare request parameters
        kwargs = {
            "headers": headers or {}
        }
        
        # Handle different request methods with data
        if method.upper() in ["POST", "PUT", "PATCH"] and data:
            kwargs["json"] = data
            
        # Send request
        response = requests.request(method.upper(), url, **kwargs)
        
        # Prepare response data
        try:
            response_data = response.json()
        except:
            response_data = response.text
            
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "data": response_data
        }
    except Exception as e:
        raise ValueError(f"Failed to execute HTTP request: {str(e)}")

@register_tool
def disk_usage(path: str = "/") -> Dict[str, Any]:
    """
    Get disk usage information for a specified path.
    
    Args:
        path: Path to check disk usage, default is root directory
        
    Returns:
        Dictionary containing disk usage information
    """
    print(f"[工具调用] 检查磁盘使用情况: {path}")
    try:
        usage = psutil.disk_usage(path)
        return {
            "path": path,
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "percent_used": usage.percent,
            "total_human": _format_size(usage.total),
            "used_human": _format_size(usage.used),
            "free_human": _format_size(usage.free),
            "updated_at": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting disk usage: {str(e)}")
        raise ValueError(f"Failed to get disk usage for '{path}': {str(e)}")

@register_tool
def process_list(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get list of running processes.
    
    Args:
        limit: Maximum number of processes to return, sorted by CPU usage
        
    Returns:
        List of process information dictionaries
    """
    print(f"[工具调用] 获取进程列表 (限制: {limit})")
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'username']):
            try:
                pinfo = proc.info
                processes.append({
                    "pid": pinfo['pid'],
                    "name": pinfo['name'],
                    "cpu_percent": pinfo['cpu_percent'],
                    "memory_percent": pinfo['memory_percent'],
                    "username": pinfo['username']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU usage and limit results
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        return processes[:limit]
    except Exception as e:
        logger.error(f"Error getting process list: {str(e)}")
        raise ValueError(f"Failed to get process list: {str(e)}")

@register_tool
def system_load() -> Dict[str, Any]:
    """
    Get system load information including CPU, memory, and disk usage.
    
    Returns:
        Dictionary containing system load information
    """
    print("[工具调用] 获取系统负载信息")
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Disk usage
        disk = psutil.disk_usage('/')
        
        return {
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count,
                "load_avg": psutil.getloadavg()
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "free": memory.free,
                "percent": memory.percent,
                "total_human": _format_size(memory.total),
                "available_human": _format_size(memory.available),
                "used_human": _format_size(memory.used),
                "free_human": _format_size(memory.free)
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent,
                "total_human": _format_size(disk.total),
                "used_human": _format_size(disk.used),
                "free_human": _format_size(disk.free)
            },
            "updated_at": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting system load: {str(e)}")
        raise ValueError(f"Failed to get system load information: {str(e)}")
