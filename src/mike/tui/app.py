"""Main TUI Application for Mike."""

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive

from mike.tui.screens.dashboard import DashboardScreen
from mike.tui.screens.sessions import SessionsScreen
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
    }

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("question_mark", "push_screen('help')", "Help"),
        ("1", "switch_screen('dashboard')", "Dashboard"),
        ("2", "switch_screen('sessions')", "Sessions"),
        ("3", "action_not_implemented", "Logs"),
    ]

    theme = reactive("dark")

    def __init__(self, db_path: str = None, theme: str = "dark", **kwargs):
        self.db_path = db_path
        self.theme = theme
        super().__init__(**kwargs)

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
            status_bar.set_message("Logs screen not yet implemented")

    def action_not_implemented(self):
        """Show not implemented message."""
        status_bar = self.query_one(StatusBar)
        status_bar.set_message("Feature coming soon...")
