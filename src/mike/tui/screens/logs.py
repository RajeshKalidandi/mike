"""Logs screen for Mike TUI with live tailing."""

import os
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

from textual.screen import Screen
from textual.widgets import RichLog, Static, Select
from textual.reactive import reactive
from textual.worker import Worker
from textual.containers import Horizontal, Vertical


class LogsScreen(Screen):
    """Screen showing live logs with tailing."""

    BINDINGS = [
        ("s", "toggle_scroll", "Toggle Scroll"),
        ("c", "clear", "Clear"),
        ("r", "refresh", "Refresh"),
    ]

    auto_scroll = reactive(True)
    log_level = reactive("INFO")
    log_file_path = reactive(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._worker: Optional[Worker] = None

    def compose(self):
        """Compose the screen."""
        with Vertical():
            # Header with controls
            with Horizontal(id="logs-header"):
                yield Static("Logs", id="logs-title")
                yield Select(
                    [
                        ("All", "ALL"),
                        ("Debug", "DEBUG"),
                        ("Info", "INFO"),
                        ("Warning", "WARNING"),
                        ("Error", "ERROR"),
                    ],
                    value="INFO",
                    id="level-select",
                )
                yield Static(
                    "[s] Toggle Scroll | [c] Clear | [r] Refresh", id="logs-controls"
                )

            # Log display
            log_widget = RichLog(id="log-viewer", highlight=True, markup=True)
            log_widget.auto_scroll = self.auto_scroll
            yield log_widget

    def on_mount(self):
        """Start log tailing on mount."""
        self.find_log_file()
        if self.log_file_path and os.path.exists(self.log_file_path):
            self.start_tailing()
            self.load_initial_logs()
        else:
            self.add_log_message("warning", "No log file found")

    def find_log_file(self):
        """Find the log file path."""
        # Check common locations
        home = Path.home()
        possible_paths = [
            home / ".mike" / "logs" / "mike.log",
            home / ".mike" / "mike.log",
            Path("logs") / "mike.log",
            Path("mike.log"),
        ]

        for path in possible_paths:
            if path.exists():
                self.log_file_path = str(path)
                return

        # Default to first option even if doesn't exist
        self.log_file_path = str(possible_paths[0])

    def load_initial_logs(self):
        """Load existing log content."""
        try:
            if self.log_file_path and os.path.exists(self.log_file_path):
                with open(self.log_file_path, "r") as f:
                    # Read last 100 lines
                    lines = f.readlines()
                    lines = lines[-100:] if len(lines) > 100 else lines

                    log_widget = self.query_one("#log-viewer", RichLog)
                    for line in lines:
                        self._write_log_line(line.strip())
        except Exception as e:
            self.add_log_message("error", f"Error loading logs: {e}")

    def start_tailing(self):
        """Start background log tailing."""
        if self._worker:
            self._worker.cancel()
        self._worker = self.run_worker(self._tail_logs, exclusive=True)

    def _tail_logs(self):
        """Tail logs in background (runs in worker)."""
        if not self.log_file_path:
            return

        try:
            with open(self.log_file_path, "r") as f:
                # Go to end of file
                f.seek(0, 2)

                while True:
                    line = f.readline()
                    if line:
                        # Use call_from_thread to update UI from worker
                        self.app.call_from_thread(self._write_log_line, line.strip())
                    else:
                        time.sleep(0.5)

        except Exception as e:
            self.app.call_from_thread(
                self.add_log_message, "error", f"Tailing error: {e}"
            )

    def _write_log_line(self, line: str):
        """Write a log line to the widget."""
        if not line:
            return

        # Check level filter
        if self.log_level != "ALL":
            if self.log_level == "DEBUG" and "DEBUG" not in line:
                return
            elif self.log_level == "INFO" and not any(
                l in line for l in ["INFO", "WARNING", "ERROR"]
            ):
                return
            elif self.log_level == "WARNING" and not any(
                l in line for l in ["WARNING", "ERROR"]
            ):
                return
            elif self.log_level == "ERROR" and "ERROR" not in line:
                return

        log_widget = self.query_one("#log-viewer", RichLog)

        # Colorize based on level
        if "ERROR" in line:
            line = f"[red]{line}[/red]"
        elif "WARNING" in line:
            line = f"[yellow]{line}[/yellow]"
        elif "INFO" in line:
            line = f"[green]{line}[/green]"

        log_widget.write(line)

    def add_log_message(self, level: str, message: str):
        """Add a message to the log widget."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp} - {level.upper()} - {message}"
        self._write_log_line(line)

    def on_select_changed(self, event: Select.Changed):
        """Handle log level filter change."""
        if event.select.id == "level-select":
            self.log_level = event.value
            self.add_log_message("info", f"Filter changed to {self.log_level}")

    def action_toggle_scroll(self):
        """Toggle auto-scroll."""
        self.auto_scroll = not self.auto_scroll
        log_widget = self.query_one("#log-viewer", RichLog)
        log_widget.auto_scroll = self.auto_scroll
        self.add_log_message(
            "info", f"Auto-scroll: {'ON' if self.auto_scroll else 'OFF'}"
        )

    def action_clear(self):
        """Clear logs."""
        log_widget = self.query_one("#log-viewer", RichLog)
        log_widget.clear()
        self.add_log_message("info", "Logs cleared")

    def action_refresh(self):
        """Refresh and restart tailing."""
        self.query_one("#log-viewer", RichLog).clear()
        self.load_initial_logs()
        self.start_tailing()

    def on_unmount(self):
        """Stop tailing when screen unmounts."""
        if self._worker:
            self._worker.cancel()
