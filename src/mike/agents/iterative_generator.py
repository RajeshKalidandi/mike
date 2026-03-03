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
        logger.info(f"Starting iterative generation for: {file_spec.path}")

        execution_results = []
        fixes_applied = []
        current_content = None

        for iteration in range(1, self.max_iterations + 1):
            logger.debug(
                f"Iteration {iteration}/{self.max_iterations} for {file_spec.path}"
            )

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
                execution_results.append(
                    ExecutionResult(
                        success=False,
                        stdout="",
                        stderr=f"Syntax error: {syntax_error}",
                        return_code=-1,
                        status=ExecutionStatus.ERROR,
                        execution_time=0.0,
                        files_created=[],
                    )
                )

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
                    logger.info(
                        f"Tests passed for {file_spec.path} after {iteration} iterations"
                    )
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
                execution_results.append(
                    ExecutionResult(
                        success=True,
                        stdout="",
                        stderr="",
                        return_code=0,
                        status=ExecutionStatus.SUCCESS,
                        execution_time=0.0,
                        files_created=[str(file_path)],
                    )
                )

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
        if template and hasattr(template, "file_templates"):
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
                test_path = (
                    project_path / test_dir / f"test_{Path(file_spec.path).name}"
                )
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
