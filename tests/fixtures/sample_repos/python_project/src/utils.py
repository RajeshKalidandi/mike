"""Utility functions for Python project."""

import re
from typing import Any, Dict, List, Optional


def format_data(data: Dict[str, Any]) -> str:
    """Format dictionary data as string."""
    return ", ".join(f"{k}={v}" for k, v in data.items())


def validate_input(data: Dict[str, Any]) -> bool:
    """Validate input data."""
    if not isinstance(data, dict):
        return False
    return len(data) > 0


def parse_int(value: str, default: int = 0) -> int:
    """Parse string to integer with default."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def sanitize_string(value: str) -> str:
    """Sanitize string input."""
    if not isinstance(value, str):
        return ""
    # Remove special characters
    return re.sub(r"[^<a-zA-Z0-9\s]", "", value)


def chunk_list(items: List[Any], size: int) -> List[List[Any]]:
    """Split list into chunks of specified size."""
    return [items[i : i + size] for i in range(0, len(items), size)]


def flatten_list(nested: List[List[Any]]) -> List[Any]:
    """Flatten a nested list."""
    return [item for sublist in nested for item in sublist]
