"""Main TUI Application for Mike."""

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive

from mike.tui.screens.dashboard import DashboardScreen
from mike.tui.screens.sessions import SessionsScreen
from mike.tui.screens.session_detail import SessionDetailScreen
from mike.tui.screens.logs import LogsScreen
from mike.tui.screens.help import HelpScreen
from mike.tui.widgets.sidebar import Sidebar
from mike.tui.widgets.status_bar import StatusBar


class MikeApp(App):
    """Main Mike TUI Application."""

    CSS_PATHS = [
        "styles/base.tcss",
        "styles/dark.tcss",
    ]

    TITLE = "Mike"
    SUB_TITLE = "Local AI Software Architect"

    SCREENS = {
        "dashboard": DashboardScreen,
        "sessions": SessionsScreen,
        "session_detail": SessionDetailScreen,
        "logs": LogsScreen,
    }

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("question_mark", "action_show_help", "Help"),
        ("1", "switch_screen('dashboard')", "Dashboard"),
        ("2", "switch_screen('sessions')", "Sessions"),
        ("3", "switch_screen('logs')", "Logs"),
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
        self.CSS_PATHS = [
            "styles/base.tcss",
            f"styles/{theme}.tcss",
        ]

    def compose(self) -> ComposeResult:
        """Compose the main app layout."""
        with Horizontal():
            yield Sidebar()
            with Vertical(id="content"):
                yield DashboardScreen()
        yield StatusBar()

    def on_mount(self):
        """Handle app mount."""
        self.push_screen("dashboard")
        status_bar = self.query_one(StatusBar)
        status_bar.mode = "Dashboard"

    def on_sidebar_selected(self, event: Sidebar.Selected):
        """Handle sidebar navigation."""
        status_bar = self.query_one(StatusBar)
        status_bar.mode = event.item

        if event.item == "Dashboard":
            self.switch_screen("dashboard")
        elif event.item == "Sessions":
            self.switch_screen("sessions")
        elif event.item == "Logs":
            self.switch_screen("logs")

    def action_not_implemented(self):
        """Show not implemented message."""
        status_bar = self.query_one(StatusBar)
        status_bar.set_message("Feature coming soon...")

    def action_show_help(self):
        """Show help screen."""
        self.push_screen(HelpScreen())

    def watch_ui_theme(self, theme: str):
        """Watch for theme changes and update CSS paths."""
        self._set_theme_css_paths(theme)
        self.refresh_css()
        self.notify(f"Theme changed to {theme}", severity="information")

    def action_toggle_theme(self):
        """Toggle between light and dark themes."""
        self.ui_theme = "light" if self.ui_theme == "dark" else "dark"
