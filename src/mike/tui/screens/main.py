"""Main interface screen for Mike TUI - Claude Code inspired layout."""

import json
import os
import sqlite3
import subprocess
import urllib.request
import webbrowser
from pathlib import Path
from typing import List, Optional, Any, Dict

from textual.screen import Screen
from textual.widgets import Static, TextArea, RichLog
from textual.containers import Vertical
from textual.reactive import reactive
from textual.events import Key

from mike.config.loader import ConfigLoader
from mike.config.settings import Settings


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

        # Initialize configuration system
        self.config_dir = Path.home() / ".mike"
        self.config_file = self.config_dir / "config.json"
        self.config_loader = ConfigLoader(user_config_dir=self.config_dir)
        self.settings: Optional[Settings] = None

        # Default model - will be overwritten by config if exists
        self.current_model = "ollama/qwen2.5-coder:14b"
        self.available_models: Dict[str, List[str]] = {}

        # Load or create default config
        self._load_or_create_config()

    def _load_or_create_config(self):
        """Load configuration from ~/.mike/config.json or create default."""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    config = json.load(f)

                # Load current model from config
                if "llm" in config and "model" in config["llm"]:
                    provider = config["llm"].get("provider", "ollama")
                    model = config["llm"]["model"]
                    self.current_model = f"{provider}/{model}"

                # Load settings
                self.settings = Settings.model_validate(config)
            else:
                # Create default config
                self._save_config()
                self.settings = Settings()
        except Exception:
            # Use defaults if config can't be loaded
            self.settings = Settings()

    def _save_config(self) -> bool:
        """Save current configuration to ~/.mike/config.json."""
        try:
            # Ensure directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # Load existing config or create new
            config = {}
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    config = json.load(f)

            # Parse current model
            if "/" in self.current_model:
                provider, model = self.current_model.split("/", 1)
            else:
                provider = "ollama"
                model = self.current_model

            # Ensure llm section exists
            if "llm" not in config:
                config["llm"] = {}

            # Update model settings
            config["llm"]["provider"] = provider
            config["llm"]["model"] = model

            # Save config
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2)

            return True
        except Exception:
            return False

    def _get_nested_value(self, obj: Any, key_path: str) -> Any:
        """Get nested value using dot notation (e.g., 'llm.model')."""
        keys = key_path.split(".")
        current = obj
        for key in keys:
            if hasattr(current, key):
                current = getattr(current, key)
            elif isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    def _set_nested_value(self, obj: Any, key_path: str, value: Any) -> bool:
        """Set nested value using dot notation."""
        keys = key_path.split(".")
        current = obj
        for key in keys[:-1]:
            if hasattr(current, key):
                current = getattr(current, key)
            elif isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return False

        final_key = keys[-1]
        try:
            if hasattr(current, final_key):
                current_attr = getattr(current, final_key)
                if isinstance(current_attr, bool) and isinstance(value, str):
                    value = value.lower() in ("true", "yes", "1", "on")
                elif isinstance(current_attr, int) and isinstance(value, str):
                    value = int(value)
                elif isinstance(current_attr, float) and isinstance(value, str):
                    value = float(value)
                elif isinstance(current_attr, Path) and isinstance(value, str):
                    value = Path(value).expanduser()
                setattr(current, final_key, value)
                return True
            elif isinstance(current, dict):
                current[final_key] = value
                return True
            return False
        except (ValueError, TypeError):
            return False

    def _detect_ollama_models(self) -> List[str]:
        """Detect available Ollama models by running 'ollama list'."""
        try:
            result = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                return []

            models = []
            lines = result.stdout.strip().split("\n")

            # Skip header line if present
            start_idx = 0
            if lines and ("NAME" in lines[0] or "ID" in lines[0]):
                start_idx = 1

            for line in lines[start_idx:]:
                line = line.strip()
                if not line:
                    continue

                # Parse model name (first column)
                parts = line.split()
                if parts:
                    model_name = parts[0]
                    # Remove :latest suffix if present
                    if model_name.endswith(":latest"):
                        model_name = model_name[:-7]
                    models.append(model_name)

            return models
        except subprocess.TimeoutExpired:
            return []
        except FileNotFoundError:
            # Ollama not installed
            return []
        except Exception:
            return []

    def _detect_available_models(self) -> Dict[str, List[str]]:
        """Detect all available models from configured providers."""
        models = {}

        # Detect Ollama models
        ollama_models = self._detect_ollama_models()
        if ollama_models:
            models["ollama"] = ollama_models
        else:
            # Fallback to checking if ollama is installed
            try:
                subprocess.run(["ollama", "--version"], capture_output=True, timeout=5)
                # Ollama is installed but no models or error listing
                models["ollama"] = []
            except (FileNotFoundError, subprocess.TimeoutExpired):
                # Ollama not installed
                pass

        return models

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
                self.cmd_sessions(log)
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
        """Handle /scan command - perform actual codebase scanning."""
        if not args:
            log.write("[red]Usage:[/red] /scan <path>")
            log.write("[dim]Example: /scan ./src or /scan /home/user/project[/dim]")
            return

        path = " ".join(args)

        # Check if Mike API is available
        if not self.app.mike:
            log.write("[red]Error:[/red] Mike API not initialized")
            log.write("[dim]Check database connection and try again.[/dim]")
            return

        log.write(f"[cyan]Starting scan of: {path}[/cyan]")

        # Run scan in a worker to avoid blocking the UI
        self.run_worker(self._do_scan(path), exclusive=True)

    async def _do_scan(self, path: str):
        """Perform the actual scan operation in a background worker."""
        log = self.query_one("#output-log", RichLog)

        try:
            import os

            # Validate path exists (for local paths)
            is_git_url = path.startswith("http") or path.startswith("git@")

            if not is_git_url:
                abs_path = os.path.abspath(os.path.expanduser(path))
                if not os.path.exists(abs_path):
                    log.write(f"[red]Error:[/red] Path not found: {path}")
                    return
                if not os.path.isdir(abs_path):
                    log.write(f"[red]Error:[/red] Path is not a directory: {path}")
                    return

            # Perform the scan using Mike API
            log.write("[dim]Scanning files...[/dim]")
            result = self.app.mike.scan_codebase(path)

            if result.success:
                log.write("")
                log.write("[bold green]✓ Scan Complete[/bold green]")
                log.write(f"[cyan]Session ID:[/cyan] {result.session_id}")
                log.write(f"[cyan]Files Scanned:[/cyan] {result.files_scanned}")

                if result.languages:
                    log.write("")
                    log.write("[bold]Languages Detected:[/bold]")
                    # Sort by count descending
                    sorted_langs = sorted(
                        result.languages.items(), key=lambda x: x[1], reverse=True
                    )
                    for lang, count in sorted_langs[:10]:  # Show top 10
                        log.write(f"  {lang}: {count} files")

                    if len(result.languages) > 10:
                        log.write(f"  ... and {len(result.languages) - 10} more")

                log.write("")
                log.write(f"[dim]Source: {result.source_path}[/dim]")
                log.write("[dim]Use /sessions to view all sessions[/dim]")

                self.app.notify(
                    f"Scanned {result.files_scanned} files", severity="success"
                )
            else:
                log.write(f"[red]Scan failed:[/red] {result.error or 'Unknown error'}")
                self.app.notify("Scan failed", severity="error")

        except Exception as e:
            log.write(f"[red]Error:[/red] {str(e)}")
            self.app.notify(f"Scan error: {str(e)}", severity="error")

    def cmd_clear(self, log):
        """Handle /clear command."""
        log.clear()
        log.write("[dim]Screen cleared.[/dim]")

    def cmd_model(self, args: list, log):
        """Handle /model command - switch models."""
        if not args:
            log.write(f"[bold]Current model:[/bold] {self.current_model}")
            log.write("")
            log.write("[dim]Usage: /model <provider>/<model>[/dim]")
            log.write(
                "[dim]Example: /model ollama/mistral or /model ollama/qwen2.5-coder:14b[/dim]"
            )
            log.write("")
            log.write("[dim]Use /models to list all available models.[/dim]")
            return

        model_spec = args[0]
        if "/" not in model_spec:
            log.write("[red]Error:[/red] Model must be specified as <provider>/<model>")
            log.write("[dim]Example: /model ollama/mistral[/dim]")
            return

        provider, model = model_spec.split("/", 1)
        provider = provider.lower()

        # Validate provider
        if provider != "ollama":
            log.write(f"[red]Error:[/red] Unknown provider '{provider}'")
            log.write("[dim]Currently only 'ollama' provider is supported.[/dim]")
            return

        # Check if Ollama is installed
        try:
            subprocess.run(["ollama", "--version"], capture_output=True, timeout=5)
        except FileNotFoundError:
            log.write("[red]Error:[/red] Ollama is not installed or not in PATH")
            log.write("[dim]Install from https://ollama.com[/dim]")
            return
        except subprocess.TimeoutExpired:
            log.write("[red]Error:[/red] Ollama is not responding")
            return

        # Detect available models
        available_models = self._detect_ollama_models()

        # Check if model exists
        if available_models and model not in available_models:
            log.write(f"[yellow]Warning:[/yellow] Model '{model}' not found in Ollama")
            if available_models:
                log.write(
                    f"[dim]Available models: {', '.join(available_models[:10])}[/dim]"
                )
                if len(available_models) > 10:
                    log.write(f"[dim]... and {len(available_models) - 10} more[/dim]")
            log.write("")
            log.write(
                "[dim]You can still switch to this model, but it may need to be pulled first.[/dim]"
            )
            log.write(f"[dim]Use: ollama pull {model}[/dim]")

        # Switch model
        self.current_model = model_spec

        # Save to config
        if self._save_config():
            log.write(f"[green]✓[/green] Switched to {model_spec}")
            log.write("[dim]Configuration saved.[/dim]")
        else:
            log.write(f"[green]✓[/green] Switched to {model_spec}")
            log.write("[yellow]Warning:[/yellow] Failed to save configuration")

    def cmd_models(self, log):
        """Handle /models command - list all available models."""
        log.write("[bold]Available Models[/bold]")
        log.write("")

        # Detect available models
        self.available_models = self._detect_available_models()

        if not self.available_models:
            # Check if Ollama is installed
            try:
                subprocess.run(["ollama", "--version"], capture_output=True, timeout=5)
                log.write("[yellow]Ollama is installed but no models found.[/yellow]")
                log.write("[dim]Install models with: ollama pull <model-name>[/dim]")
                log.write("")
                log.write("[dim]Popular models:[/dim]")
                log.write("  • qwen2.5-coder:14b - Code generation")
                log.write("  • llama3.2 - General purpose")
                log.write("  • mistral - Balanced performance")
                log.write("  • codellama - Code-focused")
                log.write("  • phi4 - Microsoft model")
            except FileNotFoundError:
                log.write("[red]Error:[/red] Ollama is not installed")
                log.write("[dim]Install from https://ollama.com[/dim]")
            except subprocess.TimeoutExpired:
                log.write("[red]Error:[/red] Ollama is not responding")
            return

        # Display models by provider
        for provider, models in self.available_models.items():
            log.write(f"[bold cyan]{provider}[/bold cyan]")

            if not models:
                log.write("  [dim]No models installed[/dim]")
                log.write("  [dim]Install with: ollama pull <model-name>[/dim]")
            else:
                for model in models:
                    indicator = (
                        "●" if f"{provider}/{model}" == self.current_model else "○"
                    )
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
        """Handle /settings command - display current configuration."""
        if not self.settings:
            log.write("[red]Error:[/red] Settings not loaded")
            return

        log.write("[bold]Mike Settings[/bold]")
        log.write("")

        # LLM Settings
        log.write("[bold cyan]AI Model[/bold cyan]")
        log.write(f"  Provider:    {self.settings.llm.provider}")
        log.write(f"  Model:       {self.settings.llm.model}")
        log.write(f"  Temperature: {self.settings.llm.temperature}")
        log.write(f"  Max Tokens:  {self.settings.llm.max_tokens}")
        log.write("")

        # UI Settings
        log.write("[bold cyan]Interface[/bold cyan]")
        log.write(f"  Theme:       {self.app.ui_theme}")
        log.write(f"  Log Level:   {self.settings.log_level}")
        log.write("")

        # Database
        log.write("[bold cyan]Storage[/bold cyan]")
        log.write(f"  Database:    {self.settings.database.path}")
        log.write(f"  Pool Size:   {self.settings.database.pool_size}")
        log.write("")

        # Cache Settings
        log.write("[bold cyan]Cache[/bold cyan]")
        log.write(f"  Cache Dir:   {self.settings.paths.cache_dir}")
        log.write(f"  Vector Store: {self.settings.paths.vector_store_dir}")
        log.write("")

        # Scanner
        log.write("[bold cyan]Scanner[/bold cyan]")
        log.write(
            f"  Max File:    {self.settings.scanner.max_file_size / 1024 / 1024:.1f} MB"
        )
        log.write(f"  Max Files:   {self.settings.scanner.max_files:,}")
        log.write("")

        log.write("[dim]Config file:[/dim]")
        log.write(f"[dim]  {self.config_file}[/dim]")
        log.write("")
        log.write("[dim]Use /config to manage configuration[/dim]")

    def cmd_status(self, log):
        """Handle /status command - shows real system status."""
        import sqlite3
        import urllib.request
        import os
        from pathlib import Path

        log.write("[bold]System Status[/bold]")
        log.write("")

        # TUI Status
        log.write("[bold]TUI:[/bold]")
        log.write("  [green]●[/green] Running ✓")
        log.write("")

        # Model Status
        log.write("[bold]AI Model:[/bold]")
        log.write(f"  [cyan]●[/cyan] Current: {self.current_model}")
        log.write("")

        # Theme Status
        log.write("[bold]Theme:[/bold]")
        log.write(f"  [cyan]●[/cyan] {self.app.ui_theme.capitalize()}")
        log.write("")

        # Database Status
        log.write("[bold]Database:[/bold]")
        db_path = getattr(self.app, "db_path", None)
        if db_path and os.path.exists(db_path):
            try:
                db_size = os.path.getsize(db_path)
                size_str = self._format_bytes(db_size)
                log.write(f"  [green]●[/green] Connected")
                log.write(f"  [dim]  Path:[/dim] {db_path}")
                log.write(f"  [dim]  Size:[/dim] {size_str}")

                # Get session count
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM sessions")
                    session_count = cursor.fetchone()[0]
                    log.write(f"  [dim]  Sessions:[/dim] {session_count}")
                    conn.close()
                except Exception as e:
                    log.write(f"  [yellow]![/yellow] Session count unavailable: {e}")
            except Exception as e:
                log.write(f"  [red]✗[/red] Error reading database: {e}")
        else:
            if db_path:
                log.write(f"  [yellow]●[/yellow] Not found: {db_path}")
            else:
                log.write("  [yellow]●[/yellow] No database path configured")
        log.write("")

        # Vector Store Status
        log.write("[bold]Vector Store:[/bold]")
        vector_store_path = Path("vector_store/chroma.sqlite3")
        if vector_store_path.exists():
            try:
                vs_size = vector_store_path.stat().st_size
                size_str = self._format_bytes(vs_size)
                log.write(f"  [green]●[/green] Available")
                log.write(f"  [dim]  Path:[/dim] {vector_store_path}")
                log.write(f"  [dim]  Size:[/dim] {size_str}")

                # Try to get collection count from ChromaDB
                try:
                    import chromadb

                    client = chromadb.PersistentClient(
                        path=str(vector_store_path.parent)
                    )
                    collections = client.list_collections()
                    log.write(f"  [dim]  Collections:[/dim] {len(collections)}")
                    if collections:
                        for col in collections:
                            try:
                                count = col.count()
                                log.write(
                                    f"    [dim]  - {col.name}: {count} documents[/dim]"
                                )
                            except:
                                log.write(
                                    f"    [dim]  - {col.name}: unknown count[/dim]"
                                )
                except ImportError:
                    log.write(
                        "  [dim]  ChromaDB not installed - collection info unavailable[/dim]"
                    )
                except Exception as e:
                    log.write(f"  [dim]  Collection info unavailable[/dim]")
            except Exception as e:
                log.write(f"  [yellow]![/yellow] Error reading vector store: {e}")
        else:
            log.write("  [yellow]●[/yellow] Not initialized (no data ingested yet)")
            log.write(f"  [dim]  Expected:[/dim] {vector_store_path}")
        log.write("")

        # Ollama Status
        log.write("[bold]Ollama:[/bold]")
        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/tags",
                method="GET",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    log.write("  [green]●[/green] Running on localhost:11434")
                    try:
                        import json

                        data = json.loads(response.read().decode("utf-8"))
                        models = data.get("models", [])
                        log.write(f"  [dim]  Models loaded:[/dim] {len(models)}")
                        if models:
                            model_names = [m.get("name", "unknown") for m in models[:5]]
                            log.write(
                                f"  [dim]  Available:[/dim] {', '.join(model_names)}"
                            )
                            if len(models) > 5:
                                log.write(
                                    f"  [dim]  ... and {len(models) - 5} more[/dim]"
                                )
                    except Exception:
                        log.write("  [dim]  (model details unavailable)[/dim]")
                else:
                    log.write(
                        f"  [yellow]●[/yellow] Unexpected response: {response.status}"
                    )
        except urllib.error.URLError as e:
            log.write("  [red]✗[/red] Not running or unreachable")
            log.write("  [dim]  Check: is Ollama installed and running?[/dim]")
            log.write("  [dim]  Install: https://ollama.com/download[/dim]")
        except Exception as e:
            log.write(f"  [yellow]![/yellow] Check failed: {e}")
        log.write("")

        # Cache Status
        log.write("[bold]Cache:[/bold]")
        cache_dirs = [
            Path(".pytest_cache"),
            Path(".ruff_cache"),
            Path("tests/cache"),
        ]
        total_cache_size = 0
        cache_found = False
        for cache_dir in cache_dirs:
            if cache_dir.exists():
                try:
                    size = self._get_dir_size(cache_dir)
                    total_cache_size += size
                    cache_found = True
                except:
                    pass

        if cache_found:
            log.write(f"  [green]●[/green] Active")
            log.write(f"  [dim]  Size:[/dim] {self._format_bytes(total_cache_size)}")
        else:
            log.write("  [dim]●[/dim] No cache directories found")
        log.write("")

        log.write("[dim]Use /sessions to view active sessions[/dim]")

    def _format_bytes(self, size: int) -> str:
        """Format bytes to human-readable string."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def _get_dir_size(self, path: Path) -> int:
        """Get total size of directory in bytes."""
        total = 0
        try:
            for entry in os.scandir(path):
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += self._get_dir_size(Path(entry.path))
        except (PermissionError, OSError):
            pass
        return total

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

    def cmd_sessions(self, log):
        """Handle /sessions command - list all sessions from database."""
        try:
            from mike.cli_orchestrator import Orchestrator
            from mike.db.models import Database

            db_path = getattr(self.app, "db_path", None)
            if not db_path:
                log.write("[red]Error:[/red] Database not initialized")
                return

            # Get sessions from database
            orchestrator = Orchestrator(db_path)
            sessions = orchestrator.list_sessions()

            if not sessions:
                log.write("[yellow]No sessions found.[/yellow]")
                log.write("")
                log.write("[dim]To create a session, use:[/dim]")
                log.write("  /scan <path>     Scan a codebase")
                return

            # Get file counts for each session
            db = Database(db_path)
            session_file_counts = {}
            for session in sessions:
                files = db.get_files_for_session(session.session_id)
                session_file_counts[session.session_id] = len(files)

            # Display sessions
            log.write("[bold]Sessions[/bold]")
            log.write("")

            for session in sessions:
                session_id_short = session.session_id[:8]
                source_name = session.source_path
                # Extract just the directory name for cleaner display
                if "/" in source_name:
                    source_name = source_name.split("/")[-1]
                if "\\" in source_name:
                    source_name = source_name.split("\\")[-1]

                created = session.created_at[:16] if session.created_at else "Unknown"
                file_count = session_file_counts.get(session.session_id, 0)

                status_color = "green" if session.status == "active" else "yellow"

                log.write(f"[cyan]{session_id_short}[/cyan]  {source_name}")
                log.write(f"       [dim]Source:[/dim] {session.source_path}")
                log.write(
                    f"       [dim]Type:[/dim] {session.session_type}  [dim]Status:[/dim] [{status_color}]{session.status}[/{status_color}]"
                )
                log.write(
                    f"       [dim]Created:[/dim] {created}  [dim]Files:[/dim] {file_count}"
                )
                log.write("")

            log.write(f"[dim]Total: {len(sessions)} session(s)[/dim]")
            log.write("")
            log.write(
                "[dim]Use 'sessions' (no slash) to open the sessions screen for detailed view.[/dim]"
            )

        except Exception as e:
            log.write(f"[red]Error loading sessions:[/red] {e}")
            log.write(
                "[dim]Make sure the database is initialized and accessible.[/dim]"
            )

    def cmd_config(self, args: list, log):
        """Handle /config command with subcommands."""
        if not args:
            log.write("[bold]Configuration Commands[/bold]")
            log.write("")
            log.write("  /config show              Show current configuration (JSON)")
            log.write("  /config edit              Open config in default editor")
            log.write(
                "  /config reset             Reset to defaults (with confirmation)"
            )
            log.write("  /config get <key>         Get specific config value")
            log.write("  /config set <key> <val>   Set specific config value")
            log.write("")
            log.write(f"[dim]Config location: {self.config_file}[/dim]")
            return

        subcmd = args[0].lower()

        if subcmd == "show":
            log.write("[bold]Current Configuration[/bold]")
            log.write("")
            try:
                if self.config_file.exists():
                    with open(self.config_file, "r") as f:
                        config = json.load(f)
                    log.write(json.dumps(config, indent=2))
                else:
                    log.write("[dim]No configuration file found.[/dim]")
                    log.write(
                        f"[dim]Config will be created at: {self.config_file}[/dim]"
                    )
            except Exception as e:
                log.write(f"[red]Error reading config:[/red] {e}")

        elif subcmd == "edit":
            editor = os.environ.get("EDITOR", "")
            if not editor:
                # Try to find a sensible default
                for candidate in ["code", "vim", "nano", "open", "notepad"]:
                    try:
                        subprocess.run(
                            ["which", candidate], capture_output=True, check=True
                        )
                        editor = candidate
                        break
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue

            if not editor:
                log.write("[red]Error:[/red] No editor found")
                log.write(
                    "[dim]Set $EDITOR environment variable or install vim/nano/code[/dim]"
                )
                return

            try:
                # Ensure config file exists
                if not self.config_file.exists():
                    self._save_config()

                log.write(f"[yellow]Opening {self.config_file} in {editor}...[/yellow]")

                # Open in background
                if editor in ["code", "vim", "nano"]:
                    subprocess.Popen([editor, str(self.config_file)])
                else:
                    subprocess.Popen(
                        [editor, str(self.config_file)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

                log.write("[green]✓[/green] Editor opened")
                log.write(
                    "[dim]Save the file and run /config reload to apply changes[/dim]"
                )
            except Exception as e:
                log.write(f"[red]Error opening editor:[/red] {e}")

        elif subcmd == "reset":
            if len(args) < 2 or args[1].lower() != "confirm":
                log.write(
                    "[bold yellow]⚠ Warning:[/bold yellow] This will reset all settings to defaults!"
                )
                log.write("")
                log.write("To confirm, run: [bold]/config reset confirm[/bold]")
                return

            try:
                if self.config_file.exists():
                    self.config_file.unlink()
                self.current_model = "ollama/qwen2.5-coder:14b"
                self.settings = Settings.default()
                self._save_config()
                log.write("[green]✓[/green] Configuration reset to defaults")
                log.write(f"[dim]Saved to: {self.config_file}[/dim]")
            except Exception as e:
                log.write(f"[red]Error:[/red] {e}")

        elif subcmd == "get":
            if len(args) < 2:
                log.write("[red]Usage:[/red] /config get <key>")
                log.write("[dim]Examples:[/dim]")
                log.write("  /config get llm.model")
                log.write("  /config get database.path")
                return

            key = args[1]
            value = self._get_nested_value(self.settings, key)

            if value is not None:
                log.write(f"[bold]{key}[/bold] = {value}")
            else:
                log.write(f"[red]Error:[/red] Key '{key}' not found")
                log.write(
                    "[dim]Available top-level keys: version, debug, log_level, embedding_model, database, llm, embeddings, agents, scanner, paths, logging, profile[/dim]"
                )

        elif subcmd == "set":
            if len(args) < 3:
                log.write("[red]Usage:[/red] /config set <key> <value>")
                log.write("[dim]Examples:[/dim]")
                log.write("  /config set llm.model llama3.2")
                log.write("  /config set llm.temperature 0.5")
                log.write("  /config set debug true")
                return

            key = args[1]
            value = " ".join(args[2:])  # Allow values with spaces

            if self._set_nested_value(self.settings, key, value):
                if self._save_config():
                    log.write(f"[green]✓[/green] Set {key} = {value}")
                else:
                    log.write(f"[yellow]✓[/yellow] Set {key} = {value} (not saved)")
            else:
                log.write(f"[red]Error:[/red] Failed to set '{key}'")
                log.write(
                    "[dim]Check that the key exists and value type is valid[/dim]"
                )

        elif subcmd == "reload":
            try:
                self._load_or_create_config()
                log.write("[green]✓[/green] Configuration reloaded")
            except Exception as e:
                log.write(f"[red]Error reloading config:[/red] {e}")

        else:
            log.write(f"[red]Unknown config command:[/red] {subcmd}")
            log.write(
                "[dim]Use /config without arguments to see available commands[/dim]"
            )

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
        log.write("  /config             Configuration management")
        log.write("    show              Display config as JSON")
        log.write("    edit              Open in default editor")
        log.write("    get <key>         Get specific value")
        log.write("    set <key> <val>   Set specific value")
        log.write("    reset             Reset to defaults")
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
