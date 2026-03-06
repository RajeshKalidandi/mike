"""Main TUI Application for Mike - Modern interface inspired by Claude Code."""

from pathlib import Path
from textual.app import App, ComposeResult
from textual.reactive import reactive

from mike.tui.screens.welcome import WelcomeScreen
from mike.tui.screens.main import MainScreen
from mike.tui.screens.sessions import SessionsScreen
from mike.tui.screens.session_detail import SessionDetailScreen
from mike.tui.screens.logs import LogsScreen
from mike.tui.screens.help import HelpScreen

# Get the directory containing this file
TUI_DIR = Path(__file__).parent


class MikeApp(App):
    """Main Mike TUI Application."""

    # CSS paths relative to this file's directory
    CSS_PATH = [
        TUI_DIR / "styles" / "base.tcss",
        TUI_DIR / "styles" / "dark.tcss",
    ]

    TITLE = "Mike"
    SUB_TITLE = "Local AI Software Architect"

    SCREENS = {
        "welcome": WelcomeScreen,
        "main": MainScreen,
        "sessions": SessionsScreen,
        "session_detail": SessionDetailScreen,
        "logs": LogsScreen,
        "help": HelpScreen,
    }

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("question_mark", "action_show_help", "Help"),
        ("ctrl+t", "toggle_theme", "Toggle Theme"),
    ]

    ui_theme = reactive("dark")

    def __init__(self, db_path: str = None, theme: str = "dark", **kwargs):
        self.db_path = db_path
        # Set CSS paths based on theme before super().__init__
        self._set_theme_css_paths(theme)
        super().__init__(**kwargs)
        self.ui_theme = theme  # Set reactive after super().__init__()

    def _set_theme_css_paths(self, theme: str):
        """Set CSS paths based on the current theme."""
        self.CSS_PATH = [
            TUI_DIR / "styles" / "base.tcss",
            TUI_DIR / "styles" / f"{theme}.tcss",
        ]

    def on_mount(self):
        """Handle app mount."""
        self.push_screen("welcome")

    def action_show_help(self):
        """Show help screen."""
        self.push_screen("help")

    def watch_ui_theme(self, theme: str):
        """Watch for theme changes and update CSS paths."""
        self._set_theme_css_paths(theme)
        self.refresh_css()
        # Only notify if app is mounted (screen stack exists)
        try:
            _ = self.screen
            self.notify(f"Theme changed to {theme}", severity="information")
        except Exception:
            pass  # App not yet mounted, skip notification

    def action_toggle_theme(self):
        """Toggle between light and dark themes."""
        self.ui_theme = "light" if self.ui_theme == "dark" else "dark"

    def notify(self, message: str, severity: str = "information", **kwargs):
        """Show a notification toast."""
        level_map = {
            "information": "info",
            "warning": "warning",
            "error": "error",
            "success": "success",
        }
        level = level_map.get(severity, "info")

        try:
            from mike.tui.widgets.notifications import NotificationContainer

            container = self.query_one("#notifications", NotificationContainer)
            container.notify(message, level)
        except Exception:
            # Fallback if notifications not available
            pass


def safe_action(func):
    """Decorator to catch exceptions in actions and show notification."""

    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            self.app.notify(f"Error: {str(e)}", severity="error")

    return wrapper
