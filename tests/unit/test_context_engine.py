"""Unit tests for ContextEngine."""

import json
import pytest
from unittest.mock import MagicMock, patch

from mike.orchestrator.context_engine import ContextEngine, ContextBundle


@pytest.fixture
def mock_embedding_service():
    svc = MagicMock()
    svc.embed.return_value = [0.1] * 1024
    svc.dimension = 1024
    return svc


@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    store.search.return_value = [
        {
            "id": "chunk_0",
            "content": "def hello(): pass",
            "metadata": {"file_path": "src/main.py", "language": "python", "start_line": 1, "end_line": 3},
            "distance": 0.15,
        },
        {
            "id": "chunk_1",
            "content": "def world(): pass",
            "metadata": {"file_path": "src/utils.py", "language": "python", "start_line": 10, "end_line": 15},
            "distance": 0.25,
        },
    ]
    return store


@pytest.fixture
def mock_graph_builder():
    builder = MagicMock()
    builder.get_neighbors.return_value = {"src/helpers.py"}
    return builder


@pytest.fixture
def mock_execution_memory():
    memory = MagicMock()
    memory.failed_approaches = {"qa": ["bad approach: it failed"]}
    memory.successful_patterns = {"qa": [{"query": "what", "result_keys": ["answer"]}]}
    memory.get_learnings.return_value = ["Use specific file paths"]
    memory.get_average_iterations.return_value = 1.5
    return memory


class TestContextBundle:
    def test_create_bundle(self):
        bundle = ContextBundle(
            query="How does auth work?",
            agent_type="qa",
            semantic_chunks=[{"content": "test"}],
            structural_context={"files": []},
            execution_memory={"failed_approaches": []},
            shared_context={},
            token_budget=8000,
            estimated_tokens=500,
            metadata={},
        )
        assert bundle.query == "How does auth work?"
        assert len(bundle.semantic_chunks) == 1

    def test_to_dict(self):
        bundle = ContextBundle(
            query="test", agent_type="qa",
            semantic_chunks=[], structural_context={},
            execution_memory={}, shared_context={},
            token_budget=8000, estimated_tokens=0, metadata={},
        )
        d = bundle.to_dict()
        assert d["query"] == "test"
        assert "token_budget" in d


class TestContextEngine:
    def test_build_returns_context_bundle(
        self, mock_vector_store, mock_embedding_service, mock_graph_builder, mock_execution_memory
    ):
        engine = ContextEngine(
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
            graph_builder=mock_graph_builder,
            execution_memory=mock_execution_memory,
        )
        bundle = engine.build(
            query="How does auth work?",
            agent_type="qa",
            session_id="session123",
        )
        assert isinstance(bundle, ContextBundle)
        assert bundle.query == "How does auth work?"
        assert bundle.agent_type == "qa"

    def test_semantic_retrieval_embeds_query(
        self, mock_vector_store, mock_embedding_service
    ):
        engine = ContextEngine(
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
        )
        engine.build(query="test query", agent_type="qa", session_id="s1")
        mock_embedding_service.embed.assert_called_once_with("test query")
        mock_vector_store.search.assert_called_once()

    def test_semantic_chunks_included(
        self, mock_vector_store, mock_embedding_service
    ):
        engine = ContextEngine(
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
        )
        bundle = engine.build(query="test", agent_type="qa", session_id="s1")
        assert len(bundle.semantic_chunks) == 2
        assert bundle.semantic_chunks[0]["content"] == "def hello(): pass"

    def test_graph_expansion_fetches_neighbors(
        self, mock_vector_store, mock_embedding_service, mock_graph_builder
    ):
        engine = ContextEngine(
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
            graph_builder=mock_graph_builder,
        )
        bundle = engine.build(query="test", agent_type="qa", session_id="s1")
        mock_graph_builder.get_neighbors.assert_called()
        assert "src/helpers.py" in bundle.structural_context.get("expanded_files", [])

    def test_skip_structural_when_disabled(
        self, mock_vector_store, mock_embedding_service, mock_graph_builder
    ):
        engine = ContextEngine(
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
            graph_builder=mock_graph_builder,
        )
        bundle = engine.build(
            query="test", agent_type="qa", session_id="s1",
            include_structural=False,
        )
        mock_graph_builder.get_neighbors.assert_not_called()
        assert bundle.structural_context == {}

    def test_skip_semantic_when_disabled(
        self, mock_vector_store, mock_embedding_service
    ):
        engine = ContextEngine(
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
        )
        bundle = engine.build(
            query="test", agent_type="qa", session_id="s1",
            include_semantic=False,
        )
        mock_embedding_service.embed.assert_not_called()
        assert bundle.semantic_chunks == []

    def test_execution_memory_included(
        self, mock_vector_store, mock_embedding_service, mock_execution_memory
    ):
        engine = ContextEngine(
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
            execution_memory=mock_execution_memory,
        )
        bundle = engine.build(query="test", agent_type="qa", session_id="s1")
        assert "failed_approaches" in bundle.execution_memory
        assert "successful_patterns" in bundle.execution_memory

    def test_token_budget_estimation(
        self, mock_vector_store, mock_embedding_service
    ):
        engine = ContextEngine(
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
        )
        bundle = engine.build(
            query="test", agent_type="qa", session_id="s1",
            token_budget=8000,
        )
        assert bundle.token_budget == 8000
        assert bundle.estimated_tokens > 0

    def test_works_without_optional_dependencies(
        self, mock_vector_store, mock_embedding_service
    ):
        engine = ContextEngine(
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
        )
        bundle = engine.build(query="test", agent_type="qa", session_id="s1")
        assert isinstance(bundle, ContextBundle)
        assert bundle.structural_context == {}
        assert bundle.execution_memory == {}
