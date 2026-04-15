# Mike TUI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Add a modern, beautiful Terminal User Interface (TUI) to Mike using Textual framework, providing an interactive alternative to the classic CLI with screens for Dashboard, Sessions, Logs, and more.

**Architecture:**
- **Framework:** Textual (modern Python TUI framework with CSS-like styling, reactive bindings, async support)
- **Layout:** Left sidebar navigation + main content area + bottom status bar (lazygit/k9s style)
- **Screens:** Dashboard (system status), Sessions (data table), Session Detail (file tree + stats), Logs (live tailing)
- **Integration:** New `mike tui` command and `--tui` flag on existing commands
- **Theming:** Dark mode default (catppuccin-inspired), light mode optional

**Tech Stack:**
- Textual >= 0.50.0 (core TUI framework)
- textual-dev (optional, for development)
- Rich (already included with Textual, for rendering)

---

## Folder Structure

```
src/mike/
├── tui/
│   ├── __init__.py           # TUI entry point, exports
│   ├── app.py                # Main Textual App class
│   ├── screens/
│   │   ├── __init__.py
│   │   ├── dashboard.py      # System status dashboard
│   │   ├── sessions.py       # Sessions list with data table
│   │   ├── session_detail.py # Individual session view
│   │   ├── logs.py           # Live log tailing
│   │   └── help.py           # Help modal/screen
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── sidebar.py        # Left navigation sidebar
│   │   ├── status_bar.py     # Bottom status bar
│   │   ├── session_card.py   # Session info card
│   │   └── file_tree.py      # File browser tree
│   ├── styles/
│   │   ├── __init__.py
│   │   ├── base.tcss         # Base styles
│   │   ├── dark.tcss         # Dark theme
│   │   └── light.tcss        # Light theme
│   └── utils.py              # TUI utilities
```

---

## Dependencies

Add to `pyproject.toml` under `[project.optional-dependencies]`:

```toml
tui = [
    "textual>=0.50.0",
]
dev = [
    "textual-dev>=1.0.0",  # For textual run/console commands
    # ... existing dev deps
]
```

Or add to `requirements.txt`:
```
# TUI Dependencies
textual>=0.50.0
textual-dev>=1.0.0  # Dev only
```

---

## Task 1: Create TUI Module Structure

**Files:**
- Create: `src/mike/tui/__init__.py`
- Create: `src/mike/tui/app.py`
- Create: `src/mike/tui/screens/__init__.py`
- Create: `src/mike/tui/widgets/__init__.py`
- Create: `src/mike/tui/styles/__init__.py`
- Create: `src/mike/tui/utils.py`
- Modify: `pyproject.toml` (add tui dependencies)

**Step 1: Create base module files**

Create empty files with proper structure and imports.

**Step 2: Run syntax check**

```bash
cd /Users/krissdev/mike
python -c "from src.mike.tui import app; print('OK')"
```

Expected: Import error (files don't exist yet) or OK

**Step 3: Add dependencies to pyproject.toml**

Add tui optional dependencies section.

**Step 4: Commit**

```bash
git add pyproject.toml src/mike/tui/
git commit -m "feat: add TUI module structure and Textual dependencies"
```

---

## Task 2: Implement TUI App Framework

**Files:**
- Create: `src/mike/tui/app.py`
- Create: `src/mike/tui/screens/dashboard.py`
- Create: `src/mike/tui/widgets/sidebar.py`
- Create: `src/mike/tui/widgets/status_bar.py`
- Create: `src/mike/tui/styles/base.tcss`
- Create: `src/mike/tui/styles/dark.tcss`

**Step 1: Write base CSS styles**

Create `base.tcss` with base layout styles (no colors).

**Step 2: Write dark theme CSS**

Create `dark.tcss` with catppuccin-inspired dark colors.

**Step 3: Implement StatusBar widget**

Simple widget showing current mode and key hints.

**Step 4: Implement Sidebar widget**

ListView-based sidebar with navigation items.

**Step 5: Implement DashboardScreen**

Grid layout with system status cards.

**Step 6: Implement MikeApp**

Main App class with:
- CSS_PATHS for styles
- SCREENS dict for screen management
- Sidebar + Content + StatusBar layout
- Navigation bindings (1-5 for screens, q to quit)

**Step 7: Write test**

```python
def test_app_imports():
    from mike.tui.app import MikeApp
    assert MikeApp is not None
```

**Step 8: Run test**

```bash
pytest tests/tui/test_app.py::test_app_imports -v
```

Expected: PASS

**Step 9: Commit**

```bash
git add src/mike/tui/app.py src/mike/tui/screens/ src/mike/tui/widgets/ src/mike/tui/styles/
git commit -m "feat: implement TUI app framework with dashboard"
```

---

## Task 3: Implement Sessions Screen

**Files:**
- Create: `src/mike/tui/screens/sessions.py`
- Create: `src/mike/tui/widgets/session_card.py`
- Create: `tests/tui/test_sessions_screen.py`

**Step 1: Implement SessionCard widget**

Card showing session info (id, source, type, status, file count).

**Step 2: Implement SessionsScreen**

- DataTable showing all sessions
- Selection highlights row
- Enter key opens session detail
- r key refreshes list
- d key deletes selected session (with confirmation)

**Step 3: Write test**

```python
def test_sessions_screen_imports():
    from mike.tui.screens.sessions import SessionsScreen
    assert SessionsScreen is not None
```

**Step 4: Run test**

```bash
pytest tests/tui/test_sessions_screen.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/mike/tui/screens/sessions.py src/mike/tui/widgets/session_card.py tests/tui/
git commit -m "feat: implement sessions screen with data table"
```

---

## Task 4: Implement Session Detail Screen

**Files:**
- Create: `src/mike/tui/screens/session_detail.py`
- Create: `src/mike/tui/widgets/file_tree.py`
- Create: `tests/tui/test_session_detail.py`

**Step 1: Implement FileTree widget**

Tree widget for browsing session files with expandable directories.

**Step 2: Implement SessionDetailScreen**

- Header with session info
- Left: FileTree of session files
- Right: File content viewer or stats
- Show language breakdown
- Show file count and line count

**Step 3: Write test**

```python
def test_session_detail_imports():
    from mike.tui.screens.session_detail import SessionDetailScreen
    assert SessionDetailScreen is not None
```

**Step 4: Run test**

```bash
pytest tests/tui/test_session_detail.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/mike/tui/screens/session_detail.py src/mike/tui/widgets/file_tree.py tests/tui/test_session_detail.py
git commit -m "feat: implement session detail screen with file tree"
```

---

## Task 5: Implement Logs Screen with Live Tailing

**Files:**
- Create: `src/mike/tui/screens/logs.py`
- Create: `tests/tui/test_logs_screen.py`

**Step 1: Implement LogsScreen**

- RichLog widget for displaying logs
- Worker for tailing log file
- Auto-scroll toggle
- Filter by level (INFO, WARNING, ERROR)
- Clear logs button

**Step 2: Add live log tailing worker**

Use Textual's @work decorator for async log tailing without blocking UI.

**Step 3: Write test**

```python
def test_logs_screen_imports():
    from mike.tui.screens.logs import LogsScreen
    assert LogsScreen is not None
```

**Step 4: Run test**

```bash
pytest tests/tui/test_logs_screen.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/mike/tui/screens/logs.py tests/tui/test_logs_screen.py
git commit -m "feat: implement logs screen with live tailing"
```

---

## Task 6: Implement Help Screen/Modal

**Files:**
- Create: `src/mike/tui/screens/help.py`
- Create: `tests/tui/test_help_screen.py`

**Step 1: Implement HelpScreen**

- Markdown display of keyboard shortcuts
- Organized by section (Navigation, Actions, Global)
- Close with Esc or q

**Step 2: Write test**

```python
def test_help_screen_imports():
    from mike.tui.screens.help import HelpScreen
    assert HelpScreen is not None
```

**Step 3: Run test**

```bash
pytest tests/tui/test_help_screen.py -v
```

Expected: PASS

**Step 4: Commit**

```bash
git add src/mike/tui/screens/help.py tests/tui/test_help_screen.py
git commit -m "feat: implement help screen with keyboard shortcuts"
```

---

## Task 7: Integrate TUI into CLI

**Files:**
- Modify: `src/mike/cli.py` (add tui command)
- Modify: `src/mike/tui/__init__.py` (export launch function)

**Step 1: Add launch_tui function to tui/__init__.py**

```python
def launch_tui(db_path: str = None, theme: str = "dark"):
    """Launch the TUI application."""
    from mike.tui.app import MikeApp
    app = MikeApp(db_path=db_path, theme=theme)
    app.run()
```

**Step 2: Add tui command to CLI**

Add to src/mike/cli.py:
```python
@main.command()
@click.option("--theme", default="dark", type=click.Choice(["dark", "light"]))
@click.pass_context
def tui(ctx: click.Context, theme: str) -> None:
    """Launch interactive TUI."""
    from mike.tui import launch_tui
    db_path = ctx.obj["db_path"]
    launch_tui(db_path=db_path, theme=theme)
```

**Step 3: Write integration test**

```python
def test_tui_command():
    from click.testing import CliRunner
    from mike.cli import main
    
    runner = CliRunner()
    # Test that command exists (won't actually run TUI in test)
    result = runner.invoke(main, ['tui', '--help'])
    assert result.exit_code == 0
    assert 'TUI' in result.output or 'interactive' in result.output
```

**Step 4: Run test**

```bash
pytest tests/tui/test_cli_integration.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/mike/cli.py src/mike/tui/__init__.py tests/tui/test_cli_integration.py
git commit -m "feat: integrate TUI into CLI with 'mike tui' command"
```

---

## Task 8: Add Light Theme Support

**Files:**
- Create: `src/mike/tui/styles/light.tcss`
- Modify: `src/mike/tui/app.py` (theme switching)

**Step 1: Create light.tcss**

Light theme with gruvbox-light or similar palette.

**Step 2: Add theme switching to MikeApp**

Support --theme flag and runtime theme toggle (Ctrl+T).

**Step 3: Write test**

```python
def test_theme_loading():
    from mike.tui.app import MikeApp
    # Test dark theme
    app = MikeApp(theme="dark")
    assert app.theme == "dark"
    # Test light theme
    app = MikeApp(theme="light")
    assert app.theme == "light"
```

**Step 4: Run test**

```bash
pytest tests/tui/test_theme.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/mike/tui/styles/light.tcss src/mike/tui/app.py tests/tui/test_theme.py
git commit -m "feat: add light theme support with runtime switching"
```

---

## Task 9: Implement Error Handling and Notifications

**Files:**
- Modify: `src/mike/tui/app.py` (add error handling)
- Create: `src/mike/tui/widgets/notifications.py`

**Step 1: Create Notification widget**

Toast notifications for errors, warnings, info.

**Step 2: Add error boundary to app**

Wrap async operations with try/except and show notifications.

**Step 3: Commit**

```bash
git add src/mike/tui/widgets/notifications.py src/mike/tui/app.py
git commit -m "feat: add error handling and toast notifications"
```

---

## Task 10: Create Comprehensive TUI Tests

**Files:**
- Create: `tests/tui/conftest.py`
- Create: `tests/tui/test_integration.py`
- Modify: Existing test files for completeness

**Step 1: Create conftest.py**

Pytest fixtures for TUI testing using Textual's Pilot.

**Step 2: Write integration tests**

Test full user flows:
- Open app, navigate to sessions, open session detail
- Test keyboard shortcuts
- Test theme switching

**Step 3: Run all TUI tests**

```bash
pytest tests/tui/ -v --tb=short
```

Expected: All PASS

**Step 4: Commit**

```bash
git add tests/tui/
git commit -m "test: add comprehensive TUI test suite"
```

---

## Summary of All Files

**New Files (17):**
- `src/mike/tui/__init__.py`
- `src/mike/tui/app.py`
- `src/mike/tui/utils.py`
- `src/mike/tui/screens/__init__.py`
- `src/mike/tui/screens/dashboard.py`
- `src/mike/tui/screens/sessions.py`
- `src/mike/tui/screens/session_detail.py`
- `src/mike/tui/screens/logs.py`
- `src/mike/tui/screens/help.py`
- `src/mike/tui/widgets/__init__.py`
- `src/mike/tui/widgets/sidebar.py`
- `src/mike/tui/widgets/status_bar.py`
- `src/mike/tui/widgets/session_card.py`
- `src/mike/tui/widgets/file_tree.py`
- `src/mike/tui/widgets/notifications.py`
- `src/mike/tui/styles/__init__.py`
- `src/mike/tui/styles/base.tcss`
- `src/mike/tui/styles/dark.tcss`
- `src/mike/tui/styles/light.tcss`

**Test Files (6):**
- `tests/tui/__init__.py`
- `tests/tui/conftest.py`
- `tests/tui/test_app.py`
- `tests/tui/test_sessions_screen.py`
- `tests/tui/test_session_detail.py`
- `tests/tui/test_logs_screen.py`
- `tests/tui/test_help_screen.py`
- `tests/tui/test_cli_integration.py`
- `tests/tui/test_theme.py`
- `tests/tui/test_integration.py`

**Modified Files (2):**
- `pyproject.toml` (add tui dependencies)
- `src/mike/cli.py` (add tui command)

---

## Usage

```bash
# Install with TUI support
pip install -e ".[tui]"

# Launch TUI
mike tui
mike tui --theme light

# Classic CLI still works
mike scan /path/to/code
mike status
```

---

## Keyboard Shortcuts

**Navigation:**
- `1` - Dashboard
- `2` - Sessions
- `3` - Logs
- `?` - Help
- `q` / `Ctrl+C` - Quit

**Global:**
- `Ctrl+T` - Toggle theme
- `Ctrl+L` - Clear notifications
- `Tab` / `Shift+Tab` - Next/Previous widget
- `↑` / `↓` / `←` / `→` - Navigate

**Sessions Screen:**
- `Enter` - Open session detail
- `r` - Refresh list
- `d` - Delete selected (with confirmation)

**Logs Screen:**
- `s` - Toggle auto-scroll
- `c` - Clear logs
- `f` - Filter by level

---

## Architecture Decisions

1. **Textual over Rich + other:** Textual provides reactive state, CSS styling, and screen management out of the box. It's the standard for modern Python TUIs as of 2025-2026.

2. **Screen-based navigation:** Each major view is a Screen subclass. This allows clean separation and easy addition of new views.

3. **Workers for async:** Textual's @work decorator handles async tasks without blocking the UI. Used for log tailing and database queries.

4. **CSS-like styling:** Textual CSS (TCSS) files separate styling from logic, making theming easier.

5. **Widget composition:** Complex widgets (like SessionCard) are composed from simpler Textual widgets, following Textual best practices.

6. **Reactive data:** Use Textual's reactive attributes for state that needs to update the UI automatically.

---

## Dependencies

**Required:**
- textual>=0.50.0

**Development:**
- textual-dev>=1.0.0 (for `textual run` and `textual console`)

**Already present:**
- click (CLI framework)
- rich (rendering, bundled with textual)

---

*Plan created: 2026-03-05*
*Textual version: >=0.50.0 (latest stable)*
