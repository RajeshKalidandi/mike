"""Integration tests for agents."""

import pytest
from unittest.mock import MagicMock, patch

from architectai.agents.qa_agent import QAAgent, QueryAnalyzer, QueryIntent, QAResponse
from architectai.agents.refactor_agent import RefactorAgent


class TestQAAgent:
    """Test cases for Q&A Agent."""

    def test_agent_initialization(self):
        """Test Q&A agent initialization."""
        agent = QAAgent()

        assert agent.context_assembler is None
        assert agent.llm_client is None
        assert agent.database is None
        assert agent.query_analyzer is not None

    def test_agent_initialization_with_dependencies(self, mock_llm_client):
        """Test Q&A agent with dependencies."""
        mock_context = MagicMock()
        mock_db = MagicMock()

        agent = QAAgent(
            context_assembler=mock_context,
            llm_client=mock_llm_client,
            database=mock_db,
        )

        assert agent.context_assembler is mock_context
        assert agent.llm_client is mock_llm_client
        assert agent.database is mock_db

    def test_ask_simple_question(self):
        """Test asking a simple question."""
        agent = QAAgent()

        response = agent.ask("What is this project?", "session123")

        assert isinstance(response, QAResponse)
        assert response.query == "What is this project?"
        assert response.intent == QueryIntent.GENERAL
        assert isinstance(response.sources, list)
        assert 0 <= response.confidence <= 1.0

    def test_ask_location_question(self):
        """Test asking a location question."""
        agent = QAAgent()

        response = agent.ask("Where is the main function?", "session123")

        assert response.intent == QueryIntent.LOCATION

    def test_ask_explanation_question(self):
        """Test asking an explanation question."""
        agent = QAAgent()

        response = agent.ask("How does authentication work?", "session123")

        assert response.intent == QueryIntent.EXPLANATION

    def test_ask_relationship_question(self):
        """Test asking a relationship question."""
        agent = QAAgent()

        response = agent.ask("What calls the login function?", "session123")

        assert response.intent == QueryIntent.RELATIONSHIP

    def test_ask_modification_question(self):
        """Test asking a modification question."""
        agent = QAAgent()

        response = agent.ask("How do I add a new endpoint?", "session123")

        assert response.intent == QueryIntent.MODIFICATION

    def test_ask_with_context_filters(self):
        """Test asking with context filters."""
        agent = QAAgent()

        response = agent.ask(
            "Find the auth code",
            "session123",
            context_filters={"top_k": 5, "file_types": [".py"]},
        )

        assert isinstance(response, QAResponse)

    def test_response_to_dict(self):
        """Test converting response to dictionary."""
        response = QAResponse(
            answer="The main function is in main.py",
            query="Where is main?",
            intent=QueryIntent.LOCATION,
            confidence=0.9,
        )

        data = response.to_dict()

        assert data["query"] == "Where is main?"
        assert data["intent"] == "location"
        assert data["answer"] == "The main function is in main.py"
        assert data["confidence"] == 0.9


class TestQueryAnalyzer:
    """Test cases for QueryAnalyzer."""

    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        analyzer = QueryAnalyzer()

        assert isinstance(analyzer.PATTERNS, dict)
        assert QueryIntent.LOCATION in analyzer.PATTERNS

    def test_classify_location_intent(self):
        """Test classifying location questions."""
        analyzer = QueryAnalyzer()

        questions = [
            "Where is the main function?",
            "Find the auth code",
            "Locate the database config",
            "Which file contains the login logic?",
        ]

        for q in questions:
            intent = analyzer.classify(q)
            assert intent == QueryIntent.LOCATION, f"Failed for: {q}"

    def test_classify_explanation_intent(self):
        """Test classifying explanation questions."""
        analyzer = QueryAnalyzer()

        questions = [
            "How does authentication work?",
            "What does the UserService do?",
            "Explain the caching mechanism",
            "Describe the data flow",
        ]

        for q in questions:
            intent = analyzer.classify(q)
            assert intent == QueryIntent.EXPLANATION, f"Failed for: {q}"

    def test_classify_relationship_intent(self):
        """Test classifying relationship questions."""
        analyzer = QueryAnalyzer()

        questions = [
            "What calls the login function?",
            "Who uses the database?",
            "Show me dependencies of UserService",
        ]

        for q in questions:
            intent = analyzer.classify(q)
            assert intent == QueryIntent.RELATIONSHIP, f"Failed for: {q}"

    def test_classify_modification_intent(self):
        """Test classifying modification questions."""
        analyzer = QueryAnalyzer()

        questions = [
            "How do I add a new endpoint?",
            "How can I change the timeout?",
            "What files need to change to add auth?",
        ]

        for q in questions:
            intent = analyzer.classify(q)
            assert intent == QueryIntent.MODIFICATION, f"Failed for: {q}"

    def test_classify_general_intent(self):
        """Test that unmatched questions are general."""
        analyzer = QueryAnalyzer()

        questions = [
            "Tell me about this codebase",
            "What is this project?",
            "Overview",
        ]

        for q in questions:
            intent = analyzer.classify(q)
            assert intent == QueryIntent.GENERAL, f"Failed for: {q}"

    def test_extract_entities_pascal_case(self):
        """Test extracting PascalCase entities."""
        analyzer = QueryAnalyzer()

        entities = analyzer.extract_entities("How does UserService work?")

        assert "UserService" in entities

    def test_extract_entities_camel_case(self):
        """Test extracting camelCase entities."""
        analyzer = QueryAnalyzer()

        entities = analyzer.extract_entities("What does getUserData do?")

        assert "getUserData" in entities

    def test_extract_entities_snake_case(self):
        """Test extracting snake_case entities."""
        analyzer = QueryAnalyzer()

        entities = analyzer.extract_entities("Call process_user_data")

        # Should extract some words (filtering common words)
        assert any("process" in e.lower() for e in entities) or any(
            "user" in e.lower() for e in entities
        )

    def test_extract_file_types(self):
        """Test extracting file type hints."""
        analyzer = QueryAnalyzer()

        file_types = analyzer.extract_file_types("Show me Python files")

        assert ".py" in file_types

    def test_extract_multiple_file_types(self):
        """Test extracting multiple file types."""
        analyzer = QueryAnalyzer()

        file_types = analyzer.extract_file_types("Show Python and JavaScript files")

        assert ".py" in file_types
        assert ".js" in file_types


class TestRefactorAgent:
    """Test cases for Refactor Agent."""

    def test_agent_initialization(self):
        """Test refactor agent initialization."""
        agent = RefactorAgent()

        assert agent.parser is not None
        assert agent.config is not None
        assert agent.config["long_function_lines"] == 50

    def test_agent_custom_config(self):
        """Test refactor agent with custom config."""
        agent = RefactorAgent(config={"long_function_lines": 30})

        assert agent.config["long_function_lines"] == 30
        # Other defaults preserved
        assert agent.config["god_class_methods"] == 20

    def test_analyze_file_no_issues(self):
        """Test analyzing clean file."""
        agent = RefactorAgent()

        code = """def main():
    pass
"""
        issues = agent.analyze_file("main.py", code, "python")

        assert isinstance(issues, list)

    def test_analyze_file_with_long_function(self):
        """Test detecting long function."""
        agent = RefactorAgent(config={"long_function_lines": 10})

        # Create a 15-line function
        code = """def long_function():
    x1 = 1
    x2 = 2
    x3 = 3
    x4 = 4
    x5 = 5
    x6 = 6
    x7 = 7
    x8 = 8
    x9 = 9
    x10 = 10
    x11 = 11
    x12 = 12
    x13 = 13
    x14 = 14
    return x14
"""
        issues = agent.analyze_file("main.py", code, "python")

        long_func_issues = [i for i in issues if i.smell_type == "long_function"]
        assert len(long_func_issues) > 0

    def test_analyze_file_with_god_class(self):
        """Test detecting god class."""
        agent = RefactorAgent(config={"god_class_methods": 5})

        # Create class with 10 methods
        methods = "\n".join([f"    def method{i}(self): pass" for i in range(10)])
        code = f"""class BigClass:
{methods}
"""
        issues = agent.analyze_file("main.py", code, "python")

        god_class_issues = [i for i in issues if i.smell_type == "god_class"]
        assert len(god_class_issues) > 0

    def test_analyze_project(self):
        """Test analyzing a project."""
        agent = RefactorAgent()

        files = [
            {"path": "main.py", "content": "def main(): pass", "language": "python"},
            {"path": "utils.py", "content": "def helper(): pass", "language": "python"},
        ]

        result = agent.analyze_project(files)

        assert "summary" in result
        assert "issues" in result
        assert "by_severity" in result
        assert "by_type" in result
        assert "by_file" in result

    def test_get_top_issues(self):
        """Test getting top issues."""
        agent = RefactorAgent()

        # Add some issues manually
        files = [
            {
                "path": "main.py",
                "content": "def " + "x\n" * 60,  # Long function
                "language": "python",
            },
        ]

        agent.analyze_project(files)
        top_issues = agent.get_top_issues(5)

        assert isinstance(top_issues, list)
        assert len(top_issues) <= 5

    def test_generate_refactor_plan(self):
        """Test generating refactor plan."""
        agent = RefactorAgent()

        files = [
            {
                "path": "main.py",
                "content": "def " + "x\n" * 60,  # Long function
                "language": "python",
            },
        ]

        agent.analyze_project(files)
        plan = agent.generate_refactor_plan(10)

        assert "priority_critical" in plan
        assert "priority_high" in plan
        assert "priority_medium" in plan
        assert "priority_low" in plan
        assert "estimated_effort" in plan

    def test_format_results_structure(self):
        """Test result formatting."""
        agent = RefactorAgent()

        files = [
            {"path": "main.py", "content": "def main(): pass", "language": "python"},
        ]

        result = agent.analyze_project(files)

        # Check summary structure
        summary = result["summary"]
        assert "total_issues" in summary
        assert "critical_count" in summary
        assert "high_count" in summary
        assert "medium_count" in summary
        assert "low_count" in summary
        assert "files_analyzed" in summary
        assert "average_score" in summary


class TestAgentIntegration:
    """Integration tests for agents working together."""

    def test_qa_agent_with_mock_context(self, mock_llm_client):
        """Test Q&A agent with mocked context assembler."""
        mock_context = MagicMock()
        mock_context.assemble.return_value = MagicMock(
            semantic_chunks=[],
            graph_context={},
            total_tokens=100,
        )
        mock_context.to_prompt_context.return_value = "Mock context"

        agent = QAAgent(
            context_assembler=mock_context,
            llm_client=mock_llm_client,
        )

        response = agent.ask("What does main do?", "session123")

        assert isinstance(response, QAResponse)
        mock_context.assemble.assert_called_once()

    def test_refactor_agent_analyzes_multiple_files(self):
        """Test refactor agent analyzing multiple files."""
        agent = RefactorAgent(config={"long_function_lines": 10})

        files = [
            {
                "path": "file1.py",
                "content": "def " + "x\n" * 20,  # 21 lines
                "language": "python",
            },
            {
                "path": "file2.py",
                "content": "def short():\n    pass",  # 2 lines
                "language": "python",
            },
        ]

        result = agent.analyze_project(files)

        assert result["summary"]["files_analyzed"] == 2

        # file1 should have issues, file2 should not
        file1_issues = result["by_file"].get("file1.py", [])
        file2_issues = result["by_file"].get("file2.py", [])

        assert len(file1_issues) > 0
        assert len(file2_issues) == 0

    def test_refactor_agent_categorizes_issues(self):
        """Test that issues are properly categorized."""
        agent = RefactorAgent(
            config={"long_function_lines": 10, "god_class_methods": 5}
        )

        # Create file with multiple issues
        code = """class BigClass:
    def m1(self): pass
    def m2(self): pass
    def m3(self): pass
    def m4(self): pass
    def m5(self): pass
    def m6(self): pass

def long_func():
    x1 = 1
    x2 = 2
    x3 = 3
    x4 = 4
    x5 = 5
    x6 = 6
    x7 = 7
    x8 = 8
    x9 = 9
    x10 = 10
    x11 = 11
    x12 = 12
"""

        files = [{"path": "main.py", "content": code, "language": "python"}]
        result = agent.analyze_project(files)

        # Should have different issue types
        assert "god_class" in result["by_type"] or "long_function" in result["by_type"]

        # Issues should be in severity buckets
        total_in_severities = (
            len(result["by_severity"]["critical"])
            + len(result["by_severity"]["high"])
            + len(result["by_severity"]["medium"])
            + len(result["by_severity"]["low"])
        )
        assert total_in_severities == len(result["issues"])
