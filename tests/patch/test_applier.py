"""Tests for the Patch Applier module.

This module tests all functionality of the patch system including:
- Patch generation from refactor suggestions
- Patch application with backup
- Patch preview (dry-run)
- Patch validation
- Patch rollback
"""

import pytest
from pathlib import Path
from datetime import datetime

from mike.patch import (
    Patch,
    PatchApplication,
    PatchStatus,
    FileChange,
    ValidationResult,
    PreviewResult,
    PatchGenerator,
    PatchApplier,
    PatchValidationError,
    PatchApplicationError,
    PatchRollbackError,
)


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with sample files."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create some test files
    src_dir = project_dir / "src"
    src_dir.mkdir()

    (src_dir / "main.py").write_text("""\
def main():
    print("Hello World")
    return 0

if __name__ == "__main__":
    main()
""")

    (src_dir / "utils.py").write_text("""\
def helper():
    return 42

def unused():
    pass
""")

    (project_dir / "README.md").write_text("# Test Project\\n")

    return project_dir


@pytest.fixture
def patch_generator():
    """Create a patch generator instance."""
    return PatchGenerator()


@pytest.fixture
def patch_applier(temp_project_dir):
    """Create a patch applier instance."""
    return PatchApplier(
        project_root=temp_project_dir, backup_dir=temp_project_dir / ".mike" / "backups"
    )


class TestPatchModels:
    """Test Patch data models."""

    def test_patch_creation(self):
        """Test creating a Patch instance."""
        change = FileChange(
            file_path="src/main.py",
            old_content="old",
            new_content="new",
            change_type="modify",
        )

        patch = Patch(
            diff_content="@@ -1 +1 @@\\n-old\\n+new",
            files_affected=["src/main.py"],
            changes=[change],
            metadata={"title": "Test Patch"},
            source="test",
        )

        assert patch.diff_content
        assert len(patch.files_affected) == 1
        assert patch.source == "test"
        assert patch.metadata["title"] == "Test Patch"

    def test_patch_auto_populates_files(self):
        """Test that Patch auto-populates files_affected from changes."""
        change = FileChange(file_path="src/test.py", change_type="modify")
        patch = Patch(changes=[change])

        assert "src/test.py" in patch.files_affected

    def test_patch_application_is_active(self):
        """Test PatchApplication.is_active()."""
        app = PatchApplication(patch_id="123", status=PatchStatus.APPLIED)
        assert app.is_active()

        app.status = PatchStatus.ROLLED_BACK
        assert not app.is_active()

        app.status = PatchStatus.FAILED
        assert not app.is_active()

    def test_patch_application_can_rollback(self):
        """Test PatchApplication.can_rollback()."""
        app = PatchApplication(
            patch_id="123",
            status=PatchStatus.APPLIED,
            backup_paths={"file1": "/backup/file1"},
        )
        assert app.can_rollback()

        app.status = PatchStatus.ROLLED_BACK
        assert not app.can_rollback()

        app.status = PatchStatus.APPLIED
        app.backup_paths = {}
        assert not app.can_rollback()


class TestPatchGenerator:
    """Test PatchGenerator functionality."""

    def test_from_refactor_suggestion(self, patch_generator):
        """Test creating patch from refactor suggestion."""
        suggestion = {
            "file_path": "src/main.py",
            "line_start": 1,
            "line_end": 3,
            "original_code": 'def main():\\n    print("Hello World")\\n    return 0',
            "refactored_code": 'def main():\\n    print("Hello Universe")\\n    return 0',
            "description": "Update greeting",
            "suggestion": "Use more universal greeting",
            "smell_type": "style",
            "severity": "low",
        }

        patch = patch_generator.from_refactor_suggestion(suggestion)

        assert patch is not None
        assert len(patch.changes) == 1
        assert patch.changes[0].file_path == "src/main.py"
        assert "Update greeting" in patch.metadata.get("title", "")
        assert patch.source == "refactor_agent"

    def test_from_refactor_suggestion_requires_file_path(self, patch_generator):
        """Test that file_path is required."""
        suggestion = {"original_code": "old", "refactored_code": "new"}

        with pytest.raises(ValueError, match="file_path is required"):
            patch_generator.from_refactor_suggestion(suggestion)

    def test_generate_diff(self, patch_generator):
        """Test generating unified diff."""
        original = "line1\nline2\nline3"
        modified = "line1\nmodified\nline3"

        diff = patch_generator.generate_diff(
            original, modified, source_file="a/test.py", target_file="b/test.py"
        )

        assert "--- a/test.py" in diff
        assert "+++ b/test.py" in diff
        assert "-line2" in diff
        assert "+modified" in diff

    def test_from_file_changes(self, patch_generator):
        """Test creating patch from file changes."""
        changes = [
            {
                "file_path": "src/new.py",
                "new_content": "# New file",
                "change_type": "create",
            },
            {
                "file_path": "src/old.py",
                "old_content": "# Old content",
                "change_type": "delete",
            },
        ]

        patch = patch_generator.from_file_changes(changes, title="Multi-change patch")

        assert len(patch.changes) == 2
        assert patch.metadata["title"] == "Multi-change patch"
        assert "src/new.py" in patch.files_affected
        assert "src/old.py" in patch.files_affected

    def test_from_diff_string(self, patch_generator):
        """Test creating patch from diff string."""
        diff = """diff --git a/file.py b/file.py
--- a/file.py
+++ b/file.py
@@ -1,2 +1,2 @@
-old
+new
"""

        patch = patch_generator.from_diff_string(
            diff, metadata={"title": "Imported patch"}
        )

        assert patch.diff_content == diff
        assert patch.metadata["title"] == "Imported patch"

    def test_create_multi_file_patch(self, patch_generator):
        """Test creating multi-file patch."""
        file_changes = {
            "file1.py": {
                "old_content": "old1",
                "new_content": "new1",
                "change_type": "modify",
            },
            "file2.py": {
                "old_content": "old2",
                "new_content": "new2",
                "change_type": "modify",
            },
        }

        patch = patch_generator.create_multi_file_patch(
            file_changes, title="Multi-file"
        )

        assert len(patch.changes) == 2
        assert "file1.py" in patch.files_affected
        assert "file2.py" in patch.files_affected


class TestPatchValidation:
    """Test patch validation functionality."""

    def test_validate_patch_success(self, patch_applier, temp_project_dir):
        """Test successful patch validation."""
        change = FileChange(
            file_path="src/main.py",
            old_content=(temp_project_dir / "src" / "main.py").read_text(),
            new_content="# Modified",
            change_type="modify",
        )

        patch = Patch(changes=[change])
        result = patch_applier.validate_patch(patch)

        assert result.valid
        assert len(result.conflicts) == 0
        assert "src/main.py" in result.affected_files

    def test_validate_patch_missing_file(self, patch_applier):
        """Test validation fails for missing file."""
        change = FileChange(
            file_path="nonexistent.py",
            old_content="old",
            new_content="new",
            change_type="modify",
        )

        patch = Patch(changes=[change])
        result = patch_applier.validate_patch(patch)

        assert not result.valid
        assert len(result.conflicts) > 0
        assert any("doesn't exist" in c for c in result.conflicts)

    def test_validate_patch_create_existing(self, patch_applier, temp_project_dir):
        """Test validation fails for creating existing file."""
        change = FileChange(
            file_path="src/main.py",  # This file exists
            new_content="# New",
            change_type="create",
        )

        patch = Patch(changes=[change])
        result = patch_applier.validate_patch(patch)

        assert not result.valid
        assert any("already exists" in c for c in result.conflicts)

    def test_validate_patch_content_mismatch(self, patch_applier, temp_project_dir):
        """Test validation detects content mismatch."""
        change = FileChange(
            file_path="src/main.py",
            old_content="# Wrong content",  # Doesn't match actual content
            new_content="# New",
            change_type="modify",
        )

        patch = Patch(changes=[change])
        result = patch_applier.validate_patch(patch)

        # Should have a conflict about content mismatch
        assert len(result.conflicts) > 0
        assert any("doesn't match" in c for c in result.conflicts)


class TestPatchPreview:
    """Test patch preview (dry-run) functionality."""

    def test_preview_patch_modify(self, patch_applier, temp_project_dir):
        """Test preview of file modification."""
        original_content = (temp_project_dir / "src" / "main.py").read_text()

        change = FileChange(
            file_path="src/main.py",
            old_content=original_content,
            new_content="# Modified content",
            change_type="modify",
        )

        patch = Patch(changes=[change])
        preview = patch_applier.preview_patch(patch)

        assert preview.can_apply
        assert len(preview.file_changes) == 1
        assert preview.file_changes[0]["file_path"] == "src/main.py"
        assert preview.file_changes[0]["operation"] == "modify"
        assert preview.file_changes[0]["would_change"]
        assert "1 file(s) modified" in preview.changes_summary

    def test_preview_patch_create(self, patch_applier, temp_project_dir):
        """Test preview of file creation."""
        change = FileChange(
            file_path="src/new_file.py", new_content="# New file", change_type="create"
        )

        patch = Patch(changes=[change])
        preview = patch_applier.preview_patch(patch)

        assert preview.can_apply
        assert "1 file(s) created" in preview.changes_summary

    def test_preview_patch_delete(self, patch_applier, temp_project_dir):
        """Test preview of file deletion."""
        change = FileChange(
            file_path="src/utils.py",
            old_content=(temp_project_dir / "src" / "utils.py").read_text(),
            change_type="delete",
        )

        patch = Patch(changes=[change])
        preview = patch_applier.preview_patch(patch)

        assert preview.can_apply
        assert "1 file(s) deleted" in preview.changes_summary
        assert preview.backup_size > 0

    def test_preview_patch_warnings(self, patch_applier, temp_project_dir):
        """Test that preview generates appropriate warnings."""
        # Try to create a file that already exists
        change = FileChange(
            file_path="src/main.py",  # Already exists
            new_content="# New",
            change_type="create",
        )

        patch = Patch(changes=[change])
        preview = patch_applier.preview_patch(patch)

        assert len(preview.warnings) > 0
        assert any("already exists" in w for w in preview.warnings)

    def test_preview_to_dict(self, patch_applier, temp_project_dir):
        """Test preview result conversion to dict."""
        original_content = (temp_project_dir / "src" / "main.py").read_text()

        change = FileChange(
            file_path="src/main.py",
            old_content=original_content,
            new_content="# Modified",
            change_type="modify",
        )

        patch = Patch(changes=[change])
        preview = patch_applier.preview_patch(patch)

        d = preview.to_dict()
        assert d["can_apply"] == True
        assert "changes_summary" in d
        assert "file_changes" in d
        assert "backup_size" in d
        assert "warnings" in d


class TestPatchApplication:
    """Test patch application functionality."""

    def test_apply_patch_modify(self, patch_applier, temp_project_dir):
        """Test applying a modification patch."""
        original_content = (temp_project_dir / "src" / "main.py").read_text()

        change = FileChange(
            file_path="src/main.py",
            old_content=original_content,
            new_content="# Modified by patch",
            change_type="modify",
        )

        patch = Patch(changes=[change])
        application = patch_applier.apply_patch(patch)

        assert application.status == PatchStatus.APPLIED
        assert application.patch_id == patch.id
        assert len(application.backup_paths) == 1
        assert "src/main.py" in application.backup_paths

        # Verify file was modified
        new_content = (temp_project_dir / "src" / "main.py").read_text()
        assert new_content == "# Modified by patch"

    def test_apply_patch_create(self, patch_applier, temp_project_dir):
        """Test applying a creation patch."""
        change = FileChange(
            file_path="src/brand_new.py",
            new_content="# Brand new file",
            change_type="create",
        )

        patch = Patch(changes=[change])
        application = patch_applier.apply_patch(patch)

        assert application.status == PatchStatus.APPLIED

        # Verify file was created
        new_file = temp_project_dir / "src" / "brand_new.py"
        assert new_file.exists()
        assert new_file.read_text() == "# Brand new file"

    def test_apply_patch_delete(self, patch_applier, temp_project_dir):
        """Test applying a deletion patch."""
        change = FileChange(
            file_path="src/utils.py",
            old_content=(temp_project_dir / "src" / "utils.py").read_text(),
            change_type="delete",
        )

        patch = Patch(changes=[change])
        application = patch_applier.apply_patch(patch)

        assert application.status == PatchStatus.APPLIED
        assert len(application.backup_paths) == 1

        # Verify file was deleted
        assert not (temp_project_dir / "src" / "utils.py").exists()

    def test_apply_patch_dry_run(self, patch_applier, temp_project_dir):
        """Test dry-run mode doesn't modify files."""
        original_content = (temp_project_dir / "src" / "main.py").read_text()

        change = FileChange(
            file_path="src/main.py",
            old_content=original_content,
            new_content="# Should not apply",
            change_type="modify",
        )

        patch = Patch(changes=[change])
        application = patch_applier.apply_patch(patch, dry_run=True)

        assert application.status == PatchStatus.PENDING

        # Verify file was NOT modified
        current_content = (temp_project_dir / "src" / "main.py").read_text()
        assert current_content == original_content

    def test_apply_patch_validation_fails(self, patch_applier):
        """Test that application fails when validation fails."""
        change = FileChange(
            file_path="nonexistent.py",
            old_content="old",
            new_content="new",
            change_type="modify",
        )

        patch = Patch(changes=[change])

        with pytest.raises(PatchValidationError):
            patch_applier.apply_patch(patch)


class TestPatchRollback:
    """Test patch rollback functionality."""

    def test_rollback_patch_modify(self, patch_applier, temp_project_dir):
        """Test rolling back a modification."""
        original_content = (temp_project_dir / "src" / "main.py").read_text()

        # Apply patch
        change = FileChange(
            file_path="src/main.py",
            old_content=original_content,
            new_content="# Modified",
            change_type="modify",
        )

        patch = Patch(changes=[change])
        application = patch_applier.apply_patch(patch)
        assert application.status == PatchStatus.APPLIED

        # Rollback
        rolled_back = patch_applier.rollback_patch(patch.id)
        assert rolled_back.status == PatchStatus.ROLLED_BACK

        # Verify file was restored
        current_content = (temp_project_dir / "src" / "main.py").read_text()
        assert current_content == original_content

    def test_rollback_patch_delete(self, patch_applier, temp_project_dir):
        """Test rolling back a deletion."""
        original_content = (temp_project_dir / "src" / "utils.py").read_text()

        # Apply delete patch
        change = FileChange(
            file_path="src/utils.py", old_content=original_content, change_type="delete"
        )

        patch = Patch(changes=[change])
        application = patch_applier.apply_patch(patch)
        assert application.status == PatchStatus.APPLIED
        assert not (temp_project_dir / "src" / "utils.py").exists()

        # Rollback
        rolled_back = patch_applier.rollback_patch(patch.id)
        assert rolled_back.status == PatchStatus.ROLLED_BACK

        # Verify file was restored
        assert (temp_project_dir / "src" / "utils.py").exists()
        assert (temp_project_dir / "src" / "utils.py").read_text() == original_content

    def test_rollback_nonexistent_patch(self, patch_applier):
        """Test rollback fails for non-existent patch."""
        with pytest.raises(PatchRollbackError, match="No application found"):
            patch_applier.rollback_patch("nonexistent-id")

    def test_rollback_not_applied(self, patch_applier, temp_project_dir):
        """Test rollback fails for patch not in APPLIED state."""
        original_content = (temp_project_dir / "src" / "main.py").read_text()

        change = FileChange(
            file_path="src/main.py",
            old_content=original_content,
            new_content="# Modified",
            change_type="modify",
        )

        patch = Patch(changes=[change])
        application = patch_applier.apply_patch(patch)

        # Rollback once
        patch_applier.rollback_patch(patch.id)

        # Try to rollback again
        with pytest.raises(PatchRollbackError, match="Cannot rollback"):
            patch_applier.rollback_patch(patch.id)


class TestPatchApplierUtilities:
    """Test PatchApplier utility methods."""

    def test_get_application(self, patch_applier, temp_project_dir):
        """Test retrieving application by ID."""
        original_content = (temp_project_dir / "src" / "main.py").read_text()

        change = FileChange(
            file_path="src/main.py",
            old_content=original_content,
            new_content="# Modified",
            change_type="modify",
        )

        patch = Patch(changes=[change])
        application = patch_applier.apply_patch(patch)

        retrieved = patch_applier.get_application(patch.id)
        assert retrieved is not None
        assert retrieved.patch_id == patch.id

        # Non-existent ID
        assert patch_applier.get_application("nonexistent") is None

    def test_list_applications(self, patch_applier, temp_project_dir):
        """Test listing applications."""
        original_content = (temp_project_dir / "src" / "main.py").read_text()

        # Apply first patch
        change1 = FileChange(
            file_path="src/main.py",
            old_content=original_content,
            new_content="# Modified 0",
            change_type="modify",
        )
        patch1 = Patch(changes=[change1])
        patch_applier.apply_patch(patch1)

        # Apply second patch (use diff content to avoid content mismatch)
        change2 = FileChange(
            file_path="src/utils.py",  # Different file
            old_content=(temp_project_dir / "src" / "utils.py").read_text(),
            new_content="# Modified utils",
            change_type="modify",
        )
        patch2 = Patch(changes=[change2])
        patch_applier.apply_patch(patch2)

        all_apps = patch_applier.list_applications()
        assert len(all_apps) == 2

        # Filter by status
        applied_apps = patch_applier.list_applications(status=PatchStatus.APPLIED)
        assert len(applied_apps) == 2

    def test_backup_created(self, patch_applier, temp_project_dir):
        """Test that backups are created when applying patches."""
        original_content = (temp_project_dir / "src" / "main.py").read_text()

        change = FileChange(
            file_path="src/main.py",
            old_content=original_content,
            new_content="# Modified",
            change_type="modify",
        )

        patch = Patch(changes=[change])
        application = patch_applier.apply_patch(patch)

        # Verify backup file exists
        backup_path = application.backup_paths.get("src/main.py")
        assert backup_path is not None
        assert Path(backup_path).exists()

        # Verify backup contains original content
        backup_content = Path(backup_path).read_text()
        assert backup_content == original_content


class TestEndToEnd:
    """End-to-end tests of the patch system."""

    def test_full_workflow(self, temp_project_dir):
        """Test complete patch workflow from generation to rollback."""
        # Create generator and applier
        generator = PatchGenerator()
        applier = PatchApplier(
            project_root=temp_project_dir,
            backup_dir=temp_project_dir / ".mike" / "backups",
        )

        # Create a refactor suggestion
        original_content = (temp_project_dir / "src" / "main.py").read_text()

        suggestion = {
            "file_path": "src/main.py",
            "line_start": 1,
            "line_end": 5,
            "original_code": original_content,
            "refactored_code": """\
def main():
    print("Hello Universe!")
    return 0

if __name__ == "__main__":
    main()
""",
            "description": "Update greeting to be more universal",
            "suggestion": "Use 'Universe' instead of 'World'",
            "smell_type": "style",
            "severity": "low",
        }

        # Generate patch
        patch = generator.from_refactor_suggestion(suggestion)
        assert patch is not None
        assert len(patch.changes) == 1

        # Preview
        preview = applier.preview_patch(patch)
        assert preview.can_apply
        assert preview.file_changes[0]["would_change"]

        # Validate
        validation = applier.validate_patch(patch)
        assert validation.valid

        # Apply
        application = applier.apply_patch(patch)
        assert application.status == PatchStatus.APPLIED

        # Verify changes
        new_content = (temp_project_dir / "src" / "main.py").read_text()
        assert "Universe" in new_content

        # Rollback
        applier.rollback_patch(patch.id)

        # Verify restoration
        restored_content = (temp_project_dir / "src" / "main.py").read_text()
        assert "World" in restored_content
        assert restored_content == original_content

    def test_multi_file_patch(self, temp_project_dir):
        """Test patching multiple files at once."""
        generator = PatchGenerator()
        applier = PatchApplier(
            project_root=temp_project_dir,
            backup_dir=temp_project_dir / ".mike" / "backups",
        )

        main_content = (temp_project_dir / "src" / "main.py").read_text()
        utils_content = (temp_project_dir / "src" / "utils.py").read_text()

        # Create multi-file patch
        file_changes = {
            "src/main.py": {
                "old_content": main_content,
                "new_content": "# Modified main",
                "change_type": "modify",
            },
            "src/utils.py": {
                "old_content": utils_content,
                "new_content": "# Modified utils",
                "change_type": "modify",
            },
        }

        patch = generator.create_multi_file_patch(
            file_changes, title="Multi-file refactor"
        )

        # Preview and apply
        preview = applier.preview_patch(patch)
        assert preview.can_apply
        assert len(preview.file_changes) == 2

        application = applier.apply_patch(patch)
        assert application.status == PatchStatus.APPLIED

        # Verify both files changed
        assert (temp_project_dir / "src" / "main.py").read_text() == "# Modified main"
        assert (temp_project_dir / "src" / "utils.py").read_text() == "# Modified utils"

        # Rollback
        applier.rollback_patch(patch.id)

        # Verify both files restored
        assert (temp_project_dir / "src" / "main.py").read_text() == main_content
        assert (temp_project_dir / "src" / "utils.py").read_text() == utils_content
