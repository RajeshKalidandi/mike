# Execution Trace System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add structured JSONL execution tracing to the DAG orchestrator so every pipeline run captures intent, plan, per-node context snapshots, outputs, and timing.

**Architecture:** One new file (`trace.py`) with dataclasses + writer + formatter. Two modified files (`dag_executor.py` adds trace hooks, `engine.py` creates/writes trace in `run()`). Trace is optional — all existing behavior unchanged when trace is not passed.

**Tech Stack:** Python 3.10+, dataclasses, json, pathlib (all stdlib)

**Spec:** `docs/superpowers/specs/2026-04-15-execution-trace-design.md`

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `src/mike/orchestrator/trace.py` | NodeTrace, ExecutionTrace, TraceWriter, format_trace |
| Create | `tests/unit/test_trace.py` | Unit tests for trace types, writer, formatter |
| Modify | `src/mike/orchestrator/dag_executor.py` | Add trace hooks to execute() and _execute_node() |
| Modify | `src/mike/orchestrator/engine.py:620-679` | Create trace in run(), write on completion, attach to DAGResult |
| Modify | `src/mike/orchestrator/dag_executor.py:32-36` | Add optional `trace` field to DAGResult |
| Modify | `src/mike/orchestrator/__init__.py` | Export trace types |
| Create | `tests/unit/test_trace_integration.py` | Integration test: DAGExecutor with tracing |

---

## Task 1: Trace Data Types + TraceWriter + format_trace

**Files:**
- Create: `src/mike/orchestrator/trace.py`
- Create: `tests/unit/test_trace.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_trace.py
"""Unit tests for execution trace system."""

import json
import os
import tempfile
import time
import pytest
from pathlib import Path

from mike.orchestrator.trace import (
    NodeTrace,
    ExecutionTrace,
    TraceWriter,
    format_trace,
)


class TestNodeTrace:
    def test_create(self):
        nt = NodeTrace(
            node_id="scan", agent_type="qa",
            input_query="Analyze codebase structure",
            context_snapshot={"semantic_chunks": [{"content": "def main(): pass"}]},
            model_used="qwen2.5-coder:14b",
            output={"status": "success", "answer": "The codebase uses MVC"},
            error=None, status="success",
            start_time=100.0, end_time=101.2,
            duration_ms=1200, token_estimate=4200,
        )
        assert nt.node_id == "scan"
        assert nt.duration_ms == 1200

    def test_to_dict(self):
        nt = NodeTrace(
            node_id="a", agent_type="qa", input_query="q",
            context_snapshot={}, model_used="gemma",
            output=None, error="boom", status="failed",
            start_time=0, end_time=1, duration_ms=1000, token_estimate=0,
        )
        d = nt.to_dict()
        assert d["node_id"] == "a"
        assert d["error"] == "boom"
        assert "context_snapshot" in d

    def test_failed_node_trace(self):
        nt = NodeTrace(
            node_id="x", agent_type="refactor", input_query="fix it",
            context_snapshot={"chunks": []}, model_used="gemma",
            output=None, error="timeout", status="failed",
            start_time=0, end_time=0.3, duration_ms=300, token_estimate=500,
        )
        assert nt.status == "failed"
        assert nt.output is None

    def test_skipped_node_trace(self):
        nt = NodeTrace(
            node_id="y", agent_type="qa", input_query="verify",
            context_snapshot={}, model_used="",
            output=None, error=None, status="skipped",
            start_time=0, end_time=0, duration_ms=0, token_estimate=0,
        )
        assert nt.status == "skipped"


class TestExecutionTrace:
    def test_create(self):
        trace = ExecutionTrace(
            trace_id="abc-123",
            query="Review the architecture",
            intent={"intent": "architecture_review", "complexity": "multi_step"},
            plan={"nodes": [{"id": "scan"}], "reasoning": "template"},
            nodes=[],
            status="pending",
            total_duration_ms=0,
            timestamp="2026-04-15T12:00:00",
        )
        assert trace.trace_id == "abc-123"
        assert trace.query == "Review the architecture"

    def test_to_dict(self):
        trace = ExecutionTrace(
            trace_id="t1", query="test",
            intent={}, plan={}, nodes=[], status="success",
            total_duration_ms=500, timestamp="2026-04-15T12:00:00",
        )
        d = trace.to_dict()
        assert d["trace_id"] == "t1"
        assert d["total_duration_ms"] == 500

    def test_add_node_trace(self):
        trace = ExecutionTrace(
            trace_id="t1", query="test",
            intent={}, plan={}, nodes=[], status="pending",
            total_duration_ms=0, timestamp="2026-04-15T12:00:00",
        )
        nt = NodeTrace(
            node_id="a", agent_type="qa", input_query="q",
            context_snapshot={}, model_used="gemma",
            output={"answer": "yes"}, error=None, status="success",
            start_time=0, end_time=1, duration_ms=1000, token_estimate=100,
        )
        trace.nodes.append(nt)
        assert len(trace.nodes) == 1

    def test_to_dict_includes_node_traces(self):
        nt = NodeTrace(
            node_id="a", agent_type="qa", input_query="q",
            context_snapshot={}, model_used="gemma",
            output=None, error=None, status="success",
            start_time=0, end_time=1, duration_ms=1000, token_estimate=100,
        )
        trace = ExecutionTrace(
            trace_id="t1", query="test",
            intent={}, plan={}, nodes=[nt], status="success",
            total_duration_ms=1000, timestamp="2026-04-15T12:00:00",
        )
        d = trace.to_dict()
        assert len(d["nodes"]) == 1
        assert d["nodes"][0]["node_id"] == "a"


class TestTraceWriter:
    def test_start_trace_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = TraceWriter(log_dir=Path(tmpdir))
            trace = ExecutionTrace(
                trace_id="t1", query="test",
                intent={"intent": "qa"}, plan={"nodes": []},
                nodes=[], status="pending",
                total_duration_ms=0, timestamp="2026-04-15T12:00:00",
            )
            path = writer.start_trace(trace)
            assert path.exists()
            with open(path) as f:
                line = json.loads(f.readline())
            assert line["type"] == "header"
            assert line["trace_id"] == "t1"

    def test_write_node_appends_line(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = TraceWriter(log_dir=Path(tmpdir))
            trace = ExecutionTrace(
                trace_id="t2", query="test",
                intent={}, plan={}, nodes=[], status="pending",
                total_duration_ms=0, timestamp="2026-04-15T12:00:00",
            )
            writer.start_trace(trace)

            nt = NodeTrace(
                node_id="a", agent_type="qa", input_query="q",
                context_snapshot={"key": "val"}, model_used="gemma",
                output={"answer": "yes"}, error=None, status="success",
                start_time=0, end_time=1, duration_ms=1000, token_estimate=100,
            )
            writer.write_node(trace.trace_id, nt)

            path = writer._trace_path(trace.trace_id)
            with open(path) as f:
                lines = f.readlines()
            assert len(lines) == 2
            node_line = json.loads(lines[1])
            assert node_line["type"] == "node"
            assert node_line["node_id"] == "a"

    def test_complete_trace_writes_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = TraceWriter(log_dir=Path(tmpdir))
            trace = ExecutionTrace(
                trace_id="t3", query="test",
                intent={}, plan={}, nodes=[], status="success",
                total_duration_ms=5000, timestamp="2026-04-15T12:00:00",
            )
            writer.start_trace(trace)
            writer.complete_trace(trace)

            path = writer._trace_path(trace.trace_id)
            with open(path) as f:
                lines = f.readlines()
            summary = json.loads(lines[-1])
            assert summary["type"] == "summary"
            assert summary["status"] == "success"
            assert summary["total_duration_ms"] == 5000

    def test_creates_log_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = Path(tmpdir) / "deep" / "traces"
            writer = TraceWriter(log_dir=nested)
            trace = ExecutionTrace(
                trace_id="t4", query="test",
                intent={}, plan={}, nodes=[], status="pending",
                total_duration_ms=0, timestamp="2026-04-15T12:00:00",
            )
            writer.start_trace(trace)
            assert nested.exists()


class TestFormatTrace:
    def test_format_success_trace(self):
        nt = NodeTrace(
            node_id="scan", agent_type="qa", input_query="Analyze",
            context_snapshot={"semantic_chunks": [{"content": "a"}, {"content": "b"}]},
            model_used="qwen2.5-coder:14b",
            output={"answer": "looks good"}, error=None, status="success",
            start_time=0, end_time=1.2, duration_ms=1200, token_estimate=4200,
        )
        trace = ExecutionTrace(
            trace_id="abc", query="Review the architecture",
            intent={"intent": "architecture_review", "complexity": "multi_step", "confidence": 0.92},
            plan={"reasoning": "Using template", "planner_type": "template", "node_count": 1},
            nodes=[nt], status="success",
            total_duration_ms=1200, timestamp="2026-04-15T12:00:00",
        )
        output = format_trace(trace)
        assert "abc" in output
        assert "scan" in output
        assert "1.2s" in output or "1200" in output
        assert "success" in output.lower()

    def test_format_failed_node(self):
        nt = NodeTrace(
            node_id="health", agent_type="refactor", input_query="assess",
            context_snapshot={}, model_used="gemma",
            output=None, error="Model timeout", status="failed",
            start_time=0, end_time=0.3, duration_ms=300, token_estimate=0,
        )
        trace = ExecutionTrace(
            trace_id="def", query="test",
            intent={}, plan={}, nodes=[nt], status="failed",
            total_duration_ms=300, timestamp="2026-04-15T12:00:00",
        )
        output = format_trace(trace)
        assert "health" in output
        assert "failed" in output.lower() or "ERROR" in output or "✗" in output

    def test_format_skipped_node(self):
        nt = NodeTrace(
            node_id="verify", agent_type="qa", input_query="check",
            context_snapshot={}, model_used="",
            output=None, error=None, status="skipped",
            start_time=0, end_time=0, duration_ms=0, token_estimate=0,
        )
        trace = ExecutionTrace(
            trace_id="ghi", query="test",
            intent={}, plan={}, nodes=[nt], status="success",
            total_duration_ms=0, timestamp="2026-04-15T12:00:00",
        )
        output = format_trace(trace)
        assert "verify" in output
        assert "skipped" in output.lower() or "⊘" in output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/krissdev/mike && python3 -m pytest tests/unit/test_trace.py -v 2>&1 | head -20`
Expected: ModuleNotFoundError

- [ ] **Step 3: Implement trace.py**

```python
# src/mike/orchestrator/trace.py
"""Execution trace system for Mike.

Structured JSONL-based tracing that captures the full DAG execution
lifecycle: intent classification, plan generation, per-node context
snapshots, agent outputs, and timing.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class NodeTrace:
    """Trace of a single node's execution."""

    node_id: str
    agent_type: str
    input_query: str
    context_snapshot: Dict[str, Any]
    model_used: str
    output: Optional[Dict[str, Any]]
    error: Optional[str]
    status: str
    start_time: float
    end_time: float
    duration_ms: int
    token_estimate: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "agent_type": self.agent_type,
            "input_query": self.input_query,
            "context_snapshot": self.context_snapshot,
            "model_used": self.model_used,
            "output": self.output,
            "error": self.error,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "token_estimate": self.token_estimate,
        }


@dataclass
class ExecutionTrace:
    """Trace of a full DAG execution pipeline."""

    trace_id: str
    query: str
    intent: Dict[str, Any]
    plan: Dict[str, Any]
    nodes: List[NodeTrace]
    status: str
    total_duration_ms: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "query": self.query,
            "intent": self.intent,
            "plan": self.plan,
            "nodes": [n.to_dict() for n in self.nodes],
            "status": self.status,
            "total_duration_ms": self.total_duration_ms,
            "timestamp": self.timestamp,
        }


class TraceWriter:
    """Writes execution traces to JSONL files."""

    def __init__(self, log_dir: Path = Path("./logs/traces")):
        self._log_dir = log_dir

    def _trace_path(self, trace_id: str) -> Path:
        return self._log_dir / f"trace_{trace_id}.jsonl"

    def start_trace(self, trace: ExecutionTrace) -> Path:
        """Write trace header line. Returns file path."""
        self._log_dir.mkdir(parents=True, exist_ok=True)
        path = self._trace_path(trace.trace_id)
        header = {
            "type": "header",
            "trace_id": trace.trace_id,
            "query": trace.query,
            "intent": trace.intent,
            "plan": trace.plan,
            "timestamp": trace.timestamp,
        }
        with open(path, "w") as f:
            f.write(json.dumps(header) + "\n")
        return path

    def write_node(self, trace_id: str, node_trace: NodeTrace) -> None:
        """Append a node trace line."""
        path = self._trace_path(trace_id)
        line = {"type": "node", **node_trace.to_dict()}
        with open(path, "a") as f:
            f.write(json.dumps(line) + "\n")

    def complete_trace(self, trace: ExecutionTrace) -> None:
        """Write summary line."""
        path = self._trace_path(trace.trace_id)
        summary = {
            "type": "summary",
            "trace_id": trace.trace_id,
            "status": trace.status,
            "total_duration_ms": trace.total_duration_ms,
            "node_count": len(trace.nodes),
        }
        with open(path, "a") as f:
            f.write(json.dumps(summary) + "\n")


def _format_duration(ms: int) -> str:
    """Format milliseconds as human-readable duration."""
    if ms < 1000:
        return f"{ms}ms"
    return f"{ms / 1000:.1f}s"


def _status_icon(status: str) -> str:
    """Return status icon character."""
    icons = {
        "success": "\u2713",
        "failed": "\u2717",
        "skipped": "\u2298",
        "cancelled": "\u2298",
    }
    return icons.get(status, "?")


def format_trace(trace: ExecutionTrace) -> str:
    """Format an ExecutionTrace for terminal display."""
    lines = []
    lines.append(f"=== Execution Trace: {trace.trace_id} ===")
    lines.append(f"Query: \"{trace.query}\"")

    intent = trace.intent
    intent_str = intent.get("intent", "unknown")
    confidence = intent.get("confidence", "?")
    complexity = intent.get("complexity", "?")
    lines.append(f"Intent: {intent_str} (confidence: {confidence}, {complexity})")

    plan = trace.plan
    planner = plan.get("planner_type", "unknown")
    reasoning = plan.get("reasoning", "")
    node_count = plan.get("node_count", len(trace.nodes))
    lines.append(f"Plan: {planner} ({node_count} nodes) — \"{reasoning}\"")
    lines.append("")

    for i, node in enumerate(trace.nodes, 1):
        icon = _status_icon(node.status)
        dur = _format_duration(node.duration_ms)
        tokens = node.token_estimate
        chunks = len(node.context_snapshot.get("semantic_chunks", []))

        if node.status == "success":
            lines.append(f"[{i}] {node.node_id} ({node.agent_type}) {icon} {dur} | {tokens} tokens | {chunks} chunks")
        elif node.status == "failed":
            lines.append(f"[{i}] {node.node_id} ({node.agent_type}) {icon} {dur} | ERROR: {node.error}")
        elif node.status in ("skipped", "cancelled"):
            lines.append(f"[{i}] {node.node_id} ({node.agent_type}) {icon} {node.status}")

    lines.append("")
    lines.append(f"Status: {trace.status} | Total: {_format_duration(trace.total_duration_ms)}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/krissdev/mike && python3 -m pytest tests/unit/test_trace.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/krissdev/mike
git add src/mike/orchestrator/trace.py tests/unit/test_trace.py
git commit -m "feat: add ExecutionTrace, NodeTrace, TraceWriter, format_trace"
```

---

## Task 2: Hook Tracing Into DAGExecutor

**Files:**
- Modify: `src/mike/orchestrator/dag_executor.py`
- Create: `tests/unit/test_trace_integration.py`

- [ ] **Step 1: Write failing integration tests**

```python
# tests/unit/test_trace_integration.py
"""Integration tests for DAGExecutor with tracing."""

import pytest
from unittest.mock import MagicMock

from mike.orchestrator.dag_executor import DAGExecutor, DAGResult
from mike.orchestrator.planner import PlanNode, ExecutionPlan
from mike.orchestrator.context_engine import ContextBundle
from mike.orchestrator.trace import ExecutionTrace, NodeTrace


def _make_plan(*node_specs):
    nodes = [
        PlanNode(id=nid, agent_type=atype, description=f"Do {nid}",
                 depends_on=deps, parameters={})
        for nid, atype, deps in node_specs
    ]
    return ExecutionPlan(nodes=nodes, reasoning="test", planner_type="test")


def _make_mock_agent(result=None):
    agent = MagicMock()
    agent.execute.return_value = result or {"status": "success", "data": "mock"}
    agent.validate_result.return_value = True
    agent.requires_approval.return_value = False
    return agent


def _make_mock_registry(agents=None):
    registry = MagicMock()
    agents = agents or {}
    registry.get.side_effect = lambda t: agents.get(t.value if hasattr(t, "value") else t)
    return registry


def _make_mock_context_engine():
    engine = MagicMock()
    engine.build.return_value = ContextBundle(
        query="test", agent_type="qa",
        semantic_chunks=[{"content": "code"}], structural_context={},
        execution_memory={}, shared_context={},
        token_budget=8000, estimated_tokens=500, metadata={},
    )
    return engine


def _make_trace(query="test query"):
    return ExecutionTrace(
        trace_id="test-trace-id", query=query,
        intent={"intent": "qa"}, plan={"nodes": []},
        nodes=[], status="pending",
        total_duration_ms=0, timestamp="2026-04-15T12:00:00",
    )


class TestDAGExecutorTracing:
    def test_trace_populated_after_execution(self):
        plan = _make_plan(("a", "qa", []))
        agent = _make_mock_agent()
        registry = _make_mock_registry({"qa": agent})
        context_engine = _make_mock_context_engine()
        trace = _make_trace()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        result = executor.execute_sync(plan, session_id="s1", trace=trace)

        assert len(trace.nodes) == 1
        assert trace.nodes[0].node_id == "a"
        assert trace.nodes[0].status == "success"
        assert trace.nodes[0].duration_ms > 0 or trace.nodes[0].duration_ms == 0

    def test_trace_captures_context_snapshot(self):
        plan = _make_plan(("a", "qa", []))
        agent = _make_mock_agent()
        registry = _make_mock_registry({"qa": agent})
        context_engine = _make_mock_context_engine()
        trace = _make_trace()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        executor.execute_sync(plan, session_id="s1", trace=trace)

        assert "semantic_chunks" in trace.nodes[0].context_snapshot

    def test_trace_captures_failed_node(self):
        plan = _make_plan(("a", "qa", []))
        failing = MagicMock()
        failing.execute.side_effect = Exception("boom")
        failing.requires_approval.return_value = False
        registry = _make_mock_registry({"qa": failing})
        context_engine = _make_mock_context_engine()
        trace = _make_trace()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        executor.execute_sync(plan, session_id="s1", trace=trace)

        assert trace.nodes[0].status == "failed"
        assert trace.nodes[0].error == "boom"

    def test_trace_captures_skipped_node(self):
        plan = ExecutionPlan(
            nodes=[
                PlanNode(id="a", agent_type="refactor", description="analyze",
                         depends_on=[], parameters={}),
                PlanNode(id="b", agent_type="qa", description="verify",
                         depends_on=["a"], parameters={},
                         condition="if_suggestions_exist"),
            ],
            reasoning="test", planner_type="test",
        )
        agent_a = _make_mock_agent({"status": "success", "suggestions": []})
        agent_b = _make_mock_agent()
        registry = _make_mock_registry({"refactor": agent_a, "qa": agent_b})
        context_engine = _make_mock_context_engine()
        trace = _make_trace()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        executor.execute_sync(plan, session_id="s1", trace=trace)

        skipped = [n for n in trace.nodes if n.node_id == "b"]
        assert len(skipped) == 1
        assert skipped[0].status == "skipped"

    def test_trace_captures_cancelled_node(self):
        plan = _make_plan(
            ("a", "qa", []),
            ("b", "refactor", ["a"]),
        )
        failing = MagicMock()
        failing.execute.side_effect = Exception("fail")
        failing.requires_approval.return_value = False
        registry = _make_mock_registry({"qa": failing, "refactor": _make_mock_agent()})
        context_engine = _make_mock_context_engine()
        trace = _make_trace()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        executor.execute_sync(plan, session_id="s1", trace=trace)

        cancelled = [n for n in trace.nodes if n.node_id == "b"]
        assert len(cancelled) == 1
        assert cancelled[0].status == "cancelled"

    def test_dag_result_has_trace_field(self):
        plan = _make_plan(("a", "qa", []))
        agent = _make_mock_agent()
        registry = _make_mock_registry({"qa": agent})
        context_engine = _make_mock_context_engine()
        trace = _make_trace()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        result = executor.execute_sync(plan, session_id="s1", trace=trace)

        assert result.trace is trace

    def test_existing_tests_unaffected_without_trace(self):
        """Trace is optional — existing behavior unchanged."""
        plan = _make_plan(("a", "qa", []))
        agent = _make_mock_agent()
        registry = _make_mock_registry({"qa": agent})
        context_engine = _make_mock_context_engine()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        result = executor.execute_sync(plan, session_id="s1")

        assert result.status == "success"
        assert result.trace is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/krissdev/mike && python3 -m pytest tests/unit/test_trace_integration.py -v 2>&1 | head -20`
Expected: AttributeError — `DAGResult` has no `trace` field, `execute_sync` doesn't accept `trace`

- [ ] **Step 3: Modify dag_executor.py — add trace field to DAGResult and trace hooks**

Add `trace` field to `DAGResult` at line 36:

```python
@dataclass
class DAGResult:
    plan: ExecutionPlan
    node_results: Dict[str, NodeResult] = field(default_factory=dict)
    total_duration_ms: int = 0
    status: str = "pending"
    trace: Optional[Any] = None  # Optional[ExecutionTrace], Any to avoid circular import
```

Modify `execute()` signature to accept optional trace (line 71-76):

```python
    async def execute(
        self,
        plan: ExecutionPlan,
        session_id: str,
        shared_context: Optional[Dict[str, Any]] = None,
        trace: Optional[Any] = None,
    ) -> DAGResult:
```

Inside `execute()`, after creating `dag_result` (line 78), attach trace:

```python
        dag_result = DAGResult(plan=plan)
        dag_result.trace = trace
```

In the cancelled node block (lines 99-106), add trace entry:

```python
                    dag_result.node_results[nid] = NodeResult(
                        node_id=nid,
                        agent_type=node.agent_type,
                        status="cancelled",
                        error="Predecessor failed",
                    )
                    if trace is not None:
                        from .trace import NodeTrace
                        trace.nodes.append(NodeTrace(
                            node_id=nid, agent_type=node.agent_type,
                            input_query=node.description, context_snapshot={},
                            model_used="", output=None, error="Predecessor failed",
                            status="cancelled", start_time=0, end_time=0,
                            duration_ms=0, token_estimate=0,
                        ))
                    failed_nodes.add(nid)
                    continue
```

In the skipped node block (lines 114-120), add trace entry:

```python
                if not _evaluate_condition(node.condition, pred_results):
                    dag_result.node_results[nid] = NodeResult(
                        node_id=nid,
                        agent_type=node.agent_type,
                        status="skipped",
                    )
                    if trace is not None:
                        from .trace import NodeTrace
                        trace.nodes.append(NodeTrace(
                            node_id=nid, agent_type=node.agent_type,
                            input_query=node.description, context_snapshot={},
                            model_used="", output=None, error=None,
                            status="skipped", start_time=0, end_time=0,
                            duration_ms=0, token_estimate=0,
                        ))
                    continue
```

Pass trace to `_execute_node` (line 122):

```python
                tasks.append(self._execute_node(node, session_id, dag_result, shared_context, trace))
```

Modify `_execute_node` signature (lines 153-158):

```python
    async def _execute_node(
        self,
        node: PlanNode,
        session_id: str,
        dag_result: DAGResult,
        shared_context: Optional[Dict[str, Any]] = None,
        trace: Optional[Any] = None,
    ) -> None:
```

In `_execute_node`, after building `context_bundle` (line 180) and before calling `agent.execute`, snapshot the context. Then after agent execution, append to trace. Replace the try/except block (lines 170-204):

```python
        try:
            agent = self._registry.get(node.agent_type)
            if agent is None:
                raise ValueError(f"No agent registered for type: {node.agent_type}")

            context_bundle = self._context_engine.build(
                query=node.description,
                agent_type=node.agent_type,
                session_id=session_id,
                shared_context=pred_shared,
            )

            # Snapshot context for trace BEFORE agent execution
            context_snapshot = context_bundle.to_dict() if trace is not None else {}

            agent_context = context_bundle.to_dict()
            agent_context.update(node.parameters)
            result = agent.execute(node.description, agent_context)

            duration = int((time.monotonic() - start) * 1000)
            dag_result.node_results[node.id] = NodeResult(
                node_id=node.id,
                agent_type=node.agent_type,
                status="success",
                result=result,
                duration_ms=duration,
            )

            if trace is not None:
                from .trace import NodeTrace
                trace.nodes.append(NodeTrace(
                    node_id=node.id, agent_type=node.agent_type,
                    input_query=node.description,
                    context_snapshot=context_snapshot,
                    model_used=getattr(agent, 'model_name', lambda: "unknown")() if callable(getattr(agent, 'model_name', None)) else "unknown",
                    output=result, error=None, status="success",
                    start_time=start, end_time=time.monotonic(),
                    duration_ms=duration,
                    token_estimate=context_bundle.estimated_tokens,
                ))

        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            logger.error(f"Node {node.id} failed: {e}")
            dag_result.node_results[node.id] = NodeResult(
                node_id=node.id,
                agent_type=node.agent_type,
                status="failed",
                error=str(e),
                duration_ms=duration,
            )

            if trace is not None:
                from .trace import NodeTrace
                trace.nodes.append(NodeTrace(
                    node_id=node.id, agent_type=node.agent_type,
                    input_query=node.description,
                    context_snapshot={},
                    model_used="unknown", output=None, error=str(e),
                    status="failed", start_time=start, end_time=time.monotonic(),
                    duration_ms=duration, token_estimate=0,
                ))
```

Update `execute_sync` to pass trace through (lines 206-232):

```python
    def execute_sync(
        self,
        plan: ExecutionPlan,
        session_id: str,
        shared_context: Optional[Dict[str, Any]] = None,
        trace: Optional[Any] = None,
    ) -> DAGResult:
        """Synchronous wrapper for execute()."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    asyncio.run,
                    self.execute(plan, session_id, shared_context, trace),
                )
                return future.result()
        else:
            return asyncio.run(self.execute(plan, session_id, shared_context, trace))
```

- [ ] **Step 4: Run integration tests AND existing dag_executor tests**

Run: `cd /Users/krissdev/mike && python3 -m pytest tests/unit/test_dag_executor.py tests/unit/test_trace_integration.py -v`
Expected: All tests PASS (existing + new)

- [ ] **Step 5: Commit**

```bash
cd /Users/krissdev/mike
git add src/mike/orchestrator/dag_executor.py tests/unit/test_trace_integration.py
git commit -m "feat: add execution trace hooks to DAGExecutor"
```

---

## Task 3: Wire Trace Into run() + Update Exports

**Files:**
- Modify: `src/mike/orchestrator/engine.py:620-679`
- Modify: `src/mike/orchestrator/__init__.py`

- [ ] **Step 1: Modify run() in engine.py to create and write traces**

Replace the `run()` method (lines 620-679) with this version that creates an ExecutionTrace, passes it through the pipeline, and writes it via TraceWriter:

```python
    def run(self, query: str, session_id: str = "default", shared_context=None):
        """Full pipeline: classify intent -> plan DAG -> execute.

        Creates an ExecutionTrace capturing the full lifecycle.
        """
        import uuid
        from datetime import datetime
        from .dag_executor import DAGResult
        from .trace import ExecutionTrace, TraceWriter

        # Step 1: Classify intent
        if hasattr(self, "intent_classifier") and self.intent_classifier:
            intent = self.intent_classifier.classify(query)
        else:
            from .planner import IntentResult, Complexity
            agent_type = self.router.route(query)
            intent = IntentResult(
                intent=agent_type.value if agent_type else "general_qa",
                complexity=Complexity.SIMPLE, confidence=0.5, parameters={},
            )

        # Step 2: Plan
        if hasattr(self, "strategy_router") and self.strategy_router:
            plan = self.strategy_router.plan(intent)
        else:
            from .planner import PlanNode, ExecutionPlan
            plan = ExecutionPlan(
                nodes=[PlanNode(id="main", agent_type=intent.intent,
                               description=query, depends_on=[], parameters={})],
                reasoning="Legacy fallback", planner_type="legacy",
            )

        # Create trace
        intent_dict = {
            "intent": intent.intent,
            "complexity": intent.complexity.value if hasattr(intent.complexity, 'value') else str(intent.complexity),
            "confidence": intent.confidence,
            "parameters": intent.parameters,
        }
        plan_dict = {
            "reasoning": plan.reasoning,
            "planner_type": plan.planner_type,
            "node_count": len(plan.nodes),
            "nodes": [{"id": n.id, "agent_type": n.agent_type, "depends_on": n.depends_on} for n in plan.nodes],
        }
        trace = ExecutionTrace(
            trace_id=str(uuid.uuid4())[:8],
            query=query,
            intent=intent_dict,
            plan=plan_dict,
            nodes=[],
            status="pending",
            total_duration_ms=0,
            timestamp=datetime.now().isoformat(),
        )

        self.log_action("plan_created", {
            "query": query, "trace_id": trace.trace_id, **intent_dict,
            "planner_type": plan.planner_type,
            "node_count": len(plan.nodes), "reasoning": plan.reasoning,
        })

        # Step 3: Execute DAG with trace
        if hasattr(self, "dag_executor") and self.dag_executor:
            result = self.dag_executor.execute_sync(plan, session_id, shared_context, trace=trace)
        else:
            from .dag_executor import DAGResult, NodeResult
            node = plan.nodes[0] if plan.nodes else None
            if node:
                from .state import AgentType
                execution = self.execute(query, agent_type=AgentType(node.agent_type))
                result = DAGResult(
                    plan=plan,
                    node_results={"main": NodeResult(
                        node_id="main", agent_type=node.agent_type,
                        status="success" if execution.status.name == "SUCCESS" else "failed",
                        result=execution.result, error=execution.error, duration_ms=0,
                    )},
                    status="success" if execution.status.name == "SUCCESS" else "failed",
                )
            else:
                result = DAGResult(plan=plan, status="failed")

        # Finalize trace
        trace.status = result.status
        trace.total_duration_ms = result.total_duration_ms

        # Write trace to JSONL
        try:
            writer = TraceWriter(log_dir=self.log_dir / "traces")
            writer.start_trace(trace)
            for node_trace in trace.nodes:
                writer.write_node(trace.trace_id, node_trace)
            writer.complete_trace(trace)
        except Exception as e:
            logger.warning(f"Failed to write trace: {e}")

        self.log_action("pipeline_completed", {
            "trace_id": trace.trace_id,
            "status": result.status,
            "node_count": len(result.node_results),
            "total_duration_ms": result.total_duration_ms,
        })
        return result
```

- [ ] **Step 2: Update __init__.py exports**

Add trace imports to `src/mike/orchestrator/__init__.py`:

After line 21 (`from .dag_executor import DAGExecutor, NodeResult, DAGResult`), add:

```python
from .trace import ExecutionTrace, NodeTrace, TraceWriter, format_trace
```

Add to `__all__` list:

```python
    "ExecutionTrace", "NodeTrace", "TraceWriter", "format_trace",
```

- [ ] **Step 3: Run ALL tests**

Run: `cd /Users/krissdev/mike && python3 -m pytest tests/unit/test_trace.py tests/unit/test_trace_integration.py tests/unit/test_dag_executor.py tests/integration/test_orchestrator_integration.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
cd /Users/krissdev/mike
git add src/mike/orchestrator/engine.py src/mike/orchestrator/__init__.py
git commit -m "feat: wire execution tracing into run() pipeline with JSONL output"
```

---

## Task 4: Verify Full Test Suite + No Regressions

- [ ] **Step 1: Run all new and existing tests**

Run: `cd /Users/krissdev/mike && python3 -m pytest tests/ --ignore=tests/tui/test_integration.py --ignore=tests/unit/test_scanner.py --tb=short -q 2>&1 | tail -10`
Expected: All pass (pre-existing failures in test_config.py and test_embeddings.py are known and unrelated)

- [ ] **Step 2: Verify trace files are created**

Run: `cd /Users/krissdev/mike && ls -la logs/traces/ 2>/dev/null || echo "No trace files yet (expected - only created at runtime)"`

- [ ] **Step 3: Commit any fixes**

```bash
cd /Users/krissdev/mike
git add -u
git commit -m "fix: resolve test regressions from trace integration"
```

(Skip if no fixes needed.)
