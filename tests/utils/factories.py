"""Object factories for creating test data."""

import hashlib
import uuid
from typing import Any, Dict, List, Optional
from pathlib import Path


class FileInfoFactory:
    """Factory for creating file info objects."""

    @staticmethod
    def create(
        relative_path: str = "src/main.py",
        language: str = "Python",
        content: str = "def main():\n    pass",
        absolute_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a file info dictionary."""
        content_bytes = content.encode("utf-8")
        content_hash = hashlib.sha256(content_bytes).hexdigest()

        return {
            "relative_path": relative_path,
            "absolute_path": absolute_path or f"/test/{relative_path}",
            "language": language,
            "size_bytes": len(content_bytes),
            "line_count": len(content.split("\n")),
            "content_hash": content_hash,
            "extension": Path(relative_path).suffix.lower() or ".py",
        }

    @staticmethod
    def create_batch(
        count: int,
        base_path: str = "src",
        extension: str = ".py",
        language: str = "Python",
    ) -> List[Dict[str, Any]]:
        """Create multiple file info objects."""
        files = []
        for i in range(count):
            filename = f"file_{i}{extension}"
            relative_path = f"{base_path}/{filename}"
            content = f"def function_{i}():\n    return {i}\n"
            files.append(FileInfoFactory.create(relative_path, language, content))
        return files


class ChunkFactory:
    """Factory for creating code chunks."""

    @staticmethod
    def create(
        content: str = "def main():\n    pass",
        chunk_type: str = "definition",
        name: str = "main",
        file_path: str = "src/main.py",
        language: str = "Python",
        start_line: int = 1,
        embedding: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Create a chunk dictionary."""
        chunk = {
            "content": content,
            "metadata": {
                "type": chunk_type,
                "name": name,
                "file_path": file_path,
                "language": language,
                "start_line": start_line,
            },
        }
        if embedding:
            chunk["embedding"] = embedding
        return chunk

    @staticmethod
    def create_batch(
        count: int,
        base_content: str = "function",
        file_path: str = "src/main.py",
        with_embeddings: bool = False,
        embedding_dim: int = 1024,
    ) -> List[Dict[str, Any]]:
        """Create multiple chunks."""
        chunks = []
        for i in range(count):
            content = f"def {base_content}_{i}():\n    return {i}\n"
            embedding = [0.1] * embedding_dim if with_embeddings else None
            chunks.append(
                ChunkFactory.create(
                    content=content,
                    name=f"{base_content}_{i}",
                    file_path=file_path,
                    start_line=i * 5 + 1,
                    embedding=embedding,
                )
            )
        return chunks


class ASTNodeFactory:
    """Factory for creating AST node metadata."""

    @staticmethod
    def create_function(
        name: str = "main",
        parameters: Optional[List[str]] = None,
        start_line: int = 1,
        end_line: int = 5,
    ) -> Dict[str, Any]:
        """Create function metadata."""
        return {
            "name": name,
            "parameters": parameters or [],
            "start_line": start_line,
            "end_line": end_line,
        }

    @staticmethod
    def create_class(
        name: str = "MyClass",
        start_line: int = 1,
        end_line: int = 20,
    ) -> Dict[str, Any]:
        """Create class metadata."""
        return {
            "name": name,
            "start_line": start_line,
            "end_line": end_line,
        }

    @staticmethod
    def create_import(
        name: str = "os",
        module: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create import metadata."""
        return {
            "name": name,
            "module": module or name,
        }


class GraphEdgeFactory:
    """Factory for creating graph edges."""

    @staticmethod
    def create(
        source: str = "src/main.py",
        target: str = "src/utils.py",
        edge_type: str = "import",
        metadata: Optional[Dict] = None,
    ) -> tuple:
        """Create a graph edge tuple."""
        edge_metadata = metadata or {}
        edge_metadata["type"] = edge_type
        return (source, target, edge_metadata)

    @staticmethod
    def create_import_chain(
        files: List[str],
    ) -> List[tuple]:
        """Create a chain of import edges."""
        edges = []
        for i in range(len(files) - 1):
            edges.append(GraphEdgeFactory.create(files[i], files[i + 1], "import"))
        return edges


class SessionFactory:
    """Factory for creating session data."""

    @staticmethod
    def create(
        session_id: Optional[str] = None,
        source_path: str = "/test/path",
        session_type: str = "local",
        status: str = "active",
    ) -> Dict[str, Any]:
        """Create session data dictionary."""
        return {
            "session_id": session_id or f"test-session-{uuid.uuid4().hex[:8]}",
            "source_path": source_path,
            "session_type": session_type,
            "status": status,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }


class CodeSmellFactory:
    """Factory for creating code smell objects."""

    @staticmethod
    def create(
        smell_type: str = "long_function",
        file_path: str = "src/main.py",
        line_start: int = 1,
        line_end: int = 60,
        severity: str = "high",
        score: float = 7.5,
        description: str = "Function is too long",
        suggestion: str = "Extract smaller functions",
        entity_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a code smell dictionary."""
        return {
            "smell_type": smell_type,
            "file_path": file_path,
            "line_start": line_start,
            "line_end": line_end,
            "severity": severity,
            "score": score,
            "description": description,
            "suggestion": suggestion,
            "entity_name": entity_name or "test_function",
        }


class MockLLMFactory:
    """Factory for creating mock LLM responses."""

    @staticmethod
    def create_embedding_response(
        dimension: int = 1024,
        value: float = 0.1,
    ) -> List[float]:
        """Create a mock embedding vector."""
        return [value] * dimension

    @staticmethod
    def create_qa_response(
        query: str = "What does this code do?",
        answer: str = "This code processes data.",
        sources: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Create a mock Q&A response."""
        return {
            "query": query,
            "answer": answer,
            "intent": "explanation",
            "sources": sources
            or [
                {
                    "file_path": "src/main.py",
                    "start_line": 1,
                    "end_line": 10,
                    "entity_name": "process_data",
                }
            ],
            "confidence": 0.85,
        }


# Convenience functions for common test data
def create_sample_repo_structure(base_path: Path, languages: List[str] = None):
    """Create a sample repository structure with various files."""
    languages = languages or ["python"]

    (base_path / "src").mkdir(parents=True, exist_ok=True)
    (base_path / "tests").mkdir(parents=True, exist_ok=True)

    if "python" in languages:
        (base_path / "src" / "main.py").write_text("def main():\n    pass\n")
        (base_path / "src" / "utils.py").write_text("def helper():\n    return 42\n")
        (base_path / "tests" / "test_main.py").write_text(
            "def test_main():\n    pass\n"
        )
        (base_path / "requirements.txt").write_text("pytest\n")

    if "javascript" in languages:
        (base_path / "src" / "index.js").write_text("const x = 1;\n")
        (base_path / "package.json").write_text('{"name": "test"}\n')

    (base_path / "README.md").write_text("# Test Project\n")
    (base_path / ".gitignore").write_text("__pycache__/\n*.pyc\n")


def create_monorepo_structure(base_path: Path):
    """Create a monorepo structure with multiple packages."""
    packages = ["frontend", "backend", "shared"]

    for pkg in packages:
        pkg_path = base_path / "packages" / pkg
        pkg_path.mkdir(parents=True, exist_ok=True)
        (pkg_path / "package.json").write_text(f'{{"name": "@{pkg}"}}\n')
        (pkg_path / "src" / "index.js").write_text(f"// {pkg} module\n")
        (pkg_path / "src" / "index.js").parent.mkdir(parents=True, exist_ok=True)

    (base_path / "package.json").write_text('{"workspaces": ["packages/*"]}\n')
    (base_path / "README.md").write_text("# Monorepo\n")
