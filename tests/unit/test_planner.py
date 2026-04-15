# tests/unit/test_planner.py
"""Unit tests for Progressive Planning Architecture."""

import json
import pytest
from unittest.mock import MagicMock

from mike.orchestrator.planner import (
    Complexity,
    IntentResult,
    PlanNode,
    ExecutionPlan,
    IntentClassifier,
    StrategyRouter,
    RulePlanner,
    TemplatePlanner,
    LLMPlanner,
)
from mike.orchestrator.model_provider import ModelProvider


class TestComplexity:
    def test_enum_values(self):
        assert Complexity.SIMPLE == "simple"
        assert Complexity.MULTI_STEP == "multi_step"
        assert Complexity.OPEN_ENDED == "open_ended"


class TestIntentResult:
    def test_create(self):
        result = IntentResult(
            intent="explain_code",
            complexity=Complexity.SIMPLE,
            confidence=0.95,
            parameters={"file": "main.py"},
        )
        assert result.intent == "explain_code"
        assert result.complexity == Complexity.SIMPLE


class TestPlanNode:
    def test_create(self):
        node = PlanNode(
            id="step1", agent_type="qa",
            description="Analyze code", depends_on=[],
            parameters={"focus": "auth"},
        )
        assert node.id == "step1"
        assert node.depends_on == []

    def test_condition_defaults_to_none(self):
        node = PlanNode(id="s", agent_type="qa", description="x", depends_on=[], parameters={})
        assert node.condition is None


class TestExecutionPlan:
    def test_create(self):
        plan = ExecutionPlan(
            nodes=[PlanNode(id="a", agent_type="qa", description="test", depends_on=[], parameters={})],
            reasoning="Simple query",
            planner_type="rule",
        )
        assert len(plan.nodes) == 1
        assert plan.planner_type == "rule"

    def test_node_ids(self):
        plan = ExecutionPlan(
            nodes=[
                PlanNode(id="a", agent_type="qa", description="x", depends_on=[], parameters={}),
                PlanNode(id="b", agent_type="docs", description="y", depends_on=["a"], parameters={}),
            ],
            reasoning="test", planner_type="template",
        )
        assert plan.node_ids() == ["a", "b"]

    def test_is_valid_dag_accepts_valid(self):
        plan = ExecutionPlan(
            nodes=[
                PlanNode(id="a", agent_type="qa", description="x", depends_on=[], parameters={}),
                PlanNode(id="b", agent_type="docs", description="y", depends_on=["a"], parameters={}),
            ],
            reasoning="test", planner_type="template",
        )
        assert plan.is_valid_dag() is True

    def test_is_valid_dag_rejects_cycle(self):
        plan = ExecutionPlan(
            nodes=[
                PlanNode(id="a", agent_type="qa", description="x", depends_on=["b"], parameters={}),
                PlanNode(id="b", agent_type="docs", description="y", depends_on=["a"], parameters={}),
            ],
            reasoning="test", planner_type="template",
        )
        assert plan.is_valid_dag() is False

    def test_is_valid_dag_rejects_missing_dependency(self):
        plan = ExecutionPlan(
            nodes=[
                PlanNode(id="a", agent_type="qa", description="x", depends_on=["nonexistent"], parameters={}),
            ],
            reasoning="test", planner_type="template",
        )
        assert plan.is_valid_dag() is False


class TestIntentClassifier:
    def _make_mock_provider(self, json_response):
        provider = MagicMock(spec=ModelProvider)
        provider.generate_json.return_value = json_response
        return provider

    def test_classify_returns_intent_result(self):
        provider = self._make_mock_provider({
            "intent": "explain_code",
            "complexity": "simple",
            "confidence": 0.9,
            "parameters": {},
        })
        classifier = IntentClassifier(provider)
        result = classifier.classify("What does this function do?")
        assert isinstance(result, IntentResult)
        assert result.intent == "explain_code"
        assert result.complexity == Complexity.SIMPLE

    def test_classify_falls_back_on_invalid_json(self):
        provider = MagicMock(spec=ModelProvider)
        provider.generate_json.return_value = {}
        classifier = IntentClassifier(provider)
        result = classifier.classify("tell me about the code")
        assert isinstance(result, IntentResult)
        assert result.intent == "general_qa"
        assert result.confidence < 1.0

    def test_classify_falls_back_on_exception(self):
        provider = MagicMock(spec=ModelProvider)
        provider.generate_json.side_effect = Exception("connection refused")
        classifier = IntentClassifier(provider)
        result = classifier.classify("explain auth")
        assert isinstance(result, IntentResult)
        assert result.intent == "explain_code"

    def test_keyword_fallback_detects_docs(self):
        provider = MagicMock(spec=ModelProvider)
        provider.generate_json.side_effect = Exception("offline")
        classifier = IntentClassifier(provider)
        result = classifier.classify("generate documentation for this project")
        assert result.intent == "generate_docs"

    def test_keyword_fallback_detects_refactor(self):
        provider = MagicMock(spec=ModelProvider)
        provider.generate_json.side_effect = Exception("offline")
        classifier = IntentClassifier(provider)
        result = classifier.classify("refactor the authentication module")
        assert result.intent == "refactor"


class TestRulePlanner:
    def test_simple_qa_produces_single_node(self):
        planner = RulePlanner()
        intent = IntentResult(intent="explain_code", complexity=Complexity.SIMPLE, confidence=0.9, parameters={})
        plan = planner.plan(intent)
        assert len(plan.nodes) == 1
        assert plan.nodes[0].agent_type == "qa"
        assert plan.planner_type == "rule"

    def test_docs_intent_maps_to_docs_agent(self):
        planner = RulePlanner()
        intent = IntentResult(intent="generate_docs", complexity=Complexity.SIMPLE, confidence=0.9, parameters={})
        plan = planner.plan(intent)
        assert plan.nodes[0].agent_type == "docs"

    def test_unknown_intent_defaults_to_qa(self):
        planner = RulePlanner()
        intent = IntentResult(intent="totally_unknown", complexity=Complexity.SIMPLE, confidence=0.5, parameters={})
        plan = planner.plan(intent)
        assert plan.nodes[0].agent_type == "qa"


class TestTemplatePlanner:
    def test_architecture_review_template(self):
        planner = TemplatePlanner()
        intent = IntentResult(intent="architecture_review", complexity=Complexity.MULTI_STEP, confidence=0.9, parameters={})
        plan = planner.plan(intent)
        assert len(plan.nodes) >= 2
        assert plan.planner_type == "template"
        assert plan.is_valid_dag() is True

    def test_full_documentation_template(self):
        planner = TemplatePlanner()
        intent = IntentResult(intent="full_documentation", complexity=Complexity.MULTI_STEP, confidence=0.9, parameters={})
        plan = planner.plan(intent)
        assert len(plan.nodes) >= 3
        assert plan.is_valid_dag() is True

    def test_parameters_merged_into_nodes(self):
        planner = TemplatePlanner()
        intent = IntentResult(
            intent="architecture_review", complexity=Complexity.MULTI_STEP,
            confidence=0.9, parameters={"target_dir": "src/auth"},
        )
        plan = planner.plan(intent)
        for node in plan.nodes:
            assert "target_dir" in node.parameters

    def test_unknown_template_falls_back_to_single_node(self):
        planner = TemplatePlanner()
        intent = IntentResult(intent="unknown_workflow", complexity=Complexity.MULTI_STEP, confidence=0.5, parameters={})
        plan = planner.plan(intent)
        assert len(plan.nodes) >= 1
        assert plan.is_valid_dag() is True


class TestLLMPlanner:
    def _make_mock_provider(self, json_response):
        provider = MagicMock(spec=ModelProvider)
        provider.generate_json.return_value = json_response
        return provider

    def test_valid_llm_plan(self):
        provider = self._make_mock_provider({
            "reasoning": "Need to analyze then fix",
            "steps": [
                {"id": "analyze", "agent": "qa", "description": "Find the issue", "depends_on": [], "parameters": {}},
                {"id": "fix", "agent": "refactor", "description": "Fix it", "depends_on": ["analyze"], "parameters": {}},
            ],
        })
        planner = LLMPlanner(provider)
        intent = IntentResult(intent="complex_task", complexity=Complexity.OPEN_ENDED, confidence=0.8, parameters={})
        plan = planner.plan(intent)
        assert len(plan.nodes) == 2
        assert plan.planner_type == "llm"
        assert plan.is_valid_dag() is True

    def test_rejects_invalid_agent_type(self):
        provider = self._make_mock_provider({
            "reasoning": "test",
            "steps": [
                {"id": "s1", "agent": "INVALID_AGENT", "description": "bad", "depends_on": [], "parameters": {}},
            ],
        })
        planner = LLMPlanner(provider)
        intent = IntentResult(intent="test", complexity=Complexity.OPEN_ENDED, confidence=0.8, parameters={})
        plan = planner.plan(intent)
        assert plan.planner_type == "llm_fallback"
        assert plan.is_valid_dag() is True

    def test_rejects_cyclic_plan(self):
        provider = self._make_mock_provider({
            "reasoning": "test",
            "steps": [
                {"id": "a", "agent": "qa", "description": "x", "depends_on": ["b"], "parameters": {}},
                {"id": "b", "agent": "qa", "description": "y", "depends_on": ["a"], "parameters": {}},
            ],
        })
        planner = LLMPlanner(provider)
        intent = IntentResult(intent="test", complexity=Complexity.OPEN_ENDED, confidence=0.8, parameters={})
        plan = planner.plan(intent)
        assert plan.planner_type == "llm_fallback"

    def test_rejects_too_many_nodes(self):
        provider = self._make_mock_provider({
            "reasoning": "test",
            "steps": [
                {"id": f"s{i}", "agent": "qa", "description": f"step {i}", "depends_on": [], "parameters": {}}
                for i in range(6)
            ],
        })
        planner = LLMPlanner(provider)
        intent = IntentResult(intent="test", complexity=Complexity.OPEN_ENDED, confidence=0.8, parameters={})
        plan = planner.plan(intent)
        assert plan.planner_type == "llm_fallback"

    def test_falls_back_on_llm_error(self):
        provider = MagicMock(spec=ModelProvider)
        provider.generate_json.side_effect = Exception("timeout")
        planner = LLMPlanner(provider)
        intent = IntentResult(intent="test", complexity=Complexity.OPEN_ENDED, confidence=0.8, parameters={})
        plan = planner.plan(intent)
        assert plan.planner_type == "llm_fallback"
        assert plan.is_valid_dag() is True


class TestStrategyRouter:
    def test_routes_simple_to_rule_planner(self):
        rule = MagicMock(spec=RulePlanner)
        rule.plan.return_value = ExecutionPlan(
            nodes=[PlanNode(id="a", agent_type="qa", description="x", depends_on=[], parameters={})],
            reasoning="simple", planner_type="rule",
        )
        router = StrategyRouter(rule_planner=rule, template_planner=MagicMock(), llm_planner=MagicMock())
        intent = IntentResult(intent="explain_code", complexity=Complexity.SIMPLE, confidence=0.9, parameters={})
        plan = router.plan(intent)
        rule.plan.assert_called_once_with(intent)
        assert plan.planner_type == "rule"

    def test_routes_multi_step_to_template_planner(self):
        template = MagicMock(spec=TemplatePlanner)
        template.plan.return_value = ExecutionPlan(
            nodes=[], reasoning="template", planner_type="template",
        )
        router = StrategyRouter(rule_planner=MagicMock(), template_planner=template, llm_planner=MagicMock())
        intent = IntentResult(intent="architecture_review", complexity=Complexity.MULTI_STEP, confidence=0.9, parameters={})
        router.plan(intent)
        template.plan.assert_called_once_with(intent)

    def test_routes_open_ended_to_llm_planner(self):
        llm = MagicMock(spec=LLMPlanner)
        llm.plan.return_value = ExecutionPlan(
            nodes=[], reasoning="llm", planner_type="llm",
        )
        router = StrategyRouter(rule_planner=MagicMock(), template_planner=MagicMock(), llm_planner=llm)
        intent = IntentResult(intent="complex", complexity=Complexity.OPEN_ENDED, confidence=0.8, parameters={})
        router.plan(intent)
        llm.plan.assert_called_once_with(intent)
