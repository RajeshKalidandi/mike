"""Main interface screen for Mike TUI - Minimal and clean."""

from textual.screen import Screen
from textual.widgets import Static, Input, RichLog
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from textual.worker import Worker


class MainScreen(Screen):
    """Main screen with command input."""

    BINDINGS = [
        ("ctrl+t", "toggle_theme", "Theme"),
        ("question_mark", "show_help", "Help"),
        ("q", "quit", "Quit"),
    ]

    def compose(self):
        """Compose the main screen."""
        with Vertical(id="main-container"):
            # Output area
            yield RichLog(id="output-log", highlight=True, markup=True)

            # Input area
            with Horizontal(id="input-container"):
                yield Static("❯", id="input-prompt")
                yield Input(placeholder="Type a command...", id="command-input")

    def on_mount(self):
        """Initialize the screen."""
        self.show_welcome_message()
        self.query_one("#command-input", Input).focus()

    def show_welcome_message(self):
        """Show initial message."""
        log = self.query_one("#output-log", RichLog)
        log.write("[bold cyan]Mike[/bold cyan] — Local AI Software Architect")
        log.write("")
        log.write("Type /help for available commands or just ask me anything.")
        log.write("")

    def on_input_submitted(self, event: Input.Submitted):
        """Handle command submission."""
        command = event.value.strip()
        if not command:
            return

        log = self.query_one("#output-log", RichLog)
        log.write(f"[blue]>[/blue] {command}")

        self.process_command(command)
        event.input.value = ""

    def process_command(self, command: str):
        """Process the entered command."""
        log = self.query_one("#output-log", RichLog)

        if command.startswith("/"):
            cmd = command[1:].split()[0].lower()
            args = command[1:].split()[1:]

            if cmd == "scan":
                if args:
                    log.write("[yellow]Scanning...[/yellow]")
                else:
                    log.write("[red]Usage:[/red] /scan <path>")
            elif cmd == "sessions":
                self.app.switch_screen("sessions")
            elif cmd == "help":
                self.show_help()
            else:
                log.write(f"[red]Unknown:[/red] {cmd}")
        else:
            log.write("[dim]Processing...[/dim]")

    def show_help(self):
        """Show help."""
        log = self.query_one("#output-log", RichLog)
        log.write("")
        log.write("Commands:")
        log.write("  /scan <path>   Scan codebase")
        log.write("  /sessions      View sessions")
        log.write("  /help          Show help")
        log.write("  /quit          Exit")
        log.write("")

    def action_toggle_theme(self):
        """Toggle theme."""
        self.app.action_toggle_theme()

    def action_show_help(self):
        """Show help screen."""
        self.app.push_screen("help")
