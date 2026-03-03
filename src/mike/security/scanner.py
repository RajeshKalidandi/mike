"""Security scanner implementation."""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

from mike.security.models import (
    ConfidenceLevel,
    PatternCategory,
    SecurityFinding,
    SecurityReport,
    SeverityLevel,
)
from mike.security.patterns import PatternDatabase


class SecurityScanner:
    """Scans code for security vulnerabilities."""

    # File extensions to scan
    CODE_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".java",
        ".go",
        ".rs",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".scala",
        ".cs",
        ".fs",
        ".ex",
        ".exs",
        ".erl",
        ".clj",
        ".hs",
        ".lua",
        ".pl",
        ".sh",
        ".bash",
        ".zsh",
        ".ps1",
        ".sql",
        ".html",
        ".htm",
        ".css",
        ".scss",
        ".sass",
        ".less",
        ".xml",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".md",
        ".rst",
        ".txt",
        ".dockerfile",
        ".makefile",
    }

    # Binary extensions to skip
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

    # Directories to skip
    SKIP_DIRECTORIES = {
        ".git",
        ".svn",
        ".hg",
        ".bzr",
        "__pycache__",
        "node_modules",
        "venv",
        ".venv",
        "env",
        ".env",
        "dist",
        "build",
        "target",
        ".idea",
        ".vscode",
        ".vs",
        "out",
        "bin",
        "obj",
        "coverage",
        ".tox",
        ".pytest_cache",
        ".mypy_cache",
        ".coverage",
        "htmlcov",
    }

    def __init__(self):
        """Initialize security scanner."""
        self.pattern_db = PatternDatabase()

    def scan_file(
        self,
        file_path: str,
        content: Optional[str] = None,
        language: Optional[str] = None,
    ) -> List[SecurityFinding]:
        """Scan a single file for security issues.

        Args:
            file_path: Path to the file to scan
            content: Optional file content (if None, file will be read)
            language: Optional language override

        Returns:
            List of security findings
        """
        findings = []
        path = Path(file_path)

        # Skip binary files
        if path.suffix.lower() in self.BINARY_EXTENSIONS:
            return findings

        # Try to read file if content not provided
        if content is None:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except (IOError, OSError, UnicodeDecodeError):
                # Can't read file (binary or permission issue)
                return findings

        # Skip empty files
        if not content.strip():
            return findings

        # Detect language
        if language is None:
            language = self._detect_language(path)

        # Get context lines for better reporting
        lines = content.split("\n")

        # Pattern-based scanning
        pattern_findings = self._scan_patterns(content, file_path, lines, language)
        findings.extend(pattern_findings)

        # Entropy-based secret detection
        entropy_findings = self._scan_entropy(content, file_path, lines)
        findings.extend(entropy_findings)

        return findings

    def _scan_patterns(
        self,
        content: str,
        file_path: str,
        lines: List[str],
        language: Optional[str],
    ) -> List[SecurityFinding]:
        """Scan for pattern-based security issues."""
        findings = []

        # Get patterns for this language
        if language:
            patterns = self.pattern_db.get_patterns_by_language(language)
        else:
            patterns = self.pattern_db.patterns

        for pattern in patterns:
            for match in re.finditer(pattern.pattern, content):
                # Calculate line and column
                line_num = content[: match.start()].count("\n") + 1

                # Find column position
                line_start = content.rfind("\n", 0, match.start()) + 1
                col_start = match.start() - line_start
                col_end = match.end() - line_start

                # Get matched text
                matched_text = match.group(0)

                # Skip false positives
                if self._is_false_positive(matched_text, pattern):
                    continue

                # Get context lines
                context_lines = self._get_context_lines(lines, line_num)

                finding = SecurityFinding(
                    pattern_id=pattern.id,
                    category=pattern.category,
                    severity=pattern.severity,
                    confidence=pattern.confidence,
                    file_path=file_path,
                    line_number=line_num,
                    column_start=col_start,
                    column_end=col_end,
                    matched_text=matched_text,
                    message=pattern.description,
                    remediation=pattern.remediation,
                    context_lines=context_lines,
                )
                findings.append(finding)

        return findings

    def _scan_entropy(
        self,
        content: str,
        file_path: str,
        lines: List[str],
    ) -> List[SecurityFinding]:
        """Scan for high-entropy strings that may be secrets."""
        findings = []

        # Pattern to find potential secret strings
        # Looks for strings with high entropy and secret-like patterns
        secret_patterns = [
            # Assignment patterns
            r"['\"]([a-zA-Z0-9_\-]{20,60})['\"]",
            # Token-like patterns
            r"\b([a-fA-F0-9]{32,64})\b",
            # Base64-like patterns
            r"\b([A-Za-z0-9+/]{40,}={0,2})\b",
        ]

        seen_strings: Set[str] = set()

        for pattern in secret_patterns:
            for match in re.finditer(pattern, content):
                string_value = match.group(1)

                # Skip if we've seen this string
                if string_value in seen_strings:
                    continue
                seen_strings.add(string_value)

                # Check entropy
                entropy = self.pattern_db.calculate_entropy(string_value)

                # High entropy indicates potential secret
                if entropy >= 3.5 and len(string_value) >= 20:
                    # Calculate line and column
                    line_num = content[: match.start()].count("\n") + 1
                    line_start = content.rfind("\n", 0, match.start()) + 1
                    col_start = match.start() - line_start
                    col_end = match.end() - line_start

                    # Get context lines
                    context_lines = self._get_context_lines(lines, line_num)

                    finding = SecurityFinding(
                        pattern_id="ENTROPY_HIGH",
                        category=PatternCategory.SECRETS,
                        severity=SeverityLevel.MEDIUM,
                        confidence=ConfidenceLevel.LOW,
                        file_path=file_path,
                        line_number=line_num,
                        column_start=col_start,
                        column_end=col_end,
                        matched_text=match.group(0),
                        message=f"High entropy string detected (entropy: {entropy:.2f}). May be a hardcoded secret or token.",
                        remediation="Verify if this is a secret. If so, move it to environment variables or a secrets manager.",
                        context_lines=context_lines,
                    )
                    findings.append(finding)

        return findings

    def _is_false_positive(self, matched_text: str, pattern) -> bool:
        """Check if a match is likely a false positive."""
        # Skip environment variable access patterns
        if "os.environ" in matched_text or "os.getenv" in matched_text:
            return True

        # Skip placeholder values (only for secrets, not for injection patterns)
        if hasattr(pattern, "category") and pattern.category == PatternCategory.SECRETS:
            placeholders = [
                "your-api-key",
                "your_api_key",
                "example",
                "placeholder",
                "test-value",
                "test_value",
                "dummy",
                "sample",
                "changeme",
                "password123",
                "admin",
                "root",
                "user",
                "default",
            ]
            lower_text = matched_text.lower()
            for placeholder in placeholders:
                if placeholder in lower_text:
                    return True

        # Skip config/setting references
        if matched_text.startswith("settings.") or matched_text.startswith("config."):
            return True

        # Skip None assignments
        if "None" in matched_text or "null" in matched_text.lower():
            return True

        return False

    def _get_context_lines(
        self, lines: List[str], line_num: int, context: int = 2
    ) -> List[str]:
        """Get context lines around a specific line number.

        Args:
            lines: All lines in the file
            line_num: Line number (1-indexed)
            context: Number of lines before and after

        Returns:
            List of context lines
        """
        start = max(0, line_num - context - 1)
        end = min(len(lines), line_num + context)
        return lines[start:end]

    def scan_project(
        self,
        project_path: str,
        include_extensions: Optional[Set[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> SecurityReport:
        """Scan an entire project for security issues.

        Args:
            project_path: Root path of the project
            include_extensions: Optional set of extensions to scan
            exclude_patterns: Optional list of patterns to exclude

        Returns:
            Security report with all findings
        """
        start_time = datetime.now()
        all_findings = []
        scanned_files = 0

        root = Path(project_path).resolve()

        # Use provided extensions or default
        extensions = include_extensions or self.CODE_EXTENSIONS

        # Compile exclude patterns
        exclude_regex = None
        if exclude_patterns:
            exclude_regex = [re.compile(pattern) for pattern in exclude_patterns]

        for file_path in root.rglob("*"):
            # Skip directories
            if not file_path.is_file():
                continue

            # Check for skip directories
            if any(part in self.SKIP_DIRECTORIES for part in file_path.parts):
                continue

            # Check extension
            if file_path.suffix.lower() not in extensions:
                continue

            # Check exclude patterns
            if exclude_regex:
                path_str = str(file_path.relative_to(root))
                if any(pattern.search(path_str) for pattern in exclude_regex):
                    continue

            # Scan the file
            try:
                findings = self.scan_file(str(file_path))
                all_findings.extend(findings)
                scanned_files += 1
            except Exception:
                # Continue scanning other files on error
                continue

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        return SecurityReport(
            target_path=str(root),
            scan_timestamp=start_time,
            findings=all_findings,
            scanned_files=scanned_files,
            scan_duration_seconds=duration,
        )

    def _detect_language(self, file_path: Path) -> Optional[str]:
        """Detect programming language from file extension.

        Args:
            file_path: Path to the file

        Returns:
            Language name or None
        """
        ext = file_path.suffix.lower()

        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".cs": "csharp",
            ".fs": "fsharp",
            ".ex": "elixir",
            ".exs": "elixir",
            ".erl": "erlang",
            ".clj": "clojure",
            ".hs": "haskell",
            ".lua": "lua",
            ".pl": "perl",
            ".sh": "shell",
            ".bash": "shell",
            ".zsh": "shell",
            ".ps1": "powershell",
            ".sql": "sql",
            ".html": "html",
            ".htm": "html",
            ".css": "css",
            ".scss": "scss",
            ".sass": "sass",
            ".less": "less",
            ".xml": "xml",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".ini": "ini",
        }

        # Special handling for files without extensions
        filename = file_path.name.lower()
        if filename in ("dockerfile", "makefile", "cmakelists.txt"):
            if filename == "dockerfile":
                return "dockerfile"
            elif filename == "makefile":
                return "makefile"
            elif filename == "cmakelists.txt":
                return "cmake"

        return language_map.get(ext)

    def get_statistics(self) -> dict:
        """Get scanner statistics."""
        return {
            "total_patterns": self.pattern_db.get_pattern_count(),
            "patterns_by_category": self.pattern_db.get_category_counts(),
        }
