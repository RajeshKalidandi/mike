"""Health score gauge component for displaying architecture health metrics.

Provides a visual gauge for health scores with color-coded indicators
and dimension breakdowns.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import plotly.graph_objects as go
import streamlit as st

from mike.web.theme_utils import get_current_theme, get_theme_colors


def render_health_score_gauge(
    score: float,
    title: str = "Architecture Health",
    size: str = "large",
    show_details: bool = True,
) -> None:
    """Render a health score gauge with color-coded indicators.

    Args:
        score: Health score from 0-100
        title: Title for the gauge
        size: Size of the gauge ('small', 'medium', 'large')
        show_details: Whether to show score details below gauge
    """
    theme = get_current_theme()
    colors = get_theme_colors(theme)

    # Determine color based on score
    if score >= 80:
        bar_color = colors["success"]
        status_text = "Excellent"
        status_icon = "🟢"
    elif score >= 60:
        bar_color = colors["warning"]
        status_text = "Good"
        status_icon = "🟡"
    elif score >= 40:
        bar_color = "#ff9500"
        status_text = "Fair"
        status_icon = "🟠"
    else:
        bar_color = colors["error"]
        status_text = "Poor"
        status_icon = "🔴"

    # Size configuration
    size_config = {
        "small": {"height": 200, "font_size": 16},
        "medium": {"height": 300, "font_size": 24},
        "large": {"height": 400, "font_size": 32},
    }
    config = size_config.get(size, size_config["large"])

    # Create gauge figure
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=score,
            domain={"x": [0, 1], "y": [0, 1]},
            title={
                "text": title,
                "font": {"size": config["font_size"], "color": colors["text"]},
            },
            number={
                "font": {"size": config["font_size"] * 1.5, "color": colors["text"]},
                "suffix": "%",
            },
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickwidth": 2,
                    "tickcolor": colors["border"],
                    "tickfont": {"color": colors["text_secondary"]},
                },
                "bar": {"color": bar_color, "thickness": 0.75},
                "bgcolor": colors["secondary_background"],
                "borderwidth": 2,
                "bordercolor": colors["border"],
                "steps": [
                    {"range": [0, 40], "color": f"{colors['error']}20"},
                    {"range": [40, 60], "color": f"{colors['warning']}20"},
                    {"range": [60, 80], "color": f"{colors['info']}20"},
                    {"range": [80, 100], "color": f"{colors['success']}20"},
                ],
                "threshold": {
                    "line": {"color": colors["text"], "width": 4},
                    "thickness": 0.8,
                    "value": score,
                },
            },
        )
    )

    # Apply theme
    fig.update_layout(
        paper_bgcolor=colors["background"],
        plot_bgcolor=colors["background"],
        height=config["height"],
        margin=dict(l=20, r=20, t=50, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)

    if show_details:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Status:** {status_icon} {status_text}")
        with col2:
            st.markdown(f"**Score:** {score:.1f}/100")


def render_dimension_breakdown(
    dimensions: Dict[str, Dict[str, Any]],
    show_trends: bool = True,
) -> None:
    """Render dimension breakdown for health score.

    Args:
        dimensions: Dict of dimension_name -> {score, weight, trend, description}
        show_trends: Whether to show trend indicators
    """
    theme = get_current_theme()
    colors = get_theme_colors(theme)

    st.markdown("### 📊 Dimension Breakdown")

    for dim_name, dim_data in dimensions.items():
        score = dim_data.get("score", 0)
        weight = dim_data.get("weight", 0)
        trend = dim_data.get("trend", 0)
        description = dim_data.get("description", "")

        # Determine color
        if score >= 80:
            color = colors["success"]
            icon = "🟢"
        elif score >= 60:
            color = colors["warning"]
            icon = "🟡"
        elif score >= 40:
            color = "#ff9500"
            icon = "🟠"
        else:
            color = colors["error"]
            icon = "🔴"

        with st.container():
            col1, col2, col3 = st.columns([2, 3, 1])

            with col1:
                st.markdown(f"**{icon} {dim_name}**")
                if description:
                    st.caption(description)
                st.caption(f"Weight: {weight}%")

            with col2:
                # Progress bar for score
                progress_html = f"""
                <div style="
                    background-color: {colors["secondary_background"]};
                    border-radius: 10px;
                    height: 20px;
                    overflow: hidden;
                    border: 1px solid {colors["border"]};
                ">
                    <div style="
                        background-color: {color};
                        width: {score}%;
                        height: 100%;
                        border-radius: 10px;
                        transition: width 0.3s ease;
                    "></div>
                </div>
                <div style="text-align: right; font-size: 12px; color: {colors["text_secondary"]};">
                    {score:.1f}%
                </div>
                """
                st.markdown(progress_html, unsafe_allow_html=True)

            with col3:
                if show_trends and trend != 0:
                    trend_icon = "📈" if trend > 0 else "📉"
                    trend_color = colors["success"] if trend > 0 else colors["error"]
                    trend_html = f"""
                    <div style="color: {trend_color}; text-align: center;">
                        {trend_icon} {abs(trend):.1f}%
                    </div>
                    """
                    st.markdown(trend_html, unsafe_allow_html=True)
                else:
                    st.markdown(
                        "<div style='text-align: center;'>-</div>",
                        unsafe_allow_html=True,
                    )

            st.divider()


def render_health_trend_chart(
    history: List[Dict[str, Any]],
    height: int = 400,
) -> None:
    """Render a trend chart for health scores over time.

    Args:
        history: List of {timestamp, score, dimensions} dicts
        height: Chart height in pixels
    """
    import plotly.express as px
    import pandas as pd
    from mike.web.theme_utils import apply_chart_theme

    if not history:
        st.info("No historical data available")
        return

    theme = get_current_theme()

    # Prepare data
    df_data = []
    for entry in history:
        df_data.append(
            {
                "timestamp": entry.get("timestamp"),
                "overall": entry.get("score", 0),
            }
        )
        # Add dimension scores if available
        dimensions = entry.get("dimensions", {})
        for dim_name, dim_score in dimensions.items():
            df_data[-1][dim_name] = dim_score

    df = pd.DataFrame(df_data)

    # Create line chart
    fig = px.line(
        df,
        x="timestamp",
        y=["overall"]
        + [col for col in df.columns if col not in ["timestamp", "overall"]],
        title="Health Score Trends",
        labels={"value": "Score", "variable": "Dimension"},
    )

    # Apply theme
    fig = apply_chart_theme(fig, theme)
    fig.update_layout(
        height=height,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )

    # Add threshold lines
    colors = get_theme_colors(theme)
    fig.add_hline(
        y=80,
        line_dash="dash",
        line_color=colors["success"],
        annotation_text="Excellent",
    )
    fig.add_hline(
        y=60, line_dash="dash", line_color=colors["warning"], annotation_text="Good"
    )
    fig.add_hline(y=40, line_dash="dash", line_color="#ff9500", annotation_text="Fair")

    st.plotly_chart(fig, use_container_width=True)


def render_file_level_scores(
    files: List[Dict[str, Any]],
    max_files: int = 50,
) -> None:
    """Render file-level health scores in a sortable table.

    Args:
        files: List of {path, score, issues_count, last_analyzed} dicts
        max_files: Maximum number of files to display
    """
    import pandas as pd

    theme = get_current_theme()
    colors = get_theme_colors(theme)

    if not files:
        st.info("No file-level scores available")
        return

    # Sort by score (lowest first - worst files)
    sorted_files = sorted(files, key=lambda x: x.get("score", 100))[:max_files]

    # Prepare data for display
    df_data = []
    for f in sorted_files:
        score = f.get("score", 0)
        if score >= 80:
            status = "🟢 Good"
        elif score >= 60:
            status = "🟡 Fair"
        elif score >= 40:
            status = "🟠 Poor"
        else:
            status = "🔴 Critical"

        df_data.append(
            {
                "File": f.get("path", "Unknown"),
                "Score": score,
                "Status": status,
                "Issues": f.get("issues_count", 0),
                "Last Analyzed": f.get("last_analyzed", "Unknown"),
            }
        )

    df = pd.DataFrame(df_data)

    st.markdown(f"### 📁 File-Level Scores (showing {len(df_data)} lowest)")

    # Color-code the Score column
    def color_score(val):
        if val >= 80:
            return (
                f"background-color: {colors['success']}20; color: {colors['success']}"
            )
        elif val >= 60:
            return (
                f"background-color: {colors['warning']}20; color: {colors['warning']}"
            )
        elif val >= 40:
            return f"background-color: #ff950020; color: #ff9500"
        else:
            return f"background-color: {colors['error']}20; color: {colors['error']}"

    styled_df = df.style.applymap(color_score, subset=["Score"])
    st.dataframe(styled_df, use_container_width=True, hide_index=True)


def render_health_summary_card(
    overall_score: float,
    files_analyzed: int,
    issues_found: int,
    last_scan: str,
) -> None:
    """Render a summary card with key health metrics.

    Args:
        overall_score: Overall health score
        files_analyzed: Number of files analyzed
        issues_found: Number of issues found
        last_scan: Timestamp of last scan
    """
    theme = get_current_theme()
    colors = get_theme_colors(theme)

    # Determine status
    if overall_score >= 80:
        status_color = colors["success"]
        status_bg = f"{colors['success']}15"
        status_icon = "🟢"
        status_text = "Healthy"
    elif overall_score >= 60:
        status_color = colors["warning"]
        status_bg = f"{colors['warning']}15"
        status_icon = "🟡"
        status_text = "Needs Attention"
    else:
        status_color = colors["error"]
        status_bg = f"{colors['error']}15"
        status_icon = "🔴"
        status_text = "Critical"

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
            <h3 style="margin: 0; color: {colors["text"]};">Health Summary</h3>
            <span style="
                background-color: {status_bg};
                color: {status_color};
                padding: 5px 15px;
                border-radius: 20px;
                font-weight: bold;
                border: 1px solid {status_color};
            ">
                {status_icon} {status_text}
            </span>
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px;">
            <div style="text-align: center;">
                <div style="font-size: 32px; font-weight: bold; color: {status_color};">
                    {overall_score:.1f}%
                </div>
                <div style="color: {colors["text_secondary"]}; font-size: 14px;">Overall Score</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 32px; font-weight: bold; color: {colors["text"]};">
                    {files_analyzed:,}
                </div>
                <div style="color: {colors["text_secondary"]}; font-size: 14px;">Files Analyzed</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 32px; font-weight: bold; color: {colors["error"]};">
                    {issues_found:,}
                </div>
                <div style="color: {colors["text_secondary"]}; font-size: 14px;">Issues Found</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 14px; font-weight: bold; color: {colors["text"]};">
                    {last_scan}
                </div>
                <div style="color: {colors["text_secondary"]}; font-size: 14px;">Last Scan</div>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
