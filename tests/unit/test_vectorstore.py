"""Unit tests for the VectorStore module."""

import pytest
from unittest.mock import MagicMock, patch

from mike.vectorstore.store import VectorStore


class TestVectorStore:
    """Test cases for VectorStore."""

    def test_store_initialization(self, temp_dir):
        """Test vector store initialization."""
        store = VectorStore(str(temp_dir))

        assert store.persist_directory == str(temp_dir)
        assert store.collection_prefix == "mike"

    def test_store_initialization_custom_prefix(self, temp_dir):
        """Test vector store with custom prefix."""
        store = VectorStore(str(temp_dir), collection_prefix="custom")

        assert store.collection_prefix == "custom"

    def test_get_collection_name(self, temp_dir):
        """Test collection name generation."""
        store = VectorStore(str(temp_dir), collection_prefix="test")

        name = store._get_collection_name("session123")
        assert name == "test_session123"

    @patch("mike.vectorstore.store.chromadb.PersistentClient")
    def test_add_chunks_empty(self, MockClient, temp_dir):
        """Test adding empty chunks list."""
        store = VectorStore(str(temp_dir))

        # Should not raise exception
        store.add_chunks([], "session123")

        # Collection should not be created
        MockClient.return_value.get_collection.assert_not_called()

    @patch("mike.vectorstore.store.chromadb.PersistentClient")
    def test_add_chunks(self, MockClient, temp_dir, sample_chunks_with_embeddings):
        """Test adding chunks to vector store."""
        mock_collection = MagicMock()
        # Simulate collection doesn't exist initially, so get_collection raises exception
        MockClient.return_value.get_collection.side_effect = Exception("Not found")
        MockClient.return_value.create_collection.return_value = mock_collection

        store = VectorStore(str(temp_dir))
        store.add_chunks(sample_chunks_with_embeddings, "session123")

        # Collection should be created
        MockClient.return_value.create_collection.assert_called_once()

        # Chunks should be added
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        assert "ids" in call_args.kwargs
        assert "documents" in call_args.kwargs
        assert "embeddings" in call_args.kwargs
        assert "metadatas" in call_args.kwargs

    @patch("mike.vectorstore.store.chromadb.PersistentClient")
    def test_search(self, MockClient, temp_dir):
        """Test searching vector store."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "documents": [["content1", "content2"]],
            "metadatas": [[{"key": "value"}, {"key": "value2"}]],
            "distances": [[0.1, 0.2]],
        }
        MockClient.return_value.get_collection.return_value = mock_collection

        store = VectorStore(str(temp_dir))
        results = store.search([0.1] * 1024, "session123", n_results=2)

        assert len(results) == 2
        assert results[0]["id"] == "id1"
        assert results[0]["content"] == "content1"
        assert results[0]["distance"] == 0.1

    @patch("mike.vectorstore.store.chromadb.PersistentClient")
    def test_search_no_results(self, MockClient, temp_dir):
        """Test searching with no results."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
        MockClient.return_value.get_collection.return_value = mock_collection

        store = VectorStore(str(temp_dir))
        results = store.search([0.1] * 1024, "session123")

        assert results == []

    @patch("mike.vectorstore.store.chromadb.PersistentClient")
    def test_search_by_text(self, MockClient, temp_dir, mock_embedding_service):
        """Test searching with text query."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["id1"]],
            "documents": [["content1"]],
            "metadatas": [[{"key": "value"}]],
            "distances": [[0.1]],
        }
        MockClient.return_value.get_collection.return_value = mock_collection

        store = VectorStore(str(temp_dir))
        results = store.search_by_text(
            "test query", mock_embedding_service, "session123"
        )

        assert len(results) == 1
        mock_embedding_service.embed.assert_called_once_with("test query")

    @patch("mike.vectorstore.store.chromadb.PersistentClient")
    def test_delete_session(self, MockClient, temp_dir):
        """Test deleting session data."""
        store = VectorStore(str(temp_dir))
        store.delete_session("session123")

        MockClient.return_value.delete_collection.assert_called_once_with(
            name="mike_session123"
        )

    @patch("mike.vectorstore.store.chromadb.PersistentClient")
    def test_delete_session_nonexistent(self, MockClient, temp_dir):
        """Test deleting non-existent session (should not raise)."""
        MockClient.return_value.delete_collection.side_effect = Exception("Not found")

        store = VectorStore(str(temp_dir))

        # Should not raise exception
        store.delete_session("session123")

    @patch("mike.vectorstore.store.chromadb.PersistentClient")
    def test_count(self, MockClient, temp_dir):
        """Test counting chunks in session."""
        mock_collection = MagicMock()
        mock_collection.count.return_value = 42
        MockClient.return_value.get_collection.return_value = mock_collection

        store = VectorStore(str(temp_dir))
        count = store.count("session123")

        assert count == 42

    @patch("mike.vectorstore.store.chromadb.PersistentClient")
    def test_count_error(self, MockClient, temp_dir):
        """Test counting when collection doesn't exist."""
        MockClient.return_value.get_collection.side_effect = Exception("Not found")
        MockClient.return_value.create_collection.side_effect = Exception("Not found")

        store = VectorStore(str(temp_dir))
        count = store.count("session123")

        assert count == 0

    @patch("mike.vectorstore.store.chromadb.PersistentClient")
    def test_list_sessions(self, MockClient, temp_dir):
        """Test listing all sessions."""
        # Mock collections
        mock_collection1 = MagicMock()
        mock_collection1.name = "mike_session1"
        mock_collection2 = MagicMock()
        mock_collection2.name = "mike_session2"
        mock_collection3 = MagicMock()
        mock_collection3.name = "other_collection"

        MockClient.return_value.list_collections.return_value = [
            mock_collection1,
            mock_collection2,
            mock_collection3,
        ]

        store = VectorStore(str(temp_dir))
        sessions = store.list_sessions()

        assert "session1" in sessions
        assert "session2" in sessions
        assert "other_collection" not in sessions

    @patch("mike.vectorstore.store.chromadb.PersistentClient")
    def test_list_sessions_error(self, MockClient, temp_dir):
        """Test listing sessions when client fails."""
        MockClient.return_value.list_collections.side_effect = Exception("Error")

        store = VectorStore(str(temp_dir))
        sessions = store.list_sessions()

        assert sessions == []

    @patch("mike.vectorstore.store.chromadb.PersistentClient")
    def test_metadata_serialization(self, MockClient, temp_dir):
        """Test that complex metadata values are serialized."""
        mock_collection = MagicMock()
        # Simulate collection doesn't exist initially
        MockClient.return_value.get_collection.side_effect = Exception("Not found")
        MockClient.return_value.create_collection.return_value = mock_collection

        store = VectorStore(str(temp_dir))

        chunks = [
            {
                "content": "test",
                "embedding": [0.1] * 1024,
                "metadata": {
                    "string_val": "test",
                    "int_val": 42,
                    "float_val": 3.14,
                    "bool_val": True,
                    "list_val": [1, 2, 3],  # Should be converted to string
                    "dict_val": {"key": "value"},  # Should be converted to string
                },
            }
        ]

        store.add_chunks(chunks, "session123")

        # Get the metadatas passed to add
        call_args = mock_collection.add.call_args
        metadatas = call_args.kwargs["metadatas"]

        # Check serialization
        assert metadatas[0]["string_val"] == "test"
        assert metadatas[0]["int_val"] == 42
        assert metadatas[0]["float_val"] == 3.14
        assert metadatas[0]["bool_val"] == True
        assert metadatas[0]["list_val"] == "[1, 2, 3]"
        assert metadatas[0]["dict_val"] == "{'key': 'value'}"


class TestVectorStoreIntegration:
    """Integration tests for VectorStore with real ChromaDB."""

    def test_full_workflow(self, temp_vector_dir, mock_embedding_service):
        """Test full workflow with real ChromaDB."""
        store = VectorStore(str(temp_vector_dir))
        session_id = "test_session"

        # Add chunks
        chunks = [
            {
                "content": "def main(): pass",
                "embedding": [0.1] * 1024,
                "metadata": {"file_path": "main.py", "type": "function"},
            },
            {
                "content": "class MyClass: pass",
                "embedding": [0.2] * 1024,
                "metadata": {"file_path": "class.py", "type": "class"},
            },
        ]

        store.add_chunks(chunks, session_id)

        # Verify count
        count = store.count(session_id)
        assert count == 2

        # Search
        query_embedding = [0.15] * 1024
        results = store.search(query_embedding, session_id, n_results=2)

        assert len(results) > 0

        # List sessions
        sessions = store.list_sessions()
        assert session_id in sessions

        # Delete session
        store.delete_session(session_id)
        count_after = store.count(session_id)
        assert count_after == 0
