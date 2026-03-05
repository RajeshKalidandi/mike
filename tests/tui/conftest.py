"""Pytest configuration and fixtures for TUI tests."""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_db_path():
    """Create a temporary database path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    # Cleanup
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def mock_session_data():
    """Mock session data for testing."""
    return {
        "session_id": "test-session-123",
        "source_path": "/path/to/code",
        "session_type": "local",
        "status": "active",
        "created_at": "2026-03-05T10:00:00",
        "updated_at": "2026-03-05T10:00:00",
    }


@pytest.fixture
def mock_files_data():
    """Mock files data for testing."""
    return [
        {
            "relative_path": "src/main.py",
            "absolute_path": "/path/to/code/src/main.py",
            "language": "python",
            "size_bytes": 1024,
            "line_count": 50,
        },
        {
            "relative_path": "src/utils.py",
            "absolute_path": "/path/to/code/src/utils.py",
            "language": "python",
            "size_bytes": 512,
            "line_count": 25,
        },
        {
            "relative_path": "README.md",
            "absolute_path": "/path/to/code/README.md",
            "language": "markdown",
            "size_bytes": 256,
            "line_count": 10,
        },
    ]


@pytest.fixture
def mock_stats():
    """Mock session stats for testing."""
    return {
        "file_count": 3,
        "parsed_count": 3,
        "total_lines": 85,
        "languages": {"python": 2, "markdown": 1},
    }
