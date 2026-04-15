# tests/unit/test_trace.py
"""Unit tests for execution trace system."""

import json
import tempfile
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
        assert "Model timeout" in output

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
        assert "skipped" in output.lower()
