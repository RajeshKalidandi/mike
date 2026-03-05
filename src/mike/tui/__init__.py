"""Mike TUI - Terminal User Interface."""

from typing import Optional

__all__ = ["launch_tui"]


def launch_tui(db_path: Optional[str] = None, theme: str = "dark") -> None:
    """Launch the Mike TUI application.

    Args:
        db_path: Path to the database file. If None, uses default.
        theme: Theme name ('dark' or 'light').
    """
    from mike.tui.app import MikeApp

    if db_path is not None:
        app = MikeApp(db_path=db_path, theme=theme)
    else:
        app = MikeApp(theme=theme)
    app.run()
