"""Shared logging configuration for the library and teaching CLI."""
import logging
import os
from typing import Dict, Optional

from rich.logging import RichHandler

_LOGGERS: Dict[str, logging.Logger] = {}
_ROOT_LOGGER_CONFIGURED = False
_CLI_MODE = False
_THIRD_PARTY_LOGGERS = ["httpx", "httpcore", "urllib3"]
_LEVEL_MAP = {name: getattr(logging, name) for name in
              ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")}


def _parse_level(default: str = "INFO") -> int:
    return _LEVEL_MAP.get(os.environ.get("LOG_LEVEL", default).upper(), logging.INFO)


def _file_handler(path, level, format_str=None):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    handler = logging.FileHandler(path)
    handler.setFormatter(logging.Formatter(format_str or
                         "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    handler.setLevel(level)
    return handler


def get_logger(name: str, level: Optional[int] = None,
               format_str: Optional[str] = None, log_file: Optional[str] = None) -> logging.Logger:
    """Create once; subsequent requests reuse the logger and its handlers."""
    global _ROOT_LOGGER_CONFIGURED
    if name in _LOGGERS:
        return _LOGGERS[name]
    if not _ROOT_LOGGER_CONFIGURED:
        setup_root_logger(level, format_str)
    logger = logging.getLogger(name)
    level = _parse_level() if level is None else level
    logger.setLevel(level)
    if log_file and not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        logger.addHandler(_file_handler(log_file, level, format_str))
    _LOGGERS[name] = logger
    return logger


def _configure_root_logger(level: Optional[int] = None, format_str: Optional[str] = None):
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    level = _parse_level("WARNING" if _CLI_MODE else "INFO") if level is None else level
    root.setLevel(level)
    handler = RichHandler(rich_tracebacks=True, markup=True)
    handler.setFormatter(logging.Formatter(format_str or "%(message)s"))
    handler.setLevel(level)
    root.addHandler(handler)


def _fix_third_party_loggers():
    for name in _THIRD_PARTY_LOGGERS:
        logger = logging.getLogger(name)
        logger.propagate = False
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
            handler.setLevel(_parse_level())
            logger.addHandler(handler)


def setup_root_logger(level: Optional[int] = None, format_str: Optional[str] = None,
                      log_file: Optional[str] = None) -> None:
    global _ROOT_LOGGER_CONFIGURED
    _configure_root_logger(level, format_str)
    _fix_third_party_loggers()
    _ROOT_LOGGER_CONFIGURED = True
    if log_file:
        logging.getLogger().addHandler(_file_handler(log_file, level or logging.INFO, format_str))


def set_cli_mode(enabled: bool = True) -> None:
    """Use WARNING by default in the CLI, unless LOG_LEVEL overrides it."""
    global _CLI_MODE
    _CLI_MODE = enabled
    if _ROOT_LOGGER_CONFIGURED:
        setup_root_logger()
