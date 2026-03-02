"""End-to-end tests for CLI commands."""

import json
import os
from pathlib import Path
from click.testing import CliRunner

import pytest

from architectai.cli import main


class TestCLIScan:
    """Test cases for CLI scan command."""

    def test_scan_local_directory(self, temp_dir):
        """Test scanning a local directory."""
        runner = CliRunner()

        # Create test files
        (temp_dir / "main.py").write_text("def main(): pass")
        (temp_dir / "README.md").write_text("# Test")

        result = runner.invoke(
            main, ["--db", str(temp_dir / "test.db"), "scan", str(temp_dir)]
        )

        assert result.exit_code == 0
        assert "2 files" in result.output or "files" in result.output

    def test_scan_json_output(self, temp_dir):
        """Test scan with JSON output format."""
        runner = CliRunner()

        (temp_dir / "main.py").write_text("def main(): pass")

        result = runner.invoke(
            main,
            [
                "--db",
                str(temp_dir / "test.db"),
                "--output",
                "json",
                "scan",
                str(temp_dir),
            ],
        )

        assert result.exit_code == 0

        # Parse JSON output
        data = json.loads(result.output)
        assert "session_id" in data
        assert "files_scanned" in data
        assert data["files_scanned"] >= 1

    def test_scan_markdown_output(self, temp_dir):
        """Test scan with Markdown output format."""
        runner = CliRunner()

        (temp_dir / "main.py").write_text("def main(): pass")

        result = runner.invoke(
            main,
            [
                "--db",
                str(temp_dir / "test.db"),
                "--output",
                "markdown",
                "scan",
                str(temp_dir),
            ],
        )

        assert result.exit_code == 0
        assert "# Scan Results" in result.output

    def test_scan_nonexistent_path(self, temp_dir):
        """Test scanning non-existent path."""
        runner = CliRunner()

        result = runner.invoke(
            main, ["--db", str(temp_dir / "test.db"), "scan", "/nonexistent/path"]
        )

        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_scan_verbose(self, temp_dir):
        """Test scan with verbose output."""
        runner = CliRunner()

        (temp_dir / "main.py").write_text("def main(): pass")

        result = runner.invoke(
            main,
            ["--db", str(temp_dir / "test.db"), "--verbose", "scan", str(temp_dir)],
        )

        assert result.exit_code == 0
        # Verbose output should contain more details


class TestCLISession:
    """Test cases for CLI session commands."""

    def test_session_list_empty(self, temp_dir):
        """Test listing sessions when none exist."""
        runner = CliRunner()

        result = runner.invoke(
            main, ["--db", str(temp_dir / "test.db"), "session", "list"]
        )

        assert result.exit_code == 0

    def test_session_list_after_scan(self, temp_dir):
        """Test listing sessions after creating one."""
        runner = CliRunner()

        (temp_dir / "main.py").write_text("pass")

        # Create a session
        runner.invoke(main, ["--db", str(temp_dir / "test.db"), "scan", str(temp_dir)])

        # List sessions
        result = runner.invoke(
            main, ["--db", str(temp_dir / "test.db"), "session", "list"]
        )

        assert result.exit_code == 0

    def test_session_info(self, temp_dir):
        """Test getting session info."""
        runner = CliRunner()

        (temp_dir / "main.py").write_text("pass")

        # Create a session
        scan_result = runner.invoke(
            main,
            [
                "--db",
                str(temp_dir / "test.db"),
                "--output",
                "json",
                "scan",
                str(temp_dir),
            ],
        )

        session_data = json.loads(scan_result.output)
        session_id = session_data["session_id"]

        # Get session info
        result = runner.invoke(
            main, ["--db", str(temp_dir / "test.db"), "session", "info", session_id]
        )

        assert result.exit_code == 0

    def test_session_delete(self, temp_dir):
        """Test deleting a session."""
        runner = CliRunner()

        (temp_dir / "main.py").write_text("pass")

        # Create a session
        scan_result = runner.invoke(
            main,
            [
                "--db",
                str(temp_dir / "test.db"),
                "--output",
                "json",
                "scan",
                str(temp_dir),
            ],
        )

        session_data = json.loads(scan_result.output)
        session_id = session_data["session_id"]

        # Delete session
        result = runner.invoke(
            main,
            [
                "--db",
                str(temp_dir / "test.db"),
                "session",
                "delete",
                "--force",
                session_id,
            ],
        )

        assert result.exit_code == 0


class TestCLIParse:
    """Test cases for CLI parse command."""

    def test_parse_session(self, temp_dir):
        """Test parsing a session."""
        runner = CliRunner()

        (temp_dir / "main.py").write_text("def main(): pass")

        # Create a session
        scan_result = runner.invoke(
            main,
            [
                "--db",
                str(temp_dir / "test.db"),
                "--output",
                "json",
                "scan",
                str(temp_dir),
            ],
        )

        session_data = json.loads(scan_result.output)
        session_id = session_data["session_id"]

        # Parse
        result = runner.invoke(
            main, ["--db", str(temp_dir / "test.db"), "parse", session_id]
        )

        assert result.exit_code == 0

    def test_parse_nonexistent_session(self, temp_dir):
        """Test parsing non-existent session."""
        runner = CliRunner()

        result = runner.invoke(
            main, ["--db", str(temp_dir / "test.db"), "parse", "nonexistent-session-id"]
        )

        assert result.exit_code == 1


class TestCLIStatus:
    """Test cases for CLI status command."""

    def test_status_command(self, temp_dir):
        """Test status command."""
        runner = CliRunner()

        result = runner.invoke(main, ["--db", str(temp_dir / "test.db"), "status"])

        assert result.exit_code == 0
        assert "ArchitectAI" in result.output or "version" in result.output.lower()

    def test_status_json_output(self, temp_dir):
        """Test status with JSON output."""
        runner = CliRunner()

        result = runner.invoke(
            main, ["--db", str(temp_dir / "test.db"), "--output", "json", "status"]
        )

        assert result.exit_code == 0

        data = json.loads(result.output)
        assert "version" in data
        assert "database_path" in data


class TestCLIDocs:
    """Test cases for CLI docs command."""

    @pytest.mark.skip(reason="Requires orchestrator dependencies")
    def test_docs_generation(self, temp_dir):
        """Test documentation generation."""
        runner = CliRunner()

        (temp_dir / "main.py").write_text("def main(): pass")

        # Create session
        scan_result = runner.invoke(
            main,
            [
                "--db",
                str(temp_dir / "test.db"),
                "--output",
                "json",
                "scan",
                str(temp_dir),
            ],
        )

        session_data = json.loads(scan_result.output)
        session_id = session_data["session_id"]

        output_dir = temp_dir / "docs"

        # Generate docs
        result = runner.invoke(
            main,
            [
                "--db",
                str(temp_dir / "test.db"),
                "docs",
                "--output",
                str(output_dir),
                session_id,
            ],
        )

        assert result.exit_code == 0


class TestCLIRebuild:
    """Test cases for CLI rebuild command."""

    @pytest.mark.skip(reason="Requires orchestrator dependencies")
    def test_rebuild_project(self, temp_dir):
        """Test rebuilding a project."""
        runner = CliRunner()

        (temp_dir / "main.py").write_text("def main(): pass")

        # Create session
        scan_result = runner.invoke(
            main,
            [
                "--db",
                str(temp_dir / "test.db"),
                "--output",
                "json",
                "scan",
                str(temp_dir),
            ],
        )

        session_data = json.loads(scan_result.output)
        session_id = session_data["session_id"]

        output_dir = temp_dir / "rebuilt"

        # Rebuild
        result = runner.invoke(
            main,
            ["--db", str(temp_dir / "test.db"), "rebuild", session_id, str(output_dir)],
        )

        assert result.exit_code == 0


class TestCLIOutputFormats:
    """Test different output formats."""

    def test_plain_output(self, temp_dir):
        """Test plain text output."""
        runner = CliRunner()

        (temp_dir / "main.py").write_text("pass")

        result = runner.invoke(
            main,
            [
                "--db",
                str(temp_dir / "test.db"),
                "--output",
                "plain",
                "scan",
                str(temp_dir),
            ],
        )

        assert result.exit_code == 0
        # Plain output should not be JSON
        try:
            json.loads(result.output)
            assert False, "Output should not be valid JSON"
        except json.JSONDecodeError:
            pass

    def test_json_output_valid(self, temp_dir):
        """Test that JSON output is valid."""
        runner = CliRunner()

        (temp_dir / "main.py").write_text("pass")

        result = runner.invoke(
            main,
            [
                "--db",
                str(temp_dir / "test.db"),
                "--output",
                "json",
                "scan",
                str(temp_dir),
            ],
        )

        assert result.exit_code == 0

        data = json.loads(result.output)
        assert isinstance(data, dict)

    def test_markdown_output_format(self, temp_dir):
        """Test Markdown output format."""
        runner = CliRunner()

        (temp_dir / "main.py").write_text("pass")

        result = runner.invoke(
            main,
            [
                "--db",
                str(temp_dir / "test.db"),
                "--output",
                "markdown",
                "scan",
                str(temp_dir),
            ],
        )

        assert result.exit_code == 0
        assert "#" in result.output  # Markdown headers


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def test_invalid_command(self, temp_dir):
        """Test invalid command."""
        runner = CliRunner()

        result = runner.invoke(
            main, ["--db", str(temp_dir / "test.db"), "invalidcommand"]
        )

        assert result.exit_code != 0

    def test_missing_argument(self, temp_dir):
        """Test command with missing argument."""
        runner = CliRunner()

        result = runner.invoke(
            main,
            [
                "--db",
                str(temp_dir / "test.db"),
                "scan",  # Missing required argument
            ],
        )

        assert result.exit_code != 0

    def test_invalid_session_id_format(self, temp_dir):
        """Test with invalid session ID format."""
        runner = CliRunner()

        result = runner.invoke(
            main,
            ["--db", str(temp_dir / "test.db"), "session", "info", "invalid-id-format"],
        )

        assert result.exit_code == 1


class TestCLIGlobalOptions:
    """Test global CLI options."""

    def test_verbose_flag(self):
        """Test verbose flag."""
        runner = CliRunner()

        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "verbose" in result.output.lower()

    def test_db_option(self):
        """Test database option."""
        runner = CliRunner()

        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "db" in result.output.lower()

    def test_output_option(self):
        """Test output format option."""
        runner = CliRunner()

        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "output" in result.output.lower()


class TestCLIMultiLanguageSupport:
    """Test CLI with multiple languages."""

    def test_scan_detects_multiple_languages(self, temp_dir):
        """Test that CLI detects multiple languages."""
        runner = CliRunner()

        # Create files in different languages
        (temp_dir / "main.py").write_text("def main(): pass")
        (temp_dir / "app.js").write_text("const x = 1;")
        (temp_dir / "main.go").write_text("package main\nfunc main() {}")

        result = runner.invoke(
            main,
            [
                "--db",
                str(temp_dir / "test.db"),
                "--output",
                "json",
                "scan",
                str(temp_dir),
            ],
        )

        assert result.exit_code == 0

        data = json.loads(result.output)
        languages = data.get("languages", {})

        assert len(languages) >= 2
        assert "Python" in languages or "JavaScript" in languages or "Go" in languages
