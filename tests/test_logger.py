"""Tests for the logging module."""

import logging
import os
import pytest
from unittest.mock import patch

from miniagent.logger import get_logger, _parse_level, _LEVEL_MAP


def test_get_logger_returns_logger():
    """get_logger() returns a standard logging.Logger."""
    lg = get_logger("test_basic")
    assert isinstance(lg, logging.Logger)
    assert lg.name == "test_basic"


def test_get_logger_caches():
    """Same name should return same logger instance."""
    a = get_logger("test_cache_a")
    b = get_logger("test_cache_a")
    assert a is b


def test_parse_level_default():
    """Without LOG_LEVEL env var, default should be INFO."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("LOG_LEVEL", None)
        assert _parse_level() == logging.INFO


def test_parse_level_debug():
    """LOG_LEVEL=DEBUG should map to logging.DEBUG."""
    with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
        assert _parse_level() == logging.DEBUG


def test_parse_level_case_insensitive():
    """LOG_LEVEL should be case-insensitive."""
    with patch.dict(os.environ, {"LOG_LEVEL": "warning"}):
        assert _parse_level() == logging.WARNING


def test_parse_level_invalid_falls_back():
    """Invalid LOG_LEVEL should fall back to INFO."""
    with patch.dict(os.environ, {"LOG_LEVEL": "NONSENSE"}):
        assert _parse_level() == logging.INFO


def test_level_map_complete():
    """_LEVEL_MAP must have all 5 standard levels."""
    expected = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    assert set(_LEVEL_MAP.keys()) == expected


def test_get_logger_with_explicit_level():
    """get_logger with explicit level should set that level."""
    lg = get_logger("test_explicit_level", level=logging.ERROR)
    assert lg.level == logging.ERROR
