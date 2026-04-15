"""Tests for theme support."""


def test_theme_loading():
    """Test that themes can be loaded."""
    from mike.tui.app import MikeApp

    # Test dark theme
    app = MikeApp(theme="dark")
    assert app.ui_theme == "dark"
    css_paths = [str(p) for p in app.CSS_PATH]
    assert any("dark" in p for p in css_paths)

    # Test light theme
    app = MikeApp(theme="light")
    assert app.ui_theme == "light"
    css_paths = [str(p) for p in app.CSS_PATH]
    assert any("light" in p for p in css_paths)


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
