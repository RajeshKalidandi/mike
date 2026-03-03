"""Unit tests for Refactor Agent."""

import pytest
from unittest.mock import MagicMock, patch

from mike.agents.refactor_agent import RefactorAgent, RefactorReportGenerator
from mike.agents.patterns import CodeSmell


class TestRefactorAgent:
    """Test cases for RefactorAgent."""

    def test_initialization(self):
        """Test agent initialization with defaults."""
        agent = RefactorAgent()

        assert agent.parser is not None
        assert agent.config == agent.DEFAULT_CONFIG
        assert agent.pattern_matcher is not None
        assert agent.duplicate_detector is not None

    def test_initialization_with_config(self):
        """Test initialization with custom config."""
        custom_config = {
            "long_function_lines": 30,
            "god_class_methods": 15,
        }

        agent = RefactorAgent(config=custom_config)

        assert agent.config["long_function_lines"] == 30
        assert agent.config["god_class_methods"] == 15
        # Other defaults should still be present
        assert agent.config["deep_nesting_levels"] == 4

    def test_analyze_file_python_simple(self):
        """Test analyzing a simple Python file."""
        agent = RefactorAgent()

        code = """
def main():
    pass
"""
        issues = agent.analyze_file("test.py", code, "python")

        # Simple file should have no issues
        assert len(issues) == 0

    def test_analyze_file_long_function(self):
        """Test detecting long functions."""
        agent = RefactorAgent()

        # Create a function with many lines
        code = "def long_function():\n"
        code += "    x = 1\n" * 60  # 60 lines

        issues = agent.analyze_file("test.py", code, "python")

        long_func_issues = [i for i in issues if i.smell_type == "long_function"]
        assert len(long_func_issues) > 0

    def test_analyze_file_many_parameters(self):
        """Test detecting functions with too many parameters."""
        agent = RefactorAgent()

        code = "def func(a, b, c, d, e, f, g):\n    pass\n"

        issues = agent.analyze_file("test.py", code, "python")

        param_issues = [i for i in issues if i.smell_type == "too_many_parameters"]
        assert len(param_issues) > 0

    def test_analyze_file_god_class(self):
        """Test detecting god classes."""
        agent = RefactorAgent()

        code = """
class GodClass:
    def method1(self): pass
    def method2(self): pass
    def method3(self): pass
    def method4(self): pass
    def method5(self): pass
    def method6(self): pass
    def method7(self): pass
    def method8(self): pass
    def method9(self): pass
    def method10(self): pass
    def method11(self): pass
    def method12(self): pass
    def method13(self): pass
    def method14(self): pass
    def method15(self): pass
    def method16(self): pass
    def method17(self): pass
    def method18(self): pass
    def method19(self): pass
    def method20(self): pass
    def method21(self): pass
    def method22(self): pass
    def method23(self): pass
    def method24(self): pass
    def method25(self): pass
"""
        issues = agent.analyze_file("test.py", code, "python")

        god_class_issues = [i for i in issues if i.smell_type == "god_class"]
        assert len(god_class_issues) > 0

    def test_analyze_project_multiple_files(self):
        """Test analyzing multiple files in a project."""
        agent = RefactorAgent()

        files = [
            {
                "path": "src/main.py",
                "content": "def main():\n    pass\n",
                "language": "python",
            },
            {
                "path": "src/utils.py",
                "content": "def helper():\n    return 42\n",
                "language": "python",
            },
        ]

        results = agent.analyze_project(files)

        assert "summary" in results
        assert "issues" in results
        assert "by_severity" in results
        assert "by_type" in results
        assert "by_file" in results

    def test_format_results(self):
        """Test formatting analysis results."""
        agent = RefactorAgent()

        # Add some test issues
        agent._issues = [
            CodeSmell(
                smell_type="long_function",
                file_path="test.py",
                line_start=1,
                line_end=60,
                severity="high",
                score=7.5,
                description="Long function",
                suggestion="Refactor",
            ),
            CodeSmell(
                smell_type="dead_code",
                file_path="utils.py",
                line_start=10,
                line_end=10,
                severity="medium",
                score=5.0,
                description="Unused function",
                suggestion="Remove",
            ),
        ]

        results = agent._format_results()

        assert results["summary"]["total_issues"] == 2
        assert results["summary"]["high_count"] == 1
        assert results["summary"]["medium_count"] == 1
        assert len(results["by_severity"]["high"]) == 1
        assert len(results["by_severity"]["medium"]) == 1

    def test_get_top_issues(self):
        """Test getting top issues."""
        agent = RefactorAgent()

        # Add test issues
        agent._issues = [
            CodeSmell(
                smell_type="critical_issue",
                file_path="test.py",
                line_start=1,
                line_end=1,
                severity="critical",
                score=9.0,
                description="Critical",
                suggestion="Fix",
            ),
            CodeSmell(
                smell_type="low_issue",
                file_path="test.py",
                line_start=1,
                line_end=1,
                severity="low",
                score=3.0,
                description="Low",
                suggestion="Fix",
            ),
        ]

        top_issues = agent.get_top_issues(count=1)

        assert len(top_issues) == 1
        assert top_issues[0]["smell_type"] == "critical_issue"

    def test_get_issues_for_file(self):
        """Test getting issues for a specific file."""
        agent = RefactorAgent()

        agent._issues = [
            CodeSmell(
                smell_type="issue1",
                file_path="file1.py",
                line_start=1,
                line_end=1,
                severity="high",
                score=8.0,
                description="Issue 1",
                suggestion="Fix",
            ),
            CodeSmell(
                smell_type="issue2",
                file_path="file2.py",
                line_start=1,
                line_end=1,
                severity="high",
                score=7.0,
                description="Issue 2",
                suggestion="Fix",
            ),
        ]

        file1_issues = agent.get_issues_for_file("file1.py")

        assert len(file1_issues) == 1
        assert file1_issues[0]["smell_type"] == "issue1"

    def test_generate_refactor_plan(self):
        """Test generating refactoring plan."""
        agent = RefactorAgent()

        agent._issues = [
            CodeSmell(
                smell_type="critical_issue",
                file_path="test.py",
                line_start=1,
                line_end=10,
                severity="critical",
                score=9.5,
                description="Critical issue",
                suggestion="Fix immediately",
            ),
        ]

        plan = agent.generate_refactor_plan()

        assert "priority_critical" in plan
        assert "priority_high" in plan
        assert "priority_medium" in plan
        assert "priority_low" in plan
        assert "estimated_effort" in plan

    def test_is_likely_entry_point(self):
        """Test detection of entry points."""
        agent = RefactorAgent()

        # Main functions
        assert agent._is_likely_entry_point("main", "src/main.py")
        assert agent._is_likely_entry_point("run", "src/app.py")

        # Test functions
        assert agent._is_likely_entry_point("test_something", "tests/test_file.py")
        assert agent._is_likely_entry_point("test_main", "src/test.py")

        # Regular functions
        assert not agent._is_likely_entry_point("helper", "src/utils.py")
        assert not agent._is_likely_entry_point("process_data", "src/main.py")

    def test_estimate_effort(self):
        """Test effort estimation."""
        agent = RefactorAgent()

        issues = [
            {"smell_type": "long_function", "severity": "high"},
            {"smell_type": "dead_code", "severity": "low"},
        ]

        effort = agent._estimate_effort(issues)

        assert "total_hours" in effort
        assert "total_days" in effort
        assert effort["total_hours"] > 0
        assert effort["confidence"] == "medium"


class TestRefactorReportGenerator:
    """Test cases for RefactorReportGenerator."""

    def test_initialization(self):
        """Test report generator initialization."""
        agent = RefactorAgent()
        generator = RefactorReportGenerator(agent)

        assert generator.agent == agent

    def test_generate_markdown_report(self):
        """Test generating Markdown report."""
        agent = RefactorAgent()
        agent._issues = [
            CodeSmell(
                smell_type="long_function",
                file_path="src/main.py",
                line_start=1,
                line_end=60,
                severity="high",
                score=7.5,
                description="Function too long",
                suggestion="Extract methods",
                entity_name="main",
            ),
        ]

        generator = RefactorReportGenerator(agent)
        report = generator.generate_markdown_report()

        assert "# Code Refactoring Report" in report
        assert "long_function" in report
        assert "src/main.py" in report
        assert "Function too long" in report

    def test_generate_json_report(self):
        """Test generating JSON report."""
        agent = RefactorAgent()
        agent._issues = [
            CodeSmell(
                smell_type="test_issue",
                file_path="test.py",
                line_start=1,
                line_end=1,
                severity="medium",
                score=5.0,
                description="Test",
                suggestion="Fix",
            ),
        ]

        generator = RefactorReportGenerator(agent)
        report = generator.generate_json_report()

        assert "summary" in report
        assert "issues" in report
        assert "refactoring_plan" in report
        assert "metadata" in report
