"""Tests for TUI app."""

import pytest


def test_app_imports():
    """Test that MikeApp can be imported."""
    from mike.tui.app import MikeApp

    assert MikeApp is not None


def test_dashboard_imports():
    """Test that DashboardScreen can be imported."""
    from mike.tui.screens.dashboard import DashboardScreen

    assert DashboardScreen is not None


def test_sidebar_imports():
    """Test that Sidebar can be imported."""
    from mike.tui.widgets.sidebar import Sidebar

    assert Sidebar is not None


def test_status_bar_imports():
    """Test that StatusBar can be imported."""
    from mike.tui.widgets.status_bar import StatusBar

    assert StatusBar is not None
