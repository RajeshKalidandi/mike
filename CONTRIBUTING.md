# Contributing to Mike

Thanks for your interest in contributing! Mike is an open-source multi-agent AI system for codebase analysis.

## Quick Start

```bash
git clone https://github.com/RajeshKalidandi/mike.git
cd mike
pip install -e ".[dev]"
python3 -m pytest tests/ -v
```

## Development Workflow

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Write tests first (TDD encouraged)
4. Implement your changes
5. Run the test suite: `python3 -m pytest tests/ -v`
6. Run code quality checks: `black src tests && isort src tests && ruff check src tests`
7. Commit with conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`
8. Open a PR

## Architecture Overview

The codebase has clear layers:

- **`orchestrator/`** -- Multi-agent orchestration (planner, DAG executor, context engine, model providers, tracing)
- **`agents/`** -- 4 specialized AI agents (docs, Q&A, refactor, rebuilder)
- **`parser/`** -- Tree-sitter AST parsing for 8 languages
- **`graph/`** -- NetworkX dependency graphs
- **`embeddings/`** + **`vectorstore/`** -- Semantic search pipeline
- **`web/`** -- Streamlit web interface
- **`tui/`** -- Textual terminal UI

## What We're Looking For

- Bug fixes with tests
- New workflow templates for the TemplatePlanner
- Additional language support (Tree-sitter bindings)
- Context ranking improvements (recency, structural importance)
- Documentation improvements
- Performance optimizations with benchmarks

## Code Standards

- Python 3.10+ type hints
- No `any` types -- use proper types
- Functions under 50 lines
- Tests describe behavior: "rejects expired tokens" not "test validateToken"
- Conventional commits

## Questions?

Open an issue or start a discussion. We're friendly.
