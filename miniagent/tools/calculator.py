"""
Calculator tool for MiniAgent.

This module provides a simple calculator tool that can perform basic arithmetic operations.
"""

import re
import ast
import math
import logging
from typing import Dict, Any, Union, List

from miniagent.tools import register_tool

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@register_tool
def calculate(expression: str) -> Dict[str, Any]:
    """
    Evaluate a mathematical expression.
    
    This tool can handle basic arithmetic operations, as well as some mathematical functions 
    like sin, cos, sqrt, etc.
    
    Args:
        expression: Mathematical expression to evaluate
        
    Returns:
        Dictionary containing the result or error
    """
    try:
        # Clean and preprocess the expression
        expression = expression.strip()
        
        # Create a safe dictionary with allowed mathematical functions
        safe_dict = {
            'abs': abs,
            'pow': pow,
            'round': round,
            'min': min,
            'max': max,
            'sum': sum,
            'len': len,
            'int': int,
            'float': float,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'asin': math.asin,
            'acos': math.acos,
            'atan': math.atan,
            'atan2': math.atan2,
            'sinh': math.sinh,
            'cosh': math.cosh,
            'tanh': math.tanh,
            'exp': math.exp,
            'log': math.log,
            'log10': math.log10,
            'sqrt': math.sqrt,
            'pi': math.pi,
            'e': math.e,
            'ceil': math.ceil,
            'floor': math.floor,
            'degrees': math.degrees,
            'radians': math.radians
        }
        
        # Evaluate the expression
        tree = ast.parse(expression, mode='eval')
        
        # Verify that the expression only contains allowed operations
        check_node(tree.body)
        
        # Evaluate the expression using a safe environment
        result = eval(compile(tree, '<string>', 'eval'), {"__builtins__": {}}, safe_dict)
        
        # Format the result
        if isinstance(result, (int, float)):
            return {
                "expression": expression,
                "result": result
            }
        else:
            return {
                "expression": expression,
                "result": str(result)
            }
    except Exception as e:
        logger.error(f"Calculator error: {e}", exc_info=True)
        return {
            "expression": expression,
            "error": f"Error evaluating expression: {str(e)}"
        }

def check_node(node):
    """
    Recursively check if a node in the AST contains only allowed operations.
    
    Args:
        node: AST node to check
        
    Raises:
        ValueError: If the node contains disallowed operations
    """
    # Check for disallowed node types
    if isinstance(node, (ast.Call, ast.Name)):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                allowed_funcs = [
                    'abs', 'pow', 'round', 'min', 'max', 'sum', 'len', 'int', 'float',
                    'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'atan2',
                    'sinh', 'cosh', 'tanh', 'exp', 'log', 'log10', 'sqrt',
                    'ceil', 'floor', 'degrees', 'radians'
                ]
                if func_name not in allowed_funcs:
                    raise ValueError(f"Function '{func_name}' is not allowed")
            else:
                raise ValueError("Only direct function calls are allowed")
            
            # Check function arguments
            for arg in node.args:
                check_node(arg)
            for keyword in node.keywords:
                check_node(keyword.value)
    
    # Recursively check child nodes
    for child in ast.iter_child_nodes(node):
        check_node(child)

# Example usage
if __name__ == "__main__":
    test_expression = "2 + 3 * 4"
    result = calculate(test_expression)
    print(f"Expression: {test_expression}, Result: {result}")
    
    test_expression = "sin(pi/2)"
    result = calculate(test_expression)
    print(f"Expression: {test_expression}, Result: {result}") 