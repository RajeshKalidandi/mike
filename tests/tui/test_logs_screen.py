"""Tests for logs screen."""


def test_logs_screen_imports():
    """Test that LogsScreen can be imported."""
    from mike.tui.screens.logs import LogsScreen

    assert LogsScreen is not None
