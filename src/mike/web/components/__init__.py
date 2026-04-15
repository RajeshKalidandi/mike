"""Web components for Mike Streamlit UI."""

# Import original core components
from mike.web.components._core import (
    render_agent_result,
    render_code_viewer,
    render_dependency_graph,
    render_file_size_chart,
    render_file_tree,
    render_language_chart,
    render_log_viewer,
    render_metrics_cards,
    render_progress_bar,
    render_session_card,
    render_timeline_chart,
)

# Import new Phase 1 components
from mike.web.components.health_score import (
    render_health_score_gauge,
    render_dimension_breakdown,
    render_health_trend_chart,
    render_file_level_scores,
    render_health_summary_card,
)
from mike.web.components.security_card import (
    render_vulnerability_card,
    render_vulnerability_table,
    render_risk_score_display,
    render_security_scan_summary,
)
from mike.web.components.git_chart import (
    render_hotspots_heatmap,
    render_churn_chart,
    render_author_contributions,
    render_bug_prone_files,
    render_rework_rate_chart,
    render_commit_activity_calendar,
    render_git_summary_metrics,
)
from mike.web.components.patch_preview import (
    render_diff_preview,
    render_patch_card,
    render_patch_list,
    render_patch_history,
    render_apply_confirmation,
)

__all__ = [
    # Core components
    "render_agent_result",
    "render_code_viewer",
    "render_dependency_graph",
    "render_file_size_chart",
    "render_file_tree",
    "render_language_chart",
    "render_log_viewer",
    "render_metrics_cards",
    "render_progress_bar",
    "render_session_card",
    "render_timeline_chart",
    # Health components
    "render_health_score_gauge",
    "render_dimension_breakdown",
    "render_health_trend_chart",
    "render_file_level_scores",
    "render_health_summary_card",
    # Security components
    "render_vulnerability_card",
    "render_vulnerability_table",
    "render_risk_score_display",
    "render_security_scan_summary",
    # Git components
    "render_hotspots_heatmap",
    "render_churn_chart",
    "render_author_contributions",
    "render_bug_prone_files",
    "render_rework_rate_chart",
    "render_commit_activity_calendar",
    "render_git_summary_metrics",
    # Patch components
    "render_diff_preview",
    "render_patch_card",
    "render_patch_list",
    "render_patch_history",
    "render_apply_confirmation",
]
