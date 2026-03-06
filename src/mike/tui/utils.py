"""TUI utility functions."""

from typing import Optional


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def truncate_string(s: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string to max length with suffix."""
    if len(s) <= max_length:
        return s
    return s[: max_length - len(suffix)] + suffix
