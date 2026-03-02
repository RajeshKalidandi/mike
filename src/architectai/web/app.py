"""Main Streamlit application for ArchitectAI.

Provides a multi-page web interface for:
- Home: System overview and quick stats
- Upload: File and repository upload
- Sessions: Session management
- Analysis: Agent execution and results
- Visualizations: Dependency graphs and metrics
- Settings: Configuration management
"""

from __future__ import annotations

import io
import os
import sqlite3
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import streamlit as st

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from architectai.cli_orchestrator import Orchestrator, TaskProgress
from architectai.db.models import Database
from architectai.scanner.scanner import FileScanner
from architectai.web.components import (
    render_agent_result,
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
from architectai.web.utils import (
    add_log,
    format_duration,
    format_file_size,
    format_timestamp,
    get_db_path,
    get_language_distribution,
    init_session_state,
    load_settings,
    save_settings,
    scan_directory_for_upload,
)

# Page configuration
st.set_page_config(
    page_title="ArchitectAI",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
init_session_state()

# Custom CSS
st.markdown(
    """
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .log-container {
        background-color: #1e1e1e;
        color: #ffffff;
        padding: 1rem;
        border-radius: 5px;
        font-family: monospace;
        max-height: 400px;
        overflow-y: auto;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# Sidebar navigation
def render_sidebar():
    """Render the sidebar navigation."""
    with st.sidebar:
        st.title("🏗️ ArchitectAI")
        st.caption("Local AI Software Architect")

        st.divider()

        # Navigation
        pages = {
            "home": "🏠 Home",
            "upload": "📤 Upload",
            "sessions": "📁 Sessions",
            "analysis": "🔍 Analysis",
            "visualizations": "📊 Visualizations",
            "settings": "⚙️ Settings",
        }

        for key, label in pages.items():
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.current_page = key
                st.rerun()

        st.divider()

        # Current session info
        if st.session_state.current_session_id:
            st.markdown("### Current Session")
            st.markdown(f"**ID:** `{st.session_state.current_session_id[:8]}`")
            if st.session_state.current_session_name:
                st.markdown(f"**Name:** {st.session_state.current_session_name}")

            if st.button("Clear Session", key="clear_session"):
                st.session_state.current_session_id = None
                st.session_state.current_session_name = None
                st.rerun()
        else:
            st.info("No active session")

        st.divider()

        # System status
        with st.expander("System Status"):
            try:
                db_path = get_db_path()
                orchestrator = Orchestrator(db_path)
                status = orchestrator.get_system_status()

                st.markdown(f"**Version:** {status.get('version', 'Unknown')}")
                st.markdown(f"**Sessions:** {status.get('session_count', 0)}")

                # Agent status
                st.markdown("**Agents:**")
                for agent_name, agent_info in status.get("agents", {}).items():
                    status_icon = (
                        "🟢" if agent_info.get("status") == "available" else "🔴"
                    )
                    st.markdown(f"{status_icon} {agent_name}")
            except Exception as e:
                st.error(f"Error: {e}")


def render_home():
    """Render the home page."""
    st.title("🏠 Welcome to ArchitectAI")

    st.markdown(
        """
        ### Local AI Software Architect
        
        ArchitectAI is a fully local, offline-capable AI system that ingests any codebase
        and produces:
        
        - 📚 **Detailed documentation** - Human-readable docs at every level
        - 🗺️ **Architecture overviews** - Dependency maps and structure analysis
        - ❓ **Q&A over codebases** - Natural language queries about your code
        - 🔧 **Refactor suggestions** - Code smell detection and improvements
        - 🏗️ **Project scaffolding** - Generate new projects from templates
        
        **No third-party APIs. No code leaves your machine.**
        """
    )

    st.divider()

    # Quick stats
    st.markdown("### 📊 System Overview")

    try:
        db_path = get_db_path()
        orchestrator = Orchestrator(db_path)
        status = orchestrator.get_system_status()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Sessions", status.get("session_count", 0))

        with col2:
            available_agents = sum(
                1
                for a in status.get("agents", {}).values()
                if a.get("status") == "available"
            )
            st.metric("Available Agents", available_agents)

        with col3:
            st.metric("Database", "✅" if status.get("database_exists") else "❌")

        with col4:
            st.metric("Version", status.get("version", "Unknown"))

    except Exception as e:
        st.error(f"Error loading system status: {e}")

    st.divider()

    # Quick actions
    st.markdown("### 🚀 Quick Actions")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Get Started**")
        if st.button("📤 Upload Codebase", use_container_width=True):
            st.session_state.current_page = "upload"
            st.rerun()

    with col2:
        st.markdown("**Existing Work**")
        if st.button("📁 View Sessions", use_container_width=True):
            st.session_state.current_page = "sessions"
            st.rerun()

    with col3:
        st.markdown("**Configuration**")
        if st.button("⚙️ Settings", use_container_width=True):
            st.session_state.current_page = "settings"
            st.rerun()

    st.divider()

    # Recent activity
    st.markdown("### 📋 Recent Activity")

    try:
        db_path = get_db_path()
        orchestrator = Orchestrator(db_path)
        sessions = orchestrator.list_sessions()[:5]

        if sessions:
            for session in sessions:
                render_session_card(
                    {
                        "session_id": session.session_id,
                        "source_path": session.source_path,
                        "created_at": session.created_at,
                        "status": session.status,
                    },
                    is_active=(
                        session.session_id == st.session_state.current_session_id
                    ),
                )
        else:
            st.info("No sessions yet. Upload a codebase to get started!")

    except Exception as e:
        st.error(f"Error loading recent sessions: {e}")


def render_upload():
    """Render the upload page."""
    st.title("📤 Upload Codebase")

    st.markdown(
        """
        Upload a codebase for analysis. You can upload:
        - 📁 A local directory
        - 📦 A ZIP file containing your project
        - 🔗 A Git repository URL (coming soon)
        """
    )

    tab1, tab2 = st.tabs(["📁 Local Directory", "📦 ZIP File"])

    with tab1:
        st.markdown("### Upload from Local Directory")

        upload_path = st.text_input(
            "Directory Path",
            placeholder="/path/to/your/project",
            help="Enter the absolute path to your project directory",
        )

        session_name = st.text_input(
            "Session Name (Optional)",
            placeholder="My Project",
            help="Give your session a memorable name",
        )

        col1, col2 = st.columns([1, 4])
        with col1:
            scan_button = st.button("🔍 Scan Directory", use_container_width=True)

        if scan_button and upload_path:
            path = Path(upload_path)
            if not path.exists():
                st.error(f"Path does not exist: {upload_path}")
            elif not path.is_dir():
                st.error(f"Path is not a directory: {upload_path}")
            else:
                with st.spinner("Scanning directory..."):
                    try:
                        # Scan files
                        progress_bar = st.progress(0)
                        files_scanned = [0]

                        def progress_callback(count):
                            files_scanned[0] = count
                            progress_bar.progress(min(count / 100, 0.99))

                        files, total_size = scan_directory_for_upload(
                            path, progress_callback
                        )
                        progress_bar.progress(1.0)

                        st.success(
                            f"Found {len(files)} files ({format_file_size(total_size)})"
                        )

                        # Show file preview
                        with st.expander("Preview Files", expanded=True):
                            file_data = []
                            for f in files[:50]:  # Show first 50
                                file_data.append(
                                    {
                                        "Path": f["relative_path"],
                                        "Size": format_file_size(f["size_bytes"]),
                                        "Lines": f["line_count"],
                                    }
                                )

                            df = pd.DataFrame(file_data)
                            st.dataframe(df, use_container_width=True)

                            if len(files) > 50:
                                st.caption(f"... and {len(files) - 50} more files")

                        # Create session
                        if st.button("✅ Create Session", use_container_width=True):
                            with st.spinner("Creating session..."):
                                try:
                                    db_path = get_db_path()
                                    db = Database(db_path)
                                    db.init()

                                    # Calculate content hash
                                    file_paths = [
                                        Path(f["absolute_path"]) for f in files
                                    ]
                                    from architectai.web.utils import (
                                        calculate_content_hash,
                                    )

                                    content_hash = calculate_content_hash(file_paths)

                                    # Check for existing session
                                    existing_session = db.check_content_hash_exists(
                                        content_hash
                                    )
                                    if existing_session:
                                        st.warning(
                                            f"Session already exists for this codebase: {existing_session[:8]}"
                                        )
                                        if st.button("Load Existing Session"):
                                            st.session_state.current_session_id = (
                                                existing_session
                                            )
                                            st.session_state.current_session_name = (
                                                session_name or path.name
                                            )
                                            st.success("Session loaded!")
                                            st.rerun()
                                    else:
                                        # Create new session
                                        session_id = db.create_session(
                                            source_path=str(path),
                                            session_type="local",
                                            content_hash=content_hash,
                                        )

                                        # Insert file records
                                        for file_info in files:
                                            db.insert_file(
                                                session_id=session_id,
                                                relative_path=file_info[
                                                    "relative_path"
                                                ],
                                                absolute_path=file_info[
                                                    "absolute_path"
                                                ],
                                                language=file_info.get("extension", "")
                                                .replace(".", "")
                                                .upper(),
                                                size_bytes=file_info["size_bytes"],
                                                line_count=file_info["line_count"],
                                                content_hash="",  # Would calculate per file
                                            )

                                        # Store code hash
                                        conn = sqlite3.connect(db_path)
                                        cursor = conn.cursor()
                                        cursor.execute(
                                            """
                                            INSERT INTO code_hashes (hash, session_id, file_count, total_lines)
                                            VALUES (?, ?, ?, ?)
                                            """,
                                            (
                                                content_hash,
                                                session_id,
                                                len(files),
                                                sum(f["line_count"] for f in files),
                                            ),
                                        )
                                        conn.commit()
                                        conn.close()

                                        st.session_state.current_session_id = session_id
                                        st.session_state.current_session_name = (
                                            session_name or path.name
                                        )

                                        st.success(f"Session created: {session_id[:8]}")
                                        add_log(
                                            f"Created session {session_id[:8]} from {path}",
                                            "success",
                                        )
                                        st.rerun()

                                except Exception as e:
                                    st.error(f"Error creating session: {e}")
                                    add_log(f"Error creating session: {e}", "error")

                    except Exception as e:
                        st.error(f"Error scanning directory: {e}")

    with tab2:
        st.markdown("### Upload from ZIP File")

        uploaded_file = st.file_uploader(
            "Choose a ZIP file",
            type=["zip"],
            help="Upload a ZIP archive of your codebase",
        )

        if uploaded_file:
            st.success(
                f"Uploaded: {uploaded_file.name} ({format_file_size(len(uploaded_file.getvalue()))})"
            )

            if st.button("📦 Extract and Create Session", use_container_width=True):
                with st.spinner("Extracting and processing..."):
                    try:
                        # Extract to temp directory
                        temp_dir = Path("/tmp/architectai_upload")
                        temp_dir.mkdir(parents=True, exist_ok=True)

                        with zipfile.ZipFile(
                            io.BytesIO(uploaded_file.getvalue())
                        ) as zf:
                            zf.extractall(temp_dir)

                        # Find root directory
                        extracted_dirs = [d for d in temp_dir.iterdir() if d.is_dir()]
                        if extracted_dirs:
                            root_dir = extracted_dirs[0]
                        else:
                            root_dir = temp_dir

                        st.success(f"Extracted to: {root_dir}")

                        # Now scan this directory
                        files, total_size = scan_directory_for_upload(root_dir)

                        st.success(
                            f"Found {len(files)} files ({format_file_size(total_size)})"
                        )

                        # Create session (similar to above)
                        db_path = get_db_path()
                        db = Database(db_path)
                        db.init()

                        file_paths = [Path(f["absolute_path"]) for f in files]
                        from architectai.web.utils import calculate_content_hash

                        content_hash = calculate_content_hash(file_paths)

                        session_id = db.create_session(
                            source_path=f"zip:{uploaded_file.name}",
                            session_type="zip",
                            content_hash=content_hash,
                        )

                        for file_info in files:
                            db.insert_file(
                                session_id=session_id,
                                relative_path=file_info["relative_path"],
                                absolute_path=file_info["absolute_path"],
                                language=file_info.get("extension", "")
                                .replace(".", "")
                                .upper(),
                                size_bytes=file_info["size_bytes"],
                                line_count=file_info["line_count"],
                                content_hash="",
                            )

                        st.session_state.current_session_id = session_id
                        st.session_state.current_session_name = (
                            uploaded_file.name.replace(".zip", "")
                        )

                        st.success(f"Session created: {session_id[:8]}")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error processing ZIP: {e}")


def render_sessions():
    """Render the sessions page."""
    st.title("📁 Session Management")

    # Load sessions
    try:
        db_path = get_db_path()
        orchestrator = Orchestrator(db_path)
        sessions = orchestrator.list_sessions()

        if not sessions:
            st.info("No sessions yet. Upload a codebase to get started!")

            if st.button("📤 Upload Codebase", use_container_width=True):
                st.session_state.current_page = "upload"
                st.rerun()
            return

        # Session filter
        col1, col2 = st.columns([3, 1])
        with col1:
            filter_text = st.text_input(
                "🔍 Filter sessions", placeholder="Search by name or path..."
            )
        with col2:
            sort_by = st.selectbox(
                "Sort by",
                ["Date (newest)", "Date (oldest)", "Name (A-Z)", "Name (Z-A)"],
            )

        # Filter and sort
        filtered_sessions = sessions
        if filter_text:
            filtered_sessions = [
                s
                for s in sessions
                if filter_text.lower() in s.source_path.lower()
                or filter_text.lower() in s.session_id.lower()
            ]

        if sort_by == "Date (newest)":
            filtered_sessions.sort(key=lambda s: s.created_at, reverse=True)
        elif sort_by == "Date (oldest)":
            filtered_sessions.sort(key=lambda s: s.created_at)
        elif sort_by == "Name (A-Z)":
            filtered_sessions.sort(key=lambda s: Path(s.source_path).name.lower())
        elif sort_by == "Name (Z-A)":
            filtered_sessions.sort(
                key=lambda s: Path(s.source_path).name.lower(), reverse=True
            )

        # Display sessions
        st.markdown(f"Showing {len(filtered_sessions)} of {len(sessions)} sessions")

        for session in filtered_sessions:
            with st.container():
                col1, col2, col3 = st.columns([4, 1, 1])

                with col1:
                    display_name = Path(session.source_path).name
                    st.markdown(f"**{display_name}**")
                    st.caption(f"📁 `{session.source_path}`")
                    st.caption(
                        f"🕐 {format_timestamp(session.created_at)} • ID: `{session.session_id[:8]}`"
                    )

                with col2:
                    # Stats
                    try:
                        stats = orchestrator.get_session_stats(session.session_id)
                        st.markdown(f"📄 {stats['file_count']} files")
                        st.markdown(f"📝 {stats['total_lines']:,} lines")
                    except Exception:
                        pass

                with col3:
                    # Actions
                    if st.button(
                        "Load",
                        key=f"load_session_{session.session_id}",
                        use_container_width=True,
                    ):
                        st.session_state.current_session_id = session.session_id
                        st.session_state.current_session_name = display_name
                        st.success(f"Loaded session: {display_name}")
                        st.rerun()

                    if st.button(
                        "🗑️ Delete",
                        key=f"delete_session_{session.session_id}",
                        use_container_width=True,
                    ):
                        if orchestrator.delete_session(session.session_id):
                            st.success(f"Deleted session: {display_name}")
                            add_log(
                                f"Deleted session {session.session_id[:8]}", "warning"
                            )
                            st.rerun()
                        else:
                            st.error("Failed to delete session")

                st.divider()

    except Exception as e:
        st.error(f"Error loading sessions: {e}")


def render_analysis():
    """Render the analysis page."""
    st.title("🔍 Analysis")

    if not st.session_state.current_session_id:
        st.warning("No active session. Please select or create a session first.")
        if st.button("📁 Go to Sessions", use_container_width=True):
            st.session_state.current_page = "sessions"
            st.rerun()
        return

    session_id = st.session_state.current_session_id
    session_name = st.session_state.current_session_name or "Unnamed Session"

    st.markdown(f"**Session:** {session_name} (`{session_id[:8]}`)")

    # Agent selection
    st.divider()
    st.markdown("### 🤖 Select Agent")

    agent_type = st.selectbox(
        "Choose an agent to run",
        [
            ("docs", "📚 Documentation Agent - Generate documentation"),
            ("qa", "❓ Q&A Agent - Ask questions about the codebase"),
            ("refactor", "🔧 Refactor Agent - Analyze and suggest improvements"),
            ("rebuild", "🏗️ Rebuilder Agent - Scaffold a new project"),
        ],
        format_func=lambda x: x[1],
    )[0]

    # Agent-specific inputs
    st.divider()

    if agent_type == "docs":
        st.markdown("### 📚 Documentation Generation")

        doc_types = st.multiselect(
            "Documentation types to generate",
            ["README", "ARCHITECTURE", "API_REFERENCE", "ENV_GUIDE"],
            default=["README", "ARCHITECTURE"],
        )

        output_dir = st.text_input(
            "Output Directory (Optional)",
            placeholder="Leave empty for default",
        )

        if st.button("🚀 Generate Documentation", use_container_width=True):
            progress_placeholder = st.empty()
            result_placeholder = st.empty()

            try:
                db_path = get_db_path()
                orchestrator = Orchestrator(db_path)

                for progress in orchestrator.generate_documentation(
                    session_id=session_id,
                    output_dir=output_dir if output_dir else None,
                    doc_types=[d.lower() for d in doc_types],
                ):
                    with progress_placeholder.container():
                        render_progress_bar(
                            progress.progress,
                            progress.message,
                            progress.status,
                        )

                with result_placeholder.container():
                    st.success("Documentation generated successfully!")
                    add_log(
                        f"Generated documentation for session {session_id[:8]}",
                        "success",
                    )

            except Exception as e:
                st.error(f"Error generating documentation: {e}")
                add_log(f"Documentation error: {e}", "error")

    elif agent_type == "qa":
        st.markdown("### ❓ Ask a Question")

        question = st.text_area(
            "Your question",
            placeholder="e.g., 'Where is authentication handled?' or 'What happens when a payment fails?'",
            height=100,
        )

        if st.button("🔍 Ask", use_container_width=True) and question:
            progress_placeholder = st.empty()
            result_placeholder = st.empty()

            try:
                db_path = get_db_path()
                orchestrator = Orchestrator(db_path)

                answer_text = ""
                for progress in orchestrator.ask_question(
                    session_id=session_id,
                    question=question,
                ):
                    with progress_placeholder.container():
                        render_progress_bar(
                            progress.progress,
                            progress.message,
                            progress.status,
                        )

                    if progress.result and "answer" in progress.result:
                        answer_text = progress.result["answer"]

                with result_placeholder.container():
                    st.markdown("### 💬 Answer")
                    st.markdown(answer_text)

                    if progress.result and "relevant_files" in progress.result:
                        with st.expander("📄 Relevant Files"):
                            for file_path in progress.result["relevant_files"]:
                                st.markdown(f"- `{file_path}`")

                    add_log(f"Q&A completed for session {session_id[:8]}", "success")

            except Exception as e:
                st.error(f"Error asking question: {e}")
                add_log(f"Q&A error: {e}", "error")

    elif agent_type == "refactor":
        st.markdown("### 🔧 Refactoring Analysis")

        focus_areas = st.multiselect(
            "Focus areas (Optional)",
            ["code_smells", "performance", "security", "maintainability"],
            default=["code_smells"],
        )

        if st.button("🔍 Analyze Code", use_container_width=True):
            progress_placeholder = st.empty()
            result_placeholder = st.empty()

            try:
                db_path = get_db_path()
                orchestrator = Orchestrator(db_path)

                suggestions = []
                for progress in orchestrator.analyze_refactoring(
                    session_id=session_id,
                    focus_areas=focus_areas if focus_areas else None,
                ):
                    with progress_placeholder.container():
                        render_progress_bar(
                            progress.progress,
                            progress.message,
                            progress.status,
                        )

                with result_placeholder.container():
                    st.markdown("### 📋 Suggestions")

                    if progress.result and "suggestions" in progress.result:
                        suggestions = progress.result["suggestions"]

                        for suggestion in suggestions:
                            with st.expander(
                                f"🔍 {suggestion['type'].replace('_', ' ').title()}"
                            ):
                                st.markdown(
                                    f"**Description:** {suggestion['description']}"
                                )
                                st.markdown(
                                    f"**Recommendation:** {suggestion['recommendation']}"
                                )

                                if "files" in suggestion:
                                    st.markdown("**Files:**")
                                    for file_path in suggestion["files"]:
                                        st.markdown(f"- `{file_path}`")
                    else:
                        st.info(
                            "No refactoring suggestions found. Your code looks good!"
                        )

                    add_log(
                        f"Refactoring analysis completed for session {session_id[:8]}",
                        "success",
                    )

            except Exception as e:
                st.error(f"Error analyzing code: {e}")
                add_log(f"Refactoring error: {e}", "error")

    elif agent_type == "rebuild":
        st.markdown("### 🏗️ Project Rebuilder")

        output_dir = st.text_input(
            "Output Directory",
            placeholder="/path/to/new/project",
            help="Where to scaffold the new project",
        )

        constraints = st.text_area(
            "Constraints (Optional)",
            placeholder="e.g., 'Make it multi-tenant', 'Switch from REST to GraphQL'",
            height=100,
        )

        if st.button("🚀 Scaffold Project", use_container_width=True) and output_dir:
            progress_placeholder = st.empty()
            result_placeholder = st.empty()

            try:
                db_path = get_db_path()
                orchestrator = Orchestrator(db_path)

                constraints_dict = {"notes": constraints} if constraints else None

                for progress in orchestrator.rebuild_project(
                    template_session_id=session_id,
                    output_dir=output_dir,
                    constraints=constraints_dict,
                ):
                    with progress_placeholder.container():
                        render_progress_bar(
                            progress.progress,
                            progress.message,
                            progress.status,
                        )

                with result_placeholder.container():
                    st.success(f"Project scaffolded in: {output_dir}")

                    if progress.result and "files_created" in progress.result:
                        with st.expander("📄 Created Files"):
                            for file_path in progress.result["files_created"]:
                                st.markdown(f"- `{file_path}`")

                    add_log(f"Project rebuilt from session {session_id[:8]}", "success")

            except Exception as e:
                st.error(f"Error scaffolding project: {e}")
                add_log(f"Rebuild error: {e}", "error")

    # Execution logs
    st.divider()
    st.markdown("### 📝 Execution Logs")

    if st.session_state.logs:
        render_log_viewer(st.session_state.logs, max_height=300)
    else:
        st.info("No logs yet")

    if st.button("🗑️ Clear Logs"):
        st.session_state.logs = []
        st.rerun()


def render_visualizations():
    """Render the visualizations page."""
    st.title("📊 Visualizations")

    if not st.session_state.current_session_id:
        st.warning("No active session. Please select or create a session first.")
        if st.button("📁 Go to Sessions", use_container_width=True):
            st.session_state.current_page = "sessions"
            st.rerun()
        return

    session_id = st.session_state.current_session_id
    session_name = st.session_state.current_session_name or "Unnamed Session"

    st.markdown(f"**Session:** {session_name} (`{session_id[:8]}`)")

    try:
        db_path = get_db_path()
        orchestrator = Orchestrator(db_path)

        # Get session stats
        stats = orchestrator.get_session_stats(session_id)
        files_count = stats.get("file_count", 0)

        if files_count == 0:
            st.info("No files in this session to visualize.")
            return

        # Metrics cards
        st.divider()
        render_metrics_cards(stats)

        # Charts
        st.divider()
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🌐 Language Distribution")
            languages = stats.get("languages", {})
            if languages:
                render_language_chart(languages)
            else:
                st.info("No language data available")

        with col2:
            st.markdown("### 📁 File Size Distribution")
            # Get files for size chart
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files WHERE session_id = ?", (session_id,))
            files = [dict(row) for row in cursor.fetchall()]
            conn.close()

            render_file_size_chart(files)

        # File tree
        st.divider()
        st.markdown("### 🌳 File Tree")

        selected_file = None

        def on_file_select(file_path: str):
            st.session_state.selected_file = file_path

        with st.expander("Browse Files", expanded=True):
            render_file_tree(files, on_file_select=on_file_select)

        # Code viewer
        if "selected_file" in st.session_state and st.session_state.selected_file:
            st.divider()
            st.markdown(
                f"### 👁️ Code Viewer: `{Path(st.session_state.selected_file).name}`"
            )

            from architectai.web.components import render_code_viewer

            render_code_viewer(st.session_state.selected_file)

        # Dependency graph
        st.divider()
        st.markdown("### 🔗 Dependency Graph")

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM graph_edges WHERE session_id = ?", (session_id,))
        edges = [dict(row) for row in cursor.fetchall()]
        conn.close()

        if edges:
            render_dependency_graph(edges)
        else:
            st.info(
                "No dependency data available yet. Dependencies are extracted during AST parsing."
            )
            st.markdown("Run the AST parser to generate dependency graphs.")

    except Exception as e:
        st.error(f"Error loading visualizations: {e}")


def render_settings():
    """Render the settings page."""
    st.title("⚙️ Settings")

    st.markdown("### 🔧 General Settings")

    settings = st.session_state.settings

    # Model settings
    st.markdown("#### 🤖 Model Configuration")

    model_provider = st.selectbox(
        "Model Provider",
        ["ollama", "vllm", "llamacpp"],
        index=["ollama", "vllm", "llamacpp"].index(
            settings.get("model_provider", "ollama")
        ),
    )

    model_name = st.text_input(
        "Model Name",
        value=settings.get("model_name", "codellama"),
        help="Name of the model to use (e.g., 'codellama', 'gpt4', 'claude')",
    )

    embedding_model = st.text_input(
        "Embedding Model",
        value=settings.get("embedding_model", "nomic-embed-text"),
        help="Model for generating embeddings",
    )

    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=settings.get("temperature", 0.1),
        step=0.1,
        help="Lower = more deterministic, Higher = more creative",
    )

    max_context = st.number_input(
        "Max Context Length",
        min_value=1024,
        max_value=32768,
        value=settings.get("max_context_length", 8192),
        step=1024,
        help="Maximum context length for model calls",
    )

    # Paths
    st.markdown("#### 📁 Paths")

    db_path = st.text_input(
        "Database Path",
        value=settings.get("db_path", "~/.architectai/architectai.db"),
    )

    log_dir = st.text_input(
        "Log Directory",
        value=settings.get("log_dir", "~/.architectai/logs"),
    )

    output_dir = st.text_input(
        "Output Directory",
        value=settings.get("output_dir", "~/.architectai/output"),
    )

    # UI settings
    st.markdown("#### 🎨 UI Settings")

    theme = st.selectbox(
        "Theme",
        ["dark", "light"],
        index=["dark", "light"].index(settings.get("theme", "dark")),
    )

    show_line_numbers = st.checkbox(
        "Show Line Numbers in Code Viewer",
        value=settings.get("show_line_numbers", True),
    )

    syntax_highlighting = st.checkbox(
        "Enable Syntax Highlighting",
        value=settings.get("syntax_highlighting", True),
    )

    auto_save = st.checkbox(
        "Auto-save Settings",
        value=settings.get("auto_save", True),
    )

    # Save button
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Save Settings", use_container_width=True):
            new_settings = {
                "model_provider": model_provider,
                "model_name": model_name,
                "embedding_model": embedding_model,
                "temperature": temperature,
                "max_context_length": max_context,
                "db_path": db_path,
                "log_dir": log_dir,
                "output_dir": output_dir,
                "theme": theme,
                "show_line_numbers": show_line_numbers,
                "syntax_highlighting": syntax_highlighting,
                "auto_save": auto_save,
            }

            if save_settings(new_settings):
                st.session_state.settings = new_settings
                st.success("Settings saved!")
                add_log("Settings saved", "success")
            else:
                st.error("Failed to save settings")

    with col2:
        if st.button("🔄 Reset to Defaults", use_container_width=True):
            from architectai.web.utils import DEFAULT_SETTINGS

            st.session_state.settings = DEFAULT_SETTINGS.copy()
            st.success("Settings reset to defaults")
            st.rerun()

    # System info
    st.divider()
    st.markdown("### ℹ️ System Information")

    try:
        import platform

        st.markdown(f"**Python Version:** {platform.python_version()}")
        st.markdown(f"**Operating System:** {platform.system()} {platform.release()}")
        st.markdown(f"**Platform:** {platform.platform()}")

        # Check database
        db_path_expanded = os.path.expanduser(db_path)
        if os.path.exists(db_path_expanded):
            size = os.path.getsize(db_path_expanded)
            st.markdown(f"**Database:** ✅ Exists ({format_file_size(size)})")
        else:
            st.markdown(f"**Database:** ❌ Not found")

        # Check available packages
        st.markdown("**Installed Packages:**")
        packages = ["streamlit", "plotly", "networkx", "pandas"]
        for pkg in packages:
            try:
                __import__(pkg)
                st.markdown(f"  ✅ {pkg}")
            except ImportError:
                st.markdown(f"  ❌ {pkg}")

    except Exception as e:
        st.error(f"Error getting system info: {e}")


def main():
    """Main application entry point."""
    # Initialize current page
    if "current_page" not in st.session_state:
        st.session_state.current_page = "home"

    # Render sidebar
    render_sidebar()

    # Render current page
    page = st.session_state.current_page

    if page == "home":
        render_home()
    elif page == "upload":
        render_upload()
    elif page == "sessions":
        render_sessions()
    elif page == "analysis":
        render_analysis()
    elif page == "visualizations":
        render_visualizations()
    elif page == "settings":
        render_settings()
    else:
        render_home()


if __name__ == "__main__":
    main()
