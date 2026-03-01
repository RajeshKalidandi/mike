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

## Detailed Usage

### Scanning a Codebase

The `scan` command ingests a codebase and creates a session:

```bash
# Basic usage
architectai scan /path/to/project

# With custom database location
architectai --db /path/to/custom.db scan /path/to/project

# With verbose output
architectai --verbose scan /path/to/project

# With session name
architectai scan /path/to/project --session-name "My Project"

# Scan a GitHub repository
architectai scan https://github.com/username/repository
```

The scan command will:
1. Create a new session in the database
2. Recursively scan all supported source files
3. Ignore files matching `.gitignore` patterns
4. Store file metadata and content hashes
5. Display a summary with language breakdown

### Parsing Code

The `parse` command performs AST analysis on scanned files:

```bash
# Parse all files in a session
architectai parse <session-id>

# With verbose output (shows parsed functions and classes)
architectai --verbose parse <session-id>
```

The parse command will:
1. Load all files from the session
2. Parse each file using tree-sitter
3. Extract functions, classes, and imports
4. Update the database with parsing status

### Managing Sessions

```bash
# List all sessions
architectai list-sessions

# The database is stored at ~/.architectai/architectai.db by default
# You can specify a custom database with --db flag
```

## CLI Reference

### Global Options

- `--db PATH`: Path to database file (default: ~/.architectai/architectai.db)
- `--verbose, -v`: Enable verbose output
- `--help`: Show help message and exit

### Commands

#### `scan <source>`

Scan a codebase directory or git repository.

**Arguments:**
- `source`: Path to local directory or GitHub repository URL

**Options:**
- `--session-name, -n TEXT`: Optional session name

**Examples:**
```bash
architectai scan ./my-project
architectai scan https://github.com/user/repo --session-name "My Repo"
```

#### `parse <session_id>`

Parse code in a session using tree-sitter AST analysis.

**Arguments:**
- `session_id`: Session ID returned from scan command

**Examples:**
```bash
architectai parse 550e8400-e29b-41d4-a716-446655440000
```

#### `list-sessions`

List all active sessions in the database.

**Examples:**
```bash
architectai list-sessions
```

## Supported Languages

- Python (`.py`)
- JavaScript (`.js`)
- TypeScript (`.ts`, `.tsx`)
- Go (`.go`)
- Java (`.java`)
- Rust (`.rs`)
- C (`.c`, `.h`)
- C++ (`.cpp`, `.hpp`, `.cc`)
- Ruby (`.rb`)
- PHP (`.php`)

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=src/architectai

# Run integration tests only
pytest tests/test_integration.py -v

# Format code
black src tests
isort src tests

# Run linter
ruff check src tests
```

## Architecture

See [CONTEXT.md](CONTEXT.md) for full architecture documentation.

## Database Schema

The system uses SQLite for persistence:

- **sessions**: Stores session metadata (ID, source path, type, timestamps)
- **files**: Stores file metadata (path, language, size, line count, hash)
- **code_hashes**: Tracks content hashes for deduplication

## Milestones

- [x] M1: File scanner + language detection + AST parsing
- [ ] M2: Dependency graph + chunker + embeddings + vector store
- [ ] M3: Documentation Agent
- [ ] M4: Q&A Agent
- [ ] M5: Refactor Agent
- [ ] M6: Rebuilder Agent (basic)
- [ ] M7: Streamlit frontend
- [ ] M8: Rebuilder Agent (full)

## License

MIT License
