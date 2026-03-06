"""Main interface screen for Mike TUI - Claude Code inspired layout."""

from textual.screen import Screen
from textual.widgets import Static, TextArea, RichLog
from textual.containers import Vertical
from textual.reactive import reactive
from textual.events import Key


class MainScreen(Screen):
    """Main screen with command input - Claude Code style."""

    BINDINGS = [
        ("ctrl+t", "toggle_theme", "Theme"),
        ("question_mark", "show_help", "Help"),
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
    ]

    def compose(self):
        """Compose the main screen with header, output, input, and footer."""
        with Vertical(id="main-container"):
            # Header bar
            yield Static("Mike  —  Local AI Software Architect", id="header-bar")

            # Output area (grows upward)
            yield RichLog(id="output-log", highlight=True, markup=True)

            # Dotted separator line
            yield Static("╌" * 100, id="input-separator")

            # TextArea input with rounded border
            yield TextArea(
                text="", id="command-input", soft_wrap=True, tab_behavior="indent"
            )

            # Hint footer
            yield Static(
                "enter submit · shift+enter newline · ? help · ctrl+t theme",
                id="input-hints",
            )

    def on_mount(self):
        """Initialize the screen."""
        self.show_welcome_message()
        # Focus the TextArea and position cursor at end
        input_widget = self.query_one("#command-input", TextArea)
        input_widget.focus()

    def show_welcome_message(self):
        """Show initial message in output area."""
        log = self.query_one("#output-log", RichLog)
        log.write("")
        log.write("[bold cyan]Mike[/bold cyan]  —  Local AI Software Architect")
        log.write("")
        log.write("Type /help for available commands or just ask me anything.")
        log.write("")

    def on_key(self, event: Key) -> None:
        """Handle key events - intercept Enter for submission."""
        # Only handle when TextArea is focused
        try:
            text_area = self.query_one("#command-input", TextArea)
            if not text_area.has_focus:
                return
        except Exception:
            return

        # Check for Enter key
        if event.key == "enter":
            if not event.shift:  # Enter without Shift = submit
                event.stop()  # Prevent TextArea from handling
                event.prevent_default()
                self.submit_command()
            # Shift+Enter will pass through and insert newline

    def submit_command(self):
        """Submit the current command."""
        text_area = self.query_one("#command-input", TextArea)
        command = text_area.text.strip()

        if not command:
            return

        log = self.query_one("#output-log", RichLog)
        log.write(f"[blue]>{command}[/blue]")

        self.process_command(command)
        # Clear input after submission
        text_area.text = ""

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
            elif cmd == "quit":
                self.app.exit()
            else:
                log.write(f"[red]Unknown command:[/red] {cmd}")
        else:
            # Natural language query
            log.write("[dim]Processing...[/dim]")
            # TODO: Send to agent for processing
            log.write(f"[dim]Query received: {command}[/dim]")

    def show_help(self):
        """Show help in output area."""
        log = self.query_one("#output-log", RichLog)
        log.write("")
        log.write("[bold]Commands:[/bold]")
        log.write("  /scan <path>   Scan codebase")
        log.write("  /sessions      View sessions")
        log.write("  /help          Show help")
        log.write("  /quit          Exit")
        log.write("")
        log.write("[bold]Shortcuts:[/bold]")
        log.write("  Enter          Submit command")
        log.write("  Shift+Enter    New line in input")
        log.write("  ?              Show help screen")
        log.write("  Ctrl+T         Toggle light/dark theme")
        log.write("  Ctrl+C         Exit")
        log.write("")

    def action_toggle_theme(self):
        """Toggle theme."""
        self.app.action_toggle_theme()

    def action_show_help(self):
        """Show help screen."""
        self.app.push_screen("help")
