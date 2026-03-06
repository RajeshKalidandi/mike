"""Help screen for Mike TUI."""

from textual.screen import ModalScreen
from textual.widgets import Markdown, Static
from textual.containers import Vertical, VerticalScroll


HELP_MARKDOWN = """
# Mike Keyboard Shortcuts

## Global

| Key | Action |
|-----|--------|
| `Ctrl+T` | Toggle light/dark theme |
| `?` | Show this help |
| `q` / `Ctrl+C` | Quit |

## Main Screen

| Key | Action |
|-----|--------|
| `Tab` / `Shift+Tab` | Next/Previous widget |
| `/sessions` | Open sessions list |
| `/scan <path>` | Scan a codebase |
| `/help` | Show commands |

## Sessions

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate sessions |
| `Enter` | Open session detail |
| `r` | Refresh list |
| `d` | Delete selected session |
| `Esc` | Go back to main |

## Session Detail

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate files |
| `r` | Refresh |
| `Esc` | Go back to sessions |

## Logs

| Key | Action |
|-----|--------|
| `s` | Toggle auto-scroll |
| `c` | Clear logs |
| `r` | Refresh/restart tailing |

---

*Mike - Local AI Software Architect*
*Press `q` or `Esc` to close this help*
"""


class HelpScreen(ModalScreen):
    """Modal help screen showing keyboard shortcuts."""

    BINDINGS = [
        ("q", "dismiss", "Close"),
        ("escape", "dismiss", "Close"),
        ("question_mark", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }
    
    #help-container {
        width: 80;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    
    #help-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        height: 1;
        margin-bottom: 1;
    }
    
    #help-content {
        height: auto;
        max-height: 70%;
    }
    
    #help-footer {
        text-align: center;
        color: $text-muted;
        height: 1;
        margin-top: 1;
    }
    """

    def compose(self):
        """Compose the help screen."""
        with Vertical(id="help-container"):
            yield Static("Mike Help", id="help-title")
            with VerticalScroll(id="help-content"):
                yield Markdown(HELP_MARKDOWN)
            yield Static("Press q or Esc to close", id="help-footer")

    def action_dismiss(self):
        """Close the help screen."""
        self.dismiss()
