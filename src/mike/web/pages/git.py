"""Git Analytics page for Mike v2 Phase 1.

Provides git history visualization, code hotspots, churn analysis,
author contributions, and bug-prone file detection.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

import streamlit as st

from mike.web.components.git_chart import (
    render_author_contributions,
    render_bug_prone_files,
    render_churn_chart,
    render_commit_activity_calendar,
    render_git_summary_metrics,
    render_hotspots_heatmap,
    render_rework_rate_chart,
)
from mike.web.utils import format_timestamp


def render_git_analytics():
    """Render the git analytics page."""
    st.title("📊 Git Analytics")
    st.markdown(
        "Analyze repository history, contributions, and code evolution patterns"
    )

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

    # Generate sample git data
    git_data = _generate_sample_git_data()

    # Summary metrics
    render_git_summary_metrics(
        total_commits=git_data["total_commits"],
        total_authors=git_data["total_authors"],
        avg_commits_per_week=git_data["avg_commits_per_week"],
        active_branches=git_data["active_branches"],
        time_range=git_data["time_range"],
    )

    # Tabs for different analytics views
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["🔥 Hotspots", "📈 Churn", "👥 Contributors", "🐛 Bug Files", "📅 Activity"]
    )

    with tab1:
        render_hotspots_tab(git_data)

    with tab2:
        render_churn_tab(git_data)

    with tab3:
        render_contributors_tab(git_data)

    with tab4:
        render_bug_files_tab(git_data)

    with tab5:
        render_activity_tab(git_data)


def render_hotspots_tab(git_data: Dict[str, Any]):
    """Render the code hotspots tab."""
    st.markdown("### 🔥 Code Hotspots")
    st.markdown("Files with high commit activity and churn")

    # Filter options
    col1, col2 = st.columns([2, 1])
    with col1:
        min_commits = st.slider("Min Commits", 1, 50, 5)
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    # Filter hotspots
    filtered_hotspots = [h for h in git_data["hotspots"] if h["commits"] >= min_commits]

    if filtered_hotspots:
        render_hotspots_heatmap(filtered_hotspots, height=500)
    else:
        st.info("No hotspots found matching criteria")

    # Hotspots table
    st.markdown("### 📋 Hotspot Details")
    import pandas as pd

    df = pd.DataFrame(filtered_hotspots[:20])
    if not df.empty:
        df = df.sort_values("commits", ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_churn_tab(git_data: Dict[str, Any]):
    """Render the churn analysis tab."""
    st.markdown("### 📈 Code Churn Analysis")
    st.markdown("Track code changes over time")

    # Time period selector
    time_period = st.selectbox(
        "Time Period",
        ["Daily", "Weekly", "Monthly"],
        index=1,
    )

    period_map = {"Daily": "daily", "Weekly": "weekly", "Monthly": "monthly"}

    render_churn_chart(
        git_data["churn"],
        time_period=period_map[time_period],
        height=400,
    )

    # Rework rate
    st.markdown("### 🔄 Rework Rate")
    st.markdown("Percentage of commits that are fixes or modifications to recent code")

    render_rework_rate_chart(git_data["rework_rate"], height=350)

    # Churn statistics
    st.markdown("### 📊 Churn Statistics")

    total_added = sum(c["added"] for c in git_data["churn"])
    total_deleted = sum(c["deleted"] for c in git_data["churn"])
    total_modified = sum(c["modified"] for c in git_data["churn"])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Lines Added", f"{total_added:,}")
    with col2:
        st.metric("Lines Deleted", f"{total_deleted:,}")
    with col3:
        st.metric("Lines Modified", f"{total_modified:,}")
    with col4:
        net_churn = total_added - total_deleted
        st.metric("Net Churn", f"{net_churn:+,}")


def render_contributors_tab(git_data: Dict[str, Any]):
    """Render the contributors tab."""
    st.markdown("### 👥 Contributor Analysis")

    # Chart type selector
    chart_type = st.selectbox(
        "Chart Type",
        ["Pie Chart", "Bar Chart", "Treemap"],
        index=0,
    )

    type_map = {"Pie Chart": "pie", "Bar Chart": "bar", "Treemap": "treemap"}

    render_author_contributions(
        git_data["contributors"],
        chart_type=type_map[chart_type],
        height=400,
    )

    # Contributors table
    st.markdown("### 📋 Contributor Details")
    import pandas as pd

    df = pd.DataFrame(git_data["contributors"])
    if not df.empty:
        df = df.sort_values("commits", ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_bug_files_tab(git_data: Dict[str, Any]):
    """Render the bug-prone files tab."""
    st.markdown("### 🐛 Bug-Prone Files")
    st.markdown("Files with high bug fix commit ratio")

    # Filter options
    col1, col2 = st.columns([2, 1])
    with col1:
        min_bug_ratio = st.slider("Min Bug Ratio (%)", 0, 50, 10) / 100
    with col2:
        if st.button("🔄 Refresh", use_container_width=True, key="refresh_bug_files"):
            st.rerun()

    # Filter files
    filtered_files = [
        f for f in git_data["bug_prone_files"] if f["bug_ratio"] >= min_bug_ratio
    ]

    if filtered_files:
        render_bug_prone_files(filtered_files, max_files=30)
    else:
        st.info("No bug-prone files found matching criteria")

    # Insights
    st.markdown("### 💡 Insights")

    high_risk = [f for f in filtered_files if f["bug_ratio"] >= 0.3]
    if high_risk:
        st.warning(f"Found {len(high_risk)} high-risk files (≥30% bug ratio)")
        st.markdown("Consider refactoring these files or adding more tests.")
    else:
        st.success("No high-risk files found. Good job!")


def render_activity_tab(git_data: Dict[str, Any]):
    """Render the activity calendar tab."""
    st.markdown("### 📅 Commit Activity")

    render_commit_activity_calendar(git_data["commit_activity"], height=200)

    # Activity patterns
    st.markdown("### 📊 Activity Patterns")

    # Calculate patterns
    weekday_activity = {}
    for entry in git_data["commit_activity"]:
        date = datetime.fromisoformat(entry["date"])
        weekday = date.strftime("%A")
        weekday_activity[weekday] = weekday_activity.get(weekday, 0) + entry["commits"]

    # Display as bar chart
    import plotly.express as px
    from mike.web.theme_utils import apply_chart_theme, get_current_theme

    theme = get_current_theme()

    weekday_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    weekdays = [d for d in weekday_order if d in weekday_activity]
    commits = [weekday_activity[d] for d in weekdays]

    fig = px.bar(
        x=weekdays,
        y=commits,
        title="Commits by Day of Week",
        labels={"x": "Day", "y": "Commits"},
    )
    fig = apply_chart_theme(fig, theme)
    st.plotly_chart(fig, use_container_width=True)

    # Most active day
    if weekday_activity:
        most_active = max(weekday_activity.items(), key=lambda x: x[1])
        st.info(f"📈 Most active day: **{most_active[0]}** ({most_active[1]} commits)")


def _generate_sample_git_data() -> Dict[str, Any]:
    """Generate sample git analytics data."""
    import random

    # Hotspots
    hotspots = []
    sample_files = [
        "src/main.py",
        "src/utils.py",
        "src/models.py",
        "src/api.py",
        "tests/test_main.py",
        "config.py",
        "requirements.txt",
        "src/services/auth.py",
        "src/services/database.py",
        "src/controllers/user.py",
        "src/controllers/product.py",
        "src/views/index.html",
        "src/static/app.js",
        "src/static/style.css",
    ]

    for file_path in sample_files:
        hotspots.append(
            {
                "file": file_path,
                "commits": random.randint(5, 100),
                "complexity": random.randint(1, 50),
                "churn": random.uniform(0, 1),
            }
        )

    # Churn data (monthly)
    churn = []
    base_date = datetime.now() - timedelta(days=365)
    for i in range(12):
        date = base_date + timedelta(days=i * 30)
        churn.append(
            {
                "date": date.isoformat(),
                "added": random.randint(100, 1000),
                "deleted": random.randint(50, 500),
                "modified": random.randint(100, 800),
                "net_churn": random.randint(-200, 500),
            }
        )

    # Contributors
    contributors = [
        {
            "author": "Alice Johnson",
            "commits": 245,
            "additions": 12500,
            "deletions": 3200,
            "files": 45,
        },
        {
            "author": "Bob Smith",
            "commits": 189,
            "additions": 8900,
            "deletions": 2100,
            "files": 38,
        },
        {
            "author": "Carol White",
            "commits": 156,
            "additions": 7600,
            "deletions": 1800,
            "files": 32,
        },
        {
            "author": "David Brown",
            "commits": 134,
            "additions": 6200,
            "deletions": 1500,
            "files": 28,
        },
        {
            "author": "Eve Davis",
            "commits": 98,
            "additions": 4500,
            "deletions": 1100,
            "files": 22,
        },
    ]

    # Bug-prone files
    bug_prone_files = []
    for file_path in sample_files[:10]:
        total_commits = random.randint(10, 80)
        bug_commits = int(total_commits * random.uniform(0.05, 0.4))
        bug_prone_files.append(
            {
                "path": file_path,
                "bug_commits": bug_commits,
                "total_commits": total_commits,
                "bug_ratio": bug_commits / total_commits if total_commits > 0 else 0,
                "last_bug_date": (
                    datetime.now() - timedelta(days=random.randint(0, 90))
                ).isoformat(),
            }
        )

    # Rework rate
    rework_rate = []
    for i in range(12):
        date = base_date + timedelta(days=i * 30)
        total = random.randint(20, 100)
        rework = int(total * random.uniform(0.1, 0.3))
        rework_rate.append(
            {
                "date": date.isoformat(),
                "rework_rate": (rework / total * 100) if total > 0 else 0,
                "total_commits": total,
                "rework_commits": rework,
            }
        )

    # Commit activity (daily for last 90 days)
    commit_activity = []
    for i in range(90):
        date = datetime.now() - timedelta(days=i)
        commit_activity.append(
            {
                "date": date.isoformat(),
                "commits": random.randint(0, 10),
                "authors": random.randint(1, 5),
            }
        )

    return {
        "total_commits": sum(c["commits"] for c in contributors),
        "total_authors": len(contributors),
        "avg_commits_per_week": sum(c["commits"] for c in contributors) / 52,
        "active_branches": random.randint(3, 15),
        "time_range": "Last 12 months",
        "hotspots": hotspots,
        "churn": churn,
        "contributors": contributors,
        "bug_prone_files": bug_prone_files,
        "rework_rate": rework_rate,
        "commit_activity": commit_activity,
    }


# Page entry point
if __name__ == "__main__":
    render_git_analytics()
