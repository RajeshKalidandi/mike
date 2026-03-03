"""Patch Generator for creating unified diffs from refactor suggestions.

This module provides functionality to generate patches from various sources
including refactor suggestions, code changes, and manual edits.
"""

from __future__ import annotations

import difflib
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from .models import Patch, FileChange, PatchStatus


class PatchGenerator:
    """Generates patches from various sources.

    This class provides methods to create patches from:
    - Refactor suggestions
    - File content changes
    - Manual edits
    - Diff strings
    """

    def __init__(self, backup_dir: Optional[Path] = None):
        """Initialize the patch generator.

        Args:
            backup_dir: Directory for storing backups (default: .mike/backups)
        """
        self.backup_dir = backup_dir or Path(".mike/backups")

    def from_refactor_suggestion(
        self,
        suggestion: Dict[str, Any],
        file_content: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> Patch:
        """Create a patch from a refactor suggestion.

        Args:
            suggestion: Refactor suggestion dict with keys like:
                       - file_path: Path to the file
                       - line_start: Starting line number
                       - line_end: Ending line number
                       - original_code: Code to replace
                       - refactored_code: New code
                       - description: Description of the change
                       - suggestion: Human-readable suggestion text
            file_content: Full file content (if available)
            file_path: Override file path from suggestion

        Returns:
            Patch object representing the refactoring change

        Example:
            suggestion = {
                "file_path": "src/main.py",
                "line_start": 10,
                "line_end": 20,
                "original_code": "def old_func():\\n    pass",
                "refactored_code": "def new_func():\\n    return 42",
                "description": "Rename and improve function",
                "suggestion": "Use more descriptive name",
            }
            patch = generator.from_refactor_suggestion(suggestion)
        """
        # Extract file path
        target_file = file_path or suggestion.get("file_path", "")
        if not target_file:
            raise ValueError("file_path is required in suggestion or as argument")

        # Extract code sections
        original_code = suggestion.get("original_code", "")
        refactored_code = suggestion.get("refactored_code", "")

        # Create file change
        change = FileChange(
            file_path=target_file,
            old_content=original_code if file_content else None,
            new_content=refactored_code,
            change_type="modify",
        )

        # Generate diff
        diff_content = self.generate_diff(
            original_code,
            refactored_code,
            source_file=target_file,
            target_file=target_file,
        )

        # Create patch
        patch = Patch(
            diff_content=diff_content,
            files_affected=[target_file],
            changes=[change],
            metadata={
                "title": suggestion.get("description", "Refactoring"),
                "description": suggestion.get("suggestion", ""),
                "line_start": suggestion.get("line_start"),
                "line_end": suggestion.get("line_end"),
                "smell_type": suggestion.get("smell_type", "unknown"),
                "severity": suggestion.get("severity", "medium"),
            },
            source="refactor_agent",
        )

        return patch

    def from_file_changes(
        self,
        changes: List[Dict[str, Any]],
        title: str = "File Changes",
        description: str = "",
    ) -> Patch:
        """Create a patch from a list of file changes.

        Args:
            changes: List of change dictionaries with keys:
                    - file_path: Path to the file
                    - old_content: Original content (None for new files)
                    - new_content: New content (None for deletions)
                    - change_type: 'modify', 'create', 'delete', 'rename'
                    - original_path: For renames, the original path
            title: Title for the patch
            description: Description of the changes

        Returns:
            Patch object with unified diff
        """
        file_changes = []
        files_affected = []
        diff_parts = []

        for change_dict in changes:
            file_path = change_dict["file_path"]
            files_affected.append(file_path)

            # Create FileChange object
            file_change = FileChange(
                file_path=file_path,
                old_content=change_dict.get("old_content"),
                new_content=change_dict.get("new_content"),
                change_type=change_dict.get("change_type", "modify"),
                original_path=change_dict.get("original_path"),
            )
            file_changes.append(file_change)

            # Generate diff for this file
            old_content = change_dict.get("old_content") or ""
            new_content = change_dict.get("new_content") or ""
            change_type = change_dict.get("change_type", "modify")

            if change_type == "create":
                # New file diff
                diff_part = self._generate_new_file_diff(file_path, new_content)
            elif change_type == "delete":
                # Deleted file diff
                diff_part = self._generate_deleted_file_diff(file_path, old_content)
            elif change_type == "rename":
                # Renamed file diff
                original_path = change_dict.get("original_path", file_path)
                diff_part = self._generate_rename_diff(
                    original_path, file_path, old_content, new_content
                )
            else:
                # Modified file diff
                diff_part = self.generate_diff(
                    old_content,
                    new_content,
                    source_file=file_path,
                    target_file=file_path,
                )

            diff_parts.append(diff_part)

        # Combine all diffs
        full_diff = "\\n".join(diff_parts)

        return Patch(
            diff_content=full_diff,
            files_affected=files_affected,
            changes=file_changes,
            metadata={
                "title": title,
                "description": description,
            },
            source="manual",
        )

    def from_diff_string(
        self,
        diff_content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Patch:
        """Create a patch from an existing diff string.

        Args:
            diff_content: Unified diff format string
            metadata: Optional metadata dictionary

        Returns:
            Patch object
        """
        # Parse diff to extract affected files
        files_affected = self._parse_diff_files(diff_content)

        return Patch(
            diff_content=diff_content,
            files_affected=files_affected,
            changes=[],  # Would need full parsing to populate
            metadata=metadata or {},
            source="imported",
        )

    def generate_diff(
        self,
        original: str,
        modified: str,
        source_file: str = "a/file",
        target_file: str = "b/file",
        context_lines: int = 3,
    ) -> str:
        """Generate a unified diff between two strings.

        Args:
            original: Original content
            modified: Modified content
            source_file: Label for original file (for diff header)
            target_file: Label for modified file (for diff header)
            context_lines: Number of context lines in diff

        Returns:
            Unified diff string

        Example:
            >>> generator = PatchGenerator()
            >>> diff = generator.generate_diff(
            ...     "def foo():\\n    pass",
            ...     "def foo():\\n    return 42",
            ...     "a/main.py",
            ...     "b/main.py"
            ... )
        """
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)

        # Ensure lines end with newline for proper diff
        if original_lines and not original_lines[-1].endswith("\\n"):
            original_lines[-1] += "\\n"
        if modified_lines and not modified_lines[-1].endswith("\\n"):
            modified_lines[-1] += "\\n"

        # Generate unified diff
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=source_file,
            tofile=target_file,
            n=context_lines,
        )

        return "".join(diff)

    def create_multi_file_patch(
        self,
        file_changes: Dict[str, Dict[str, str]],
        title: str = "Multi-file Patch",
        description: str = "",
    ) -> Patch:
        """Create a patch affecting multiple files.

        Args:
            file_changes: Dictionary mapping file paths to change dicts:
                         {
                             "file_path": {
                                 "old_content": "...",
                                 "new_content": "...",
                                 "change_type": "modify"
                             }
                         }
            title: Title for the patch
            description: Description

        Returns:
            Patch object
        """
        changes = []
        for file_path, change_info in file_changes.items():
            changes.append(
                {
                    "file_path": file_path,
                    **change_info,
                }
            )

        return self.from_file_changes(changes, title, description)

    def _generate_new_file_diff(self, file_path: str, content: str) -> str:
        """Generate diff for a new file."""
        lines = content.splitlines(keepends=True)
        if lines and not lines[-1].endswith("\\n"):
            lines[-1] += "\\n"

        diff_lines = [
            f"diff --git a/{file_path} b/{file_path}",
            f"new file mode 100644",
            f"index 0000000..{self._hash_content(content)[:7]}",
            f"--- /dev/null",
            f"+++ b/{file_path}",
            f"@@ -0,0 +1,{len(lines)} @@",
        ]

        for line in lines:
            stripped = line.rstrip("\n")
            diff_lines.append(f"+{stripped}")

        return "\\n".join(diff_lines)

    def _generate_deleted_file_diff(self, file_path: str, content: str) -> str:
        """Generate diff for a deleted file."""
        lines = content.splitlines(keepends=True)
        if lines and not lines[-1].endswith("\\n"):
            lines[-1] += "\\n"

        diff_lines = [
            f"diff --git a/{file_path} b/{file_path}",
            f"deleted file mode 100644",
            f"index {self._hash_content(content)[:7]}..0000000",
            f"--- a/{file_path}",
            f"+++ /dev/null",
            f"@@ -1,{len(lines)} +0,0 @@",
        ]

        for line in lines:
            stripped = line.rstrip("\n")
            diff_lines.append(f"-{stripped}")

        return "\\n".join(diff_lines)

    def _generate_rename_diff(
        self,
        old_path: str,
        new_path: str,
        old_content: str,
        new_content: str,
    ) -> str:
        """Generate diff for a renamed file."""
        # For simplicity, treat as delete + create with similarity
        diff_lines = [
            f"diff --git a/{old_path} b/{new_path}",
            f"similarity index {self._calculate_similarity(old_content, new_content):.0f}%",
            f"rename from {old_path}",
            f"rename to {new_path}",
        ]

        # If content changed, add the diff
        if old_content != new_content:
            content_diff = self.generate_diff(
                old_content, new_content, old_path, new_path
            )
            diff_lines.append(content_diff)

        return "\\n".join(diff_lines)

    def _parse_diff_files(self, diff_content: str) -> List[str]:
        """Parse diff to extract affected file paths."""
        files = []
        for line in diff_content.split("\\n"):
            if line.startswith("+++ b/"):
                file_path = line[6:]
                if file_path != "/dev/null":
                    files.append(file_path)
            elif line.startswith("rename to "):
                files.append(line[10:])
        return files

    def _hash_content(self, content: str) -> str:
        """Generate hash of content for diff headers."""
        return hashlib.sha1(content.encode("utf-8")).hexdigest()

    def _calculate_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity percentage between two contents."""
        if content1 == content2:
            return 100.0

        # Simple similarity based on lines
        lines1 = set(content1.splitlines())
        lines2 = set(content2.splitlines())

        if not lines1 and not lines2:
            return 100.0

        intersection = len(lines1 & lines2)
        union = len(lines1 | lines2)

        return (intersection / union * 100) if union > 0 else 100.0
