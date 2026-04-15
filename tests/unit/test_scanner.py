"""Unit tests for the FileScanner module."""

import os
from pathlib import Path

import pytest

from mike.scanner.scanner import FileScanner


class TestFileScanner:
    """Test cases for FileScanner."""

    def test_scanner_initialization(self):
        """Test that scanner initializes correctly."""
        scanner = FileScanner()
        assert scanner.gitignore_patterns == []
        assert isinstance(scanner.BINARY_EXTENSIONS, set)
        assert ".pyc" in scanner.BINARY_EXTENSIONS
        assert ".py" not in scanner.BINARY_EXTENSIONS

    def test_scan_directory_empty(self, temp_dir):
        """Test scanning an empty directory."""
        scanner = FileScanner()
        files = scanner.scan_directory(str(temp_dir))
        assert files == []

    def test_scan_directory_with_files(self, temp_dir):
        """Test scanning directory with Python files."""
        scanner = FileScanner()

        # Create test files
        (temp_dir / "main.py").write_text("def main(): pass")
        (temp_dir / "utils.py").write_text("def helper(): pass")
        (temp_dir / "README.md").write_text("# README")

        files = scanner.scan_directory(str(temp_dir))

        assert len(files) == 3
        relative_paths = {f["relative_path"] for f in files}
        assert "main.py" in relative_paths
        assert "utils.py" in relative_paths
        assert "README.md" in relative_paths

    def test_scan_skips_binary_files(self, temp_dir):
        """Test that binary files are skipped."""
        scanner = FileScanner()

        # Create binary and text files
        (temp_dir / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (temp_dir / "script.py").write_text("print('hello')")

        files = scanner.scan_directory(str(temp_dir))

        assert len(files) == 1
        assert files[0]["relative_path"] == "script.py"

    def test_scan_skips_hidden_directories(self, temp_dir):
        """Test that hidden directories are skipped."""
        scanner = FileScanner()

        # Create hidden and visible directories
        (temp_dir / ".git").mkdir()
        (temp_dir / ".git" / "config").write_text("[core]")
        (temp_dir / "src").mkdir()
        (temp_dir / "src" / "main.py").write_text("pass")

        files = scanner.scan_directory(str(temp_dir))

        assert len(files) == 1
        assert files[0]["relative_path"] == "src/main.py"

    def test_scan_respects_gitignore(self, temp_dir):
        """Test that .gitignore patterns are respected."""
        scanner = FileScanner()

        # Create files and gitignore
        (temp_dir / "main.py").write_text("pass")
        (temp_dir / "__pycache__").mkdir()
        (temp_dir / "__pycache__" / "main.cpython-310.pyc").write_bytes(b"compiled")
        (temp_dir / ".gitignore").write_text("__pycache__/\n*.pyc\n")

        files = scanner.scan_directory(str(temp_dir))

        relative_paths = {f["relative_path"] for f in files}
        assert "main.py" in relative_paths
        assert "__pycache__/main.cpython-310.pyc" not in relative_paths

    def test_file_info_extraction(self, temp_dir):
        """Test that file metadata is correctly extracted."""
        scanner = FileScanner()

        (temp_dir / "test.py").write_text("line1\nline2\nline3\n")

        files = scanner.scan_directory(str(temp_dir))

        assert len(files) == 1
        file_info = files[0]

        assert file_info["relative_path"] == "test.py"
        assert file_info["language"] == "Python"
        assert file_info["line_count"] == 3
        assert file_info["size_bytes"] == 18  # "line1\nline2\nline3\n"
        assert file_info["extension"] == ".py"
        assert len(file_info["content_hash"]) == 64  # SHA-256 hex length

    def test_detect_language_by_extension(self, temp_dir):
        """Test language detection for various extensions."""
        scanner = FileScanner()

        test_cases = [
            ("main.py", "Python"),
            ("script.js", "JavaScript"),
            ("app.ts", "TypeScript"),
            ("Main.java", "Java"),
            ("main.go", "Go"),
            ("lib.rs", "Rust"),
            ("README.md", "Markdown"),
            ("config.json", "JSON"),
            ("Dockerfile", "Dockerfile"),
            ("Makefile", "Makefile"),
        ]

        for filename, expected_lang in test_cases:
            (temp_dir / filename).write_text(f"// {filename}")

        files = scanner.scan_directory(str(temp_dir))

        for file_info in files:
            filename = Path(file_info["relative_path"]).name
            expected = next(lang for name, lang in test_cases if name == filename)
            assert file_info["language"] == expected, f"Wrong language for {filename}"

    def test_skip_empty_files(self, temp_dir):
        """Test that empty files are skipped."""
        scanner = FileScanner()

        (temp_dir / "empty.py").write_text("")
        (temp_dir / "content.py").write_text("pass")

        files = scanner.scan_directory(str(temp_dir))

        assert len(files) == 1
        assert files[0]["relative_path"] == "content.py"

    def test_skip_binary_content(self, temp_dir):
        """Test that files with binary content are skipped."""
        scanner = FileScanner()

        # Create file with binary content but text extension
        (temp_dir / "fake.py").write_bytes(b"\x00\x01\x02\x03\xff\xfe")

        files = scanner.scan_directory(str(temp_dir))

        assert len(files) == 0

    def test_gitignore_wildcards(self, temp_dir):
        """Test gitignore wildcard patterns."""
        scanner = FileScanner()

        (temp_dir / ".gitignore").write_text("*.log\n")
        (temp_dir / "app.log").write_text("log line")
        (temp_dir / "debug.log").write_text("debug line")
        (temp_dir / "main.py").write_text("pass")

        files = scanner.scan_directory(str(temp_dir))

        relative_paths = {f["relative_path"] for f in files}
        assert "main.py" in relative_paths
        assert "app.log" not in relative_paths
        assert "debug.log" not in relative_paths

    def test_gitignore_directory_pattern(self, temp_dir):
        """Test gitignore directory patterns."""
        scanner = FileScanner()

        (temp_dir / ".gitignore").write_text("node_modules/\n")
        (temp_dir / "node_modules").mkdir()
        (temp_dir / "node_modules" / "package.json").write_text("{}")
        (temp_dir / "src").mkdir()
        (temp_dir / "src" / "index.js").write_text("const x = 1;")

        files = scanner.scan_directory(str(temp_dir))

        relative_paths = {f["relative_path"] for f in files}
        assert "src/index.js" in relative_paths
        assert "node_modules/package.json" not in relative_paths

    def test_nested_directories(self, temp_dir):
        """Test scanning nested directory structures."""
        scanner = FileScanner()

        # Create nested structure
        (temp_dir / "a" / "b" / "c").mkdir(parents=True)
        (temp_dir / "a" / "file1.py").write_text("pass")
        (temp_dir / "a" / "b" / "file2.py").write_text("pass")
        (temp_dir / "a" / "b" / "c" / "file3.py").write_text("pass")

        files = scanner.scan_directory(str(temp_dir))

        assert len(files) == 3
        relative_paths = {f["relative_path"] for f in files}
        assert "a/file1.py" in relative_paths
        assert "a/b/file2.py" in relative_paths
        assert "a/b/c/file3.py" in relative_paths

    def test_multiple_languages_count(self, temp_dir):
        """Test scanning project with multiple languages."""
        scanner = FileScanner()

        # Create files in different languages
        (temp_dir / "src").mkdir()
        (temp_dir / "src" / "main.py").write_text("pass")
        (temp_dir / "src" / "utils.py").write_text("pass")
        (temp_dir / "src" / "app.js").write_text("const x = 1;")
        (temp_dir / "src" / "app.ts").write_text("const y: number = 1;")
        (temp_dir / "README.md").write_text("# Project")

        files = scanner.scan_directory(str(temp_dir))

        languages = {}
        for f in files:
            lang = f["language"]
            languages[lang] = languages.get(lang, 0) + 1

        assert languages.get("Python") == 2
        assert languages.get("JavaScript") == 1
        assert languages.get("TypeScript") == 1
        assert languages.get("Markdown") == 1

    def test_content_hash_consistency(self, temp_dir):
        """Test that content hash is consistent for same content."""
        scanner = FileScanner()

        content = "def main():\n    return 42\n"
        (temp_dir / "file1.py").write_text(content)
        (temp_dir / "file2.py").write_text(content)

        files = scanner.scan_directory(str(temp_dir))

        hashes = [f["content_hash"] for f in files]
        assert hashes[0] == hashes[1]

    def test_content_hash_changes(self, temp_dir):
        """Test that content hash changes with content."""
        scanner = FileScanner()

        (temp_dir / "file1.py").write_text("def a(): pass")
        (temp_dir / "file2.py").write_text("def b(): pass")

        files = scanner.scan_directory(str(temp_dir))

        hashes = [f["content_hash"] for f in files]
        assert hashes[0] != hashes[1]


class TestGitignoreMatching:
    """Test cases for gitignore pattern matching."""

    def test_simple_pattern(self, temp_dir):
        """Test simple filename matching."""
        scanner = FileScanner()
        scanner.gitignore_patterns = ["test.py"]

        assert scanner._matches_gitignore(Path("test.py"))
        assert not scanner._matches_gitignore(Path("other.py"))

    def test_wildcard_pattern(self, temp_dir):
        """Test wildcard pattern matching."""
        scanner = FileScanner()
        scanner.gitignore_patterns = ["*.pyc"]

        assert scanner._matches_gitignore(Path("test.pyc"))
        assert scanner._matches_gitignore(Path("main.pyc"))
        assert not scanner._matches_gitignore(Path("test.py"))

    def test_directory_pattern(self, temp_dir):
        """Test directory pattern matching."""
        scanner = FileScanner()
        scanner.gitignore_patterns = ["build/"]

        assert scanner._matches_gitignore(Path("build"))
        assert scanner._matches_gitignore(Path("build/output.txt"))

    def test_comment_lines_ignored(self, temp_dir):
        """Test that comment lines in gitignore are ignored."""
        scanner = FileScanner()

        gitignore_path = temp_dir / ".gitignore"
        gitignore_path.write_text("# This is a comment\n*.pyc\n")

        patterns = scanner._load_gitignore(gitignore_path)

        assert "# This is a comment" not in patterns
        assert "*.pyc" in patterns

    def test_empty_lines_ignored(self, temp_dir):
        """Test that empty lines in gitignore are ignored."""
        scanner = FileScanner()

        gitignore_path = temp_dir / ".gitignore"
        gitignore_path.write_text("*.pyc\n\n\n*.log\n")

        patterns = scanner._load_gitignore(gitignore_path)

        assert "" not in patterns
        assert len(patterns) == 2
