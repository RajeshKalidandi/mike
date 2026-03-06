"""Patch preview component for displaying and managing code refactor patches.

Provides diff visualization, patch application, and rollback functionality.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import streamlit as st

from mike.web.theme_utils import get_current_theme, get_theme_colors


def render_diff_preview(
    original_code: str,
    patched_code: str,
    file_path: str = "",
    language: str = "python",
    show_line_numbers: bool = True,
    max_height: int = 400,
) -> None:
    """Render a side-by-side diff preview.

    Args:
        original_code: Original code content
        patched_code: Modified code content
        file_path: Path to the file being modified
        language: Programming language for syntax highlighting
        show_line_numbers: Whether to show line numbers
        max_height: Maximum height of the diff viewer
    """
    theme = get_current_theme()
    colors = get_theme_colors(theme)

    # Calculate diff
    import difflib

    original_lines = original_code.splitlines(keepends=True)
    patched_lines = patched_code.splitlines(keepends=True)

    diff = list(
        difflib.unified_diff(
            original_lines,
            patched_lines,
            fromfile=f"a/{file_path}" if file_path else "original",
            tofile=f"b/{file_path}" if file_path else "patched",
            lineterm="",
        )
    )

    if not diff:
        st.info("No changes to display")
        return

    # Render diff with syntax highlighting
    diff_html = f"""
    <div style="
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        font-size: 13px;
        line-height: 1.5;
        background-color: {colors["card_background"]};
        border: 1px solid {colors["border"]};
        border-radius: 8px;
        overflow: auto;
        max-height: {max_height}px;
    ">
    """

    line_num_old = 0
    line_num_new = 0

    for line in diff:
        if line.startswith("@@"):
            # Hunk header
            diff_html += f'<div style="background-color: {colors["secondary_background"]}; color: {colors["accent_blue"]}; padding: 4px 8px; font-weight: bold;">{line}</div>'
            # Parse line numbers
            try:
                parts = line.split()[1:3]
                line_num_old = int(parts[0].split(",")[0].replace("-", "")) - 1
                line_num_new = int(parts[1].split(",")[0].replace("+", "")) - 1
            except:
                pass
        elif line.startswith("---"):
            diff_html += f'<div style="color: {colors["text_secondary"]}; padding: 2px 8px;">{line}</div>'
        elif line.startswith("+++"):
            diff_html += f'<div style="color: {colors["text_secondary"]}; padding: 2px 8px;">{line}</div>'
        elif line.startswith("-"):
            line_num_old += 1
            diff_html += f'<div style="background-color: {colors["error"]}15; color: {colors["error"]}; padding: 2px 8px;">{line}</div>'
        elif line.startswith("+"):
            line_num_new += 1
            diff_html += f'<div style="background-color: {colors["success"]}15; color: {colors["success"]}; padding: 2px 8px;">{line}</div>'
        else:
            line_num_old += 1
            line_num_new += 1
            diff_html += (
                f'<div style="color: {colors["text"]}; padding: 2px 8px;">{line}</div>'
            )

    diff_html += "</div>"

    if file_path:
        st.markdown(f"**File:** `{file_path}`")

    st.markdown(diff_html, unsafe_allow_html=True)

    # Summary stats
    added = sum(
        1 for line in diff if line.startswith("+") and not line.startswith("+++")
    )
    removed = sum(
        1 for line in diff if line.startswith("-") and not line.startswith("---")
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"<span style='color: {colors['success']};'>+{added} lines added</span>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"<span style='color: {colors['error']};'>-{removed} lines removed</span>",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(f"**Net change:** {added - removed:+d} lines")


def render_patch_card(
    patch: Dict[str, Any],
    on_apply: Optional[Callable] = None,
    on_preview: Optional[Callable] = None,
    on_discard: Optional[Callable] = None,
) -> None:
    """Render a patch card with actions.

    Args:
        patch: Patch data dict
        on_apply: Callback when apply button is clicked
        on_preview: Callback when preview button is clicked
        on_discard: Callback when discard button is clicked
    """
    theme = get_current_theme()
    colors = get_theme_colors(theme)

    patch_id = patch.get("id", "unknown")
    title = patch.get("title", "Untitled Patch")
    description = patch.get("description", "")
    file_path = patch.get("file_path", "")
    status = patch.get("status", "pending")  # pending, applied, failed, rolled_back
    created_at = patch.get("created_at", "")

    # Status styling
    status_styles = {
        "pending": {
            "color": colors["warning"],
            "bg": f"{colors['warning']}15",
            "icon": "⏳",
        },
        "applied": {
            "color": colors["success"],
            "bg": f"{colors['success']}15",
            "icon": "✅",
        },
        "failed": {
            "color": colors["error"],
            "bg": f"{colors['error']}15",
            "icon": "❌",
        },
        "rolled_back": {
            "color": colors["text_secondary"],
            "bg": f"{colors['text_secondary']}15",
            "icon": "↩️",
        },
    }
    style = status_styles.get(status, status_styles["pending"])

    with st.container():
        st.markdown(
            f"""
        <div style="
            background-color: {colors["card_background"]};
            border: 1px solid {colors["border"]};
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
        ">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div style="flex: 1;">
                    <h4 style="margin: 0 0 5px 0; color: {colors["text"]};">{title}</h4>
                    <p style="margin: 0; color: {colors["text_secondary"]}; font-size: 14px;">{description}</p>
                    {f'<p style="margin: 5px 0 0 0; font-size: 12px; color: {colors["text_secondary"]};">📄 {file_path}</p>' if file_path else ""}
                </div>
                <span style="
                    background-color: {style["bg"]};
                    color: {style["color"]};
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: bold;
                    margin-left: 10px;
                ">{style["icon"]} {status.replace("_", " ").title()}</span>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Action buttons
        col1, col2, col3 = st.columns([1, 1, 3])

        with col1:
            if status == "pending" and on_apply:
                if st.button(
                    "✅ Apply", key=f"apply_{patch_id}", use_container_width=True
                ):
                    on_apply(patch)

        with col2:
            if on_preview:
                if st.button(
                    "👁️ Preview", key=f"preview_{patch_id}", use_container_width=True
                ):
                    on_preview(patch)

        with col3:
            if status == "pending" and on_discard:
                if st.button(
                    "🗑️ Discard", key=f"discard_{patch_id}", use_container_width=True
                ):
                    on_discard(patch)

        st.divider()


def render_patch_list(
    patches: List[Dict[str, Any]],
    filter_status: Optional[str] = None,
    on_apply: Optional[Callable] = None,
    on_preview: Optional[Callable] = None,
    on_discard: Optional[Callable] = None,
    on_rollback: Optional[Callable] = None,
) -> None:
    """Render a list of patches with filtering.

    Args:
        patches: List of patch dicts
        filter_status: Filter by status ('pending', 'applied', 'failed', 'rolled_back')
        on_apply: Callback when apply button is clicked
        on_preview: Callback when preview button is clicked
        on_discard: Callback when discard button is clicked
        on_rollback: Callback when rollback button is clicked
    """
    if not patches:
        st.info("No patches available")
        return

    # Filter patches
    if filter_status:
        patches = [p for p in patches if p.get("status") == filter_status]

    # Group by status
    pending = [p for p in patches if p.get("status") == "pending"]
    applied = [p for p in patches if p.get("status") == "applied"]
    failed = [p for p in patches if p.get("status") == "failed"]
    rolled_back = [p for p in patches if p.get("status") == "rolled_back"]

    # Summary
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Pending", len(pending))
    with col2:
        st.metric("Applied", len(applied))
    with col3:
        st.metric("Failed", len(failed))
    with col4:
        st.metric("Rolled Back", len(rolled_back))

    st.divider()

    # Display patches by status
    if pending:
        st.markdown("### ⏳ Pending Patches")
        for patch in pending:
            render_patch_card(patch, on_apply, on_preview, on_discard)

    if applied:
        st.markdown("### ✅ Applied Patches")
        for patch in applied:
            patch_id = patch.get("id", "unknown")
            with st.container():
                render_patch_card(patch, on_preview=on_preview)
                if on_rollback:
                    if st.button(
                        "↩️ Rollback",
                        key=f"rollback_{patch_id}",
                        use_container_width=True,
                    ):
                        on_rollback(patch)

    if failed:
        st.markdown("### ❌ Failed Patches")
        for patch in failed:
            error_message = patch.get("error_message", "Unknown error")
            with st.container():
                render_patch_card(patch, on_preview=on_preview)
                st.error(f"Error: {error_message}")

    if rolled_back:
        st.markdown("### ↩️ Rolled Back Patches")
        for patch in rolled_back:
            rolled_back_at = patch.get("rolled_back_at", "")
            with st.container():
                render_patch_card(patch, on_preview=on_preview)
                st.caption(f"Rolled back at: {rolled_back_at}")


def render_patch_history(
    history: List[Dict[str, Any]],
) -> None:
    """Render patch application history.

    Args:
        history: List of {timestamp, patch_id, action, user, details} dicts
    """
    theme = get_current_theme()
    colors = get_theme_colors(theme)

    if not history:
        st.info("No patch history available")
        return

    st.markdown("### 📜 Patch History")

    for entry in history:
        timestamp = entry.get("timestamp", "")
        action = entry.get("action", "")
        patch_title = entry.get("patch_title", "Unknown")
        user = entry.get("user", "System")

        # Action styling
        action_styles = {
            "created": {"icon": "📝", "color": colors["info"]},
            "applied": {"icon": "✅", "color": colors["success"]},
            "failed": {"icon": "❌", "color": colors["error"]},
            "rolled_back": {"icon": "↩️", "color": colors["text_secondary"]},
            "discarded": {"icon": "🗑️", "color": colors["text_secondary"]},
        }
        style = action_styles.get(action, {"icon": "📋", "color": colors["text"]})

        st.markdown(
            f"""
        <div style="
            border-left: 3px solid {style["color"]};
            padding: 8px 12px;
            margin-bottom: 8px;
            background-color: {colors["secondary_background"]};
            border-radius: 0 4px 4px 0;
        ">
            <div style="display: flex; justify-content: space-between;">
                <span>{style["icon"]} <strong>{action.title()}</strong> - {patch_title}</span>
                <span style="color: {colors["text_secondary"]}; font-size: 12px;">{timestamp}</span>
            </div>
            <div style="color: {colors["text_secondary"]}; font-size: 12px; margin-top: 4px;">
                by {user}
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )


def render_apply_confirmation(
    patch: Dict[str, Any],
    on_confirm: Optional[Callable] = None,
    on_cancel: Optional[Callable] = None,
) -> None:
    """Render a confirmation dialog for applying a patch.

    Args:
        patch: Patch data dict
        on_confirm: Callback when confirmed
        on_cancel: Callback when cancelled
    """
    theme = get_current_theme()
    colors = get_theme_colors(theme)

    title = patch.get("title", "Untitled")
    file_path = patch.get("file_path", "")
    backup_path = patch.get("backup_path", "")

    st.warning("⚠️ Please review the patch before applying")

    st.markdown(
        f"""
    <div style="
        background-color: {colors["warning"]}10;
        border: 1px solid {colors["warning"]};
        border-radius: 8px;
        padding: 15px;
        margin: 15px 0;
    ">
        <h4 style="margin-top: 0;">Patch Details</h4>
        <p><strong>Title:</strong> {title}</p>
        <p><strong>File:</strong> <code>{file_path}</code></p>
        <p><strong>Backup:</strong> Will be created at <code>{backup_path or "auto-generated"}</code></p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        if on_confirm and st.button(
            "✅ Confirm Apply", use_container_width=True, type="primary"
        ):
            on_confirm(patch)
    with col2:
        if on_cancel and st.button("❌ Cancel", use_container_width=True):
            on_cancel()
