"""Integration test for the full orchestrator pipeline."""

import pytest
from unittest.mock import MagicMock

from mike.orchestrator.engine import AgentOrchestrator
from mike.orchestrator.state import OrchestratorState, AgentType
from mike.orchestrator.model_provider import ModelProvider
from mike.orchestrator.context_engine import ContextEngine
from mike.orchestrator.planner import (
    IntentClassifier, StrategyRouter, RulePlanner, TemplatePlanner, LLMPlanner,
)
from mike.orchestrator.dag_executor import DAGExecutor, DAGResult


class TestOrchestratorRunPipeline:
    def _setup_orchestrator(self):
        model_provider = MagicMock(spec=ModelProvider)
        model_provider.generate_json.return_value = {
            "intent": "explain_code", "complexity": "simple",
            "confidence": 0.95, "parameters": {},
        }
        model_provider.model_name.return_value = "test-model"

        vector_store = MagicMock()
        vector_store.search.return_value = [
            {"id": "c0", "content": "def main(): pass",
             "metadata": {"file_path": "main.py"}, "distance": 0.1}
        ]
        embedding_service = MagicMock()
        embedding_service.embed.return_value = [0.1] * 1024

        context_engine = ContextEngine(
            vector_store=vector_store,
            embedding_service=embedding_service,
        )
        intent_classifier = IntentClassifier(model_provider)
        strategy_router = StrategyRouter(
            rule_planner=RulePlanner(),
            template_planner=TemplatePlanner(),
            llm_planner=LLMPlanner(model_provider),
        )

        state = OrchestratorState()
        orchestrator = AgentOrchestrator(state=state)

        mock_agent = MagicMock()
        mock_agent.agent_type = AgentType.QA
        mock_agent.execute.return_value = {"status": "success", "answer": "The function does X"}
        mock_agent.validate_result.return_value = True
        mock_agent.requires_approval.return_value = False
        orchestrator.register_agent(mock_agent)

        # Wrap the registry so DAGExecutor can look up agents by string value
        # (DAGExecutor uses string agent_type from PlanNodes, while AgentRegistry
        # indexes by AgentType enum)
        real_registry = orchestrator.registry
        _agent_map = {at.value: agent for at, agent in real_registry.get_all().items()}
        original_get = real_registry.get

        def _flexible_get(agent_type):
            if isinstance(agent_type, str):
                return _agent_map.get(agent_type)
            return original_get(agent_type)

        real_registry.get = _flexible_get

        orchestrator.intent_classifier = intent_classifier
        orchestrator.strategy_router = strategy_router
        orchestrator.context_engine = context_engine
        orchestrator.dag_executor = DAGExecutor(
            agent_registry=real_registry,
            context_engine=context_engine,
        )

        return orchestrator

    def test_run_simple_query(self):
        orchestrator = self._setup_orchestrator()
        result = orchestrator.run("What does the main function do?", session_id="test-session")
        assert isinstance(result, DAGResult)
        assert result.status == "success"
        assert len(result.node_results) == 1

    def test_run_returns_agent_output(self):
        orchestrator = self._setup_orchestrator()
        result = orchestrator.run("explain the code", session_id="test-session")
        node_result = list(result.node_results.values())[0]
        assert node_result.result["answer"] == "The function does X"

    def test_run_with_plan_explainability(self):
        orchestrator = self._setup_orchestrator()
        result = orchestrator.run("What does this do?", session_id="test-session")
        assert result.plan.reasoning is not None
        assert result.plan.planner_type == "rule"
