# CONTEXT.md
## Local AI Software Architect for Private Codebases

> **Project Codename:** Mike (working title)
> **Version:** 0.1 — Architecture Draft
> **Author:** Rajesh
> **Last Updated:** March 2026

---

## 1. What This Project Is

A fully local, offline-capable AI system that ingests any codebase or GitHub repository and produces:

- Detailed, human-readable documentation
- Architecture overviews and dependency maps
- Q&A over the codebase (natural language queries)
- Refactor suggestions and code smell detection
- The ability to scaffold and generate similar software autonomously via AI agents

No third-party APIs. No code leaves the machine. Everything runs on local models and local infrastructure.

---

## 2. Problem Being Solved

Existing tools like GitHub Copilot, Cursor, and Codeium work well but require sending code to external servers. This is a hard blocker for:

- Fintech companies
- Healthcare platforms
- Defense-adjacent software
- Any company with IP sensitivity or compliance requirements (especially in India)

Current local alternatives either stop at "smart grep" or fail to understand global architecture. This project solves the full pipeline — from raw files to architectural intelligence — without touching the cloud.

---

## 3. Core Design Philosophy

**Three principles drive every design decision:**

1. **Local-first, always.** If a component requires an external API, it is not used.
2. **Structure over prompting.** The system builds real data structures (AST, dependency graphs, knowledge graphs) rather than hoping the model infers structure from raw text.
3. **Agents are orchestrated, not free-roaming.** Each agent has a narrow, well-defined responsibility. The orchestrator controls flow.

---

## 4. System Architecture

### 4.1 Full Pipeline

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
  [File → Module → Subsystem → System]
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
        │
        ▼
Human Review & Approval
```

---

### 4.2 Memory Architecture

The system maintains **three distinct memory layers**. Most RAG systems only implement one. Missing any of them degrades agent intelligence significantly.

| Memory Type | What It Stores | Implementation |
|---|---|---|
| **Structural Memory** | AST nodes, dependency graph, import trees, function call chains | NetworkX graph + SQLite |
| **Semantic Memory** | Embeddings of code chunks, business logic summaries, doc strings | ChromaDB / Qdrant |
| **Execution Memory** | Agent reasoning steps, what was tried, what failed, iteration history | In-memory + JSON log |

Execution Memory is the most commonly skipped layer. Without it, agents repeat failed reasoning paths and have no sense of prior context within a session.

---

### 4.3 Context Assembly Pipeline

Before any agent call, context is assembled — not just retrieved. Raw vector search is insufficient for code.

```
Query (natural language or structured)
        │
        ▼
Semantic Search → Top-K Chunks
        │
        ▼
Graph-Aware Expansion
  (Fetch callers + callees of matched functions)
        │
        ▼
Hierarchical Summary Injection
  (Add module-level and system-level summaries)
        │
        ▼
Token Budget Manager
  (Trim to fit model context window)
        │
        ▼
Assembled Context → Agent
```

This is what separates "smart grep" from actual architectural understanding.

---

## 5. Agent Definitions

### 5.1 Documentation Agent

**Responsibility:** Generate documentation at every level of the hierarchy.

**Inputs:** Hierarchical summaries, AST metadata, dependency graph  
**Outputs:**
- `README.md` (project overview, setup, usage)
- `ARCHITECTURE.md` (system design, component map)
- `API_REFERENCE.md` (function signatures, params, return types)
- `ENV_GUIDE.md` (detected environment variables, config files)
- Inline docstrings (optionally patched back into source)

**Approach:** Bottom-up summarization. Summarize leaf files first, then modules, then subsystems, then the full system. Each layer summarizes the layer below it, not the raw code.

---

### 5.2 Q&A Agent

**Responsibility:** Answer natural language questions about the codebase.

**Inputs:** User query, assembled context (semantic + structural)  
**Outputs:** Plain-language explanation with file/line references

**Example queries:**
- "Where is authentication handled?"
- "What happens when a payment fails?"
- "Which files would I need to change to add a new user role?"

**Approach:** Query → semantic search → graph expansion → context assembly → LLM answer with source attribution.

---

### 5.3 Refactor Agent

**Responsibility:** Detect problems and suggest improvements.

**Inputs:** AST, dependency graph, code chunks  
**Outputs:** Ranked refactor suggestions with file references

**Detects:**
- Code smells (long functions, god classes, deep nesting)
- Circular dependencies
- Dead code (functions never called)
- Duplicated logic
- Missing error handling patterns
- Security anti-patterns (basic)

---

### 5.4 Rebuilder Agent

**Responsibility:** Generate new software inspired by the analyzed codebase.

**Inputs:** Architecture template extracted from source + new constraints from user  
**Outputs:** Scaffolded project with working code

**Workflow:**
1. Extract architecture template from analyzed codebase
2. Accept new constraints from user (e.g. "make it multi-tenant", "switch from REST to GraphQL")
3. Generate a build plan (structured, reviewed before execution)
4. Scaffold folder/file structure
5. Write code file by file
6. Self-review against plan
7. Flag ambiguities for human review
8. Iterate

**Note:** This is the hardest agent. Quality is gated by model size. Minimum recommended: **EXAONE 4.0 32B** or **Qwen3-Coder-Next**. For best results: **Kimi K2.5** or **GLM-5 (Reasoning)** — both are free to self-host and sit at #1 open-source on coding benchmarks as of Feb 2026. On smaller models (12B), use it for scaffolding + boilerplate only and rely on human review for logic-heavy code.

---

## 6. Technology Stack

All components are local, open-source, and free. No API keys. No billing. Stack reflects March 2026 benchmarks.

### 6.1 Local LLM — 2026 Best Open Source Models

The gap between open-source and proprietary models has effectively closed for coding tasks. These are the top performers as of February 2026, all self-hostable for free.

**Tier 1 — Best overall (high VRAM / server)**

| Model | SWE-bench | Context | License | Notes |
|---|---|---|---|---|
| **Kimi K2.5** | 76.8% | 256K | Open | #1 open-source on SWE-bench — best for code agents & multi-file edits |
| **GLM-5 (Reasoning)** | 91.2% (GLM-4.7) | 203K | Open | #1 overall Feb 2026 quality index — coding + reasoning |
| **DeepSeek V3.2** | 73.1% | 128K | MIT | Best MIT-licensed model, strong general + code, 37B active MoE |

**Tier 2 — Mid-size (24–48GB VRAM, practical for most setups)**

| Model | Best For | Context | License |
|---|---|---|---|
| **EXAONE 4.0 32B** | Best 32B overall, strong coding | — | Open |
| **Qwen3-Coder-Next** | Code agents, repo-level tasks | 128K | Qwen License |
| **MiMo-V2-Flash** | Fast, 256K context, hybrid reasoning | 256K | Open |
| **DeepSeek R1 Distill Llama 70B** | Deep reasoning, documentation | — | Open |

**Tier 3 — Low VRAM (runs on 12–16GB, Mac M2 Pro and above)**

| Model | Best For | VRAM |
|---|---|---|
| **Gemma 3 12B** | Fast Q&A, lightweight docs | 10GB |
| **Phi-4** | Strong reasoning, tiny footprint | 10GB |
| **Qwen3 30B A3B** | Best small MoE, punches above weight | 12GB |

> **Recommended defaults:** Use **Kimi K2.5** or **DeepSeek V3.2** for agents and code generation. Use **Gemma 3 12B** or **Phi-4** for fast Q&A on constrained hardware. Serve all via **Ollama** in dev, **vLLM** in production.

**Model serving:**

| Tool | Use Case |
|---|---|
| **Ollama** | Dev/prototyping — 3 commands, zero config, Metal support on Mac |
| **vLLM** | Production — high throughput, OpenAI-compatible API, batching |
| **llama.cpp** | Maximum control, lowest RAM via quantization |

---

### 6.2 Free Tier API Fallback (Optional, Zero Cost)

When local hardware is limited, these have generous free tiers — **no payment required**:

| Service | Free Offering | Best Use |
|---|---|---|
| **Groq** | Free tier — ultra-fast inference of open models | Fast Q&A during dev/testing |
| **Together AI** | $0.20–0.80/M tokens for top open models | Model experimentation |
| **Cerebras** | Free tier, fastest inference | Rapid prototyping |
| **Mistral (Le Chat / API)** | Free tier including Codestral | Code completion |
| **Hugging Face Inference API** | Free tier | Embedding + smaller models |

> These are **opt-in only**. The system works 100% offline without them. Use only when you need speed during early development.

---

### 6.3 Embedding Models (Free, Local)

| Model | Via | Quality | Notes |
|---|---|---|---|
| **nomic-embed-text** | Ollama | Good | Fast, reliable default |
| **mxbai-embed-large** | Ollama | Better | Higher quality retrieval |
| **BGE-M3** | Ollama / HuggingFace | Best | Multilingual, strongest overall |
| **Snowflake Arctic Embed** | HuggingFace | Good | Optimized for retrieval tasks |

> **Recommendation:** Use `mxbai-embed-large` locally. Switch to `BGE-M3` if the codebase is multilingual or for production quality.

---

### 6.4 Vector Store (Free, Open Source)

| Tool | Type | Best For |
|---|---|---|
| **ChromaDB** | Local / embedded | Dev, prototyping, small-medium repos |
| **Qdrant** | Local self-hosted | Production, large repos, rich metadata filtering |
| **LanceDB** | Local embedded | No-server option, very fast |
| **Zvec** *(Alibaba, 2026)* | Embedded in-process | "SQLite of vector databases" — perfect for local desktop tools, Apache 2.0 |
| **Weaviate** | Self-hosted | Hybrid search (vector + keyword) |

> **Recommendation:** Start with `ChromaDB` for M1–M4. Migrate to `Qdrant` for production. Watch **Zvec** — it's brand new (Feb 2026), Apache 2.0, and designed exactly for on-device RAG with no external server dependency.

---

### 6.5 Code Analysis & AST (Free, Open Source)

| Tool | Purpose |
|---|---|
| **Tree-sitter** | AST parsing — 40+ languages, battle-tested |
| **ast-grep** | Pattern matching across AST nodes |
| **Semgrep (OSS)** | Code smell detection, security patterns, free tier |
| **NetworkX** | Dependency graph — Python-native, no setup |
| **Graphviz** | Visualize dependency graphs in docs |

---

### 6.6 Agent Frameworks (Free, Open Source)

| Framework | Why Use It |
|---|---|
| **LangGraph** | Best for controlled multi-step agent loops. Explicit state machine. |
| **CrewAI** | Simpler multi-agent setup. Good for Documentation + Q&A agents. |
| **Smolagents (HuggingFace)** | Lightweight, minimal, great for fast prototyping |
| **AutoGen (Microsoft)** | Strong for code execution loops in Rebuilder Agent |

> **Recommendation:** Use `LangGraph` as the orchestrator backbone. Use `CrewAI` patterns for the Documentation and Q&A agents. Use `AutoGen` patterns for the Rebuilder Agent's code-write-test-fix loop.

---

### 6.7 Supporting Stack (All Free)

| Layer | Tool | Notes |
|---|---|---|
| Language Detection | `linguist` / `guesslang` | Auto-detect language per file |
| Chunking | `langchain-text-splitters` | AST-aware chunking |
| Storage | SQLite + flat files | Zero-dependency persistence |
| Frontend v1 | **Streamlit** | Ship UI in hours |
| Frontend v2 | **Gradio** or React | Gradio for ML-native UI, React for polish |
| Monitoring | **AgentOps (free tier)** | Track agent runs, costs, failures |
| Dev Environment | **Continue.dev** | Free VSCode plugin — use this project to build itself |

---

## 7. Supported Languages (Phase 1)

Tree-sitter supports most of these out of the box.

- Python
- JavaScript / TypeScript
- Go
- Java
- Rust
- C / C++
- Ruby
- PHP

Languages are auto-detected via file extension + content heuristics.

---

## 8. What Is Not In Scope (v1)

To ship a working v1, these are explicitly out of scope:

- Real-time indexing (no file watcher — upload and re-process)
- Multi-user collaboration
- Cloud sync or remote model serving
- Notebook support (.ipynb)
- Binary or compiled code analysis
- Security vulnerability scanning (this is not a SAST tool)

---

## 9. Hardware Requirements

| Use Case | Minimum | Recommended |
|---|---|---|
| Documentation + Q&A | 16GB RAM, 8GB VRAM | 32GB RAM, 16GB VRAM |
| Refactor Agent | 16GB RAM, 8GB VRAM | 32GB RAM, 24GB VRAM |
| Rebuilder Agent (full) | 32GB RAM, 24GB VRAM | 64GB RAM, 48GB VRAM (A100 class) |
| Mac (Apple Silicon) | M2 Pro 16GB (usable) | M3 Max / M4 Max (strong) |

Apple Silicon is well-supported via Ollama's Metal backend. For the Rebuilder Agent at full capacity, a Mac Studio M4 Ultra or a machine with an RTX 4090 / A6000 is the realistic target.

---

## 10. Key Technical Risks

**Risk 1: Context window overflow on large repos**
Large codebases (500k+ LOC) will exceed any model's context window during summarization. Mitigation: hierarchical summarization ensures no single pass exceeds the window. Each layer summarizes the layer below — not the raw code.

**Risk 2: Model quality floor for Rebuilder Agent**
Sub-14B models produce structurally correct but logically shallow code. The Rebuilder Agent should enforce a minimum model size requirement and warn the user if they're below it.

**Risk 3: AST parsing failures on mixed/unusual syntax**
Tree-sitter handles most cases but fails on heavily templated, generated, or obfuscated code. Mitigation: graceful fallback to line-based chunking when AST parsing fails, with a warning logged.

**Risk 4: Graph retrieval latency at scale**
Very large dependency graphs (millions of nodes) will slow graph-aware context expansion. Mitigation: index the graph with an adjacency cache, limit expansion depth to 2 hops by default.

---

## 11. Project Milestones

| Milestone | Deliverable | Status |
|---|---|---|
| M1 | File scanner + language detection + AST parsing | Not started |
| M2 | Dependency graph + chunker + embeddings + vector store | Not started |
| M3 | Documentation Agent (working, local) | Not started |
| M4 | Q&A Agent (working, local) | Not started |
| M5 | Refactor Agent | Not started |
| M6 | Rebuilder Agent (basic scaffolding) | Not started |
| M7 | Streamlit frontend + full pipeline integration | ✅ Completed |

**M7 Implementation Summary (March 2026):**

The M7 Streamlit frontend has been fully implemented with the following features:

**UI Components:**
- **Multi-page navigation**: Home, Upload, Sessions, Analysis, Visualizations, Settings
- **Theme Support**: Full dark/light mode with CSS variables and chart theming
- **Build Plan Approval**: 3-phase workflow for Rebuilder Agent (Configure → Plan → Approve → Execute)
- **Download System**: ZIP generation, individual file downloads, clipboard copy
- **Responsive Design**: Mobile-friendly layouts, touch targets, adaptive grids

**Pages Implemented:**
- **Home**: System overview, quick stats, recent sessions
- **Upload**: Directory and ZIP file upload with progress tracking
- **Sessions**: Session management, filtering, sorting, deletion
- **Analysis**: All 4 agents (Docs, Q&A, Refactor, Rebuilder) with progress indicators
- **Visualizations**: Language charts, file trees, dependency graphs, code viewer
- **Settings**: Full configuration panel with model, paths, and UI settings

**Technical Features:**
- **Session State Management**: Persistent settings, logs, current session tracking
- **Progress Indicators**: Real-time progress bars for all agent operations
- **Error Handling**: Graceful error display and logging
- **File Browser**: Interactive file tree with syntax-highlighted code viewer
- **Charts**: Plotly-based visualizations with theme support
- **Content Hashing**: Deduplication for uploaded codebases

**Files Added/Modified:**
- `src/mike/web/app.py` (1,187 lines) - Main application
- `src/mike/web/components.py` (634 lines) - UI components
- `src/mike/web/utils.py` (535 lines) - Utilities and helpers
- `src/mike/web/theme_utils.py` (480 lines) - Theme system
- `tests/web/test_web_components.py` (37 tests) - Comprehensive test suite
- `requirements.txt` - Added streamlit, plotly, pandas, networkx
| M8 | Rebuilder Agent (full code generation loop) | ✅ Completed |

---

## 12. Positioning

**This is not:**
- A code search tool
- A chatbot that reads files
- A wrapper around GPT-4

**This is:**
> A local AI software architect that understands your codebase at structural, semantic, and architectural levels — and can generate new software from that understanding, entirely on your hardware.

**Target customers (India-first):**
- Fintech startups that cannot send code to OpenAI
- Enterprise engineering teams with IP sensitivity
- Defense and government tech contractors
- Any team that has been told "no cloud AI" by legal or compliance

---

## 13. Session Boundary Definition

**What constitutes a session:**
- A session begins when a user uploads a codebase (repo/folder/ZIP) and ends when:
  - The user explicitly ends it via UI/command
  - 30 minutes of inactivity (configurable)
  - Process termination

**What gets cleared vs persisted:**
- **Cleared**: Execution Memory (agent reasoning history, iteration logs), in-memory caches
- **Persisted**: Structural Memory (NetworkX graph), Semantic Memory (vector store), processed metadata
- **Content Hash Strategy**: SHA-256 hash of file tree + content. If same codebase is re-uploaded, skip re-ingestion entirely. Hash stored in SQLite with timestamp.
- **Session UUID Namespacing**: All data scoped to `{session_uuid}/` prefix in storage. Enables multiple concurrent sessions without collision.

## 14. Monorepo Handling

**Detection Logic:**
- Look for workspace markers: `package.json` (workspaces), `pom.xml`, `Cargo.toml` (workspace), `go.work`, `pyproject.toml`
- Heuristic: Multiple root-level directories with their own dependency files
- Config file: `.mike/config.json` for explicit monorepo boundaries

**Per-Sub-Project Indexing:**
- Each detected sub-project gets its own namespace in vector store
- Dependency graph maintains cross-project edges with `project:` prefix
- Agents default to single-project scope unless query explicitly requests cross-project

**v1 Limitations:**
- Build system coupling (Gradle, Bazel) not automatically resolved
- Cross-language calls within monorepo traced only via file references, not deep semantic analysis

## 15. Testing Strategy

**Three-Layer Approach:**

1. **Deterministic Unit Tests** (pytest)
   - AST parsing correctness on known code samples
   - Dependency graph construction from fixtures
   - Chunking logic with edge cases (empty files, binary, unicode)

2. **Structural Integration Tests**
   - End-to-end pipeline on test repos (small, medium, large)
   - Verify vector store population, graph completeness
   - Performance benchmarks: ingestion time < 1 min per 10k LOC

3. **Human-Reviewed E2E Evaluation**
   - Documentation Agent output rated by humans (1-5 scale)
   - Q&A accuracy on curated question set
   - Regression baseline: frozen test repos with expected outputs

## 16. Security Considerations

**Code Execution Isolation:**
- Rebuilder Agent runs in sandboxed subprocess (Firejail on Linux, sandbox-exec on macOS)
- No network access during code generation
- Generated code scanned for common patterns (eval, exec, subprocess) before display

**Prompt Injection Mitigation:**
- All user inputs sanitized before embedding in system prompts
- Structured output schemas validated with Pydantic
- Model temperature = 0 for critical operations (graph building, doc generation)

**Graph Poisoning Protection:**
- Cycle detection in dependency graph (fails fast on circular imports)
- Max node/edge limits to prevent DoS via crafted codebase
- Rate limiting on agent iterations per session

**Model Server Security:**
- Ollama binds to localhost only (never exposed externally)
- No telemetry, no external connections during operation
- All data stays in user-controlled directories

## 17. Open Questions

These need decisions before or during M1–M3:

1. ~~Should the vector store and graph be persistent across sessions, or rebuilt on each upload?~~ **Resolved**: Persisted with content hash deduplication (Section 13)
2. ~~What is the minimum viable output format for the Documentation Agent — Markdown only, or also HTML and PDF?~~ **Resolved**: Markdown v1, HTML/PDF v2
3. ~~Should the Rebuilder Agent require human approval at each step, or run autonomously with a final review?~~ **Resolved**: Human approval at plan generation, autonomous execution with final review
4. ~~How do we handle monorepos with multiple languages and frameworks in a single upload?~~ **Resolved**: Section 14
5. What is the rollout strategy — CLI tool first, or web UI from day one?

---

*This document is the single source of truth for project architecture and design intent. Update it as decisions are made.*
