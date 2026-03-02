"""Web utilities for the ArchitectAI Streamlit frontend.

Provides helper functions for file handling, session management,
settings persistence, and chart generation.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import sqlite3

import streamlit as st


# Default settings
DEFAULT_SETTINGS = {
    "theme": "dark",
    "model_provider": "ollama",
    "model_name": "codellama",
    "embedding_model": "nomic-embed-text",
    "max_context_length": 8192,
    "temperature": 0.1,
    "db_path": "~/.architectai/architectai.db",
    "log_dir": "~/.architectai/logs",
    "output_dir": "~/.architectai/output",
    "auto_save": True,
    "show_line_numbers": True,
    "syntax_highlighting": True,
}


def get_settings_path() -> Path:
    """Get the path to the settings file."""
    config_dir = Path.home() / ".architectai"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "settings.json"


def load_settings() -> Dict[str, Any]:
    """Load settings from file or return defaults."""
    settings_path = get_settings_path()

    if settings_path.exists():
        try:
            with open(settings_path, "r") as f:
                settings = json.load(f)
                # Merge with defaults to ensure all keys exist
                merged = DEFAULT_SETTINGS.copy()
                merged.update(settings)
                return merged
        except Exception:
            pass

    return DEFAULT_SETTINGS.copy()


def save_settings(settings: Dict[str, Any]) -> bool:
    """Save settings to file."""
    try:
        settings_path = get_settings_path()
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception:
        return False


def get_db_path() -> str:
    """Get the database path from settings or default."""
    settings = load_settings()
    db_path = settings.get("db_path", DEFAULT_SETTINGS["db_path"])
    return os.path.expanduser(db_path)


def get_log_dir() -> Path:
    """Get the log directory from settings."""
    settings = load_settings()
    log_dir = settings.get("log_dir", DEFAULT_SETTINGS["log_dir"])
    path = Path(os.path.expanduser(log_dir))
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_output_dir() -> Path:
    """Get the output directory from settings."""
    settings = load_settings()
    output_dir = settings.get("output_dir", DEFAULT_SETTINGS["output_dir"])
    path = Path(os.path.expanduser(output_dir))
    path.mkdir(parents=True, exist_ok=True)
    return path


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def format_timestamp(timestamp: str | datetime | None) -> str:
    """Format timestamp for display."""
    if timestamp is None:
        return "Unknown"

    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return timestamp

    if isinstance(timestamp, datetime):
        return timestamp.strftime("%Y-%m-%d %H:%M")

    return str(timestamp)


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}m"
    else:
        return f"{seconds / 3600:.1f}h"


def calculate_content_hash(file_paths: List[Path]) -> str:
    """Calculate a content hash for a list of files."""
    hasher = hashlib.sha256()

    for path in sorted(file_paths):
        if path.is_file():
            try:
                with open(path, "rb") as f:
                    hasher.update(f.read())
            except Exception:
                pass

    return hasher.hexdigest()


def create_session_zip(
    session_id: str, source_path: str, db_path: str
) -> Optional[Path]:
    """Create a ZIP archive of a session including metadata."""
    try:
        output_dir = get_output_dir()
        zip_path = output_dir / f"session_{session_id[:8]}.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add metadata
            metadata = {
                "session_id": session_id,
                "source_path": source_path,
                "exported_at": datetime.now().isoformat(),
            }
            zf.writestr("metadata.json", json.dumps(metadata, indent=2))

            # Add files from database
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files WHERE session_id = ?", (session_id,))
            files = [dict(row) for row in cursor.fetchall()]
            conn.close()

            for file_info in files:
                abs_path = file_info.get("absolute_path")
                if abs_path and Path(abs_path).exists():
                    arcname = f"files/{file_info['relative_path']}"
                    zf.write(abs_path, arcname)

        return zip_path
    except Exception:
        return None


def extract_session_zip(zip_path: Path, extract_dir: Path) -> Optional[Dict[str, Any]]:
    """Extract a session ZIP and return metadata."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

            metadata_path = extract_dir / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    return json.load(f)

        return None
    except Exception:
        return None


def scan_directory_for_upload(
    directory: Path, progress_callback=None
) -> Tuple[List[Dict[str, Any]], int]:
    """Scan a directory and return file information."""
    files = []
    total_size = 0

    for file_path in directory.rglob("*"):
        if file_path.is_file():
            try:
                stat = file_path.stat()
                size = stat.st_size
                total_size += size

                # Count lines
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        line_count = len(f.readlines())
                except Exception:
                    line_count = 0

                files.append(
                    {
                        "relative_path": str(file_path.relative_to(directory)),
                        "absolute_path": str(file_path),
                        "size_bytes": size,
                        "line_count": line_count,
                        "extension": file_path.suffix.lower(),
                    }
                )

                if progress_callback:
                    progress_callback(len(files))
            except Exception:
                pass

    return files, total_size


def get_language_distribution(files: List[Dict[str, Any]]) -> Dict[str, int]:
    """Get language distribution from file list."""
    distribution = {}

    extension_to_language = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".jsx": "JavaScript",
        ".tsx": "TypeScript",
        ".java": "Java",
        ".go": "Go",
        ".rs": "Rust",
        ".c": "C",
        ".cpp": "C++",
        ".h": "C",
        ".hpp": "C++",
        ".rb": "Ruby",
        ".php": "PHP",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".scala": "Scala",
        ".cs": "C#",
        ".lua": "Lua",
        ".sh": "Shell",
        ".sql": "SQL",
        ".html": "HTML",
        ".css": "CSS",
        ".scss": "SCSS",
        ".json": "JSON",
        ".xml": "XML",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".md": "Markdown",
        ".dockerfile": "Dockerfile",
        ".tf": "Terraform",
    }

    for file_info in files:
        ext = file_info.get("extension", "").lower()
        lang = extension_to_language.get(ext, "Other")
        distribution[lang] = distribution.get(lang, 0) + 1

    return distribution


def init_session_state():
    """Initialize Streamlit session state variables."""
    defaults = {
        "current_session_id": None,
        "current_session_name": None,
        "upload_progress": 0,
        "processing_status": None,
        "agent_results": {},
        "logs": [],
        "settings": load_settings(),
        "last_activity": datetime.now(),
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def add_log(message: str, level: str = "info"):
    """Add a log message to session state."""
    if "logs" not in st.session_state:
        st.session_state.logs = []

    st.session_state.logs.append(
        {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
        }
    )

    # Keep only last 1000 logs
    if len(st.session_state.logs) > 1000:
        st.session_state.logs = st.session_state.logs[-1000:]


def get_log_level_color(level: str) -> str:
    """Get color for log level."""
    colors = {
        "debug": "gray",
        "info": "blue",
        "warning": "orange",
        "error": "red",
        "success": "green",
    }
    return colors.get(level.lower(), "gray")
