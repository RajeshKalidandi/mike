"""Language definitions and utilities for tree-sitter parser."""

from typing import Optional
from tree_sitter import Language

# Import tree-sitter language modules
from tree_sitter_python import language as python_language
from tree_sitter_javascript import language as javascript_language
from tree_sitter_go import language as go_language
from tree_sitter_java import language as java_language
from tree_sitter_rust import language as rust_language
from tree_sitter_c import language as c_language
from tree_sitter_cpp import language as cpp_language
from tree_sitter_ruby import language as ruby_language
from tree_sitter_php import language_php as php_language


# Map normalized language names to tree-sitter Language objects
LANGUAGE_MAP = {
    "python": Language(python_language()),
    "javascript": Language(javascript_language()),
    "typescript": Language(javascript_language()),  # TypeScript uses JavaScript grammar
    "go": Language(go_language()),
    "java": Language(java_language()),
    "rust": Language(rust_language()),
    "c": Language(c_language()),
    "cpp": Language(cpp_language()),
    "c++": Language(cpp_language()),
    "ruby": Language(ruby_language()),
    "php": Language(php_language()),
}

# Set of all supported language names (normalized)
SUPPORTED_LANGUAGES = set(LANGUAGE_MAP.keys())


def normalize_language(language_name: str) -> str:
    """Normalize language name to lowercase standard form.

    Args:
        language_name: The language name to normalize.

    Returns:
        Normalized lowercase language name.
    """
    normalized = language_name.lower().strip()

    # Handle special cases
    if normalized in ("c++", "cplusplus"):
        return "cpp"

    return normalized


def get_language(language_name: str) -> Optional[object]:
    """Get the tree-sitter language object for a given language name.

    Args:
        language_name: The language name (e.g., "Python", "JavaScript").

    Returns:
        The tree-sitter language object, or None if not supported.
    """
    normalized = normalize_language(language_name)
    return LANGUAGE_MAP.get(normalized)


def is_language_supported(language_name: str) -> bool:
    """Check if a language is supported by the parser.

    Args:
        language_name: The language name to check.

    Returns:
        True if the language is supported, False otherwise.
    """
    normalized = normalize_language(language_name)
    return normalized in SUPPORTED_LANGUAGES
