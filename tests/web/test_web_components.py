"""Comprehensive tests for Mike web UI components.

Tests for theme utilities, components, and web utilities.
"""

import json
import os
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Mock heavy dependencies BEFORE any web imports
mock_st = MagicMock()
mock_st.session_state = {}

# Mock plotly modules
mock_plotly_go = MagicMock()
mock_plotly_px = MagicMock()
mock_plotly_subplots = MagicMock()

# Mock networkx
mock_nx = MagicMock()

# Mock pandas
mock_pd = MagicMock()

# Set up sys.modules before importing web modules
sys.modules["streamlit"] = mock_st
sys.modules["plotly"] = MagicMock()
sys.modules["plotly.graph_objects"] = mock_plotly_go
sys.modules["plotly.express"] = mock_plotly_px
sys.modules["plotly.subplots"] = mock_plotly_subplots
sys.modules["networkx"] = mock_nx
sys.modules["pandas"] = mock_pd

# Now import the modules under test
from mike.web.theme_utils import (
    get_current_theme,
    set_theme,
    generate_css,
    get_chart_theme,
    get_theme_colors,
    THEME_COLORS,
)
from mike.web.utils import (
    DEFAULT_SETTINGS,
    load_settings,
    save_settings,
    format_file_size,
    format_timestamp,
    format_duration,
    calculate_content_hash,
    create_session_zip,
    get_language_distribution,
)


class TestThemeUtils:
    """Tests for theme utilities."""

    def test_themes_structure(self):
        """Test that THEME_COLORS dictionary has all required keys."""
        assert "dark" in THEME_COLORS
        assert "light" in THEME_COLORS

        for theme_name in ["dark", "light"]:
            theme = THEME_COLORS[theme_name]
            assert "background" in theme
            assert "secondary_background" in theme
            assert "text" in theme
            assert "primary" in theme

    def test_generate_css_dark(self):
        """Test CSS generation for dark theme."""
        css = generate_css("dark")
        assert "#0e1117" in css  # Background color
        assert "#fafafa" in css  # Text color
        assert isinstance(css, str)
        assert len(css) > 0

    def test_generate_css_light(self):
        """Test CSS generation for light theme."""
        css = generate_css("light")
        assert "#ffffff" in css  # Background color
        assert "#31333f" in css  # Text color
        assert isinstance(css, str)

    def test_get_chart_theme_dark(self):
        """Test chart theme for dark mode."""
        theme = get_chart_theme("dark")
        assert theme["paper_bgcolor"] == "#1e1e1e"
        assert theme["font"]["color"] == "#fafafa"

    def test_get_chart_theme_light(self):
        """Test chart theme for light mode."""
        theme = get_chart_theme("light")
        assert theme["paper_bgcolor"] == "#ffffff"
        assert theme["font"]["color"] == "#31333f"

    def test_get_theme_colors(self):
        """Test getting theme colors."""
        dark_colors = get_theme_colors("dark")
        assert dark_colors["background"] == "#0e1117"

        light_colors = get_theme_colors("light")
        assert light_colors["background"] == "#ffffff"


class TestWebUtils:
    """Tests for web utilities."""

    def test_default_settings_structure(self):
        """Test that default settings has all required keys."""
        required_keys = [
            "theme",
            "model_provider",
            "model_name",
            "embedding_model",
            "max_context_length",
            "temperature",
            "db_path",
            "log_dir",
            "output_dir",
            "auto_save",
            "show_line_numbers",
            "syntax_highlighting",
        ]
        for key in required_keys:
            assert key in DEFAULT_SETTINGS, f"Missing key: {key}"

    def test_format_file_size_bytes(self):
        """Test file size formatting for bytes."""
        assert format_file_size(500) == "500 B"
        assert format_file_size(0) == "0 B"

    def test_format_file_size_kb(self):
        """Test file size formatting for kilobytes."""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1536) == "1.5 KB"

    def test_format_file_size_mb(self):
        """Test file size formatting for megabytes."""
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(5 * 1024 * 1024) == "5.0 MB"

    def test_format_file_size_gb(self):
        """Test file size formatting for gigabytes."""
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"

    def test_format_timestamp_datetime(self):
        """Test timestamp formatting from datetime."""
        dt = datetime(2024, 3, 15, 14, 30)
        assert format_timestamp(dt) == "2024-03-15 14:30"

    def test_format_timestamp_iso_string(self):
        """Test timestamp formatting from ISO string."""
        iso_str = "2024-03-15T14:30:00"
        assert format_timestamp(iso_str) == "2024-03-15 14:30"

    def test_format_timestamp_none(self):
        """Test timestamp formatting for None."""
        assert format_timestamp(None) == "Unknown"

    def test_format_duration_seconds(self):
        """Test duration formatting for seconds."""
        assert format_duration(45) == "45.0s"

    def test_format_duration_minutes(self):
        """Test duration formatting for minutes."""
        assert format_duration(150) == "2.5m"

    def test_format_duration_hours(self):
        """Test duration formatting for hours."""
        assert format_duration(7200) == "2.0h"

    def test_calculate_content_hash(self):
        """Test content hash calculation."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            file_paths = [Path(temp_path)]
            hash1 = calculate_content_hash(file_paths)
            hash2 = calculate_content_hash(file_paths)

            # Same content should produce same hash
            assert hash1 == hash2
            assert len(hash1) == 64  # SHA-256 hex length
        finally:
            os.unlink(temp_path)

    def test_calculate_content_hash_different_content(self):
        """Test that different content produces different hashes."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f1:
            f1.write("content1")
            path1 = f1.name

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f2:
            f2.write("content2")
            path2 = f2.name

        try:
            hash1 = calculate_content_hash([Path(path1)])
            hash2 = calculate_content_hash([Path(path2)])

            assert hash1 != hash2
        finally:
            os.unlink(path1)
            os.unlink(path2)

    def test_get_language_distribution(self):
        """Test language distribution calculation."""
        files = [
            {"extension": ".py"},
            {"extension": ".py"},
            {"extension": ".js"},
            {"extension": ".ts"},
            {"extension": ".unknown"},
        ]

        distribution = get_language_distribution(files)

        assert distribution["Python"] == 2
        assert distribution["JavaScript"] == 1
        assert distribution["TypeScript"] == 1
        assert distribution["Other"] == 1

    def test_get_language_distribution_empty(self):
        """Test language distribution with empty list."""
        distribution = get_language_distribution([])
        assert distribution == {}


class TestSettingsPersistence:
    """Tests for settings load/save functionality."""

    def test_load_settings_default(self, tmp_path):
        """Test loading settings returns defaults when no file exists."""
        with patch(
            "mike.web.utils.get_settings_path",
            return_value=tmp_path / "nonexistent.json",
        ):
            settings = load_settings()
            assert settings["theme"] == DEFAULT_SETTINGS["theme"]
            assert settings["model_provider"] == DEFAULT_SETTINGS["model_provider"]

    def test_save_and_load_settings(self, tmp_path):
        """Test saving and loading settings."""
        settings_file = tmp_path / "settings.json"

        with patch(
            "mike.web.utils.get_settings_path", return_value=settings_file
        ):
            custom_settings = DEFAULT_SETTINGS.copy()
            custom_settings["theme"] = "light"
            custom_settings["model_name"] = "custom-model"

            assert save_settings(custom_settings) is True

            loaded = load_settings()
            assert loaded["theme"] == "light"
            assert loaded["model_name"] == "custom-model"

    def test_save_settings_merges_with_defaults(self, tmp_path):
        """Test that saved settings merge with defaults."""
        settings_file = tmp_path / "settings.json"

        with patch(
            "mike.web.utils.get_settings_path", return_value=settings_file
        ):
            partial_settings = {"theme": "light"}
            save_settings(partial_settings)

            loaded = load_settings()
            # Should have all default keys
            for key in DEFAULT_SETTINGS:
                assert key in loaded
            # Should have custom value
            assert loaded["theme"] == "light"


class TestBuildPlanComponents:
    """Tests for build plan approval components."""

    def test_build_plan_data_structure(self):
        """Test build plan data structure is valid."""
        plan_data = {
            "project_name": "test_project",
            "description": "Test project description",
            "directories": ["src", "tests"],
            "files": [
                {"path": "src/main.py", "type": "python", "description": "Main file"}
            ],
            "dependencies": ["fastapi"],
            "estimated_files": 10,
            "template_session": "abc123",
        }

        # Validate structure
        assert "project_name" in plan_data
        assert "directories" in plan_data
        assert "files" in plan_data
        assert isinstance(plan_data["files"], list)

    def test_file_tree_preview_structure(self):
        """Test file tree preview data structure."""
        files = [
            {"path": "src/main.py", "type": "python", "description": "Entry point"},
            {"path": "README.md", "type": "markdown", "description": "Docs"},
        ]

        # Validate structure
        assert len(files) == 2
        assert files[0]["path"] == "src/main.py"
        assert files[0]["type"] == "python"


class TestIntegrationWorkflows:
    """Integration tests for complete workflows."""

    def test_theme_css_generation(self):
        """Test complete CSS generation workflow."""
        # Generate CSS for both themes
        dark_css = generate_css("dark")
        light_css = generate_css("light")

        # Both should be valid CSS strings
        assert isinstance(dark_css, str)
        assert isinstance(light_css, str)
        assert len(dark_css) > 0
        assert len(light_css) > 0

        # Should contain theme-specific colors
        assert "#0e1117" in dark_css
        assert "#ffffff" in light_css

    def test_settings_persistence_workflow(self, tmp_path):
        """Test complete settings save/load workflow."""
        settings_file = tmp_path / "settings.json"

        with patch(
            "mike.web.utils.get_settings_path", return_value=settings_file
        ):
            # Save custom settings
            custom = DEFAULT_SETTINGS.copy()
            custom["theme"] = "light"
            custom["model_name"] = "gpt-4"

            save_settings(custom)

            # Load and verify
            loaded = load_settings()
            assert loaded["theme"] == "light"
            assert loaded["model_name"] == "gpt-4"

            # Verify all defaults present
            for key in DEFAULT_SETTINGS:
                assert key in loaded


@pytest.mark.parametrize(
    "file_size,expected",
    [
        (0, "0 B"),
        (512, "512 B"),
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (1024 * 1024, "1.0 MB"),
        (2.5 * 1024 * 1024, "2.5 MB"),
        (1024 * 1024 * 1024, "1.0 GB"),
    ],
)
def test_format_file_size_parametrized(file_size, expected):
    """Parametrized test for file size formatting."""
    assert format_file_size(file_size) == expected


@pytest.mark.parametrize("theme_name", ["dark", "light"])
def test_all_themes_have_required_colors(theme_name):
    """Test that all themes have required color keys."""
    theme = THEME_COLORS[theme_name]
    required_keys = [
        "background",
        "secondary_background",
        "text",
        "primary",
        "success",
        "warning",
        "error",
    ]

    for key in required_keys:
        assert key in theme, f"Theme '{theme_name}' missing '{key}'"
        assert theme[key].startswith("#"), f"Theme color should be hex"
        assert len(theme[key]) == 7, f"Theme color should be 7 chars (#RRGGBB)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
