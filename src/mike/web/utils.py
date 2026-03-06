"""Web utilities for the Mike Streamlit frontend.

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
    "db_path": "~/.mike/mike.db",
    "log_dir": "~/.mike/logs",
    "output_dir": "~/.mike/output",
    "auto_save": True,
    "show_line_numbers": True,
    "syntax_highlighting": True,
}


def get_settings_path() -> Path:
    """Get the path to the settings file."""
    config_dir = Path.home() / ".mike"
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
        # Build Plan Approval state
        "build_plan": None,
        "build_plan_status": None,  # 'draft', 'approved', 'executing', 'completed', 'cancelled'
        "build_plan_output_dir": None,
        "build_plan_constraints": None,
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


def create_files_zip(
    files: List[Dict[str, Any]], zip_name: str, base_path: Optional[Path] = None
) -> Optional[Path]:
    """Create a ZIP archive from a list of files.

    Args:
        files: List of file dicts with 'path', 'content', and optionally 'relative_path'
        zip_name: Name of the output ZIP file (without extension)
        base_path: Base directory for the ZIP contents

    Returns:
        Path to created ZIP file or None if failed
    """
    try:
        output_dir = get_output_dir()
        zip_path = output_dir / f"{zip_name}.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add metadata
            metadata = {
                "created_at": datetime.now().isoformat(),
                "file_count": len(files),
                "total_size": sum(
                    len(f.get("content", "").encode("utf-8")) for f in files
                ),
            }
            zf.writestr(".mike/metadata.json", json.dumps(metadata, indent=2))

            # Add files
            for file_info in files:
                if "content" in file_info:
                    # Content provided directly
                    rel_path = file_info.get("relative_path", file_info.get("path", ""))
                    content = file_info["content"]
                    zf.writestr(rel_path, content)
                elif "path" in file_info and Path(file_info["path"]).exists():
                    # Read from file system
                    abs_path = file_info["path"]
                    rel_path = file_info.get("relative_path", Path(abs_path).name)
                    zf.write(abs_path, rel_path)

        return zip_path
    except Exception as e:
        add_log(f"Failed to create ZIP: {e}", "error")
        return None


def create_project_zip(project_dir: Path, zip_name: str) -> Optional[Path]:
    """Create a ZIP archive of an entire project directory.

    Args:
        project_dir: Path to project directory
        zip_name: Name of output ZIP file

    Returns:
        Path to created ZIP file or None if failed
    """
    try:
        output_dir = get_output_dir()
        zip_path = output_dir / f"{zip_name}.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in project_dir.rglob("*"):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(project_dir))
                    zf.write(file_path, arcname)

            # Add metadata
            metadata = {
                "created_at": datetime.now().isoformat(),
                "source": "rebuilder_agent",
                "project_name": project_dir.name,
            }
            zf.writestr(".mike/metadata.json", json.dumps(metadata, indent=2))

        return zip_path
    except Exception as e:
        add_log(f"Failed to create project ZIP: {e}", "error")
        return None


def read_file_content(
    file_path: str | Path, max_size: int = 1024 * 1024
) -> Optional[str]:
    """Read file content with size limit and encoding detection.

    Args:
        file_path: Path to file
        max_size: Maximum file size in bytes (default 1MB)

    Returns:
        File content as string or None if failed
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return None

        if path.stat().st_size > max_size:
            return f"# File too large ({format_file_size(path.stat().st_size)})"

        # Try UTF-8 first, then fall back
        encodings = ["utf-8", "latin-1", "cp1252"]
        for encoding in encodings:
            try:
                with open(path, "r", encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue

        return "# Binary file - cannot display"
    except Exception as e:
        return f"# Error reading file: {e}"


def copy_to_clipboard_button(content: str, key: str) -> None:
    """Create a JavaScript-based copy to clipboard button.

    Note: This uses Streamlit's native button with JavaScript injection.
    """
    import streamlit as st

    # Use st.code with copy button if available, otherwise provide workaround
    st.code(content, language=None)
    st.caption("Copy button available in code block above ☝️")


def detect_language_from_content(content: str, file_path: str = "") -> str:
    """Detect programming language from content and/or file path.

    Args:
        content: File content
        file_path: Optional file path for extension-based detection

    Returns:
        Language name for syntax highlighting
    """
    # Extension-based detection first
    if file_path:
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
            ".scss": "scss",
            ".json": "json",
            ".xml": "xml",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".dockerfile": "dockerfile",
        }
        if ext in ext_to_lang:
            return ext_to_lang[ext]

    # Content-based detection
    shebang_map = {
        "python": ["python", "python3"],
        "bash": ["bash", "sh"],
        "ruby": ["ruby"],
        "perl": ["perl"],
        "nodejs": ["node"],
    }

    if content.startswith("#!/"):
        first_line = content.split("\n")[0].lower()
        for lang, interpreters in shebang_map.items():
            if any(interp in first_line for interp in interpreters):
                return lang

    return "text"


def get_file_stats(file_info: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and format file statistics.

    Args:
        file_info: File information dict

    Returns:
        Formatted statistics dict
    """
    content = file_info.get("content", "")
    if isinstance(content, str):
        lines = content.count("\n") + (
            1 if content and not content.endswith("\n") else 0
        )
        size = len(content.encode("utf-8"))
    else:
        lines = file_info.get("line_count", 0)
        size = file_info.get("size_bytes", 0)

    return {
        "lines": lines,
        "size_bytes": size,
        "size_formatted": format_file_size(size),
        "language": detect_language_from_content(content, file_info.get("path", "")),
    }
