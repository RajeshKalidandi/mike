# Execution Trace System Design Spec

**Date:** 2026-04-15
**Status:** Approved
**Scope:** Structured execution tracing for DAG-based agent orchestration

---

## 1. Problem Statement

The orchestrator now runs multi-node DAGs, but when something fails there's no structured way to see which node failed, what context it received, or what the model produced. Debugging is blind. Execution traces make every failure data.

## 2. Core Types

### NodeTrace

Captures everything about a single node's execution — input, context (exactly as the model saw it), output, timing.

```python
@dataclass
class NodeTrace:
    node_id: str
    agent_type: str
    input_query: str           # Description passed to agent
    context_snapshot: Dict     # Exact context dict as seen by agent
    model_used: str            # Model name that handled this node
    output: Optional[Dict]     # Agent result
    error: Optional[str]       # Error message if failed
    status: str                # success/failed/skipped/cancelled
    start_time: float          # time.monotonic() at start
    end_time: float            # time.monotonic() at end
    duration_ms: int
    token_estimate: int        # From ContextBundle.estimated_tokens
```

### ExecutionTrace

Wraps the full DAG lifecycle — from query to final result.

```python
@dataclass
class ExecutionTrace:
    trace_id: str              # UUID
    query: str                 # Original user query
    intent: Dict               # IntentResult serialized
    plan: Dict                 # ExecutionPlan serialized (includes reasoning)
    nodes: List[NodeTrace]     # Per-node traces in execution order
    status: str                # success/partial/failed
    total_duration_ms: int
    timestamp: str             # ISO 8601 when trace started
```

Both have `to_dict()` methods for JSON serialization.

## 3. Hook Points

Three places in the execution pipeline where tracing hooks in:

### Hook 1: After Planning (in `AgentOrchestrator.run()`)

After `strategy_router.plan()` returns, create the `ExecutionTrace` header with query, intent, and plan. Pass the trace object into `DAGExecutor.execute()`.

### Hook 2: Before Each Node (in `DAGExecutor._execute_node()`)

After `ContextEngine.build()` returns but before `agent.execute()`, snapshot:
- `input_query` = node.description
- `context_snapshot` = context_bundle.to_dict()
- `model_used` = model name from provider (or "unknown" if not available)
- `start_time` = time.monotonic()
- `token_estimate` = context_bundle.estimated_tokens

### Hook 3: After Each Node (in `DAGExecutor._execute_node()`)

After agent execution (success or failure), complete the NodeTrace:
- `output` = agent result dict
- `error` = exception message if failed
- `status` = success/failed/skipped/cancelled
- `end_time` = time.monotonic()
- `duration_ms` = computed from start/end

Append the completed NodeTrace to the ExecutionTrace.

## 4. Storage

### Format: JSONL

One file per `run()` call: `logs/traces/trace_{trace_id}.jsonl`

Structure:
- Line 1: Trace header — `{"type": "header", "trace_id": ..., "query": ..., "intent": ..., "plan": ..., "timestamp": ...}`
- Lines 2-N: Node traces — `{"type": "node", "node_id": ..., ...}`
- Last line: Summary — `{"type": "summary", "trace_id": ..., "status": ..., "total_duration_ms": ..., "node_count": ...}`

### TraceWriter

```python
class TraceWriter:
    def __init__(self, log_dir: Path = Path("./logs/traces")):
        ...

    def start_trace(self, trace: ExecutionTrace) -> Path:
        """Write trace header. Returns file path."""

    def write_node(self, trace_id: str, node_trace: NodeTrace) -> None:
        """Append node trace line."""

    def complete_trace(self, trace: ExecutionTrace) -> None:
        """Write summary line."""
```

The writer creates the `logs/traces/` directory on first use.

## 5. Trace Viewer

A `format_trace()` function for terminal output. Takes an `ExecutionTrace` and returns a formatted string:

```
=== Execution Trace: abc123 ===
Query: "Review the architecture"
Intent: architecture_review (confidence: 0.92, multi_step)
Plan: template (3 nodes) — "Using architecture_review template with 3 steps"

[1] scan (qa) ✓ 1.2s | 4200 tokens | 3 chunks
    Top chunks: main.py:1-50, router.py:10-80, config.py:1-30
[2] health (refactor) ✓ 2.1s | 3800 tokens | 2 chunks
[3] suggest (refactor) ✓ 1.8s | 5100 tokens | 4 chunks

Status: success | Total: 5.1s
```

For failed nodes:
```
[2] health (refactor) ✗ 0.3s | ERROR: Model timeout
```

For skipped/cancelled:
```
[3] verify (qa) ⊘ skipped (condition: if_suggestions_exist)
```

## 6. Integration Changes

### dag_executor.py

- `execute()` method gains optional `trace: Optional[ExecutionTrace]` parameter
- `_execute_node()` creates NodeTrace before calling agent, completes it after
- Skipped and cancelled nodes also get NodeTrace entries (with appropriate status, no context snapshot)

### engine.py

- `run()` method creates ExecutionTrace after planning
- Passes trace to `dag_executor.execute()`
- After execution, writes trace via TraceWriter
- Returns trace alongside DAGResult (add `trace` field to return or return a tuple)

Decision: Add `trace` field to `DAGResult` rather than changing the return type. This preserves backward compat.

### __init__.py

- Export `ExecutionTrace`, `NodeTrace`, `TraceWriter`, `format_trace`

## 7. File Structure

```
src/mike/orchestrator/
    trace.py             # NEW: ExecutionTrace, NodeTrace, TraceWriter, format_trace
    dag_executor.py      # MODIFY: add trace hooks
    engine.py            # MODIFY: create trace in run(), write on completion
    __init__.py          # MODIFY: export trace types
tests/unit/
    test_trace.py        # NEW: tests for trace types, writer, formatter
```

## 8. Testing Strategy

- **NodeTrace/ExecutionTrace:** Unit test creation, to_dict() serialization, all fields populated
- **TraceWriter:** Unit test with temp directory — verify JSONL format, header/node/summary structure, file creation
- **format_trace():** Unit test output contains expected markers (node ids, status symbols, timing)
- **Integration:** Test that `DAGExecutor.execute()` with trace parameter populates node traces correctly
- **Regression:** Existing DAGExecutor tests must still pass (trace parameter is optional)

## 9. Out of Scope (v1)

- SQLite storage (future, when cross-session queries needed)
- Trace-based evals (future, builds on this)
- Streaming trace updates (JSONL is append-only, so `tail -f` works naturally)
- Web UI trace viewer (CLI format_trace is enough for now)
