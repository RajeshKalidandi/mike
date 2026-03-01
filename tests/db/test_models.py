import pytest
import sqlite3
import tempfile
import os
from architectai.db.models import Database, Session, FileRecord


class TestDatabase:
    def test_database_initialization(self):
        """Test database creates tables correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = Database(db_path)
            db.init()

            # Verify tables exist
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row[0] for row in cursor.fetchall()}
            conn.close()

            assert "sessions" in tables
            assert "files" in tables
            assert "code_hashes" in tables

    def test_session_creation(self):
        """Test session creation and retrieval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(os.path.join(tmpdir, "test.db"))
            db.init()

            session_id = db.create_session("/path/to/repo", "upload")
            session = db.get_session(session_id)

            assert session is not None
            assert session["source_path"] == "/path/to/repo"
            assert session["session_type"] == "upload"
            assert session["status"] == "active"


class TestFileRecord:
    def test_file_insertion(self):
        """Test file record insertion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(os.path.join(tmpdir, "test.db"))
            db.init()

            session_id = db.create_session("/repo", "upload")
            file_id = db.insert_file(
                session_id=session_id,
                relative_path="src/main.py",
                absolute_path="/repo/src/main.py",
                language="Python",
                size_bytes=1024,
                line_count=50,
                content_hash="abc123",
            )

            assert file_id is not None

            files = db.get_files_for_session(session_id)
            assert len(files) == 1
            assert files[0]["relative_path"] == "src/main.py"
