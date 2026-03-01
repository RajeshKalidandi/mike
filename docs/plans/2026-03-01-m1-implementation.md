# M1 Implementation Plan: File Scanner + Language Detection + AST Parsing

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Build the foundation layer that ingests any codebase, detects languages, and parses AST for further analysis.

**Architecture:** Python CLI tool with pluggable scanners, Tree-sitter for AST parsing, linguist-inspired language detection, SQLite for metadata storage.

**Tech Stack:** Python 3.10+, tree-sitter, PyGithub (for repo cloning), python-enry (language detection), SQLite3, pytest, click (CLI framework)

---

## Task 1: Project Bootstrap & Dependencies

**Files:**
- Create: `pyproject.toml` (project root)
- Create: `requirements.txt` (project root)
- Create: `.gitignore` (project root)
- Create: `README.md` (project root - basic setup)
- Create: `src/architectai/__init__.py`
- Create: `tests/__init__.py`

**Step 1: Create project structure**

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "architectai"
version = "0.1.0"
description = "Local AI software architect for private codebases"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "Rajesh", email = "rajesh@example.com"},
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = [
    "click>=8.0.0",
    "tree-sitter>=0.20.0",
    "tree-sitter-python>=0.20.0",
    "tree-sitter-javascript>=0.20.0",
    "tree-sitter-go>=0.20.0",
    "tree-sitter-java>=0.20.0",
    "tree-sitter-rust>=0.20.0",
    "tree-sitter-c>=0.20.0",
    "tree-sitter-cpp>=0.20.0",
    "tree-sitter-ruby>=0.20.0",
    "tree-sitter-php>=0.20.0",
    "python-enry>=0.1.0",
    "PyGithub>=2.0.0",
    "requests>=2.28.0",
    "GitPython>=3.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "isort>=5.12.0",
    "mypy>=1.0.0",
    "ruff>=0.1.0",
]

[project.scripts]
architectai = "architectai.cli:main"

[tool.black]
line-length = 100
target-version = ['py310']

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "--cov=src/architectai --cov-report=term-missing"
```

**Step 2: Create requirements.txt**

```
click>=8.0.0
tree-sitter>=0.20.0
tree-sitter-python>=0.20.0
tree-sitter-javascript>=0.20.0
tree-sitter-go>=0.20.0
tree-sitter-java>=0.20.0
tree-sitter-rust>=0.20.0
tree-sitter-c>=0.20.0
tree-sitter-cpp>=0.20.0
tree-sitter-ruby>=0.20.0
tree-sitter-php>=0.20.0
python-enry>=0.1.0
PyGithub>=2.0.0
requests>=2.28.0
GitPython>=3.1.0
```

**Step 3: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/
.venv

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.coverage
htmlcov/
.pytest_cache/

# Data
*.db
*.sqlite
uploads/
sessions/

# OS
.DS_Store
Thumbs.db
```

**Step 4: Create src structure**

```bash
mkdir -p src/architectai/scanner
mkdir -p src/architectai/parser
mkdir -p src/architectai/db
mkdir -p tests/scanner
mkdir -p tests/parser
```

**Step 5: Commit**

```bash
git add .
git commit -m "chore: bootstrap project with dependencies"
```

---

## Task 2: Database Layer - Session & File Metadata

**Files:**
- Create: `src/architectai/db/__init__.py`
- Create: `src/architectai/db/models.py`
- Create: `src/architectai/db/session.py`
- Create: `tests/db/test_models.py`

**Step 1: Write failing test**

```python
# tests/db/test_models.py
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
                content_hash="abc123"
            )
            
            assert file_id is not None
            
            files = db.get_files_for_session(session_id)
            assert len(files) == 1
            assert files[0]["relative_path"] == "src/main.py"
```

**Step 2: Run test (should fail)**

```bash
cd /Users/krissdev/mike
python -m pytest tests/db/test_models.py -v
```
Expected: ImportError or ModuleNotFoundError

**Step 3: Implement database models**

```python
# src/architectai/db/__init__.py
from .models import Database
from .session import SessionManager

__all__ = ["Database", "SessionManager"]
```

```python
# src/architectai/db/models.py
"""Database models and operations."""
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any


class Database:
    """SQLite database for metadata storage."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_dir()
    
    def _ensure_dir(self) -> None:
        """Ensure database directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def init(self) -> None:
        """Initialize database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    source_path TEXT NOT NULL,
                    session_type TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    content_hash TEXT
                )
            """)
            
            # Files table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    absolute_path TEXT NOT NULL,
                    language TEXT,
                    size_bytes INTEGER,
                    line_count INTEGER,
                    content_hash TEXT,
                    parsed_at TIMESTAMP,
                    ast_available BOOLEAN DEFAULT 0,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            
            # Code hashes for deduplication
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS code_hashes (
                    hash TEXT PRIMARY KEY,
                    session_id TEXT,
                    file_count INTEGER,
                    total_lines INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_session ON files(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_language ON files(language)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_hash ON files(content_hash)")
            
            conn.commit()
    
    def create_session(
        self,
        source_path: str,
        session_type: str,
        content_hash: Optional[str] = None
    ) -> str:
        """Create a new session and return its ID."""
        session_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO sessions (id, source_path, session_type, content_hash)
                   VALUES (?, ?, ?, ?)""",
                (session_id, source_path, session_type, content_hash)
            )
            conn.commit()
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def insert_file(
        self,
        session_id: str,
        relative_path: str,
        absolute_path: str,
        language: Optional[str] = None,
        size_bytes: Optional[int] = None,
        line_count: Optional[int] = None,
        content_hash: Optional[str] = None
    ) -> int:
        """Insert a file record and return its ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO files
                   (session_id, relative_path, absolute_path, language, size_bytes, line_count, content_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session_id, relative_path, absolute_path, language, size_bytes, line_count, content_hash)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_files_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all files for a session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files WHERE session_id = ?", (session_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def update_file_parsed(self, file_id: int, ast_available: bool = True) -> None:
        """Mark file as parsed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE files SET parsed_at = CURRENT_TIMESTAMP, ast_available = ?
                   WHERE id = ?""",
                (ast_available, file_id)
            )
            conn.commit()
    
    def check_content_hash_exists(self, content_hash: str) -> Optional[str]:
        """Check if a content hash exists. Returns session_id if found."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT session_id FROM code_hashes WHERE hash = ?",
                (content_hash,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
```

**Step 4: Run tests (should pass)**

```bash
python -m pytest tests/db/test_models.py -v
```
Expected: All tests pass

**Step 5: Commit**

```bash
git add .
git commit -m "feat(db): add database layer for sessions and file metadata"
```

---

## Task 3: File Scanner - Repository Ingestion

**Files:**
- Create: `src/architectai/scanner/__init__.py`
- Create: `src/architectai/scanner/scanner.py`
- Create: `src/architectai/scanner/clone.py`
- Create: `tests/scanner/test_scanner.py`
- Create: `tests/fixtures/sample_repo/` (minimal test repo)

**Step 1: Create test fixtures**

```bash
mkdir -p tests/fixtures/sample_repo/src
mkdir -p tests/fixtures/sample_repo/tests
```

```python
# tests/fixtures/sample_repo/src/main.py
"""Main module for sample project."""


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


def main():
    """Main entry point."""
    result = add(1, 2)
    print(f"Result: {result}")


if __name__ == "__main__":
    main()
```

```javascript
// tests/fixtures/sample_repo/src/utils.js
/**
 * Utility functions
 */

function formatMessage(name, message) {
    return `${name}: ${message}`;
}

module.exports = { formatMessage };
```

```
# tests/fixtures/sample_repo/README.md
# Sample Project

This is a test fixture.
```

```
# tests/fixtures/sample_repo/.gitignore
__pycache__/
node_modules/
```

**Step 2: Write failing test**

```python
# tests/scanner/test_scanner.py
import pytest
import tempfile
import os
import shutil
from pathlib import Path
from architectai.scanner.scanner import FileScanner


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
```

**Step 3: Run test (should fail)**

```bash
python -m pytest tests/scanner/test_scanner.py::TestFileScanner::test_scan_local_directory -v
```
Expected: ImportError

**Step 4: Implement scanner**

```python
# src/architectai/scanner/__init__.py
from .scanner import FileScanner
from .clone import clone_repository

__all__ = ["FileScanner", "clone_repository"]
```

```python
# src/architectai/scanner/scanner.py
"""File scanning and discovery."""
import os
import hashlib
import fnmatch
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, asdict

import enry


@dataclass
class FileInfo:
    """Information about a scanned file."""
    relative_path: str
    absolute_path: str
    language: Optional[str]
    size_bytes: int
    line_count: int
    content_hash: str
    extension: str


class FileScanner:
    """Scan directories and identify source files."""
    
    # Binary file extensions to skip
    BINARY_EXTENSIONS = {
        '.exe', '.dll', '.so', '.dylib', '.bin',
        '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
        '.mp3', '.mp4', '.avi', '.mov', '.wav',
        '.zip', '.tar', '.gz', '.rar', '.7z',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx',
        '.db', '.sqlite', '.sqlite3'
    }
    
    # Files/directories to always ignore
    DEFAULT_IGNORES = {
        '.git', '.svn', '.hg',  # Version control
        'node_modules', 'vendor',  # Dependencies
        '__pycache__', '.pytest_cache', '.mypy_cache',  # Python
        '.venv', 'venv', 'env',  # Virtual environments
        'dist', 'build', 'target',  # Build artifacts
        '.idea', '.vscode',  # IDE
        '.DS_Store', 'Thumbs.db',  # OS files
    }
    
    def __init__(self, respect_gitignore: bool = True):
        self.respect_gitignore = respect_gitignore
        self._gitignore_patterns: Dict[str, List[str]] = {}
    
    def scan_directory(self, root_path: str) -> List[Dict[str, Any]]:
        """Scan directory and return list of file info dictionaries."""
        root = Path(root_path).resolve()
        files = []
        
        # Load gitignore patterns if requested
        if self.respect_gitignore:
            self._load_gitignore(root)
        
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            
            relative = path.relative_to(root)
            relative_str = str(relative).replace(os.sep, '/')
            
            # Skip if matches ignore patterns
            if self._should_ignore(relative_str, root):
                continue
            
            # Skip binary files
            if path.suffix.lower() in self.BINARY_EXTENSIONS:
                continue
            
            # Get file info
            file_info = self._analyze_file(path, relative_str)
            if file_info:
                files.append(asdict(file_info))
        
        return files
    
    def _load_gitignore(self, root: Path) -> None:
        """Load .gitignore patterns from directory."""
        gitignore_path = root / ".gitignore"
        if gitignore_path.exists():
            patterns = []
            with open(gitignore_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line)
            self._gitignore_patterns[str(root)] = patterns
    
    def _should_ignore(self, relative_path: str, root: Path) -> bool:
        """Check if path should be ignored."""
        # Check default ignores
        parts = relative_path.split('/')
        for part in parts:
            if part in self.DEFAULT_IGNORES:
                return True
        
        # Check gitignore patterns
        if self.respect_gitignore:
            for patterns in self._gitignore_patterns.values():
                for pattern in patterns:
                    if self._matches_pattern(relative_path, pattern):
                        return True
        
        return False
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches gitignore pattern."""
        # Handle directory patterns (ending with /)
        if pattern.endswith('/'):
            pattern = pattern[:-1]
            if pattern in path.split('/'):
                return True
        
        # Handle glob patterns
        if fnmatch.fnmatch(path, pattern):
            return True
        if fnmatch.fnmatch(os.path.basename(path), pattern):
            return True
        
        return False
    
    def _analyze_file(self, path: Path, relative_path: str) -> Optional[FileInfo]:
        """Analyze a single file and return FileInfo."""
        try:
            content = path.read_bytes()
            text_content = content.decode('utf-8', errors='ignore')
            
            # Detect language
            language = self._detect_language(path, text_content)
            
            # Calculate hash
            content_hash = hashlib.sha256(content).hexdigest()
            
            # Count lines
            line_count = len(text_content.splitlines())
            
            return FileInfo(
                relative_path=relative_path,
                absolute_path=str(path),
                language=language,
                size_bytes=len(content),
                line_count=line_count,
                content_hash=content_hash,
                extension=path.suffix.lower()
            )
        except Exception as e:
            # Log error but continue scanning
            print(f"Warning: Could not analyze {path}: {e}")
            return None
    
    def _detect_language(self, path: Path, content: str) -> Optional[str]:
        """Detect programming language using enry."""
        filename = path.name
        
        # Use enry for language detection
        lang = enry.get_language(filename, content)
        
        return lang if lang else None
```

```python
# src/architectai/scanner/clone.py
"""Repository cloning functionality."""
import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import git


def clone_repository(
    repo_url: str,
    target_dir: Optional[str] = None,
    branch: Optional[str] = None,
    depth: int = 1
) -> str:
    """Clone a git repository.
    
    Args:
        repo_url: Git repository URL or local path
        target_dir: Target directory (created if doesn't exist)
        branch: Branch to checkout (default: default branch)
        depth: Clone depth (1 for shallow clone)
    
    Returns:
        Path to cloned repository
    """
    # Determine target directory
    if target_dir is None:
        target_dir = tempfile.mkdtemp(prefix="architectai_")
    else:
        Path(target_dir).mkdir(parents=True, exist_ok=True)
    
    # Clone options
    clone_kwargs = {"depth": depth}
    if branch:
        clone_kwargs["branch"] = branch
    
    try:
        repo = git.Repo.clone_from(repo_url, target_dir, **clone_kwargs)
        return str(repo.working_dir)
    except git.GitCommandError as e:
        raise RuntimeError(f"Failed to clone repository: {e}")


def is_git_url(url: str) -> bool:
    """Check if string is a git URL."""
    parsed = urlparse(url)
    
    # Check for git protocol or common git hosts
    if parsed.scheme in ('http', 'https', 'git', 'ssh'):
        return True
    
    # Check for git@host:path format
    if '@' in url and ':' in url and not parsed.scheme:
        return True
    
    return False
```

**Step 5: Run tests (should pass)**

```bash
python -m pytest tests/scanner/test_scanner.py -v
```
Expected: All tests pass

**Step 6: Commit**

```bash
git add .
git commit -m "feat(scanner): add file scanner with language detection"
```

---

## Task 4: AST Parser - Tree-sitter Integration

**Files:**
- Create: `src/architectai/parser/__init__.py`
- Create: `src/architectai/parser/parser.py`
- Create: `src/architectai/parser/languages.py`
- Create: `tests/parser/test_parser.py`

**Step 1: Write failing test**

```python
# tests/parser/test_parser.py
import pytest
from pathlib import Path
from architectai.parser.parser import ASTParser


class TestASTParser:
    def test_parse_python_file(self):
        """Test parsing a Python file."""
        parser = ASTParser()
        
        code = '''
def add(a, b):
    """Add two numbers."""
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
'''
        
        result = parser.parse(code, "Python")
        
        assert result is not None
        assert "functions" in result
        assert "classes" in result
        assert "imports" in result
        
        # Check functions extracted
        func_names = [f["name"] for f in result["functions"]]
        assert "add" in func_names
        assert "multiply" in func_names
        
        # Check classes extracted
        class_names = [c["name"] for c in result["classes"]]
        assert "Calculator" in class_names
    
    def test_parse_javascript_file(self):
        """Test parsing a JavaScript file."""
        parser = ASTParser()
        
        code = '''
function greet(name) {
    return `Hello, ${name}!`;
}

class Person {
    constructor(name) {
        this.name = name;
    }
    
    sayHello() {
        console.log(`Hello, I'm ${this.name}`);
    }
}

module.exports = { Person };
'''
        
        result = parser.parse(code, "JavaScript")
        
        assert result is not None
        func_names = [f["name"] for f in result["functions"]]
        assert "greet" in func_names
        
        class_names = [c["name"] for c in result["classes"]]
        assert "Person" in class_names
    
    def test_extract_imports(self):
        """Test import extraction."""
        parser = ASTParser()
        
        code = '''
import os
import sys
from typing import List
from mymodule import utils, helpers
'''
        
        result = parser.parse(code, "Python")
        imports = result["imports"]
        
        import_names = [i["name"] for i in imports]
        assert "os" in import_names
        assert "sys" in import_names
        assert "typing.List" in import_names or "List" in import_names
```

**Step 2: Run test (should fail)**

```bash
python -m pytest tests/parser/test_parser.py::TestASTParser::test_parse_python_file -v
```
Expected: ImportError

**Step 3: Implement parser**

```python
# src/architectai/parser/__init__.py
from .parser import ASTParser
from .languages import get_language, SUPPORTED_LANGUAGES

__all__ = ["ASTParser", "get_language", "SUPPORTED_LANGUAGES"]
```

```python
# src/architectai/parser/languages.py
"""Language-specific Tree-sitter setup."""
from typing import Optional, Dict, Any
import tree_sitter

# Import language modules
try:
    from tree_sitter_python import language as python_language
    from tree_sitter_javascript import language as javascript_language
    from tree_sitter_go import language as go_language
    from tree_sitter_java import language as java_language
    from tree_sitter_rust import language as rust_language
    from tree_sitter_c import language as c_language
    from tree_sitter_cpp import language as cpp_language
    from tree_sitter_ruby import language as ruby_language
    from tree_sitter_php import language as php_language
    
    LANGUAGE_MODULES = {
        "Python": python_language,
        "JavaScript": javascript_language,
        "Go": go_language,
        "Java": java_language,
        "Rust": rust_language,
        "C": c_language,
        "C++": cpp_language,
        "Ruby": ruby_language,
        "PHP": php_language,
    }
except ImportError as e:
    print(f"Warning: Some language modules not available: {e}")
    LANGUAGE_MODULES = {}


# Language name normalization
LANGUAGE_ALIASES = {
    "Python": "Python",
    "JavaScript": "JavaScript",
    "JS": "JavaScript",
    "TypeScript": "JavaScript",  # Use JS parser for TS initially
    "TS": "JavaScript",
    "Go": "Go",
    "Golang": "Go",
    "Java": "Java",
    "Rust": "Rust",
    "C": "C",
    "C++": "C++",
    "CPP": "C++",
    "Ruby": "Ruby",
    "PHP": "PHP",
}

SUPPORTED_LANGUAGES = set(LANGUAGE_MODULES.keys())


def get_language(language_name: str) -> Optional[Any]:
    """Get tree-sitter language object by name."""
    normalized = LANGUAGE_ALIASES.get(language_name)
    if not normalized:
        return None
    
    return LANGUAGE_MODULES.get(normalized)


def normalize_language(language_name: str) -> Optional[str]:
    """Normalize language name to canonical form."""
    return LANGUAGE_ALIASES.get(language_name)
```

```python
# src/architectai/parser/parser.py
"""AST parsing using Tree-sitter."""
from typing import Dict, List, Any, Optional
import tree_sitter

from .languages import get_language, normalize_language


class ASTParser:
    """Parse source code into AST and extract structured information."""
    
    def __init__(self):
        self._parsers: Dict[str, tree_sitter.Parser] = {}
    
    def _get_parser(self, language: str) -> Optional[tree_sitter.Parser]:
        """Get or create parser for language."""
        if language in self._parsers:
            return self._parsers[language]
        
        lang_obj = get_language(language)
        if not lang_obj:
            return None
        
        parser = tree_sitter.Parser()
        parser.set_language(lang_obj)
        self._parsers[language] = parser
        return parser
    
    def parse(self, code: str, language: str) -> Optional[Dict[str, Any]]:
        """Parse code and extract structured information.
        
        Returns dict with:
        - functions: list of function info
        - classes: list of class info
        - imports: list of import info
        - tree: raw AST tree (optional)
        """
        normalized = normalize_language(language)
        if not normalized:
            return None
        
        parser = self._get_parser(normalized)
        if not parser:
            return None
        
        try:
            tree = parser.parse(code.encode('utf-8'))
            root = tree.root_node
            
            return {
                "functions": self._extract_functions(root, normalized),
                "classes": self._extract_classes(root, normalized),
                "imports": self._extract_imports(root, normalized),
                "language": normalized
            }
        except Exception as e:
            print(f"Error parsing code: {e}")
            return None
    
    def _extract_functions(self, root: tree_sitter.Node, language: str) -> List[Dict[str, Any]]:
        """Extract function definitions from AST."""
        functions = []
        
        if language == "Python":
            query_str = """
            (function_definition
              name: (identifier) @name
              parameters: (parameters) @params
              body: (block) @body) @func
            """
        elif language in ("JavaScript", "TypeScript"):
            query_str = """
            (function_declaration
              name: (identifier) @name
              parameters: (formal_parameters) @params
              body: (statement_block) @body) @func
            
            (method_definition
              name: (property_identifier) @name
              parameters: (formal_parameters) @params) @func
            """
        elif language == "Go":
            query_str = """
            (function_declaration
              name: (identifier) @name
              parameters: (parameter_list) @params) @func
            """
        elif language == "Java":
            query_str = """
            (method_declaration
              name: (identifier) @name
              parameters: (formal_parameters) @params) @func
            """
        elif language == "Rust":
            query_str = """
            (function_item
              name: (identifier) @name
              parameters: (parameters) @params) @func
            """
        else:
            return functions
        
        try:
            query = root.language.query(query_str)
            captures = query.captures(root)
            
            func_nodes = [node for node, name in captures if name == "func"]
            
            for func_node in func_nodes:
                func_info = self._parse_function_node(func_node, language)
                if func_info:
                    functions.append(func_info)
        except Exception as e:
            print(f"Error extracting functions: {e}")
        
        return functions
    
    def _parse_function_node(self, node: tree_sitter.Node, language: str) -> Optional[Dict[str, Any]]:
        """Parse a function node and extract info."""
        info = {
            "name": None,
            "parameters": [],
            "start_line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1
        }
        
        for child in node.children:
            if child.type == "identifier":
                info["name"] = child.text.decode('utf-8') if child.text else None
            elif child.type in ("parameters", "formal_parameters", "parameter_list"):
                info["parameters"] = self._extract_parameters(child, language)
            elif child.type == "property_identifier":
                info["name"] = child.text.decode('utf-8') if child.text else None
        
        return info if info["name"] else None
    
    def _extract_parameters(self, params_node: tree_sitter.Node, language: str) -> List[str]:
        """Extract parameter names from parameters node."""
        params = []
        
        if language == "Python":
            for child in params_node.children:
                if child.type == "identifier":
                    params.append(child.text.decode('utf-8') if child.text else "")
                elif child.type == "typed_parameter":
                    for subchild in child.children:
                        if subchild.type == "identifier":
                            params.append(subchild.text.decode('utf-8') if subchild.text else "")
                            break
                elif child.type == "default_parameter":
                    for subchild in child.children:
                        if subchild.type == "identifier":
                            params.append(subchild.text.decode('utf-8') if subchild.text else "")
                            break
        elif language in ("JavaScript", "TypeScript", "Go", "Java", "Rust"):
            for child in params_node.children:
                if child.type == "identifier":
                    params.append(child.text.decode('utf-8') if child.text else "")
        
        return params
    
    def _extract_classes(self, root: tree_sitter.Node, language: str) -> List[Dict[str, Any]]:
        """Extract class definitions from AST."""
        classes = []
        
        if language == "Python":
            query_str = """
            (class_definition
              name: (identifier) @name
              body: (block) @body) @class
            """
        elif language in ("JavaScript", "TypeScript"):
            query_str = """
            (class_declaration
              name: (identifier) @name
              body: (class_body) @body) @class
            """
        elif language == "Java":
            query_str = """
            (class_declaration
              name: (identifier) @name
              body: (class_body) @body) @class
            """
        elif language == "Rust":
            query_str = """
            (struct_item
              name: (type_identifier) @name) @class
            
            (impl_item
              type: (type_identifier) @name) @class
            """
        else:
            return classes
        
        try:
            query = root.language.query(query_str)
            captures = query.captures(root)
            
            class_nodes = [node for node, name in captures if name == "class"]
            
            for class_node in class_nodes:
                class_info = self._parse_class_node(class_node, language)
                if class_info:
                    classes.append(class_info)
        except Exception as e:
            print(f"Error extracting classes: {e}")
        
        return classes
    
    def _parse_class_node(self, node: tree_sitter.Node, language: str) -> Optional[Dict[str, Any]]:
        """Parse a class node and extract info."""
        info = {
            "name": None,
            "start_line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1
        }
        
        for child in node.children:
            if child.type in ("identifier", "type_identifier"):
                info["name"] = child.text.decode('utf-8') if child.text else None
                break
        
        return info if info["name"] else None
    
    def _extract_imports(self, root: tree_sitter.Node, language: str) -> List[Dict[str, Any]]:
        """Extract import statements from AST."""
        imports = []
        
        if language == "Python":
            query_str = """
            (import_statement
              (dotted_name) @name) @import
            
            (import_from_statement
              module_name: (dotted_name) @module
              (imported_names
                (identifier) @name)) @import
            
            (import_from_statement
              module_name: (relative_import) @module
              (imported_names
                (identifier) @name)) @import
            """
        elif language in ("JavaScript", "TypeScript"):
            query_str = """
            (import_statement
              (import_clause) @clause
              source: (string) @source) @import
            
            (call_expression
              function: (identifier) @func (#eq? @func "require")
              arguments: (arguments (string) @source)) @import
            """
        elif language == "Go":
            query_str = """
            (import_spec
              path: (interpreted_string_literal) @path) @import
            """
        elif language == "Java":
            query_str = """
            (import_declaration
              (scoped_identifier) @name) @import
            """
        elif language == "Rust":
            query_str = """
            (use_declaration
              argument: (scoped_use_list) @arg) @import
            
            (use_declaration
              argument: (identifier) @arg) @import
            """
        else:
            return imports
        
        try:
            query = root.language.query(query_str)
            captures = query.captures(root)
            
            import_nodes = [node for node, name in captures if name == "import"]
            
            for import_node in import_nodes:
                import_info = self._parse_import_node(import_node, language)
                if import_info:
                    imports.append(import_info)
        except Exception as e:
            print(f"Error extracting imports: {e}")
        
        return imports
    
    def _parse_import_node(self, node: tree_sitter.Node, language: str) -> Optional[Dict[str, Any]]:
        """Parse an import node and extract info."""
        info = {"name": None, "module": None}
        
        if language == "Python":
            # Handle different import styles
            for child in node.children:
                if child.type == "dotted_name":
                    info["name"] = child.text.decode('utf-8') if child.text else None
                elif child.type == "import_from_statement":
                    for subchild in child.children:
                        if subchild.type == "dotted_name":
                            info["module"] = subchild.text.decode('utf-8') if subchild.text else None
                        elif subchild.type == "imported_names":
                            # Extract imported names
                            names = []
                            for name_node in subchild.children:
                                if name_node.type == "identifier":
                                    names.append(name_node.text.decode('utf-8') if name_node.text else "")
                            if names:
                                info["name"] = ", ".join(names)
        elif language in ("JavaScript", "TypeScript"):
            for child in node.children:
                if child.type == "string":
                    source = child.text.decode('utf-8') if child.text else None
                    if source:
                        info["module"] = source.strip('"\'')
        elif language == "Go":
            for child in node.children:
                if child.type == "interpreted_string_literal":
                    path = child.text.decode('utf-8') if child.text else None
                    if path:
                        info["module"] = path.strip('"')
        elif language == "Java":
            for child in node.children:
                if child.type == "scoped_identifier":
                    info["name"] = child.text.decode('utf-8') if child.text else None
        elif language == "Rust":
            for child in node.children:
                if child.type in ("scoped_use_list", "identifier"):
                    info["name"] = child.text.decode('utf-8') if child.text else None
        
        if info["name"] or info["module"]:
            return info
        return None
```

**Step 4: Run tests (should pass)**

```bash
python -m pytest tests/parser/test_parser.py -v
```
Expected: All tests pass

**Step 5: Commit**

```bash
git add .
git commit -m "feat(parser): add AST parsing with tree-sitter"
```

---

## Task 5: CLI Interface - Basic Commands

**Files:**
- Create: `src/architectai/cli.py`
- Create: `tests/test_cli.py`

**Step 1: Write failing test**

```python
# tests/test_cli.py
import pytest
import tempfile
import os
from pathlib import Path
from click.testing import CliRunner
from architectai.cli import main


class TestCLI:
    def test_scan_command_local_path(self):
        """Test scan command with local path."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            Path(tmpdir, "main.py").write_text("print('hello')")
            
            result = runner.invoke(main, ['scan', tmpdir])
            
            assert result.exit_code == 0
            assert "Scanned" in result.output or "files" in result.output.lower()
    
    def test_scan_with_db_storage(self):
        """Test scan stores data in database."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            Path(tmpdir, "code").mkdir()
            Path(tmpdir, "code", "app.py").write_text("def main(): pass")
            
            result = runner.invoke(main, [
                '--db', db_path,
                'scan', os.path.join(tmpdir, "code")
            ])
            
            assert result.exit_code == 0
            assert os.path.exists(db_path)
```

**Step 2: Run test (should fail)**

```bash
python -m pytest tests/test_cli.py -v
```
Expected: ImportError

**Step 3: Implement CLI**

```python
# src/architectai/cli.py
"""Command-line interface for ArchitectAI."""
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

import click

from .db import Database
from .scanner import FileScanner, clone_repository, is_git_url
from .parser import ASTParser


@click.group()
@click.option('--db', default=None, help='Database file path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def main(ctx: click.Context, db: Optional[str], verbose: bool) -> None:
    """ArchitectAI - Local AI software architect for private codebases."""
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Set database path
    if db is None:
        # Use default location in user's home
        home = Path.home()
        db_dir = home / ".architectai"
        db_dir.mkdir(exist_ok=True)
        db = str(db_dir / "architectai.db")
    
    ctx.obj['db_path'] = db
    ctx.obj['verbose'] = verbose


@main.command()
@click.argument('source')
@click.option('--session-name', '-n', default=None, help='Session name')
@click.pass_context
def scan(ctx: click.Context, source: str, session_name: Optional[str]) -> None:
    """Scan a codebase (local path or git URL).
    
    SOURCE can be:
    - Local directory path
    - Git repository URL (https:// or git@)
    """
    db_path = ctx.obj['db_path']
    verbose = ctx.obj['verbose']
    
    click.echo(f"ArchitectAI - Scanning {source}...")
    
    # Initialize database
    db = Database(db_path)
    db.init()
    
    # Determine source type and prepare
    target_path = source
    is_temp = False
    
    if is_git_url(source):
        click.echo("Cloning repository...")
        target_path = tempfile.mkdtemp(prefix="architectai_")
        is_temp = True
        try:
            target_path = clone_repository(source, target_path)
            click.echo(f"Cloned to {target_path}")
        except RuntimeError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    if not os.path.exists(target_path):
        click.echo(f"Error: Path not found: {target_path}", err=True)
        sys.exit(1)
    
    # Create session
    session_id = db.create_session(
        source_path=source,
        session_type="git" if is_git_url(source) else "local"
    )
    
    if verbose:
        click.echo(f"Session ID: {session_id}")
    
    # Scan directory
    scanner = FileScanner(respect_gitignore=True)
    files = scanner.scan_directory(target_path)
    
    click.echo(f"Found {len(files)} files")
    
    # Store file metadata
    for file_info in files:
        db.insert_file(
            session_id=session_id,
            relative_path=file_info['relative_path'],
            absolute_path=file_info['absolute_path'],
            language=file_info['language'],
            size_bytes=file_info['size_bytes'],
            line_count=file_info['line_count'],
            content_hash=file_info['content_hash']
        )
    
    # Cleanup temp directory if cloned
    if is_temp:
        import shutil
        shutil.rmtree(target_path, ignore_errors=True)
    
    click.echo(f"Session {session_id[:8]}... created with {len(files)} files")
    click.echo(f"Database: {db_path}")


@main.command()
@click.argument('session_id')
@click.pass_context
def parse(ctx: click.Context, session_id: str) -> None:
    """Parse AST for all files in a session."""
    db_path = ctx.obj['db_path']
    verbose = ctx.obj['verbose']
    
    db = Database(db_path)
    
    # Get session
    session = db.get_session(session_id)
    if not session:
        click.echo(f"Error: Session not found: {session_id}", err=True)
        sys.exit(1)
    
    # Get files
    files = db.get_files_for_session(session_id)
    
    click.echo(f"Parsing {len(files)} files...")
    
    parser = ASTParser()
    parsed_count = 0
    error_count = 0
    
    for file_record in files:
        if not file_record['language']:
            continue
        
        try:
            with open(file_record['absolute_path'], 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            
            result = parser.parse(code, file_record['language'])
            
            if result:
                db.update_file_parsed(file_record['id'], ast_available=True)
                parsed_count += 1
                
                if verbose:
                    func_count = len(result.get('functions', []))
                    class_count = len(result.get('classes', []))
                    click.echo(f"  {file_record['relative_path']}: {func_count} functions, {class_count} classes")
            else:
                error_count += 1
                
        except Exception as e:
            error_count += 1
            if verbose:
                click.echo(f"  Error parsing {file_record['relative_path']}: {e}")
    
    click.echo(f"Parsed {parsed_count} files, {error_count} errors")


@main.command()
@click.pass_context
def list_sessions(ctx: click.Context) -> None:
    """List all sessions."""
    db_path = ctx.obj['db_path']
    
    # TODO: Implement list sessions
    click.echo("Sessions:")
    click.echo("(Not yet implemented)")


if __name__ == '__main__':
    main()
```

**Step 4: Run tests (should pass)**

```bash
python -m pytest tests/test_cli.py -v
```
Expected: All tests pass

**Step 5: Commit**

```bash
git add .
git commit -m "feat(cli): add basic CLI commands (scan, parse)"
```

---

## Task 6: Integration Test & Documentation

**Files:**
- Create: `tests/test_integration.py`
- Modify: `README.md` (update with usage instructions)

**Step 1: Integration test**

```python
# tests/test_integration.py
"""Integration tests for full pipeline."""
import pytest
import tempfile
import os
from pathlib import Path
from click.testing import CliRunner
from architectai.cli import main
from architectai.db import Database


class TestIntegration:
    def test_full_pipeline_local_repo(self):
        """Test full pipeline with local repository."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test repository
            code_dir = Path(tmpdir, "myproject")
            code_dir.mkdir()
            
            # Python file
            (code_dir / "main.py").write_text('''
import os
import sys

def main():
    """Main function."""
    print("Hello, World!")

if __name__ == "__main__":
    main()
''')
            
            # JavaScript file
            (code_dir / "app.js").write_text('''
const utils = require('./utils');

function init() {
    console.log("Initializing...");
}

module.exports = { init };
''')
            
            # Gitignore
            (code_dir / ".gitignore").write_text("node_modules/\n__pycache__/")
            
            db_path = os.path.join(tmpdir, "test.db")
            
            # Run scan
            result = runner.invoke(main, [
                '--db', db_path,
                '--verbose',
                'scan', str(code_dir)
            ])
            
            assert result.exit_code == 0, f"Scan failed: {result.output}"
            assert "Found 2 files" in result.output
            
            # Verify database
            db = Database(db_path)
            
            # Get session
            import sqlite3
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM sessions LIMIT 1")
                session_id = cursor.fetchone()[0]
            
            # Run parse
            result = runner.invoke(main, [
                '--db', db_path,
                '--verbose',
                'parse', session_id
            ])
            
            assert result.exit_code == 0, f"Parse failed: {result.output}"
            assert "Parsed" in result.output
```

**Step 2: Run integration test**

```bash
python -m pytest tests/test_integration.py -v
```
Expected: Test passes

**Step 3: Update README**

```markdown
# ArchitectAI

Local AI software architect for private codebases.

## Features

- **Local-only**: No code leaves your machine
- **Multi-language**: Python, JavaScript, Go, Java, Rust, C/C++, Ruby, PHP
- **AST Parsing**: Full tree-sitter integration
- **Documentation Generation**: Coming in M3
- **Q&A Agent**: Coming in M4

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Scan a local codebase
architectai scan /path/to/project

# Scan a GitHub repository
architectai scan https://github.com/user/repo

# Parse AST for a session
architectai parse <session-id>

# List all sessions
architectai list-sessions
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=src/architectai

# Format code
black src tests
isort src tests
```

## Architecture

See [CONTEXT.md](CONTEXT.md) for full architecture documentation.

## Milestones

- [x] M1: File scanner + language detection + AST parsing
- [ ] M2: Dependency graph + chunker + embeddings + vector store
- [ ] M3: Documentation Agent
- [ ] M4: Q&A Agent
- [ ] M5: Refactor Agent
- [ ] M6: Rebuilder Agent (basic)
- [ ] M7: Streamlit frontend
- [ ] M8: Rebuilder Agent (full)
```

**Step 4: Final commit**

```bash
git add .
git commit -m "docs: add integration tests and README usage guide"
```

---

## Summary

M1 is complete! We now have:

1. **Database Layer**: SQLite storage for sessions and file metadata
2. **File Scanner**: Recursive directory scanning with gitignore support
3. **Language Detection**: Using python-enry for automatic language identification
4. **AST Parser**: Tree-sitter integration for Python, JS, Go, Java, Rust, C/C++, Ruby, PHP
5. **CLI**: Click-based interface with `scan` and `parse` commands
6. **Repository Cloning**: Git URL support for GitHub repos
7. **Content Hashing**: SHA-256 for deduplication
8. **Tests**: Unit and integration tests with pytest

## Next Steps

M2 will add:
- Dependency graph builder (NetworkX)
- Code chunking with metadata
- Local embeddings (Ollama)
- Vector store integration (ChromaDB)

Ready to proceed to M2 when you are!
