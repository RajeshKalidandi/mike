# ArchitectAI

**Local AI Software Architect for Private Codebases**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

ArchitectAI is a fully local, offline-capable AI system that ingests any codebase or GitHub repository and produces:

- **Detailed Documentation** - README, architecture guides, API references
- **Architecture Overviews** - Dependency maps, component diagrams
- **Natural Language Q&A** - Ask questions about your codebase in plain English
- **Refactor Suggestions** - Detect code smells and improvement opportunities  
- **Code Generation** - Scaffold new projects from existing architecture

**No third-party APIs. No code leaves your machine. Everything runs on local models and local infrastructure.**

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
- [CLI Reference](#cli-reference)
- [Python API](#python-api)
- [Architecture](#architecture)
- [Supported Languages](#supported-languages)
- [System Requirements](#system-requirements)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Core Capabilities

- **100% Local Processing** - No data leaves your machine
- **Multi-Language Support** - Python, JavaScript/TypeScript, Go, Java, Rust, C/C++, Ruby, PHP
- **AST Analysis** - Deep code understanding via tree-sitter parsing
- **Semantic Search** - Vector-based code search with embeddings
- **Dependency Graphs** - Visualize and analyze code relationships
- **Agent Orchestration** - Multi-agent system for complex tasks

### Agents

- **Documentation Agent** - Generate comprehensive docs from code
- **Q&A Agent** - Answer questions about your codebase
- **Refactor Agent** - Detect issues and suggest improvements
- **Rebuilder Agent** - Scaffold new projects from templates

### Memory Architecture

Three-layer memory system for comprehensive code understanding:

1. **Structural Memory** - AST nodes, dependency graphs, call chains
2. **Semantic Memory** - Embeddings, summaries, natural language context
3. **Execution Memory** - Agent reasoning history, learned patterns

---

## Installation

### Prerequisites

- **Python** 3.8 or higher
- **Git** (for cloning repositories)
- **Ollama** (optional, for LLM support) - [Install from ollama.ai](https://ollama.ai)

### Method 1: pip install

```bash
pip install architectai
```

### Method 2: Development install

```bash
git clone https://github.com/rajesh/architectai.git
cd architectai
pip install -e ".[dev]"
```

### Method 3: With all extras

```bash
pip install -e ".[all]"
```

### Post-Installation Setup

Run the bootstrap process to initialize the system:

```bash
# Initialize directories and database
python -c "from architectai import bootstrap; bootstrap()"

# Or use the CLI
architectai bootstrap
```

Download recommended models (requires Ollama):

```bash
# Download default models
ollama pull mxbai-embed-large
ollama pull qwen2.5-coder:14b
```

---

## Quick Start

### 1. Scan a Codebase

```bash
# Scan a local directory
architectai scan /path/to/your/project

# Scan a GitHub repository
architectai scan https://github.com/username/repository

# With a custom session name
architectai scan ./my-project --session-name "My Project"
```

### 2. Analyze the Code

```bash
# Parse AST and build dependency graph
architectai parse <session-id>

# Generate embeddings for semantic search
architectai embed <session-id>
```

### 3. Generate Documentation

```bash
# Generate README and architecture docs
architectai docs <session-id> --output ./docs

# Specify which docs to generate
architectai docs <session-id> --type readme --type architecture --type api
```

### 4. Ask Questions

```bash
# Ask about your codebase
architectai ask <session-id> "Where is authentication handled?"

# Another example
architectai ask <session-id> "What happens when a payment fails?"
```

### 5. Web Interface

```bash
# Launch the Streamlit web UI
python web_launcher.py

# Or with specific port
python web_launcher.py --port 8501
```

---

## Usage Examples

### Python API

#### Basic Usage

```python
from architectai import create_ai

# Initialize
ai = create_ai()

# Scan a codebase
result = ai.scan_codebase("/path/to/project")
print(f"Session ID: {result.session_id}")
print(f"Files scanned: {result.files_scanned}")

# Run analysis
analysis = ai.analyze(result.session_id)
print(f"Dependencies found: {analysis.dependencies_found}")

# Generate documentation
docs = ai.generate_docs(result.session_id, output_dir="./docs")
print(f"Generated {len(docs.files_generated)} files")

# Ask questions
qa = ai.ask_question(result.session_id, "Where is authentication handled?")
print(qa.answer)
print(f"Relevant files: {qa.relevant_files}")
```

#### Advanced Usage with Progress Callbacks

```python
from architectai import ArchitectAI

def on_progress(task, progress, message):
    print(f"[{task}] {int(progress*100)}%: {message}")

ai = ArchitectAI(verbose=True)
ai.add_progress_callback(on_progress)

# Operations will now report progress
result = ai.scan_codebase("./my-project")
docs = ai.generate_docs(result.session_id)
```

#### Session Management

```python
# List all sessions
sessions = ai.list_sessions(limit=10, include_stats=True)
for session in sessions:
    print(f"{session.session_id[:8]}: {session.file_count} files")

# Get session details
session = ai.get_session(session_id)
print(f"Source: {session.source_path}")
print(f"Languages: {session.languages}")

# Delete a session
ai.delete_session(session_id)
```

#### Refactoring Analysis

```python
# Get refactoring suggestions
refactor = ai.suggest_refactoring(session_id)
for suggestion in refactor.suggestions:
    print(f"[{suggestion['type']}] {suggestion['description']}")
    print(f"Recommendation: {suggestion['recommendation']}")

# Focus on specific areas
refactor = ai.suggest_refactoring(
    session_id,
    focus_areas=["performance", "readability"]
)
```

#### Project Rebuilding

```python
# Scaffold a new project from existing codebase
result = ai.rebuild_project(
    session_id=template_session_id,
    output_dir="./new-project",
    constraints={
        "framework": "fastapi",
        "database": "postgresql"
    }
)
print(f"Created {len(result.files_created)} files")
```

### CLI Examples

#### Complete Workflow

```bash
# 1. Scan a codebase
SESSION_ID=$(architectai scan ./my-project --output json | jq -r '.session_id')

# 2. Parse AST
architectai parse $SESSION_ID

# 3. Build dependency graph
architectai build-graph $SESSION_ID --output graph.json

# 4. Generate embeddings
architectai embed $SESSION_ID

# 5. Generate docs
architectai docs $SESSION_ID --output ./docs

# 6. Ask questions
architectai ask $SESSION_ID "What are the main components?"

# 7. Search semantic index
architectai search $SESSION_ID "authentication logic" --n-results 5
```

#### Session Management

```bash
# List sessions
architectai session list

# Get session info
architectai session info <session-id>

# Delete session
architectai session delete <session-id> --force
```

#### System Status

```bash
# Check system status
architectai status

# Telemetry
architectai telemetry stats
architectai telemetry report --format markdown --output report.md
```

---

## CLI Reference

### Global Options

```bash
architectai [OPTIONS] COMMAND [ARGS]...

Options:
  --db PATH          Database file path (default: ~/.architectai/architectai.db)
  --verbose, -v      Enable verbose output
  --output, -o       Output format: plain, json, markdown (default: plain)
  --help             Show help message
```

### Commands

#### `scan <source>`
Scan a codebase directory or git repository.

```bash
architectai scan /path/to/project [--session-name NAME]
architectai scan https://github.com/user/repo
```

#### `parse <session_id>`
Parse code using tree-sitter AST analysis.

```bash
architectai parse <session_id>
```

#### `docs <session_id>`
Generate documentation.

```bash
architectai docs <session_id> [--output DIR] [--type readme] [--type architecture]
```

#### `ask <session_id> <question>`
Ask a question about the codebase.

```bash
architectai ask <session_id> "What does this function do?"
```

#### `refactor <session_id>`
Analyze code for refactoring opportunities.

```bash
architectai refactor <session_id> [--focus performance] [--focus readability]
```

#### `rebuild <template_session_id> <output_dir>`
Scaffold a new project from a template.

```bash
architectai rebuild <session_id> ./new-project [--constraint framework=fastapi]
```

#### `build-graph <session_id>`
Build dependency graph.

```bash
architectai build-graph <session_id> [--output graph.json]
```

#### `embed <session_id>`
Generate embeddings for semantic search.

```bash
architectai embed <session_id> [--model mxbai-embed-large]
```

#### `search <session_id> <query>`
Semantic search in codebase.

```bash
architectai search <session_id> "authentication logic" [--n-results 10]
```

#### `session list`
List all sessions.

```bash
architectai session list [--limit 20]
```

#### `session info <session_id>`
Show session details.

```bash
architectai session info <session_id>
```

#### `session delete <session_id>`
Delete a session.

```bash
architectai session delete <session_id> [--force]
```

#### `status`
Show system status.

```bash
architectai status
```

---

## Python API

### Main Class: `ArchitectAI`

The `ArchitectAI` class is the primary interface for programmatic usage.

#### Constructor

```python
ArchitectAI(
    config_path: Optional[Union[str, Path]] = None,
    settings: Optional[Settings] = None,
    db_path: Optional[str] = None,
    verbose: bool = False,
)
```

#### Core Methods

##### `scan_codebase(path, session_name=None, ignore_patterns=None)`
Scan and ingest a codebase.

**Parameters:**
- `path` (str|Path): Path to local directory or Git URL
- `session_name` (str, optional): Name for the session
- `ignore_patterns` (List[str], optional): Additional ignore patterns

**Returns:** `ScanResult`

##### `analyze(session_id, include_graph=True, include_embeddings=False)`
Run full analysis on a session.

**Parameters:**
- `session_id` (str): Session ID to analyze
- `include_graph` (bool): Build dependency graph
- `include_embeddings` (bool): Generate embeddings

**Returns:** `AnalysisResult`

##### `generate_docs(session_id, output_dir=None, doc_types=None)`
Generate documentation.

**Parameters:**
- `session_id` (str): Session ID
- `output_dir` (str|Path, optional): Output directory
- `doc_types` (List[str], optional): Doc types to generate

**Returns:** `DocsResult`

##### `ask_question(session_id, query, include_context=True)`
Ask a question about the codebase.

**Parameters:**
- `session_id` (str): Session ID
- `query` (str): Natural language question
- `include_context` (bool): Include semantic context

**Returns:** `QAResult`

##### `suggest_refactoring(session_id, focus_areas=None)`
Get refactoring suggestions.

**Parameters:**
- `session_id` (str): Session ID
- `focus_areas` (List[str], optional): Focus areas

**Returns:** `RefactorResult`

##### `rebuild_project(session_id, output_dir, constraints=None)`
Scaffold a new project.

**Parameters:**
- `session_id` (str): Template session ID
- `output_dir` (str|Path): Output directory
- `constraints` (Dict, optional): Project constraints

**Returns:** `RebuildResult`

#### Session Management Methods

##### `get_session(session_id)`
Get session information.

**Returns:** `SessionInfo` or `None`

##### `list_sessions(limit=100, include_stats=False)`
List all sessions.

**Returns:** `List[SessionInfo]`

##### `delete_session(session_id)`
Delete a session.

**Returns:** `bool`

#### Context Manager Support

```python
with ArchitectAI() as ai:
    result = ai.scan_codebase("./project")
    # Automatically closed when done
```

### Bootstrap Utilities

```python
from architectai import bootstrap, check_dependencies, verify_installation

# Run full bootstrap
result = bootstrap(download_default_models=True, verbose=True)

# Check dependencies
deps = check_dependencies()
print(f"Ollama available: {deps['external']['ollama']['available']}")

# Verify installation
status = verify_installation()
if status['ready']:
    print("System ready!")
```

---

## Architecture

```
User Upload (Repo / Folder / ZIP)
        │
        ▼
File Scanner + Language Detection
        │
        ▼
AST Parsing (Tree-sitter)
        │
        ▼
Dependency Graph Builder (NetworkX)
        │
        ▼
Hierarchical Summarizer (Bottom-Up)
        │
        ▼
Chunker + Metadata Tagger
        │
        ▼
Local Embedding Model (Ollama / nomic-embed-text)
        │
        ▼
Vector Store (ChromaDB or Qdrant — local)
        │
        ▼
Code Knowledge Graph
        │
        ▼
Agent Orchestrator (LangGraph)
        │
        ├──── Documentation Agent
        ├──── Q&A Agent
        ├──── Refactor Agent
        └──── Rebuilder Agent
        │
        ▼
Structured Output (Markdown / JSON / Scaffolded Code)
```

### Three-Layer Memory

| Memory Type | What It Stores | Implementation |
|---|---|---|
| **Structural** | AST nodes, dependency graph, import trees | NetworkX graph + SQLite |
| **Semantic** | Embeddings, code chunks, summaries | ChromaDB / Qdrant |
| **Execution** | Agent reasoning, iteration history | In-memory + JSON log |

### Context Assembly Pipeline

```
Query (natural language or structured)
        │
        ▼
Semantic Search → Top-K Chunks
        │
        ▼
Graph-Aware Expansion
  (Fetch callers + callees)
        │
        ▼
Hierarchical Summary Injection
        │
        ▼
Token Budget Manager
        │
        ▼
Assembled Context → Agent
```

---

## Supported Languages

| Language | Extensions | AST Parsing | Dependencies |
|---|---|---|---|
| Python | .py | ✅ | ✅ |
| JavaScript | .js | ✅ | ✅ |
| TypeScript | .ts, .tsx | ✅ | ✅ |
| Go | .go | ✅ | ✅ |
| Java | .java | ✅ | ✅ |
| Rust | .rs | ✅ | ✅ |
| C | .c, .h | ✅ | ✅ |
| C++ | .cpp, .hpp, .cc | ✅ | ✅ |
| Ruby | .rb | ✅ | ✅ |
| PHP | .php | ✅ | ✅ |

---

## System Requirements

### Minimum Requirements

- **OS**: macOS, Linux, or Windows with WSL
- **RAM**: 16GB
- **Storage**: 10GB free space
- **Python**: 3.8+

### Recommended for Full Features

- **RAM**: 32GB+
- **GPU**: NVIDIA with CUDA (optional, for faster embeddings)
- **Storage**: 50GB+ SSD

### Model Requirements

| Use Case | Minimum VRAM | Recommended Model |
|---|---|---|
| Documentation + Q&A | 8GB | Qwen2.5-Coder 14B |
| Refactoring | 8GB | Qwen2.5-Coder 14B |
| Code Generation | 24GB | Kimi K2.5 or DeepSeek V3 |

---

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/rajesh/architectai.git
cd architectai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=src/architectai
```

### Code Style

```bash
# Format code
black src tests
isort src tests

# Run linter
ruff check src tests

# Type checking
mypy src/architectai
```

### Project Structure

```
architectai/
├── src/architectai/
│   ├── __init__.py          # Public API exports
│   ├── api.py               # Main API interface
│   ├── bootstrap.py         # System initialization
│   ├── cli.py               # Command-line interface
│   ├── cli_orchestrator.py  # CLI task orchestration
│   ├── agents/              # AI agents
│   │   ├── qa_agent.py
│   │   ├── refactor_agent.py
│   │   └── rebuilder_agent.py
│   ├── chunker/             # Code chunking
│   ├── config/              # Configuration management
│   ├── db/                  # Database models
│   ├── embeddings/          # Embedding service
│   ├── graph/               # Dependency graph
│   ├── orchestrator/        # Agent orchestration
│   ├── parser/              # AST parsing
│   ├── scanner/             # File scanning
│   ├── vectorstore/         # Vector database
│   └── web/                 # Streamlit web UI
├── tests/                   # Test suite
├── docs/                    # Documentation
├── examples/                # Example usage
├── web_launcher.py          # Web UI launcher
├── setup.py                 # Package setup
└── requirements.txt         # Dependencies
```

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Contribution Guide

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add tests for new features
- Update documentation
- Ensure all tests pass before submitting PR

### Reporting Issues

Please use GitHub Issues to report bugs or request features. Include:

- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- System information (OS, Python version, etc.)

---

## Milestones

| Milestone | Status | Description |
|---|---|---|
| M1 | ✅ Complete | File scanner + language detection + AST parsing |
| M2 | ✅ Complete | Dependency graph + chunker + embeddings + vector store |
| M3 | ✅ Complete | Documentation Agent |
| M4 | ✅ Complete | Q&A Agent |
| M5 | ✅ Complete | Refactor Agent |
| M6 | ✅ Complete | Rebuilder Agent (basic) |
| M7 | ✅ Complete | Streamlit frontend |
| M8 | 🚧 Planned | Rebuilder Agent (full code generation) |

---

## Security

- **No external API calls** - All processing is local
- **No telemetry** - No data is sent to external servers
- **Code isolation** - Rebuilder runs in sandboxed subprocess
- **Prompt injection protection** - Input sanitization built-in

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) - AST parsing
- [Ollama](https://ollama.ai) - Local LLM hosting
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [NetworkX](https://networkx.org/) - Graph analysis
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent orchestration patterns

---

## Support

- 📖 [Documentation](https://github.com/rajesh/architectai/wiki)
- 🐛 [Issue Tracker](https://github.com/rajesh/architectai/issues)
- 💬 [Discussions](https://github.com/rajesh/architectai/discussions)

---

**Built with ❤️ for the developer community**
