from .models import Database


class SessionManager:
    """Manages database sessions."""

    def __init__(self, db: Database):
        self.db = db
