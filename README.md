<div align="center">

# Mike - AI Software Architect

### The open-source, fully local multi-agent system that understands your entire codebase

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-739%20passing-brightgreen.svg)](./tests)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

**No API keys. No cloud. No data leaves your machine.**
Works with any open model: Gemma, Qwen, Llama, Mistral, DeepSeek, and more.

[Getting Started](#-getting-started) | [How It Works](#-how-it-works) | [Web UI](#-web-interface) | [Python API](#-python-api) | [Contributing](#-contributing)

</div>

---

## Why Mike?

Most "AI code tools" are wrappers around a single LLM call. Mike is different.

Mike is a **multi-agent orchestration system** that scans your entire codebase, builds a knowledge graph, and coordinates specialized AI agents to answer questions, generate docs, find bugs, and scaffold new projects.

**What makes it real multi-agent (not fake):**
- A **planning layer** that decides which agents to run and in what order
- A **context engine** that gives each agent exactly the right code context
- A **DAG executor** that runs agents in parallel with dependency resolution
- **Execution traces** so you can see exactly what each agent did and why

> "Most multi-agent systems are just `for agent in agents: agent.run()`. Mike has actual orchestration." 

---

## What Can Mike Do?

```bash
# Scan any codebase (local dir, git repo, or ZIP)
mike scan ./your-project --session-name "My App"

# Ask questions in plain English
mike ask <session> "Where is authentication handled?"
mike ask <session> "What are the main entry points?"
mike ask <session> "How does error handling work?"

# Generate full documentation
mike docs <session> --output ./docs

# Find code smells and security issues  
mike refactor <session> -f security
mike security <session> --format sarif

# Scaffold a new project from existing architecture
mike rebuild <session> ./new-project

# Architecture health scoring
mike health <session> --format markdown

# Git intelligence (churn, hotspots, contributors)
mike git analyze . --since-days 90
```

---

## Key Features

### Multi-Agent Orchestration (Real, Not Fake)

Mike doesn't just call one model. It plans, decomposes, and coordinates:

```
User Query
    |
    v
Intent Classifier (LLM) --> "architecture_review" + "multi_step"
    |
    v
Strategy Router --> TemplatePlanner
    |
    v
Execution Plan (DAG):
    [scan] --> [health] --> [suggest]
      |                       |
      +--> [docs] (parallel)  +--> [verify] (conditional)
    |
    v
DAG Executor (async, parallel branches, cancellation)
    |
    v
Aggregated Results + Execution Trace (JSONL)
```

**Progressive Planning Architecture (PPA):**
- Simple queries --> direct agent routing (fast)
- Known workflows --> parametric templates (reliable)
- Novel queries --> LLM-composed plans with constraints (flexible)

### 4 Specialized AI Agents

| Agent | What It Does |
|-------|-------------|
| **Documentation** | Generates README, architecture guides, API reference, env guides |
| **Q&A** | Answers questions with source attribution and confidence scores |
| **Refactor** | Detects code smells, security issues, complexity, performance problems |
| **Rebuilder** | Scaffolds entire projects from architecture templates with approval workflow |

### Works With Any Open Model

Mike uses a **ModelProvider abstraction** that works with any model backend:

| Backend | Models | Setup |
|---------|--------|-------|
| **Ollama** (default) | Gemma 3, Qwen 2.5 Coder, Llama 3.3, Mistral, DeepSeek Coder, CodeLlama | `ollama pull qwen2.5-coder:14b` |
| **OpenAI-compatible** | Any model via vLLM, LM Studio, Together AI, OpenRouter | Point to your endpoint |
| **Local GGUF** | Any model via llama.cpp / Ollama | Pull or load locally |

```python
# Use any model
from mike.orchestrator import OllamaProvider, OpenAICompatibleProvider

# Ollama (default)
provider = OllamaProvider(model="gemma3:12b")

# vLLM / LM Studio / any OpenAI-compatible API
provider = OpenAICompatibleProvider(
    model="llama-3.3-70b",
    endpoint="http://localhost:8000/v1"
)
```

### Three-Layer Memory Architecture

| Layer | What It Stores | Technology |
|-------|---------------|------------|
| **Structural** | AST nodes, dependency graphs, import trees | Tree-sitter + NetworkX + SQLite |
| **Semantic** | Code embeddings, chunks, summaries | ChromaDB + Ollama embeddings |
| **Execution** | Agent reasoning history, learned patterns, failure memory | In-memory + JSON |

### Context Engine (The Secret Sauce)

> Context quality matters more than model quality.

Mike's ContextEngine assembles rich, token-budgeted context for every agent call:

1. **Semantic retrieval** -- embed query, search vector store for relevant code chunks
2. **Graph-aware expansion** -- fetch callers and callees of relevant files
3. **Execution memory** -- inject past successes/failures to avoid repeating mistakes
4. **Token budget management** -- trim context to fit model window with priority-based pruning

### Execution Traces (Debuggable AI)

Every pipeline run produces a structured JSONL trace:

```
=== Execution Trace: a1b2c3d4 ===
Query: "Review the architecture"
Intent: architecture_review (confidence: 0.92, multi_step)
Plan: template (3 nodes) -- "Using architecture_review template"

[1] scan (qa)      OK  1.2s | 4200 tokens | 3 chunks
[2] health (refactor) OK  2.1s | 3800 tokens | 2 chunks
[3] suggest (refactor) OK  1.8s | 5100 tokens | 4 chunks

Status: success | Total: 5.1s
```

Each node trace captures the **exact context the model saw** -- not references, not IDs, the actual prompt context. When a node hallucinates, you can see exactly why.

### 8-Language Support

Deep AST analysis via Tree-sitter for:

Python | JavaScript/TypeScript | Go | Java | Rust | C/C++ | Ruby | PHP

### Architecture Health Scoring

7-dimension health assessment:

- Coupling analysis (fan-in/fan-out)
- Cohesion scoring (LCOM)
- Circular dependency detection
- Cyclomatic complexity
- Layer violation detection
- Dead code identification
- Test coverage integration

### Security Scanning

Pattern-based vulnerability detection:

- Secrets (API keys, passwords, tokens)
- Injection vulnerabilities (SQL, command, code)
- Cryptographic issues
- SARIF export for CI/CD integration

### Git Intelligence

Repository analytics:

- Code churn tracking
- Hotspot detection (high-frequency change areas)
- Bug-prone file identification
- Contributor statistics
- Rework rate analysis

---

## Getting Started

### Prerequisites

- **Python 3.10+**
- **Ollama** (recommended) -- [Install from ollama.ai](https://ollama.ai)

### Install

```bash
git clone https://github.com/RajeshKalidandi/mike.git
cd mike
pip install -e ".[web,dev]"

# Pull a model (pick one)
ollama pull qwen2.5-coder:14b    # Best for code tasks
ollama pull gemma3:12b            # Good general purpose
ollama pull mxbai-embed-large     # For embeddings
```

### First Run

```bash
# Scan a project
mike scan ./your-project --session-name "My App"
# Output: Created session: d5634ac4-...

# Ask a question
mike ask d5634ac4 "What does this project do?"

# Generate docs
mike docs d5634ac4 --output ./docs

# Launch web UI
streamlit run src/mike/web/app.py
```

---

## How It Works

### System Architecture

```
User Query
    |
    v
Intent Classifier (LLM-powered, keyword fallback)
    |
    v
Strategy Router
    |
    +--> RulePlanner (simple queries)
    +--> TemplatePlanner (known workflows)  
    +--> LLMPlanner (novel queries, constrained composition)
    |
    v
Validated Agent DAG
    |
    v
DAG Executor (Kahn's algorithm, async parallel)
    |
    +---> Agent A ---> ContextEngine.build() ---> ModelProvider.generate()
    +---> Agent B ---> ContextEngine.build() ---> ModelProvider.generate()
    |
    v
Aggregated Results + Execution Trace (JSONL)
```

### The Orchestration Pipeline

1. **Intent Classification** -- LLM classifies the query (explain, refactor, document, etc.) with complexity level (simple/multi-step/open-ended)

2. **Progressive Planning** -- Based on complexity:
   - Simple --> single agent, direct routing
   - Multi-step --> parametric workflow template (5 built-in templates)
   - Open-ended --> LLM composes a plan from the known agent set (constrained, max 4 nodes)

3. **DAG Execution** -- Kahn's algorithm with:
   - Parallel branch execution (asyncio.gather)
   - Result passing between dependent nodes
   - Conditional execution (skip nodes based on predecessor output)
   - Cancellation propagation (failed node cancels dependents, independent branches continue)

4. **Context Assembly** -- Per-node, the ContextEngine builds rich context:
   - Semantic search (embed query, search ChromaDB)
   - Graph expansion (1-hop neighbors via NetworkX)
   - Execution memory (avoid past failures)
   - Token budgeting (priority-based trimming)

5. **Trace Capture** -- Full JSONL trace of every step for debugging and evaluation

### Data Pipeline

```
Source Code --> File Scanner --> AST Parser (Tree-sitter)
    |                              |
    v                              v
Language Detection          Dependency Graph (NetworkX)
    |                              |
    v                              v
Code Chunker -----------> Embedding Model (Ollama)
                                   |
                                   v
                          Vector Store (ChromaDB)
                                   |
                                   v
                          Context Engine (retrieval + expansion + budgeting)
                                   |
                                   v
                          Agent Orchestrator (planning + DAG execution)
```

---

## Web Interface

Launch the Streamlit web UI:

```bash
streamlit run src/mike/web/app.py
```

**10 pages:**

| Page | What It Does |
|------|-------------|
| Home | System overview, stats, recent activity |
| Upload | Scan directories, upload ZIPs, clone git repos |
| Sessions | Browse, filter, delete analysis sessions |
| Analysis | Run all 4 agents with visual progress |
| Visualizations | Dependency graphs, language charts, file trees |
| Health | 7-dimension architecture health scoring |
| Security | Vulnerability detection with SARIF export |
| Git Analytics | Code churn, hotspots, contributor stats |
| Patches | Refactoring suggestions with preview and rollback |
| Settings | Model config, database paths, UI preferences |

Dark/light theme support. Responsive design (desktop, tablet, mobile).

---

## Python API

```python
from mike import Mike

ai = Mike()

# Scan and analyze
session = ai.scan_codebase("./my-project")

# Ask questions
answer = ai.ask_question(session.session_id, "How does auth work?")
print(answer.text)
print(answer.sources)  # File:line references

# Generate docs
ai.generate_docs(session.session_id, output_dir="./docs")

# Refactoring suggestions
suggestions = ai.suggest_refactoring(session.session_id)

# Scaffold new project
ai.rebuild_project(session.session_id, output_dir="./new-project")
```

### Using the Orchestrator Directly

```python
from mike.orchestrator import (
    AgentOrchestrator, OllamaProvider, ContextEngine,
    IntentClassifier, StrategyRouter, RulePlanner,
    TemplatePlanner, LLMPlanner, DAGExecutor, format_trace,
)

# Set up the full pipeline
provider = OllamaProvider(model="qwen2.5-coder:14b")
context_engine = ContextEngine(vector_store=vs, embedding_service=es)
classifier = IntentClassifier(provider)
router = StrategyRouter(
    rule_planner=RulePlanner(),
    template_planner=TemplatePlanner(),
    llm_planner=LLMPlanner(provider),
)

orchestrator = AgentOrchestrator()
orchestrator.intent_classifier = classifier
orchestrator.strategy_router = router
orchestrator.context_engine = context_engine
orchestrator.dag_executor = DAGExecutor(
    agent_registry=orchestrator.registry,
    context_engine=context_engine,
)

# Run a query through the full pipeline
result = orchestrator.run("Review the architecture of this project")

# Print the execution trace
print(format_trace(result.trace))
```

---

## CLI Reference

```bash
mike scan <source> [--session-name NAME]        # Scan codebase
mike parse <session-id>                          # Parse AST
mike build-graph <session-id>                    # Build dependency graph
mike embed <session-id>                          # Generate embeddings
mike search <session-id> <query>                 # Semantic search
mike docs <session-id> [--output DIR]            # Generate documentation
mike ask <session-id> <question>                 # Ask questions
mike refactor <session-id> [-f FOCUS]            # Refactoring analysis
mike rebuild <session-id> <output-dir>           # Scaffold project
mike health <session-id>                         # Health scoring
mike security <source> [--format sarif]          # Security scan
mike git analyze <source>                        # Git analytics
mike session list                                # List sessions
mike status                                      # System status
```

---

## Project Structure

```
mike/
  src/mike/
    orchestrator/           # Multi-agent orchestration engine
      engine.py             # AgentOrchestrator with run() pipeline
      planner.py            # Progressive Planning Architecture (3-tier)
      dag_executor.py       # DAG execution with Kahn's algorithm
      context_engine.py     # Semantic retrieval + graph expansion + token budgeting
      model_provider.py     # ModelProvider abstraction (Ollama, OpenAI-compatible)
      trace.py              # Structured execution tracing (JSONL)
      state.py              # Session and execution state management
    agents/                 # 4 specialized AI agents
    parser/                 # Tree-sitter AST parsing (8 languages)
    graph/                  # Dependency graph (NetworkX)
    embeddings/             # Embedding service (Ollama)
    vectorstore/            # Vector database (ChromaDB)
    security/               # Vulnerability scanning
    health/                 # Architecture health scoring
    git/                    # Git analytics
    patch/                  # Safe code modification with rollback
    web/                    # Streamlit web interface (10 pages)
    tui/                    # Terminal UI (Textual)
    config/                 # Configuration management (Pydantic v2)
    db/                     # SQLite database models
    cache/                  # DiskCache for AST, embeddings, graphs
    monitoring/             # Telemetry and metrics
  tests/                    # 739+ tests
  docs/                     # Documentation and specs
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| AST Parsing | Tree-sitter (8 language bindings) |
| Dependency Graphs | NetworkX |
| Vector Database | ChromaDB |
| LLM Integration | Ollama + OpenAI-compatible API |
| Database | SQLite |
| Configuration | Pydantic v2 |
| Web UI | Streamlit + Plotly |
| Terminal UI | Textual |
| Caching | DiskCache |
| HTTP Client | httpx |
| Git Analysis | GitPython |

---

## Comparison With Other Tools

| Feature | Mike | Cursor/Copilot | Aider | SWE-Agent |
|---------|------|---------------|-------|-----------|
| Fully local / offline | Yes | No | No | No |
| Multi-agent orchestration | Yes (DAG) | No | No | Partial |
| Codebase-wide understanding | Yes | File-level | File-level | Repo-level |
| Architecture health scoring | Yes | No | No | No |
| Security scanning | Yes | No | No | No |
| Dependency graph analysis | Yes | No | No | No |
| Works with any open model | Yes | GPT/Claude only | GPT/Claude | GPT/Claude |
| Execution traces | Yes | No | No | No |
| Web UI + CLI + Python API | All three | IDE only | CLI only | CLI only |
| Free and open source | MIT | Paid | Free/Paid | MIT |

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Setup development environment
git clone https://github.com/RajeshKalidandi/mike.git
cd mike
pip install -e ".[dev]"

# Run tests
python3 -m pytest tests/ -v

# Code quality
black src tests && isort src tests && ruff check src tests
```

---

## Roadmap

- [x] Multi-agent orchestration with DAG execution
- [x] Progressive Planning Architecture (3-tier)
- [x] Context Engine with semantic retrieval and graph expansion
- [x] ModelProvider abstraction (any open model)
- [x] Execution traces (JSONL)
- [ ] Feedback loop (query -> plan -> outcome storage for self-improvement)
- [ ] Skills/plugin system (runtime-loadable agent capabilities)
- [ ] Streaming results from agents
- [ ] Context ranking improvements (recency, structural importance)
- [ ] Multi-repo analysis

---

## Star History

If Mike helps you understand or improve your codebase, consider giving it a star. It helps others discover the project.

---

## License

MIT License -- see [LICENSE](LICENSE) for details.

## Author

**Rajesh Kalidandi** -- [GitHub](https://github.com/RajeshKalidandi)

---

<div align="center">

**Built for developers who want AI that actually understands their code.**

[Star this repo](https://github.com/RajeshKalidandi/mike) | [Report an issue](https://github.com/RajeshKalidandi/mike/issues) | [Contribute](CONTRIBUTING.md)

</div>
