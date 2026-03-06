"""Patch Apply Mode for Mike v2.

This module provides functionality to create, apply, preview, and rollback
code patches generated from refactor suggestions or manual edits.

Example:
    from mike.patch import PatchGenerator, PatchApplier, Patch, PatchStatus

    # Generate a patch from a refactor suggestion
    generator = PatchGenerator()
    patch = generator.from_refactor_suggestion(suggestion)

    # Preview the patch
    applier = PatchApplier(project_root="/path/to/project")
    preview = applier.preview_patch(patch)
    print(preview.changes_summary)

    # Apply the patch with automatic backup
    application = applier.apply_patch(patch)

    # If needed, rollback
    if application.status == PatchStatus.APPLIED:
        applier.rollback_patch(patch.id)
"""

from .models import (
    Patch,
    PatchApplication,
    PatchStatus,
    FileChange,
    ValidationResult,
    PreviewResult,
    PatchError,
    PatchValidationError,
    PatchApplicationError,
    PatchRollbackError,
)
from .generator import PatchGenerator
from .applier import PatchApplier

__all__ = [
    # Models
    "Patch",
    "PatchApplication",
    "PatchStatus",
    "FileChange",
    "ValidationResult",
    "PreviewResult",
    # Exceptions
    "PatchError",
    "PatchValidationError",
    "PatchApplicationError",
    "PatchRollbackError",
    # Classes
    "PatchGenerator",
    "PatchApplier",
]
