import pytest
import tempfile
import os
from pathlib import Path
from mike.scanner.scanner import FileScanner


class TestFileScanner:
    def test_scan_local_directory(self):
        """Test scanning a local directory."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_repo"
        scanner = FileScanner()

        files = scanner.scan_directory(str(fixture_path))

        assert len(files) >= 2  # At least Python and JS files

        # Check Python file detected
        py_files = [f for f in files if f["relative_path"].endswith(".py")]
        assert len(py_files) > 0
        assert py_files[0]["language"] == "Python"

        # Check JS file detected
        js_files = [f for f in files if f["relative_path"].endswith(".js")]
        assert len(js_files) > 0
        assert js_files[0]["language"] == "JavaScript"

    def test_respects_gitignore(self):
        """Test that .gitignore patterns are respected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create structure
            Path(tmpdir, "src").mkdir()
            Path(tmpdir, "src", "main.py").write_text("# main")
            Path(tmpdir, "src", "__pycache__").mkdir()
            Path(tmpdir, "src", "__pycache__", "cache.pyc").write_text("cached")
            Path(tmpdir, ".gitignore").write_text("__pycache__/\n*.pyc")

            scanner = FileScanner()
            files = scanner.scan_directory(tmpdir)

            paths = [f["relative_path"] for f in files]
            assert "src/main.py" in paths
            assert "src/__pycache__/cache.pyc" not in paths

    def test_calculates_content_hash(self):
        """Test that content hash is calculated for each file."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_repo"
        scanner = FileScanner()

        files = scanner.scan_directory(str(fixture_path))

        for f in files:
            assert "content_hash" in f
            assert len(f["content_hash"]) == 64  # SHA-256 hex
