"""Test helpers and utility functions."""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Generator
from contextlib import contextmanager


@contextmanager
def temp_directory(prefix: str = "architectai_test_") -> Generator[Path, None, None]:
    """Create a temporary directory for testing.

    Args:
        prefix: Prefix for the directory name

    Yields:
        Path to temporary directory
    """
    path = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@contextmanager
def temp_file(
    suffix: str = "", prefix: str = "test_", content: Optional[str] = None
) -> Generator[Path, None, None]:
    """Create a temporary file for testing.

    Args:
        suffix: File suffix
        prefix: File prefix
        content: Optional content to write

    Yields:
        Path to temporary file
    """
    fd, path_str = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    os.close(fd)
    path = Path(path_str)

    try:
        if content is not None:
            path.write_text(content)
        yield path
    finally:
        path.unlink(missing_ok=True)


def create_test_file(
    directory: Path, relative_path: str, content: str, encoding: str = "utf-8"
) -> Path:
    """Create a test file with the given content.

    Args:
        directory: Base directory
        relative_path: Relative path within directory
        content: File content
        encoding: File encoding

    Returns:
        Path to created file
    """
    file_path = directory / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding=encoding)
    return file_path


def create_sample_repo(
    base_path: Path, language: str = "python", name: str = "sample_repo"
) -> Path:
    """Create a sample repository structure.

    Args:
        base_path: Base path for the repository
        language: Language type (python, javascript, go, etc.)
        name: Repository name

    Returns:
        Path to created repository
    """
    repo_path = base_path / name
    repo_path.mkdir(exist_ok=True)

    if language == "python":
        _create_python_repo(repo_path)
    elif language == "javascript":
        _create_javascript_repo(repo_path)
    elif language == "go":
        _create_go_repo(repo_path)
    elif language == "java":
        _create_java_repo(repo_path)
    elif language == "mixed":
        _create_mixed_repo(repo_path)
    elif language == "monorepo":
        _create_monorepo(repo_path)

    return repo_path


def _create_python_repo(repo_path: Path) -> None:
    """Create a Python sample repository."""
    # Directory structure
    (repo_path / "src" / "myapp").mkdir(parents=True)
    (repo_path / "tests").mkdir()
    (repo_path / "docs").mkdir()

    # Main module
    create_test_file(
        repo_path,
        "src/myapp/__init__.py",
        '"""MyApp package."""\n__version__ = \'1.0.0\'\n',
    )

    create_test_file(
        repo_path,
        "src/myapp/main.py",
        """
\"\"\"Main application module.\"\"\"
import os
import sys
from typing import List, Optional

from .config import Config
from .utils import logger


class Application:
    \"\"\"Main application class.\"\"\"
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.running = False
    
    def start(self) -> None:
        \"\"\"Start the application.\"\"\"
        logger.info("Starting application")
        self.running = True
        self._run_main_loop()
    
    def stop(self) -> None:
        \"\"\"Stop the application.\"\"\"
        logger.info("Stopping application")
        self.running = False
    
    def _run_main_loop(self) -> None:
        \"\"\"Run the main loop.\"\"\"
        while self.running:
            self._process_iteration()
    
    def _process_iteration(self) -> None:
        \"\"\"Process one iteration.\"\"\"
        pass


def main(args: Optional[List[str]] = None) -> int:
    \"\"\"Main entry point.\"\"\"
    app = Application()
    try:
        app.start()
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    finally:
        app.stop()


if __name__ == "__main__":
    sys.exit(main())
""",
    )

    create_test_file(
        repo_path,
        "src/myapp/config.py",
        """
\"\"\"Configuration module.\"\"\"
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    \"\"\"Application configuration.\"\"\"
    debug: bool = False
    host: str = "localhost"
    port: int = 8080
    database_url: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "Config":
        \"\"\"Load configuration from environment.\"\"\"
        return cls(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            host=os.getenv("HOST", "localhost"),
            port=int(os.getenv("PORT", "8080")),
            database_url=os.getenv("DATABASE_URL"),
        )
""",
    )

    create_test_file(
        repo_path,
        "src/myapp/utils.py",
        """
\"\"\"Utility functions.\"\"\"
import logging
from typing import Any


def setup_logging(level: str = "INFO") -> logging.Logger:
    \"\"\"Setup logging configuration.\"\"\"
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger("myapp")


logger = setup_logging()


def safe_get(d: dict, key: str, default: Any = None) -> Any:
    \"\"\"Safely get a value from a dictionary.\"\"\"
    try:
        return d[key]
    except (KeyError, TypeError):
        return default
""",
    )

    # Tests
    create_test_file(repo_path, "tests/__init__.py", "")
    create_test_file(
        repo_path,
        "tests/test_main.py",
        """
\"\"\"Tests for main module.\"\"\"
import pytest
from myapp.main import Application, main
from myapp.config import Config


class TestApplication:
    \"\"\"Test cases for Application class.\"\"\"
    
    def test_initialization(self):
        app = Application()
        assert not app.running
        assert app.config is not None
    
    def test_start_stop(self):
        app = Application()
        # Note: start() would block, so we test indirectly
        assert hasattr(app, 'start')
        assert hasattr(app, 'stop')


def test_main_function():
    result = main([])
    assert isinstance(result, int)
""",
    )

    create_test_file(
        repo_path,
        "tests/test_config.py",
        """
\"\"\"Tests for config module.\"\"\"
import os
from myapp.config import Config


class TestConfig:
    def test_default_values(self):
        config = Config()
        assert config.host == "localhost"
        assert config.port == 8080
        assert not config.debug
    
    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("HOST", "0.0.0.0")
        monkeypatch.setenv("PORT", "3000")
        monkeypatch.setenv("DEBUG", "true")
        
        config = Config.from_env()
        assert config.host == "0.0.0.0"
        assert config.port == 3000
        assert config.debug
""",
    )

    # Configuration files
    create_test_file(
        repo_path,
        "README.md",
        """# Sample Python Project

This is a sample Python project for testing.

## Installation

```bash
pip install -e .
```

## Usage

```bash
python -m myapp
```

## Testing

```bash
pytest
```
""",
    )

    create_test_file(
        repo_path,
        "requirements.txt",
        """pytest>=7.0.0
click>=8.0.0
""",
    )

    create_test_file(
        repo_path,
        "pyproject.toml",
        """[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "myapp"
version = "1.0.0"
description = "Sample Python application"
requires-python = ">=3.8"
""",
    )

    create_test_file(
        repo_path,
        ".gitignore",
        """__pycache__/
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
.pytest_cache/
.coverage
htmlcov/
.env
.venv
venv/
""",
    )


def _create_javascript_repo(repo_path: Path) -> None:
    """Create a JavaScript sample repository."""
    (repo_path / "src").mkdir()
    (repo_path / "tests").mkdir()

    create_test_file(
        repo_path,
        "package.json",
        """{
  "name": "sample-js-app",
  "version": "1.0.0",
  "description": "Sample JavaScript application",
  "main": "src/index.js",
  "scripts": {
    "test": "jest",
    "start": "node src/index.js"
  },
  "dependencies": {
    "express": "^4.18.0"
  },
  "devDependencies": {
    "jest": "^29.0.0"
  }
}
""",
    )

    create_test_file(
        repo_path,
        "src/index.js",
        """
const express = require('express');
const { logger } = require('./utils');

class AppServer {
    constructor(port = 3000) {
        this.app = express();
        this.port = port;
        this.setupRoutes();
    }

    setupRoutes() {
        this.app.get('/', (req, res) => {
            res.json({ message: 'Hello, World!' });
        });

        this.app.get('/health', (req, res) => {
            res.json({ status: 'healthy' });
        });
    }

    start() {
        this.app.listen(this.port, () => {
            logger.info(`Server running on port ${this.port}`);
        });
    }
}

const server = new AppServer(process.env.PORT || 3000);
server.start();

module.exports = { AppServer };
""",
    )

    create_test_file(
        repo_path,
        "src/utils.js",
        """
const logger = {
    info: (msg) => console.log(`[INFO] ${new Date().toISOString()}: ${msg}`),
    error: (msg) => console.error(`[ERROR] ${new Date().toISOString()}: ${msg}`),
};

const safeParseJSON = (str) => {
    try {
        return JSON.parse(str);
    } catch (e) {
        return null;
    }
};

module.exports = { logger, safeParseJSON };
""",
    )

    create_test_file(
        repo_path,
        "tests/index.test.js",
        """
const { AppServer } = require('../src/index');

describe('AppServer', () => {
    test('should create instance', () => {
        const server = new AppServer();
        expect(server).toBeDefined();
        expect(server.port).toBe(3000);
    });
});
""",
    )

    create_test_file(
        repo_path,
        ".gitignore",
        """node_modules/
dist/
.env
.env.local
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.DS_Store
coverage/
.nyc_output/
""",
    )


def _create_go_repo(repo_path: Path) -> None:
    """Create a Go sample repository."""
    create_test_file(
        repo_path,
        "go.mod",
        """module github.com/example/sample-go-app

go 1.21
""",
    )

    create_test_file(
        repo_path,
        "main.go",
        """package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
)

type Server struct {
	port    string
	handler http.Handler
}

func NewServer(port string) *Server {
	return &Server{
		port:    port,
		handler: nil,
	}
}

func (s *Server) Start() error {
	fmt.Printf("Starting server on port %s\n", s.port)
	return http.ListenAndServe(":"+s.port, s.handler)
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	server := NewServer(port)
	if err := server.Start(); err != nil {
		log.Fatal(err)
	}
}
""",
    )

    (repo_path / "internal" / "config").mkdir(parents=True)
    create_test_file(
        repo_path,
        "internal/config/config.go",
        """package config

import (
	"os"
	"strconv"
)

type Config struct {
	Debug    bool
	Port     string
	Database string
}

func Load() (*Config, error) {
	debug, _ := strconv.ParseBool(os.Getenv("DEBUG"))
	
	return &Config{
		Debug:    debug,
		Port:     getEnv("PORT", "8080"),
		Database: getEnv("DATABASE_URL", ""),
	}, nil
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
""",
    )


def _create_java_repo(repo_path: Path) -> None:
    """Create a Java sample repository."""
    src_path = repo_path / "src" / "main" / "java" / "com" / "example"
    src_path.mkdir(parents=True)
    test_path = repo_path / "src" / "test" / "java" / "com" / "example"
    test_path.mkdir(parents=True)

    create_test_file(
        repo_path,
        "pom.xml",
        """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <groupId>com.example</groupId>
    <artifactId>sample-app</artifactId>
    <version>1.0.0</version>
    
    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
    </properties>
</project>
""",
    )

    create_test_file(
        src_path,
        "App.java",
        """package com.example;

import java.util.List;

public class App {
    private final Config config;
    private final Service service;
    
    public App(Config config) {
        this.config = config;
        this.service = new Service();
    }
    
    public void run() {
        System.out.println("Application started");
        service.initialize();
    }
    
    public static void main(String[] args) {
        Config config = Config.fromArgs(args);
        App app = new App(config);
        app.run();
    }
}
""",
    )

    create_test_file(
        src_path,
        "Config.java",
        """package com.example;

public class Config {
    private String host;
    private int port;
    
    public static Config fromArgs(String[] args) {
        Config config = new Config();
        config.host = "localhost";
        config.port = 8080;
        return config;
    }
    
    public String getHost() { return host; }
    public int getPort() { return port; }
}
""",
    )

    create_test_file(
        src_path,
        "Service.java",
        """package com.example;

public class Service {
    public void initialize() {
        System.out.println("Service initialized");
    }
}
""",
    )


def _create_mixed_repo(repo_path: Path) -> None:
    """Create a mixed-language repository."""
    # Python backend
    (repo_path / "backend" / "src").mkdir(parents=True)
    create_test_file(repo_path, "backend/src/main.py", "def main(): pass")
    create_test_file(repo_path, "backend/requirements.txt", "flask\n")

    # JavaScript frontend
    (repo_path / "frontend" / "src").mkdir(parents=True)
    create_test_file(repo_path, "frontend/src/App.js", "const App = () => {};")
    create_test_file(repo_path, "frontend/package.json", '{"name": "frontend"}')

    # Go worker
    (repo_path / "worker").mkdir()
    create_test_file(repo_path, "worker/main.go", "package main\nfunc main() {}")

    # Documentation
    create_test_file(repo_path, "README.md", "# Mixed Project\n")


def _create_monorepo(repo_path: Path) -> None:
    """Create a monorepo structure."""
    # Project A - Python service
    (repo_path / "services" / "service-a" / "src").mkdir(parents=True)
    create_test_file(repo_path, "services/service-a/src/main.py", "def main(): pass")
    create_test_file(repo_path, "services/service-a/requirements.txt", "fastapi\n")
    create_test_file(repo_path, "services/service-a/Dockerfile", "FROM python:3.9")

    # Project B - Node.js service
    (repo_path / "services" / "service-b" / "src").mkdir(parents=True)
    create_test_file(
        repo_path,
        "services/service-b/src/index.js",
        "const express = require('express');",
    )
    create_test_file(
        repo_path, "services/service-b/package.json", '{"name": "service-b"}'
    )
    create_test_file(repo_path, "services/service-b/Dockerfile", "FROM node:18")

    # Shared library
    (repo_path / "libs" / "shared" / "src").mkdir(parents=True)
    create_test_file(repo_path, "libs/shared/src/utils.py", "def helper(): pass")

    # Root configuration
    create_test_file(
        repo_path,
        "docker-compose.yml",
        """version: '3.8'
services:
  service-a:
    build: ./services/service-a
  service-b:
    build: ./services/service-b
""",
    )
    create_test_file(repo_path, "README.md", "# Monorepo\n")


def make_file_executable(path: Path) -> None:
    """Make a file executable."""
    current = path.stat().st_mode
    path.chmod(current | 0o111)


def count_files(directory: Path, pattern: str = "*") -> int:
    """Count files matching a pattern in directory recursively.

    Args:
        directory: Directory to search
        pattern: Glob pattern to match

    Returns:
        Number of matching files
    """
    return len(list(directory.rglob(pattern)))


def get_all_file_paths(directory: Path) -> List[Path]:
    """Get all file paths in directory recursively.

    Args:
        directory: Directory to search

    Returns:
        List of file paths
    """
    return [f for f in directory.rglob("*") if f.is_file()]


def get_file_sizes(directory: Path) -> Dict[Path, int]:
    """Get sizes of all files in directory.

    Args:
        directory: Directory to search

    Returns:
        Dictionary mapping file paths to sizes
    """
    return {f: f.stat().st_size for f in get_all_file_paths(directory)}
