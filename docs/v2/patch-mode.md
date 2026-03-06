# Patch Apply Mode

The Patch Apply Mode provides a safe, controlled way to apply code changes with automatic backup, preview capabilities, and easy rollback. This feature ensures you can experiment with refactoring suggestions without risking your codebase.

## Overview

Patch Apply Mode provides:

- **Safe Application** - Automatic backups before changes
- **Preview Mode** - Dry-run to see what would change
- **Validation** - Check for conflicts before applying
- **Easy Rollback** - One-command undo
- **Multiple Operations** - Create, modify, delete, rename files

## Creating Patches

### From Refactor Suggestions

The most common use case is applying refactoring suggestions:

```python
from mike.patch import PatchGenerator, PatchApplier

# Generate patch from suggestion
suggestion = {
    "type": "extract_method",
    "description": "Extract complex logic into separate method",
    "file_path": "src/calculator.py",
    "old_content": '''def calculate_total(items):
    total = 0
    for item in items:
        if item.price > 0:
            if item.quantity > 0:
                total += item.price * item.quantity
                if item.taxable:
                    total += total * 0.1
    return total''',
    "new_content": '''def calculate_total(items):
    total = sum(
        calculate_item_total(item)
        for item in items
        if item.price > 0 and item.quantity > 0
    )
    return total

def calculate_item_total(item):
    subtotal = item.price * item.quantity
    if item.taxable:
        subtotal += subtotal * 0.1
    return subtotal''',
}

generator = PatchGenerator()
patch = generator.from_refactor_suggestion(suggestion)

print(f"Created patch: {patch.id}")
print(f"Files affected: {patch.files_affected}")
```

### From File Changes

Create patches manually for custom changes:

```python
from mike.patch.models import Patch, FileChange

# Create a multi-file patch
patch = Patch(
    changes=[
        # Modify existing file
        FileChange(
            file_path="src/config.py",
            old_content='DEBUG = True',
            new_content='DEBUG = False',
            change_type="modify",
        ),
        # Create new file
        FileChange(
            file_path="src/utils/helpers.py",
            new_content="""def helper():
    pass""",
            change_type="create",
        ),
        # Delete file
        FileChange(
            file_path="src/old_module.py",
            change_type="delete",
        ),
        # Rename file
        FileChange(
            file_path="src/new_name.py",
            original_path="src/old_name.py",
            change_type="rename",
        ),
    ],
    metadata={
        "title": "Configuration Update",
        "description": "Update debug mode and add helpers",
        "author": "developer@example.com",
    }
)
```

### From Diff Format

Import existing unified diffs:

```python
diff_content = '''diff --git a/src/main.py b/src/main.py
index abc123..def456 100644
--- a/src/main.py
+++ b/src/main.py
@@ -10,7 +10,7 @@ def main():
-    print("Hello")
+    print("Hello, World!")
     return 0
'''

patch = generator.from_diff(diff_content)
```

## Safe Application

### Validation Before Apply

Always validate patches before applying:

```python
applier = PatchApplier(project_root="/path/to/project")

# Validate the patch
validation = applier.validate_patch(patch)

if validation.valid:
    print("✓ Patch can be applied safely")
else:
    print("✗ Validation failed:")
    for conflict in validation.conflicts:
        print(f"  - {conflict}")
    
    if validation.missing_files:
        print(f"\nMissing files: {validation.missing_files}")
    
    if validation.warnings:
        print(f"\nWarnings: {validation.warnings}")
```

### Preview Changes

See exactly what would change before applying:

```python
preview = applier.preview_patch(patch)

print(f"Can apply: {preview.can_apply}")
print(f"Summary: {preview.changes_summary}")
print(f"Backup size: {preview.backup_size} bytes")

print("\nFile changes:")
for change in preview.file_changes:
    print(f"  {change['file_path']}")
    print(f"    Operation: {change['operation']}")
    print(f"    Would change: {change['would_change']}")
    print(f"    File exists: {change['exists']}")

if preview.warnings:
    print("\nWarnings:")
    for warning in preview.warnings:
        print(f"  ⚠️ {warning}")
```

### Apply with Backup

Apply patches with automatic backup:

```python
try:
    application = applier.apply_patch(patch)
    
    print(f"✓ Patch applied successfully")
    print(f"  Status: {application.status.value}")
    print(f"  Applied at: {application.applied_at}")
    
    # Show backed up files
    if application.backup_paths:
        print(f"\nBacked up files:")
        for original, backup in application.backup_paths.items():
            print(f"  {original} -> {backup}")
            
except PatchValidationError as e:
    print(f"✗ Validation failed: {e}")
    
except PatchApplicationError as e:
    print(f"✗ Application failed: {e}")
```

### Dry Run Mode

Test application without making changes:

```python
# Dry run - validates but doesn't apply
application = applier.apply_patch(patch, dry_run=True)

if application.status == PatchStatus.PENDING:
    print("✓ Dry run successful - patch can be applied")
    print(f"  Validation: {application.validation_result}")
```

## Rollback Procedures

### Rollback a Patch

Revert applied patches easily:

```python
# Rollback by patch ID
application = applier.rollback_patch(patch.id)

print(f"✓ Patch rolled back")
print(f"  Status: {application.status.value}")
print(f"  Rolled back at: {application.rolled_back_at}")

# Verify files are restored
for file_path in patch.files_affected:
    full_path = applier.project_root / file_path
    if full_path.exists():
        print(f"  ✓ {file_path} restored")
    else:
        print(f"  ✓ {file_path} removed (was created by patch)")
```

### Check Rollback Status

Verify if a patch can be rolled back:

```python
application = applier.get_application(patch.id)

if application.can_rollback():
    print("✓ Patch can be rolled back")
    print(f"  Backups available: {len(application.backup_paths)} files")
else:
    print("✗ Cannot rollback:")
    if application.status != PatchStatus.APPLIED:
        print(f"  - Status is {application.status.value}, not APPLIED")
    if not application.backup_paths:
        print("  - No backups available")
```

### List Applied Patches

View all applied patches:

```python
# All applications
all_apps = applier.list_applications()

# Only active (not rolled back)
active = applier.list_applications(status=PatchStatus.APPLIED)

# Failed applications
failed = applier.list_applications(status=PatchStatus.FAILED)

print(f"Active patches: {len(active)}")
for app in active:
    print(f"  {app.patch_id[:8]}... - {app.applied_at}")
```

## Best Practices

### 1. Always Preview First

```python
def safe_apply(applier, patch):
    """Safely apply a patch with preview."""
    # Preview first
    preview = applier.preview_patch(patch)
    
    print(f"Patch Preview:")
    print(f"  Summary: {preview.changes_summary}")
    print(f"  Backup size: {preview.backup_size} bytes")
    
    if preview.warnings:
        print("\nWarnings:")
        for warning in preview.warnings:
            print(f"  ⚠️ {warning}")
    
    if not preview.can_apply:
        print("\n✗ Cannot apply - aborting")
        return None
    
    # Confirm with user
    confirm = input("\nApply patch? [y/N]: ")
    if confirm.lower() != 'y':
        print("Aborted")
        return None
    
    # Apply
    return applier.apply_patch(patch)
```

### 2. Verify Before Rollback

```python
def safe_rollback(applier, patch_id):
    """Safely rollback a patch with verification."""
    application = applier.get_application(patch_id)
    
    if not application:
        print("✗ Patch not found")
        return None
    
    if not application.can_rollback():
        print(f"✗ Cannot rollback (status: {application.status.value})")
        return None
    
    # Show what will be restored
    print(f"Will restore {len(application.backup_paths)} files:")
    for original, backup in application.backup_paths.items():
        print(f"  {original}")
    
    # Confirm
    confirm = input("\nRollback? [y/N]: ")
    if confirm.lower() != 'y':
        print("Aborted")
        return None
    
    return applier.rollback_patch(patch_id)
```

### 3. Batch Operations

Apply multiple patches safely:

```python
def apply_patches_safely(applier, patches):
    """Apply multiple patches with rollback on failure."""
    applied = []
    
    try:
        for i, patch in enumerate(patches, 1):
            print(f"\n[{i}/{len(patches)}] Applying patch {patch.id[:8]}...")
            
            # Validate
            validation = applier.validate_patch(patch)
            if not validation.valid:
                print(f"✗ Validation failed:")
                for conflict in validation.conflicts:
                    print(f"    {conflict}")
                raise Exception(f"Patch {patch.id} validation failed")
            
            # Apply
            application = applier.apply_patch(patch)
            applied.append(application)
            print(f"✓ Applied successfully")
            
    except Exception as e:
        print(f"\n✗ Failed: {e}")
        print("Rolling back applied patches...")
        
        # Rollback in reverse order
        for application in reversed(applied):
            try:
                applier.rollback_patch(application.patch_id)
                print(f"  ✓ Rolled back {application.patch_id[:8]}...")
            except Exception as rollback_error:
                print(f"  ✗ Failed to rollback {application.patch_id[:8]}: {rollback_error}")
        
        raise
    
    return applied
```

### 4. Backup Management

Clean up old backups:

```python
import shutil
from datetime import datetime, timedelta
from pathlib import Path

def cleanup_old_backups(backup_dir, days=30):
    """Remove backups older than specified days."""
    cutoff = datetime.now() - timedelta(days=days)
    backup_path = Path(backup_dir)
    
    removed = 0
    for backup_subdir in backup_path.iterdir():
        if not backup_subdir.is_dir():
            continue
        
        # Parse timestamp from directory name (format: YYYYMMDD_HHMMSS_)
        try:
            timestamp_str = backup_subdir.name[:15]
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            
            if timestamp < cutoff:
                shutil.rmtree(backup_subdir)
                removed += 1
                print(f"Removed old backup: {backup_subdir.name}")
        except ValueError:
            continue
    
    print(f"\nCleaned up {removed} old backups")
    return removed
```

### 5. Patch Testing

Test patches in isolation:

```python
import tempfile
import shutil

def test_patch_in_isolation(project_path, patch):
    """Test a patch in a temporary copy of the project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Copy project to temp directory
        test_project = Path(tmpdir) / "project"
        shutil.copytree(project_path, test_project)
        
        # Apply patch
        applier = PatchApplier(project_root=test_project)
        
        try:
            application = applier.apply_patch(patch)
            print("✓ Patch applied successfully in test environment")
            
            # Run tests if available
            import subprocess
            result = subprocess.run(
                ["python", "-m", "pytest"],
                cwd=test_project,
                capture_output=True
            )
            
            if result.returncode == 0:
                print("✓ Tests pass")
                return True
            else:
                print("✗ Tests fail")
                return False
                
        except Exception as e:
            print(f"✗ Patch failed: {e}")
            return False
```

### 6. Patch Documentation

Document all patches for audit trail:

```python
def document_patch(patch, application, output_path="patch_history.json"):
    """Document patch application for audit trail."""
    import json
    from datetime import datetime
    
    documentation = {
        "patch_id": patch.id,
        "timestamp": datetime.now().isoformat(),
        "status": application.status.value,
        "files_affected": patch.files_affected,
        "metadata": patch.metadata,
        "applied_by": application.applied_by,
        "validation_result": application.validation_result,
    }
    
    # Load existing history
    try:
        with open(output_path) as f:
            history = json.load(f)
    except FileNotFoundError:
        history = []
    
    history.append(documentation)
    
    with open(output_path, "w") as f:
        json.dump(history, f, indent=2)
    
    print(f"Patch documented in {output_path}")
```

## Integration Examples

### CI/CD Integration

```yaml
# .github/workflows/patches.yml
name: Apply Refactoring Patches

on:
  workflow_dispatch:
    inputs:
      patch_file:
        description: 'Path to patch file'
        required: true

jobs:
  apply-patch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install Mike
        run: pip install mike
      
      - name: Load and Apply Patch
        run: |
          python -c "
          import json
          from mike.patch import PatchApplier
          from mike.patch.models import Patch
          
          # Load patch
          with open('${{ github.event.inputs.patch_file }}') as f:
              patch_dict = json.load(f)
          
          patch = Patch(**patch_dict)
          
          # Apply
          applier = PatchApplier()
          preview = applier.preview_patch(patch)
          
          if not preview.can_apply:
              print('Cannot apply patch')
              exit(1)
          
          application = applier.apply_patch(patch)
          print(f'Applied: {application.status}')
          "
      
      - name: Run Tests
        run: pytest
      
      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          title: 'Apply refactoring patch'
          body: 'Automated patch application'
```

### Pre-Commit Hook

```python
#!/usr/bin/env python
# .git/hooks/pre-commit

import sys
from pathlib import Path
from mike.patch import PatchApplier

# Check for staged patches
staged_patches = list(Path(".mike/patches/staged").glob("*.json"))

if not staged_patches:
    sys.exit(0)

applier = PatchApplier()

print(f"Found {len(staged_patches)} staged patches")

for patch_file in staged_patches:
    # Load and validate
    patch = load_patch(patch_file)
    validation = applier.validate_patch(patch)
    
    if not validation.valid:
        print(f"✗ {patch_file.name} has conflicts:")
        for conflict in validation.conflicts:
            print(f"    {conflict}")
        sys.exit(1)
    
    print(f"✓ {patch_file.name} validated")

print("All patches validated")
```

### IDE Integration

```python
# VS Code extension helper
def vscode_apply_patch(patch_file):
    """Apply patch from VS Code extension."""
    import json
    
    # Load patch
    with open(patch_file) as f:
        patch_dict = json.load(f)
    
    patch = Patch(**patch_dict)
    
    # Apply
    applier = PatchApplier()
    preview = applier.preview_patch(patch)
    
    if not preview.can_apply:
        return {
            "success": False,
            "error": "Cannot apply patch",
            "conflicts": preview.file_changes,
        }
    
    try:
        application = applier.apply_patch(patch)
        return {
            "success": True,
            "patch_id": patch.id,
            "files_changed": len(patch.files_affected),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
```

## CLI Integration

### Patch Commands

```bash
# Apply a patch file
mike patch apply refactoring.patch.json

# Preview a patch
mike patch preview refactoring.patch.json

# Validate a patch
mike patch validate refactoring.patch.json

# Rollback a patch
mike patch rollback <patch-id>

# List applied patches
mike patch list

# Show patch details
mike patch show <patch-id>
```

### Patch File Format

```json
{
  "id": "uuid-string",
  "files_affected": ["src/main.py", "src/utils.py"],
  "changes": [
    {
      "file_path": "src/main.py",
      "change_type": "modify",
      "old_content": "original code",
      "new_content": "refactored code"
    }
  ],
  "metadata": {
    "title": "Refactoring Title",
    "description": "Description of changes",
    "author": "developer@example.com",
    "source": "refactor_agent"
  }
}
```

## Troubleshooting

### Common Issues

**File Not Found:**
```python
# Ensure file exists before patching
if not (applier.project_root / "file.py").exists():
    raise FileNotFoundError("Target file doesn't exist")
```

**Content Mismatch:**
```python
# Check if file has changed since patch creation
validation = applier.validate_patch(patch)
if validation.conflicts:
    print("File has changed since patch was created")
    print("Consider regenerating the patch")
```

**Permission Errors:**
```python
# Ensure write permissions
import os
os.chmod(applier.project_root, 0o755)
```

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now apply patch - will show detailed logs
application = applier.apply_patch(patch)
```
