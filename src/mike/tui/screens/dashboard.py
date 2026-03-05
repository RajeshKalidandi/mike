"""Dashboard screen for Mike TUI."""

from textual.screen import Screen
from textual.widgets import Static
from textual.containers import Grid as GridContainer
from textual.reactive import reactive


class DashboardCard(Static):
    """A card showing a metric."""

    def __init__(self, title: str, value: str = "--", **kwargs):
        self.card_title = title
        self.card_value = value
        super().__init__(**kwargs)
        self.add_class("dashboard-card")

    def compose(self):
        yield Static(self.card_title, classes="dashboard-card-title")
        yield Static(self.card_value, classes="dashboard-card-value", id="card-value")

    def update_value(self, value: str):
        """Update the card value."""
        self.card_value = value
        value_widget = self.query_one("#card-value", Static)
        value_widget.update(value)


class DashboardScreen(Screen):
    """Main dashboard showing system status."""

    BINDINGS = [
        ("r", "refresh", "Refresh"),
    ]

    system_status = reactive({})

    def compose(self):
        """Compose the dashboard."""
        with GridContainer(id="dashboard-grid"):
            yield DashboardCard("Sessions", "--", id="sessions-card")
            yield DashboardCard("Agents Available", "--", id="agents-card")
            yield DashboardCard("Database", "--", id="db-card")
            yield DashboardCard("Version", "--", id="version-card")

    def on_mount(self):
        """Load initial data."""
        self.load_status()

    def load_status(self):
        """Load system status."""
        try:
            from mike.cli_orchestrator import Orchestrator

            orchestrator = Orchestrator(self.app.db_path)
            status = orchestrator.get_system_status()
            self.update_cards(status)
        except Exception as e:
            self.update_cards({"error": str(e)})

    def update_cards(self, status: dict):
        """Update dashboard cards with status."""
        sessions = self.query_one("#sessions-card", DashboardCard)
        agents = self.query_one("#agents-card", DashboardCard)
        db = self.query_one("#db-card", DashboardCard)
        version = self.query_one("#version-card", DashboardCard)

        sessions.update_value(str(status.get("session_count", 0)))
        agents.update_value(
            str(
                len(
                    [
                        a
                        for a in status.get("agents", {}).values()
                        if a.get("status") == "available"
                    ]
                )
            )
        )
        db.update_value("Connected" if status.get("database_path") else "Not connected")
        version.update_value(status.get("version", "--"))

    def action_refresh(self):
        """Refresh dashboard."""
        self.load_status()
