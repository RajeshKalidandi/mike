"""Patch Manager page for Mike v2 Phase 1.

Provides management of pending refactor suggestions,
diff preview, apply/rollback functionality, and patch history.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import streamlit as st

from mike.web.components.patch_preview import (
    render_apply_confirmation,
    render_diff_preview,
    render_patch_card,
    render_patch_history,
    render_patch_list,
)
from mike.web.utils import format_timestamp


def render_patch_manager():
    """Render the patch manager page."""
    st.title("🔧 Patch Manager")
    st.markdown("Review, apply, and manage code refactoring patches")

    # Check for active session
    if not st.session_state.get("current_session_id"):
        st.warning("No active session. Please select or create a session first.")
        if st.button("📁 Go to Sessions", use_container_width=True):
            st.session_state.current_page = "sessions"
            st.rerun()
        return

    session_id = st.session_state.current_session_id
    session_name = st.session_state.get("current_session_name", "Unnamed Session")

    st.markdown(f"**Session:** {session_name} (`{session_id[:8]}`)")

    # Generate sample patch data
    patches_data = _generate_sample_patches()

    # Sidebar filters
    with st.sidebar:
        st.markdown("### 🎛️ Filters")

        status_filter = st.selectbox(
            "Status",
            ["All", "Pending", "Applied", "Failed", "Rolled Back"],
        )

        st.divider()

        st.markdown("### 📊 Statistics")
        pending_count = len(
            [p for p in patches_data["patches"] if p["status"] == "pending"]
        )
        applied_count = len(
            [p for p in patches_data["patches"] if p["status"] == "applied"]
        )

        st.metric("Pending Patches", pending_count)
        st.metric("Applied Patches", applied_count)

    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["📋 Patch List", "🔍 Preview", "📜 History"])

    with tab1:
        render_patch_list_tab(patches_data["patches"], status_filter)

    with tab2:
        render_preview_tab(patches_data["patches"])

    with tab3:
        render_patch_history(patches_data["history"])


def render_patch_list_tab(patches: List[Dict[str, Any]], status_filter: str):
    """Render the patch list tab."""
    st.markdown("### 📋 Available Patches")

    # Filter patches
    filter_status = (
        None if status_filter == "All" else status_filter.lower().replace(" ", "_")
    )

    # Action handlers
    def on_apply(patch: Dict[str, Any]):
        st.session_state.selected_patch_for_apply = patch
        st.rerun()

    def on_preview(patch: Dict[str, Any]):
        st.session_state.selected_patch_for_preview = patch
        st.info(f"Previewing: {patch['title']}. Switch to the Preview tab.")

    def on_discard(patch: Dict[str, Any]):
        st.warning(f"Discarded: {patch['title']}")
        # In real implementation: call backend to discard

    def on_rollback(patch: Dict[str, Any]):
        st.warning(f"Rolled back: {patch['title']}")
        # In real implementation: call backend to rollback

    # Check if we need to show confirmation dialog
    if st.session_state.get("selected_patch_for_apply"):
        patch = st.session_state.selected_patch_for_apply

        st.markdown("### ⚠️ Confirm Patch Application")

        def confirm_apply(p):
            st.success(f"Applied: {p['title']}")
            st.session_state.selected_patch_for_apply = None
            # In real implementation: call backend to apply
            st.rerun()

        def cancel_apply():
            st.session_state.selected_patch_for_apply = None
            st.rerun()

        render_apply_confirmation(patch, confirm_apply, cancel_apply)
    else:
        # Show patch list
        render_patch_list(
            patches=patches,
            filter_status=filter_status,
            on_apply=on_apply,
            on_preview=on_preview,
            on_discard=on_discard,
            on_rollback=on_rollback,
        )


def render_preview_tab(patches: List[Dict[str, Any]]):
    """Render the patch preview tab."""
    st.markdown("### 🔍 Patch Preview")

    # Select patch to preview
    pending_patches = [p for p in patches if p["status"] == "pending"]

    if not pending_patches:
        st.info("No pending patches to preview")
        return

    # Use session state for selection
    if "selected_patch_for_preview" not in st.session_state:
        st.session_state.selected_patch_for_preview = pending_patches[0]

    selected_title = st.selectbox(
        "Select Patch",
        [p["title"] for p in pending_patches],
        index=0,
    )

    selected_patch = next(
        (p for p in pending_patches if p["title"] == selected_title), pending_patches[0]
    )

    st.session_state.selected_patch_for_preview = selected_patch

    # Show patch info
    st.markdown(f"**File:** `{selected_patch['file_path']}`")
    st.markdown(f"**Description:** {selected_patch['description']}")

    # Show diff preview
    if "original_code" in selected_patch and "patched_code" in selected_patch:
        render_diff_preview(
            original_code=selected_patch["original_code"],
            patched_code=selected_patch["patched_code"],
            file_path=selected_patch["file_path"],
            language=selected_patch.get("language", "python"),
            show_line_numbers=True,
            max_height=500,
        )
    else:
        st.info("No code diff available for this patch")

    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 3])

    with col1:
        if st.button("✅ Apply Patch", use_container_width=True, type="primary"):
            st.session_state.selected_patch_for_apply = selected_patch
            st.rerun()

    with col2:
        if st.button("🗑️ Discard", use_container_width=True):
            st.warning(f"Discarded: {selected_patch['title']}")
            st.rerun()


def render_history_tab(history: List[Dict[str, Any]]):
    """Render the history tab (wrapper for component)."""
    render_patch_history(history)


def _generate_sample_patches() -> Dict[str, Any]:
    """Generate sample patch data for demonstration."""
    import random

    patches = []

    # Sample patch 1: Extract method
    patches.append(
        {
            "id": "patch-001",
            "title": "Extract validation logic into separate method",
            "description": "Refactor long validation function by extracting it into smaller, reusable methods",
            "file_path": "src/services/user_service.py",
            "status": "pending",
            "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "language": "python",
            "original_code": """def validate_user_input(data):
    errors = []
    if not data.get('username'):
        errors.append('Username is required')
    if not data.get('email'):
        errors.append('Email is required')
    if '@' not in data.get('email', ''):
        errors.append('Invalid email format')
    if len(data.get('password', '')) < 8:
        errors.append('Password must be at least 8 characters')
    if not any(c.isupper() for c in data.get('password', '')):
        errors.append('Password must contain uppercase letter')
    if not any(c.islower() for c in data.get('password', '')):
        errors.append('Password must contain lowercase letter')
    if not any(c.isdigit() for c in data.get('password', '')):
        errors.append('Password must contain digit')
    return errors""",
            "patched_code": """def validate_user_input(data):
    errors = []
    errors.extend(_validate_username(data))
    errors.extend(_validate_email(data))
    errors.extend(_validate_password(data))
    return errors

def _validate_username(data):
    if not data.get('username'):
        return ['Username is required']
    return []

def _validate_email(data):
    errors = []
    if not data.get('email'):
        errors.append('Email is required')
    elif '@' not in data.get('email', ''):
        errors.append('Invalid email format')
    return errors

def _validate_password(data):
    errors = []
    password = data.get('password', '')
    if len(password) < 8:
        errors.append('Password must be at least 8 characters')
    if not any(c.isupper() for c in password):
        errors.append('Password must contain uppercase letter')
    if not any(c.islower() for c in password):
        errors.append('Password must contain lowercase letter')
    if not any(c.isdigit() for c in password):
        errors.append('Password must contain digit')
    return errors""",
        }
    )

    # Sample patch 2: Fix SQL injection
    patches.append(
        {
            "id": "patch-002",
            "title": "Fix SQL injection vulnerability",
            "description": "Replace string formatting with parameterized queries",
            "file_path": "src/services/database.py",
            "status": "pending",
            "created_at": (datetime.now() - timedelta(hours=5)).isoformat(),
            "language": "python",
            "original_code": """def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query).fetchone()""",
            "patched_code": """def get_user(user_id):
    query = "SELECT * FROM users WHERE id = %s"
    return db.execute(query, (user_id,)).fetchone()""",
        }
    )

    # Sample patch 3: Applied patch
    patches.append(
        {
            "id": "patch-003",
            "title": "Remove unused imports",
            "description": "Clean up unused imports in main module",
            "file_path": "src/main.py",
            "status": "applied",
            "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
            "applied_at": (datetime.now() - timedelta(hours=12)).isoformat(),
            "backup_path": ".mike/backups/main.py.bak",
        }
    )

    # Sample patch 4: Failed patch
    patches.append(
        {
            "id": "patch-004",
            "title": "Refactor authentication logic",
            "description": "Simplify authentication flow",
            "file_path": "src/auth.py",
            "status": "failed",
            "created_at": (datetime.now() - timedelta(days=2)).isoformat(),
            "error_message": "Merge conflict detected. File has been modified since patch creation.",
        }
    )

    # Sample patch 5: Rolled back
    patches.append(
        {
            "id": "patch-005",
            "title": "Update API endpoint URLs",
            "description": "Change REST API versioning scheme",
            "file_path": "src/api.py",
            "status": "rolled_back",
            "created_at": (datetime.now() - timedelta(days=3)).isoformat(),
            "applied_at": (datetime.now() - timedelta(days=2)).isoformat(),
            "rolled_back_at": (datetime.now() - timedelta(days=1)).isoformat(),
            "backup_path": ".mike/backups/api.py.bak",
        }
    )

    # More random patches
    for i in range(6, 10):
        statuses = ["pending", "pending", "applied"]
        status = random.choice(statuses)

        patches.append(
            {
                "id": f"patch-{i:03d}",
                "title": f"Refactoring suggestion #{i}",
                "description": f"Automated refactoring suggestion for improving code quality",
                "file_path": f"src/module{i}.py",
                "status": status,
                "created_at": (
                    datetime.now() - timedelta(hours=random.randint(1, 48))
                ).isoformat(),
            }
        )

    # History
    history = [
        {
            "timestamp": format_timestamp(
                (datetime.now() - timedelta(hours=12)).isoformat()
            ),
            "patch_id": "patch-003",
            "patch_title": "Remove unused imports",
            "action": "applied",
            "user": "System",
        },
        {
            "timestamp": format_timestamp(
                (datetime.now() - timedelta(days=1)).isoformat()
            ),
            "patch_id": "patch-004",
            "patch_title": "Refactor authentication logic",
            "action": "failed",
            "user": "System",
        },
        {
            "timestamp": format_timestamp(
                (datetime.now() - timedelta(days=1)).isoformat()
            ),
            "patch_id": "patch-005",
            "patch_title": "Update API endpoint URLs",
            "action": "rolled_back",
            "user": "admin",
        },
        {
            "timestamp": format_timestamp(
                (datetime.now() - timedelta(days=2)).isoformat()
            ),
            "patch_id": "patch-005",
            "patch_title": "Update API endpoint URLs",
            "action": "applied",
            "user": "System",
        },
        {
            "timestamp": format_timestamp(
                (datetime.now() - timedelta(days=2)).isoformat()
            ),
            "patch_id": "patch-004",
            "patch_title": "Refactor authentication logic",
            "action": "created",
            "user": "Refactor Agent",
        },
    ]

    return {
        "patches": patches,
        "history": history,
    }


# Page entry point
if __name__ == "__main__":
    render_patch_manager()
