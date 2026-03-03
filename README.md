# Mike 🏗️

**Local AI Software Architect for Private Codebases**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests](https://img.shields.io/badge/tests-467%20passing-brightgreen.svg)](./tests)

> 🎉 **All 8 Milestones Complete!** Fully functional local AI software architect system with 4 intelligent agents, comprehensive web interface, and full code generation capabilities.

Mike is a fully local, offline-capable AI system that ingests any codebase or GitHub repository and produces:

- 📚 **Detailed Documentation** - README, architecture guides, API references
- 🗺️ **Architecture Overviews** - Dependency maps, component diagrams  
- ❓ **Natural Language Q&A** - Ask questions about your codebase in plain English
- 🔧 **Refactor Suggestions** - Detect code smells and improvement opportunities
- 🏗️ **Code Generation** - Scaffold new projects from existing architecture

**🔒 No third-party APIs. No code leaves your machine. Everything runs on local models and local infrastructure.**

---

## 🎬 Demo

```bash
# Scan a codebase
$ mike scan ./my-project --session-name "My Project"
Created session: d5634ac4-443e-4735-afa2-8cbf9cac39f0
Found 127 files
Scanned 127 files

# Generate documentation
$ mike docs d5634ac4-443e-4735-afa2-8cbf9cac39f0 --output ./docs
Generating documentation... completed
Documentation generated in: ./docs

# Ask questions about your code
$ mike ask d5634ac4-443e-4735-afa2-8cbf9cac39f0 "Where is authentication handled?"
Based on the codebase analysis:

Found 3 potentially relevant files:
- `src/auth.py` (lines 15-45)
- `src/middleware/auth.py` (lines 8-32)
- `src/routes/login.py` (lines 12-28)
```

---

## 📋 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Usage](#-usage)
- [Web Interface](#-web-interface)
- [CLI Reference](#-cli-reference)
- [Python API](#-python-api)
- [Architecture](#-architecture)
- [Development](#-development)
- [Milestones](#-milestones)
- [License](#-license)

---

## ✨ Features

### 🧠 Core Capabilities

- **100% Local Processing** - No data leaves your machine
- **Multi-Language Support** - Python, JavaScript/TypeScript, Go, Java, Rust, C/C++, Ruby, PHP
- **AST Analysis** - Deep code understanding via tree-sitter parsing
- **Semantic Search** - Vector-based code search with embeddings
- **Dependency Graphs** - Visualize and analyze code relationships
- **Agent Orchestration** - Multi-agent system for complex tasks

### 🤖 AI Agents

| Agent | Description | Status |
|-------|-------------|--------|
| **📚 Documentation** | Generate README, architecture guides, API reference | ✅ Active |
| **❓ Q&A** | Answer questions with source attribution | ✅ Active |
| **🔧 Refactor** | Detect code smells, security issues, improvements | ✅ Active |
| **🏗️ Rebuilder** | Scaffold new projects from architecture templates | ✅ Active |

### 🧠 Three-Layer Memory Architecture

| Layer | Stores | Implementation |
|-------|--------|----------------|
| **Structural** | AST nodes, dependency graphs, import trees | NetworkX + SQLite |
| **Semantic** | Embeddings, code chunks, summaries | ChromaDB |
| **Execution** | Agent reasoning history, learned patterns | In-memory + JSON |

---

## 🚀 Installation

### Prerequisites

- **Python** 3.10 or higher
- **Git** (for cloning repositories)
- **Ollama** (optional, for LLM support) - [Install from ollama.ai](https://ollama.ai)

### Option 1: Install from Source

```bash
git clone https://github.com/RajeshKalidandi/mike.git
cd mike
pip install -e ".[web,dev]"
```

### Option 2: Install CLI Only

```bash
git clone https://github.com/RajeshKalidandi/mike.git
cd mike
pip install -e "."
```

### Post-Installation

```bash
# Initialize system
mkdir -p ~/.mike/logs ~/.mike/output

# Optional: Download models for enhanced AI
ollama pull mxbai-embed-large
ollama pull qwen2.5-coder:14b
```

---

## 🎯 Quick Start

### 1️⃣ Scan a Codebase

```bash
# Local directory
mike scan /path/to/your/project --session-name "My Project"

# Output:
# Created session: d5634ac4-443e-4735-afa2-8cbf9cac39f0
# Found 127 files
# Scanned 127 files
```

### 2️⃣ Generate Documentation

```bash
# Generate all documentation types
mike docs <session-id> --output ./docs

# Generated files:
# ./docs/README.md
# ./docs/ARCHITECTURE.md
# ./docs/API_REFERENCE.md
# ./docs/ENV_GUIDE.md
```

### 3️⃣ Ask Questions

```bash
mike ask <session-id> "Where is authentication handled?"
mike ask <session-id> "What are the main components?"
mike ask <session-id> "How does error handling work?"
```

### 4️⃣ Analyze Code Quality

```bash
# Check for code smells and improvements
mike refactor <session-id> -f readability
mike refactor <session-id> -f security
```

---

## 💻 Usage

### Complete Workflow Example

```bash
# 1. Scan your codebase
SESSION_ID=$(mike scan ./my-project --session-name "My Project" 2>&1 | grep "Created session:" | awk '{print $3}')
echo "Session ID: $SESSION_ID"

# 2. Parse AST and build dependencies
mike parse $SESSION_ID
mike build-graph $SESSION_ID --output graph.json

# 3. Generate embeddings for semantic search
mike embed $SESSION_ID

# 4. Generate documentation
mike docs $SESSION_ID --output ./docs

# 5. Ask questions
mike ask $SESSION_ID "What are the main entry points?"

# 6. Search semantically
mike search $SESSION_ID "authentication logic"

# 7. Analyze for refactoring
mike refactor $SESSION_ID -f performance
```

### Session Management

```bash
# List all sessions
mike session list

# Get session details
mike session info <session-id>

# Delete a session
mike session delete <session-id>
```

### System Status

```bash
# Check system status
mike status

# Output:
# Mike v0.1.0
# Database: /Users/krissdev/.mike/mike.db
# Sessions: 27
# 
# Agents:
#   [✓] docs         - Documentation generation
#   [✓] qa           - Question answering
#   [✓] refactor     - Refactoring analysis
#   [✓] rebuild      - Project scaffolding
```

---

## 🌐 Web Interface

Launch the beautiful Streamlit web UI:

```bash
streamlit run src/mike/web/app.py
```

Then open http://localhost:8501 in your browser.

### Web Interface Features

- 🏠 **Home**: System overview with stats, quick actions, and recent activity
- 📤 **Upload**: 
  - Scan local directories with real-time progress
  - Upload and extract ZIP files
  - Content hashing to prevent duplicate uploads
  - File preview before creating session
- 📁 **Sessions**: 
  - Browse all sessions with filtering and sorting
  - View session statistics (files, lines, languages)
  - Delete sessions with confirmation
  - Quick load recent sessions
- 🔍 **Analysis**: 
  - Run all 4 agents with visual progress indicators
  - **Documentation Agent**: Generate README, ARCHITECTURE, API_REFERENCE, ENV_GUIDE
  - **Q&A Agent**: Ask questions with source attribution
  - **Refactor Agent**: Detect code smells with file references
  - **Rebuilder Agent**: Scaffold new projects with build plan approval
- 📊 **Visualizations**: 
  - Language distribution pie charts
  - File size bar charts
  - Interactive dependency graphs (NetworkX + Plotly)
  - Collapsible file tree browser
  - Code viewer with syntax highlighting (15+ languages)
  - Real-time execution logs
- ⚙️ **Settings**: 
  - Model configuration (provider, name, temperature)
  - Embedding model selection
  - Database and output paths
  - UI preferences (theme, line numbers, syntax highlighting)
  - System information display

### 🎨 Theme Support

Toggle between **Dark** and **Light** modes:
- Dynamic CSS generation based on theme
- Plotly charts automatically themed
- Session preference persistence
- System preference detection

### 📋 Build Plan Approval

The Rebuilder Agent now includes a **3-phase workflow**:
1. **Configure**: Set output directory and constraints
2. **Generate Plan**: Preview complete project structure
3. **Review & Approve**: 
   - View file tree with descriptions
   - See dependencies and configuration
   - Check for ambiguities and warnings
   - Approve, regenerate, or cancel
4. **Execute**: Scaffold project after approval

### 📥 Downloads

- **One-click ZIP**: Download entire generated projects
- **Individual files**: Download specific files with preview
- **Documentation**: Export generated docs as ZIP
- **Clipboard**: Copy file contents directly

### 📱 Responsive Design

Works seamlessly across devices:
- **Desktop**: Full sidebar, multi-column layouts
- **Tablet**: Adaptive grids, optimized spacing  
- **Mobile**: Collapsible navigation, touch-friendly buttons (44px+), scrollable tables

---

## 📖 CLI Reference

### Global Options

```bash
mike [OPTIONS] COMMAND [ARGS...]

Options:
  --db PATH          Database file path
  -v, --verbose      Enable verbose output
  -o, --output       Output format: plain, json, markdown
  --help             Show help message
```

### Commands

#### Core Operations

```bash
# Scan codebase
mike scan <source> [--session-name NAME]

# Parse AST
mike parse <session-id>

# Build dependency graph
mike build-graph <session-id> [--output FILE]

# Generate embeddings
mike embed <session-id> [--model MODEL]

# Search codebase
mike search <session-id> <query> [--n-results N]
```

#### Agent Commands

```bash
# Generate documentation
mike docs <session-id> [--output DIR] [--type TYPE]

# Ask questions
mike ask <session-id> <question>

# Refactoring analysis
mike refactor <session-id> [-f performance|readability|structure|security]

# Rebuild/scaffold project
mike rebuild <session-id> <output-dir>
```

#### Session Management

```bash
# List sessions
mike session list [--limit N]

# Session info
mike session info <session-id>

# Delete session
mike session delete <session-id> [--force]
```

#### System

```bash
# System status
mike status

# Telemetry
mike telemetry stats
mike telemetry report
```

---

## 🐍 Python API

### Basic Usage

```python
from mike import create_ai

# Initialize
ai = create_ai()

# Scan codebase
result = ai.scan_codebase("/path/to/project")
print(f"Session: {result.session_id}")
print(f"Files: {result.files_scanned}")

# Generate docs
docs = ai.generate_docs(result.session_id, output_dir="./docs")

# Ask questions
answer = ai.ask_question(result.session_id, "Where is auth?")
print(answer.text)
```

### Advanced Usage

```python
from mike import Mike

# With progress tracking
def on_progress(task, progress, message):
    print(f"[{task}] {int(progress*100)}%: {message}")

ai = Mike(verbose=True)
ai.add_progress_callback(on_progress)

# Full analysis
result = ai.scan_codebase("./project")
ai.parse(result.session_id)
ai.build_graph(result.session_id)
ai.embed(result.session_id)

# Run agents
ai.generate_docs(result.session_id)
refactor = ai.suggest_refactoring(result.session_id)
```

### Session Management

```python
# List sessions
sessions = ai.list_sessions(limit=10)
for session in sessions:
    print(f"{session.session_id[:8]}: {session.file_count} files")

# Get details
info = ai.get_session(session_id)
print(f"Languages: {info.languages}")

# Delete
ai.delete_session(session_id)
```

---

## 🏛️ Architecture

```
User Input → CLI → Orchestrator → Agents → Output
                    ↓
            Context Assembler
                    ↓
    Structural (Graph) + Semantic (Vector) Memory
```

### System Pipeline

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
Local Embedding Model (Ollama)
        │
        ▼
Vector Store (ChromaDB)
        │
        ▼
Code Knowledge Graph
        │
        ▼
Agent Orchestrator (LangGraph-style)
        │
        ├──── 📚 Documentation Agent
        ├──── ❓ Q&A Agent
        ├──── 🔧 Refactor Agent
        └──── 🏗️ Rebuilder Agent
        │
        ▼
Structured Output (Markdown / JSON / Code)
```

### Context Assembly Pipeline

```
Query (natural language)
        │
        ▼
Semantic Search → Top-K Chunks
        │
        ▼
Graph-Aware Expansion (callers + callees)
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

## 🛠️ Development

### Setup

```bash
git clone https://github.com/RajeshKalidandi/mike.git
cd mike
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/mike

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m e2e
```

### Code Quality

```bash
# Format
black src tests
isort src tests

# Lint
ruff check src tests

# Type check
mypy src/mike
```

### Project Structure

```
mike/
├── src/mike/
│   ├── __init__.py              # Public API exports
│   ├── api.py                   # Main API interface
│   ├── bootstrap.py             # System initialization
│   ├── cli.py                   # Command-line interface
│   ├── cli_orchestrator.py      # CLI task orchestration
│   ├── agents/                  # AI agents
│   │   ├── qa_agent.py          # Q&A Agent (825 lines)
│   │   ├── refactor_agent.py    # Refactor Agent (673 lines)
│   │   ├── rebuilder_agent.py   # Rebuilder Agent (2500+ lines)
│   │   └── patterns.py          # Pattern detection (876 lines)
│   ├── chunker/                 # Code chunking
│   ├── config/                  # Configuration management
│   ├── context/                 # Context assembly pipeline
│   ├── db/                      # Database models
│   ├── docs/                    # Documentation generation
│   ├── embeddings/              # Embedding service
│   ├── graph/                   # Dependency graph
│   ├── orchestrator/            # Agent orchestration
│   │   ├── engine.py            # Main orchestrator (983 lines)
│   │   └── state.py             # State management (434 lines)
│   ├── parser/                  # AST parsing (904 lines)
│   ├── scanner/                 # File scanning (269 lines)
│   ├── vectorstore/             # Vector database (215 lines)
│   └── web/                     # Streamlit web UI (1184 lines)
├── tests/                       # Comprehensive test suite (393 tests)
├── docs/                        # Project documentation
├── examples/                    # Usage examples
└── requirements.txt             # Dependencies
```

---

## 🎯 Milestones

| Milestone | Status | Description | Lines of Code |
|-----------|--------|-------------|---------------|
| **M1** | ✅ Complete | File scanner + language detection + AST parsing | 1,200+ |
| **M2** | ✅ Complete | Dependency graph + chunker + embeddings + vector store | 1,500+ |
| **M3** | ✅ Complete | Documentation Agent with Jinja2 templates | 500+ |
| **M4** | ✅ Complete | Q&A Agent with intent classification | 825+ |
| **M5** | ✅ Complete | Refactor Agent with code smell detection | 673+ |
| **M6** | ✅ Complete | Rebuilder Agent (basic scaffolding) | 2,500+ |
| **M7** | ✅ Complete | Streamlit frontend + full integration | 1,184+ |
| **M8** | ✅ Complete | Rebuilder Agent (full code generation) | 2,697+ |

**Web Interface Highlights:**
- 🎨 Dark/Light theme support with dynamic CSS switching
- 📋 Build Plan Approval - Preview project structure before generation
- 📥 One-click downloads - ZIP export of generated projects
- 📱 Responsive design - Works on desktop, tablet, and mobile
- 📊 Interactive visualizations - Dependency graphs, language charts
- 🖥️ Code viewer - Syntax highlighting with 15+ languages

**Total**: 8,000+ lines of production code + 467 tests

---

## 🔒 Security

- ✅ **No external API calls** - All processing is local
- ✅ **No telemetry** - No data sent to external servers  
- ✅ **Code isolation** - Rebuilder runs in sandboxed subprocess
- ✅ **Prompt injection protection** - Input sanitization built-in
- ✅ **Graph poisoning protection** - Cycle detection and limits

---

## 🙏 Acknowledgments

- [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) - AST parsing
- [Ollama](https://ollama.ai) - Local LLM hosting
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [NetworkX](https://networkx.org/) - Graph analysis
- [Streamlit](https://streamlit.io/) - Web interface

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Rajesh** - [GitHub](https://github.com/RajeshKalidandi)

---

**Built with ❤️ for the developer community**

⭐ Star this repo if you find it useful!
