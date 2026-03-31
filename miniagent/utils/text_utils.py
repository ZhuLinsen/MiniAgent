"""Shared text utilities for MiniAgent."""


def smart_truncate(text: str, limit: int) -> str:
    """Truncate text keeping both head and tail so error info at end is preserved.
    
    Uses 70/30 split: 70% from the beginning, 30% from the end.
    
    Args:
        text: Text to truncate.
        limit: Maximum character count.
        
    Returns:
        Original text if within limit, otherwise truncated with indicator.
    """
    if len(text) <= limit:
        return text
    head_size = int(limit * 0.7)
    tail_size = limit - head_size - 80
    return (
        text[:head_size]
        + f"\n\n... [truncated {len(text) - head_size - tail_size} chars, {len(text)} total] ...\n\n"
        + text[-tail_size:]
    )
