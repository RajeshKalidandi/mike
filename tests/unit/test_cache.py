"""Unit tests for Cache module."""

import pytest
from unittest.mock import MagicMock, patch
import time

from architectai.cache.manager import CacheManager
from architectai.cache.ast_cache import ASTCache
from architectai.cache.embedding_cache import EmbeddingCache
from architectai.cache.graph_cache import GraphCache


class TestCacheManager:
    """Test cases for CacheManager."""

    def test_initialization(self, temp_dir):
        """Test cache manager initialization."""
        cache_dir = temp_dir / "cache"
        manager = CacheManager(str(cache_dir))

        assert manager.cache_dir == cache_dir
        assert cache_dir.exists()

    def test_initialization_creates_directory(self, temp_dir):
        """Test that initialization creates cache directory."""
        cache_dir = temp_dir / "new_cache_dir"

        manager = CacheManager(str(cache_dir))

        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_get_cache_path(self, temp_dir):
        """Test getting cache file path."""
        manager = CacheManager(str(temp_dir))

        path = manager._get_cache_path("test_session", "ast")

        assert "test_session" in str(path)
        assert "ast" in str(path)
        assert path.suffix == ".json"

    def test_clear_session_cache(self, temp_dir):
        """Test clearing session cache."""
        manager = CacheManager(str(temp_dir))

        # Create some cache files
        cache_file = temp_dir / "test_session_ast.json"
        cache_file.write_text("{}")

        manager.clear_session_cache("test_session")

        assert not cache_file.exists()


class TestASTCache:
    """Test cases for ASTCache."""

    def test_initialization(self, temp_dir):
        """Test AST cache initialization."""
        cache = ASTCache(str(temp_dir))

        assert cache.cache_dir == temp_dir

    def test_get_set_ast(self, temp_dir):
        """Test getting and setting AST data."""
        cache = ASTCache(str(temp_dir))

        ast_data = {
            "functions": [{"name": "main", "start_line": 1}],
            "classes": [],
            "imports": [],
        }

        # Set cache
        cache.set("file1.py", "python", ast_data)

        # Get cache
        result = cache.get("file1.py", "python")

        assert result == ast_data

    def test_get_nonexistent(self, temp_dir):
        """Test getting non-existent cache entry."""
        cache = ASTCache(str(temp_dir))

        result = cache.get("nonexistent.py", "python")

        assert result is None

    def test_invalidate_file(self, temp_dir):
        """Test invalidating a file's cache."""
        cache = ASTCache(str(temp_dir))

        ast_data = {"functions": [], "classes": [], "imports": []}
        cache.set("file1.py", "python", ast_data)

        # Invalidate
        cache.invalidate("file1.py")

        result = cache.get("file1.py", "python")
        assert result is None

    def test_clear_all(self, temp_dir):
        """Test clearing all cache entries."""
        cache = ASTCache(str(temp_dir))

        cache.set("file1.py", "python", {"functions": []})
        cache.set("file2.py", "python", {"functions": []})

        cache.clear_all()

        assert cache.get("file1.py", "python") is None
        assert cache.get("file2.py", "python") is None


class TestEmbeddingCache:
    """Test cases for EmbeddingCache."""

    def test_initialization(self, temp_dir):
        """Test embedding cache initialization."""
        cache = EmbeddingCache(str(temp_dir))

        assert cache.cache_dir == temp_dir

    def test_get_set_embedding(self, temp_dir):
        """Test getting and setting embeddings."""
        cache = EmbeddingCache(str(temp_dir))

        embedding = [0.1, 0.2, 0.3, 0.4]

        # Set cache
        cache.set("content_hash_123", embedding)

        # Get cache
        result = cache.get("content_hash_123")

        assert result == embedding

    def test_get_set_batch(self, temp_dir):
        """Test batch get and set operations."""
        cache = EmbeddingCache(str(temp_dir))

        embeddings = {
            "hash1": [0.1, 0.2],
            "hash2": [0.3, 0.4],
        }

        # Set batch
        cache.set_batch(embeddings)

        # Get batch
        results = cache.get_batch(["hash1", "hash2", "hash3"])

        assert results["hash1"] == [0.1, 0.2]
        assert results["hash2"] == [0.3, 0.4]
        assert results["hash3"] is None

    def test_embedding_dimension_consistency(self, temp_dir):
        """Test that embedding dimensions are consistent."""
        cache = EmbeddingCache(str(temp_dir))

        embedding_1024 = [0.1] * 1024
        cache.set("hash1", embedding_1024)

        result = cache.get("hash1")

        assert len(result) == 1024


class TestGraphCache:
    """Test cases for GraphCache."""

    def test_initialization(self, temp_dir):
        """Test graph cache initialization."""
        cache = GraphCache(str(temp_dir))

        assert cache.cache_dir == temp_dir

    def test_get_set_graph(self, temp_dir):
        """Test getting and setting graph data."""
        cache = GraphCache(str(temp_dir))

        graph_data = {
            "session_id": "test_session",
            "nodes": [{"id": "a.py"}, {"id": "b.py"}],
            "edges": [{"source": "a.py", "target": "b.py"}],
        }

        # Set cache
        cache.set("test_session", graph_data)

        # Get cache
        result = cache.get("test_session")

        assert result == graph_data

    def test_graph_stats(self, temp_dir):
        """Test graph statistics retrieval."""
        cache = GraphCache(str(temp_dir))

        graph_data = {
            "session_id": "test_session",
            "nodes": [{"id": "a.py"}, {"id": "b.py"}],
            "edges": [{"source": "a.py", "target": "b.py"}],
        }

        cache.set("test_session", graph_data)

        stats = cache.get_stats("test_session")

        assert stats["nodes"] == 2
        assert stats["edges"] == 1

    def test_invalidate_session(self, temp_dir):
        """Test invalidating session graph cache."""
        cache = GraphCache(str(temp_dir))

        graph_data = {
            "session_id": "test_session",
            "nodes": [],
            "edges": [],
        }

        cache.set("test_session", graph_data)
        cache.invalidate("test_session")

        result = cache.get("test_session")
        assert result is None


class TestCacheIntegration:
    """Integration tests for cache system."""

    def test_multiple_cache_types_same_session(self, temp_dir):
        """Test that different cache types can coexist."""
        ast_cache = ASTCache(str(temp_dir))
        embedding_cache = EmbeddingCache(str(temp_dir))
        graph_cache = GraphCache(str(temp_dir))

        # Store different data types
        ast_cache.set("file.py", "python", {"functions": []})
        embedding_cache.set("hash123", [0.1, 0.2])
        graph_cache.set("session1", {"nodes": [], "edges": []})

        # Retrieve all
        assert ast_cache.get("file.py", "python") is not None
        assert embedding_cache.get("hash123") is not None
        assert graph_cache.get("session1") is not None

    def test_cache_persistence(self, temp_dir):
        """Test that cache persists across instances."""
        # First instance stores data
        cache1 = EmbeddingCache(str(temp_dir))
        cache1.set("hash123", [0.1, 0.2, 0.3])

        # Second instance reads data
        cache2 = EmbeddingCache(str(temp_dir))
        result = cache2.get("hash123")

        assert result == [0.1, 0.2, 0.3]

    def test_cache_ttl(self, temp_dir):
        """Test cache TTL/expiry if implemented."""
        cache = ASTCache(str(temp_dir))

        ast_data = {"functions": [], "classes": [], "imports": []}

        # Store with TTL (if supported)
        cache.set("file.py", "python", ast_data)

        # Immediately retrieve - should exist
        result = cache.get("file.py", "python")
        assert result is not None
