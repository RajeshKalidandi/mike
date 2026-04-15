"""Status bar widget for Mike TUI."""

from textual.widgets import Static
from textual.reactive import reactive


class StatusBar(Static):
    """Bottom status bar showing current mode and hints."""

    mode = reactive("Dashboard")
    message = reactive("")

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        content-align: center middle;
    }
    """

    def compose(self):
        """Compose the status bar."""
        yield Static(self.render_content(), id="status-content")

    def render_content(self) -> str:
        """Render status content."""
        hints = "[1]Dashboard [2]Sessions [3]Logs [?]Help [q]Quit"
        if self.message:
            return f" {self.mode} | {self.message} | {hints}"
        return f" {self.mode} | {hints}"

    def watch_mode(self, mode: str):
        """Update when mode changes."""
        self.update(self.render_content())

    def watch_message(self, message: str):
        """Update when message changes."""
        self.update(self.render_content())

    def set_message(self, message: str):
        """Set a temporary message."""
        self.message = message
