"""Agent Orchestrator Engine for Mike.

Provides the main orchestration logic for coordinating multiple agents:
- Agent registry and discovery
- Task routing
- State management
- Execution memory
- Sequential and parallel execution modes
- Human approval checkpoints
- Context assembly
- JSON logging
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

from .state import (
    AgentExecution,
    AgentType,
    ExecutionMode,
    ExecutionStatus,
    OrchestratorState,
    SessionContext,
)


# Configure JSON logging
logger = logging.getLogger(__name__)


class Agent(ABC):
    """Abstract base class for all agents.

    Agents implement specific functionality:
    - Documentation Agent
    - Q&A Agent
    - Refactor Agent
    - Rebuilder Agent
    """

    def __init__(self, agent_type: AgentType, config: Optional[Dict[str, Any]] = None):
        self.agent_type = agent_type
        self.config = config or {}
        self.logger = logging.getLogger(f"mike.agents.{agent_type.value}")

    @abstractmethod
    def execute(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent with the given query and context.

        Args:
            query: The user query or task description
            context: Assembled context including structural and semantic memory

        Returns:
            Execution result dictionary
        """
        pass

    @abstractmethod
    def requires_approval(self, query: str, context: Dict[str, Any]) -> bool:
        """Determine if this execution requires human approval.

        Args:
            query: The user query
            context: Execution context

        Returns:
            True if approval is required
        """
        pass

    def validate_result(self, result: Dict[str, Any]) -> bool:
        """Validate the execution result.

        Args:
            result: The execution result

        Returns:
            True if result is valid
        """
        return result is not None and "status" in result

    def log_action(self, action: str, metadata: Dict[str, Any]) -> None:
        """Log an agent action in JSON format.

        Args:
            action: The action name
            metadata: Action metadata
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent_type": self.agent_type.value,
            "action": action,
            "metadata": metadata,
        }
        self.logger.info(json.dumps(log_entry))


class AgentRegistry:
    """Registry for managing and discovering agents.

    Provides:
    - Agent registration
    - Agent discovery by type
    - Agent metadata management
    """

    def __init__(self):
        self._agents: Dict[AgentType, Agent] = {}
        self._agent_metadata: Dict[AgentType, Dict[str, Any]] = {}

    def register(self, agent: Agent, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Register an agent.

        Args:
            agent: The agent instance
            metadata: Optional metadata about the agent
        """
        self._agents[agent.agent_type] = agent
        self._agent_metadata[agent.agent_type] = metadata or {}
        logger.info(f"Registered agent: {agent.agent_type.value}")

    def unregister(self, agent_type: AgentType) -> None:
        """Unregister an agent.

        Args:
            agent_type: The agent type to unregister
        """
        if agent_type in self._agents:
            del self._agents[agent_type]
            del self._agent_metadata[agent_type]
            logger.info(f"Unregistered agent: {agent_type.value}")

    def get(self, agent_type: AgentType) -> Optional[Agent]:
        """Get an agent by type.

        Args:
            agent_type: The agent type

        Returns:
            The agent instance or None if not found
        """
        return self._agents.get(agent_type)

    def get_all(self) -> Dict[AgentType, Agent]:
        """Get all registered agents.

        Returns:
            Dictionary of agent types to agent instances
        """
        return self._agents.copy()

    def get_metadata(self, agent_type: AgentType) -> Optional[Dict[str, Any]]:
        """Get metadata for an agent.

        Args:
            agent_type: The agent type

        Returns:
            Agent metadata or None if not found
        """
        return self._agent_metadata.get(agent_type)

    def list_agents(self) -> List[str]:
        """List all registered agent types.

        Returns:
            List of agent type names
        """
        return [agent_type.value for agent_type in self._agents.keys()]

    def is_registered(self, agent_type: AgentType) -> bool:
        """Check if an agent is registered.

        Args:
            agent_type: The agent type

        Returns:
            True if the agent is registered
        """
        return agent_type in self._agents


class TaskRouter:
    """Routes tasks to appropriate agents.

    Implements routing logic based on:
    - Query intent classification
    - Agent capabilities
    - Historical performance
    """

    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self._routing_rules: List[Callable[[str], Optional[AgentType]]] = []
        self._setup_default_rules()

    def _setup_default_rules(self) -> None:
        """Setup default routing rules."""
        # Documentation-related keywords
        self._routing_rules.append(
            lambda q: AgentType.DOCUMENTATION
            if any(
                kw in q.lower()
                for kw in [
                    "document",
                    "readme",
                    "architecture",
                    "api reference",
                    "docs",
                    "generate docs",
                    "create documentation",
                    "explain structure",
                ]
            )
            else None
        )

        # Refactor-related keywords
        self._routing_rules.append(
            lambda q: AgentType.REFACTOR
            if any(
                kw in q.lower()
                for kw in [
                    "refactor",
                    "improve",
                    "code smell",
                    "clean up",
                    "optimize",
                    "restructure",
                    "simplify",
                    "better way",
                ]
            )
            else None
        )

        # Rebuilder-related keywords
        self._routing_rules.append(
            lambda q: AgentType.REBUILDER
            if any(
                kw in q.lower()
                for kw in [
                    "scaffold",
                    "generate project",
                    "create app",
                    "build similar",
                    "new project",
                    "template",
                    "boilerplate",
                    "rebuild",
                ]
            )
            else None
        )

        # Default to Q&A
        self._routing_rules.append(lambda q: AgentType.QA)

    def add_routing_rule(self, rule: Callable[[str], Optional[AgentType]]) -> None:
        """Add a custom routing rule.

        Rules are evaluated in order. First match wins.

        Args:
            rule: Function that takes a query and returns AgentType or None
        """
        self._routing_rules.insert(0, rule)

    def route(self, query: str) -> Optional[AgentType]:
        """Route a query to the appropriate agent type.

        Args:
            query: The user query

        Returns:
            The best matching agent type, or None if no match
        """
        for rule in self._routing_rules:
            result = rule(query)
            if result is not None:
                logger.debug(f"Routed query to {result.value}: {query[:50]}...")
                return result
        return None

    def route_with_agent(self, query: str) -> Optional[Agent]:
        """Route and return the agent instance.

        Args:
            query: The user query

        Returns:
            The best matching agent, or None if no match
        """
        agent_type = self.route(query)
        if agent_type:
            return self.registry.get(agent_type)
        return None


class ContextAssembler:
    """Assembles context for agent execution.

    Implements the context assembly pipeline from CONTEXT.md:
    1. Semantic search → Top-K chunks
    2. Graph-aware expansion (callers + callees)
    3. Hierarchical summary injection
    4. Token budget management
    """

    def __init__(self, state: OrchestratorState):
        self.state = state

    def assemble(
        self,
        query: str,
        agent_type: AgentType,
        include_structural: bool = True,
        include_semantic: bool = True,
        token_budget: int = 8000,
    ) -> Dict[str, Any]:
        """Assemble context for an agent execution.

        Args:
            query: The user query
            agent_type: The target agent type
            include_structural: Include structural memory (AST, dependency graph)
            include_semantic: Include semantic memory (embeddings, chunks)
            token_budget: Maximum tokens for context

        Returns:
            Assembled context dictionary
        """
        context: Dict[str, Any] = {
            "query": query,
            "agent_type": agent_type.value,
            "assembled_at": datetime.now().isoformat(),
            "session_id": self.state.session.session_id,
        }

        # Add structural memory if available
        if include_structural and self.state.session.structural_memory:
            context["structural"] = self._assemble_structural_context(query)

        # Add semantic memory if available
        if include_semantic and self.state.session.semantic_memory:
            context["semantic"] = self._assemble_semantic_context(query)

        # Add execution memory
        context["execution_memory"] = self._assemble_execution_memory(agent_type)

        # Add shared context from previous agents
        context["shared"] = self.state.shared_context.copy()

        # Apply token budget management
        context = self._apply_token_budget(context, token_budget)

        return context

    def _assemble_structural_context(self, query: str) -> Dict[str, Any]:
        """Assemble structural context (AST, dependency graph).

        Args:
            query: The user query

        Returns:
            Structural context dictionary
        """
        structural = self.state.session.structural_memory

        # TODO: Implement graph-aware expansion
        # - Find relevant nodes based on query
        # - Fetch callers and callees (2-hop expansion)
        # - Include relevant file paths

        return {
            "files": structural.get("files", []),
            "dependencies": structural.get("dependencies", {}),
            "ast_summary": structural.get("ast_summary", {}),
        }

    def _assemble_semantic_context(self, query: str) -> Dict[str, Any]:
        """Assemble semantic context (embeddings, chunks).

        Args:
            query: The user query

        Returns:
            Semantic context dictionary
        """
        semantic = self.state.session.semantic_memory

        # TODO: Implement semantic search
        # - Embed the query
        # - Search vector store for top-k chunks
        # - Include metadata for each chunk

        return {
            "chunks": semantic.get("chunks", []),
            "summaries": semantic.get("summaries", {}),
            "query_embedding": None,  # To be implemented
        }

    def _assemble_execution_memory(self, agent_type: AgentType) -> Dict[str, Any]:
        """Assemble execution memory for an agent.

        Args:
            agent_type: The target agent type

        Returns:
            Execution memory dictionary
        """
        memory = self.state.session.execution_memory

        return {
            "failed_approaches": memory.failed_approaches.get(agent_type.value, []),
            "successful_patterns": memory.successful_patterns.get(agent_type.value, []),
            "learnings": memory.get_learnings(agent_type),
            "average_iterations": memory.get_average_iterations(agent_type.value),
        }

    def _apply_token_budget(
        self, context: Dict[str, Any], token_budget: int
    ) -> Dict[str, Any]:
        """Apply token budget management to context.

        Args:
            context: The assembled context
            token_budget: Maximum tokens allowed

        Returns:
            Trimmed context
        """
        # TODO: Implement token counting and trimming
        # - Count tokens in each section
        # - Prioritize critical sections
        # - Trim less important sections to fit budget

        context["token_budget"] = token_budget
        context["estimated_tokens"] = self._estimate_tokens(context)

        return context

    def _estimate_tokens(self, context: Dict[str, Any]) -> int:
        """Estimate token count for context.

        Simple estimation: ~4 characters per token on average.

        Args:
            context: The context dictionary

        Returns:
            Estimated token count
        """
        json_str = json.dumps(context)
        return len(json_str) // 4


class AgentOrchestrator:
    """Main orchestrator for coordinating agents.

    Implements:
    - LangGraph-style state machine
    - Agent registry and discovery
    - Task routing
    - State management
    - Execution memory
    - Sequential and parallel execution modes
    - Human approval checkpoints
    - Context assembly
    - JSON logging
    """

    def __init__(
        self,
        state: Optional[OrchestratorState] = None,
        log_dir: Optional[Path] = None,
    ):
        self.state = state or OrchestratorState()
        self.registry = AgentRegistry()
        self.router = TaskRouter(self.registry)
        self.context_assembler = ContextAssembler(self.state)

        # Execution settings
        self.execution_mode = ExecutionMode.SEQUENTIAL
        self.max_workers = 4
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)

        # Logging
        self.log_dir = log_dir or Path("./logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._setup_json_logging()

        # Approval callbacks
        self._approval_handlers: List[Callable[[AgentExecution], None]] = []

        logger.info("AgentOrchestrator initialized")

    def _setup_json_logging(self) -> None:
        """Setup JSON file logging for all agent actions."""
        log_file = (
            self.log_dir
            / f"orchestrator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        )

        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.INFO)

        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)

        # Create a logger for agent actions
        self.action_logger = logging.getLogger("mike.orchestrator.actions")
        self.action_logger.addHandler(handler)
        self.action_logger.setLevel(logging.INFO)

    def log_action(self, action_type: str, data: Dict[str, Any]) -> None:
        """Log an action in JSON format.

        Args:
            action_type: Type of action
            data: Action data
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "session_id": self.state.session.session_id,
            "state": self.state.current_state,
            "data": data,
        }
        self.action_logger.info(json.dumps(log_entry))

    def register_agent(
        self, agent: Agent, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register an agent with the orchestrator.

        Args:
            agent: The agent instance
            metadata: Optional agent metadata
        """
        self.registry.register(agent, metadata)
        self.log_action(
            "agent_registered",
            {
                "agent_type": agent.agent_type.value,
                "metadata": metadata or {},
            },
        )

    def register_approval_handler(
        self, handler: Callable[[AgentExecution], None]
    ) -> None:
        """Register a handler for approval requests.

        Args:
            handler: Function called when approval is needed
        """
        self._approval_handlers.append(handler)

    def execute(
        self,
        query: str,
        agent_type: Optional[AgentType] = None,
        context_overrides: Optional[Dict[str, Any]] = None,
        wait_for_approval: bool = True,
    ) -> AgentExecution:
        """Execute a single agent task.

        Args:
            query: The user query or task
            agent_type: Specific agent type, or None for auto-routing
            context_overrides: Optional context to override defaults
            wait_for_approval: Whether to wait for human approval if required

        Returns:
            The execution record
        """
        # Determine agent type
        if agent_type is None:
            agent_type = self.router.route(query)
            if agent_type is None:
                raise ValueError(f"Could not route query: {query}")

        # Get agent
        agent = self.registry.get(agent_type)
        if agent is None:
            raise ValueError(f"Agent not registered: {agent_type.value}")

        # Create execution record
        execution = AgentExecution(
            agent_type=agent_type,
            query=query,
            context=context_overrides or {},
        )

        # Check if approval is required
        assembled_context = self._assemble_context(query, agent_type)
        execution.requires_approval = agent.requires_approval(query, assembled_context)

        if execution.requires_approval and wait_for_approval:
            execution.status = ExecutionStatus.AWAITING_APPROVAL
            self.state.add_execution(execution)
            self._request_approval(execution)
            return execution

        # Execute
        self._execute_single(execution, agent, assembled_context)

        return execution

    def run(self, query: str, session_id: str = "default", shared_context=None):
        """Full pipeline: classify intent -> plan DAG -> execute."""
        from .dag_executor import DAGResult

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

        self.log_action("plan_created", {
            "query": query, "intent": intent.intent,
            "complexity": intent.complexity.value if hasattr(intent.complexity, 'value') else str(intent.complexity),
            "planner_type": plan.planner_type,
            "node_count": len(plan.nodes), "reasoning": plan.reasoning,
        })

        # Step 3: Execute DAG
        if hasattr(self, "dag_executor") and self.dag_executor:
            result = self.dag_executor.execute_sync(plan, session_id, shared_context)
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

        self.log_action("pipeline_completed", {
            "status": result.status,
            "node_count": len(result.node_results),
            "total_duration_ms": result.total_duration_ms,
        })
        return result

    def execute_batch(
        self,
        tasks: List[Dict[str, Any]],
        mode: ExecutionMode = ExecutionMode.SEQUENTIAL,
    ) -> List[AgentExecution]:
        """Execute multiple tasks.

        Args:
            tasks: List of task dictionaries with 'query' and optional 'agent_type'
            mode: Execution mode (sequential or parallel)

        Returns:
            List of execution records
        """
        if mode == ExecutionMode.SEQUENTIAL:
            return self._execute_sequential(tasks)
        else:
            return self._execute_parallel(tasks)

    def _execute_sequential(self, tasks: List[Dict[str, Any]]) -> List[AgentExecution]:
        """Execute tasks sequentially.

        Args:
            tasks: List of task dictionaries

        Returns:
            List of execution records
        """
        results: List[AgentExecution] = []

        for task in tasks:
            execution = self.execute(
                query=task["query"],
                agent_type=task.get("agent_type"),
                context_overrides=task.get("context"),
                wait_for_approval=task.get("wait_for_approval", True),
            )
            results.append(execution)

            # Stop on failure if configured
            if execution.status == ExecutionStatus.FAILED and task.get(
                "stop_on_failure", True
            ):
                logger.warning(f"Task failed, stopping batch: {execution.error}")
                break

        return results

    def _execute_parallel(self, tasks: List[Dict[str, Any]]) -> List[AgentExecution]:
        """Execute tasks in parallel.

        Args:
            tasks: List of task dictionaries

        Returns:
            List of execution records
        """
        futures = []

        for task in tasks:
            future = self._executor.submit(
                self.execute,
                query=task["query"],
                agent_type=task.get("agent_type"),
                context_overrides=task.get("context"),
                wait_for_approval=task.get("wait_for_approval", False),
            )
            futures.append(future)

        results: List[AgentExecution] = []
        for future in futures:
            try:
                execution = future.result(timeout=300)  # 5 minute timeout
                results.append(execution)
            except Exception as e:
                logger.error(f"Parallel execution failed: {e}")
                # Create failed execution record
                failed_execution = AgentExecution(
                    status=ExecutionStatus.FAILED,
                    error=str(e),
                )
                results.append(failed_execution)

        return results

    def _execute_single(
        self,
        execution: AgentExecution,
        agent: Agent,
        context: Dict[str, Any],
    ) -> None:
        """Execute a single agent task.

        Args:
            execution: The execution record
            agent: The agent to execute
            context: The assembled context
        """
        self.state.transition_to(
            f"executing_{execution.agent_type.value}",
            {"execution_id": execution.execution_id},
        )

        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.now()
        execution.context.update(context)

        self.log_action("execution_started", execution.to_dict())

        try:
            # Execute agent
            result = agent.execute(execution.query, execution.context)

            # Validate result
            if not agent.validate_result(result):
                raise ValueError("Agent returned invalid result")

            # Update execution
            execution.result = result
            execution.status = ExecutionStatus.SUCCESS
            execution.completed_at = datetime.now()

            # Update execution memory
            self._record_success(execution)

            # Update shared context
            if "shared_context" in result:
                for key, value in result["shared_context"].items():
                    self.state.set_shared_context(key, value)

            self.log_action("execution_completed", execution.to_dict())

        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.now()

            # Update execution memory
            self._record_failure(execution, str(e))

            self.state.add_error(str(e), {"execution_id": execution.execution_id})
            self.log_action("execution_failed", execution.to_dict())

            logger.error(f"Execution failed: {e}")

        finally:
            self.state.complete_execution(execution.execution_id)
            self.state.transition_to("idle")

    def _assemble_context(self, query: str, agent_type: AgentType) -> Dict[str, Any]:
        """Assemble context for an agent execution.

        Args:
            query: The user query
            agent_type: The target agent type

        Returns:
            Assembled context
        """
        return self.context_assembler.assemble(query, agent_type)

    def _record_success(self, execution: AgentExecution) -> None:
        """Record successful execution in memory.

        Args:
            execution: The successful execution
        """
        memory = self.state.session.execution_memory

        memory.record_success(
            execution.agent_type,
            {
                "query": execution.query,
                "result_keys": list(execution.result.keys())
                if execution.result
                else [],
                "iteration": execution.iteration,
            },
        )

    def _record_failure(self, execution: AgentExecution, reason: str) -> None:
        """Record failed execution in memory.

        Args:
            execution: The failed execution
            reason: The failure reason
        """
        memory = self.state.session.execution_memory

        memory.record_failure(execution.agent_type, execution.query, reason)

    def _request_approval(self, execution: AgentExecution) -> None:
        """Request human approval for an execution.

        Args:
            execution: The execution awaiting approval
        """
        self.state.session.pending_approvals.append(execution.execution_id)

        for handler in self._approval_handlers:
            try:
                handler(execution)
            except Exception as e:
                logger.error(f"Approval handler failed: {e}")

        self.log_action("approval_requested", execution.to_dict())

    def approve_execution(
        self, execution_id: str, approved: bool, approved_by: Optional[str] = None
    ) -> None:
        """Approve or reject an execution.

        Args:
            execution_id: The execution ID
            approved: Whether to approve
            approved_by: Identifier of approver
        """
        execution = self.state.get_execution(execution_id)
        if execution is None:
            raise ValueError(f"Execution not found: {execution_id}")

        if execution_id in self.state.session.pending_approvals:
            self.state.session.pending_approvals.remove(execution_id)

        if approved:
            execution.approved_by = approved_by or "unknown"
            execution.approved_at = datetime.now()
            execution.requires_approval = False

            # Get agent and execute
            agent = self.registry.get(execution.agent_type)
            if agent:
                assembled_context = self._assemble_context(
                    execution.query, execution.agent_type
                )
                self._execute_single(execution, agent, assembled_context)

            self.log_action("execution_approved", execution.to_dict())
        else:
            execution.status = ExecutionStatus.CANCELLED
            execution.completed_at = datetime.now()
            self.state.complete_execution(execution_id)

            self.log_action("execution_rejected", execution.to_dict())

    def retry_execution(
        self, execution_id: str, max_retries: int = 3
    ) -> Optional[AgentExecution]:
        """Retry a failed execution.

        Args:
            execution_id: The execution ID to retry
            max_retries: Maximum number of retry attempts

        Returns:
            The new execution record, or None if max retries exceeded
        """
        execution = self.state.get_execution(execution_id)
        if execution is None:
            raise ValueError(f"Execution not found: {execution_id}")

        if execution.iteration >= max_retries:
            logger.warning(f"Max retries exceeded for execution: {execution_id}")
            return None

        # Create new execution with incremented iteration
        new_execution = AgentExecution(
            agent_type=execution.agent_type,
            query=execution.query,
            context=execution.context.copy(),
            iteration=execution.iteration + 1,
            max_iterations=max_retries,
            previous_attempts=execution.previous_attempts + [execution_id],
        )

        # Add failure reason to context
        if execution.error:
            new_execution.failure_reasons.append(execution.error)

        self.log_action(
            "execution_retry",
            {
                "original_execution_id": execution_id,
                "new_execution_id": new_execution.execution_id,
                "iteration": new_execution.iteration,
            },
        )

        # Execute
        agent = self.registry.get(new_execution.agent_type)
        if agent:
            assembled_context = self._assemble_context(
                new_execution.query, new_execution.agent_type
            )
            # Add retry context
            assembled_context["retry_context"] = {
                "iteration": new_execution.iteration,
                "previous_failures": new_execution.failure_reasons,
            }
            self._execute_single(new_execution, agent, assembled_context)

        return new_execution

    def save_state(self, filepath: Optional[Path] = None) -> Path:
        """Save orchestrator state to file.

        Args:
            filepath: Optional filepath, defaults to log_dir

        Returns:
            Path to saved file
        """
        if filepath is None:
            filepath = self.log_dir / f"state_{self.state.session.session_id}.json"

        self.state.save_to_file(filepath)
        logger.info(f"State saved to: {filepath}")

        return filepath

    def load_state(self, filepath: Path) -> None:
        """Load orchestrator state from file.

        Args:
            filepath: Path to state file
        """
        self.state = OrchestratorState.load_from_file(filepath)
        self.context_assembler = ContextAssembler(self.state)

        logger.info(f"State loaded from: {filepath}")

    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status.

        Returns:
            Status dictionary
        """
        return {
            "current_state": self.state.current_state,
            "session_id": self.state.session.session_id,
            "registered_agents": self.registry.list_agents(),
            "active_executions": len(self.state.active_executions),
            "completed_executions": len(self.state.completed_executions),
            "pending_approvals": len(self.state.session.pending_approvals),
            "errors": len(self.state.errors),
        }

    def shutdown(self) -> None:
        """Shutdown the orchestrator gracefully."""
        logger.info("Shutting down orchestrator")

        # Cancel pending executions
        for execution_id, execution in list(self.state.active_executions.items()):
            execution.status = ExecutionStatus.CANCELLED
            self.state.complete_execution(execution_id)
            self.log_action("execution_cancelled_shutdown", execution.to_dict())

        # Shutdown executor
        self._executor.shutdown(wait=True)

        # Save final state
        self.save_state()

        logger.info("Orchestrator shutdown complete")
