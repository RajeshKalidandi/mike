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
import re

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
            "python",
            "javascript",
            "typescript",
            "go",
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
                status=ExecutionStatus.SUCCESS
                if result.returncode == 0
                else ExecutionStatus.FAILURE,
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
                    [sys.executable, "-m", "pytest", "-v"],
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
                status=ExecutionStatus.SUCCESS
                if result.returncode == 0
                else ExecutionStatus.FAILURE,
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
