"""Tests for session detail screen."""


def test_session_detail_imports():
    """Test that SessionDetailScreen can be imported."""
    from mike.tui.screens.session_detail import SessionDetailScreen

    assert SessionDetailScreen is not None


def test_file_tree_imports():
    """Test that FileTree can be imported."""
    from mike.tui.widgets.file_tree import FileTree

    assert FileTree is not None
