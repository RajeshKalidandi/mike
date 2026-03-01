# ArchitectAI

A fully local, offline-capable AI system for codebase analysis and architecture intelligence.

## Overview

ArchitectAI ingests any codebase or GitHub repository and produces:

- Detailed, human-readable documentation
- Architecture overviews and dependency maps
- Q&A over the codebase (natural language queries)
- Refactor suggestions and code smell detection
- Autonomous software generation via AI agents

**No third-party APIs. No code leaves the machine.**

## Features

- 🔒 **100% Local** - All processing happens on your hardware
- 📊 **Code Analysis** - AST parsing and dependency graph construction
- 🧠 **AI-Powered** - Uses local LLMs for intelligent analysis
- 📝 **Auto-Documentation** - Generates comprehensive documentation
- 🔍 **Smart Q&A** - Ask questions about your codebase in natural language
- 🏗️ **Code Generation** - Scaffold new projects based on analyzed patterns

## Quick Start

### Prerequisites

- Python 3.10+
- Local LLM server (Ollama recommended)

### Installation

```bash
pip install -e .
```

### Development Setup

```bash
pip install -e ".[dev]"
```

### Usage

```bash
# Analyze a local repository
architectai analyze /path/to/repo

# Start interactive Q&A session
architectai chat /path/to/repo

# Generate documentation
architectai docs /path/to/repo --output ./docs
```

## Supported Languages

- Python
- JavaScript / TypeScript
- Go
- Java
- Rust
- C / C++
- Ruby
- PHP

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design.

## License

MIT License - See LICENSE file for details.
