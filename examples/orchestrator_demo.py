"""Example usage of the Agent Orchestrator.

This demonstrates how to use the orchestrator with all four agent types.
"""

from pathlib import Path
from mike.orchestrator import AgentOrchestrator, AgentType
from mike.orchestrator.engine import Agent


class DocumentationAgent(Agent):
    """Example Documentation Agent implementation."""

    def __init__(self):
        super().__init__(AgentType.DOCUMENTATION, {"model": "kimi-k2.5"})

    def execute(self, query: str, context: dict) -> dict:
        self.log_action("generating_docs", {"query": query})

        # Simulate documentation generation
        return {
            "status": "success",
            "documents": ["README.md", "ARCHITECTURE.md", "API_REFERENCE.md"],
            "summary": f"Generated documentation for query: {query}",
            "shared_context": {"last_doc_generation": context.get("session_id")},
        }

    def requires_approval(self, query: str, context: dict) -> bool:
        # Large documentation tasks require approval
        return "project" in query.lower() or "full" in query.lower()


class QAAgent(Agent):
    """Example Q&A Agent implementation."""

    def __init__(self):
        super().__init__(AgentType.QA, {"model": "phi-4"})

    def execute(self, query: str, context: dict) -> dict:
        self.log_action("answering_question", {"query": query})

        # Simulate Q&A
        return {
            "status": "success",
            "answer": f"Answer to: {query}",
            "sources": ["file1.py:45", "file2.py:120"],
            "confidence": 0.95,
        }

    def requires_approval(self, query: str, context: dict) -> bool:
        return False  # Q&A doesn't need approval


class RefactorAgent(Agent):
    """Example Refactor Agent implementation."""

    def __init__(self):
        super().__init__(AgentType.REFACTOR, {"model": "deepseek-v3.2"})

    def execute(self, query: str, context: dict) -> dict:
        self.log_action("analyzing_code", {"query": query})

        # Simulate refactor analysis
        return {
            "status": "success",
            "suggestions": [
                {"type": "extract_method", "file": "main.py", "line": 45},
                {"type": "remove_duplicate", "file": "utils.py", "line": 120},
            ],
            "shared_context": {"refactor_candidates": ["main.py", "utils.py"]},
        }

    def requires_approval(self, query: str, context: dict) -> bool:
        # All refactor suggestions require approval before applying
        return True


class RebuilderAgent(Agent):
    """Example Rebuilder Agent implementation."""

    def __init__(self):
        super().__init__(AgentType.REBUILDER, {"model": "exaone-4.0-32b"})

    def execute(self, query: str, context: dict) -> dict:
        self.log_action("scaffolding_project", {"query": query})

        # Simulate project scaffolding
        return {
            "status": "success",
            "scaffolded_files": [
                "src/main.py",
                "src/models.py",
                "src/api.py",
                "tests/test_main.py",
                "README.md",
            ],
            "architecture_template": context.get("shared", {}).get(
                "last_doc_generation"
            ),
            "shared_context": {"scaffolded": True},
        }

    def requires_approval(self, query: str, context: dict) -> bool:
        # Rebuilder always requires human approval
        return True


def main():
    """Demonstrate orchestrator usage."""

    print("=" * 60)
    print("Mike Agent Orchestrator Demo")
    print("=" * 60)

    # Initialize orchestrator
    orchestrator = AgentOrchestrator(log_dir=Path("./orchestrator_logs"))

    # Register agents
    orchestrator.register_agent(
        DocumentationAgent(), {"description": "Generates documentation"}
    )
    orchestrator.register_agent(
        QAAgent(), {"description": "Answers questions about code"}
    )
    orchestrator.register_agent(
        RefactorAgent(), {"description": "Suggests code improvements"}
    )
    orchestrator.register_agent(
        RebuilderAgent(), {"description": "Scaffolds new projects"}
    )

    print("\n📋 Registered Agents:")
    for agent_type in orchestrator.registry.list_agents():
        print(f"  - {agent_type}")

    # Example 1: Q&A (auto-routed)
    print("\n🔍 Example 1: Q&A Query")
    execution = orchestrator.execute("Where is authentication handled?")
    print(f"  Status: {execution.status.name}")
    print(f"  Result: {execution.result}")

    # Example 2: Documentation (auto-routed)
    print("\n📝 Example 2: Documentation Request")
    execution = orchestrator.execute("Generate full project documentation")
    print(f"  Status: {execution.status.name}")
    if execution.requires_approval:
        print(f"  ⚠️  Requires approval - execution_id: {execution.execution_id}")
        # In real usage, would wait for human approval
        orchestrator.approve_execution(
            execution.execution_id, approved=True, approved_by="demo_user"
        )
        print(f"  Status after approval: {execution.status.name}")

    # Example 3: Refactor
    print("\n🔧 Example 3: Refactor Request")
    execution = orchestrator.execute(
        "Refactor the authentication module", agent_type=AgentType.REFACTOR
    )
    print(f"  Status: {execution.status.name}")
    print(f"  Result keys: {list(execution.result.keys()) if execution.result else []}")

    # Example 4: Batch execution (parallel)
    print("\n⚡ Example 4: Batch Execution (Parallel)")
    tasks = [
        {"query": "What does the payment module do?"},
        {"query": "Where are the database models?"},
        {"query": "Explain the API structure"},
    ]
    results = orchestrator.execute_batch(tasks, mode=orchestrator.execution_mode)
    print(f"  Completed {len(results)} tasks")
    for i, result in enumerate(results):
        print(f"    Task {i + 1}: {result.status.name}")

    # Show execution memory
    print("\n🧠 Execution Memory:")
    memory = orchestrator.state.session.execution_memory
    for agent_type in AgentType:
        learnings = memory.get_learnings(agent_type)
        if learnings:
            print(f"  {agent_type.value}: {len(learnings)} learnings")

    # Show status
    print("\n📊 Orchestrator Status:")
    status = orchestrator.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")

    # Save state
    state_file = orchestrator.save_state()
    print(f"\n💾 State saved to: {state_file}")

    # Shutdown
    orchestrator.shutdown()
    print("\n✅ Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
