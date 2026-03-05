"""Sessions screen for Mike TUI."""

from textual.screen import Screen
from textual.widgets import DataTable, Static
from textual.reactive import reactive
from textual.worker import Worker
from textual.containers import Vertical


class SessionsScreen(Screen):
    """Screen showing all sessions in a data table."""

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("d", "delete", "Delete"),
        ("enter", "open_detail", "Open"),
    ]

    sessions = reactive([])
    selected_session_id = reactive(None)

    def compose(self):
        """Compose the screen."""
        yield Static("Sessions", id="sessions-title")
        table = DataTable(id="sessions-table")
        table.add_columns("ID", "Source", "Type", "Status", "Created")
        table.cursor_type = "row"
        yield table
        yield Static(
            "Press [r] to refresh, [Enter] to open, [d] to delete", id="sessions-hints"
        )

    def on_mount(self):
        """Load sessions on mount."""
        self.load_sessions()

    def load_sessions(self):
        """Load sessions in background."""
        self.run_worker(self._fetch_sessions)

    def _fetch_sessions(self):
        """Fetch sessions from database."""
        try:
            from mike.cli_orchestrator import Orchestrator

            orchestrator = Orchestrator(self.app.db_path)
            return orchestrator.list_sessions()
        except Exception as e:
            self.app.notify(f"Error loading sessions: {e}", severity="error")
            return []

    def on_worker_state_changed(self, event: Worker.StateChanged):
        """Handle worker completion."""
        if event.state == Worker.State.SUCCESS:
            self.sessions = event.worker.result or []
            self.update_table()

    def update_table(self):
        """Update the data table with sessions."""
        table = self.query_one("#sessions-table", DataTable)
        table.clear()

        for session in self.sessions:
            created = (
                session.created_at[:16] if hasattr(session, "created_at") else "--"
            )
            table.add_row(
                session.session_id[:12],
                session.source_path[:40],
                session.session_type,
                session.status,
                created,
                key=session.session_id,
            )

    def on_data_table_row_selected(self, event):
        """Handle row selection."""
        self.selected_session_id = event.row_key.value

    def action_refresh(self):
        """Refresh sessions."""
        self.load_sessions()
        self.app.notify("Sessions refreshed", severity="information")

    def action_delete(self):
        """Delete selected session."""
        if not self.selected_session_id:
            self.app.notify("No session selected", severity="warning")
            return

        # Show confirmation modal
        self.push_screen(
            ConfirmationModal(
                f"Delete session {self.selected_session_id[:8]}...?",
                on_confirm=self._do_delete,
            )
        )

    def _do_delete(self):
        """Actually delete the session."""
        try:
            from mike.cli_orchestrator import Orchestrator

            orchestrator = Orchestrator(self.app.db_path)
            orchestrator.delete_session(self.selected_session_id)
            self.app.notify("Session deleted", severity="information")
            self.load_sessions()
        except Exception as e:
            self.app.notify(f"Error deleting: {e}", severity="error")

    def action_open_detail(self):
        """Open session detail."""
        if not self.selected_session_id:
            self.app.notify("No session selected", severity="warning")
            return

        self.app.notify(
            f"Opening {self.selected_session_id[:8]}... (not implemented yet)"
        )


class ConfirmationModal(Screen):
    """Modal for confirmation dialogs."""

    def __init__(self, message: str, on_confirm=None, **kwargs):
        self.message = message
        self.on_confirm = on_confirm
        super().__init__(**kwargs)

    def compose(self):
        """Compose the modal."""
        with Vertical(id="modal-content"):
            yield Static(self.message, id="modal-message")
            yield Static("Press [y] to confirm, [n] to cancel")

    def on_key(self, event):
        """Handle key presses."""
        if event.key == "y":
            if self.on_confirm:
                self.on_confirm()
            self.app.pop_screen()
        elif event.key == "n":
            self.app.pop_screen()
