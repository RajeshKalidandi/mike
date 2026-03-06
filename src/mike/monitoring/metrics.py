"""Metrics collection system for Mike."""

import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


class Metric(ABC):
    """Base class for all metrics."""

    def __init__(
        self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None
    ):
        self.name = name
        self.description = description
        self.labels = labels or {}
        self._lock = threading.Lock()

    @abstractmethod
    def get_value(self) -> Any:
        """Get current metric value."""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary."""
        pass


class Counter(Metric):
    """A counter metric that only increases."""

    def __init__(
        self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None
    ):
        super().__init__(name, description, labels)
        self._value = 0

    def inc(self, amount: float = 1) -> None:
        """Increment counter by amount."""
        with self._lock:
            self._value += amount

    def get_value(self) -> float:
        """Get current counter value."""
        with self._lock:
            return self._value

    def to_dict(self) -> Dict[str, Any]:
        """Convert counter to dictionary."""
        return {
            "name": self.name,
            "type": "counter",
            "description": self.description,
            "labels": self.labels,
            "value": self.get_value(),
        }


class Gauge(Metric):
    """A gauge metric that can go up and down."""

    def __init__(
        self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None
    ):
        super().__init__(name, description, labels)
        self._value = 0.0

    def set(self, value: float) -> None:
        """Set gauge to specific value."""
        with self._lock:
            self._value = value

    def inc(self, amount: float = 1) -> None:
        """Increment gauge."""
        with self._lock:
            self._value += amount

    def dec(self, amount: float = 1) -> None:
        """Decrement gauge."""
        with self._lock:
            self._value -= amount

    def get_value(self) -> float:
        """Get current gauge value."""
        with self._lock:
            return self._value

    def to_dict(self) -> Dict[str, Any]:
        """Convert gauge to dictionary."""
        return {
            "name": self.name,
            "type": "gauge",
            "description": self.description,
            "labels": self.labels,
            "value": self.get_value(),
        }


class Histogram(Metric):
    """A histogram metric for recording distributions."""

    DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60]

    def __init__(
        self,
        name: str,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
        buckets: Optional[List[float]] = None,
    ):
        super().__init__(name, description, labels)
        self.buckets = sorted(buckets or self.DEFAULT_BUCKETS)
        self._counts = {b: 0 for b in self.buckets}
        self._counts[float("inf")] = 0
        self._sum = 0.0
        self._count = 0
        self._values: deque = deque(maxlen=1000)

    def observe(self, value: float) -> None:
        """Record a value in the histogram."""
        with self._lock:
            self._sum += value
            self._count += 1
            self._values.append(value)

            for bucket in self.buckets:
                if value <= bucket:
                    self._counts[bucket] += 1
            self._counts[float("inf")] += 1

    def get_value(self) -> Dict[str, Any]:
        """Get histogram statistics."""
        with self._lock:
            values = list(self._values)
            if not values:
                return {
                    "count": 0,
                    "sum": 0,
                    "avg": 0,
                    "min": 0,
                    "max": 0,
                    "p50": 0,
                    "p95": 0,
                    "p99": 0,
                }

            sorted_values = sorted(values)
            n = len(sorted_values)

            return {
                "count": self._count,
                "sum": self._sum,
                "avg": self._sum / self._count if self._count > 0 else 0,
                "min": sorted_values[0],
                "max": sorted_values[-1],
                "p50": sorted_values[int(n * 0.5)],
                "p95": sorted_values[int(n * 0.95)] if n > 1 else sorted_values[0],
                "p99": sorted_values[int(n * 0.99)] if n > 1 else sorted_values[0],
            }

    def get_buckets(self) -> Dict[float, int]:
        """Get bucket counts."""
        with self._lock:
            return self._counts.copy()

    def to_dict(self) -> Dict[str, Any]:
        """Convert histogram to dictionary."""
        return {
            "name": self.name,
            "type": "histogram",
            "description": self.description,
            "labels": self.labels,
            "buckets": self.get_buckets(),
            "statistics": self.get_value(),
        }


@dataclass
class AgentMetrics:
    """Metrics for a single agent execution."""

    agent_name: str
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    tokens_used: int = 0
    success: bool = False
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentMetricsCollector:
    """Collector for agent-specific metrics."""

    def __init__(self, registry: "MetricsRegistry"):
        self.registry = registry
        self._active_executions: Dict[str, AgentMetrics] = {}
        self._lock = threading.Lock()

        self.execution_time = registry.histogram(
            "agent_execution_time_seconds",
            "Time spent executing agents",
            buckets=[0.1, 0.5, 1, 5, 10, 30, 60, 120, 300],
        )

        self.execution_count = registry.counter(
            "agent_executions_total",
            "Total number of agent executions",
        )

        self.success_count = registry.counter(
            "agent_executions_success_total",
            "Total number of successful agent executions",
        )

        self.failure_count = registry.counter(
            "agent_executions_failure_total",
            "Total number of failed agent executions",
        )

        self.tokens_used = registry.counter(
            "agent_tokens_used_total",
            "Total tokens used by agents",
        )

    def start_execution(self, agent_name: str, session_id: str) -> str:
        """Start tracking an agent execution."""
        execution_id = f"{agent_name}_{session_id}_{time.time()}"

        with self._lock:
            self._active_executions[execution_id] = AgentMetrics(
                agent_name=agent_name,
                session_id=session_id,
                start_time=time.time(),
            )

        self.execution_count.inc()
        return execution_id

    def end_execution(
        self,
        execution_id: str,
        success: bool = True,
        tokens_used: int = 0,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[AgentMetrics]:
        """End tracking an agent execution."""
        with self._lock:
            metrics = self._active_executions.pop(execution_id, None)

        if metrics is None:
            return None

        metrics.end_time = time.time()
        metrics.duration_ms = (metrics.end_time - metrics.start_time) * 1000
        metrics.success = success
        metrics.tokens_used = tokens_used
        metrics.error_message = error_message
        if metadata:
            metrics.metadata.update(metadata)

        self.execution_time.observe(metrics.duration_ms / 1000)
        self.tokens_used.inc(tokens_used)

        if success:
            self.success_count.inc()
        else:
            self.failure_count.inc()

        return metrics


class DatabaseMetricsCollector:
    """Collector for database query metrics."""

    def __init__(self, registry: "MetricsRegistry"):
        self.registry = registry

        self.query_time = registry.histogram(
            "db_query_time_seconds",
            "Time spent executing database queries",
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1],
        )

        self.query_count = registry.counter(
            "db_queries_total",
            "Total number of database queries",
        )

        self.error_count = registry.counter(
            "db_query_errors_total",
            "Total number of database query errors",
        )

    def record_query(
        self,
        query_type: str,
        duration_ms: float,
        success: bool = True,
        rows_affected: Optional[int] = None,
    ) -> None:
        """Record a database query."""
        self.query_time.observe(duration_ms / 1000)
        self.query_count.inc()

        if not success:
            self.error_count.inc()


class LLMMetricsCollector:
    """Collector for LLM call metrics."""

    def __init__(self, registry: "MetricsRegistry"):
        self.registry = registry

        self.call_duration = registry.histogram(
            "llm_call_duration_seconds",
            "Duration of LLM calls",
            buckets=[0.5, 1, 2, 5, 10, 20, 30, 60],
        )

        self.token_usage = registry.histogram(
            "llm_tokens_total",
            "Total tokens used in LLM calls",
            buckets=[100, 500, 1000, 2000, 4000, 8000, 16000, 32000],
        )

        self.prompt_tokens = registry.counter(
            "llm_prompt_tokens_total",
            "Total prompt tokens used",
        )

        self.completion_tokens = registry.counter(
            "llm_completion_tokens_total",
            "Total completion tokens used",
        )

        self.call_count = registry.counter(
            "llm_calls_total",
            "Total number of LLM calls",
        )

        self.error_count = registry.counter(
            "llm_call_errors_total",
            "Total number of LLM call errors",
        )

    def record_call(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration_ms: float,
        success: bool = True,
    ) -> None:
        """Record an LLM call."""
        total_tokens = prompt_tokens + completion_tokens

        self.call_duration.observe(duration_ms / 1000)
        self.token_usage.observe(total_tokens)
        self.prompt_tokens.inc(prompt_tokens)
        self.completion_tokens.inc(completion_tokens)
        self.call_count.inc()

        if not success:
            self.error_count.inc()


class FileMetricsCollector:
    """Collector for file processing metrics."""

    def __init__(self, registry: "MetricsRegistry"):
        self.registry = registry

        self.process_time = registry.histogram(
            "file_process_time_seconds",
            "Time spent processing files",
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1],
        )

        self.process_count = registry.counter(
            "files_processed_total",
            "Total number of files processed",
        )

        self.error_count = registry.counter(
            "file_process_errors_total",
            "Total number of file processing errors",
        )

        self.bytes_processed = registry.counter(
            "file_bytes_processed_total",
            "Total bytes of files processed",
        )

        self.lines_processed = registry.counter(
            "file_lines_processed_total",
            "Total lines of files processed",
        )

    def record_file(
        self,
        file_size: int,
        line_count: int,
        duration_ms: float,
        success: bool = True,
    ) -> None:
        """Record a file processing."""
        self.process_time.observe(duration_ms / 1000)
        self.process_count.inc()
        self.bytes_processed.inc(file_size)
        self.lines_processed.inc(line_count)

        if not success:
            self.error_count.inc()


class MetricsRegistry:
    """Central registry for all metrics."""

    def __init__(self):
        self._metrics: Dict[str, Metric] = {}
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[Metric], None]] = []

    def counter(
        self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None
    ) -> Counter:
        """Create or get a counter."""
        with self._lock:
            if name not in self._metrics:
                counter = Counter(name, description, labels)
                self._metrics[name] = counter
                self._notify(counter)
            return self._metrics[name]

    def gauge(
        self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None
    ) -> Gauge:
        """Create or get a gauge."""
        with self._lock:
            if name not in self._metrics:
                gauge = Gauge(name, description, labels)
                self._metrics[name] = gauge
                self._notify(gauge)
            return self._metrics[name]

    def histogram(
        self,
        name: str,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
        buckets: Optional[List[float]] = None,
    ) -> Histogram:
        """Create or get a histogram."""
        with self._lock:
            if name not in self._metrics:
                histogram = Histogram(name, description, labels, buckets)
                self._metrics[name] = histogram
                self._notify(histogram)
            return self._metrics[name]

    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a metric by name."""
        with self._lock:
            return self._metrics.get(name)

    def get_all_metrics(self) -> Dict[str, Metric]:
        """Get all registered metrics."""
        with self._lock:
            return self._metrics.copy()

    def _notify(self, metric: Metric) -> None:
        """Notify callbacks of new metric."""
        for callback in self._callbacks:
            try:
                callback(metric)
            except Exception:
                pass

    def register_callback(self, callback: Callable[[Metric], None]) -> None:
        """Register a callback for new metrics."""
        self._callbacks.append(callback)

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Convert all metrics to dictionary."""
        with self._lock:
            return {name: metric.to_dict() for name, metric in self._metrics.items()}

    def to_prometheus_format(self) -> str:
        """Export metrics in Prometheus exposition format."""
        lines = []

        for name, metric in self._metrics.items():
            lines.append(f"# HELP {name} {metric.description}")
            lines.append(f"# TYPE {name} {metric.to_dict()['type']}")

            labels_str = ""
            if metric.labels:
                labels_parts = [f'{k}="{v}"' for k, v in metric.labels.items()]
                labels_str = "{" + ",".join(labels_parts) + "}"

            if isinstance(metric, Counter) or isinstance(metric, Gauge):
                lines.append(f"{name}{labels_str} {metric.get_value()}")
            elif isinstance(metric, Histogram):
                buckets = metric.get_buckets()
                for bucket, count in sorted(buckets.items()):
                    bucket_val = "+Inf" if bucket == float("inf") else str(bucket)
                    lines.append(f'{name}_bucket{{le="{bucket_val}"}} {count}')
                stats = metric.get_value()
                lines.append(f"{name}_sum{labels_str} {stats['sum']}")
                lines.append(f"{name}_count{labels_str} {stats['count']}")

            lines.append("")

        return "\n".join(lines)


class PerformanceMonitor:
    """Monitor for detecting performance regressions."""

    def __init__(self, registry: MetricsRegistry, window_size: int = 100):
        self.registry = registry
        self.window_size = window_size
        self._baselines: Dict[str, Dict[str, float]] = {}
        self._lock = threading.Lock()

    def set_baseline(
        self, metric_name: str, p50: float, p95: float, p99: float
    ) -> None:
        """Set baseline performance values."""
        with self._lock:
            self._baselines[metric_name] = {
                "p50": p50,
                "p95": p95,
                "p99": p99,
            }

    def check_regression(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Check if metric shows performance regression."""
        metric = self.registry.get_metric(metric_name)
        if metric is None or not isinstance(metric, Histogram):
            return None

        baseline = self._baselines.get(metric_name)
        if baseline is None:
            return None

        stats = metric.get_value()
        regressions = []

        for percentile, baseline_value in baseline.items():
            current_value = stats.get(percentile, 0)
            if current_value > baseline_value * 1.2:
                regressions.append(
                    {
                        "percentile": percentile,
                        "baseline": baseline_value,
                        "current": current_value,
                        "increase_percent": (
                            (current_value - baseline_value) / baseline_value
                        )
                        * 100,
                    }
                )

        if regressions:
            return {
                "metric": metric_name,
                "regressions": regressions,
                "severity": "high"
                if any(r["increase_percent"] > 50 for r in regressions)
                else "medium",
            }

        return None

    def check_all_regressions(self) -> List[Dict[str, Any]]:
        """Check all metrics for regressions."""
        results = []
        for metric_name in self._baselines:
            regression = self.check_regression(metric_name)
            if regression:
                results.append(regression)
        return results
