"""Git analytics chart components for visualizing repository metrics.

Provides charts and visualizations for git history, hotspots, churn, and contributions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from mike.web.theme_utils import get_current_theme, get_theme_colors, apply_chart_theme


def render_hotspots_heatmap(
    hotspots: List[Dict[str, Any]],
    height: int = 500,
) -> None:
    """Render a heatmap of code hotspots.

    Args:
        hotspots: List of {file, commits, complexity, churn} dicts
        height: Chart height in pixels
    """
    import pandas as pd

    theme = get_current_theme()
    colors = get_theme_colors(theme)

    if not hotspots:
        st.info("No hotspot data available")
        return

    # Prepare data
    df = pd.DataFrame(hotspots)

    # Create treemap for hotspots
    fig = px.treemap(
        df,
        path=["file"],
        values="commits",
        color="churn",
        hover_data=["complexity"],
        title="Code Hotspots (size = commits, color = churn)",
        color_continuous_scale="RdYlGn_r",
    )

    # Apply theme
    fig.update_layout(
        paper_bgcolor=colors["background"],
        plot_bgcolor=colors["background"],
        font=dict(color=colors["text"]),
        height=height,
    )

    st.plotly_chart(fig, use_container_width=True)


def render_churn_chart(
    churn_data: List[Dict[str, Any]],
    time_period: str = "monthly",
    height: int = 400,
) -> None:
    """Render a churn visualization over time.

    Args:
        churn_data: List of {date, added, deleted, modified, net_churn} dicts
        time_period: Time grouping ('daily', 'weekly', 'monthly')
        height: Chart height in pixels
    """
    import pandas as pd

    theme = get_current_theme()
    colors = get_theme_colors(theme)

    if not churn_data:
        st.info("No churn data available")
        return

    # Prepare data
    df = pd.DataFrame(churn_data)
    df["date"] = pd.to_datetime(df["date"])

    # Create stacked bar chart
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="Added",
            x=df["date"],
            y=df["added"],
            marker_color=colors["success"],
        )
    )

    fig.add_trace(
        go.Bar(
            name="Deleted",
            x=df["date"],
            y=df["deleted"],
            marker_color=colors["error"],
        )
    )

    fig.add_trace(
        go.Bar(
            name="Modified",
            x=df["date"],
            y=df["modified"],
            marker_color=colors["warning"],
        )
    )

    fig.update_layout(
        title=f"Code Churn ({time_period.title()})",
        barmode="group",
        xaxis_title="Date",
        yaxis_title="Lines of Code",
        height=height,
    )

    # Apply theme
    fig = apply_chart_theme(fig, theme)

    st.plotly_chart(fig, use_container_width=True)


def render_author_contributions(
    contributions: List[Dict[str, Any]],
    chart_type: str = "pie",
    height: int = 400,
) -> None:
    """Render author contribution charts.

    Args:
        contributions: List of {author, commits, additions, deletions, files} dicts
        chart_type: Type of chart ('pie', 'bar', 'treemap')
        height: Chart height in pixels
    """
    import pandas as pd

    theme = get_current_theme()
    colors = get_theme_colors(theme)

    if not contributions:
        st.info("No contribution data available")
        return

    # Prepare data
    df = pd.DataFrame(contributions)

    if chart_type == "pie":
        fig = px.pie(
            df,
            values="commits",
            names="author",
            title="Commits by Author",
            hole=0.4,
        )
    elif chart_type == "bar":
        fig = px.bar(
            df,
            x="author",
            y=["commits", "additions", "deletions"],
            title="Contributions by Author",
            barmode="group",
        )
    elif chart_type == "treemap":
        fig = px.treemap(
            df,
            path=["author"],
            values="commits",
            color="files",
            title="Author Contributions (size = commits, color = files touched)",
        )
    else:
        st.error(f"Unknown chart type: {chart_type}")
        return

    # Apply theme
    fig = apply_chart_theme(fig, theme)
    fig.update_layout(height=height)

    st.plotly_chart(fig, use_container_width=True)


def render_bug_prone_files(
    files: List[Dict[str, Any]],
    max_files: int = 20,
) -> None:
    """Render a list of bug-prone files with metrics.

    Args:
        files: List of {path, bug_commits, total_commits, bug_ratio, last_bug_date} dicts
        max_files: Maximum number of files to display
    """
    import pandas as pd

    theme = get_current_theme()
    colors = get_theme_colors(theme)

    if not files:
        st.info("No bug-prone file data available")
        return

    # Sort by bug ratio
    sorted_files = sorted(files, key=lambda x: x.get("bug_ratio", 0), reverse=True)[
        :max_files
    ]

    # Prepare data
    df_data = []
    for f in sorted_files:
        bug_ratio = f.get("bug_ratio", 0)
        if bug_ratio >= 0.3:
            icon = "🔴"
        elif bug_ratio >= 0.2:
            icon = "🟠"
        elif bug_ratio >= 0.1:
            icon = "🟡"
        else:
            icon = "🟢"

        df_data.append(
            {
                "Risk": icon,
                "File": f.get("path", "Unknown"),
                "Bug Commits": f.get("bug_commits", 0),
                "Total Commits": f.get("total_commits", 0),
                "Bug Ratio": f"{bug_ratio:.1%}",
                "Last Bug": f.get("last_bug_date", "Unknown"),
            }
        )

    df = pd.DataFrame(df_data)

    st.markdown(f"### 🐛 Bug-Prone Files (top {len(df_data)})")
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_rework_rate_chart(
    rework_data: List[Dict[str, Any]],
    height: int = 350,
) -> None:
    """Render rework rate metrics over time.

    Args:
        rework_data: List of {date, rework_rate, total_commits, rework_commits} dicts
        height: Chart height in pixels
    """
    import pandas as pd

    theme = get_current_theme()
    colors = get_theme_colors(theme)

    if not rework_data:
        st.info("No rework data available")
        return

    # Prepare data
    df = pd.DataFrame(rework_data)
    df["date"] = pd.to_datetime(df["date"])

    # Create subplot with dual y-axes
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Rework rate line
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["rework_rate"],
            name="Rework Rate (%)",
            line=dict(color=colors["warning"], width=3),
            mode="lines+markers",
        ),
        secondary_y=False,
    )

    # Total commits bars
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["total_commits"],
            name="Total Commits",
            marker_color=colors["accent_blue"],
            opacity=0.5,
        ),
        secondary_y=True,
    )

    # Update layout
    fig.update_layout(
        title="Rework Rate Over Time",
        height=height,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )

    fig.update_yaxes(title_text="Rework Rate (%)", secondary_y=False)
    fig.update_yaxes(title_text="Total Commits", secondary_y=True)

    # Add threshold line
    fig.add_hline(
        y=20,
        line_dash="dash",
        line_color=colors["error"],
        annotation_text="High Rework Threshold",
    )

    # Apply theme
    fig = apply_chart_theme(fig, theme)

    st.plotly_chart(fig, use_container_width=True)


def render_commit_activity_calendar(
    commit_data: List[Dict[str, Any]],
    height: int = 200,
) -> None:
    """Render a calendar heatmap of commit activity.

    Args:
        commit_data: List of {date, commits, authors} dicts
        height: Chart height in pixels
    """
    import pandas as pd
    import numpy as np

    theme = get_current_theme()
    colors = get_theme_colors(theme)

    if not commit_data:
        st.info("No commit activity data available")
        return

    # Prepare data
    df = pd.DataFrame(commit_data)
    df["date"] = pd.to_datetime(df["date"])
    df["weekday"] = df["date"].dt.day_name()
    df["week"] = df["date"].dt.isocalendar().week

    # Pivot for heatmap
    pivot = df.pivot_table(
        values="commits", index="weekday", columns="week", aggfunc="sum", fill_value=0
    )

    # Reorder weekdays
    weekday_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    pivot = pivot.reindex([d for d in weekday_order if d in pivot.index])

    # Create heatmap
    fig = px.imshow(
        pivot,
        title="Commit Activity Calendar",
        color_continuous_scale="Greens",
        aspect="auto",
    )

    fig.update_layout(
        height=height,
        xaxis_title="Week",
        yaxis_title="",
    )

    # Apply theme
    fig = apply_chart_theme(fig, theme)

    st.plotly_chart(fig, use_container_width=True)


def render_git_summary_metrics(
    total_commits: int,
    total_authors: int,
    avg_commits_per_week: float,
    active_branches: int,
    time_range: str,
) -> None:
    """Render summary metrics for git analytics.

    Args:
        total_commits: Total number of commits
        total_authors: Number of unique authors
        avg_commits_per_week: Average commits per week
        active_branches: Number of active branches
        time_range: Time range of the analysis (e.g., "Last 30 days")
    """
    theme = get_current_theme()
    colors = get_theme_colors(theme)

    st.markdown(
        f"""
    <div style="
        background-color: {colors["card_background"]};
        border: 1px solid {colors["border"]};
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <h4 style="margin: 0; color: {colors["text"]};">📊 Git Analytics Summary</h4>
            <span style="color: {colors["text_secondary"]}; font-size: 14px;">{time_range}</span>
        </div>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px;">
            <div style="text-align: center;">
                <div style="font-size: 28px; font-weight: bold; color: {colors["primary"]};">
                    {total_commits:,}
                </div>
                <div style="color: {colors["text_secondary"]}; font-size: 14px;">Total Commits</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 28px; font-weight: bold; color: {colors["accent_blue"]};">
                    {total_authors}
                </div>
                <div style="color: {colors["text_secondary"]}; font-size: 14px;">Contributors</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 28px; font-weight: bold; color: {colors["accent_green"]};">
                    {avg_commits_per_week:.1f}
                </div>
                <div style="color: {colors["text_secondary"]}; font-size: 14px;">Avg Commits/Week</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 28px; font-weight: bold; color: {colors["accent_purple"]};">
                    {active_branches}
                </div>
                <div style="color: {colors["text_secondary"]}; font-size: 14px;">Active Branches</div>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
