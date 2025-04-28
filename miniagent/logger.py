"""
Logging module providing consistent logging across the entire application.
"""

import logging
import os
from typing import Dict, Optional

# Global logger dictionary to keep track of created loggers
_LOGGERS: Dict[str, logging.Logger] = {}

def get_logger(
    name: str, 
    level: Optional[int] = None, 
    format_str: Optional[str] = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Get or create a logger with the given name and configuration.
    
    Args:
        name: The name of the logger.
        level: The logging level (defaults to environment variable LOG_LEVEL or INFO).
        format_str: The logging format string (defaults to a standard format).
        log_file: Optional file path to also log to a file.
        
    Returns:
        A configured logger instance.
    """
    # Check if logger already exists
    if name in _LOGGERS:
        return _LOGGERS[name]
        
    # Create new logger
    logger = logging.getLogger(name)
    
    # Set log level from environment variable or default to INFO
    if level is None:
        env_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        level = level_map.get(env_level, logging.INFO)
        
    logger.setLevel(level)
    
    # Set default format if not provided
    if format_str is None:
        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
    formatter = logging.Formatter(format_str)
    
    # Add console handler if logger doesn't have handlers yet
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        # Create directory if needed
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)
    
    # Cache logger for future use
    _LOGGERS[name] = logger
    
    return logger

def setup_root_logger(level: Optional[int] = None, format_str: Optional[str] = None, log_file: Optional[str] = None) -> None:
    """
    Configure the root logger.
    
    Args:
        level: Logging level (defaults to environment variable or INFO)
        format_str: Logging format string
        log_file: Optional file path to log to
    """
    # Get the root logger
    root_logger = get_logger("root", level, format_str, log_file)
    
    # Set as the root logger
    logging.root = root_logger 