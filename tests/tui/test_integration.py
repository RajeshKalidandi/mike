"""Integration tests for Mike TUI."""

import pytest


class TestTUIApp:
    """Integration tests for the TUI application."""

    def test_app_creation(self, temp_db_path):
        """Test that MikeApp can be created."""
        from mike.tui.app import MikeApp

        app = MikeApp(db_path=temp_db_path, theme="dark")
        assert app is not None
        assert app.ui_theme == "dark"
        assert app.db_path == temp_db_path

    def test_app_with_light_theme(self, temp_db_path):
        """Test app creation with light theme."""
        from mike.tui.app import MikeApp

        app = MikeApp(db_path=temp_db_path, theme="light")
        assert app.ui_theme == "light"
        assert "light" in app.CSS_PATHS[1]

    def test_app_widgets_exist(self, temp_db_path):
        """Test that all main widgets can be imported."""
        from mike.tui.app import MikeApp
        from mike.tui.widgets.sidebar import Sidebar
        from mike.tui.widgets.status_bar import StatusBar
        from mike.tui.widgets.notifications import NotificationContainer

        app = MikeApp(db_path=temp_db_path)
        # Widget classes exist
        assert Sidebar is not None
        assert StatusBar is not None
        assert NotificationContainer is not None


class TestScreens:
    """Tests for screen functionality."""

    def test_all_screens_importable(self):
        """Test that all screens can be imported."""
        from mike.tui.screens.dashboard import DashboardScreen
        from mike.tui.screens.sessions import SessionsScreen
        from mike.tui.screens.session_detail import SessionDetailScreen
        from mike.tui.screens.logs import LogsScreen
        from mike.tui.screens.help import HelpScreen

        assert DashboardScreen is not None
        assert SessionsScreen is not None
        assert SessionDetailScreen is not None
        assert LogsScreen is not None
        assert HelpScreen is not None

    def test_dashboard_bindings(self):
        """Test dashboard has required bindings."""
        from mike.tui.screens.dashboard import DashboardScreen

        bindings = DashboardScreen.BINDINGS
        assert any(b[0] == "r" for b in bindings)

    def test_sessions_bindings(self):
        """Test sessions screen has required bindings."""
        from mike.tui.screens.sessions import SessionsScreen

        bindings = SessionsScreen.BINDINGS
        assert any(b[0] == "r" for b in bindings)
        assert any(b[0] == "d" for b in bindings)
        assert any(b[0] == "enter" for b in bindings)


class TestWidgets:
    """Tests for widget functionality."""

    def test_file_tree_builds_structure(self, mock_files_data):
        """Test that FileTree builds correct structure from files."""
        from mike.tui.widgets.file_tree import FileTree

        tree = FileTree(mock_files_data)
        # Tree should have root "Files"
        assert tree.root.label.plain == "Files"
        # Should have children
        assert len(tree.root.children) > 0

    def test_notification_levels(self):
        """Test notification supports all levels."""
        from mike.tui.widgets.notifications import Notification

        for level in ["info", "warning", "error", "success"]:
            notification = Notification(f"Test {level}", level=level)
            assert notification.level == level


class TestCLIIntegration:
    """Tests for CLI integration."""

    def test_launch_tui_function(self):
        """Test that launch_tui function exists and imports correctly."""
        from mike.tui import launch_tui
        import inspect

        assert callable(launch_tui)
        sig = inspect.signature(launch_tui)
        params = list(sig.parameters.keys())
        assert "db_path" in params
        assert "theme" in params


class TestThemeSupport:
    """Tests for theme support."""

    def test_theme_switching(self, temp_db_path):
        """Test theme can be switched."""
        from mike.tui.app import MikeApp

        app = MikeApp(db_path=temp_db_path, theme="dark")
        assert app.ui_theme == "dark"

        # Switch to light
        app.ui_theme = "light"
        assert app.ui_theme == "light"

    def test_both_themes_exist(self):
        """Test that both CSS files exist."""
        from pathlib import Path

        base_path = (
            Path(__file__).parent.parent.parent / "src" / "mike" / "tui" / "styles"
        )

        dark_css = base_path / "dark.tcss"
        light_css = base_path / "light.tcss"
        base_css = base_path / "base.tcss"

        assert dark_css.exists(), "dark.tcss should exist"
        assert light_css.exists(), "light.tcss should exist"
        assert base_css.exists(), "base.tcss should exist"
