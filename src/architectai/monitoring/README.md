# ArchitectAI Monitoring Module

A comprehensive monitoring and telemetry system for tracking agent performance, system metrics, and usage statistics in ArchitectAI.

## Features

- **Event Tracking**: Track agent starts, completions, errors, LLM calls, database queries, and file processing
- **Performance Metrics**: Counter, Gauge, and Histogram metric types with Prometheus-compatible export
- **System Monitoring**: Real-time CPU, memory, and disk usage tracking
- **Session Management**: Session-level and system-level aggregation
- **Reporting**: Console, JSON, and Markdown report generation
- **Dashboard**: HTML dashboard with interactive charts
- **Offline Operation**: 100% local - no external APIs required

## Quick Start

```python
from architectai.monitoring import TelemetryCollector, MetricsRegistry

# Initialize telemetry
collector = TelemetryCollector()
registry = MetricsRegistry()

# Start a session
collector.start_session("session_123")

# Record an event
span_id = collector.record_agent_start("documentation_agent")
# ... do work ...
collector.record_agent_complete(span_id, success=True, tokens_used=1500)

# End session
collector.end_session()
```

## CLI Commands

### Show Statistics
```bash
# Show system-wide statistics
architectai telemetry stats

# Show statistics for a specific session
architectai telemetry stats --session <session_id>

# Output in different formats
architectai telemetry stats --format json
architectai telemetry stats --format markdown
```

### Generate Reports
```bash
# Generate console report
architectai telemetry report

# Generate JSON report
architectai telemetry report --format json

# Generate Markdown report and save to file
architectai telemetry report --format markdown --output report.md

# Report for specific session
architectai telemetry report --session <session_id>
```

### Generate Dashboard
```bash
# Generate HTML dashboard
architectai telemetry dashboard --output dashboard.html

# Generate and serve on localhost
architectai telemetry dashboard --serve --port 8080
```

### View Metrics
```bash
# Show current metrics
architectai telemetry metrics

# Export in Prometheus format
architectai telemetry metrics --format prometheus

# Export as JSON
architectai telemetry metrics --format json
```

## Module Structure

### telemetry.py
`TelemetryCollector` - Main telemetry collection system:
- Event tracking with timestamps
- Session management
- Performance snapshots (CPU, memory, disk)
- SQLite storage for events
- JSON log files for session logs
- Callback system for real-time notifications

### metrics.py
`MetricsRegistry` - Central metrics registry:
- `Counter`: Monotonically increasing values
- `Gauge`: Values that can go up or down
- `Histogram`: Distribution tracking with percentiles
- Prometheus-compatible export format
- Specialized collectors: `AgentMetricsCollector`, `DatabaseMetricsCollector`, `LLMMetricsCollector`, `FileMetricsCollector`
- `PerformanceMonitor`: Detect performance regressions

### reporter.py
Reporters for different output formats:
- `ConsoleReporter`: Human-readable console output
- `JsonReporter`: Machine-readable JSON output
- `MarkdownReporter`: Documentation-friendly Markdown
- `ReportGenerator`: Comprehensive reports with trend analysis

### dashboard.py
`DashboardGenerator` - HTML dashboard generation:
- Interactive charts using Chart.js
- Real-time metrics view
- Historical data visualization
- Agent performance comparison
- Built-in HTTP server option

## Storage

- **SQLite Database**: `~/.architectai/telemetry.db`
  - `telemetry_events`: All telemetry events
  - `telemetry_sessions`: Session metadata
  - `performance_snapshots`: System performance history

- **Log Files**: `~/.architectai/logs/telemetry_YYYYMMDD.jsonl`
  - Rotating daily log files
  - JSON Lines format
  - Easy to parse and analyze

## Metrics Tracked

### Agent Metrics
- Execution count (total, success, failure)
- Execution duration (avg, p50, p95, p99)
- Token usage
- Success rate

### Database Metrics
- Query count
- Query duration
- Error count

### LLM Metrics
- Call count
- Call duration
- Token usage (prompt, completion, total)
- Error count

### File Processing Metrics
- Files processed
- Processing duration
- Bytes processed
- Lines processed
- Error count

## Integration Example

```python
from architectai.monitoring import (
    TelemetryCollector,
    MetricsRegistry,
    AgentMetricsCollector,
)

class MyAgent:
    def __init__(self):
        self.telemetry = TelemetryCollector()
        self.metrics = MetricsRegistry()
        self.agent_metrics = AgentMetricsCollector(self.metrics)
    
    def execute(self, task):
        # Track execution
        span_id = self.agent_metrics.start_execution(
            agent_name="my_agent",
            session_id="session_123"
        )
        
        try:
            # Do work
            result = self.process_task(task)
            
            # Record success
            self.agent_metrics.end_execution(
                span_id,
                success=True,
                tokens_used=result.tokens
            )
            
        except Exception as e:
            # Record failure
            self.agent_metrics.end_execution(
                span_id,
                success=False,
                error_message=str(e)
            )
            raise
```

## Configuration

The telemetry system uses sensible defaults:
- Buffer size: 100 events
- Flush interval: 10 seconds
- System metrics collection: Every 60 seconds
- Log rotation: Daily

To customize, pass parameters to `TelemetryCollector`:

```python
collector = TelemetryCollector(
    db_path="/custom/path/telemetry.db",
    log_dir="/custom/path/logs",
    enable_console=True,
    system_metrics_interval=30,
)
```

## Performance Considerations

- Events are buffered and flushed asynchronously
- SQLite writes are batched for efficiency
- System metrics collection runs in a background thread
- Minimal overhead on agent execution
- Log files rotate daily to prevent unbounded growth
