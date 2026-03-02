"""Integration tests for Rebuilder Agent M8 features."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from architectai.agents.rebuilder_agent import (
    RebuilderAgent,
    RebuilderWorkflow,
    ArchitectureTemplate,
    ArchitecturePattern,
    FileSpec,
    BuildPlan,
    BuildPlanStatus,
)
from architectai.agents.code_executor import CodeExecutor
from architectai.agents.iterative_generator import IterativeGenerator


class TestRebuilderIntegration:
    """Integration tests for Rebuilder Agent workflow."""

    def test_rebuilder_agent_with_iterative_components(self, tmp_path):
        """Test that RebuilderAgent initializes with iterative components."""
        agent = RebuilderAgent(output_dir=str(tmp_path))

        # Check that iterative components are initialized
        assert hasattr(agent, "code_executor")
        assert hasattr(agent, "iterative_generator")
        assert isinstance(agent.code_executor, CodeExecutor)
        assert isinstance(agent.iterative_generator, IterativeGenerator)

    def test_end_to_end_scaffolding(self, tmp_path):
        """Test project scaffolding without LLM calls."""
        agent = RebuilderAgent(
            model_name="mock-model",
            output_dir=str(tmp_path),
        )

        # Create a simple template
        template = ArchitectureTemplate(
            source_repo="/test",
            languages=["python"],
            frameworks=[],
            patterns=[],
            directory_structure={},
            dependencies={},
            file_templates={},
            config_patterns={},
            entry_points=[],
            tests_structure=None,
            documentation_structure=None,
        )

        plan = agent.generate_build_plan(
            template=template,
            project_name="test-project",
            description="A test project",
            constraints=[],
        )

        # Scaffold
        project_path = agent.scaffold_project(plan)

        assert Path(project_path).exists()
        assert (Path(project_path) / "README.md").exists()

    def test_rebuilder_agent_generate_with_constraints(self, tmp_path):
        """Test build plan generation with constraints."""
        agent = RebuilderAgent(output_dir=str(tmp_path))

        template = ArchitectureTemplate(
            source_repo="/test",
            languages=["python"],
            frameworks=["fastapi"],
            patterns=[],
            directory_structure={},
            dependencies={},
            file_templates={},
            config_patterns={},
            entry_points=["main.py"],
            tests_structure=None,
            documentation_structure=None,
        )

        plan = agent.generate_build_plan(
            template=template,
            project_name="test-project",
            description="A test project",
            constraints=["multi-tenant", "auth"],
        )

        assert plan.project_name == "test-project"
        assert plan.target_language == "python"
        assert "multi-tenant" in plan.constraints
        assert "auth" in plan.constraints

        # Check that constraint-specific files are added
        file_paths = [f.path for f in plan.files]
        assert any("tenant" in fp for fp in file_paths)
        assert any("auth" in fp for fp in file_paths)

    def test_apply_constraints_to_existing_plan(self, tmp_path):
        """Test applying new constraints to an existing plan."""
        agent = RebuilderAgent(output_dir=str(tmp_path))

        # Create initial plan
        template = ArchitectureTemplate(
            source_repo="/test",
            languages=["python"],
            frameworks=[],
            patterns=[],
            directory_structure={},
            dependencies={},
            file_templates={},
            config_patterns={},
            entry_points=[],
            tests_structure=None,
            documentation_structure=None,
        )

        plan = agent.generate_build_plan(
            template=template,
            project_name="test-project",
            description="A test project",
            constraints=[],
        )

        initial_file_count = len(plan.files)

        # Apply new constraints
        plan = agent.apply_constraints(plan, ["redis"])

        assert "redis" in plan.constraints
        assert len(plan.files) > initial_file_count

        # Check that redis files are added
        file_paths = [f.path for f in plan.files]
        assert any("redis" in fp or "cache" in fp for fp in file_paths)

    def test_self_review_functionality(self, tmp_path):
        """Test self-review functionality."""
        agent = RebuilderAgent(output_dir=str(tmp_path))

        # Create a plan
        template = ArchitectureTemplate(
            source_repo="/test",
            languages=["python"],
            frameworks=[],
            patterns=[],
            directory_structure={},
            dependencies={},
            file_templates={},
            config_patterns={},
            entry_points=[],
            tests_structure=None,
            documentation_structure=None,
        )

        plan = agent.generate_build_plan(
            template=template,
            project_name="test-project",
            description="A test project",
            constraints=[],
        )

        # Scaffold project
        project_path = agent.scaffold_project(plan)

        # Run self-review
        review = agent.self_review(plan, project_path)

        assert review.passed is not None
        assert review.coverage_score is not None
        assert isinstance(review.issues, list)
        assert isinstance(review.suggestions, list)

    def test_export_import_build_plan(self, tmp_path):
        """Test exporting and importing build plans."""
        agent = RebuilderAgent(output_dir=str(tmp_path))

        # Create a plan
        template = ArchitectureTemplate(
            source_repo="/test",
            languages=["python"],
            frameworks=[],
            patterns=[],
            directory_structure={},
            dependencies={},
            file_templates={},
            config_patterns={},
            entry_points=[],
            tests_structure=None,
            documentation_structure=None,
        )

        original_plan = agent.generate_build_plan(
            template=template,
            project_name="test-project",
            description="A test project",
            constraints=["auth"],
        )

        # Export plan
        plan_path = agent.export_plan(original_plan, str(tmp_path / "plan.json"))
        assert Path(plan_path).exists()

        # Import plan
        imported_plan = agent.import_plan(plan_path)

        assert imported_plan.project_name == original_plan.project_name
        assert imported_plan.target_language == original_plan.target_language
        assert imported_plan.constraints == original_plan.constraints
        assert len(imported_plan.files) == len(original_plan.files)


class TestRebuilderWorkflowIntegration:
    """Integration tests for RebuilderWorkflow."""

    def test_workflow_initialization(self):
        """Test RebuilderWorkflow initialization."""
        workflow = RebuilderWorkflow()

        assert workflow.agent is not None
        assert workflow.current_plan is None
        assert workflow.current_template is None

    def test_workflow_with_custom_agent(self, tmp_path):
        """Test RebuilderWorkflow with custom agent."""
        agent = RebuilderAgent(output_dir=str(tmp_path))
        workflow = RebuilderWorkflow(agent=agent)

        assert workflow.agent == agent

    @pytest.mark.skip(reason="Requires Ollama mock or full integration test")
    def test_full_workflow_execution(self, tmp_path):
        """Test full workflow execution (requires LLM)."""
        # This test is skipped by default as it requires Ollama
        pass


class TestCodeExecutorIntegration:
    """Integration tests for CodeExecutor."""

    def test_execute_python_simple_script(self, tmp_path):
        """Test executing a simple Python script."""
        executor = CodeExecutor()

        code = """
result = 2 + 2
print(f"Result: {result}")
"""
        result = executor.execute_python(code, tmp_path)

        assert result.success is True
        assert "Result: 4" in result.stdout
        assert result.return_code == 0

    def test_execute_python_with_error(self, tmp_path):
        """Test executing Python code with error."""
        executor = CodeExecutor()

        code = "1 / 0"  # Division by zero
        result = executor.execute_python(code, tmp_path)

        assert result.success is False
        assert "ZeroDivisionError" in result.stderr

    def test_validate_syntax_python(self):
        """Test Python syntax validation."""
        executor = CodeExecutor()

        # Valid code
        valid_code = "def add(a, b):\n    return a + b"
        is_valid, error = executor.validate_syntax(valid_code, "python")
        assert is_valid is True
        assert error is None

        # Invalid code
        invalid_code = "def add(a, b)\n    return a + b"
        is_valid, error = executor.validate_syntax(invalid_code, "python")
        assert is_valid is False
        assert error is not None

    def test_security_pattern_detection(self, tmp_path):
        """Test security pattern detection."""
        executor = CodeExecutor()

        code_with_eval = "eval('1 + 1')"
        result = executor.execute_python(code_with_eval, tmp_path)

        assert result.success is False
        assert "Security check failed" in result.stderr


class TestIterativeGeneratorIntegration:
    """Integration tests for IterativeGenerator."""

    def test_iteration_result_creation(self):
        """Test creating IterationResult."""
        from architectai.agents.iterative_generator import (
            IterationResult,
            IterationStatus,
        )

        result = IterationResult(
            success=True,
            file_path="src/main.py",
            final_content="def main(): pass",
            iterations=1,
            status=IterationStatus.SUCCESS,
        )

        assert result.success is True
        assert result.file_path == "src/main.py"
        assert result.iterations == 1
        assert result.status == IterationStatus.SUCCESS

    def test_build_context_integration(self):
        """Test context building with real objects."""
        from architectai.agents.iterative_generator import IterativeGenerator

        generator = IterativeGenerator()

        # Create mock file_spec
        file_spec = MagicMock()
        file_spec.path = "src/main.py"
        file_spec.purpose = "Main module"
        file_spec.dependencies = ["src/utils.py"]
        file_spec.template_hints = {"type": "main"}

        # Create mock plan
        plan = MagicMock()
        plan.project_name = "test-project"
        plan.description = "Test description"
        plan.target_language = "python"
        plan.target_framework = "fastapi"
        plan.architecture_pattern = "layered"
        plan.constraints = ["auth"]

        context = generator._build_context(
            file_spec=file_spec,
            plan=plan,
            template=None,
            generated_files={"src/utils.py": "def helper(): pass"},
        )

        assert context["project_name"] == "test-project"
        assert context["target_language"] == "python"
        assert "src/utils.py" in context["dependencies"]
