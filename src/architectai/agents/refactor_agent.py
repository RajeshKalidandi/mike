"""Refactor Agent implementation for code analysis and improvement suggestions."""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import asdict
from pathlib import Path

from tree_sitter import Parser

from ..parser.parser import ASTParser
from ..parser.languages import normalize_language
from .patterns import (
    CodeSmell,
    ASTPatternMatcher,
    DuplicateDetector,
    ComplexityAnalyzer,
    DependencyAnalyzer,
)


logger = logging.getLogger(__name__)


class RefactorAgent:
    """Agent responsible for detecting code smells and suggesting improvements.

    This agent analyzes code for:
    - Code smells (long functions, god classes, deep nesting)
    - Circular dependencies
    - Dead code (unused functions)
    - Security anti-patterns
    - Duplicated logic

    All analysis is performed locally without external API calls.
    """

    # Configuration thresholds
    DEFAULT_CONFIG = {
        "long_function_lines": 50,
        "god_class_methods": 20,
        "deep_nesting_levels": 4,
        "max_cyclomatic_complexity": 10,
        "duplicate_min_lines": 5,
        "duplicate_similarity_threshold": 0.8,
    }

    def __init__(
        self,
        parser: Optional[ASTParser] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the Refactor Agent.

        Args:
            parser: AST parser instance (creates new one if None)
            config: Configuration dictionary overriding defaults
        """
        self.parser = parser or ASTParser()
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}

        # Initialize analyzers
        self.pattern_matcher = ASTPatternMatcher()
        self.duplicate_detector = DuplicateDetector(
            min_lines=self.config["duplicate_min_lines"],
            similarity_threshold=self.config["duplicate_similarity_threshold"],
        )
        self.complexity_analyzer = ComplexityAnalyzer()
        self.dependency_analyzer = DependencyAnalyzer()

        # Storage for analysis results
        self._files_content: Dict[str, str] = {}
        self._ast_data: Dict[str, Dict[str, Any]] = {}
        self._issues: List[CodeSmell] = []

    def analyze_file(
        self, file_path: str, content: str, language: str
    ) -> List[CodeSmell]:
        """Analyze a single file for code smells.

        Args:
            file_path: Path to the file
            content: File content
            language: Programming language

        Returns:
            List of detected code smells
        """
        issues = []
        normalized_lang = normalize_language(language)

        try:
            # Parse the file
            ast_data = self.parser.parse(content, normalized_lang)
            self._files_content[file_path] = content
            self._ast_data[file_path] = ast_data

            # Analyze functions
            for func in ast_data.get("functions", []):
                func_issues = self._analyze_function(
                    func, content, file_path, normalized_lang
                )
                issues.extend(func_issues)

            # Analyze classes
            for cls in ast_data.get("classes", []):
                class_issues = self._analyze_class(
                    cls, content, file_path, normalized_lang
                )
                issues.extend(class_issues)

            # Check for security issues
            security_issues = self.pattern_matcher.find_security_issues(
                content, file_path, normalized_lang
            )
            issues.extend(security_issues)

        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            # Add error as low-severity issue
            issues.append(
                CodeSmell(
                    smell_type="analysis_error",
                    file_path=file_path,
                    line_start=1,
                    line_end=1,
                    severity="low",
                    score=1.0,
                    description=f"Failed to analyze file: {str(e)}",
                    suggestion="Check file syntax and encoding.",
                )
            )

        return issues

    def analyze_project(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze an entire project for code smells.

        Args:
            files: List of file dictionaries with 'path', 'content', 'language' keys

        Returns:
            Dictionary containing all analysis results
        """
        self._issues = []
        self._files_content = {}
        self._ast_data = {}

        # First pass: analyze individual files
        logger.info(f"Analyzing {len(files)} files...")

        for file_info in files:
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")
            language = file_info.get("language", "")

            if not file_path or not content:
                continue

            file_issues = self.analyze_file(file_path, content, language)
            self._issues.extend(file_issues)

        # Second pass: cross-file analysis
        logger.info("Performing cross-file analysis...")

        # Find duplicates
        duplicate_issues = self.duplicate_detector.find_duplicates(
            self._files_content, self._ast_data
        )
        self._issues.extend(duplicate_issues)

        # Build dependency graph and find issues
        self.dependency_analyzer.build_call_graph(self._files_content, self._ast_data)

        # Find circular dependencies
        circular_deps = self.dependency_analyzer.find_circular_dependencies()
        for cycle in circular_deps:
            self._issues.append(
                CodeSmell(
                    smell_type="circular_dependency",
                    file_path=cycle[0] if cycle else "unknown",
                    line_start=1,
                    line_end=1,
                    severity="high",
                    score=8.0,
                    description=f"Circular dependency detected: {' → '.join(cycle)}",
                    suggestion="Break the cycle by refactoring or introducing interfaces/abstractions.",
                )
            )

        # Find dead code
        dead_code = self.dependency_analyzer.find_dead_code()
        for func_name, file_path, line in dead_code:
            # Skip likely entry points
            if not self._is_likely_entry_point(func_name, file_path):
                self._issues.append(
                    CodeSmell(
                        smell_type="dead_code",
                        file_path=file_path,
                        line_start=line,
                        line_end=line,
                        severity="medium",
                        score=5.0,
                        description=f'Function "{func_name}" appears to be unused',
                        suggestion="Consider removing this function or verify it's needed.",
                        entity_name=func_name,
                    )
                )

        # Sort and return results
        return self._format_results()

    def _analyze_function(
        self, func: Dict[str, Any], content: str, file_path: str, language: str
    ) -> List[CodeSmell]:
        """Analyze a single function for code smells.

        Args:
            func: Function metadata from AST
            content: File content
            file_path: Path to file
            language: Programming language

        Returns:
            List of detected issues
        """
        issues = []

        func_name = func.get("name", "unknown")
        start_line = func.get("start_line", 1)
        end_line = func.get("end_line", start_line)
        line_count = end_line - start_line + 1

        # Check for long function
        if line_count > self.config["long_function_lines"]:
            excess = line_count - self.config["long_function_lines"]
            score = min(5.0 + excess / 20, 8.5)
            issues.append(
                CodeSmell(
                    smell_type="long_function",
                    file_path=file_path,
                    line_start=start_line,
                    line_end=end_line,
                    severity="high" if excess > 30 else "medium",
                    score=score,
                    description=f'Function "{func_name}" is {line_count} lines long (threshold: {self.config["long_function_lines"]})',
                    suggestion="Extract smaller functions. Aim for functions under 50 lines. Consider the Single Responsibility Principle.",
                    entity_name=func_name,
                )
            )

        # Check parameter count
        params = func.get("parameters", [])
        if len(params) > 5:
            issues.append(
                CodeSmell(
                    smell_type="too_many_parameters",
                    file_path=file_path,
                    line_start=start_line,
                    line_end=start_line,
                    severity="medium",
                    score=5.0 + (len(params) - 5) * 0.5,
                    description=f'Function "{func_name}" has {len(params)} parameters',
                    suggestion="Consider grouping parameters into a configuration object or data class.",
                    entity_name=func_name,
                )
            )

        # Get function body for complexity analysis
        lines = content.split("\n")
        func_body = "\n".join(lines[start_line - 1 : end_line])

        # Re-parse just this function to get AST node
        try:
            func_ast = self.parser.parse(func_body, language)
            if func_ast:
                # Calculate nesting depth
                nesting_depth = self.pattern_matcher.calculate_nesting_depth(
                    func_body,
                    language,  # type: ignore
                )

                if nesting_depth > self.config["deep_nesting_levels"]:
                    issues.append(
                        CodeSmell(
                            smell_type="deep_nesting",
                            file_path=file_path,
                            line_start=start_line,
                            line_end=end_line,
                            severity="medium",
                            score=6.0
                            + (nesting_depth - self.config["deep_nesting_levels"])
                            * 0.5,
                            description=f'Function "{func_name}" has nesting depth of {nesting_depth} levels',
                            suggestion="Reduce nesting by extracting helper functions or using early returns.",
                            entity_name=func_name,
                        )
                    )
        except Exception:
            # If parsing fails, skip complexity analysis
            pass

        return issues

    def _analyze_class(
        self, cls: Dict[str, Any], content: str, file_path: str, language: str
    ) -> List[CodeSmell]:
        """Analyze a single class for code smells.

        Args:
            cls: Class metadata from AST
            content: File content
            file_path: Path to file
            language: Programming language

        Returns:
            List of detected issues
        """
        issues = []

        class_name = cls.get("name", "unknown")
        start_line = cls.get("start_line", 1)
        end_line = cls.get("end_line", start_line)

        # Count methods in class
        method_count = 0
        for func in self._ast_data.get(file_path, {}).get("functions", []):
            func_start = func.get("start_line", 0)
            if start_line <= func_start <= end_line:
                method_count += 1

        # Check for god class
        if method_count > self.config["god_class_methods"]:
            excess = method_count - self.config["god_class_methods"]
            issues.append(
                CodeSmell(
                    smell_type="god_class",
                    file_path=file_path,
                    line_start=start_line,
                    line_end=end_line,
                    severity="high",
                    score=min(6.0 + excess / 5, 9.0),
                    description=f'Class "{class_name}" has {method_count} methods (threshold: {self.config["god_class_methods"]})',
                    suggestion="This class may have too many responsibilities. Consider splitting into smaller, focused classes.",
                    entity_name=class_name,
                )
            )

        return issues

    def _is_likely_entry_point(self, func_name: str, file_path: str) -> bool:
        """Check if a function is likely an entry point (main, test, etc.).

        Args:
            func_name: Name of the function
            file_path: Path to the file

        Returns:
            True if likely entry point
        """
        entry_point_names = {
            "main",
            "__main__",
            "run",
            "start",
            "execute",
            "test_",
            "setup",
            "teardown",
            "fixture_",
        }

        if func_name in entry_point_names:
            return True

        if func_name.startswith(("test_", "Test", "fixture_")):
            return True

        # Check if file is in test directory
        path_parts = file_path.lower().split("/")
        if any(part in ["test", "tests", "spec", "specs"] for part in path_parts):
            return True

        return False

    def _format_results(self) -> Dict[str, Any]:
        """Format analysis results for output.

        Returns:
            Dictionary with formatted results
        """
        # Sort issues by score (descending)
        sorted_issues = sorted(
            self._issues, key=lambda x: (x.score, x.severity), reverse=True
        )

        # Group by severity
        by_severity: Dict[str, List[Dict]] = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
        }

        # Group by type
        by_type: Dict[str, List[Dict]] = {}

        # Group by file
        by_file: Dict[str, List[Dict]] = {}

        for issue in sorted_issues:
            issue_dict = asdict(issue)

            # By severity
            if issue.severity in by_severity:
                by_severity[issue.severity].append(issue_dict)

            # By type
            smell_type = issue.smell_type
            if smell_type not in by_type:
                by_type[smell_type] = []
            by_type[smell_type].append(issue_dict)

            # By file
            file_path = issue.file_path
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(issue_dict)

        # Calculate summary statistics
        summary = {
            "total_issues": len(sorted_issues),
            "critical_count": len(by_severity["critical"]),
            "high_count": len(by_severity["high"]),
            "medium_count": len(by_severity["medium"]),
            "low_count": len(by_severity["low"]),
            "files_analyzed": len(self._files_content),
            "average_score": (
                sum(i.score for i in sorted_issues) / len(sorted_issues)
                if sorted_issues
                else 0.0
            ),
        }

        return {
            "summary": summary,
            "issues": [asdict(issue) for issue in sorted_issues],
            "by_severity": by_severity,
            "by_type": by_type,
            "by_file": by_file,
        }

    def get_top_issues(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get the top N most severe issues.

        Args:
            count: Number of issues to return

        Returns:
            List of top issues as dictionaries
        """
        sorted_issues = sorted(
            self._issues, key=lambda x: (x.score, x.severity), reverse=True
        )

        return [asdict(issue) for issue in sorted_issues[:count]]

    def get_issues_for_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Get all issues for a specific file.

        Args:
            file_path: Path to the file

        Returns:
            List of issues for the file
        """
        file_issues = [
            asdict(issue) for issue in self._issues if issue.file_path == file_path
        ]

        return sorted(
            file_issues, key=lambda x: (x["score"], x["severity"]), reverse=True
        )

    def generate_refactor_plan(self, max_suggestions: int = 20) -> Dict[str, Any]:
        """Generate a refactoring plan prioritizing high-impact changes.

        Args:
            max_suggestions: Maximum number of suggestions to include

        Returns:
            Dictionary with prioritized refactoring suggestions
        """
        # Get top issues
        top_issues = self.get_top_issues(max_suggestions)

        # Organize by priority
        plan = {
            "priority_critical": [],
            "priority_high": [],
            "priority_medium": [],
            "priority_low": [],
        }

        for issue in top_issues:
            severity = issue.get("severity", "low")
            key = f"priority_{severity}"
            if key in plan:
                plan[key].append(
                    {
                        "type": issue.get("smell_type"),
                        "file": issue.get("file_path"),
                        "location": f"lines {issue.get('line_start')}-{issue.get('line_end')}",
                        "entity": issue.get("entity_name"),
                        "description": issue.get("description"),
                        "suggestion": issue.get("suggestion"),
                        "score": issue.get("score"),
                    }
                )

        # Add estimated effort
        plan["estimated_effort"] = self._estimate_effort(top_issues)

        return plan

    def _estimate_effort(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Estimate refactoring effort based on issues.

        Args:
            issues: List of issues

        Returns:
            Effort estimation dictionary
        """
        # Simple heuristic-based estimation
        effort_hours = 0

        for issue in issues:
            smell_type = issue.get("smell_type", "")
            severity = issue.get("severity", "low")

            base_hours = {
                "long_function": 2,
                "god_class": 4,
                "deep_nesting": 1.5,
                "too_many_parameters": 1,
                "circular_dependency": 3,
                "dead_code": 0.5,
                "duplicate_code": 2,
                "security_eval": 1,
                "security_hardcoded_secret": 0.5,
                "security_sql_injection": 2,
            }.get(smell_type, 1)

            # Adjust by severity
            multiplier = {
                "critical": 1.5,
                "high": 1.2,
                "medium": 1.0,
                "low": 0.8,
            }.get(severity, 1.0)

            effort_hours += base_hours * multiplier

        return {
            "total_hours": round(effort_hours, 1),
            "total_days": round(effort_hours / 6, 1),  # Assuming 6-hour days
            "confidence": "medium",
            "note": "Estimation is approximate and assumes familiar codebase.",
        }


class RefactorReportGenerator:
    """Generates human-readable reports from refactor analysis."""

    def __init__(self, agent: RefactorAgent):
        """Initialize with a RefactorAgent instance.

        Args:
            agent: RefactorAgent with analysis results
        """
        self.agent = agent

    def generate_markdown_report(self) -> str:
        """Generate a Markdown formatted report.

        Returns:
            Markdown report string
        """
        lines = []

        # Header
        lines.append("# Code Refactoring Report\n")
        lines.append(f"**Generated:** Refactor Agent Analysis\n")
        lines.append("---\n")

        # Summary
        summary = self.agent._format_results()["summary"]
        lines.append("## Summary\n")
        lines.append(f"- **Total Issues:** {summary['total_issues']}")
        lines.append(f"- **Critical:** {summary['critical_count']}")
        lines.append(f"- **High:** {summary['high_count']}")
        lines.append(f"- **Medium:** {summary['medium_count']}")
        lines.append(f"- **Low:** {summary['low_count']}")
        lines.append(f"- **Files Analyzed:** {summary['files_analyzed']}")
        lines.append(
            f"- **Average Severity Score:** {summary['average_score']:.2f}/10\n"
        )

        # Priority issues
        lines.append("## Priority Issues\n")

        top_issues = self.agent.get_top_issues(15)
        for i, issue in enumerate(top_issues, 1):
            lines.append(f"### {i}. {issue.get('smell_type', 'Unknown')}")
            lines.append(f"**File:** `{issue.get('file_path')}`")
            lines.append(
                f"**Location:** Lines {issue.get('line_start')}-{issue.get('line_end')}"
            )
            if issue.get("entity_name"):
                lines.append(f"**Entity:** `{issue.get('entity_name')}`")
            lines.append(
                f"**Severity:** {issue.get('severity').upper()} (Score: {issue.get('score'):.1f})\n"
            )
            lines.append(f"**Description:** {issue.get('description')}\n")
            lines.append(f"**Suggestion:** {issue.get('suggestion')}\n")
            lines.append("---\n")

        # Refactoring plan
        plan = self.agent.generate_refactor_plan(20)
        lines.append("## Suggested Refactoring Plan\n")

        effort = plan.get("estimated_effort", {})
        lines.append(
            f"**Estimated Effort:** {effort.get('total_hours', 0)} hours ({effort.get('total_days', 0)} days)\n"
        )

        for priority in ["priority_critical", "priority_high", "priority_medium"]:
            items = plan.get(priority, [])
            if items:
                level = priority.replace("priority_", "").upper()
                lines.append(f"\n### {level} Priority ({len(items)} items)\n")
                for item in items[:10]:  # Limit to 10 per section
                    lines.append(
                        f"- **{item['type']}** in `{item['file']}` ({item['location']})"
                    )
                    lines.append(f"  - {item['description']}")

        return "\n".join(lines)

    def generate_json_report(self) -> Dict[str, Any]:
        """Generate a structured JSON report.

        Returns:
            Dictionary with complete analysis results
        """
        results = self.agent._format_results()
        plan = self.agent.generate_refactor_plan(50)

        return {
            "summary": results["summary"],
            "issues": results["issues"],
            "by_severity": results["by_severity"],
            "by_type": results["by_type"],
            "refactoring_plan": plan,
            "metadata": {
                "thresholds": self.agent.config,
                "analyzer_version": "1.0.0",
            },
        }
