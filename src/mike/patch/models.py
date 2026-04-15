"""Patch Apply Mode data models for Mike v2.

This module defines data classes for representing patches and their application status.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any


class PatchStatus(str, Enum):
    """Status of a patch application."""

    PENDING = "pending"
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class FileChange:
    """Represents a single file change in a patch.

    Attributes:
        file_path: Path to the file being changed
        old_content: Original content (None for new files)
        new_content: New content (None for deletions)
        change_type: Type of change - 'modify', 'create', 'delete', 'rename'
        original_path: For renames, the original file path
    """

    file_path: str
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    change_type: str = "modify"  # modify, create, delete, rename
    original_path: Optional[str] = None


@dataclass
class Patch:
    """Represents a code patch with multiple file changes.

    Attributes:
        id: Unique identifier for the patch
        diff_content: Unified diff format content
        files_affected: List of file paths affected
        changes: List of detailed file changes
        metadata: Additional metadata (title, description, author, etc.)
        created_at: Timestamp when patch was created
        source: Source of the patch (e.g., 'refactor_agent', 'manual')
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    diff_content: str = ""
    files_affected: List[str] = field(default_factory=list)
    changes: List[FileChange] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = "unknown"

    def __post_init__(self):
        """Ensure files_affected is populated from changes."""
        if not self.files_affected and self.changes:
            self.files_affected = [change.file_path for change in self.changes]


@dataclass
class PatchApplication:
    """Tracks the application status of a patch.

    Attributes:
        patch_id: Reference to the applied patch
        status: Current status of the application
        backup_paths: Mapping of file paths to backup file paths
        errors: List of errors encountered during application
        applied_at: Timestamp when patch was applied
        rolled_back_at: Timestamp when patch was rolled back (if applicable)
        applied_by: User/system that applied the patch
        validation_result: Result of validation before application
    """

    patch_id: str
    status: PatchStatus = PatchStatus.PENDING
    backup_paths: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    applied_at: Optional[str] = None
    rolled_back_at: Optional[str] = None
    applied_by: str = "system"
    validation_result: Optional[Dict[str, Any]] = None

    def is_active(self) -> bool:
        """Check if the patch is currently applied (not rolled back or failed)."""
        return self.status == PatchStatus.APPLIED

    def can_rollback(self) -> bool:
        """Check if the patch can be rolled back."""
        return self.status == PatchStatus.APPLIED and bool(self.backup_paths)


@dataclass
class ValidationResult:
    """Result of patch validation.

    Attributes:
        valid: Whether the patch can be applied
        conflicts: List of conflict descriptions
        warnings: List of warnings
        affected_files: List of files that would be modified
        missing_files: List of files that don't exist but would be modified
        checksums: Mapping of file paths to their current checksums
    """

    valid: bool = True
    conflicts: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    affected_files: List[str] = field(default_factory=list)
    missing_files: List[str] = field(default_factory=list)
    checksums: Dict[str, str] = field(default_factory=dict)

    @property
    def has_issues(self) -> bool:
        """Check if there are any conflicts or warnings."""
        return bool(self.conflicts) or bool(self.warnings)


@dataclass
class PreviewResult:
    """Result of patch preview (dry-run).

    Attributes:
        can_apply: Whether the patch can be applied
        changes_summary: Human-readable summary of changes
        file_changes: Detailed list of file operations
        backup_size: Estimated size of backup (bytes)
        warnings: List of warnings
    """

    can_apply: bool = True
    changes_summary: str = ""
    file_changes: List[Dict[str, Any]] = field(default_factory=list)
    backup_size: int = 0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert preview result to dictionary."""
        return {
            "can_apply": self.can_apply,
            "changes_summary": self.changes_summary,
            "file_changes": self.file_changes,
            "backup_size": self.backup_size,
            "warnings": self.warnings,
        }


class PatchError(Exception):
    """Base exception for patch-related errors."""

    pass


class PatchValidationError(PatchError):
    """Raised when patch validation fails."""

    pass


class PatchApplicationError(PatchError):
    """Raised when patch application fails."""

    pass


class PatchRollbackError(PatchError):
    """Raised when patch rollback fails."""

    pass
