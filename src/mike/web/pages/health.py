"""Health Dashboard page for Mike v2 Phase 1.

Provides architecture health score display, dimension breakdown,
trend charts, and file-level score analysis.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

import streamlit as st

from mike.web.components.health_score import (
    render_dimension_breakdown,
    render_file_level_scores,
    render_health_score_gauge,
    render_health_summary_card,
    render_health_trend_chart,
)
from mike.web.utils import format_timestamp, get_db_path


def render_health_dashboard():
    """Render the health dashboard page."""
    st.title("🏥 Health Dashboard")
    st.markdown("Analyze your codebase architecture health and quality metrics")

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

    # Generate sample health data (in real implementation, fetch from backend)
    health_data = _generate_sample_health_data()

    # Summary card
    render_health_summary_card(
        overall_score=health_data["overall_score"],
        files_analyzed=health_data["files_analyzed"],
        issues_found=health_data["issues_found"],
        last_scan=health_data["last_scan"],
    )

    # Main layout
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### Overall Health Score")
        render_health_score_gauge(
            score=health_data["overall_score"],
            title="Architecture Health",
            size="large",
            show_details=True,
        )

    with col2:
        render_dimension_breakdown(
            dimensions=health_data["dimensions"],
            show_trends=True,
        )

    st.divider()

    # Trend chart
    st.markdown("### 📈 Health Trends")
    render_health_trend_chart(
        history=health_data["history"],
        height=400,
    )

    st.divider()

    # File-level scores
    st.markdown("### 📁 File-Level Analysis")

    # Filter options
    filter_cols = st.columns([2, 2, 1])
    with filter_cols[0]:
        min_score = st.slider("Min Score", 0, 100, 0)
    with filter_cols[1]:
        sort_by = st.selectbox(
            "Sort By",
            ["Score (Lowest)", "Score (Highest)", "Issues Count", "Last Analyzed"],
        )
    with filter_cols[2]:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    # Filter and sort files
    filtered_files = [f for f in health_data["file_scores"] if f["score"] >= min_score]

    if sort_by == "Score (Lowest)":
        filtered_files.sort(key=lambda x: x["score"])
    elif sort_by == "Score (Highest)":
        filtered_files.sort(key=lambda x: x["score"], reverse=True)
    elif sort_by == "Issues Count":
        filtered_files.sort(key=lambda x: x["issues_count"], reverse=True)
    elif sort_by == "Last Analyzed":
        filtered_files.sort(key=lambda x: x["last_analyzed"], reverse=True)

    render_file_level_scores(filtered_files, max_files=50)

    st.divider()

    # Actions
    st.markdown("### 🚀 Actions")

    action_cols = st.columns(3)
    with action_cols[0]:
        if st.button("🔍 Run Health Check", use_container_width=True):
            with st.spinner("Analyzing codebase health..."):
                # In real implementation: call backend API
                st.success("Health check completed!")
                st.rerun()

    with action_cols[1]:
        if st.button("📊 Export Report", use_container_width=True):
            # Generate report
            report_data = _generate_health_report(health_data)
            st.download_button(
                label="Download JSON",
                data=report_data,
                file_name=f"health_report_{session_id[:8]}.json",
                mime="application/json",
                use_container_width=True,
            )

    with action_cols[2]:
        if st.button("🔧 Fix Issues", use_container_width=True):
            st.info("Navigate to Patch Manager to apply fixes")
            st.session_state.current_page = "patch"
            st.rerun()


def _generate_sample_health_data() -> Dict[str, Any]:
    """Generate sample health data for demonstration."""
    import random

    # Dimensions
    dimensions = {
        "Coupling": {
            "score": random.uniform(60, 85),
            "weight": 20,
            "trend": random.uniform(-5, 10),
            "description": "Inter-module dependencies",
        },
        "Cohesion": {
            "score": random.uniform(70, 90),
            "weight": 20,
            "trend": random.uniform(-3, 5),
            "description": "Module internal consistency",
        },
        "Complexity": {
            "score": random.uniform(50, 75),
            "weight": 25,
            "trend": random.uniform(-10, 5),
            "description": "Cyclomatic complexity",
        },
        "Maintainability": {
            "score": random.uniform(65, 80),
            "weight": 20,
            "trend": random.uniform(-2, 8),
            "description": "Code maintainability index",
        },
        "Test Coverage": {
            "score": random.uniform(40, 70),
            "weight": 15,
            "trend": random.uniform(-5, 15),
            "description": "Unit test coverage",
        },
    }

    # Calculate overall score
    overall_score = sum(d["score"] * (d["weight"] / 100) for d in dimensions.values())

    # Historical data
    history = []
    base_date = datetime.now() - timedelta(days=90)
    for i in range(12):
        date = base_date + timedelta(days=i * 7)
        score_variation = random.uniform(-5, 5)
        history.append(
            {
                "timestamp": date.isoformat(),
                "score": max(0, min(100, overall_score + score_variation)),
                "dimensions": {
                    name: max(0, min(100, data["score"] + random.uniform(-5, 5)))
                    for name, data in dimensions.items()
                },
            }
        )

    # File scores
    file_scores = []
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
    ]

    for file_path in sample_files:
        score = random.uniform(30, 95)
        issues = int((100 - score) / 10) + random.randint(0, 3)
        file_scores.append(
            {
                "path": file_path,
                "score": score,
                "issues_count": issues,
                "last_analyzed": (
                    datetime.now() - timedelta(days=random.randint(0, 7))
                ).isoformat(),
            }
        )

    return {
        "overall_score": overall_score,
        "files_analyzed": len(sample_files),
        "issues_found": sum(f["issues_count"] for f in file_scores),
        "last_scan": format_timestamp(datetime.now().isoformat()),
        "dimensions": dimensions,
        "history": history,
        "file_scores": file_scores,
    }


def _generate_health_report(health_data: Dict[str, Any]) -> str:
    """Generate a health report as JSON string."""
    import json

    report = {
        "generated_at": datetime.now().isoformat(),
        "overall_score": health_data["overall_score"],
        "dimensions": health_data["dimensions"],
        "files_analyzed": health_data["files_analyzed"],
        "issues_found": health_data["issues_found"],
        "recommendations": _generate_recommendations(health_data),
    }

    return json.dumps(report, indent=2)


def _generate_recommendations(health_data: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on health data."""
    recommendations = []

    for dim_name, dim_data in health_data["dimensions"].items():
        if dim_data["score"] < 60:
            recommendations.append(
                f"Improve {dim_name}: Score is {dim_data['score']:.1f}% (below threshold)"
            )

    # Add general recommendations
    low_score_files = [f for f in health_data["file_scores"] if f["score"] < 50]
    if low_score_files:
        recommendations.append(
            f"Refactor {len(low_score_files)} files with low health scores"
        )

    if not recommendations:
        recommendations.append("Codebase health is good! Keep up the good work.")

    return recommendations


# Page entry point
if __name__ == "__main__":
    render_health_dashboard()
