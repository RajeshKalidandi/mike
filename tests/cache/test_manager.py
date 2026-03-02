import pytest
import tempfile
import os
from architectai.cache.manager import CacheManager


class TestCacheManager:
    def test_cache_manager_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(base_path=tmpdir)
            assert cm is not None
            assert cm.stats["hits"] == 0
            assert cm.stats["misses"] == 0

    def test_memory_cache_set_get(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(base_path=tmpdir)
            cm.set("key1", "value1", backend="memory")
            result = cm.get("key1", backend="memory")
            assert result == "value1"

    def test_cache_miss_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(base_path=tmpdir)
            result = cm.get("nonexistent")
            assert result is None
            assert cm.stats["misses"] == 1

    def test_cache_hit_updates_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(base_path=tmpdir)
            cm.set("key1", "value1")
            cm.get("key1")
            cm.get("key1")
            assert cm.stats["hits"] == 2
            assert cm.stats["sets"] == 1

    def test_disk_cache_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(base_path=tmpdir)
            cm.set("persist_key", {"data": "test"}, backend="disk")

            # Create new manager to test persistence
            cm2 = CacheManager(base_path=tmpdir)
            result = cm2.get("persist_key", backend="disk")
            assert result == {"data": "test"}

    def test_generate_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(base_path=tmpdir)
            key1 = cm.generate_key("component1", "component2", 123)
            key2 = cm.generate_key("component1", "component2", 123)
            assert key1 == key2
            assert len(key1) == 64

    def test_cache_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(base_path=tmpdir)
            cm.set("key", "value")
            assert cm.delete("key")
            assert cm.get("key") is None

    def test_cache_clear(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(base_path=tmpdir)
            cm.set("key1", "value1")
            cm.set("key2", "value2")
            cm.clear()
            assert cm.get("key1") is None
            assert cm.get("key2") is None

    def test_warm_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(base_path=tmpdir)
            items = [("k1", "v1"), ("k2", "v2"), ("k3", "v3")]
            cm.warm_cache(items)
            assert cm.get("k1") == "v1"
            assert cm.get("k2") == "v2"
            assert cm.get("k3") == "v3"
