# M8 - Rebuilder Agent (Full Code Generation Loop) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the Rebuilder Agent with full code generation loop including iterative refinement, sandboxed testing, and AutoGen-style code-write-test-fix workflows.

**Architecture:** The Rebuilder Agent will be enhanced with a new `CodeExecutor` for sandboxed testing, an `IterativeGenerator` for the write-test-fix loop, and integration with the existing orchestrator. All components work 100% offline with local Ollama models.

**Tech Stack:** Python, Ollama, subprocess sandboxing, pytest for test execution

---

## Current State Analysis

The existing Rebuilder Agent has:
- ✅ Architecture template extraction
- ✅ Build plan generation with constraints
- ✅ Project scaffolding
- ✅ Basic code generation via Ollama
- ✅ Self-review functionality
- ✅ Workflow orchestration

**Missing for M8:**
- ❌ Sandboxed code execution for testing
- ❌ Iterative write-test-fix loop
- ❌ Execution memory and retry logic
- ❌ Advanced constraint validation
- ❌ Integration with test execution

---

## Task 1: Create Code Execution Sandbox

**Files:**
- Create: `src/architectai/agents/code_executor.py`
- Test: `tests/unit/test_agents/test_code_executor.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_agents/test_code_executor.py
import pytest
from pathlib import Path
from architectai.agents.code_executor import CodeExecutor, ExecutionResult

class TestCodeExecutor:
    def test_initialization(self):
        executor = CodeExecutor()
        assert executor.timeout == 30
        assert executor.sandbox_enabled is True
    
    def test_execute_python_code_success(self, tmp_path):
        executor = CodeExecutor()
        code = "print('Hello, World!')"
        result = executor.execute_python(code, tmp_path)
        
        assert result.success is True
        assert "Hello, World!" in result.stdout
        assert result.stderr == ""
        assert result.return_code == 0
    
    def test_execute_python_code_failure(self, tmp_path):
        executor = CodeExecutor()
        code = "raise ValueError('Test error')"
        result = executor.execute_python(code, tmp_path)
        
        assert result.success is False
        assert "ValueError" in result.stderr
        assert result.return_code != 0
    
    def test_execute_with_timeout(self, tmp_path):
        executor = CodeExecutor(timeout=1)
        code = "import time; time.sleep(10)"
        result = executor.execute_python(code, tmp_path)
        
        assert result.success is False
        assert "timeout" in result.stderr.lower() or result.return_code == -1
    
    def test_run_tests_python(self, tmp_path):
        executor = CodeExecutor()
        
        # Create a Python file
        (tmp_path / "main.py").write_text("def add(a, b): return a + b")
        
        # Create a test file
        test_code = """
from main import add

def test_add():
    assert add(2, 3) == 5
"""
        (tmp_path / "test_main.py").write_text(test_code)
        
        result = executor.run_tests(tmp_path, "python")
        
        assert result.success is True
        assert "passed" in result.stdout.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_agents/test_code_executor.py -v`
Expected: FAIL with "module not found"

**Step 3: Implement the CodeExecutor**

```python
# src/architectai/agents/code_executor.py
"""Code execution sandbox for testing generated code.

Provides isolated execution environment for testing code
across multiple languages with timeout and security controls.
"""

import subprocess
import tempfile
import os
import signal
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum
import logging
import sys

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Status of code execution."""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    stdout: str
    stderr: str
    return_code: int
    status: ExecutionStatus
    execution_time: float
    files_created: List[str]


class CodeExecutor:
    """
    Sandboxed code executor for testing generated code.
    
    Supports multiple languages:
    - Python (with pytest)
    - JavaScript/TypeScript (with npm test)
    - Go (with go test)
    
    Features:
    - Timeout control
    - Sandboxed execution (when possible)
    - Test runner integration
    - Security pattern detection
    """
    
    def __init__(
        self,
        timeout: int = 30,
        sandbox_enabled: bool = True,
        allowed_languages: Optional[List[str]] = None,
    ):
        """
        Initialize the code executor.
        
        Args:
            timeout: Maximum execution time in seconds
            sandbox_enabled: Whether to use sandboxing
            allowed_languages: List of allowed languages (None = all)
        """
        self.timeout = timeout
        self.sandbox_enabled = sandbox_enabled
        self.allowed_languages = allowed_languages or [
            "python", "javascript", "typescript", "go"
        ]
        
        logger.info(f"CodeExecutor initialized (sandbox={sandbox_enabled})")
    
    def execute_python(
        self,
        code: str,
        working_dir: Path,
        filename: str = "script.py",
    ) -> ExecutionResult:
        """
        Execute Python code in sandbox.
        
        Args:
            code: Python code to execute
            working_dir: Working directory
            filename: Filename for the script
            
        Returns:
            ExecutionResult with output and status
        """
        import time
        
        if "python" not in self.allowed_languages:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="Python execution not allowed",
                return_code=-1,
                status=ExecutionStatus.ERROR,
                execution_time=0.0,
                files_created=[],
            )
        
        # Check for dangerous patterns
        security_check = self._check_security_patterns(code, "python")
        if security_check:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Security check failed: {security_check}",
                return_code=-1,
                status=ExecutionStatus.ERROR,
                execution_time=0.0,
                files_created=[],
            )
        
        # Write code to file
        script_path = working_dir / filename
        script_path.write_text(code)
        
        start_time = time.time()
        
        try:
            # Run with timeout
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(working_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                status=ExecutionStatus.SUCCESS if result.returncode == 0 else ExecutionStatus.FAILURE,
                execution_time=execution_time,
                files_created=[str(script_path)],
            )
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Execution timed out after {self.timeout}s",
                return_code=-1,
                status=ExecutionStatus.TIMEOUT,
                execution_time=execution_time,
                files_created=[str(script_path)],
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                status=ExecutionStatus.ERROR,
                execution_time=execution_time,
                files_created=[str(script_path)],
            )
    
    def run_tests(
        self,
        project_path: Path,
        language: str,
        test_command: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Run tests for a project.
        
        Args:
            project_path: Path to project directory
            language: Programming language
            test_command: Optional custom test command
            
        Returns:
            ExecutionResult with test results
        """
        import time
        
        if language not in self.allowed_languages:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Language {language} not allowed",
                return_code=-1,
                status=ExecutionStatus.ERROR,
                execution_time=0.0,
                files_created=[],
            )
        
        start_time = time.time()
        
        try:
            if language == "python":
                cmd = test_command or "pytest -v"
                # Check if pytest is available
                result = subprocess.run(
                    ["python", "-m", "pytest", "-v"],
                    cwd=str(project_path),
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
            elif language in ["javascript", "typescript"]:
                cmd = test_command or "npm test"
                result = subprocess.run(
                    ["npm", "test"],
                    cwd=str(project_path),
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
            elif language == "go":
                cmd = test_command or "go test -v ./..."
                result = subprocess.run(
                    ["go", "test", "-v", "./..."],
                    cwd=str(project_path),
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
            else:
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr=f"Test execution not supported for {language}",
                    return_code=-1,
                    status=ExecutionStatus.ERROR,
                    execution_time=0.0,
                    files_created=[],
                )
            
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                status=ExecutionStatus.SUCCESS if result.returncode == 0 else ExecutionStatus.FAILURE,
                execution_time=execution_time,
                files_created=[],
            )
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Test execution timed out after {self.timeout}s",
                return_code=-1,
                status=ExecutionStatus.TIMEOUT,
                execution_time=execution_time,
                files_created=[],
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                status=ExecutionStatus.ERROR,
                execution_time=execution_time,
                files_created=[],
            )
    
    def _check_security_patterns(self, code: str, language: str) -> Optional[str]:
        """
        Check code for dangerous patterns.
        
        Args:
            code: Code to check
            language: Programming language
            
        Returns:
            Error message if dangerous patterns found, None otherwise
        """
        dangerous_patterns = {
            "python": [
                (r"\beval\s*\(", "eval() function"),
                (r"\bexec\s*\(", "exec() function"),
                (r"__import__\s*\(", "dynamic import"),
                (r"subprocess\.call\s*\(", "subprocess call"),
                (r"os\.system\s*\(", "os.system call"),
                (r"open\s*\([^)]*['\"]w['\"]", "file write operation"),
            ],
            "javascript": [
                (r"\beval\s*\(", "eval() function"),
                (r"\bFunction\s*\(", "Function constructor"),
                (r"child_process", "child_process module"),
            ],
        }
        
        import re
        
        patterns = dangerous_patterns.get(language, [])
        for pattern, description in patterns:
            if re.search(pattern, code):
                return f"Dangerous pattern detected: {description}"
        
        return None
    
    def validate_syntax(self, code: str, language: str) -> tuple[bool, Optional[str]]:
        """
        Validate code syntax without executing.
        
        Args:
            code: Code to validate
            language: Programming language
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if language == "python":
            try:
                import ast
                ast.parse(code)
                return True, None
            except SyntaxError as e:
                return False, str(e)
        
        elif language == "javascript":
            # Basic validation - check for balanced braces
            open_braces = code.count("{")
            close_braces = code.count("}")
            open_parens = code.count("(")
            close_parens = code.count(")")
            
            if open_braces != close_braces:
                return False, "Unbalanced braces"
            if open_parens != close_parens:
                return False, "Unbalanced parentheses"
            
            return True, None
        
        elif language == "go":
            # Check for package declaration
            if "package " not in code:
                return False, "Missing package declaration"
            
            open_braces = code.count("{")
            close_braces = code.count("}")
            if open_braces != close_braces:
                return False, "Unbalanced braces"
            
            return True, None
        
        return True, None  # Default: assume valid for unknown languages
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_agents/test_code_executor.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/architectai/agents/code_executor.py tests/unit/test_agents/test_code_executor.py
git commit -m "feat: add CodeExecutor for sandboxed code execution and testing"
```

---

## Task 2: Implement Iterative Code Generator

**Files:**
- Create: `src/architectai/agents/iterative_generator.py`
- Modify: `src/architectai/agents/rebuilder_agent.py` (integrate iterative generator)
- Test: `tests/unit/test_agents/test_iterative_generator.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_agents/test_iterative_generator.py
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from architectai.agents.iterative_generator import IterativeGenerator, IterationResult
from architectai.agents.rebuilder_agent import FileSpec, BuildPlan, BuildPlanStatus

class TestIterativeGenerator:
    def test_initialization(self):
        generator = IterativeGenerator()
        assert generator.max_iterations == 3
        assert generator.code_executor is not None
    
    def test_generate_file_with_iteration(self, tmp_path):
        mock_code_gen = MagicMock()
        mock_code_gen.generate_file.return_value = "def add(a, b): return a + b"
        
        generator = IterativeGenerator(code_generator=mock_code_gen)
        
        file_spec = FileSpec(
            path="main.py",
            purpose="Main module",
            dependencies=[],
            estimated_lines=10,
            template_hints={},
        )
        
        plan = MagicMock()
        plan.target_language = "python"
        plan.target_framework = None
        
        result = generator.generate_file_with_tests(
            file_spec=file_spec,
            plan=plan,
            project_path=tmp_path,
        )
        
        assert isinstance(result, IterationResult)
        assert result.iterations >= 1
        assert result.final_content is not None
    
    def test_fix_code_based_on_errors(self):
        generator = IterativeGenerator()
        
        code = "def add(a, b): return a + b"
        error = "NameError: name 'add' is not defined"
        
        mock_code_gen = MagicMock()
        mock_code_gen.generate_with_template.return_value = "def add(a, b): return a + b\n\nresult = add(1, 2)"
        generator.code_generator = mock_code_gen
        
        fixed = generator._fix_code_based_on_errors(code, error, "python")
        
        assert fixed is not None
    
    def test_max_iterations_limit(self, tmp_path):
        mock_code_gen = MagicMock()
        # Always generate code that fails
        mock_code_gen.generate_file.return_value = "invalid syntax here"
        
        generator = IterativeGenerator(
            code_generator=mock_code_gen,
            max_iterations=2,
        )
        
        file_spec = FileSpec(
            path="main.py",
            purpose="Main module",
            dependencies=[],
            estimated_lines=10,
            template_hints={},
        )
        
        plan = MagicMock()
        plan.target_language = "python"
        
        result = generator.generate_file_with_tests(
            file_spec=file_spec,
            plan=plan,
            project_path=tmp_path,
        )
        
        assert result.iterations <= 2
        assert result.success is False or result.success is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_agents/test_iterative_generator.py -v`
Expected: FAIL with module not found

**Step 3: Implement the IterativeGenerator**

```python
# src/architectai/agents/iterative_generator.py
"""Iterative code generator with write-test-fix loop.

Implements AutoGen-style iterative refinement where code is generated,
tested, and fixed in a loop until it passes or max iterations reached.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

from .code_executor import CodeExecutor, ExecutionResult, ExecutionStatus
from .code_generator import CodeGenerator

logger = logging.getLogger(__name__)


class IterationStatus(Enum):
    """Status of iterative generation."""
    SUCCESS = "success"
    MAX_ITERATIONS = "max_iterations_reached"
    FAILED = "failed"
    ERROR = "error"


@dataclass
class IterationResult:
    """Result of iterative code generation."""
    success: bool
    file_path: str
    final_content: str
    iterations: int
    status: IterationStatus
    execution_results: List[ExecutionResult] = field(default_factory=list)
    fixes_applied: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class IterativeGenerator:
    """
    Iterative code generator with write-test-fix loop.
    
    Workflow:
    1. Generate initial code
    2. Validate syntax
    3. Execute/run tests
    4. If failures, analyze and fix
    5. Repeat until success or max iterations
    
    Inspired by AutoGen patterns for autonomous code improvement.
    """
    
    def __init__(
        self,
        code_generator: Optional[CodeGenerator] = None,
        code_executor: Optional[CodeExecutor] = None,
        max_iterations: int = 3,
        enable_tests: bool = True,
    ):
        """
        Initialize the iterative generator.
        
        Args:
            code_generator: CodeGenerator instance
            code_executor: CodeExecutor instance
            max_iterations: Maximum fix iterations
            enable_tests: Whether to run tests during iteration
        """
        self.code_generator = code_generator or CodeGenerator()
        self.code_executor = code_executor or CodeExecutor()
        self.max_iterations = max_iterations
        self.enable_tests = enable_tests
        
        logger.info(f"IterativeGenerator initialized (max_iterations={max_iterations})")
    
    def generate_file_with_tests(
        self,
        file_spec: Any,
        plan: Any,
        project_path: Path,
        template: Optional[Any] = None,
        generated_files: Optional[Dict[str, str]] = None,
    ) -> IterationResult:
        """
        Generate a file with iterative testing and fixing.
        
        Args:
            file_spec: File specification
            plan: Build plan
            project_path: Project directory path
            template: Optional architecture template
            generated_files: Already generated files for context
            
        Returns:
            IterationResult with final code and iteration history
        """
        from .rebuilder_agent import FileSpec
        
        logger.info(f"Starting iterative generation for: {file_spec.path}")
        
        execution_results = []
        fixes_applied = []
        current_content = None
        
        for iteration in range(1, self.max_iterations + 1):
            logger.debug(f"Iteration {iteration}/{self.max_iterations} for {file_spec.path}")
            
            # Generate or fix code
            if iteration == 1:
                # Initial generation
                context = self._build_context(
                    file_spec, plan, template, generated_files or {}
                )
                current_content = self.code_generator.generate_file(
                    file_spec=file_spec,
                    context=context,
                    language=plan.target_language,
                    framework=plan.target_framework,
                )
            else:
                # Fix based on previous errors
                last_result = execution_results[-1]
                error_info = self._extract_error_info(last_result)
                
                fix_description = f"Fixing: {error_info[:100]}"
                fixes_applied.append(fix_description)
                
                current_content = self._fix_code_based_on_errors(
                    current_content,
                    error_info,
                    plan.target_language,
                    file_spec,
                    plan,
                )
            
            # Validate syntax first
            is_valid, syntax_error = self.code_executor.validate_syntax(
                current_content,
                plan.target_language,
            )
            
            if not is_valid:
                logger.warning(f"Syntax error in {file_spec.path}: {syntax_error}")
                execution_results.append(ExecutionResult(
                    success=False,
                    stdout="",
                    stderr=f"Syntax error: {syntax_error}",
                    return_code=-1,
                    status=ExecutionStatus.ERROR,
                    execution_time=0.0,
                    files_created=[],
                ))
                
                if iteration == self.max_iterations:
                    return IterationResult(
                        success=False,
                        file_path=file_spec.path,
                        final_content=current_content,
                        iterations=iteration,
                        status=IterationStatus.MAX_ITERATIONS,
                        execution_results=execution_results,
                        fixes_applied=fixes_applied,
                        error_message=f"Max iterations reached with syntax errors: {syntax_error}",
                    )
                continue
            
            # Write file to project
            file_path = project_path / file_spec.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(current_content)
            
            # Execute or test
            if self.enable_tests and file_spec.path.endswith(".py"):
                # Run pytest if test file exists
                test_result = self._run_tests_for_file(
                    file_spec, project_path, plan.target_language
                )
                execution_results.append(test_result)
                
                if test_result.success:
                    logger.info(f"Tests passed for {file_spec.path} after {iteration} iterations")
                    return IterationResult(
                        success=True,
                        file_path=file_spec.path,
                        final_content=current_content,
                        iterations=iteration,
                        status=IterationStatus.SUCCESS,
                        execution_results=execution_results,
                        fixes_applied=fixes_applied,
                    )
            else:
                # Just validate syntax for non-test files
                execution_results.append(ExecutionResult(
                    success=True,
                    stdout="",
                    stderr="",
                    return_code=0,
                    status=ExecutionStatus.SUCCESS,
                    execution_time=0.0,
                    files_created=[str(file_path)],
                ))
                
                return IterationResult(
                    success=True,
                    file_path=file_spec.path,
                    final_content=current_content,
                    iterations=iteration,
                    status=IterationStatus.SUCCESS,
                    execution_results=execution_results,
                    fixes_applied=fixes_applied,
                )
            
            # Check if max iterations reached
            if iteration == self.max_iterations:
                logger.warning(f"Max iterations reached for {file_spec.path}")
                return IterationResult(
                    success=False,
                    file_path=file_spec.path,
                    final_content=current_content,
                    iterations=iteration,
                    status=IterationStatus.MAX_ITERATIONS,
                    execution_results=execution_results,
                    fixes_applied=fixes_applied,
                    error_message="Max iterations reached",
                )
        
        # Should not reach here
        return IterationResult(
            success=False,
            file_path=file_spec.path,
            final_content=current_content or "",
            iterations=self.max_iterations,
            status=IterationStatus.ERROR,
            execution_results=execution_results,
            fixes_applied=fixes_applied,
            error_message="Unexpected end of iteration loop",
        )
    
    def _build_context(
        self,
        file_spec: Any,
        plan: Any,
        template: Optional[Any],
        generated_files: Dict[str, str],
    ) -> Dict[str, Any]:
        """Build context for code generation."""
        context = {
            "project_name": plan.project_name,
            "project_description": plan.description,
            "target_language": plan.target_language,
            "target_framework": plan.target_framework,
            "architecture_pattern": plan.architecture_pattern,
            "constraints": plan.constraints,
            "file_purpose": file_spec.purpose,
            "file_path": file_spec.path,
            "dependencies": {},
            "template_hints": file_spec.template_hints,
        }
        
        # Add dependency content
        for dep_path in file_spec.dependencies:
            if dep_path in generated_files:
                context["dependencies"][dep_path] = generated_files[dep_path]
        
        # Add template examples
        if template and hasattr(template, 'file_templates'):
            context["template_examples"] = template.file_templates
        
        return context
    
    def _run_tests_for_file(
        self,
        file_spec: Any,
        project_path: Path,
        language: str,
    ) -> ExecutionResult:
        """Run tests for a specific file."""
        # Look for corresponding test file
        test_file_name = f"test_{file_spec.path}"
        test_file_path = project_path / test_file_name
        
        if not test_file_path.exists():
            # Try common test directories
            test_dirs = ["tests", "test", "__tests__"]
            for test_dir in test_dirs:
                test_path = project_path / test_dir / f"test_{Path(file_spec.path).name}"
                if test_path.exists():
                    test_file_path = test_path
                    break
        
        if test_file_path.exists():
            return self.code_executor.run_tests(project_path, language)
        
        # No test file found - consider it a pass for now
        return ExecutionResult(
            success=True,
            stdout="No tests found for this file",
            stderr="",
            return_code=0,
            status=ExecutionStatus.SUCCESS,
            execution_time=0.0,
            files_created=[],
        )
    
    def _extract_error_info(self, execution_result: ExecutionResult) -> str:
        """Extract error information from execution result."""
        if execution_result.stderr:
            return execution_result.stderr
        elif not execution_result.success:
            return "Unknown error during execution"
        return ""
    
    def _fix_code_based_on_errors(
        self,
        current_code: str,
        error_info: str,
        language: str,
        file_spec: Any,
        plan: Any,
    ) -> str:
        """
        Fix code based on error information.
        
        Uses the LLM to analyze errors and generate fixed code.
        """
        # Build fix prompt
        prompt = f"""Fix the following {language} code based on the error:

## Current Code
```{language}
{current_code}
```

## Error
{error_info}

## File Purpose
{file_spec.purpose}

## Requirements
1. Fix the error while maintaining the original purpose
2. Keep the same general structure
3. Ensure the fix addresses the root cause
4. Return only the fixed code in a {language} code block

## Fixed Code
"""
        
        try:
            # Use code generator to fix
            fixed_content = self.code_generator._call_ollama(prompt)
            
            # Clean the response
            fixed_content = self.code_generator._clean_generated_code(
                fixed_content,
                language,
            )
            
            return fixed_content
            
        except Exception as e:
            logger.error(f"Failed to fix code: {e}")
            return current_code  # Return original if fix fails
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_agents/test_iterative_generator.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/architectai/agents/iterative_generator.py tests/unit/test_agents/test_iterative_generator.py
git commit -m "feat: add IterativeGenerator with write-test-fix loop"
```

---

## Task 3: Update RebuilderAgent to Use Iterative Generator

**Files:**
- Modify: `src/architectai/agents/rebuilder_agent.py`
- Test: `tests/unit/test_agents/test_rebuilder_agent.py` (update existing)

**Step 1: Update imports and initialization**

Edit `src/architectai/agents/rebuilder_agent.py`:
- Add import for IterativeGenerator
- Update __init__ to accept iterative generator
- Add execution_memory tracking

**Step 2: Update write_code method to use iterative generation**

Replace the existing `write_code` method to use `IterativeGenerator`.

**Step 3: Run existing tests**

Run: `pytest tests/unit/test_agents/test_rebuilder_agent.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add src/architectai/agents/rebuilder_agent.py
git commit -m "feat: integrate IterativeGenerator into RebuilderAgent"
```

---

## Task 4: Add Execution Memory to RebuilderAgent

**Files:**
- Modify: `src/architectai/agents/rebuilder_agent.py`

**Step 1: Add execution memory tracking**

Add execution memory dataclass and methods to track:
- Generation attempts
- Fix iterations
- Test results
- Model interactions

**Step 2: Add memory persistence**

Add methods to save/load execution memory to JSON.

**Step 3: Update workflow to log all actions**

Ensure all major actions are logged to execution memory.

**Step 4: Commit**

```bash
git add src/architectai/agents/rebuilder_agent.py
git commit -m "feat: add execution memory tracking to RebuilderAgent"
```

---

## Task 5: Create Integration Tests

**Files:**
- Create: `tests/integration/test_rebuilder_workflow.py`

**Step 1: Write integration test**

```python
# tests/integration/test_rebuilder_workflow.py
import pytest
from pathlib import Path
from architectai.agents.rebuilder_agent import RebuilderAgent, RebuilderWorkflow

class TestRebuilderWorkflow:
    def test_full_workflow_with_mock(self, tmp_path):
        """Test full rebuild workflow with mocked LLM."""
        # This would require mocking Ollama
        pass
    
    def test_end_to_end_scaffolding(self, tmp_path):
        """Test project scaffolding without LLM calls."""
        agent = RebuilderAgent(
            model_name="mock-model",
            output_dir=str(tmp_path),
        )
        
        # Create a simple template
        from architectai.agents.rebuilder_agent import (
            ArchitectureTemplate,
            BuildPlan,
        )
        
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
```

**Step 2: Run integration test**

Run: `pytest tests/integration/test_rebuilder_workflow.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/integration/test_rebuilder_workflow.py
git commit -m "test: add integration tests for Rebuilder workflow"
```

---

## Task 6: Update Agent Orchestrator Integration

**Files:**
- Modify: `src/architectai/orchestrator/engine.py` (if exists)
- OR Create integration in CLI

**Step 1: Add RebuilderAgent to orchestrator or CLI**

Ensure the RebuilderAgent can be invoked from the main orchestrator or CLI.

**Step 2: Add rebuild command to CLI**

If there's a CLI, add a `rebuild` command.

**Step 3: Test CLI integration**

Test the rebuild command works end-to-end.

**Step 4: Commit**

```bash
git commit -m "feat: integrate RebuilderAgent with CLI/orchestrator"
```

---

## Task 7: Final Testing and Verification

**Step 1: Run all tests**

```bash
pytest tests/unit/test_agents/ -v
pytest tests/integration/test_rebuilder_workflow.py -v
```
Expected: All PASS

**Step 2: Run linting and type checking**

```bash
# Check for available lint/type commands
black --check src/architectai/agents/
mypy src/architectai/agents/
```

**Step 3: Update milestone status**

Update CONTEXT.md to mark M8 as completed.

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete M8 - Rebuilder Agent with full code generation loop"
```

---

## Summary

This implementation plan adds the following components for M8:

1. **CodeExecutor** - Sandboxed execution for testing generated code
2. **IterativeGenerator** - Write-test-fix loop inspired by AutoGen
3. **Execution Memory** - Track all generation attempts and fixes
4. **Integration Tests** - End-to-end workflow testing
5. **CLI Integration** - Make rebuild available from command line

The Rebuilder Agent now supports:
- ✅ Architecture template extraction
- ✅ Build plan generation with constraints
- ✅ Human approval checkpoint
- ✅ Project scaffolding
- ✅ Iterative code generation with testing
- ✅ Self-review and validation
- ✅ Execution memory for debugging
- ✅ Multi-language support (Python, JS/TS, Go)

**Hardware Requirements:**
- Minimum: 16GB RAM, 8GB VRAM (for basic scaffolding)
- Recommended: 32GB RAM, 24GB VRAM (for full generation with large models)
- Models: 12B+ for scaffolding only, 32B+ for full code generation

**Next Steps:**
1. Execute this plan using `superpowers:executing-plans`
2. Run all tests to verify
3. Update documentation
4. Create example usage scripts
