# tests/unit/test_dag_executor.py
"""Unit tests for DAGExecutor."""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from mike.orchestrator.dag_executor import DAGExecutor, NodeResult, DAGResult
from mike.orchestrator.planner import PlanNode, ExecutionPlan
from mike.orchestrator.context_engine import ContextBundle


def _make_plan(*node_specs):
    nodes = [
        PlanNode(id=nid, agent_type=atype, description=f"Do {nid}",
                 depends_on=deps, parameters={})
        for nid, atype, deps in node_specs
    ]
    return ExecutionPlan(nodes=nodes, reasoning="test plan", planner_type="test")


def _make_mock_agent(result=None):
    agent = MagicMock()
    agent.execute.return_value = result or {"status": "success", "data": "mock result"}
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
        semantic_chunks=[], structural_context={},
        execution_memory={}, shared_context={},
        token_budget=8000, estimated_tokens=100, metadata={},
    )
    return engine


class TestNodeResult:
    def test_create(self):
        result = NodeResult(
            node_id="step1", agent_type="qa",
            status="success", result={"data": "x"},
            error=None, duration_ms=150,
        )
        assert result.status == "success"
        assert result.duration_ms == 150


class TestDAGExecutorSingleNode:
    def test_executes_single_node(self):
        plan = _make_plan(("main", "qa", []))
        agent = _make_mock_agent()
        registry = _make_mock_registry({"qa": agent})
        context_engine = _make_mock_context_engine()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        result = executor.execute_sync(plan, session_id="s1")

        assert isinstance(result, DAGResult)
        assert result.status == "success"
        assert "main" in result.node_results
        assert result.node_results["main"].status == "success"
        agent.execute.assert_called_once()


class TestDAGExecutorSequentialDependencies:
    def test_respects_dependency_order(self):
        plan = _make_plan(
            ("a", "qa", []),
            ("b", "refactor", ["a"]),
        )
        agent_a = _make_mock_agent({"status": "success", "data": "from_a"})
        agent_b = _make_mock_agent({"status": "success", "data": "from_b"})
        registry = _make_mock_registry({"qa": agent_a, "refactor": agent_b})
        context_engine = _make_mock_context_engine()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        result = executor.execute_sync(plan, session_id="s1")

        assert result.status == "success"
        assert result.node_results["a"].status == "success"
        assert result.node_results["b"].status == "success"

    def test_passes_predecessor_results_in_shared_context(self):
        plan = _make_plan(
            ("a", "qa", []),
            ("b", "refactor", ["a"]),
        )
        agent_a = _make_mock_agent({"status": "success", "data": "from_a"})
        agent_b = _make_mock_agent()
        registry = _make_mock_registry({"qa": agent_a, "refactor": agent_b})
        context_engine = _make_mock_context_engine()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        executor.execute_sync(plan, session_id="s1")

        calls = context_engine.build.call_args_list
        b_call = [c for c in calls if c[1].get("agent_type") == "refactor" or
                  (c[0] and len(c[0]) > 1 and c[0][1] == "refactor")]
        assert len(b_call) >= 1


class TestDAGExecutorParallelBranches:
    def test_independent_nodes_both_execute(self):
        plan = _make_plan(
            ("a", "qa", []),
            ("b", "docs", []),
        )
        agent_qa = _make_mock_agent()
        agent_docs = _make_mock_agent()
        registry = _make_mock_registry({"qa": agent_qa, "docs": agent_docs})
        context_engine = _make_mock_context_engine()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        result = executor.execute_sync(plan, session_id="s1")

        assert result.node_results["a"].status == "success"
        assert result.node_results["b"].status == "success"


class TestDAGExecutorFailureHandling:
    def test_failed_node_cancels_dependents(self):
        plan = _make_plan(
            ("a", "qa", []),
            ("b", "refactor", ["a"]),
            ("c", "docs", []),
        )
        failing_agent = MagicMock()
        failing_agent.execute.side_effect = Exception("boom")
        failing_agent.requires_approval.return_value = False
        ok_agent = _make_mock_agent()
        registry = _make_mock_registry({"qa": failing_agent, "refactor": ok_agent, "docs": ok_agent})
        context_engine = _make_mock_context_engine()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        result = executor.execute_sync(plan, session_id="s1")

        assert result.node_results["a"].status == "failed"
        assert result.node_results["b"].status == "cancelled"
        assert result.node_results["c"].status == "success"
        assert result.status == "partial"

    def test_missing_agent_fails_node(self):
        plan = _make_plan(("a", "nonexistent", []))
        registry = _make_mock_registry({})
        context_engine = _make_mock_context_engine()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        result = executor.execute_sync(plan, session_id="s1")

        assert result.node_results["a"].status == "failed"
        assert result.status == "failed"


class TestDAGExecutorConditions:
    def test_skips_node_when_condition_not_met(self):
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

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        result = executor.execute_sync(plan, session_id="s1")

        assert result.node_results["a"].status == "success"
        assert result.node_results["b"].status == "skipped"

    def test_executes_node_when_condition_met(self):
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
        agent_a = _make_mock_agent({"status": "success", "suggestions": ["fix X", "fix Y"]})
        agent_b = _make_mock_agent()
        registry = _make_mock_registry({"refactor": agent_a, "qa": agent_b})
        context_engine = _make_mock_context_engine()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        result = executor.execute_sync(plan, session_id="s1")

        assert result.node_results["b"].status == "success"
