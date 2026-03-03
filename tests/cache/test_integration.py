import pytest
import tempfile
import numpy as np
import networkx as nx
from mike.cache import CacheManager, ASTCache, EmbeddingCache, GraphCache
from mike.performance import ParallelProcessor, BatchProcessor


class TestCacheIntegration:
    def test_full_cache_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test AST caching
            ast_cache = ASTCache(base_path=tmpdir, parser_version="1.0")
            ast_tree = {"type": "function", "name": "hello"}
            ast_cache.set_ast("file123", "python", ast_tree)
            assert ast_cache.get_ast("file123", "python") == ast_tree

            # Test Embedding caching
            emb_cache = EmbeddingCache(base_path=tmpdir, model_version="test-1.0")
            embedding = np.array([0.1, 0.2, 0.3])
            emb_cache.set_embedding("hello world", embedding)
            retrieved_emb = emb_cache.get_embedding("hello world")
            assert np.allclose(retrieved_emb, embedding)

            # Test Graph caching
            graph_cache = GraphCache(base_path=tmpdir)
            graph = nx.DiGraph()
            graph.add_edge("A", "B")
            graph_cache.set_graph("repo123", "deps", graph)
            retrieved_graph = graph_cache.get_graph("repo123", "deps")
            assert list(retrieved_graph.edges()) == [("A", "B")]

    def test_cache_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # First session
            cache = CacheManager(base_path=tmpdir)
            cache.set("key1", {"nested": ["data"]})

            # Second session (simulated)
            cache2 = CacheManager(base_path=tmpdir)
            result = cache2.get("key1")
            assert result == {"nested": ["data"]}

    def test_performance_with_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(base_path=tmpdir)

            # Simulate expensive computation
            def expensive_compute(x):
                result = x**2
                # Cache the result
                cache.set(f"compute_{x}", result)
                return result

            # First computation (expensive)
            import time

            start = time.time()
            result1 = expensive_compute(100)
            compute_time = time.time() - start

            # Second computation (from cache)
            start = time.time()
            result2 = cache.get("compute_100")
            cache_time = time.time() - start

            assert result1 == result2 == 10000
            # Cache should be faster
            assert cache_time < compute_time


class TestCachePerformanceTargets:
    def test_cache_hit_speedup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(base_path=tmpdir)

            # Populate cache
            for i in range(100):
                cache.set(f"key{i}", {"data": i * 2})

            # Measure cache hit time
            import time

            start = time.time()
            for i in range(1000):
                cache.get(f"key{i % 100}")
            hit_time = time.time() - start

            # Should be fast (less than 1 second for 1000 hits)
            assert hit_time < 1.0

            # Verify stats
            stats = cache.stats
            assert stats["hits"] == 1000

    def test_batch_operations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(base_path=tmpdir)

            # Batch insert
            items = [(f"batch_key_{i}", i * 10) for i in range(1000)]
            cache.warm_cache(items)

            # Verify all items
            for i in range(1000):
                assert cache.get(f"batch_key_{i}") == i * 10


class TestParallelWithCache:
    def test_parallel_cache_access(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(base_path=tmpdir)

            # Pre-populate cache
            for i in range(100):
                cache.set(f"parallel_key_{i}", i**2)

            # Parallel access
            pp = ParallelProcessor(max_workers=4)
            keys = [f"parallel_key_{i}" for i in range(100)]
            results = pp.map(cache.get, keys)
            pp.shutdown()

            assert len(results) == 100
            assert all(r is not None for r in results)

    def test_batch_processing_integration(self):
        bp = BatchProcessor(batch_size=10)
        items = list(range(100))

        batches = list(bp.create_batches(items))
        assert len(batches) == 10

        # Verify all items processed
        all_items = []
        for batch in batches:
            all_items.extend(batch)
        assert all_items == items
