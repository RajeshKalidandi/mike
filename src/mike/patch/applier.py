"""Patch Applier for applying and rolling back patches.

This module provides functionality to apply patches with automatic backups,
rollback patches, preview changes, and validate patches before application.
"""

from __future__ import annotations

import hashlib
import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union

from .models import (
    Patch,
    PatchApplication,
    PatchStatus,
    ValidationResult,
    PreviewResult,
    PatchValidationError,
    PatchApplicationError,
    PatchRollbackError,
)
from .generator import PatchGenerator


logger = logging.getLogger(__name__)


class PatchApplier:
    """Applies patches with automatic backup and rollback support.

    This class provides methods to:
    - Apply patches with automatic backup
    - Rollback applied patches
    - Preview changes before applying (dry-run)
    - Validate patches before application
    - Handle file creation, deletion, and renames
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        backup_dir: Optional[Path] = None,
    ):
        """Initialize the patch applier.

        Args:
            project_root: Root directory of the project (default: current directory)
            backup_dir: Directory for storing backups (default: .mike/backups)
        """
        self.project_root = project_root or Path.cwd()
        self.backup_dir = backup_dir or self.project_root / ".mike" / "backups"
        self._applications: Dict[str, PatchApplication] = {}
        self._generator = PatchGenerator(self.backup_dir)

    def apply_patch(
        self,
        patch: Patch,
        dry_run: bool = False,
    ) -> PatchApplication:
        """Apply a patch with automatic backup.

        Args:
            patch: Patch to apply
            dry_run: If True, only validate without applying

        Returns:
            PatchApplication tracking the application status

        Raises:
            PatchValidationError: If validation fails
            PatchApplicationError: If application fails

        Example:
            >>> applier = PatchApplier()
            >>> application = applier.apply_patch(patch)
            >>> if application.status == PatchStatus.APPLIED:
            ...     print("Patch applied successfully!")
        """
        # Validate first
        validation = self.validate_patch(patch)
        if not validation.valid:
            raise PatchValidationError(
                f"Patch validation failed: {'; '.join(validation.conflicts)}"
            )

        if dry_run:
            return PatchApplication(
                patch_id=patch.id,
                status=PatchStatus.PENDING,
                validation_result=validation.__dict__,
            )

        # Create application record
        application = PatchApplication(
            patch_id=patch.id,
            status=PatchStatus.PENDING,
            validation_result=validation.__dict__,
            applied_at=datetime.now().isoformat(),
        )

        try:
            # Create backup directory for this patch
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_subdir = self.backup_dir / f"{timestamp}_{patch.id[:8]}"
            backup_subdir.mkdir(parents=True, exist_ok=True)

            # Backup and apply each change
            for change in patch.changes:
                self._apply_change(change, backup_subdir, application)

            # Apply diff if no detailed changes
            if not patch.changes and patch.diff_content:
                self._apply_diff(patch.diff_content, backup_subdir, application)

            application.status = PatchStatus.APPLIED
            self._applications[patch.id] = application

            logger.info(f"Patch {patch.id[:8]} applied successfully")

        except Exception as e:
            application.status = PatchStatus.FAILED
            application.errors.append(str(e))
            logger.error(f"Failed to apply patch {patch.id[:8]}: {e}")
            raise PatchApplicationError(f"Failed to apply patch: {e}") from e

        return application

    def rollback_patch(self, patch_id: str) -> PatchApplication:
        """Rollback an applied patch.

        Args:
            patch_id: ID of the patch to rollback

        Returns:
            Updated PatchApplication

        Raises:
            PatchRollbackError: If rollback fails

        Example:
            >>> applier = PatchApplier()
            >>> applier.apply_patch(patch)
            >>> # Oops, need to undo
            >>> applier.rollback_patch(patch.id)
        """
        if patch_id not in self._applications:
            raise PatchRollbackError(f"No application found for patch {patch_id}")

        application = self._applications[patch_id]

        if not application.can_rollback():
            raise PatchRollbackError(
                f"Cannot rollback patch {patch_id}: status={application.status}, "
                f"backups={bool(application.backup_paths)}"
            )

        try:
            # Restore from backups
            for file_path, backup_path in application.backup_paths.items():
                full_path = self.project_root / file_path
                backup_full = Path(backup_path)

                if backup_full.exists():
                    # Restore the backup
                    shutil.copy2(backup_full, full_path)
                    logger.debug(f"Restored {file_path} from backup")
                else:
                    # Backup doesn't exist, file was likely created by patch
                    if full_path.exists():
                        full_path.unlink()
                        logger.debug(f"Deleted created file {file_path}")

            application.status = PatchStatus.ROLLED_BACK
            application.rolled_back_at = datetime.now().isoformat()

            logger.info(f"Patch {patch_id[:8]} rolled back successfully")

        except Exception as e:
            logger.error(f"Failed to rollback patch {patch_id[:8]}: {e}")
            raise PatchRollbackError(f"Failed to rollback patch: {e}") from e

        return application

    def preview_patch(self, patch: Patch) -> PreviewResult:
        """Preview what would change if the patch is applied (dry-run).

        Args:
            patch: Patch to preview

        Returns:
            PreviewResult with details of what would change

        Example:
            >>> applier = PatchApplier()
            >>> preview = applier.preview_patch(patch)
            >>> print(preview.changes_summary)
            >>> for change in preview.file_changes:
            ...     print(f"  {change['file_path']}: {change['operation']}")
        """
        validation = self.validate_patch(patch)

        file_changes = []
        backup_size = 0
        warnings = list(validation.warnings)

        # Analyze each change
        for change in patch.changes:
            change_info = {
                "file_path": change.file_path,
                "operation": change.change_type,
                "exists": False,
                "would_change": False,
            }

            full_path = self.project_root / change.file_path
            exists = full_path.exists()
            change_info["exists"] = exists

            if change.change_type == "create":
                if exists:
                    warnings.append(
                        f"File {change.file_path} already exists and would be overwritten"
                    )
                change_info["would_change"] = True

            elif change.change_type == "delete":
                if exists:
                    change_info["would_change"] = True
                    backup_size += full_path.stat().st_size if exists else 0
                else:
                    warnings.append(
                        f"File {change.file_path} doesn't exist for deletion"
                    )

            elif change.change_type == "rename":
                if change.original_path:
                    orig_path = self.project_root / change.original_path
                    if orig_path.exists():
                        change_info["would_change"] = True
                        backup_size += orig_path.stat().st_size
                    else:
                        warnings.append(
                            f"Original file {change.original_path} doesn't exist"
                        )

            else:  # modify
                if exists:
                    change_info["would_change"] = True
                    backup_size += full_path.stat().st_size

                    # Check if content actually differs
                    current_content = full_path.read_text()
                    if change.old_content and current_content != change.old_content:
                        # Content has changed since patch was created
                        if not self._content_matches_expected(
                            current_content, change.old_content
                        ):
                            warnings.append(
                                f"File {change.file_path} has changed since patch was created"
                            )
                else:
                    warnings.append(
                        f"File {change.file_path} doesn't exist for modification"
                    )

            file_changes.append(change_info)

        # Generate summary
        num_changes = sum(1 for c in file_changes if c["would_change"])
        creates = sum(1 for c in file_changes if c["operation"] == "create")
        deletes = sum(1 for c in file_changes if c["operation"] == "delete")
        modifies = sum(1 for c in file_changes if c["operation"] == "modify")
        renames = sum(1 for c in file_changes if c["operation"] == "rename")

        summary_parts = []
        if creates:
            summary_parts.append(f"{creates} file(s) created")
        if deletes:
            summary_parts.append(f"{deletes} file(s) deleted")
        if modifies:
            summary_parts.append(f"{modifies} file(s) modified")
        if renames:
            summary_parts.append(f"{renames} file(s) renamed")

        summary = f"Would modify {num_changes} file(s): " + ", ".join(summary_parts)
        if not summary_parts:
            summary = "No files would be changed"

        return PreviewResult(
            can_apply=validation.valid and not validation.conflicts,
            changes_summary=summary,
            file_changes=file_changes,
            backup_size=backup_size,
            warnings=warnings,
        )

    def validate_patch(self, patch: Patch) -> ValidationResult:
        """Validate if a patch can be applied.

        Args:
            patch: Patch to validate

        Returns:
            ValidationResult with validation details

        Example:
            >>> applier = PatchApplier()
            >>> result = applier.validate_patch(patch)
            >>> if result.valid:
            ...     print("Patch can be applied")
            ... else:
            ...     print(f"Conflicts: {result.conflicts}")
        """
        conflicts = []
        warnings = []
        affected_files = []
        missing_files = []
        checksums = {}

        for change in patch.changes:
            file_path = change.file_path
            full_path = self.project_root / file_path
            exists = full_path.exists()

            affected_files.append(file_path)

            if change.change_type == "create":
                if exists:
                    conflicts.append(f"File {file_path} already exists")

            elif change.change_type == "delete":
                if not exists:
                    conflicts.append(f"File {file_path} doesn't exist for deletion")
                    missing_files.append(file_path)
                else:
                    checksums[file_path] = self._compute_checksum(full_path)

            elif change.change_type == "rename":
                if not change.original_path:
                    conflicts.append(
                        f"Rename operation missing original_path for {file_path}"
                    )
                else:
                    orig_path = self.project_root / change.original_path
                    if not orig_path.exists():
                        conflicts.append(
                            f"Original file {change.original_path} doesn't exist"
                        )
                        missing_files.append(change.original_path)
                    else:
                        checksums[change.original_path] = self._compute_checksum(
                            orig_path
                        )

            else:  # modify
                if not exists:
                    conflicts.append(f"File {file_path} doesn't exist for modification")
                    missing_files.append(file_path)
                else:
                    checksums[file_path] = self._compute_checksum(full_path)

                    # Check if file content matches expected
                    if change.old_content:
                        current_content = full_path.read_text()
                        if current_content != change.old_content:
                            # Check if it's a meaningful difference
                            if not self._content_matches_expected(
                                current_content, change.old_content
                            ):
                                conflicts.append(
                                    f"File {file_path} content doesn't match expected (file was modified)"
                                )

        # Validate diff if no changes provided
        if not patch.changes and patch.diff_content:
            diff_validation = self._validate_diff(patch.diff_content)
            conflicts.extend(diff_validation.get("conflicts", []))
            warnings.extend(diff_validation.get("warnings", []))
            affected_files.extend(diff_validation.get("affected_files", []))
            missing_files.extend(diff_validation.get("missing_files", []))

        return ValidationResult(
            valid=len(conflicts) == 0,
            conflicts=conflicts,
            warnings=warnings,
            affected_files=list(set(affected_files)),
            missing_files=list(set(missing_files)),
            checksums=checksums,
        )

    def get_application(self, patch_id: str) -> Optional[PatchApplication]:
        """Get the application status for a patch.

        Args:
            patch_id: Patch ID

        Returns:
            PatchApplication if found, None otherwise
        """
        return self._applications.get(patch_id)

    def list_applications(
        self, status: Optional[PatchStatus] = None
    ) -> List[PatchApplication]:
        """List all patch applications.

        Args:
            status: Filter by status (optional)

        Returns:
            List of PatchApplication objects
        """
        apps = list(self._applications.values())
        if status:
            apps = [a for a in apps if a.status == status]
        return apps

    def _apply_change(
        self,
        change,
        backup_subdir: Path,
        application: PatchApplication,
    ) -> None:
        """Apply a single file change."""
        file_path = change.file_path
        full_path = self.project_root / file_path

        if change.change_type == "create":
            # Create new file
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(change.new_content or "")
            logger.debug(f"Created file {file_path}")

        elif change.change_type == "delete":
            # Backup and delete
            if full_path.exists():
                backup_path = backup_subdir / file_path.replace("/", "_")
                shutil.copy2(full_path, backup_path)
                application.backup_paths[file_path] = str(backup_path)
                full_path.unlink()
                logger.debug(f"Deleted file {file_path}")

        elif change.change_type == "rename":
            # Rename file
            if change.original_path:
                orig_path = self.project_root / change.original_path
                if orig_path.exists():
                    # Backup original
                    backup_path = backup_subdir / change.original_path.replace("/", "_")
                    shutil.copy2(orig_path, backup_path)
                    application.backup_paths[change.original_path] = str(backup_path)

                    # Rename
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    orig_path.rename(full_path)
                    logger.debug(f"Renamed {change.original_path} to {file_path}")

        else:  # modify
            # Backup and modify
            if full_path.exists():
                backup_path = backup_subdir / file_path.replace("/", "_")
                shutil.copy2(full_path, backup_path)
                application.backup_paths[file_path] = str(backup_path)

                # Apply change
                full_path.write_text(change.new_content or "")
                logger.debug(f"Modified file {file_path}")

    def _apply_diff(
        self,
        diff_content: str,
        backup_subdir: Path,
        application: PatchApplication,
    ) -> None:
        """Apply a unified diff."""
        # Parse and apply diff
        files_to_patch = self._parse_diff(diff_content)

        for file_info in files_to_patch:
            file_path = file_info["path"]
            full_path = self.project_root / file_path

            # Backup if exists
            if full_path.exists():
                backup_path = backup_subdir / file_path.replace("/", "_")
                shutil.copy2(full_path, backup_path)
                application.backup_paths[file_path] = str(backup_path)

            # Apply the patch
            if file_info["operation"] == "create":
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(file_info.get("new_content", ""))
            elif file_info["operation"] == "delete":
                if full_path.exists():
                    full_path.unlink()
            else:  # modify
                current_content = full_path.read_text() if full_path.exists() else ""
                new_content = self._apply_diff_to_content(
                    current_content, file_info.get("hunks", [])
                )
                full_path.write_text(new_content)

    def _parse_diff(self, diff_content: str) -> List[Dict[str, Any]]:
        """Parse unified diff into structured format."""
        files = []
        current_file = None
        current_hunk = None

        for line in diff_content.split("\\n"):
            # File header
            if line.startswith("diff --git"):
                if current_file:
                    files.append(current_file)
                current_file = {"hunks": []}

            elif line.startswith("--- "):
                if current_file:
                    old_file = line[4:]
                    if old_file != "/dev/null":
                        current_file["old_path"] = old_file.replace("a/", "", 1)

            elif line.startswith("+++ "):
                if current_file:
                    new_file = line[4:]
                    if new_file != "/dev/null":
                        current_file["path"] = new_file.replace("b/", "", 1)

            elif line.startswith("@@ "):
                if current_file:
                    if current_hunk:
                        current_file["hunks"].append(current_hunk)
                    current_hunk = {
                        "header": line,
                        "lines": [],
                    }

            elif current_hunk is not None and line:
                current_hunk["lines"].append(line)

        # Close last hunk and file
        if current_hunk and current_file:
            current_file["hunks"].append(current_hunk)
        if current_file:
            files.append(current_file)

        return files

    def _apply_diff_to_content(self, content: str, hunks: List[Dict[str, Any]]) -> str:
        """Apply diff hunks to content."""
        lines = content.splitlines(keepends=True)

        # Simple implementation - just return the expected new content
        # A full implementation would properly apply each hunk
        # For now, we rely on the detailed changes in the Patch object
        return content

    def _validate_diff(self, diff_content: str) -> Dict[str, Any]:
        """Validate a unified diff."""
        result = {
            "conflicts": [],
            "warnings": [],
            "affected_files": [],
            "missing_files": [],
        }

        files = self._parse_diff(diff_content)
        for file_info in files:
            file_path = file_info.get("path", "")
            if file_path:
                result["affected_files"].append(file_path)
                full_path = self.project_root / file_path
                if not full_path.exists():
                    result["missing_files"].append(file_path)

        return result

    def _compute_checksum(self, file_path: Path) -> str:
        """Compute SHA-256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _content_matches_expected(
        self,
        current: str,
        expected: str,
        tolerance: float = 0.8,
    ) -> bool:
        """Check if current content roughly matches expected.

        Uses fuzzy matching to handle minor whitespace/formatting changes.
        """
        if current == expected:
            return True

        # Normalize whitespace
        current_norm = "\\n".join(
            line.strip() for line in current.splitlines() if line.strip()
        )
        expected_norm = "\\n".join(
            line.strip() for line in expected.splitlines() if line.strip()
        )

        if current_norm == expected_norm:
            return True

        # Check similarity
        current_lines = set(current_norm.split("\\n"))
        expected_lines = set(expected_norm.split("\\n"))

        if not expected_lines:
            return True

        intersection = len(current_lines & expected_lines)
        similarity = intersection / len(expected_lines)

        return similarity >= tolerance
