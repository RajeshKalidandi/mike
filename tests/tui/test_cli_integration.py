"""Tests for CLI integration."""

from click.testing import CliRunner
from mike.cli import main


def test_tui_command_exists():
    """Test that 'tui' command exists."""
    runner = CliRunner()
    result = runner.invoke(main, ["tui", "--help"])
    assert result.exit_code == 0
    assert "TUI" in result.output or "interface" in result.output.lower()


def test_tui_theme_option():
    """Test that --theme option exists."""
    runner = CliRunner()
    result = runner.invoke(main, ["tui", "--help"])
    assert result.exit_code == 0
    assert "--theme" in result.output
    assert "dark" in result.output
    assert "light" in result.output
