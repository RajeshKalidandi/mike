"""Agent Orchestrator for Mike.

Provides a multi-agent orchestration system with:
- Progressive Planning Architecture (intent -> plan -> DAG)
- ContextEngine (semantic retrieval, graph expansion, token budgeting)
- DAGExecutor (topological execution, parallel branches, cancellation)
- ModelProvider abstraction (Ollama, OpenAI-compatible, model routing)
"""

from .state import OrchestratorState, AgentExecution, SessionContext, ExecutionMemory
from .engine import AgentOrchestrator, AgentRegistry, TaskRouter
from .model_provider import (
    ModelCapabilities, ModelProvider, OllamaProvider,
    OpenAICompatibleProvider, ModelRouter,
)
from .context_engine import ContextEngine, ContextBundle
from .planner import (
    Complexity, IntentResult, PlanNode, ExecutionPlan,
    IntentClassifier, StrategyRouter, RulePlanner, TemplatePlanner, LLMPlanner,
)
from .dag_executor import DAGExecutor, NodeResult, DAGResult
from .trace import ExecutionTrace, NodeTrace, TraceWriter, format_trace

__all__ = [
    "OrchestratorState", "AgentExecution", "SessionContext", "ExecutionMemory",
    "AgentOrchestrator", "AgentRegistry", "TaskRouter",
    "ModelCapabilities", "ModelProvider", "OllamaProvider",
    "OpenAICompatibleProvider", "ModelRouter",
    "ContextEngine", "ContextBundle",
    "Complexity", "IntentResult", "PlanNode", "ExecutionPlan",
    "IntentClassifier", "StrategyRouter", "RulePlanner", "TemplatePlanner", "LLMPlanner",
    "DAGExecutor", "NodeResult", "DAGResult",
    "ExecutionTrace", "NodeTrace", "TraceWriter", "format_trace",
]
