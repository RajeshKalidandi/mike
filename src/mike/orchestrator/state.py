"""State management for the Agent Orchestrator.

Provides data structures for tracking session state, agent execution history,
and execution memory to prevent repeated failures.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable


class AgentType(Enum):
    """Supported agent types."""

    DOCUMENTATION = "docs"
    QA = "qa"
    REFACTOR = "refactor"
    REBUILDER = "rebuild"


class ExecutionStatus(Enum):
    """Status of an agent execution."""

    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    CANCELLED = auto()
    AWAITING_APPROVAL = auto()


class ExecutionMode(Enum):
    """Execution mode for agent tasks."""

    SEQUENTIAL = auto()
    PARALLEL = auto()


@dataclass
class AgentExecution:
    """Record of a single agent execution.

    Tracks what was tried, what failed, and what succeeded to enable
    execution memory and prevent repeated failures.
    """

    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_type: AgentType = AgentType.QA
    status: ExecutionStatus = ExecutionStatus.PENDING

    # Input/Output
    query: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Iteration tracking
    iteration: int = 0
    max_iterations: int = 10

    # Human approval
    requires_approval: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

    # Execution memory
    previous_attempts: List[str] = field(default_factory=list)
    failure_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "execution_id": self.execution_id,
            "agent_type": self.agent_type.value,
            "status": self.status.name,
            "query": self.query,
            "context": self.context,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "requires_approval": self.requires_approval,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "previous_attempts": self.previous_attempts,
            "failure_reasons": self.failure_reasons,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AgentExecution:
        """Create from dictionary."""
        return cls(
            execution_id=data["execution_id"],
            agent_type=AgentType(data["agent_type"]),
            status=ExecutionStatus[data["status"]],
            query=data.get("query", ""),
            context=data.get("context", {}),
            result=data.get("result"),
            error=data.get("error"),
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"])
            if data.get("started_at")
            else None,
            completed_at=datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None,
            iteration=data.get("iteration", 0),
            max_iterations=data.get("max_iterations", 10),
            requires_approval=data.get("requires_approval", False),
            approved_by=data.get("approved_by"),
            approved_at=datetime.fromisoformat(data["approved_at"])
            if data.get("approved_at")
            else None,
            previous_attempts=data.get("previous_attempts", []),
            failure_reasons=data.get("failure_reasons", []),
        )


@dataclass
class SessionContext:
    """Context for the current session.

    Maintains session-wide state including codebase information,
    agent configurations, and shared context.
    """

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_name: str = "default"
    codebase_path: Optional[Path] = None

    # Memory stores
    structural_memory: Dict[str, Any] = field(
        default_factory=dict
    )  # AST, dependency graph
    semantic_memory: Dict[str, Any] = field(default_factory=dict)  # Embeddings, chunks
    execution_memory: ExecutionMemory = field(default_factory=lambda: ExecutionMemory())

    # Configuration
    model_config: Dict[str, Any] = field(default_factory=dict)
    agent_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # State tracking
    current_execution: Optional[AgentExecution] = None
    execution_history: List[AgentExecution] = field(default_factory=list)
    pending_approvals: List[str] = field(default_factory=list)

    # Context assembly cache
    context_cache: Dict[str, Any] = field(default_factory=dict)
    cache_timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "codebase_path": str(self.codebase_path) if self.codebase_path else None,
            "structural_memory": self.structural_memory,
            "semantic_memory": self.semantic_memory,
            "execution_memory": self.execution_memory.to_dict(),
            "model_config": self.model_config,
            "agent_configs": self.agent_configs,
            "execution_history": [e.to_dict() for e in self.execution_history],
            "pending_approvals": self.pending_approvals,
            "cache_timestamp": self.cache_timestamp.isoformat()
            if self.cache_timestamp
            else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SessionContext:
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            session_name=data.get("session_name", "default"),
            codebase_path=Path(data["codebase_path"])
            if data.get("codebase_path")
            else None,
            structural_memory=data.get("structural_memory", {}),
            semantic_memory=data.get("semantic_memory", {}),
            execution_memory=ExecutionMemory.from_dict(
                data.get("execution_memory", {})
            ),
            model_config=data.get("model_config", {}),
            agent_configs=data.get("agent_configs", {}),
            execution_history=[
                AgentExecution.from_dict(e) for e in data.get("execution_history", [])
            ],
            pending_approvals=data.get("pending_approvals", []),
            cache_timestamp=datetime.fromisoformat(data["cache_timestamp"])
            if data.get("cache_timestamp")
            else None,
        )


@dataclass
class ExecutionMemory:
    """Execution memory to prevent repeated failures.

    Tracks what agents have tried, what failed, and why.
    Enables learning from past mistakes within a session.
    """

    # Failed approaches with reasons
    failed_approaches: Dict[str, List[str]] = field(default_factory=dict)

    # Successful patterns
    successful_patterns: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

    # Agent-specific learnings
    agent_learnings: Dict[str, List[str]] = field(default_factory=dict)

    # Iteration history per query type
    iteration_history: Dict[str, List[int]] = field(default_factory=dict)

    # Context that worked well
    effective_contexts: List[Dict[str, Any]] = field(default_factory=list)

    def record_failure(self, agent_type: AgentType, approach: str, reason: str) -> None:
        """Record a failed approach."""
        key = agent_type.value
        if key not in self.failed_approaches:
            self.failed_approaches[key] = []
        self.failed_approaches[key].append(f"{approach}: {reason}")

    def record_success(self, agent_type: AgentType, pattern: Dict[str, Any]) -> None:
        """Record a successful pattern."""
        key = agent_type.value
        if key not in self.successful_patterns:
            self.successful_patterns[key] = []
        self.successful_patterns[key].append(pattern)

    def has_failed_before(self, agent_type: AgentType, approach: str) -> bool:
        """Check if an approach has failed before."""
        key = agent_type.value
        if key not in self.failed_approaches:
            return False
        return any(approach in failure for failure in self.failed_approaches[key])

    def get_learnings(self, agent_type: AgentType) -> List[str]:
        """Get accumulated learnings for an agent."""
        return self.agent_learnings.get(agent_type.value, [])

    def add_learning(self, agent_type: AgentType, learning: str) -> None:
        """Add a learning for an agent."""
        key = agent_type.value
        if key not in self.agent_learnings:
            self.agent_learnings[key] = []
        self.agent_learnings[key].append(learning)

    def record_iteration(self, query_type: str, iteration_count: int) -> None:
        """Record iteration count for a query type."""
        if query_type not in self.iteration_history:
            self.iteration_history[query_type] = []
        self.iteration_history[query_type].append(iteration_count)

    def get_average_iterations(self, query_type: str) -> float:
        """Get average iterations for a query type."""
        history = self.iteration_history.get(query_type, [])
        if not history:
            return 0.0
        return sum(history) / len(history)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "failed_approaches": self.failed_approaches,
            "successful_patterns": self.successful_patterns,
            "agent_learnings": self.agent_learnings,
            "iteration_history": self.iteration_history,
            "effective_contexts": self.effective_contexts,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExecutionMemory:
        """Create from dictionary."""
        return cls(
            failed_approaches=data.get("failed_approaches", {}),
            successful_patterns=data.get("successful_patterns", {}),
            agent_learnings=data.get("agent_learnings", {}),
            iteration_history=data.get("iteration_history", {}),
            effective_contexts=data.get("effective_contexts", []),
        )


@dataclass
class OrchestratorState:
    """Main state container for the orchestrator.

    Implements a LangGraph-style state machine with:
    - Current state tracking
    - Transition history
    - Shared context between agents
    """

    # State machine
    current_state: str = "idle"
    previous_state: Optional[str] = None
    state_history: List[Dict[str, Any]] = field(default_factory=list)

    # Session context
    session: SessionContext = field(default_factory=SessionContext)

    # Active executions
    active_executions: Dict[str, AgentExecution] = field(default_factory=dict)
    completed_executions: List[AgentExecution] = field(default_factory=list)

    # Shared context for agent communication
    shared_context: Dict[str, Any] = field(default_factory=dict)

    # Human approval queue
    approval_callbacks: Dict[str, Callable[[bool, Optional[str]], None]] = field(
        default_factory=dict
    )

    # Error tracking
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def transition_to(
        self, new_state: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Transition to a new state."""
        self.previous_state = self.current_state
        self.current_state = new_state

        self.state_history.append(
            {
                "from_state": self.previous_state,
                "to_state": new_state,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
            }
        )

    def add_execution(self, execution: AgentExecution) -> None:
        """Add an execution to active executions."""
        self.active_executions[execution.execution_id] = execution

    def complete_execution(self, execution_id: str) -> None:
        """Move execution from active to completed."""
        if execution_id in self.active_executions:
            execution = self.active_executions.pop(execution_id)
            self.completed_executions.append(execution)
            self.session.execution_history.append(execution)

    def get_execution(self, execution_id: str) -> Optional[AgentExecution]:
        """Get an execution by ID."""
        return self.active_executions.get(execution_id) or next(
            (e for e in self.completed_executions if e.execution_id == execution_id),
            None,
        )

    def add_error(self, error: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Add an error to the error log."""
        self.errors.append(
            {
                "error": error,
                "timestamp": datetime.now().isoformat(),
                "context": context or {},
            }
        )

    def set_shared_context(self, key: str, value: Any) -> None:
        """Set a value in shared context."""
        self.shared_context[key] = value

    def get_shared_context(self, key: str, default: Any = None) -> Any:
        """Get a value from shared context."""
        return self.shared_context.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "current_state": self.current_state,
            "previous_state": self.previous_state,
            "state_history": self.state_history,
            "session": self.session.to_dict(),
            "active_executions": {
                k: v.to_dict() for k, v in self.active_executions.items()
            },
            "completed_executions": [e.to_dict() for e in self.completed_executions],
            "shared_context": self.shared_context,
            "errors": self.errors,
        }

    def save_to_file(self, filepath: Path) -> None:
        """Save state to JSON file."""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> OrchestratorState:
        """Create from dictionary."""
        state = cls(
            current_state=data.get("current_state", "idle"),
            previous_state=data.get("previous_state"),
            state_history=data.get("state_history", []),
            session=SessionContext.from_dict(data.get("session", {})),
            shared_context=data.get("shared_context", {}),
            errors=data.get("errors", []),
        )

        # Restore executions
        for exec_data in data.get("active_executions", {}).values():
            state.active_executions[exec_data["execution_id"]] = (
                AgentExecution.from_dict(exec_data)
            )

        for exec_data in data.get("completed_executions", []):
            state.completed_executions.append(AgentExecution.from_dict(exec_data))

        return state

    @classmethod
    def load_from_file(cls, filepath: Path) -> OrchestratorState:
        """Load state from JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)
