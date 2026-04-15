"""Integration tests for the full pipeline."""

import os
import time
from pathlib import Path

import pytest

from mike.scanner.scanner import FileScanner
from mike.parser.parser import ASTParser
from mike.chunker.chunker import CodeChunker


class TestPipelineEndToEnd:
    """End-to-end tests for the full pipeline."""

    def test_full_pipeline_python_project(self, temp_dir):
        """Test full pipeline on a Python project."""
        # Create a Python project structure
        (temp_dir / "src").mkdir()
        (temp_dir / "tests").mkdir()

        # Create main.py
        main_py = temp_dir / "src" / "main.py"
        main_py.write_text("""import os
import sys
from utils import helper

class MainApp:
    def __init__(self):
        self.config = {}
    
    def run(self):
        result = helper()
        return result

def main():
    app = MainApp()
    app.run()

if __name__ == "__main__":
    main()
""")

        # Create utils.py
        utils_py = temp_dir / "src" / "utils.py"
        utils_py.write_text("""def helper():
    return 42

def unused():
    pass
""")

        # Create test file
        test_py = temp_dir / "tests" / "test_main.py"
        test_py.write_text("""import sys
sys.path.insert(0, '../src')
from main import MainApp

def test_app():
    app = MainApp()
    assert app.run() == 42
""")

        # Step 1: Scan
        scanner = FileScanner()
        files = scanner.scan_directory(str(temp_dir))

        assert len(files) == 3

        # Step 2: Parse
        parser = ASTParser()
        parsed_files = []

        for file_info in files:
            content = Path(file_info["absolute_path"]).read_text()
            ast_data = parser.parse(content, file_info["language"])
            parsed_files.append(
                {
                    **file_info,
                    "ast": ast_data,
                    "content": content,
                }
            )

        # Verify parsing results
        main_file = next(f for f in parsed_files if f["relative_path"] == "src/main.py")
        assert len(main_file["ast"]["functions"]) == 1  # main function
        assert len(main_file["ast"]["classes"]) == 1  # MainApp class
        assert len(main_file["ast"]["imports"]) >= 3  # os, sys, utils

        # Step 3: Chunk
        chunker = CodeChunker()
        all_chunks = []

        for file_info in parsed_files:
            chunks = chunker.chunk_code(
                file_info["content"], file_info["language"], file_info["relative_path"]
            )
            all_chunks.extend(chunks)

        assert len(all_chunks) >= 3  # Should have chunks from all files

        # Verify chunks have correct structure
        for chunk in all_chunks:
            assert "content" in chunk
            assert "metadata" in chunk
            assert chunk["content"]

    def test_full_pipeline_javascript_project(self, temp_dir):
        """Test full pipeline on a JavaScript project."""
        # Create JavaScript project
        (temp_dir / "src").mkdir()
        (temp_dir / "lib").mkdir()

        # Create main.js
        main_js = temp_dir / "src" / "main.js"
        main_js.write_text("""const utils = require('../lib/utils');

class App {
    constructor() {
        this.name = 'MyApp';
    }
    
    start() {
        console.log('Starting', this.name);
        utils.greet();
    }
}

const app = new App();
app.start();
""")

        # Create utils.js
        utils_js = temp_dir / "lib" / "utils.js"
        utils_js.write_text("""function greet() {
    console.log('Hello!');
}

function helper() {
    return 'helper';
}

module.exports = { greet, helper };
""")

        # Create package.json
        package_json = temp_dir / "package.json"
        package_json.write_text('{"name": "test-project", "version": "1.0.0"}')

        # Run pipeline
        scanner = FileScanner()
        files = scanner.scan_directory(str(temp_dir))

        assert len(files) == 3

        parser = ASTParser()
        js_file = next(f for f in files if f["relative_path"] == "src/main.js")
        content = Path(js_file["absolute_path"]).read_text()
        ast_data = parser.parse(content, "javascript")

        assert len(ast_data["classes"]) == 1  # App class
        assert len(ast_data["functions"]) >= 1

    def test_full_pipeline_mixed_languages(self, temp_dir):
        """Test full pipeline with mixed language project."""
        # Create Python files
        (temp_dir / "backend").mkdir()
        (temp_dir / "backend" / "main.py").write_text("def main(): pass")

        # Create JavaScript files
        (temp_dir / "frontend").mkdir()
        (temp_dir / "frontend" / "app.js").write_text("const x = 1;")

        # Create Go files
        (temp_dir / "worker").mkdir()
        (temp_dir / "worker" / "main.go").write_text("package main\nfunc main() {}")

        # Create README
        (temp_dir / "README.md").write_text("# Project")

        # Scan
        scanner = FileScanner()
        files = scanner.scan_directory(str(temp_dir))

        assert len(files) == 4

        # Check languages
        languages = {f["language"] for f in files}
        assert "Python" in languages
        assert "JavaScript" in languages
        assert "Go" in languages
        assert "Markdown" in languages

        # Parse each language
        parser = ASTParser()

        for file_info in files:
            if file_info["language"] in ["Python", "JavaScript", "Go"]:
                content = Path(file_info["absolute_path"]).read_text()
                ast_data = parser.parse(content, file_info["language"])

                # Each parsed file should have structure
                assert "functions" in ast_data
                assert "classes" in ast_data
                assert "imports" in ast_data

    def test_pipeline_preserves_file_structure(self, temp_dir):
        """Test that pipeline preserves directory structure in metadata."""
        # Create nested structure
        (temp_dir / "a" / "b" / "c").mkdir(parents=True)
        (temp_dir / "a" / "file1.py").write_text("def f1(): pass")
        (temp_dir / "a" / "b" / "file2.py").write_text("def f2(): pass")
        (temp_dir / "a" / "b" / "c" / "file3.py").write_text("def f3(): pass")

        scanner = FileScanner()
        files = scanner.scan_directory(str(temp_dir))

        paths = {f["relative_path"] for f in files}
        assert "a/file1.py" in paths
        assert "a/b/file2.py" in paths
        assert "a/b/c/file3.py" in paths

    def test_pipeline_handles_empty_files(self, temp_dir):
        """Test that pipeline handles empty files gracefully."""
        (temp_dir / "empty.py").write_text("")
        (temp_dir / "content.py").write_text("def main(): pass")

        scanner = FileScanner()
        files = scanner.scan_directory(str(temp_dir))

        assert len(files) == 1
        assert files[0]["relative_path"] == "content.py"

    def test_pipeline_handles_binary_files(self, temp_dir):
        """Test that pipeline handles binary files gracefully."""
        (temp_dir / "image.png").write_bytes(b"\x89PNG\r\n\x1a\nfake image data")
        (temp_dir / "script.py").write_text("print('hello')")

        scanner = FileScanner()
        files = scanner.scan_directory(str(temp_dir))

        assert len(files) == 1
        assert files[0]["relative_path"] == "script.py"

    def test_pipeline_gitignore_respected(self, temp_dir):
        """Test that pipeline respects .gitignore."""
        (temp_dir / ".gitignore").write_text("__pycache__/\n*.pyc\n*.log\n")
        (temp_dir / "main.py").write_text("pass")
        (temp_dir / "__pycache__").mkdir()
        (temp_dir / "__pycache__" / "main.cpython-310.pyc").write_bytes(b"compiled")
        (temp_dir / "debug.log").write_text("log message")

        scanner = FileScanner()
        files = scanner.scan_directory(str(temp_dir))

        relative_paths = {f["relative_path"] for f in files}
        assert "main.py" in relative_paths
        assert "__pycache__/main.cpython-310.pyc" not in relative_paths
        assert "debug.log" not in relative_paths

    def test_pipeline_line_counts_accurate(self, temp_dir):
        """Test that line counts are accurate."""
        code = """line1
line2
line3
line4
line5"""
        (temp_dir / "file.py").write_text(code)

        scanner = FileScanner()
        files = scanner.scan_directory(str(temp_dir))

        assert len(files) == 1
        assert files[0]["line_count"] == 5

    def test_pipeline_content_hashes_unique(self, temp_dir):
        """Test that content hashes differentiate files."""
        (temp_dir / "file1.py").write_text("def a(): pass")
        (temp_dir / "file2.py").write_text("def b(): pass")

        scanner = FileScanner()
        files = scanner.scan_directory(str(temp_dir))

        hashes = {f["content_hash"] for f in files}
        assert len(hashes) == 2  # Different content = different hashes

    def test_pipeline_content_hashes_same_content(self, temp_dir):
        """Test that identical content produces same hash."""
        content = "def main(): pass"
        (temp_dir / "file1.py").write_text(content)
        (temp_dir / "file2.py").write_text(content)

        scanner = FileScanner()
        files = scanner.scan_directory(str(temp_dir))

        hashes = {f["content_hash"] for f in files}
        assert len(hashes) == 1  # Same content = same hash


class TestPerformanceBenchmarks:
    """Performance benchmarks for the pipeline."""

    @pytest.mark.slow
    def test_scan_performance(self, temp_dir):
        """Benchmark scanning performance."""
        # Create many files
        (temp_dir / "src").mkdir()
        for i in range(100):
            (temp_dir / "src" / f"file_{i:03d}.py").write_text(f"def func_{i}(): pass")

        scanner = FileScanner()

        start_time = time.time()
        files = scanner.scan_directory(str(temp_dir))
        duration = time.time() - start_time

        assert len(files) == 100
        assert duration < 5.0  # Should scan 100 files in under 5 seconds

    @pytest.mark.slow
    def test_parse_performance(self, sample_python_code):
        """Benchmark parsing performance."""
        parser = ASTParser()

        start_time = time.time()
        for _ in range(100):
            result = parser.parse(sample_python_code, "python")
        duration = time.time() - start_time

        assert result["functions"] is not None
        assert duration < 10.0  # Should parse 100 times in under 10 seconds

    @pytest.mark.slow
    def test_chunk_performance(self, sample_python_code):
        """Benchmark chunking performance."""
        chunker = CodeChunker()

        start_time = time.time()
        for _ in range(1000):
            chunks = chunker.chunk_code(sample_python_code, "python", "test.py")
        duration = time.time() - start_time

        assert len(chunks) > 0
        assert duration < 5.0  # Should chunk 1000 times in under 5 seconds


class TestMultiLanguageSupport:
    """Test multi-language support in the pipeline."""

    def test_language_detection_accuracy(self, temp_dir):
        """Test that languages are correctly detected."""
        test_cases = [
            ("main.py", "Python"),
            ("app.js", "JavaScript"),
            ("app.ts", "TypeScript"),
            ("Main.java", "Java"),
            ("main.go", "Go"),
            ("lib.rs", "Rust"),
            ("README.md", "Markdown"),
            ("Dockerfile", "Dockerfile"),
            ("Makefile", "Makefile"),
        ]

        scanner = FileScanner()

        for filename, expected_lang in test_cases:
            (temp_dir / filename).write_text(f"// {filename}")

        files = scanner.scan_directory(str(temp_dir))

        for file_info in files:
            filename = Path(file_info["relative_path"]).name
            expected = next(lang for name, lang in test_cases if name == filename)
            assert file_info["language"] == expected, f"Wrong language for {filename}"

    def test_all_supported_languages_can_be_parsed(self, temp_dir):
        """Test that all supported languages can be parsed."""
        # Create files for each supported language
        test_files = {
            "test.py": "def main(): pass",
            "test.js": "function main() {}",
            "test.ts": "function main(): void {}",
            "test.java": "public class Test { void main() {} }",
            "test.go": "package main\nfunc main() {}",
            "test.rs": "fn main() {}",
            "test.rb": "def main; end",
            "test.php": "<?php function main() {} ?>",
        }

        scanner = FileScanner()
        parser = ASTParser()

        for filename, content in test_files.items():
            filepath = temp_dir / filename
            filepath.write_text(content)

        files = scanner.scan_directory(str(temp_dir))

        for file_info in files:
            if file_info["language"] == "Unknown":
                continue

            content = Path(file_info["absolute_path"]).read_text()

            try:
                ast_data = parser.parse(content, file_info["language"])
                # Should have structure fields
                assert "functions" in ast_data
                assert "classes" in ast_data
                assert "imports" in ast_data
            except Exception as e:
                pytest.fail(f"Failed to parse {file_info['relative_path']}: {e}")


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_directory(self, temp_dir):
        """Test scanning empty directory."""
        scanner = FileScanner()
        files = scanner.scan_directory(str(temp_dir))

        assert files == []

    def test_very_deep_directory(self, temp_dir):
        """Test scanning very deep directory structure."""
        # Create deep directory structure
        current = temp_dir
        for i in range(20):
            current = current / f"level_{i}"
            current.mkdir()

        (current / "file.py").write_text("pass")

        scanner = FileScanner()
        files = scanner.scan_directory(str(temp_dir))

        assert len(files) == 1

    def test_unicode_filenames(self, temp_dir):
        """Test handling unicode filenames."""
        (temp_dir / "文件.py").write_text("pass")
        (temp_dir / "файл.py").write_text("pass")
        (temp_dir / "ファイル.py").write_text("pass")

        scanner = FileScanner()
        files = scanner.scan_directory(str(temp_dir))

        assert len(files) == 3

    def test_special_characters_in_content(self, temp_dir):
        """Test handling special characters in file content."""
        content = """def main():
    # Unicode: 你好世界 🌍
    print("Special chars: àáâãäåæçèéêë")
    print("Quotes: 'single' \\"double\\"")
    print("Newlines: \\n\\r\\t")
"""
        (temp_dir / "special.py").write_text(content, encoding="utf-8")

        scanner = FileScanner()
        files = scanner.scan_directory(str(temp_dir))

        assert len(files) == 1

        parser = ASTParser()
        file_info = files[0]
        content = Path(file_info["absolute_path"]).read_text()
        ast_data = parser.parse(content, "python")

        assert len(ast_data["functions"]) == 1

    def test_symlinks_handled(self, temp_dir):
        """Test handling of symbolic links."""
        # Create a file and a symlink
        (temp_dir / "real.py").write_text("pass")

        try:
            (temp_dir / "link.py").symlink_to(temp_dir / "real.py")

            scanner = FileScanner()
            files = scanner.scan_directory(str(temp_dir))

            # Should find both files (symlinks are followed)
            assert len(files) == 2
        except OSError:
            # Symlinks not supported on this platform
            pytest.skip("Symlinks not supported")

    def test_permission_error_handling(self, temp_dir):
        """Test handling of permission errors."""
        # Create a file
        secret_file = temp_dir / "secret.py"
        secret_file.write_text("password = 'secret'")

        try:
            # Remove read permission
            secret_file.chmod(0o000)

            scanner = FileScanner()
            files = scanner.scan_directory(str(temp_dir))

            # Should handle permission error gracefully
            # The file might be skipped or included depending on implementation
        finally:
            # Restore permissions for cleanup
            secret_file.chmod(0o644)
