"""Tests for theme support."""


def test_theme_loading():
    """Test that themes can be loaded."""
    from mike.tui.app import MikeApp

    # Test dark theme
    app = MikeApp(theme="dark")
    assert app.ui_theme == "dark"
    assert "dark" in app.CSS_PATHS[1]

    # Test light theme
    app = MikeApp(theme="light")
    assert app.ui_theme == "light"
    assert "light" in app.CSS_PATHS[1]


def test_light_css_exists():
    """Test that light.tcss file exists."""
    from pathlib import Path

    css_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "mike"
        / "tui"
        / "styles"
        / "light.tcss"
    )
    assert css_path.exists(), "light.tcss should exist"
