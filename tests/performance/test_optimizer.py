import pytest
import asyncio
from concurrent.futures import ThreadPoolExecutor
from architectai.performance.optimizer import (
    ParallelProcessor,
    BatchProcessor,
    MemoryOptimizer,
    AsyncIOHelper,
    PerformanceMonitor,
)


class TestParallelProcessor:
    def test_parallel_map(self):
        pp = ParallelProcessor(max_workers=2)
        items = [1, 2, 3, 4, 5]
        result = pp.map(lambda x: x * 2, items)
        assert sorted(result) == [2, 4, 6, 8, 10]
        pp.shutdown()

    def test_parallel_map_empty(self):
        pp = ParallelProcessor(max_workers=2)
        result = pp.map(lambda x: x * 2, [])
        assert result == []
        pp.shutdown()

    def test_context_manager(self):
        with ParallelProcessor(max_workers=2) as pp:
            result = pp.map(lambda x: x + 1, [1, 2, 3])
            assert sorted(result) == [2, 3, 4]


class TestBatchProcessor:
    def test_batch_process(self):
        bp = BatchProcessor(batch_size=2)
        items = [1, 2, 3, 4, 5]
        batches = list(bp.create_batches(items))
        assert len(batches) == 3
        assert batches[0] == [1, 2]
        assert batches[1] == [3, 4]
        assert batches[2] == [5]

    def test_batch_process_exact_multiple(self):
        bp = BatchProcessor(batch_size=2)
        items = [1, 2, 3, 4]
        batches = list(bp.create_batches(items))
        assert len(batches) == 2
        assert batches[0] == [1, 2]
        assert batches[1] == [3, 4]

    def test_process_batches(self):
        bp = BatchProcessor(batch_size=2)
        items = [1, 2, 3, 4, 5]

        def process_batch(batch):
            return [x * 2 for x in batch]

        results = list(bp.process_batches(process_batch, items))
        assert sorted(results) == [2, 4, 6, 8, 10]


class TestMemoryOptimizer:
    def test_estimate_size(self):
        mo = MemoryOptimizer()
        size = mo.estimate_object_size([1, 2, 3, 4, 5])
        assert size > 0

    def test_format_size(self):
        mo = MemoryOptimizer()
        assert mo.format_size(100) == "100.00 B"
        assert mo.format_size(1024) == "1.00 KB"
        assert mo.format_size(1024 * 1024) == "1.00 MB"

    def test_track_object(self):
        mo = MemoryOptimizer()
        mo.track_object("test", [1, 2, 3])
        sizes = mo.get_tracked_sizes()
        assert "test" in sizes
        assert "B" in sizes["test"]

    def test_force_gc(self):
        mo = MemoryOptimizer()
        # Just verify it doesn't throw
        collected = mo.force_gc()
        assert isinstance(collected, int)


class TestAsyncIOHelper:
    def test_run_async(self):
        async def async_func():
            return "result"

        helper = AsyncIOHelper()
        result = helper.run(async_func())
        assert result == "result"

    def test_run_with_function(self):
        helper = AsyncIOHelper()
        result = helper.run_async(lambda: "computed")
        assert result == "computed"

    def test_gather_with_limit(self):
        async def task(n):
            await asyncio.sleep(0.01)
            return n

        helper = AsyncIOHelper()
        coros = [task(i) for i in range(5)]
        results = helper.run(helper.gather_with_limit(coros, limit=2))
        assert sorted(results) == [0, 1, 2, 3, 4]


class TestPerformanceMonitor:
    def test_record_timing(self):
        pm = PerformanceMonitor()
        pm.record_timing("op1", 0.5)
        pm.record_timing("op1", 1.0)
        pm.record_timing("op2", 0.3)

        stats = pm.get_stats()
        assert stats["op1"]["count"] == 2
        assert stats["op1"]["total"] == 1.5
        assert stats["op1"]["mean"] == 0.75
        assert stats["op2"]["count"] == 1

    def test_time_operation_context(self):
        pm = PerformanceMonitor()

        with pm.time_operation("test_op"):
            pass  # Immediate execution

        stats = pm.get_stats()
        assert "test_op" in stats
        assert stats["test_op"]["count"] == 1

    def test_increment_count(self):
        pm = PerformanceMonitor()
        pm.increment_count("counter1")
        pm.increment_count("counter1", 5)
        pm.increment_count("counter2", 3)

        stats = pm.get_stats()
        assert stats["counts"]["counter1"] == 6
        assert stats["counts"]["counter2"] == 3

    def test_reset(self):
        pm = PerformanceMonitor()
        pm.record_timing("op", 0.5)
        pm.increment_count("counter")

        pm.reset()
        stats = pm.get_stats()

        assert "op" not in stats
        assert not stats["counts"]
