"""Sidebar navigation widget for Mike TUI."""

from textual.widgets import Static, ListView, ListItem, Label
from textual.reactive import reactive
from textual.message import Message


class Sidebar(ListView):
    """Left sidebar with navigation items."""

    class Selected(Message):
        """Message sent when item is selected."""

        def __init__(self, index: int, item: str) -> None:
            self.index = index
            self.item = item
            super().__init__()

    def __init__(self):
        super().__init__()
        self.nav_items = [
            ("Dashboard", "1"),
            ("Sessions", "2"),
            ("Logs", "3"),
        ]

    def compose(self):
        """Compose the sidebar."""
        for name, key in self.nav_items:
            yield ListItem(Label(f"[{key}] {name}"), id=f"nav-{key}")

    def on_list_view_selected(self, event):
        """Handle selection."""
        index = event.list_view.index
        if index is not None and 0 <= index < len(self.nav_items):
            name, key = self.nav_items[index]
            self.post_message(self.Selected(index, name))
