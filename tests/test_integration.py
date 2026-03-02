"""Integration tests for full pipeline."""

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from architectai.cli import main
from architectai.db.models import Database


class TestIntegration:
    """Integration tests for the full pipeline."""

    def test_full_pipeline_local_repo(self):
        """Test full pipeline with local repository."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test repository
            code_dir = Path(tmpdir, "myproject")
            code_dir.mkdir()

            # Python file
            (code_dir / "main.py").write_text(
                '''
import os
import sys

def main():
    """Main function."""
    print("Hello, World!")

if __name__ == "__main__":
    main()
'''
            )

            # JavaScript file
            (code_dir / "app.js").write_text(
                """
const utils = require('./utils');

function init() {
    console.log("Initializing...");
}

module.exports = { init };
"""
            )

            # Gitignore
            (code_dir / ".gitignore").write_text("node_modules/\n__pycache__/")

            db_path = os.path.join(tmpdir, "test.db")

            # Run scan
            result = runner.invoke(
                main, ["--db", db_path, "--verbose", "scan", str(code_dir)]
            )

            assert result.exit_code == 0, f"Scan failed: {result.output}"
            assert "Found 3 files" in result.output

            # Verify database
            db = Database(db_path)

            # Get session
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM sessions LIMIT 1")
                row = cursor.fetchone()
                assert row is not None, "No session found in database"
                session_id = row[0]

            # Run parse
            result = runner.invoke(
                main, ["--db", db_path, "--verbose", "parse", session_id]
            )

            assert result.exit_code == 0, f"Parse failed: {result.output}"
            assert "Parsed" in result.output

            # Verify files were parsed (2 code files + .gitignore)
            files = db.get_files_for_session(session_id)
            assert len(files) == 3, f"Expected 3 files, got {len(files)}"

            # Check that all files have been parsed
            for file_record in files:
                assert file_record["ast_available"] == 1, (
                    f"File {file_record['relative_path']} was not parsed"
                )

    def test_scan_github_repo_mock(self, monkeypatch):
        """Test scanning a GitHub repository (with mocked clone)."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock repo structure
            mock_repo = Path(tmpdir, "mock_repo")
            mock_repo.mkdir()
            (mock_repo / "README.md").write_text("# Test Repo\n")

            # Mock the clone function - must patch where it's imported in cli.py
            def mock_clone(repo_url, temp_dir, branch=None, depth=1):
                return str(mock_repo)

            # Patch clone_repository where it's imported in cli module
            monkeypatch.setattr("architectai.cli.clone_repository", mock_clone)

            db_path = os.path.join(tmpdir, "test.db")

            # Run scan with git URL (must end in .git)
            result = runner.invoke(
                main,
                [
                    "--db",
                    db_path,
                    "--verbose",
                    "scan",
                    "https://github.com/user/repo.git",
                ],
            )

            assert result.exit_code == 0, f"Scan failed: {result.output}"
            assert "Scanned 1 files" in result.output

    def test_list_sessions_command(self):
        """Test the list-sessions command."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")

            # Run list-sessions
            result = runner.invoke(main, ["--db", db_path, "list-sessions"])

            assert result.exit_code == 0, f"Command failed: {result.output}"
            assert "Sessions:" in result.output or "No sessions found" in result.output

    def test_parse_invalid_session(self):
        """Test parsing with invalid session ID."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")

            # Run parse with invalid session ID
            result = runner.invoke(
                main, ["--db", db_path, "parse", "invalid-session-id"]
            )

            assert result.exit_code == 1
            assert "Error: Session not found" in result.output

    def test_scan_invalid_path(self):
        """Test scanning an invalid path."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")

            # Run scan with invalid path
            result = runner.invoke(main, ["--db", db_path, "scan", "/nonexistent/path"])

            assert result.exit_code == 1
            assert "Error: Path not found" in result.output
