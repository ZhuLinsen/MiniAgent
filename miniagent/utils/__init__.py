"""Compatibility utilities loaded only when requested."""

def __getattr__(name):
    if name == "Reflector":
        from .reflector import Reflector
        return Reflector
    if name == "smart_truncate":
        from .text_utils import smart_truncate
        return smart_truncate
    if name in {"parse_json", "extract_json_from_markdown", "extract_tool_call", "format_tool_response"}:
        from . import json_utils
        return getattr(json_utils, name)
    raise AttributeError(name)
