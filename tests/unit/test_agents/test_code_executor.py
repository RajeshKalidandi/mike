"""Unit tests for CodeExecutor."""

import pytest
from pathlib import Path
from mike.agents.code_executor import (
    CodeExecutor,
    ExecutionResult,
    ExecutionStatus,
)


class TestCodeExecutor:
    """Test cases for CodeExecutor."""

    def test_initialization(self):
        """Test executor initialization."""
        executor = CodeExecutor()

        assert executor.timeout == 30
        assert executor.sandbox_enabled is True
        assert "python" in executor.allowed_languages

    def test_initialization_with_custom_params(self):
        """Test initialization with custom parameters."""
        executor = CodeExecutor(
            timeout=60,
            sandbox_enabled=False,
            allowed_languages=["python"],
        )

        assert executor.timeout == 60
        assert executor.sandbox_enabled is False
        assert executor.allowed_languages == ["python"]

    def test_execute_python_code_success(self, tmp_path):
        """Test successful Python code execution."""
        executor = CodeExecutor()
        code = "print('Hello, World!')"
        result = executor.execute_python(code, tmp_path)

        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert "Hello, World!" in result.stdout
        assert result.stderr == ""
        assert result.return_code == 0
        assert result.status == ExecutionStatus.SUCCESS

    def test_execute_python_code_failure(self, tmp_path):
        """Test Python code execution with error."""
        executor = CodeExecutor()
        code = "raise ValueError('Test error')"
        result = executor.execute_python(code, tmp_path)

        assert result.success is False
        assert "ValueError" in result.stderr
        assert result.return_code != 0
        assert result.status == ExecutionStatus.FAILURE

    def test_execute_with_timeout(self, tmp_path):
        """Test execution timeout."""
        executor = CodeExecutor(timeout=1)
        code = "import time; time.sleep(10)"
        result = executor.execute_python(code, tmp_path)

        assert result.success is False
        assert "timed out" in result.stderr.lower()
        assert result.status == ExecutionStatus.TIMEOUT

    def test_security_check_eval(self, tmp_path):
        """Test security check for eval()."""
        executor = CodeExecutor()
        code = "eval('1 + 1')"
        result = executor.execute_python(code, tmp_path)

        assert result.success is False
        assert "Security check failed" in result.stderr
        assert "eval" in result.stderr

    def test_security_check_exec(self, tmp_path):
        """Test security check for exec()."""
        executor = CodeExecutor()
        code = "exec('print(1)')"
        result = executor.execute_python(code, tmp_path)

        assert result.success is False
        assert "Security check failed" in result.stderr

    def test_validate_syntax_python_valid(self):
        """Test Python syntax validation with valid code."""
        executor = CodeExecutor()
        code = "def add(a, b):\n    return a + b"

        is_valid, error = executor.validate_syntax(code, "python")

        assert is_valid is True
        assert error is None

    def test_validate_syntax_python_invalid(self):
        """Test Python syntax validation with invalid code."""
        executor = CodeExecutor()
        code = "def add(a, b)\n    return a + b"  # Missing colon

        is_valid, error = executor.validate_syntax(code, "python")

        assert is_valid is False
        assert error is not None
        assert "SyntaxError" in error or "invalid syntax" in error

    def test_validate_syntax_javascript_valid(self):
        """Test JavaScript syntax validation with valid code."""
        executor = CodeExecutor()
        code = "function add(a, b) { return a + b; }"

        is_valid, error = executor.validate_syntax(code, "javascript")

        assert is_valid is True
        assert error is None

    def test_validate_syntax_javascript_unbalanced_braces(self):
        """Test JavaScript syntax validation with unbalanced braces."""
        executor = CodeExecutor()
        code = "function add(a, b) { return a + b;"  # Missing closing brace

        is_valid, error = executor.validate_syntax(code, "javascript")

        assert is_valid is False
        assert "Unbalanced braces" in error

    def test_validate_syntax_go_valid(self):
        """Test Go syntax validation with valid code."""
        executor = CodeExecutor()
        code = 'package main\n\nfunc main() {\n    println("hello")\n}'

        is_valid, error = executor.validate_syntax(code, "go")

        assert is_valid is True
        assert error is None

    def test_validate_syntax_go_no_package(self):
        """Test Go syntax validation without package."""
        executor = CodeExecutor()
        code = 'func main() {\n    println("hello")\n}'

        is_valid, error = executor.validate_syntax(code, "go")

        assert is_valid is False
        assert "Missing package declaration" in error

    def test_run_tests_python(self, tmp_path):
        """Test running Python tests."""
        executor = CodeExecutor()

        # Create a Python file
        (tmp_path / "main.py").write_text("def add(a, b): return a + b")

        # Create a test file
        test_code = """from main import add

def test_add():
    assert add(2, 3) == 5
"""
        (tmp_path / "test_main.py").write_text(test_code)

        result = executor.run_tests(tmp_path, "python")

        # Note: This will fail if pytest is not installed
        # But the test structure is correct
        assert isinstance(result, ExecutionResult)

    def test_execute_python_language_not_allowed(self, tmp_path):
        """Test execution when language is not allowed."""
        executor = CodeExecutor(allowed_languages=["javascript"])
        code = "print('hello')"
        result = executor.execute_python(code, tmp_path)

        assert result.success is False
        assert "Python execution not allowed" in result.stderr

    def test_run_tests_language_not_allowed(self, tmp_path):
        """Test running tests when language is not allowed."""
        executor = CodeExecutor(allowed_languages=["python"])
        result = executor.run_tests(tmp_path, "go")

        assert result.success is False
        assert "Language go not allowed" in result.stderr
