"""Reusable UI components for the ArchitectAI Streamlit frontend.

Provides components for rendering sessions, file trees, progress indicators,
agent results, and visualizations.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import networkx as nx
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from .utils import format_file_size, format_timestamp, get_log_level_color


def render_session_card(
    session: Dict[str, Any],
    is_active: bool = False,
    on_select: Optional[Callable] = None,
    on_delete: Optional[Callable] = None,
) -> None:
    """Render a session card with key information."""
    session_id = session.get("session_id", session.get("id", "unknown"))
    source_path = session.get("source_path", "Unknown")
    created_at = session.get("created_at", "Unknown")
    status = session.get("status", "unknown")

    # Card container
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            # Session name and path
            display_name = (
                Path(source_path).name if source_path != "Unknown" else "Unknown"
            )
            st.markdown(f"**{display_name}**")
            st.caption(f"📁 `{source_path}`")
            st.caption(f"🕐 {format_timestamp(created_at)}")

        with col2:
            # Status badge
            status_colors = {
                "active": "🟢",
                "processing": "🟡",
                "completed": "✅",
                "failed": "❌",
                "archived": "⚪",
            }
            status_icon = status_colors.get(status, "⚪")
            st.markdown(f"{status_icon} **{status.title()}**")

            if is_active:
                st.markdown("🔵 **Current**")

        with col3:
            # Actions
            if on_select:
                if st.button(
                    "Load", key=f"load_{session_id}", use_container_width=True
                ):
                    on_select(session_id)

            if on_delete:
                if st.button("🗑️", key=f"delete_{session_id}", help="Delete session"):
                    on_delete(session_id)

        st.divider()


def render_file_tree(
    files: List[Dict[str, Any]],
    on_file_select: Optional[Callable[[str], None]] = None,
    max_depth: int = 5,
) -> None:
    """Render an interactive file tree."""
    if not files:
        st.info("No files to display")
        return

    # Build tree structure
    tree: Dict[str, Any] = {}

    for file_info in files:
        rel_path = file_info.get("relative_path", "")
        parts = Path(rel_path).parts

        current = tree
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                # File
                current[part] = {"__file__": file_info}
            else:
                # Directory
                if part not in current:
                    current[part] = {}
                current = current[part]

    # Render tree
    def render_node(
        node: Dict[str, Any], name: str, depth: int = 0, path: str = ""
    ) -> None:
        if depth > max_depth:
            return

        indent = "  " * depth
        current_path = f"{path}/{name}" if path else name

        if "__file__" in node:
            # It's a file
            file_info = node["__file__"]
            lang = file_info.get("language", "unknown")
            lines = file_info.get("line_count", 0)
            size = format_file_size(file_info.get("size_bytes", 0))

            col1, col2 = st.columns([4, 1])
            with col1:
                if on_file_select:
                    if st.button(
                        f"{indent}📄 {name}",
                        key=f"file_{current_path}",
                        help=f"{lang} • {lines} lines • {size}",
                    ):
                        on_file_select(file_info.get("absolute_path", ""))
                else:
                    st.text(f"{indent}📄 {name}")

            with col2:
                st.caption(f"{lines} lines")
        else:
            # It's a directory
            with st.expander(f"{indent}📁 {name}/", expanded=depth < 2):
                for child_name, child_node in sorted(node.items()):
                    render_node(child_node, child_name, depth + 1, current_path)

    # Render root nodes
    for name, node in sorted(tree.items()):
        render_node(node, name)


def render_progress_bar(
    progress: float,
    message: str = "",
    status: str = "running",
) -> None:
    """Render a progress bar with status."""
    col1, col2 = st.columns([4, 1])

    with col1:
        st.progress(min(max(progress, 0.0), 1.0))

    with col2:
        status_icons = {
            "pending": "⏳",
            "running": "🔄",
            "completed": "✅",
            "failed": "❌",
            "cancelled": "🚫",
        }
        icon = status_icons.get(status, "⏳")
        st.markdown(f"{icon} **{status.title()}**")

    if message:
        st.caption(message)


def render_agent_result(
    result: Dict[str, Any],
    agent_type: str,
    expanded: bool = False,
) -> None:
    """Render agent execution result."""
    status = result.get("status", "unknown")
    message = result.get("message", "")

    # Header
    status_icons = {
        "success": "✅",
        "completed": "✅",
        "failed": "❌",
        "error": "❌",
        "running": "🔄",
        "pending": "⏳",
    }
    icon = status_icons.get(status, "📄")

    with st.expander(f"{icon} {agent_type.title()} Result", expanded=expanded):
        st.markdown(f"**Status:** {status.title()}")

        if message:
            st.markdown(f"**Message:** {message}")

        # Show result data
        result_data = result.get("result", {})
        if result_data:
            st.markdown("**Result:**")
            st.json(result_data)

        # Show error if any
        error = result.get("error")
        if error:
            st.error(f"**Error:** {error}")


def render_dependency_graph(
    edges: List[Dict[str, str]],
    height: int = 600,
) -> None:
    """Render an interactive dependency graph using Plotly."""
    if not edges:
        st.info("No dependency data available")
        return

    # Build NetworkX graph
    G = nx.DiGraph()

    for edge in edges:
        source = edge.get("source_file", edge.get("source", ""))
        target = edge.get("target_file", edge.get("target", ""))
        edge_type = edge.get("edge_type", "depends_on")

        if source and target:
            G.add_edge(source, target, type=edge_type)

    if len(G.nodes()) == 0:
        st.info("No valid dependencies to display")
        return

    # Calculate layout
    pos = nx.spring_layout(G, k=2, iterations=50)

    # Create edges
    edge_x = []
    edge_y = []
    edge_colors = []

    edge_type_colors = {
        "import": "#2ecc71",
        "call": "#3498db",
        "inheritance": "#9b59b6",
        "depends_on": "#95a5a6",
    }

    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

        edge_type = edge[2].get("type", "depends_on")
        edge_colors.append(edge_type_colors.get(edge_type, "#95a5a6"))

    # Create nodes
    node_x = []
    node_y = []
    node_text = []
    node_sizes = []

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)
        # Size based on degree
        degree = G.degree(node)
        node_sizes.append(20 + degree * 5)

    # Create figure
    fig = go.Figure()

    # Add edges
    fig.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line=dict(width=1, color="#95a5a6"),
            hoverinfo="none",
        )
    )

    # Add nodes
    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            marker=dict(
                size=node_sizes,
                color="#3498db",
                line=dict(width=2, color="#2980b9"),
            ),
            text=node_text,
            textposition="top center",
            textfont=dict(size=8),
            hovertemplate="%{text}<br>Connections: %{marker.size}<extra></extra>",
        )
    )

    fig.update_layout(
        showlegend=False,
        hovermode="closest",
        margin=dict(b=20, l=5, r=5, t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=height,
        title="Dependency Graph",
    )

    st.plotly_chart(fig, use_container_width=True)


def render_metrics_cards(metrics: Dict[str, Any]) -> None:
    """Render metric cards in a grid."""
    cols = st.columns(4)

    metric_items = [
        ("Files", metrics.get("file_count", 0), "📄"),
        ("Lines of Code", metrics.get("total_lines", 0), "📝"),
        ("Languages", len(metrics.get("languages", {})), "🌐"),
        ("Parsed", metrics.get("parsed_count", 0), "🔍"),
    ]

    for i, (label, value, icon) in enumerate(metric_items):
        with cols[i]:
            st.metric(label=f"{icon} {label}", value=value)


def render_language_chart(languages: Dict[str, int]) -> None:
    """Render a pie chart of language distribution."""
    if not languages:
        st.info("No language data available")
        return

    # Sort by count
    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)

    # Take top 8, group rest as "Other"
    if len(sorted_langs) > 8:
        top_langs = sorted_langs[:8]
        other_count = sum(count for _, count in sorted_langs[8:])
        sorted_langs = top_langs + [("Other", other_count)]

    labels = [lang for lang, _ in sorted_langs]
    values = [count for _, count in sorted_langs]

    fig = px.pie(
        names=labels,
        values=values,
        title="Language Distribution",
        hole=0.4,
    )

    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(height=400)

    st.plotly_chart(fig, use_container_width=True)


def render_file_size_chart(files: List[Dict[str, Any]]) -> None:
    """Render a bar chart of file sizes by extension."""
    if not files:
        st.info("No file data available")
        return

    # Group by extension
    ext_sizes: Dict[str, int] = {}
    for file_info in files:
        ext = file_info.get("extension", ".unknown")
        size = file_info.get("size_bytes", 0)
        ext_sizes[ext] = ext_sizes.get(ext, 0) + size

    # Sort by size
    sorted_exts = sorted(ext_sizes.items(), key=lambda x: x[1], reverse=True)[:10]

    exts = [ext for ext, _ in sorted_exts]
    sizes = [size / (1024 * 1024) for _, size in sorted_exts]  # Convert to MB

    fig = px.bar(
        x=exts,
        y=sizes,
        title="File Size by Extension (Top 10)",
        labels={"x": "Extension", "y": "Size (MB)"},
    )

    fig.update_layout(height=400)

    st.plotly_chart(fig, use_container_width=True)


def render_log_viewer(
    logs: List[Dict[str, Any]],
    max_height: int = 400,
    filter_level: Optional[str] = None,
) -> None:
    """Render a scrollable log viewer."""
    if not logs:
        st.info("No logs available")
        return

    # Filter logs
    if filter_level:
        logs = [
            log for log in logs if log.get("level", "").lower() == filter_level.lower()
        ]

    # Show latest first
    logs = list(reversed(logs))

    # Create log display
    log_html = '<div style="font-family: monospace; font-size: 12px; max-height: {}px; overflow-y: auto; background-color: #1e1e1e; padding: 10px; border-radius: 5px;">'.format(
        max_height
    )

    for log in logs:
        timestamp = format_timestamp(log.get("timestamp"))
        level = log.get("level", "info").upper()
        message = log.get("message", "")

        # Escape HTML
        message = message.replace("<", "&lt;").replace(">", "&gt;")

        level_colors = {
            "DEBUG": "#6c757d",
            "INFO": "#0dcaf0",
            "WARNING": "#ffc107",
            "ERROR": "#dc3545",
            "SUCCESS": "#198754",
        }
        color = level_colors.get(level, "#6c757d")

        log_html += f'<div style="margin-bottom: 4px;"><span style="color: #6c757d;">[{timestamp}]</span> <span style="color: {color}; font-weight: bold;">{level}</span> {message}</div>'

    log_html += "</div>"

    st.markdown(log_html, unsafe_allow_html=True)


def render_code_viewer(
    file_path: str,
    content: Optional[str] = None,
    language: Optional[str] = None,
    height: int = 600,
) -> None:
    """Render a code viewer with syntax highlighting."""
    try:
        if content is None and file_path:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

        if not content:
            st.info("No content to display")
            return

        # Detect language from extension
        if language is None:
            ext = Path(file_path).suffix.lower()
            ext_to_lang = {
                ".py": "python",
                ".js": "javascript",
                ".ts": "typescript",
                ".jsx": "javascript",
                ".tsx": "typescript",
                ".java": "java",
                ".go": "go",
                ".rs": "rust",
                ".c": "c",
                ".cpp": "cpp",
                ".h": "c",
                ".hpp": "cpp",
                ".rb": "ruby",
                ".php": "php",
                ".swift": "swift",
                ".kt": "kotlin",
                ".scala": "scala",
                ".cs": "csharp",
                ".lua": "lua",
                ".sh": "bash",
                ".sql": "sql",
                ".html": "html",
                ".css": "css",
                ".json": "json",
                ".xml": "xml",
                ".yaml": "yaml",
                ".yml": "yaml",
                ".md": "markdown",
            }
            language = ext_to_lang.get(ext, "text")

        # Use streamlit-ace if available, otherwise fallback to code block
        try:
            from streamlit_ace import st_ace

            st_ace(
                value=content,
                language=language,
                theme="monokai",
                height=height,
                readonly=True,
                show_gutter=True,
                key=f"code_viewer_{file_path}",
            )
        except ImportError:
            # Fallback to streamlit code block
            st.code(content, language=language)

    except Exception as e:
        st.error(f"Error loading file: {e}")


def render_timeline_chart(executions: List[Dict[str, Any]]) -> None:
    """Render a timeline chart of agent executions."""
    if not executions:
        st.info("No execution data available")
        return

    # Prepare data
    data = []
    for exec_info in executions:
        agent_type = exec_info.get("agent_type", "unknown")
        status = exec_info.get("status", "unknown")
        start = exec_info.get("started_at") or exec_info.get("created_at")
        end = exec_info.get("completed_at")

        if start and end:
            try:
                start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                duration = (end_dt - start_dt).total_seconds() / 60  # minutes

                data.append(
                    {
                        "agent": agent_type,
                        "status": status,
                        "start": start_dt,
                        "duration": duration,
                    }
                )
            except Exception:
                pass

    if not data:
        st.info("No valid timeline data")
        return

    fig = px.timeline(
        data,
        x_start="start",
        x_end=[
            d["start"] + __import__("datetime").timedelta(minutes=d["duration"])
            for d in data
        ],
        y="agent",
        color="status",
        title="Agent Execution Timeline",
    )

    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)
