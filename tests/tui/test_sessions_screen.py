"""Tests for sessions screen."""


def test_sessions_screen_imports():
    """Test that SessionsScreen can be imported."""
    from mike.tui.screens.sessions import SessionsScreen

    assert SessionsScreen is not None


def test_session_card_imports():
    """Test that SessionCard can be imported."""
    from mike.tui.widgets.session_card import SessionCard

    assert SessionCard is not None
