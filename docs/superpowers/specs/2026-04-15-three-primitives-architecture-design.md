# Three Missing Primitives: Architecture Design Spec

**Date:** 2026-04-15
**Status:** Draft
**Scope:** ContextEngine, Progressive Planning Architecture, ModelProvider Abstraction, DAG Executor

---

## 1. Problem Statement

Mike has well-built agents, parsers, and memory stores — but no connective tissue. The system is a collection of agents with a scheduler, not an orchestration system. Three primitives are missing:

1. **Planning Layer** — Nothing decides what agents to run, in what order, with what dependencies
2. **Context Layer** — `ContextAssembler` is stubbed; agents get empty context dicts
3. **Execution Graph** — No DAG, no sub-agents, no dependency resolution, no result passing

Additionally, the model layer is hardwired to Ollama with model names scattered across files.

## 2. Architecture Overview

```
User Query
    |
    v
IntentClassifier (LLM call, cheap)
    |
    v
StrategyRouter (complexity-based dispatch)
    |
    +--> simple    --> RulePlanner
    +--> multi_step --> TemplatePlanner
    +--> open_ended --> LLMPlanner (constrained composition)
    |
    v
Validated AgentDAG
    |
    v
DAGExecutor (topological, async)
    |
    +---> Agent A ---> ContextEngine.build() ---> ModelProvider.generate()
    +---> Agent B ---> ContextEngine.build() ---> ModelProvider.generate()
    |
    v
Aggregated Results
```

## 3. Primitive 1: ContextEngine

**Location:** `src/mike/orchestrator/context_engine.py` (new file, replaces stubbed `ContextAssembler`)

### 3.1 Purpose

The ContextEngine is the most impactful component. It assembles rich, token-budgeted context for each agent execution by combining three memory layers.

### 3.2 Interface

```python
@dataclass
class ContextBundle:
    """Assembled context for an agent execution."""
    query: str
    agent_type: str
    semantic_chunks: List[Dict[str, Any]]      # Vector search results
    structural_context: Dict[str, Any]          # AST nodes, graph neighbors
    execution_memory: Dict[str, Any]            # Past successes/failures
    shared_context: Dict[str, Any]              # Inter-agent state
    token_budget: int
    estimated_tokens: int
    metadata: Dict[str, Any]

class ContextEngine:
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_service: EmbeddingService,
        graph_builder: Optional[DependencyGraphBuilder] = None,
        execution_memory: Optional[ExecutionMemory] = None,
    ): ...

    def build(
        self,
        query: str,
        agent_type: str,
        session_id: str,
        token_budget: int = 8000,
        include_structural: bool = True,
        include_semantic: bool = True,
    ) -> ContextBundle: ...
```

### 3.3 Context Assembly Pipeline

**Step 1: Semantic Retrieval**
- Embed the query using `EmbeddingService`
- Search `VectorStore` for top-K chunks (K=10 default, configurable)
- Return chunks with metadata (file_path, language, line numbers, relevance score)

**Step 2: Graph-Aware Expansion**
- For each file referenced in semantic results, fetch 1-hop neighbors from `DependencyGraphBuilder`
- Include callers (predecessors) and callees (successors)
- Cap expansion at 2x the original chunk count to prevent context explosion

**Step 3: Execution Memory Injection**
- Pull failed approaches for this agent type (avoid repeating mistakes)
- Pull successful patterns (prefer what worked before)
- Pull learnings accumulated during the session

**Step 4: Token Budget Management**
- Estimate tokens: `len(json.dumps(section)) // 4` (simple heuristic, matches existing code)
- Priority order for trimming: shared_context (lowest) -> structural -> execution_memory -> semantic (highest)
- Never trim below 2 semantic chunks — that's the minimum for useful context

### 3.4 What It Replaces

The existing `ContextAssembler` class in `engine.py` (lines 309-464) becomes a thin wrapper that delegates to `ContextEngine`. This preserves backward compatibility for any code using the old interface.

---

## 4. Primitive 2: Progressive Planning Architecture (PPA)

**Location:** `src/mike/orchestrator/planner.py` (new file)

### 4.1 Purpose

Replace keyword-based `TaskRouter` with a three-tier planning system that routes based on query complexity.

### 4.2 Core Types

```python
class Complexity(str, Enum):
    SIMPLE = "simple"           # Single agent, direct answer
    MULTI_STEP = "multi_step"   # Known workflow, template-driven
    OPEN_ENDED = "open_ended"   # Novel query, LLM-composed plan

@dataclass
class IntentResult:
    intent: str                 # e.g., "architecture_review", "fix_bug", "explain_code"
    complexity: Complexity
    confidence: float           # 0.0 - 1.0
    parameters: Dict[str, Any]  # Extracted entities (file names, concepts, etc.)

@dataclass
class PlanNode:
    id: str
    agent_type: str             # Maps to AgentType enum value
    description: str            # Human-readable step description
    depends_on: List[str]       # IDs of predecessor nodes
    parameters: Dict[str, Any]  # Agent-specific params
    condition: Optional[str]    # e.g., "if_needed=True" — skip if prior step sufficient

@dataclass
class ExecutionPlan:
    nodes: List[PlanNode]
    reasoning: str              # Why this plan was chosen (explainability)
    planner_type: str           # "rule", "template", or "llm"
    estimated_duration: Optional[str]
```

### 4.3 IntentClassifier

```python
class IntentClassifier:
    def __init__(self, model_provider: ModelProvider): ...

    def classify(self, query: str) -> IntentResult: ...
```

**LLM Prompt (constrained output):**

```
Classify the following user query about a codebase.

Query: "{query}"

Respond with ONLY a JSON object:
{{
  "intent": "<one of: explain_code, find_code, architecture_review, refactor, generate_docs, rebuild_project, fix_bug, compare, general_qa>",
  "complexity": "<one of: simple, multi_step, open_ended>",
  "confidence": <float 0.0-1.0>,
  "parameters": {{<extracted entities like file names, function names, concepts>}}
}}
```

**Fallback:** If LLM fails to return valid JSON or is unavailable, fall back to keyword-based classification (preserving existing `TaskRouter` logic as the degraded path).

### 4.4 StrategyRouter

```python
class StrategyRouter:
    def __init__(
        self,
        rule_planner: RulePlanner,
        template_planner: TemplatePlanner,
        llm_planner: LLMPlanner,
    ): ...

    def plan(self, intent: IntentResult) -> ExecutionPlan:
        if intent.complexity == Complexity.SIMPLE:
            return self.rule_planner.plan(intent)
        elif intent.complexity == Complexity.MULTI_STEP:
            return self.template_planner.plan(intent)
        else:
            return self.llm_planner.plan(intent)
```

### 4.5 Three Planners

#### RulePlanner (fast path)

Direct intent-to-single-agent mapping. No DAG needed.

```python
RULES = {
    "explain_code": "qa",
    "find_code": "qa",
    "general_qa": "qa",
    "generate_docs": "docs",
}
```

Produces a single-node `ExecutionPlan`.

#### TemplatePlanner (primary path for multi-step)

Parametric workflow templates:

```python
TEMPLATES = {
    "architecture_review": [
        PlanNode(id="scan", agent_type="qa", description="Analyze codebase structure",
                 depends_on=[], parameters={"focus": "architecture"}),
        PlanNode(id="health", agent_type="refactor", description="Assess architecture health",
                 depends_on=["scan"], parameters={"focus": "health_scoring"}),
        PlanNode(id="suggest", agent_type="refactor", description="Generate improvement suggestions",
                 depends_on=["health"], parameters={"focus": "suggestions"}),
    ],
    "full_documentation": [
        PlanNode(id="scan", agent_type="qa", description="Survey codebase",
                 depends_on=[], parameters={}),
        PlanNode(id="readme", agent_type="docs", description="Generate README",
                 depends_on=["scan"], parameters={"doc_type": "readme"}),
        PlanNode(id="arch", agent_type="docs", description="Generate architecture docs",
                 depends_on=["scan"], parameters={"doc_type": "architecture"}),
        PlanNode(id="api", agent_type="docs", description="Generate API reference",
                 depends_on=["scan"], parameters={"doc_type": "api"}),
    ],
    "refactor_with_review": [
        PlanNode(id="analyze", agent_type="refactor", description="Analyze code smells",
                 depends_on=[], parameters={}),
        PlanNode(id="suggest", agent_type="refactor", description="Generate refactoring plan",
                 depends_on=["analyze"], parameters={}),
        PlanNode(id="verify", agent_type="qa", description="Verify suggestions are safe",
                 depends_on=["suggest"], parameters={"focus": "safety_check"},
                 condition="if_suggestions_exist"),
    ],
    "rebuild_project": [
        PlanNode(id="analyze", agent_type="qa", description="Understand existing architecture",
                 depends_on=[], parameters={"depth": "comprehensive"}),
        PlanNode(id="plan", agent_type="rebuild", description="Generate build plan",
                 depends_on=["analyze"], parameters={}),
        PlanNode(id="scaffold", agent_type="rebuild", description="Scaffold project",
                 depends_on=["plan"], parameters={}),
    ],
}
```

Parameters from `IntentResult.parameters` are merged into template node parameters.

#### LLMPlanner (constrained composition for open-ended queries)

**Critical constraint:** The LLM does NOT invent agents. It composes from the known set.

```python
class LLMPlanner:
    SYSTEM_PROMPT = """You are a planning engine. Given a user query about a codebase,
    create an execution plan using ONLY these available agents:

    Available agents:
    - qa: Answer questions, explain code, find code locations
    - docs: Generate documentation (README, architecture, API reference)
    - refactor: Analyze code quality, suggest improvements, detect smells
    - rebuild: Scaffold new projects, generate code, create boilerplate

    Constraints:
    - Maximum 4 steps
    - Must form a valid DAG (no cycles)
    - Each step must specify depends_on as a list of step IDs

    Respond with ONLY a JSON object:
    {{
      "reasoning": "<why this plan>",
      "steps": [
        {{"id": "<unique_id>", "agent": "<agent_type>", "description": "<what>", "depends_on": [], "parameters": {{}}}}
      ]
    }}
    """
```

**Validation:** After LLM returns a plan, validate:
1. All agent types are in the allowed set
2. `depends_on` references exist
3. Graph is acyclic (topological sort succeeds)
4. Max 4 nodes

If validation fails, fall back to TemplatePlanner with best-guess intent mapping.

### 4.6 What It Replaces

- `TaskRouter` in `engine.py` (lines 192-306) — deprecated, kept as fallback
- Keyword-matching routing logic — replaced by LLM intent classification
- The concept of "route to one agent" — replaced by "plan a DAG of agents"

---

## 5. Primitive 3: DAGExecutor

**Location:** `src/mike/orchestrator/dag_executor.py` (new file)

### 5.1 Purpose

Execute `ExecutionPlan` respecting dependencies, enabling parallel branches, result passing, and cancellation.

### 5.2 Interface

```python
@dataclass
class NodeResult:
    node_id: str
    agent_type: str
    status: str                     # "success", "failed", "skipped", "cancelled"
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    duration_ms: int

@dataclass
class DAGResult:
    plan: ExecutionPlan
    node_results: Dict[str, NodeResult]
    total_duration_ms: int
    status: str                     # "success", "partial", "failed"

class DAGExecutor:
    def __init__(
        self,
        agent_registry: AgentRegistry,
        context_engine: ContextEngine,
        max_workers: int = 4,
    ): ...

    async def execute(
        self,
        plan: ExecutionPlan,
        session_context: SessionContext,
    ) -> DAGResult: ...
```

### 5.3 Execution Algorithm

```
1. Build adjacency list from plan.nodes
2. Compute in-degree for each node
3. Initialize ready_queue with nodes that have in-degree 0
4. While ready_queue is not empty:
   a. For each node in ready_queue (parallel via asyncio.gather):
      - Build context via ContextEngine (include results from dependencies)
      - Check condition (skip if condition not met)
      - Execute agent
      - Store NodeResult
   b. For each completed node:
      - Decrement in-degree of successors
      - If successor in-degree == 0, add to ready_queue
   c. If any node failed and stop_on_failure=True, cancel remaining
5. Return DAGResult with all node results
```

### 5.4 Key Behaviors

**Result Passing:** When building context for a node, include results from all `depends_on` nodes via `shared_context`. This is how Agent B gets Agent A's output.

**Condition Evaluation:** `PlanNode.condition` is evaluated as a simple predicate against predecessor results. Supported conditions:
- `"if_suggestions_exist"` — skip if prior node returned empty suggestions
- `"if_needed=True"` — skip if prior node's result indicates no action needed
- `None` — always execute

**Cancellation:** If a node fails, nodes that transitively depend on it are marked `"cancelled"`. Independent branches continue.

**Sync Compatibility:** Provide a `execute_sync()` wrapper that runs the async executor in a new event loop, for CLI callers that aren't async.

### 5.5 What It Replaces

- `_execute_parallel()` in `engine.py` (lines 668-703) — simple thread pool
- `_execute_sequential()` in `engine.py` (lines 639-666) — for-loop execution
- `execute_batch()` in `engine.py` (lines 620-637) — mode-switching dispatch

---

## 6. Primitive 4: ModelProvider Abstraction

**Location:** `src/mike/orchestrator/model_provider.py` (new file)

### 6.1 Purpose

Decouple agent logic from model backend. Enable loading any free/open model through a unified interface.

### 6.2 Interface

```python
@dataclass
class ModelCapabilities:
    max_context: int
    supports_json_mode: bool
    supports_tool_calling: bool
    supports_streaming: bool
    is_code_specialized: bool

class ModelProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system: Optional[str] = None, **kwargs) -> str: ...

    @abstractmethod
    def generate_json(self, prompt: str, system: Optional[str] = None, **kwargs) -> Dict[str, Any]: ...

    @abstractmethod
    def capabilities(self) -> ModelCapabilities: ...

    @abstractmethod
    def model_name(self) -> str: ...
```

### 6.3 Implementations

#### OllamaProvider (day-1, primary)

```python
class OllamaProvider(ModelProvider):
    """Provider for any Ollama-hosted model (Gemma, Qwen, Llama, Mistral, etc.)."""

    def __init__(self, model: str, endpoint: str = "http://localhost:11434", **kwargs): ...
```

Wraps the existing Ollama HTTP calls from `code_generator.py` into the provider interface.

#### OpenAICompatibleProvider (day-1, secondary)

```python
class OpenAICompatibleProvider(ModelProvider):
    """Provider for OpenAI-compatible APIs (vLLM, LM Studio, Together, OpenRouter)."""

    def __init__(self, model: str, endpoint: str, api_key: Optional[str] = None, **kwargs): ...
```

Uses standard OpenAI chat completions API format. Covers vLLM, LM Studio, Together AI, OpenRouter, and actual OpenAI/Anthropic if user has keys.

### 6.4 ModelRouter (task-aware model selection)

```python
class ModelRouter:
    def __init__(self, providers: Dict[str, ModelProvider], default: str): ...

    def select(self, task_type: str, context_size: int = 0) -> ModelProvider:
        """Select best model for a task.

        Rules:
        - Code generation tasks -> code-specialized model if available
        - Large context -> model with largest context window
        - Intent classification -> fastest available model
        - Default -> configured default
        """
```

**Configuration:**

```yaml
models:
  default: "qwen2.5-coder:14b"
  providers:
    - name: "qwen-coder"
      type: "ollama"
      model: "qwen2.5-coder:14b"
      tags: ["code", "default"]
    - name: "gemma"
      type: "ollama"
      model: "gemma3:12b"
      tags: ["general", "fast"]
    - name: "llama"
      type: "openai_compatible"
      model: "llama-3.3-70b"
      endpoint: "http://localhost:8000/v1"
      tags: ["code", "large_context"]
```

### 6.5 What It Replaces

- Hardcoded `model_name: str = "gemma3:12b"` in `code_generator.py:27`
- Hardcoded `model: str = "qwen2.5-coder:14b"` in `settings.py:81`
- Direct Ollama HTTP calls scattered through agents
- The `provider` field in `LLMConfig` gets backed by actual implementations

---

## 7. Integration: Wiring It All Together

### 7.1 New Orchestrator Flow

The existing `AgentOrchestrator` class gets a new top-level method:

```python
class AgentOrchestrator:
    def __init__(self, ...):
        self.intent_classifier = IntentClassifier(model_provider)
        self.strategy_router = StrategyRouter(rule_planner, template_planner, llm_planner)
        self.dag_executor = DAGExecutor(self.registry, self.context_engine)

    def run(self, query: str) -> DAGResult:
        """Full pipeline: classify -> plan -> execute."""
        intent = self.intent_classifier.classify(query)
        plan = self.strategy_router.plan(intent)
        result = self.dag_executor.execute_sync(plan, self.state.session)
        return result
```

The existing `execute()` method remains for single-agent calls (backward compat). `run()` is the new primary entry point.

### 7.2 CLI Integration

`cli_orchestrator.py` delegates to the engine's `run()` method instead of reimplementing orchestration. The simplified orchestrator becomes a thin adapter.

### 7.3 Web/TUI Integration

Both UIs call `run()` and display:
- The plan (with reasoning) before execution
- Per-node progress during execution
- Aggregated results after completion

---

## 8. File Structure (New Files)

```
src/mike/orchestrator/
    __init__.py          # Updated exports
    engine.py            # Modified: add run(), wire new components
    state.py             # Unchanged
    context_engine.py    # NEW: ContextEngine
    planner.py           # NEW: IntentClassifier, StrategyRouter, 3 Planners
    dag_executor.py      # NEW: DAGExecutor
    model_provider.py    # NEW: ModelProvider, OllamaProvider, OpenAICompatibleProvider, ModelRouter
```

## 9. Dependencies

No new external dependencies required. Uses:
- `asyncio` (stdlib) — for DAGExecutor
- `networkx` (already installed) — for DAG validation
- `chromadb` (already installed) — via VectorStore
- `ollama` (already installed) — via OllamaProvider
- `httpx` (already installed) — via OpenAICompatibleProvider

## 10. Testing Strategy

- **ContextEngine:** Unit test with mock VectorStore and EmbeddingService. Verify token budgeting trims correctly. Integration test with real ChromaDB.
- **IntentClassifier:** Unit test with mock ModelProvider returning canned JSON. Test fallback to keyword classification.
- **TemplatePlanner:** Unit test each template produces valid DAGs. Test parameter merging.
- **LLMPlanner:** Unit test validation logic (cycle detection, allowed agents). Test fallback on invalid LLM output.
- **DAGExecutor:** Unit test topological ordering. Test parallel branch execution. Test cancellation propagation. Test condition evaluation.
- **ModelProvider:** Unit test OllamaProvider with mocked HTTP. Test ModelRouter selection logic.

## 11. Migration Path

1. New files are additive — no existing files deleted
2. `ContextAssembler` delegates to `ContextEngine` (backward compat)
3. `TaskRouter` preserved as fallback for `IntentClassifier`
4. `execute()` method unchanged; `run()` added as new entry point
5. Existing agents don't change — they receive richer context through the same `Dict[str, Any]` interface

## 12. Out of Scope (v1)

- Skills/plugin runtime loading system (future, after agents stabilize on new primitives)
- Streaming results from agents
- Multi-session agent coordination
- Agent-spawning-agent (sub-agent protocol) — DAG handles this at the planner level instead
- Model fine-tuning or adapter loading
