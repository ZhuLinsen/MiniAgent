"""
Logging module providing consistent logging across the entire application.
"""

import logging
import os
from typing import Dict, Optional, List

# Global logger dictionary to keep track of created loggers
_LOGGERS: Dict[str, logging.Logger] = {}

# Flag to track if root logger has been configured
_ROOT_LOGGER_CONFIGURED = False

# List of loggers to fix duplicate handlers for third-party libraries
_THIRD_PARTY_LOGGERS = ["httpx", "httpcore", "urllib3"]

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
    global _ROOT_LOGGER_CONFIGURED
    
    # Check if logger already exists
    if name in _LOGGERS:
        return _LOGGERS[name]
    
    # Set up root logger if not already configured
    if not _ROOT_LOGGER_CONFIGURED:
        _configure_root_logger(level, format_str)
        _fix_third_party_loggers()
        _ROOT_LOGGER_CONFIGURED = True
        
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
    
    # Add file handler if specified - only do this once per logger
    if log_file and not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        # Create directory if needed
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Set default format if not provided
        if format_str is None:
            format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            
        formatter = logging.Formatter(format_str)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)
    
    # Cache logger for future use
    _LOGGERS[name] = logger
    
    return logger

def _configure_root_logger(level: Optional[int] = None, format_str: Optional[str] = None):
    """
    Configure the root logger with console handler.
    
    Args:
        level: Logging level
        format_str: Logging format string
    """
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Clear any existing handlers to avoid duplicates
    if root_logger.handlers:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
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
    
    root_logger.setLevel(level)
    
    # Set default format if not provided
    if format_str is None:
        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
    formatter = logging.Formatter(format_str)
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    root_logger.addHandler(console_handler)

def _fix_third_party_loggers():
    """
    Fix third-party library loggers to prevent duplicate log messages.
    This is especially useful for libraries like httpx, urllib3, etc.
    """
    for logger_name in _THIRD_PARTY_LOGGERS:
        logger = logging.getLogger(logger_name)
        # Set propagate to False to prevent the logs from being passed to the parent logger
        logger.propagate = False
        
        # If the logger doesn't have any handlers, add one to ensure messages are still logged
        if not logger.handlers:
            # Get level from environment or use INFO as default
            env_level = os.environ.get("LOG_LEVEL", "INFO").upper()
            level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL
            }
            level = level_map.get(env_level, logging.INFO)
            
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            handler.setLevel(level)
            logger.addHandler(handler)

def setup_root_logger(level: Optional[int] = None, format_str: Optional[str] = None, log_file: Optional[str] = None) -> None:
    """
    Configure the root logger.
    
    Args:
        level: Logging level (defaults to environment variable or INFO)
        format_str: Logging format string
        log_file: Optional file path to log to
    """
    global _ROOT_LOGGER_CONFIGURED
    
    # Configure the root logger
    _configure_root_logger(level, format_str)
    _fix_third_party_loggers()
    _ROOT_LOGGER_CONFIGURED = True
    
    # Add file handler if specified
    if log_file:
        root_logger = logging.getLogger()
        
        # Set default format if not provided
        if format_str is None:
            format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            
        formatter = logging.Formatter(format_str)
        
        # Create directory if needed
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level or logging.INFO)
        root_logger.addHandler(file_handler) 