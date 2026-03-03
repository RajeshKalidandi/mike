"""Pytest configuration and shared fixtures for Mike tests."""

import os
import shutil
import sqlite3
import tempfile
import uuid
from pathlib import Path
from typing import Dict, Generator, List, Any, Optional
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# =============================================================================
# Session-scoped fixtures
# =============================================================================


@pytest.fixture(scope="session")
def test_dir() -> Path:
    """Return the tests directory path."""
    return Path(__file__).parent


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def sample_repos_dir(test_dir: Path) -> Path:
    """Return the sample repositories directory."""
    return test_dir / "fixtures" / "sample_repos"


# =============================================================================
# Database fixtures
# =============================================================================


@pytest.fixture
def temp_db_path() -> Generator[str, None, None]:
    """Create a temporary database file."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def db_connection(temp_db_path: str) -> Generator[sqlite3.Connection, None, None]:
    """Create a database connection for testing."""
    conn = sqlite3.connect(temp_db_path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def mock_database() -> MagicMock:
    """Create a mock database instance."""
    db = MagicMock()
    db.init = MagicMock(return_value=None)
    db.create_session = MagicMock(return_value="test-session-123")
    db.get_session = MagicMock(return_value=None)
    db.get_files_for_session = MagicMock(return_value=[])
    db.insert_file = MagicMock(return_value=1)
    return db


# =============================================================================
# Session fixtures
# =============================================================================


@pytest.fixture
def test_session_id() -> str:
    """Generate a test session ID."""
    return f"test-session-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def mock_session_data(test_session_id: str) -> Dict[str, Any]:
    """Create mock session data."""
    return {
        "session_id": test_session_id,
        "source_path": "/test/path",
        "session_type": "local",
        "status": "active",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    }


# =============================================================================
# Temporary directory fixtures
# =============================================================================


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    path = Path(tempfile.mkdtemp(prefix="mike_test_"))
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def temp_repo(temp_dir: Path) -> Generator[Path, None, None]:
    """Create a temporary repository structure."""
    repo_path = temp_dir / "repo"
    repo_path.mkdir()

    # Create some test files
    (repo_path / "src").mkdir()
    (repo_path / "tests").mkdir()
    (repo_path / "README.md").write_text("# Test Repo\n")
    (repo_path / ".gitignore").write_text("*.pyc\n__pycache__/\n")

    yield repo_path


@pytest.fixture
def temp_vector_dir(temp_dir: Path) -> Path:
    """Create a temporary directory for vector store."""
    vector_dir = temp_dir / "vector_store"
    vector_dir.mkdir()
    return vector_dir


# =============================================================================
# Mock LLM fixtures
# =============================================================================


@pytest.fixture
def mock_embedding_response() -> List[float]:
    """Create a mock embedding response."""
    return [0.1] * 1024  # mxbai-embed-large dimension


@pytest.fixture
def mock_embedding_service(mock_embedding_response: List[float]) -> MagicMock:
    """Create a mock embedding service."""
    service = MagicMock()
    service.embed.return_value = mock_embedding_response
    service.embed_batch.return_value = [mock_embedding_response]
    service.embed_chunks.return_value = [
        {"content": "test", "metadata": {}, "embedding": mock_embedding_response}
    ]
    service.check_model_available.return_value = True
    service.dimension = 1024
    service.model = "mxbai-embed-large"
    return service


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Create a mock LLM client."""
    client = MagicMock()
    client.generate.return_value = {"text": "Test response from LLM"}
    client.is_available.return_value = True
    return client


@pytest.fixture
def mock_ollama_client() -> MagicMock:
    """Create a mock Ollama client."""
    client = MagicMock()

    # Mock embeddings response
    client.embeddings.return_value = {"embedding": [0.1] * 1024}

    # Mock list models response
    client.list.return_value = {
        "models": [
            {"name": "mxbai-embed-large:latest"},
            {"name": "nomic-embed-text:latest"},
        ]
    }

    return client


# =============================================================================
# Sample code fixtures
# =============================================================================


@pytest.fixture
def sample_python_code() -> str:
    """Return sample Python code for testing."""
    return '''
"""Sample Python module for testing."""

import os
import sys
from typing import List, Optional
from pathlib import Path


class DataProcessor:
    """Process data files."""
    
    def __init__(self, input_dir: str):
        self.input_dir = Path(input_dir)
        self.files: List[Path] = []
    
    def load_files(self) -> List[Path]:
        """Load all files from input directory."""
        self.files = list(self.input_dir.glob("*.txt"))
        return self.files
    
    def process(self, file_path: Path) -> str:
        """Process a single file."""
        with open(file_path, 'r') as f:
            content = f.read()
        return content.upper()


def main():
    """Main entry point."""
    processor = DataProcessor("./data")
    files = processor.load_files()
    for f in files:
        result = processor.process(f)
        print(result)


if __name__ == "__main__":
    main()
'''


@pytest.fixture
def sample_javascript_code() -> str:
    """Return sample JavaScript code for testing."""
    return """
/**
 * Sample JavaScript module for testing.
 */

const fs = require('fs');
const path = require('path');

class UserService {
    constructor(database) {
        this.db = database;
        this.cache = new Map();
    }

    async getUser(id) {
        if (this.cache.has(id)) {
            return this.cache.get(id);
        }
        const user = await this.db.query('SELECT * FROM users WHERE id = ?', [id]);
        this.cache.set(id, user);
        return user;
    }

    async createUser(userData) {
        const result = await this.db.insert('users', userData);
        return result;
    }
}

const processUsers = async (userIds) => {
    const service = new UserService(global.db);
    const users = [];
    for (const id of userIds) {
        const user = await service.getUser(id);
        users.push(user);
    }
    return users;
};

module.exports = { UserService, processUsers };
"""


@pytest.fixture
def sample_go_code() -> str:
    """Return sample Go code for testing."""
    return """
package main

import (
    "fmt"
    "net/http"
    "time"
)

type Server struct {
    port    int
    handler http.Handler
}

func NewServer(port int) *Server {
    return &Server{
        port:    port,
        handler: nil,
    }
}

func (s *Server) Start() error {
    addr := fmt.Sprintf(":%d", s.port)
    return http.ListenAndServe(addr, s.handler)
}

func main() {
    server := NewServer(8080)
    if err := server.Start(); err != nil {
        panic(err)
    }
}
"""


@pytest.fixture
def sample_java_code() -> str:
    """Return sample Java code for testing."""
    return """
package com.example;

import java.util.List;
import java.util.ArrayList;

public class OrderService {
    private final Database db;
    private final Logger logger;
    
    public OrderService(Database db, Logger logger) {
        this.db = db;
        this.logger = logger;
    }
    
    public Order getOrder(String id) {
        logger.info("Fetching order: " + id);
        return db.findById(Order.class, id);
    }
    
    public List<Order> getAllOrders() {
        return db.findAll(Order.class);
    }
    
    public void saveOrder(Order order) {
        db.save(order);
        logger.info("Order saved: " + order.getId());
    }
}
"""


@pytest.fixture
def sample_code_with_issues() -> str:
    """Return Python code with known issues for testing refactor agent."""
    return '''
def very_long_function_with_many_lines():
    """This function is intentionally long."""
    x = 1
    x = 2
    x = 3
    x = 4
    x = 5
    x = 6
    x = 7
    x = 8
    x = 9
    x = 10
    x = 11
    x = 12
    x = 13
    x = 14
    x = 15
    x = 16
    x = 17
    x = 18
    x = 19
    x = 20
    x = 21
    x = 22
    x = 23
    x = 24
    x = 25
    x = 26
    x = 27
    x = 28
    x = 29
    x = 30
    x = 31
    x = 32
    x = 33
    x = 34
    x = 35
    x = 36
    x = 37
    x = 38
    x = 39
    x = 40
    x = 41
    x = 42
    x = 43
    x = 44
    x = 45
    x = 46
    x = 47
    x = 48
    x = 49
    x = 50
    x = 51
    x = 52
    x = 53
    x = 54
    x = 55
    x = 56
    return x


def unused_function():
    """This function is never called."""
    return "dead code"


def deep_nesting_function(n):
    if n > 0:
        if n > 1:
            if n > 2:
                if n > 3:
                    if n > 4:
                        return "deep"
    return "not deep"


class GodClass:
    """A class with way too many methods."""
    
    def method1(self): pass
    def method2(self): pass
    def method3(self): pass
    def method4(self): pass
    def method5(self): pass
    def method6(self): pass
    def method7(self): pass
    def method8(self): pass
    def method9(self): pass
    def method10(self): pass
    def method11(self): pass
    def method12(self): pass
    def method13(self): pass
    def method14(self): pass
    def method15(self): pass
    def method16(self): pass
    def method17(self): pass
    def method18(self): pass
    def method19(self): pass
    def method20(self): pass
    def method21(self): pass
    def method22(self): pass
    def method23(self): pass
    def method24(self): pass
    def method25(self): pass


def too_many_params(a, b, c, d, e, f, g):
    """Function with too many parameters."""
    return a + b + c + d + e + f + g
'''


# =============================================================================
# Sample file info fixtures
# =============================================================================


@pytest.fixture
def sample_file_info() -> Dict[str, Any]:
    """Return sample file info dictionary."""
    return {
        "relative_path": "src/main.py",
        "absolute_path": "/test/src/main.py",
        "language": "Python",
        "size_bytes": 1024,
        "line_count": 50,
        "content_hash": "abc123def456",
        "extension": ".py",
    }


@pytest.fixture
def sample_files_list() -> List[Dict[str, Any]]:
    """Return list of sample file info dictionaries."""
    return [
        {
            "relative_path": "src/main.py",
            "absolute_path": "/test/src/main.py",
            "language": "Python",
            "size_bytes": 1024,
            "line_count": 50,
            "content_hash": "abc123",
            "extension": ".py",
        },
        {
            "relative_path": "src/utils.py",
            "absolute_path": "/test/src/utils.py",
            "language": "Python",
            "size_bytes": 512,
            "line_count": 25,
            "content_hash": "def456",
            "extension": ".py",
        },
        {
            "relative_path": "tests/test_main.py",
            "absolute_path": "/test/tests/test_main.py",
            "language": "Python",
            "size_bytes": 256,
            "line_count": 15,
            "content_hash": "ghi789",
            "extension": ".py",
        },
        {
            "relative_path": "README.md",
            "absolute_path": "/test/README.md",
            "language": "Markdown",
            "size_bytes": 128,
            "line_count": 10,
            "content_hash": "jkl012",
            "extension": ".md",
        },
    ]


# =============================================================================
# Chunk fixtures
# =============================================================================


@pytest.fixture
def sample_chunks() -> List[Dict[str, Any]]:
    """Return sample code chunks."""
    return [
        {
            "content": "def main():\n    pass",
            "metadata": {
                "type": "definition",
                "name": "main",
                "start_line": 1,
                "file_path": "src/main.py",
                "language": "Python",
            },
        },
        {
            "content": "class MyClass:\n    def method(self):\n        pass",
            "metadata": {
                "type": "definition",
                "name": "MyClass",
                "start_line": 10,
                "file_path": "src/main.py",
                "language": "Python",
            },
        },
    ]


@pytest.fixture
def sample_chunks_with_embeddings(
    sample_chunks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Return sample chunks with embeddings."""
    embedding = [0.1] * 1024
    return [{**chunk, "embedding": embedding} for chunk in sample_chunks]


# =============================================================================
# Graph fixtures
# =============================================================================


@pytest.fixture
def sample_graph_edges() -> List[tuple]:
    """Return sample graph edges."""
    return [
        ("src/main.py", "src/utils.py", {"type": "import"}),
        ("src/main.py", "src/models.py", {"type": "import"}),
        ("tests/test_main.py", "src/main.py", {"type": "import"}),
        ("src/services.py", "src/models.py", {"type": "import"}),
    ]


@pytest.fixture
def mock_dependency_graph() -> MagicMock:
    """Create a mock dependency graph."""
    graph = MagicMock()
    graph.number_of_nodes.return_value = 10
    graph.number_of_edges.return_value = 15
    graph.nodes.return_value = ["a.py", "b.py", "c.py"]
    graph.edges.return_value = [("a.py", "b.py"), ("b.py", "c.py")]
    graph.successors.return_value = ["b.py", "c.py"]
    graph.predecessors.return_value = ["a.py"]
    return graph


# =============================================================================
# Configuration fixtures
# =============================================================================


@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Return test configuration."""
    return {
        "long_function_lines": 50,
        "god_class_methods": 20,
        "deep_nesting_levels": 4,
        "max_cyclomatic_complexity": 10,
        "duplicate_min_lines": 5,
        "duplicate_similarity_threshold": 0.8,
    }


@pytest.fixture(autouse=True)
def clean_env():
    """Clean up environment variables after each test."""
    original_env = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(original_env)


# =============================================================================
# Helper functions
# =============================================================================


def create_test_file(directory: Path, relative_path: str, content: str) -> Path:
    """Create a test file with the given content."""
    file_path = directory / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    return file_path


def create_sample_repo(base_path: Path, language: str = "python") -> Path:
    """Create a sample repository structure."""
    repo_path = base_path / f"sample_{language}_repo"
    repo_path.mkdir()

    if language == "python":
        create_test_file(repo_path, "src/__init__.py", "")
        create_test_file(repo_path, "src/main.py", "def main():\n    pass")
        create_test_file(repo_path, "src/utils.py", "def helper():\n    return 42")
        create_test_file(repo_path, "tests/test_main.py", "def test_main():\n    pass")
        create_test_file(repo_path, "requirements.txt", "pytest\n")
        create_test_file(repo_path, "README.md", "# Sample Repo\n")
    elif language == "javascript":
        create_test_file(repo_path, "src/index.js", "const x = 1;")
        create_test_file(repo_path, "package.json", '{"name": "test"}')

    return repo_path


# Make helpers available to tests
pytest.create_test_file = create_test_file
pytest.create_sample_repo = create_sample_repo
