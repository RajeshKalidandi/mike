"""Tests for help screen."""


def test_help_screen_imports():
    """Test that HelpScreen can be imported."""
    from mike.tui.screens.help import HelpScreen

    assert HelpScreen is not None
