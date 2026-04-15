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
        plan = _make_plan(("a", "qa", []))
        agent = _make_mock_agent()
        registry = _make_mock_registry({"qa": agent})
        context_engine = _make_mock_context_engine()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        result = executor.execute_sync(plan, session_id="s1")

        assert result.status == "success"
        assert result.trace is None
