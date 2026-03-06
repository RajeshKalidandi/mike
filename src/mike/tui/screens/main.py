"""Main interface screen for Mike TUI - Claude Code inspired layout."""

from textual.screen import Screen
from textual.widgets import Static, TextArea, RichLog
from textual.containers import Vertical
from textual.reactive import reactive
from textual.events import Key
from typing import List


class MainScreen(Screen):
    """Main screen with command input - Claude Code style."""

    BINDINGS = [
        ("ctrl+t", "toggle_theme", "Theme"),
        ("question_mark", "show_help", "Help"),
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command_history: List[str] = []
        self.current_model = "ollama/llama3.2"
        self.available_models = {
            "ollama": ["llama3.2", "mistral", "codellama", "phi4"],
            "groq": ["llama-3.2-90b", "mixtral-8x7b"],
            "openrouter": ["claude-3.5-sonnet", "gpt-4o"],
        }

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

        # Add to history
        self.command_history.append(command)

        log = self.query_one("#output-log", RichLog)
        log.write(f"[blue]>{command}[/blue]")

        self.process_command(command)
        # Clear input after submission
        text_area.text = ""

    def process_command(self, command: str):
        """Process the entered command."""
        log = self.query_one("#output-log", RichLog)

        if command.startswith("/"):
            cmd_parts = command[1:].split()
            cmd = cmd_parts[0].lower() if cmd_parts else ""
            args = cmd_parts[1:] if len(cmd_parts) > 1 else []

            if cmd == "scan":
                self.cmd_scan(args, log)
            elif cmd == "sessions":
                self.app.switch_screen("sessions")
            elif cmd == "help":
                self.show_help()
            elif cmd == "quit":
                self.app.exit()
            elif cmd == "clear":
                self.cmd_clear(log)
            elif cmd == "model":
                self.cmd_model(args, log)
            elif cmd == "models":
                self.cmd_models(log)
            elif cmd == "theme":
                self.cmd_theme(args, log)
            elif cmd == "history":
                self.cmd_history(log)
            elif cmd == "logs":
                self.app.switch_screen("logs")
            elif cmd == "settings":
                self.cmd_settings(log)
            elif cmd == "status":
                self.cmd_status(log)
            elif cmd == "agents":
                self.cmd_agents(log)
            elif cmd == "agent":
                self.cmd_agent(args, log)
            elif cmd == "config":
                self.cmd_config(args, log)
            else:
                log.write(f"[red]Unknown command:[/red] {cmd}")
                log.write("Type /help to see available commands.")
        else:
            # Natural language query
            log.write("[dim]Processing...[/dim]")
            # TODO: Send to agent for processing
            log.write(f"[dim]Query received: {command}[/dim]")

    def cmd_scan(self, args: list, log):
        """Handle /scan command."""
        if args:
            path = " ".join(args)
            log.write(f"[yellow]Scanning {path}...[/yellow]")
            log.write(
                "[dim]This will analyze the codebase structure and dependencies.[/dim]"
            )
        else:
            log.write("[red]Usage:[/red] /scan <path>")
            log.write("[dim]Example: /scan ./src or /scan /home/user/project[/dim]")

    def cmd_clear(self, log):
        """Handle /clear command."""
        log.clear()
        log.write("[dim]Screen cleared.[/dim]")

    def cmd_model(self, args: list, log):
        """Handle /model command - switch models."""
        if not args:
            log.write(f"[bold]Current model:[/bold] {self.current_model}")
            log.write("")
            log.write("[bold]Available providers:[/bold]")
            for provider, models in self.available_models.items():
                log.write(f"  [cyan]{provider}[/cyan]: {', '.join(models)}")
            log.write("")
            log.write("[dim]Usage: /model <provider>/<model>[/dim]")
            log.write(
                "[dim]Example: /model ollama/mistral or /model groq/llama-3.2-90b[/dim]"
            )
            return

        model_spec = args[0]
        if "/" in model_spec:
            provider, model = model_spec.split("/", 1)
            if provider in self.available_models:
                if model in self.available_models[provider]:
                    self.current_model = model_spec
                    log.write(f"[green]✓[/green] Switched to {model_spec}")
                    self.app.notify(
                        f"Model changed to {model_spec}", severity="success"
                    )
                else:
                    available = ", ".join(self.available_models[provider])
                    log.write(
                        f"[red]Error:[/red] Model '{model}' not available for {provider}"
                    )
                    log.write(f"[dim]Available: {available}[/dim]")
            else:
                log.write(f"[red]Error:[/red] Unknown provider '{provider}'")
                log.write(
                    f"[dim]Available providers: {', '.join(self.available_models.keys())}[/dim]"
                )
        else:
            log.write("[red]Usage:[/red] /model <provider>/<model>")
            log.write("[dim]Example: /model ollama/mistral[/dim]")

    def cmd_models(self, log):
        """Handle /models command - list all available models."""
        log.write("[bold]Available Models[/bold]")
        log.write("")
        for provider, models in self.available_models.items():
            log.write(f"[bold cyan]{provider}[/bold cyan]")
            for model in models:
                indicator = "●" if f"{provider}/{model}" == self.current_model else "○"
                log.write(f"  {indicator} {model}")
            log.write("")
        log.write(f"[dim]Current: {self.current_model}[/dim]")
        log.write("[dim]Use /model <provider>/<model> to switch[/dim]")

    def cmd_theme(self, args: list, log):
        """Handle /theme command."""
        if not args:
            current = self.app.ui_theme
            log.write(f"[bold]Current theme:[/bold] {current}")
            log.write("")
            log.write("[bold]Available themes:[/bold]")
            log.write("  ● dark" if current == "dark" else "  ○ dark")
            log.write("  ● light" if current == "light" else "  ○ light")
            log.write("")
            log.write("[dim]Usage: /theme <dark|light> or use Ctrl+T to toggle[/dim]")
            return

        theme = args[0].lower()
        if theme in ["dark", "light"]:
            if theme != self.app.ui_theme:
                self.app.ui_theme = theme
                log.write(f"[green]✓[/green] Theme set to {theme}")
            else:
                log.write(f"[dim]Theme is already set to {theme}[/dim]")
        else:
            log.write("[red]Error:[/red] Theme must be 'dark' or 'light'")

    def cmd_history(self, log):
        """Handle /history command."""
        if not self.command_history:
            log.write("[dim]No commands in history.[/dim]")
            return

        log.write("[bold]Command History[/bold]")
        log.write("")
        # Show last 20 commands
        for i, cmd in enumerate(self.command_history[-20:], 1):
            log.write(f"  {i:2}. {cmd}")

    def cmd_settings(self, log):
        """Handle /settings command."""
        log.write("[bold]Mike Settings[/bold]")
        log.write("")
        log.write(f"[cyan]Model:[/cyan]         {self.current_model}")
        log.write(f"[cyan]Theme:[/cyan]         {self.app.ui_theme}")
        log.write(
            f"[cyan]Database:[/cyan]      {getattr(self.app, 'db_path', 'default')}"
        )
        log.write("")
        log.write("[dim]Use /model, /theme to change settings[/dim]")
        log.write("[dim]Config file: ~/.mike/config.json[/dim]")

    def cmd_status(self, log):
        """Handle /status command."""
        log.write("[bold]System Status[/bold]")
        log.write("")
        log.write("[green]●[/green] TUI Running")
        log.write(f"[cyan]●[/cyan] Model: {self.current_model}")
        log.write(f"[cyan]●[/cyan] Theme: {self.app.ui_theme}")
        log.write("")
        log.write("[dim]Use /sessions to view active sessions[/dim]")

    def cmd_agents(self, log):
        """Handle /agents command."""
        agents = [
            ("documentation", "Generate docs from code"),
            ("qa", "Answer questions about codebase"),
            ("refactor", "Suggest code improvements"),
            ("rebuilder", "Generate new code from templates"),
        ]
        log.write("[bold]Available Agents[/bold]")
        log.write("")
        for name, desc in agents:
            log.write(f"  [cyan]{name:15}[/cyan] {desc}")
        log.write("")
        log.write("[dim]Use /agent <name> to activate an agent[/dim]")

    def cmd_agent(self, args: list, log):
        """Handle /agent command."""
        if not args:
            log.write("[red]Usage:[/red] /agent <name>")
            log.write("[dim]Use /agents to see available agents[/dim]")
            return

        agent_name = args[0].lower()
        valid_agents = ["documentation", "qa", "refactor", "rebuilder"]

        if agent_name in valid_agents:
            log.write(f"[green]✓[/green] Activated [cyan]{agent_name}[/cyan] agent")
            log.write(f"[dim]This agent will handle your next queries.[/dim]")
            # TODO: Set active agent in app state
        else:
            log.write(f"[red]Error:[/red] Unknown agent '{agent_name}'")
            log.write(f"[dim]Available: {', '.join(valid_agents)}[/dim]")

    def cmd_config(self, args: list, log):
        """Handle /config command."""
        if not args:
            log.write("[bold]Configuration[/bold]")
            log.write("")
            log.write("Available config commands:")
            log.write("  /config show       Show current configuration")
            log.write("  /config edit       Open config in editor")
            log.write("  /config reset      Reset to defaults")
            log.write("")
            log.write("[dim]Config location: ~/.mike/config.json[/dim]")
            return

        subcmd = args[0].lower()
        if subcmd == "show":
            log.write("[bold]Current Configuration[/bold]")
            log.write("")
            log.write("{")
            log.write(f'  "model": "{self.current_model}",')
            log.write(f'  "theme": "{self.app.ui_theme}",')
            log.write('  "auto_save": true,')
            log.write('  "max_context": 128000')
            log.write("}")
        elif subcmd == "edit":
            log.write("[yellow]Opening config editor...[/yellow]")
            log.write(
                "[dim]Not yet implemented. Edit ~/.mike/config.json manually.[/dim]"
            )
        elif subcmd == "reset":
            log.write("[yellow]Resetting configuration to defaults...[/yellow]")
            log.write("[dim]Not yet implemented.[/dim]")
        else:
            log.write(f"[red]Unknown config command:[/red] {subcmd}")

    def show_help(self):
        """Show help in output area."""
        log = self.query_one("#output-log", RichLog)
        log.write("")
        log.write("[bold cyan]Mike Commands[/bold cyan]")
        log.write("")

        log.write("[bold]Core:[/bold]")
        log.write("  /scan <path>        Scan and analyze codebase")
        log.write("  /sessions           View active sessions")
        log.write("  /clear              Clear output screen")
        log.write("  /quit               Exit application")
        log.write("")

        log.write("[bold]AI Model:[/bold]")
        log.write("  /model              Show current model & switch")
        log.write("  /model <p>/<m>      Switch to provider/model")
        log.write("  /models             List all available models")
        log.write("")

        log.write("[bold]Agents:[/bold]")
        log.write("  /agents             List available agents")
        log.write("  /agent <name>       Activate specific agent")
        log.write("")

        log.write("[bold]Customization:[/bold]")
        log.write("  /theme              Show/set theme (dark/light)")
        log.write("  /settings           View current settings")
        log.write("  /config             Manage configuration")
        log.write("")

        log.write("[bold]System:[/bold]")
        log.write("  /status             Show system status")
        log.write("  /logs               View application logs")
        log.write("  /history            Show command history")
        log.write("  /help               Show this help")
        log.write("")

        log.write("[bold]Shortcuts:[/bold]")
        log.write("  Enter               Submit command")
        log.write("  Shift+Enter         New line in input")
        log.write("  ?                   Show help screen")
        log.write("  Ctrl+T              Toggle light/dark theme")
        log.write("  Ctrl+C              Exit")
        log.write("")

    def action_toggle_theme(self):
        """Toggle theme."""
        self.app.action_toggle_theme()

    def action_show_help(self):
        """Show help screen."""
        self.app.push_screen("help")
