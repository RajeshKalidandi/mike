"""Performance optimization utilities for parallel processing and memory management."""

import asyncio
import gc
import sys
import threading
import time
from collections import deque
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from functools import partial
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    TypeVar,
    Union,
)


T = TypeVar("T")
R = TypeVar("R")


class ParallelProcessor:
    """Parallel processing utilities using thread and process pools."""

    def __init__(self, max_workers: Optional[int] = None, use_processes: bool = False):
        self.max_workers = max_workers
        self.use_processes = use_processes
        self._executor: Optional[Union[ThreadPoolExecutor, ProcessPoolExecutor]] = None

    def _get_executor(self):
        if self._executor is None:
            if self.use_processes:
                self._executor = ProcessPoolExecutor(max_workers=self.max_workers)
            else:
                self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self._executor

    def map(
        self, func: Callable[[T], R], items: Iterable[T], chunksize: int = 1
    ) -> List[R]:
        """Map function over items in parallel."""
        executor = self._get_executor()
        return list(executor.map(func, items, chunksize=chunksize))

    def map_ordered(
        self, func: Callable[[T], R], items: Iterable[T]
    ) -> Generator[R, None, None]:
        """Map function with ordered results as they complete."""
        executor = self._get_executor()
        futures = {executor.submit(func, item): idx for idx, item in enumerate(items)}

        results = {}
        next_idx = 0

        for future in as_completed(futures):
            idx = futures[future]
            result = future.result()
            results[idx] = result

            while next_idx in results:
                yield results.pop(next_idx)
                next_idx += 1

    def shutdown(self, wait: bool = True):
        """Shutdown the executor."""
        if self._executor:
            self._executor.shutdown(wait=wait)
            self._executor = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


class BatchProcessor:
    """Batch processing utilities for efficient I/O operations."""

    def __init__(self, batch_size: int = 100, max_queue_size: int = 1000):
        self.batch_size = batch_size
        self.max_queue_size = max_queue_size

    def create_batches(self, items: Iterable[T]) -> Generator[List[T], None, None]:
        """Create batches from iterable."""
        batch = []
        for item in items:
            batch.append(item)
            if len(batch) >= self.batch_size:
                yield batch
                batch = []

        if batch:
            yield batch

    def process_batches(
        self, func: Callable[[List[T]], List[R]], items: Iterable[T]
    ) -> Generator[R, None, None]:
        """Process items in batches and yield results."""
        for batch in self.create_batches(items):
            results = func(batch)
            for result in results:
                yield result

    async def process_batches_async(
        self, func: Callable[[List[T]], Any], items: Iterable[T]
    ) -> List[Any]:
        """Process batches asynchronously."""
        tasks = []
        for batch in self.create_batches(items):
            task = asyncio.create_task(self._async_wrapper(func, batch))
            tasks.append(task)

        return await asyncio.gather(*tasks)

    async def _async_wrapper(self, func, batch):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, batch)


class MemoryOptimizer:
    """Memory optimization utilities."""

    def __init__(self, max_memory_mb: Optional[int] = None):
        self.max_memory_mb = max_memory_mb
        self._tracked_objects: Dict[str, Any] = {}

    def estimate_object_size(self, obj: Any) -> int:
        """Estimate memory size of an object in bytes."""
        seen = set()
        size = 0

        def sizeof(o):
            nonlocal size
            obj_id = id(o)
            if obj_id in seen:
                return
            seen.add(obj_id)
            size += sys.getsizeof(o)

            if isinstance(o, dict):
                for k, v in o.items():
                    sizeof(k)
                    sizeof(v)
            elif isinstance(o, (list, tuple, set)):
                for item in o:
                    sizeof(item)

        sizeof(obj)
        return size

    def format_size(self, size_bytes: int) -> str:
        """Format bytes to human-readable string."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"

    def track_object(self, name: str, obj: Any) -> None:
        """Track an object for memory monitoring."""
        self._tracked_objects[name] = obj

    def untrack_object(self, name: str) -> None:
        """Stop tracking an object."""
        self._tracked_objects.pop(name, None)

    def get_tracked_sizes(self) -> Dict[str, str]:
        """Get memory sizes of tracked objects."""
        return {
            name: self.format_size(self.estimate_object_size(obj))
            for name, obj in self._tracked_objects.items()
        }

    def force_gc(self) -> int:
        """Force garbage collection. Returns number of objects collected."""
        collected = gc.collect()
        return collected

    def clear_references(self, obj_name: str) -> bool:
        """Clear references to a tracked object to allow GC."""
        if obj_name in self._tracked_objects:
            del self._tracked_objects[obj_name]
            return True
        return False


class AsyncIOHelper:
    """Helper utilities for async I/O operations."""

    def __init__(self):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = threading.Lock()

    def get_event_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create event loop."""
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            with self._lock:
                if self._loop is None:
                    self._loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._loop)
                return self._loop

    def run(self, coro) -> Any:
        """Run a coroutine in the event loop."""
        loop = self.get_event_loop()
        return loop.run_until_complete(coro)

    def run_async(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Run a function asynchronously."""

        async def wrapper():
            return func(*args, **kwargs)

        return self.run(wrapper())

    async def gather_with_limit(
        self, coros: Iterable[Any], limit: int = 10
    ) -> List[Any]:
        """Gather coroutines with concurrency limit."""
        semaphore = asyncio.Semaphore(limit)

        async def bounded_coro(coro):
            async with semaphore:
                return await coro

        return await asyncio.gather(*[bounded_coro(c) for c in coros])

    async def run_in_executor(self, func: Callable[..., R], *args, **kwargs) -> R:
        """Run a function in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))

    def close(self):
        """Close the event loop."""
        if self._loop and not self._loop.is_closed():
            self._loop.close()
            self._loop = None


class PerformanceMonitor:
    """Monitor performance metrics during operations."""

    def __init__(self):
        self._timings: Dict[str, List[float]] = {}
        self._counts: Dict[str, int] = {}

    def time_operation(self, name: str):
        """Context manager for timing operations."""
        return _TimingContext(self, name)

    def record_timing(self, name: str, duration: float):
        """Record a timing."""
        if name not in self._timings:
            self._timings[name] = []
        self._timings[name].append(duration)

    def increment_count(self, name: str, amount: int = 1):
        """Increment a counter."""
        self._counts[name] = self._counts.get(name, 0) + amount

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        stats = {}

        for name, timings in self._timings.items():
            if timings:
                stats[name] = {
                    "count": len(timings),
                    "total": sum(timings),
                    "mean": sum(timings) / len(timings),
                    "min": min(timings),
                    "max": max(timings),
                }

        stats["counts"] = self._counts.copy()
        return stats

    def reset(self):
        """Reset all statistics."""
        self._timings.clear()
        self._counts.clear()


class _TimingContext:
    """Context manager for timing operations."""

    def __init__(self, monitor: PerformanceMonitor, name: str):
        self.monitor = monitor
        self.name = name
        self.start_time: Optional[float] = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.monitor.record_timing(self.name, duration)
