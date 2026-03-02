"""Unit tests for IterativeGenerator."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from architectai.agents.iterative_generator import (
    IterativeGenerator,
    IterationResult,
    IterationStatus,
)
from architectai.agents.code_executor import ExecutionResult, ExecutionStatus


class TestIterativeGenerator:
    """Test cases for IterativeGenerator."""

    def test_initialization(self):
        """Test generator initialization."""
        generator = IterativeGenerator()

        assert generator.max_iterations == 3
        assert generator.code_executor is not None
        assert generator.code_generator is not None
        assert generator.enable_tests is True

    def test_initialization_with_custom_params(self):
        """Test initialization with custom parameters."""
        mock_code_gen = MagicMock()
        mock_executor = MagicMock()

        generator = IterativeGenerator(
            code_generator=mock_code_gen,
            code_executor=mock_executor,
            max_iterations=5,
            enable_tests=False,
        )

        assert generator.max_iterations == 5
        assert generator.code_generator == mock_code_gen
        assert generator.code_executor == mock_executor
        assert generator.enable_tests is False

    def test_build_context(self):
        """Test context building."""
        generator = IterativeGenerator()

        file_spec = MagicMock()
        file_spec.path = "src/main.py"
        file_spec.purpose = "Main module"
        file_spec.dependencies = ["src/utils.py"]
        file_spec.template_hints = {"type": "main"}

        plan = MagicMock()
        plan.project_name = "test-project"
        plan.description = "A test project"
        plan.target_language = "python"
        plan.target_framework = "fastapi"
        plan.architecture_pattern = "layered"
        plan.constraints = ["auth"]

        generated_files = {"src/utils.py": "def helper(): pass"}

        context = generator._build_context(
            file_spec=file_spec,
            plan=plan,
            template=None,
            generated_files=generated_files,
        )

        assert context["project_name"] == "test-project"
        assert context["target_language"] == "python"
        assert context["file_purpose"] == "Main module"
        assert "src/utils.py" in context["dependencies"]

    def test_extract_error_info(self):
        """Test error info extraction."""
        generator = IterativeGenerator()

        execution_result = ExecutionResult(
            success=False,
            stdout="",
            stderr="SyntaxError: invalid syntax",
            return_code=1,
            status=ExecutionStatus.FAILURE,
            execution_time=0.1,
            files_created=[],
        )

        error_info = generator._extract_error_info(execution_result)

        assert "SyntaxError" in error_info

    def test_extract_error_info_unknown(self):
        """Test error info extraction with no stderr."""
        generator = IterativeGenerator()

        execution_result = ExecutionResult(
            success=False,
            stdout="",
            stderr="",
            return_code=1,
            status=ExecutionStatus.FAILURE,
            execution_time=0.1,
            files_created=[],
        )

        error_info = generator._extract_error_info(execution_result)

        assert "Unknown error" in error_info

    def test_run_tests_for_file_no_test_file(self, tmp_path):
        """Test running tests when no test file exists."""
        generator = IterativeGenerator()

        file_spec = MagicMock()
        file_spec.path = "src/main.py"

        result = generator._run_tests_for_file(file_spec, tmp_path, "python")

        assert result.success is True
        assert "No tests found" in result.stdout

    def test_fix_code_based_on_errors(self):
        """Test code fixing based on errors."""
        mock_code_gen = MagicMock()
        mock_code_gen._call_ollama.return_value = (
            "```python\\ndef add(a, b):\\n    return a + b\\n```"
        )
        mock_code_gen._clean_generated_code.return_value = (
            "def add(a, b):\\n    return a + b"
        )

        generator = IterativeGenerator(code_generator=mock_code_gen)

        file_spec = MagicMock()
        file_spec.purpose = "Add two numbers"

        plan = MagicMock()
        plan.target_language = "python"

        fixed_code = generator._fix_code_based_on_errors(
            current_code="def add(a b): return a + b",
            error_info="SyntaxError: invalid syntax",
            language="python",
            file_spec=file_spec,
            plan=plan,
        )

        assert fixed_code == "def add(a, b):\\n    return a + b"
        mock_code_gen._call_ollama.assert_called_once()

    def test_fix_code_fallback_on_error(self):
        """Test that original code is returned when fix fails."""
        mock_code_gen = MagicMock()
        mock_code_gen._call_ollama.side_effect = Exception("LLM error")

        generator = IterativeGenerator(code_generator=mock_code_gen)

        file_spec = MagicMock()
        file_spec.purpose = "Test"

        plan = MagicMock()
        plan.target_language = "python"

        original_code = "def add(a b): return a + b"

        fixed_code = generator._fix_code_based_on_errors(
            current_code=original_code,
            error_info="SyntaxError",
            language="python",
            file_spec=file_spec,
            plan=plan,
        )

        assert fixed_code == original_code

    def test_iteration_status_values(self):
        """Test IterationStatus enum values."""
        assert IterationStatus.SUCCESS.value == "success"
        assert IterationStatus.MAX_ITERATIONS.value == "max_iterations_reached"
        assert IterationStatus.FAILED.value == "failed"
        assert IterationStatus.ERROR.value == "error"

    def test_iteration_result_dataclass(self):
        """Test IterationResult dataclass."""
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
        assert result.execution_results == []
        assert result.fixes_applied == []
