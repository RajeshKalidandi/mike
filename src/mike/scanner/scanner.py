"""File scanner module for repository ingestion."""

import hashlib
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set


class FileScanner:
    """Scans directories and extracts file metadata."""

    # Binary file extensions to skip
    BINARY_EXTENSIONS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".ico",
        ".svg",
        ".mp3",
        ".mp4",
        ".avi",
        ".mov",
        ".wav",
        ".flac",
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".7z",
        ".rar",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".bin",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".pyc",
        ".pyo",
        ".class",
        ".o",
        ".a",
    }

    def __init__(self):
        self.gitignore_patterns: List[str] = []

    def scan_directory(self, root_path: str) -> List[Dict]:
        """Recursively scan directory and return file metadata.

        Args:
            root_path: Root directory to scan

        Returns:
            List of file info dictionaries
        """
        root = Path(root_path).resolve()
        files = []

        # Load .gitignore patterns if present
        gitignore_path = root / ".gitignore"
        if gitignore_path.exists():
            self.gitignore_patterns = self._load_gitignore(gitignore_path)
        else:
            self.gitignore_patterns = []

        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue

            # Get relative path
            try:
                relative_path = file_path.relative_to(root)
            except ValueError:
                continue

            # Skip if matches gitignore
            if self._matches_gitignore(relative_path):
                continue

            # Skip binary files
            if file_path.suffix.lower() in self.BINARY_EXTENSIONS:
                continue

            # Skip hidden files and directories
            if any(part.startswith(".") for part in relative_path.parts[:-1]):
                continue
            if (
                relative_path.name.startswith(".")
                and relative_path.name != ".gitignore"
            ):
                continue

            # Get file info
            file_info = self._get_file_info(file_path, relative_path)
            if file_info:
                files.append(file_info)

        return files

    def _load_gitignore(self, gitignore_path: Path) -> List[str]:
        """Load .gitignore patterns."""
        patterns = []
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        patterns.append(line)
        except Exception:
            pass
        return patterns

    def _matches_gitignore(self, relative_path: Path) -> bool:
        """Check if path matches any gitignore pattern."""
        path_str = str(relative_path)
        path_parts = relative_path.parts

        for pattern in self.gitignore_patterns:
            # Handle directory patterns (ending with /)
            if pattern.endswith("/"):
                dir_pattern = pattern[:-1]
                # Check if any part of the path matches
                for part in path_parts:
                    if self._match_pattern(part, dir_pattern):
                        return True
                # Also check if the full path matches
                if self._match_pattern(path_str, dir_pattern):
                    return True
            else:
                # Check file pattern
                if self._match_pattern(path_str, pattern):
                    return True
                # Check basename
                if self._match_pattern(relative_path.name, pattern):
                    return True

        return False

    def _match_pattern(self, text: str, pattern: str) -> bool:
        """Simple pattern matching for gitignore."""
        # Handle * wildcard
        if "*" in pattern:
            # Convert pattern to regex
            regex_pattern = (
                pattern.replace(".", r"\.").replace("*", ".*").replace("?", ".")
            )
            try:
                return bool(re.match(f"^{regex_pattern}$", text))
            except re.error:
                return text == pattern
        return (
            text == pattern
            or text.endswith("/" + pattern)
            or text.startswith(pattern + "/")
        )

    def _get_file_info(self, file_path: Path, relative_path: Path) -> Optional[Dict]:
        """Extract metadata from a file."""
        try:
            content = file_path.read_bytes()

            # Skip empty files
            if not content:
                return None

            # Calculate hash
            content_hash = hashlib.sha256(content).hexdigest()

            # Count lines
            try:
                text_content = content.decode("utf-8")
                line_count = len(text_content.splitlines())
            except UnicodeDecodeError:
                # Binary file, skip
                return None

            # Detect language
            language = self._detect_language(file_path)

            return {
                "relative_path": str(relative_path),
                "absolute_path": str(file_path),
                "language": language,
                "size_bytes": len(content),
                "line_count": line_count,
                "content_hash": content_hash,
                "extension": file_path.suffix.lower(),
            }
        except Exception:
            return None

    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        ext = file_path.suffix.lower()

        language_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "JavaScript",
            ".tsx": "TypeScript",
            ".java": "Java",
            ".go": "Go",
            ".rs": "Rust",
            ".c": "C",
            ".cpp": "C++",
            ".h": "C",
            ".hpp": "C++",
            ".rb": "Ruby",
            ".php": "PHP",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".scala": "Scala",
            ".r": "R",
            ".m": "Objective-C",
            ".cs": "C#",
            ".fs": "F#",
            ".ex": "Elixir",
            ".exs": "Elixir",
            ".erl": "Erlang",
            ".clj": "Clojure",
            ".hs": "Haskell",
            ".lua": "Lua",
            ".pl": "Perl",
            ".sh": "Shell",
            ".bash": "Shell",
            ".zsh": "Shell",
            ".ps1": "PowerShell",
            ".sql": "SQL",
            ".html": "HTML",
            ".htm": "HTML",
            ".css": "CSS",
            ".scss": "SCSS",
            ".sass": "Sass",
            ".less": "Less",
            ".xml": "XML",
            ".json": "JSON",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".toml": "TOML",
            ".ini": "INI",
            ".cfg": "Config",
            ".conf": "Config",
            ".md": "Markdown",
            ".rst": "reStructuredText",
            ".txt": "Text",
            ".dockerfile": "Dockerfile",
            ".makefile": "Makefile",
            ".cmake": "CMake",
        }

        # Check for special filenames
        filename = file_path.name.lower()
        if filename == "dockerfile" or filename.startswith("dockerfile."):
            return "Dockerfile"
        if filename in ("makefile", "gnumakefile"):
            return "Makefile"
        if filename == "cmakelists.txt":
            return "CMake"

        return language_map.get(ext, "Unknown")
