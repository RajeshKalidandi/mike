"""Notification widget for toast messages."""

from textual.widgets import Static
from textual.reactive import reactive
from textual.containers import Vertical
from datetime import datetime
from typing import Optional


class Notification(Static):
    """A single notification toast."""

    message = reactive("")
    level = reactive("info")  # info, warning, error, success
    timestamp = reactive("")

    def __init__(self, message: str, level: str = "info", **kwargs):
        self.message = message
        self.level = level
        self.timestamp = datetime.now().strftime("%H:%M:%S")
        super().__init__(**kwargs)

    def compose(self):
        """Compose the notification."""
        icon = {"info": "ℹ", "warning": "⚠", "error": "✗", "success": "✓"}.get(
            self.level, "ℹ"
        )

        color = {
            "info": "blue",
            "warning": "yellow",
            "error": "red",
            "success": "green",
        }.get(self.level, "blue")

        yield Static(f"{icon} [{color}]{self.message}[/{color}] ({self.timestamp})")

    def on_mount(self):
        """Auto-remove after 5 seconds."""
        self.set_timer(5, self.remove)


class NotificationContainer(Vertical):
    """Container for notifications that appears in top-right."""

    DEFAULT_CSS = """
    NotificationContainer {
        dock: top;
        width: 40;
        height: auto;
        offset: 0 0;
        layer: notification;
    }
    
    NotificationContainer .notification {
        background: $surface;
        color: $text;
        padding: 1;
        margin: 0 1 1 0;
        border: solid $primary;
    }
    
    NotificationContainer .notification.error {
        border: solid $error;
    }
    
    NotificationContainer .notification.warning {
        border: solid $warning;
    }
    
    NotificationContainer .notification.success {
        border: solid $success;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_class("notification-container")

    def notify(self, message: str, level: str = "info"):
        """Add a notification."""
        notification = Notification(message, level)
        notification.add_class("notification")
        notification.add_class(level)
        self.mount(notification)

    def clear_all(self):
        """Clear all notifications."""
        for child in list(self.children):
            child.remove()
