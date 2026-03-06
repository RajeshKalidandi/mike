"""Web frontend module for Mike.

Provides a Streamlit-based web interface for interacting with the
codebase analysis and agent orchestration system.
"""

from .utils import (
    get_db_path,
    load_settings,
    save_settings,
    format_file_size,
    format_timestamp,
    create_session_zip,
    extract_session_zip,
)

from .components import (
    render_session_card,
    render_file_tree,
    render_progress_bar,
    render_agent_result,
    render_dependency_graph,
    render_metrics_cards,
    render_log_viewer,
    render_code_viewer,
)

__all__ = [
    "get_db_path",
    "load_settings",
    "save_settings",
    "format_file_size",
    "format_timestamp",
    "create_session_zip",
    "extract_session_zip",
    "render_session_card",
    "render_file_tree",
    "render_progress_bar",
    "render_agent_result",
    "render_dependency_graph",
    "render_metrics_cards",
    "render_log_viewer",
    "render_code_viewer",
]
