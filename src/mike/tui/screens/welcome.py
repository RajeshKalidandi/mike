"""Welcome screen for Mike TUI - Minimal and clean."""

from textual.screen import Screen
from textual.widgets import Static
from textual.containers import Vertical


MIKE_LOGO = """
 ███╗   ███╗██╗██╗  ██╗███████╗
 ████╗ ████║██║██║ ██╔╝██╔════╝
 ██╔████╔██║██║█████╔╝ █████╗  
 ██║╚██╔╝██║██║██╔═██╗ ██╔══╝  
 ██║ ╚═╝ ██║██║██║  ██╗███████╗
 ╚═╝     ╚═╝╚═╝╚═╝  ╚═╝╚══════╝
"""


class WelcomeScreen(Screen):
    """Minimal welcome screen."""

    BINDINGS = [
        ("enter", "continue", "Continue"),
        ("q", "quit", "Quit"),
    ]

    def compose(self):
        """Compose the welcome screen."""
        with Vertical(id="welcome-container"):
            yield Static(MIKE_LOGO, id="welcome-logo")
            yield Static("Mike — Local AI Software Architect", id="welcome-title")
            yield Static("Press Enter to continue", id="welcome-hint")

    def action_continue(self):
        """Continue to main interface."""
        self.app.switch_screen("main")

    def action_quit(self):
        """Quit the application."""
        self.app.exit()
