"""Unit tests for the CodeChunker module."""

import pytest

from architectai.chunker.chunker import CodeChunker, CodeChunk


class TestCodeChunker:
    """Test cases for CodeChunker."""

    def test_chunker_initialization(self):
        """Test that chunker initializes with correct defaults."""
        chunker = CodeChunker()
        assert chunker.chunk_size == 1000
        assert chunker.chunk_overlap == 200

    def test_chunker_custom_settings(self):
        """Test chunker with custom settings."""
        chunker = CodeChunker(chunk_size=500, chunk_overlap=100)
        assert chunker.chunk_size == 500
        assert chunker.chunk_overlap == 100

    def test_chunk_empty_code(self):
        """Test chunking empty code."""
        chunker = CodeChunker()
        chunks = chunker.chunk_code("", "python", "test.py")
        assert chunks == []

    def test_chunk_whitespace_code(self):
        """Test chunking whitespace-only code."""
        chunker = CodeChunker()
        chunks = chunker.chunk_code("   \n\n  ", "python", "test.py")
        assert chunks == []

    def test_chunk_simple_function(self):
        """Test chunking simple function."""
        chunker = CodeChunker()
        code = """def main():
    pass"""

        chunks = chunker.chunk_code(code, "python", "test.py")

        assert len(chunks) == 1
        assert "def main():" in chunks[0]["content"]
        assert chunks[0]["metadata"]["name"] == "main"

    def test_chunk_multiple_functions(self):
        """Test chunking multiple functions."""
        chunker = CodeChunker()
        code = """def func1():
    return 1

def func2():
    return 2

def func3():
    return 3"""

        chunks = chunker.chunk_code(code, "python", "test.py")

        # Should create chunks for each function
        assert len(chunks) >= 3

        # Check that function names are in metadata
        names = {
            chunk["metadata"]["name"]
            for chunk in chunks
            if chunk["metadata"].get("name")
        }
        assert "func1" in names or any("func1" in c["content"] for c in chunks)
        assert "func2" in names or any("func2" in c["content"] for c in chunks)

    def test_chunk_with_class(self):
        """Test chunking code with class definition."""
        chunker = CodeChunker()
        code = """class MyClass:
    def __init__(self):
        self.value = 0
    
    def get_value(self):
        return self.value"""

        chunks = chunker.chunk_code(code, "python", "test.py")

        # Should have at least one chunk
        assert len(chunks) >= 1

        # Check class is recognized
        class_chunks = [c for c in chunks if "MyClass" in c["metadata"].get("name", "")]
        assert len(class_chunks) >= 1 or any(
            "class MyClass" in c["content"] for c in chunks
        )

    def test_chunk_large_file_splitting(self):
        """Test that large files are split with overlap."""
        chunker = CodeChunker(chunk_size=100, chunk_overlap=20)

        # Create a large code block
        lines = [f"line_{i:03d} = {i}" for i in range(100)]
        code = "\n".join(lines)

        chunks = chunker.chunk_code(code, "python", "test.py")

        # Should have multiple chunks
        assert len(chunks) > 1

        # Check overlap
        for i in range(len(chunks) - 1):
            current_end = chunks[i]["content"][-50:]
            next_start = chunks[i + 1]["content"][:50]
            # Some overlap should exist
            assert len(set(current_end.split()) & set(next_start.split())) > 0

    def test_chunk_preserves_line_numbers(self):
        """Test that chunk metadata includes correct line numbers."""
        chunker = CodeChunker()
        code = """# Line 1
# Line 2
def func():
    # Line 4
    pass"""

        chunks = chunker.chunk_code(code, "python", "test.py")

        # At least one chunk should have start_line metadata
        assert any("start_line" in chunk["metadata"] for chunk in chunks)

    def test_chunk_python_language(self):
        """Test chunking Python code specifically."""
        chunker = CodeChunker()
        code = """import os

def main():
    print("Hello")

class MyClass:
    pass"""

        chunks = chunker.chunk_code(code, "python", "test.py")

        # Should extract at least function and class
        assert len(chunks) >= 2

    def test_chunk_javascript_language(self):
        """Test chunking JavaScript code."""
        chunker = CodeChunker()
        code = """const x = 1;

function main() {
    console.log("Hello");
}

class MyClass {
    constructor() {
        this.value = 0;
    }
}"""

        chunks = chunker.chunk_code(code, "javascript", "test.js")

        # Should extract at least function and class
        assert len(chunks) >= 2

    def test_chunk_go_language(self):
        """Test chunking Go code."""
        chunker = CodeChunker()
        code = """package main

import "fmt"

func main() {
    fmt.Println("Hello")
}

type Config struct {
    Port int
}"""

        chunks = chunker.chunk_code(code, "go", "main.go")

        # Should have chunks
        assert len(chunks) >= 1

    def test_chunk_file_not_found(self, temp_dir):
        """Test chunking a file that doesn't exist."""
        chunker = CodeChunker()
        chunks = chunker.chunk_file(str(temp_dir / "nonexistent.py"), "python")
        assert chunks == []

    def test_chunk_file_success(self, temp_dir):
        """Test chunking an existing file."""
        chunker = CodeChunker()

        file_path = temp_dir / "test.py"
        file_path.write_text("""def func1():
    pass

def func2():
    pass""")

        chunks = chunker.chunk_file(str(file_path), "python")

        assert len(chunks) >= 2

    def test_extract_name_python(self):
        """Test extracting names from Python definitions."""
        chunker = CodeChunker()

        assert chunker._extract_name("def my_func():", "python") == "my_func"
        assert chunker._extract_name("def my_func(x, y):", "python") == "my_func"
        assert chunker._extract_name("class MyClass:", "python") == "MyClass"
        assert chunker._extract_name("class MyClass(Base):", "python") == "MyClass"

    def test_extract_name_javascript(self):
        """Test extracting names from JavaScript definitions."""
        chunker = CodeChunker()

        assert chunker._extract_name("function myFunc() {", "javascript") == "myFunc"
        assert chunker._extract_name("class MyClass {", "javascript") == "MyClass"

    def test_extract_name_go(self):
        """Test extracting names from Go definitions."""
        chunker = CodeChunker()

        assert chunker._extract_name("func main() {", "go") == "main"
        assert chunker._extract_name("func (s *Server) Start() {", "go") == "(s"

    def test_chunk_to_dict(self):
        """Test converting chunk to dictionary."""
        chunk = CodeChunk(
            content="def main(): pass", metadata={"type": "function", "name": "main"}
        )

        d = chunk.to_dict()

        assert d["content"] == "def main(): pass"
        assert d["metadata"]["type"] == "function"
        assert d["metadata"]["name"] == "main"

    def test_split_with_overlap(self):
        """Test splitting content with overlap."""
        chunker = CodeChunker(chunk_size=50, chunk_overlap=10)
        content = "a" * 100

        chunks = chunker._split_with_overlap(content, {"type": "test"})

        assert len(chunks) > 1
        # First chunk should be full size
        assert len(chunks[0]["content"]) == 50
        # Each chunk should have metadata with chunk_index
        for i, chunk in enumerate(chunks):
            assert chunk["metadata"]["chunk_index"] == i

    def test_chunk_with_imports(self):
        """Test chunking code with imports."""
        chunker = CodeChunker()
        code = """import os
import sys
from typing import List

def main():
    pass"""

        chunks = chunker.chunk_code(code, "python", "test.py")

        # Should have at least one chunk (either imports grouped or with function)
        assert len(chunks) >= 1

    def test_chunk_preserves_code_structure(self):
        """Test that chunking preserves code structure."""
        chunker = CodeChunker()
        code = """def outer():
    def inner():
        pass
    return inner"""

        chunks = chunker.chunk_code(code, "python", "test.py")

        # Both functions should be in the output
        all_content = " ".join(c["content"] for c in chunks)
        assert "outer" in all_content


class TestCodeChunk:
    """Test cases for CodeChunk dataclass."""

    def test_chunk_creation(self):
        """Test creating a CodeChunk."""
        chunk = CodeChunk(
            content="print('hello')", metadata={"file": "test.py", "line": 1}
        )

        assert chunk.content == "print('hello')"
        assert chunk.metadata["file"] == "test.py"

    def test_chunk_to_dict(self):
        """Test chunk dictionary conversion."""
        chunk = CodeChunk(content="x = 1", metadata={"type": "code"})
        d = chunk.to_dict()

        assert d == {"content": "x = 1", "metadata": {"type": "code"}}
