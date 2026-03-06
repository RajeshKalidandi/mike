"""Reporting system for Mike monitoring data."""

import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, TextIO

from mike.monitoring.telemetry import EventType, TelemetryCollector
from mike.monitoring.metrics import MetricsRegistry


class BaseReporter(ABC):
    """Base class for all reporters."""

    def __init__(self, collector: TelemetryCollector, registry: MetricsRegistry):
        self.collector = collector
        self.registry = registry

    @abstractmethod
    def generate_report(
        self,
        session_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> str:
        """Generate a report."""
        pass

    @abstractmethod
    def generate_summary(self) -> str:
        """Generate a summary report."""
        pass


class ConsoleReporter(BaseReporter):
    """Reporter that outputs to console."""

    def generate_report(
        self,
        session_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> str:
        """Generate a console-formatted report."""
        lines = []
        lines.append("=" * 70)
        lines.append("ARCHITECTAI TELEMETRY REPORT")
        lines.append("=" * 70)
        lines.append("")

        if session_id:
            lines.append(f"Session: {session_id}")
            stats = self.collector.get_session_stats(session_id)
            lines.append(self._format_session_stats(stats))
        else:
            stats = self.collector.get_system_stats(start_time, end_time)
            lines.append(self._format_system_stats(stats))

        lines.append("")
        lines.append("=" * 70)
        lines.append("METRICS")
        lines.append("=" * 70)
        lines.append(self._format_metrics())

        return "\n".join(lines)

    def _format_session_stats(self, stats: Dict[str, Any]) -> str:
        """Format session statistics."""
        lines = []
        lines.append(f"  Total Events: {stats.get('total_events', 0)}")
        lines.append(f"  Agent Runs: {stats.get('agent_runs', 0)}")
        lines.append(f"  Successful: {stats.get('agent_success', 0)}")
        lines.append(f"  Failed: {stats.get('agent_failures', 0)}")
        lines.append(f"  Success Rate: {stats.get('success_rate', 0):.1f}%")
        lines.append(f"  LLM Calls: {stats.get('llm_calls', 0)}")
        lines.append(f"  DB Queries: {stats.get('db_queries', 0)}")
        lines.append(f"  Files Processed: {stats.get('files_processed', 0)}")
        return "\n".join(lines)

    def _format_system_stats(self, stats: Dict[str, Any]) -> str:
        """Format system statistics."""
        lines = []
        lines.append(f"  Total Sessions: {stats.get('total_sessions', 0)}")
        lines.append(f"  Total Events: {stats.get('total_events', 0)}")
        lines.append(f"  Agent Runs: {stats.get('total_agent_runs', 0)}")
        lines.append(f"  Successful: {stats.get('successful_agent_runs', 0)}")
        lines.append(
            f"  Overall Success Rate: {stats.get('overall_success_rate', 0):.1f}%"
        )
        lines.append(f"  LLM Calls: {stats.get('total_llm_calls', 0)}")
        return "\n".join(lines)

    def _format_metrics(self) -> str:
        """Format metrics."""
        lines = []
        metrics = self.registry.to_dict()

        for name, metric in metrics.items():
            metric_type = metric.get("type", "unknown")
            lines.append(f"  {name} ({metric_type}):")

            if metric_type in ["counter", "gauge"]:
                lines.append(f"    Value: {metric.get('value', 0)}")
            elif metric_type == "histogram":
                stats = metric.get("statistics", {})
                lines.append(f"    Count: {stats.get('count', 0)}")
                lines.append(f"    Average: {stats.get('avg', 0):.3f}")
                lines.append(f"    P50: {stats.get('p50', 0):.3f}")
                lines.append(f"    P95: {stats.get('p95', 0):.3f}")

        return "\n".join(lines)

    def generate_summary(self) -> str:
        """Generate a brief summary."""
        stats = self.collector.get_system_stats()
        lines = [
            f"Sessions: {stats.get('total_sessions', 0)}",
            f"Agent Runs: {stats.get('total_agent_runs', 0)} "
            f"({stats.get('successful_agent_runs', 0)} success, "
            f"{stats.get('total_agent_runs', 0) - stats.get('successful_agent_runs', 0)} failed)",
            f"Success Rate: {stats.get('overall_success_rate', 0):.1f}%",
            f"LLM Calls: {stats.get('total_llm_calls', 0)}",
        ]
        return " | ".join(lines)


class JsonReporter(BaseReporter):
    """Reporter that outputs JSON."""

    def generate_report(
        self,
        session_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> str:
        """Generate a JSON report."""
        report = {
            "generated_at": datetime.now().isoformat(),
            "session_id": session_id,
            "telemetry": {},
            "metrics": self.registry.to_dict(),
        }

        if session_id:
            report["telemetry"] = self.collector.get_session_stats(session_id)
            report["events"] = [
                e.to_dict()
                for e in self.collector.get_events(session_id=session_id, limit=1000)
            ]
        else:
            report["telemetry"] = self.collector.get_system_stats(start_time, end_time)

        return json.dumps(report, indent=2, default=str)

    def generate_summary(self) -> str:
        """Generate a JSON summary."""
        stats = self.collector.get_system_stats()
        return json.dumps(
            {
                "timestamp": datetime.now().isoformat(),
                "summary": stats,
                "metrics_count": len(self.registry.get_all_metrics()),
            },
            indent=2,
        )


class MarkdownReporter(BaseReporter):
    """Reporter that outputs Markdown."""

    def generate_report(
        self,
        session_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> str:
        """Generate a Markdown report."""
        lines = []
        lines.append("# Mike Telemetry Report")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        if session_id:
            lines.append(f"## Session: `{session_id}`")
            lines.append("")
            stats = self.collector.get_session_stats(session_id)
            lines.append(self._format_session_stats_markdown(stats))

            lines.append("## Recent Events")
            lines.append("")
            events = self.collector.get_events(session_id=session_id, limit=50)
            lines.append(self._format_events_markdown(events))
        else:
            lines.append("## System Statistics")
            lines.append("")
            stats = self.collector.get_system_stats(start_time, end_time)
            lines.append(self._format_system_stats_markdown(stats))

        lines.append("## Metrics")
        lines.append("")
        lines.append(self._format_metrics_markdown())

        return "\n".join(lines)

    def _format_session_stats_markdown(self, stats: Dict[str, Any]) -> str:
        """Format session stats as markdown."""
        return f"""| Metric | Value |
|--------|-------|
| Total Events | {stats.get("total_events", 0)} |
| Agent Runs | {stats.get("agent_runs", 0)} |
| Successful | {stats.get("agent_success", 0)} |
| Failed | {stats.get("agent_failures", 0)} |
| Success Rate | {stats.get("success_rate", 0):.1f}% |
| LLM Calls | {stats.get("llm_calls", 0)} |
| DB Queries | {stats.get("db_queries", 0)} |
| Files Processed | {stats.get("files_processed", 0)} |

"""

    def _format_system_stats_markdown(self, stats: Dict[str, Any]) -> str:
        """Format system stats as markdown."""
        return f"""| Metric | Value |
|--------|-------|
| Total Sessions | {stats.get("total_sessions", 0)} |
| Total Events | {stats.get("total_events", 0)} |
| Agent Runs | {stats.get("total_agent_runs", 0)} |
| Successful | {stats.get("successful_agent_runs", 0)} |
| Overall Success Rate | {stats.get("overall_success_rate", 0):.1f}% |
| LLM Calls | {stats.get("total_llm_calls", 0)} |

"""

    def _format_events_markdown(self, events: List[Any]) -> str:
        """Format events as markdown."""
        if not events:
            return "_No events found._\n"

        lines = ["| Time | Type | Agent | Duration (ms) | Status |"]
        lines.append("|------|------|-------|---------------|--------|")

        for event in events[:20]:
            status = "✓" if event.success else "✗" if event.success is not None else "-"
            agent = event.agent_name or "-"
            duration = f"{event.duration_ms:.1f}" if event.duration_ms else "-"
            lines.append(
                f"| {event.timestamp.strftime('%H:%M:%S')} | {event.event_type.value} | {agent} | {duration} | {status} |"
            )

        return "\n".join(lines) + "\n"

    def _format_metrics_markdown(self) -> str:
        """Format metrics as markdown."""
        lines = []
        metrics = self.registry.to_dict()

        for name, metric in metrics.items():
            metric_type = metric.get("type", "unknown")
            lines.append(f"### {name}")
            lines.append("")
            lines.append(f"**Type:** {metric_type}")
            lines.append("")

            if metric_type in ["counter", "gauge"]:
                lines.append(f"- **Value:** {metric.get('value', 0)}")
            elif metric_type == "histogram":
                stats = metric.get("statistics", {})
                lines.append(f"- **Count:** {stats.get('count', 0)}")
                lines.append(f"- **Sum:** {stats.get('sum', 0):.3f}")
                lines.append(f"- **Average:** {stats.get('avg', 0):.3f}")
                lines.append(f"- **Min:** {stats.get('min', 0):.3f}")
                lines.append(f"- **Max:** {stats.get('max', 0):.3f}")
                lines.append(f"- **P50:** {stats.get('p50', 0):.3f}")
                lines.append(f"- **P95:** {stats.get('p95', 0):.3f}")
                lines.append(f"- **P99:** {stats.get('p99', 0):.3f}")
            lines.append("")

        return "\n".join(lines)

    def generate_summary(self) -> str:
        """Generate a brief markdown summary."""
        stats = self.collector.get_system_stats()
        return f"""## System Summary

- **Sessions:** {stats.get("total_sessions", 0)}
- **Agent Runs:** {stats.get("total_agent_runs", 0)}
- **Success Rate:** {stats.get("overall_success_rate", 0):.1f}%
- **LLM Calls:** {stats.get("total_llm_calls", 0)}
"""


class ReportGenerator:
    """Generate comprehensive reports with trend analysis."""

    def __init__(self, collector: TelemetryCollector, registry: MetricsRegistry):
        self.collector = collector
        self.registry = registry
        self.console = ConsoleReporter(collector, registry)
        self.json = JsonReporter(collector, registry)
        self.markdown = MarkdownReporter(collector, registry)

    def generate_trend_report(
        self,
        days: int = 7,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate trend analysis report."""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        daily_stats = []
        for i in range(days):
            day_start = start_time + timedelta(days=i)
            day_end = day_start + timedelta(days=1)

            stats = self.collector.get_system_stats(day_start, day_end)
            daily_stats.append(
                {
                    "date": day_start.strftime("%Y-%m-%d"),
                    "stats": stats,
                }
            )

        return {
            "period": f"{days} days",
            "start_date": start_time.isoformat(),
            "end_date": end_time.isoformat(),
            "daily_breakdown": daily_stats,
            "totals": self.collector.get_system_stats(start_time, end_time),
        }

    def generate_agent_performance_report(
        self,
        agent_name: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Generate agent performance report."""
        events = self.collector.get_events(
            event_type=EventType.AGENT_COMPLETE,
            agent_name=agent_name,
            limit=limit,
        )

        agent_stats: Dict[str, Dict[str, Any]] = {}
        for event in events:
            name = event.agent_name or "unknown"
            if name not in agent_stats:
                agent_stats[name] = {
                    "runs": 0,
                    "success": 0,
                    "failures": 0,
                    "total_duration_ms": 0,
                    "total_tokens": 0,
                }

            stats = agent_stats[name]
            stats["runs"] += 1
            if event.success:
                stats["success"] += 1
            else:
                stats["failures"] += 1

            if event.duration_ms:
                stats["total_duration_ms"] += event.duration_ms

            tokens = event.metadata.get("tokens_used", 0)
            stats["total_tokens"] += tokens

        for name, stats in agent_stats.items():
            if stats["runs"] > 0:
                stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["runs"]
                stats["success_rate"] = (stats["success"] / stats["runs"]) * 100

        return {
            "agent_count": len(agent_stats),
            "agents": agent_stats,
        }

    def export_to_file(
        self,
        filename: str,
        format_type: str = "markdown",
        session_id: Optional[str] = None,
    ) -> None:
        """Export report to file."""
        if format_type == "json":
            content = self.json.generate_report(session_id=session_id)
        elif format_type == "markdown":
            content = self.markdown.generate_report(session_id=session_id)
        else:
            content = self.console.generate_report(session_id=session_id)

        with open(filename, "w") as f:
            f.write(content)
