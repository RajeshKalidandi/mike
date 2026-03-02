"""Telemetry collection system for ArchitectAI."""

import json
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import psutil


class EventType(Enum):
    """Types of telemetry events."""

    AGENT_START = "agent_start"
    AGENT_COMPLETE = "agent_complete"
    AGENT_ERROR = "agent_error"
    LLM_CALL_START = "llm_call_start"
    LLM_CALL_COMPLETE = "llm_call_complete"
    LLM_CALL_ERROR = "llm_call_error"
    DB_QUERY_START = "db_query_start"
    DB_QUERY_COMPLETE = "db_query_complete"
    FILE_PROCESS_START = "file_process_start"
    FILE_PROCESS_COMPLETE = "file_process_complete"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    SYSTEM_METRICS = "system_metrics"


class EventLevel(Enum):
    """Event severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class TelemetryEvent:
    """A single telemetry event."""

    event_type: EventType
    timestamp: datetime
    session_id: Optional[str] = None
    agent_name: Optional[str] = None
    duration_ms: Optional[float] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    level: EventLevel = EventLevel.INFO
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_event_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        result = asdict(self)
        result["event_type"] = self.event_type.value
        result["level"] = self.level.value
        result["timestamp"] = self.timestamp.isoformat()
        return result

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class PerformanceSnapshot:
    """Snapshot of system performance metrics."""

    def __init__(self):
        self.timestamp = datetime.now()
        self.cpu_percent = psutil.cpu_percent(interval=0.1)
        self.memory = psutil.virtual_memory()
        self.disk = psutil.disk_usage("/")
        self.process = psutil.Process()
        self.process_memory_mb = self.process.memory_info().rss / 1024 / 1024
        self.process_cpu_percent = self.process.cpu_percent(interval=0.1)

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory.percent,
            "memory_used_mb": self.memory.used / 1024 / 1024,
            "memory_available_mb": self.memory.available / 1024 / 1024,
            "disk_percent": self.disk.percent,
            "disk_used_gb": self.disk.used / 1024 / 1024 / 1024,
            "process_memory_mb": self.process_memory_mb,
            "process_cpu_percent": self.process_cpu_percent,
        }


class TelemetryCollector:
    """Main telemetry collection system."""

    _instance: Optional["TelemetryCollector"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        db_path: Optional[str] = None,
        log_dir: Optional[str] = None,
        enable_console: bool = False,
        system_metrics_interval: int = 60,
    ):
        if self._initialized:
            return

        self._initialized = True
        self.db_path = db_path or self._get_default_db_path()
        self.log_dir = Path(log_dir or self._get_default_log_dir())
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.enable_console = enable_console
        self.system_metrics_interval = system_metrics_interval

        self._event_buffer: List[TelemetryEvent] = []
        self._buffer_lock = threading.Lock()
        self._buffer_size = 100
        self._flush_interval = 10

        self._callbacks: List[Callable[[TelemetryEvent], None]] = []
        self._callbacks_lock = threading.Lock()

        self._current_session_id: Optional[str] = None
        self._active_spans: Dict[str, TelemetryEvent] = {}
        self._spans_lock = threading.Lock()

        self._system_metrics_thread: Optional[threading.Thread] = None
        self._stop_system_metrics = threading.Event()

        self._init_db()
        self._start_background_tasks()

    def _get_default_db_path(self) -> str:
        """Get default database path."""
        home = Path.home()
        db_dir = home / ".architectai"
        db_dir.mkdir(parents=True, exist_ok=True)
        return str(db_dir / "telemetry.db")

    def _get_default_log_dir(self) -> str:
        """Get default log directory."""
        home = Path.home()
        return str(home / ".architectai" / "logs")

    def _init_db(self) -> None:
        """Initialize SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                agent_name TEXT,
                duration_ms REAL,
                success INTEGER,
                error_message TEXT,
                metadata TEXT,
                level TEXT NOT NULL,
                parent_event_id TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_session 
            ON telemetry_events(session_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_type 
            ON telemetry_events(event_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_timestamp 
            ON telemetry_events(timestamp)
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_sessions (
                session_id TEXT PRIMARY KEY,
                start_time TEXT NOT NULL,
                end_time TEXT,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                cpu_percent REAL,
                memory_percent REAL,
                memory_used_mb REAL,
                memory_available_mb REAL,
                process_memory_mb REAL,
                process_cpu_percent REAL
            )
        """)

        conn.commit()
        conn.close()

    def _start_background_tasks(self) -> None:
        """Start background tasks."""
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

        if self.system_metrics_interval > 0:
            self._system_metrics_thread = threading.Thread(
                target=self._system_metrics_loop, daemon=True
            )
            self._system_metrics_thread.start()

    def _flush_loop(self) -> None:
        """Background loop to flush events to database."""
        while True:
            time.sleep(self._flush_interval)
            self._flush_events()

    def _system_metrics_loop(self) -> None:
        """Background loop to collect system metrics."""
        while not self._stop_system_metrics.is_set():
            try:
                self._record_system_metrics()
            except Exception:
                pass
            self._stop_system_metrics.wait(self.system_metrics_interval)

    def _record_system_metrics(self) -> None:
        """Record current system metrics."""
        snapshot = PerformanceSnapshot()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO performance_snapshots 
            (timestamp, session_id, cpu_percent, memory_percent, memory_used_mb, 
             memory_available_mb, process_memory_mb, process_cpu_percent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                snapshot.timestamp.isoformat(),
                self._current_session_id,
                snapshot.cpu_percent,
                snapshot.memory.percent,
                snapshot.memory.used / 1024 / 1024,
                snapshot.memory.available / 1024 / 1024,
                snapshot.process_memory_mb,
                snapshot.process_cpu_percent,
            ),
        )

        conn.commit()
        conn.close()

        event = TelemetryEvent(
            event_type=EventType.SYSTEM_METRICS,
            timestamp=snapshot.timestamp,
            session_id=self._current_session_id,
            metadata=snapshot.to_dict(),
            level=EventLevel.DEBUG,
        )
        self._buffer_event(event)

    def _buffer_event(self, event: TelemetryEvent) -> None:
        """Add event to buffer."""
        with self._buffer_lock:
            self._event_buffer.append(event)
            if len(self._event_buffer) >= self._buffer_size:
                self._flush_events()

    def _flush_events(self) -> None:
        """Flush buffered events to database."""
        with self._buffer_lock:
            if not self._event_buffer:
                return
            events_to_flush = self._event_buffer[:]
            self._event_buffer.clear()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for event in events_to_flush:
            cursor.execute(
                """
                INSERT OR REPLACE INTO telemetry_events 
                (event_id, event_type, timestamp, session_id, agent_name, duration_ms,
                 success, error_message, metadata, level, parent_event_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    event.event_id,
                    event.event_type.value,
                    event.timestamp.isoformat(),
                    event.session_id,
                    event.agent_name,
                    event.duration_ms,
                    1 if event.success else 0 if event.success is not None else None,
                    event.error_message,
                    json.dumps(event.metadata),
                    event.level.value,
                    event.parent_event_id,
                ),
            )

        conn.commit()
        conn.close()

        self._write_to_log_file(events_to_flush)
        self._notify_callbacks(events_to_flush)

    def _write_to_log_file(self, events: List[TelemetryEvent]) -> None:
        """Write events to rotating log file."""
        log_file = self.log_dir / f"telemetry_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, "a") as f:
            for event in events:
                f.write(event.to_json() + "\n")

    def _notify_callbacks(self, events: List[TelemetryEvent]) -> None:
        """Notify registered callbacks."""
        with self._callbacks_lock:
            callbacks = self._callbacks[:]

        for event in events:
            for callback in callbacks:
                try:
                    callback(event)
                except Exception:
                    pass

            if self.enable_console:
                print(f"[TELEMETRY] {event.event_type.value}: {event.metadata}")

    def record_event(
        self,
        event_type: EventType,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        level: EventLevel = EventLevel.INFO,
        parent_event_id: Optional[str] = None,
    ) -> TelemetryEvent:
        """Record a telemetry event."""
        event = TelemetryEvent(
            event_type=event_type,
            timestamp=datetime.now(),
            session_id=self._current_session_id,
            agent_name=agent_name,
            metadata=metadata or {},
            level=level,
            parent_event_id=parent_event_id,
        )
        self._buffer_event(event)
        return event

    def start_span(
        self,
        event_type: EventType,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Start a timed span."""
        event = self.record_event(
            event_type=event_type,
            agent_name=agent_name,
            metadata=metadata or {},
        )

        with self._spans_lock:
            self._active_spans[event.event_id] = event

        return event.event_id

    def end_span(
        self,
        span_id: str,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata_updates: Optional[Dict[str, Any]] = None,
    ) -> Optional[TelemetryEvent]:
        """End a timed span."""
        with self._spans_lock:
            start_event = self._active_spans.pop(span_id, None)

        if start_event is None:
            return None

        duration_ms = (datetime.now() - start_event.timestamp).total_seconds() * 1000

        if metadata_updates:
            start_event.metadata.update(metadata_updates)

        complete_event = TelemetryEvent(
            event_type=EventType(f"{start_event.event_type.value}_complete"),
            timestamp=datetime.now(),
            session_id=start_event.session_id,
            agent_name=start_event.agent_name,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            metadata=start_event.metadata,
            level=EventLevel.ERROR if not success else EventLevel.INFO,
            parent_event_id=span_id,
        )

        self._buffer_event(complete_event)
        return complete_event

    def record_agent_start(
        self, agent_name: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Record agent execution start. Returns span ID."""
        return self.start_span(
            event_type=EventType.AGENT_START,
            agent_name=agent_name,
            metadata=metadata or {},
        )

    def record_agent_complete(
        self,
        span_id: str,
        success: bool = True,
        error_message: Optional[str] = None,
        tokens_used: Optional[int] = None,
        output_size: Optional[int] = None,
    ) -> Optional[TelemetryEvent]:
        """Record agent execution completion."""
        metadata = {}
        if tokens_used is not None:
            metadata["tokens_used"] = tokens_used
        if output_size is not None:
            metadata["output_size"] = output_size

        return self.end_span(span_id, success, error_message, metadata)

    def record_llm_call(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration_ms: float,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> TelemetryEvent:
        """Record LLM API call."""
        estimated_cost = self._estimate_cost(model, prompt_tokens, completion_tokens)

        return self.record_event(
            event_type=EventType.LLM_CALL_COMPLETE,
            metadata={
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "duration_ms": duration_ms,
                "estimated_cost_usd": estimated_cost,
            },
            level=EventLevel.ERROR if not success else EventLevel.INFO,
        )

    def _estimate_cost(
        self, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float:
        """Estimate cost for local models (always 0)."""
        return 0.0

    def record_db_query(
        self,
        query_type: str,
        duration_ms: float,
        rows_affected: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> TelemetryEvent:
        """Record database query."""
        metadata = {
            "query_type": query_type,
            "duration_ms": duration_ms,
        }
        if rows_affected is not None:
            metadata["rows_affected"] = rows_affected

        return self.record_event(
            event_type=EventType.DB_QUERY_COMPLETE,
            metadata=metadata,
            level=EventLevel.ERROR if not success else EventLevel.DEBUG,
        )

    def record_file_process(
        self,
        file_path: str,
        file_size: int,
        duration_ms: float,
        language: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> TelemetryEvent:
        """Record file processing."""
        return self.record_event(
            event_type=EventType.FILE_PROCESS_COMPLETE,
            metadata={
                "file_path": file_path,
                "file_size": file_size,
                "language": language,
                "duration_ms": duration_ms,
            },
            level=EventLevel.ERROR if not success else EventLevel.DEBUG,
        )

    def start_session(
        self, session_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Start a new session."""
        self._current_session_id = session_id

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO telemetry_sessions (session_id, start_time, metadata)
            VALUES (?, ?, ?)
        """,
            (
                session_id,
                datetime.now().isoformat(),
                json.dumps(metadata or {}),
            ),
        )

        conn.commit()
        conn.close()

        self.record_event(
            event_type=EventType.SESSION_START,
            metadata=metadata or {},
        )

    def end_session(self, metadata: Optional[Dict[str, Any]] = None) -> None:
        """End current session."""
        if self._current_session_id is None:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE telemetry_sessions 
            SET end_time = ?
            WHERE session_id = ?
        """,
            (datetime.now().isoformat(), self._current_session_id),
        )

        conn.commit()
        conn.close()

        self.record_event(
            event_type=EventType.SESSION_END,
            metadata=metadata or {},
        )

        self._current_session_id = None

    def register_callback(self, callback: Callable[[TelemetryEvent], None]) -> None:
        """Register a callback for telemetry events."""
        with self._callbacks_lock:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[TelemetryEvent], None]) -> None:
        """Unregister a callback."""
        with self._callbacks_lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def get_events(
        self,
        session_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        agent_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[TelemetryEvent]:
        """Query events from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM telemetry_events WHERE 1=1"
        params = []

        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)
        if agent_name:
            query += " AND agent_name = ?"
            params.append(agent_name)
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        events = []
        for row in rows:
            events.append(self._row_to_event(row))

        return events

    def _row_to_event(self, row: sqlite3.Row) -> TelemetryEvent:
        """Convert database row to TelemetryEvent."""
        return TelemetryEvent(
            event_id=row[0],
            event_type=EventType(row[1]),
            timestamp=datetime.fromisoformat(row[2]),
            session_id=row[3],
            agent_name=row[4],
            duration_ms=row[5],
            success=bool(row[6]) if row[6] is not None else None,
            error_message=row[7],
            metadata=json.loads(row[8]) if row[8] else {},
            level=EventLevel(row[9]),
            parent_event_id=row[10],
        )

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT 
                COUNT(*) as total_events,
                SUM(CASE WHEN event_type = 'agent_complete' THEN 1 ELSE 0 END) as agent_runs,
                SUM(CASE WHEN event_type = 'agent_complete' AND success = 1 THEN 1 ELSE 0 END) as agent_success,
                SUM(CASE WHEN event_type = 'agent_complete' AND success = 0 THEN 1 ELSE 0 END) as agent_failures,
                SUM(CASE WHEN event_type = 'llm_call_complete' THEN 1 ELSE 0 END) as llm_calls,
                SUM(CASE WHEN event_type = 'db_query_complete' THEN 1 ELSE 0 END) as db_queries,
                SUM(CASE WHEN event_type = 'file_process_complete' THEN 1 ELSE 0 END) as files_processed
            FROM telemetry_events
            WHERE session_id = ?
        """,
            (session_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row is None:
            return {}

        return {
            "total_events": row[0],
            "agent_runs": row[1] or 0,
            "agent_success": row[2] or 0,
            "agent_failures": row[3] or 0,
            "llm_calls": row[4] or 0,
            "db_queries": row[5] or 0,
            "files_processed": row[6] or 0,
            "success_rate": (row[2] / row[1] * 100) if row[1] else 0,
        }

    def get_system_stats(
        self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get system-wide statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = """
            SELECT 
                COUNT(DISTINCT session_id) as total_sessions,
                COUNT(*) as total_events,
                SUM(CASE WHEN event_type = 'agent_complete' THEN 1 ELSE 0 END) as agent_runs,
                SUM(CASE WHEN event_type = 'agent_complete' AND success = 1 THEN 1 ELSE 0 END) as agent_success,
                SUM(CASE WHEN event_type = 'llm_call_complete' THEN 1 ELSE 0 END) as llm_calls
            FROM telemetry_events
            WHERE 1=1
        """
        params = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return {}

        return {
            "total_sessions": row[0],
            "total_events": row[1] or 0,
            "total_agent_runs": row[2] or 0,
            "successful_agent_runs": row[3] or 0,
            "total_llm_calls": row[4] or 0,
            "overall_success_rate": (row[3] / row[2] * 100) if row[2] else 0,
        }

    def shutdown(self) -> None:
        """Shutdown telemetry collector."""
        self._flush_events()
        self._stop_system_metrics.set()
        if self._system_metrics_thread:
            self._system_metrics_thread.join(timeout=5)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
