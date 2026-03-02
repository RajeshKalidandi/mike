"""Unit tests for Q&A Agent."""

import pytest
from unittest.mock import MagicMock

from architectai.agents.qa_agent import (
    QAAgent,
    QueryAnalyzer,
    QueryIntent,
    SourceReference,
    QAResponse,
)


class TestQueryAnalyzer:
    """Test cases for QueryAnalyzer."""

    def test_initialization(self):
        """Test analyzer initialization."""
        analyzer = QueryAnalyzer()
        assert analyzer.PATTERNS is not None
        assert len(analyzer.PATTERNS) > 0

    def test_classify_location_intent(self):
        """Test classification of location queries."""
        analyzer = QueryAnalyzer()

        queries = [
            "Where is the authentication code?",
            "Find the user service",
            "Which file contains the database config?",
            "Locate the payment handler",
        ]

        for query in queries:
            intent = analyzer.classify(query)
            assert intent == QueryIntent.LOCATION, f"Failed for: {query}"

    def test_classify_explanation_intent(self):
        """Test classification of explanation queries."""
        analyzer = QueryAnalyzer()

        queries = [
            "How does the payment system work?",
            "Explain the authentication flow",
            "What happens when a user logs in?",
            "Walk me through the order process",
        ]

        for query in queries:
            intent = analyzer.classify(query)
            assert intent == QueryIntent.EXPLANATION, f"Failed for: {query}"

    def test_classify_relationship_intent(self):
        """Test classification of relationship queries."""
        analyzer = QueryAnalyzer()

        queries = [
            "What calls the UserService?",
            "Who uses the database connection?",
            "What depends on the config module?",
        ]

        for query in queries:
            intent = analyzer.classify(query)
            assert intent == QueryIntent.RELATIONSHIP, f"Failed for: {query}"

    def test_classify_modification_intent(self):
        """Test classification of modification queries."""
        analyzer = QueryAnalyzer()

        queries = [
            "How do I add a new user role?",
            "What files need to change for OAuth?",
            "How to implement caching?",
        ]

        for query in queries:
            intent = analyzer.classify(query)
            assert intent == QueryIntent.MODIFICATION, f"Failed for: {query}"

    def test_classify_general_intent(self):
        """Test that unknown queries default to GENERAL."""
        analyzer = QueryAnalyzer()

        queries = [
            "Tell me about this project",
            "What is this codebase?",
            "Hello",
        ]

        for query in queries:
            intent = analyzer.classify(query)
            assert intent == QueryIntent.GENERAL, f"Failed for: {query}"

    def test_extract_entities_pascal_case(self):
        """Test extraction of PascalCase entities (classes)."""
        analyzer = QueryAnalyzer()

        query = "How does UserService work with OrderProcessor?"
        entities = analyzer.extract_entities(query)

        assert "UserService" in entities
        assert "OrderProcessor" in entities

    def test_extract_entities_camel_case(self):
        """Test extraction of camelCase entities."""
        analyzer = QueryAnalyzer()

        query = "What does processPayment do with validateOrder?"
        entities = analyzer.extract_entities(query)

        assert "processPayment" in entities
        assert "validateOrder" in entities

    def test_extract_entities_snake_case(self):
        """Test extraction of snake_case entities."""
        analyzer = QueryAnalyzer()

        query = "Where is user_repository used?"
        entities = analyzer.extract_entities(query)

        # Filter out common words
        assert "user_repository" in entities

    def test_extract_entities_filters_common_words(self):
        """Test that common words are filtered from entities."""
        analyzer = QueryAnalyzer()

        query = "How does the main function work"
        entities = analyzer.extract_entities(query)

        # "the" should be filtered
        assert "the" not in entities

    def test_extract_file_types_python(self):
        """Test extraction of Python file type hints."""
        analyzer = QueryAnalyzer()

        query = "Where is the authentication in Python files?"
        file_types = analyzer.extract_file_types(query)

        assert ".py" in file_types

    def test_extract_file_types_javascript(self):
        """Test extraction of JavaScript file type hints."""
        analyzer = QueryAnalyzer()

        query = "Show me the JavaScript routes"
        file_types = analyzer.extract_file_types(query)

        assert ".js" in file_types


class TestSourceReference:
    """Test cases for SourceReference."""

    def test_format_with_entity(self):
        """Test formatting with entity name."""
        ref = SourceReference(
            file_path="src/main.py",
            start_line=10,
            end_line=20,
            entity_name="process_data",
            entity_type="function",
        )

        formatted = ref.format()
        assert "src/main.py:10-20" in formatted
        assert "function: process_data" in formatted

    def test_format_without_entity(self):
        """Test formatting without entity name."""
        ref = SourceReference(
            file_path="src/utils.py",
            start_line=5,
            end_line=15,
        )

        formatted = ref.format()
        assert formatted == "src/utils.py:5-15"


class TestQAResponse:
    """Test cases for QAResponse."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        response = QAResponse(
            answer="Test answer",
            query="Test query",
            intent=QueryIntent.LOCATION,
            sources=[
                SourceReference(
                    file_path="src/main.py",
                    start_line=1,
                    end_line=10,
                    entity_name="main",
                )
            ],
            confidence=0.9,
        )

        data = response.to_dict()

        assert data["query"] == "Test query"
        assert data["answer"] == "Test answer"
        assert data["intent"] == "location"
        assert data["confidence"] == 0.9
        assert len(data["sources"]) == 1


class TestQAAgent:
    """Test cases for QAAgent."""

    def test_initialization(self):
        """Test agent initialization."""
        agent = QAAgent()
        assert agent.query_analyzer is not None
        assert agent.context_assembler is None
        assert agent.llm_client is None

    def test_initialization_with_components(self):
        """Test initialization with context assembler and LLM client."""
        context_assembler = MagicMock()
        llm_client = MagicMock()

        agent = QAAgent(
            context_assembler=context_assembler,
            llm_client=llm_client,
        )

        assert agent.context_assembler == context_assembler
        assert agent.llm_client == llm_client

    def test_ask_without_components(self):
        """Test asking without context assembler or LLM."""
        agent = QAAgent()

        response = agent.ask("What does this code do?", "test-session")

        assert isinstance(response, QAResponse)
        assert response.query == "What does this code do?"
        assert response.intent == QueryIntent.EXPLANATION

    def test_ask_with_context_assembler(self):
        """Test asking with context assembler."""
        context_assembler = MagicMock()
        context_assembler.assemble.return_value = MagicMock(
            total_tokens=100,
            semantic_chunks=[],
        )

        agent = QAAgent(context_assembler=context_assembler)

        response = agent.ask("What does this code do?", "test-session")

        assert isinstance(response, QAResponse)
        context_assembler.assemble.assert_called_once()

    def test_ask_graceful_error_handling(self):
        """Test that errors are handled gracefully."""
        agent = QAAgent()

        # This should not raise an exception
        response = agent.ask("", "test-session")

        assert isinstance(response, QAResponse)
        assert response.confidence >= 0.0

    def test_generate_answer_fallback(self):
        """Test fallback answer generation."""
        agent = QAAgent()

        answer, sources = agent._generate_answer_fallback(
            query="Where is main?",
            intent=QueryIntent.LOCATION,
            entities=["main"],
            context=None,
        )

        assert isinstance(answer, str)
        assert isinstance(sources, list)

    def test_build_prompt(self):
        """Test prompt building."""
        agent = QAAgent()
        context = MagicMock()
        context.to_prompt_context.return_value = "Test context"

        prompt = agent._build_prompt(
            query="What does this do?",
            intent=QueryIntent.EXPLANATION,
            context=context,
        )

        assert "Test context" in prompt
        assert "What does this do?" in prompt

    def test_calculate_confidence_with_sources(self):
        """Test confidence calculation with sources."""
        agent = QAAgent()

        sources = [
            SourceReference(
                file_path="src/main.py",
                start_line=1,
                end_line=10,
                relevance_score=0.8,
            ),
            SourceReference(
                file_path="src/utils.py",
                start_line=1,
                end_line=5,
                relevance_score=0.6,
            ),
        ]

        confidence = agent._calculate_confidence(sources, None)

        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.0  # Should have some confidence with sources

    def test_calculate_confidence_no_sources(self):
        """Test confidence calculation with no sources."""
        agent = QAAgent()

        confidence = agent._calculate_confidence([], None)

        assert confidence == 0.0

    def test_build_location_answer(self):
        """Test building location answer."""
        agent = QAAgent()

        sources = [
            SourceReference(
                file_path="src/main.py",
                start_line=1,
                end_line=10,
            )
        ]

        answer = agent._build_location_answer(["main"], sources)

        assert "src/main.py:1-10" in answer

    def test_build_explanation_answer(self):
        """Test building explanation answer."""
        agent = QAAgent()

        sources = [
            SourceReference(
                file_path="src/main.py",
                start_line=1,
                end_line=10,
                entity_name="process_data",
            )
        ]

        answer = agent._build_explanation_answer(["process_data"], sources)

        assert "process_data" in answer
        assert "src/main.py:1-10" in answer

    def test_build_modification_answer(self):
        """Test building modification answer."""
        agent = QAAgent()

        sources = [
            SourceReference(
                file_path="src/main.py",
                start_line=1,
                end_line=10,
            )
        ]

        answer = agent._build_modification_answer(["main"], sources)

        assert "would need to change" in answer.lower()
        assert "src/main.py:1-10" in answer
