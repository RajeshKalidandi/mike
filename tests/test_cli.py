"""Tests for CLI module."""

import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from mike.cli import main


class TestCLI:
    """Test cases for CLI commands."""

    def test_scan_command_local_path(self):
        """Test scan command with local path."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            Path(tmpdir, "main.py").write_text("print('hello')")

            result = runner.invoke(main, ["scan", tmpdir])

            assert result.exit_code == 0
            assert "Scanned" in result.output or "files" in result.output.lower()

    def test_scan_with_db_storage(self):
        """Test scan stores data in database."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            Path(tmpdir, "code").mkdir()
            Path(tmpdir, "code", "app.py").write_text("def main(): pass")

            result = runner.invoke(
                main, ["--db", db_path, "scan", os.path.join(tmpdir, "code")]
            )

            assert result.exit_code == 0
            assert os.path.exists(db_path)

    def test_scan_with_session_name(self):
        """Test scan command with custom session name."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            Path(tmpdir, "main.py").write_text("x = 1")

            result = runner.invoke(
                main,
                [
                    "--db",
                    db_path,
                    "scan",
                    "--session-name",
                    "my-test-session",
                    tmpdir,
                ],
            )

            assert result.exit_code == 0

    def test_list_sessions_empty(self):
        """Test list-sessions with no sessions."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")

            result = runner.invoke(main, ["--db", db_path, "list-sessions"])

            assert result.exit_code == 0
            assert (
                "sessions" in result.output.lower() or "empty" in result.output.lower()
            )

    def test_parse_command(self):
        """Test parse command with session ID."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            Path(tmpdir, "code").mkdir()
            Path(tmpdir, "code", "app.py").write_text("def main():\n    pass\n")

            # First scan to create session
            scan_result = runner.invoke(
                main, ["--db", db_path, "scan", os.path.join(tmpdir, "code")]
            )
            assert scan_result.exit_code == 0

            # Extract session ID from scan output
            # Session ID format: UUID (36 chars)
            import re

            session_match = re.search(r"[0-9a-f-]{36}", scan_result.output)
            if session_match:
                session_id = session_match.group(0)

                # Now parse
                result = runner.invoke(main, ["--db", db_path, "parse", session_id])

                assert result.exit_code == 0
                assert (
                    "parsed" in result.output.lower()
                    or "parse" in result.output.lower()
                )

    def test_verbose_flag(self):
        """Test verbose output flag."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            Path(tmpdir, "main.py").write_text("x = 1")

            result = runner.invoke(main, ["--verbose", "--db", db_path, "scan", tmpdir])

            assert result.exit_code == 0

    def test_help_command(self):
        """Test CLI help displays correctly."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Mike" in result.output

    def test_scan_help(self):
        """Test scan command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["scan", "--help"])

        assert result.exit_code == 0
        assert "scan" in result.output.lower()
