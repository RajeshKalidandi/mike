# src/mike/orchestrator/trace.py
"""Execution trace system for Mike.

Structured JSONL-based tracing that captures the full DAG execution
lifecycle: intent classification, plan generation, per-node context
snapshots, agent outputs, and timing.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
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
    if ms < 1000:
        return f"{ms}ms"
    return f"{ms / 1000:.1f}s"


def _status_icon(status: str) -> str:
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
    lines.append(f"Plan: {planner} ({node_count} nodes) \u2014 \"{reasoning}\"")
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
