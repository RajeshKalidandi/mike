"""Session detail screen for Mike TUI."""

from textual.screen import Screen
from textual.widgets import Static, Markdown
from textual.reactive import reactive
from textual.worker import Worker
from textual.containers import Horizontal, Vertical


class SessionDetailScreen(Screen):
    """Screen showing details of a specific session."""

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("escape", "go_back", "Back"),
    ]

    session_id = reactive("")
    session_data = reactive({})
    files = reactive([])
    stats = reactive({})

    def __init__(self, session_id: str = "", **kwargs):
        self.session_id = session_id
        super().__init__(**kwargs)

    def compose(self):
        """Compose the screen."""
        with Horizontal():
            # Left side: File tree
            with Vertical(id="file-tree-container"):
                yield Static("Files", id="files-header")
                yield Static("Loading...", id="file-tree")

            # Right side: Session info
            with Vertical(id="session-info"):
                yield Static("Session Details", id="detail-header")
                yield Markdown("Loading...", id="detail-content")

    def on_mount(self):
        """Load session data on mount."""
        if self.session_id:
            self.load_session_data()

    def load_session_data(self):
        """Load session data in background."""
        self.run_worker(self._fetch_session_data)

    def _fetch_session_data(self):
        """Fetch session data."""
        try:
            from mike.cli_orchestrator import Orchestrator
            from mike.db.models import Database

            orchestrator = Orchestrator(self.app.db_path)
            db = Database(self.app.db_path)

            session = orchestrator.get_session(self.session_id)
            files = db.get_files_for_session(self.session_id)
            stats = orchestrator.get_session_stats(self.session_id)

            return {"session": session, "files": files, "stats": stats}
        except Exception as e:
            return {"error": str(e)}

    def on_worker_state_changed(self, event: Worker.StateChanged):
        """Handle worker completion."""
        if event.state == Worker.State.SUCCESS and event.worker.result:
            data = event.worker.result

            if "error" in data:
                self.app.notify(f"Error: {data['error']}", severity="error")
                return

            self.session_data = data.get("session", {})
            self.files = data.get("files", [])
            self.stats = data.get("stats", {})

            self.update_display()

    def update_display(self):
        """Update the display with loaded data."""
        # Update file tree
        tree_container = self.query_one("#file-tree-container", Vertical)
        tree_container.remove_children()

        with tree_container:
            yield Static("Files", id="files-header")
            from mike.tui.widgets.file_tree import FileTree

            yield FileTree(self.files, id="file-tree-widget")

        # Update detail content
        content = self.query_one("#detail-content", Markdown)

        if self.session_data:
            md = self._format_session_markdown()
            content.update(md)

    def _format_session_markdown(self) -> str:
        """Format session data as markdown."""
        session = self.session_data
        stats = self.stats

        lines = [
            f"## Session: {session.get('session_id', 'Unknown')[:16]}...",
            "",
            f"**Source:** `{session.get('source_path', 'N/A')}`",
            f"**Type:** {session.get('session_type', 'Unknown')}",
            f"**Status:** {session.get('status', 'Unknown')}",
            f"**Created:** {session.get('created_at', 'Unknown')}",
            "",
            "### Statistics",
            "",
            f"- **Files:** {stats.get('file_count', 0)}",
            f"- **Parsed:** {stats.get('parsed_count', 0)}",
            f"- **Total Lines:** {stats.get('total_lines', 0):,}",
        ]

        # Add language breakdown
        languages = stats.get("languages", {})
        if languages:
            lines.extend(["", "### Languages", ""])
            for lang, count in sorted(languages.items(), key=lambda x: -x[1])[:10]:
                lines.append(f"- {lang}: {count} files")

        return "\n".join(lines)

    def action_refresh(self):
        """Refresh session data."""
        self.load_session_data()

    def action_go_back(self):
        """Go back to sessions list."""
        self.app.switch_screen("sessions")
