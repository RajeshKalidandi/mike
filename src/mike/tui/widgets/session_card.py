"""Session card widget for displaying session info."""

from textual.widgets import Static
from textual.reactive import reactive
from textual.containers import Vertical


class SessionCard(Static):
    """Card displaying session information."""

    session_id = reactive("")
    source_path = reactive("")
    session_type = reactive("")
    status = reactive("")
    file_count = reactive(0)

    def __init__(self, session_info, **kwargs):
        super().__init__(**kwargs)
        self.session_id = session_info.session_id
        self.source_path = session_info.source_path
        self.session_type = session_info.session_type
        self.status = session_info.status
        self.file_count = getattr(session_info, "file_count", 0)

    def compose(self):
        """Compose the card."""
        with Vertical():
            yield Static(f"ID: {self.session_id[:12]}...", classes="session-id")
            yield Static(f"Source: {self.source_path}", classes="session-source")
            yield Static(
                f"Type: {self.session_type} | Status: {self.status}",
                classes="session-meta",
            )
            if self.file_count:
                yield Static(f"Files: {self.file_count}", classes="session-files")
