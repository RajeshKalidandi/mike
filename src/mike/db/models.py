import sqlite3
import uuid
from datetime import datetime
from typing import Optional, Dict, List, Any


class Database:
    """SQLite database for storing session and file metadata."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        """Initialize database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    source_path TEXT NOT NULL,
                    session_type TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    content_hash TEXT
                )
            """)

            # Files table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    absolute_path TEXT NOT NULL,
                    language TEXT,
                    size_bytes INTEGER,
                    line_count INTEGER,
                    content_hash TEXT,
                    parsed_at TIMESTAMP,
                    ast_available BOOLEAN DEFAULT 0,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)

            # Code hashes table for deduplication
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS code_hashes (
                    hash TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    file_count INTEGER,
                    total_lines INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)

            # Graph edges for dependency tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS graph_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    target_file TEXT NOT NULL,
                    edge_type TEXT NOT NULL,  -- 'import', 'call', 'inheritance', etc.
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                    UNIQUE(session_id, source_file, target_file, edge_type)
                )
            """)

            # Architecture scores table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS architecture_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    overall_score REAL NOT NULL,
                    coupling_score REAL NOT NULL,
                    cohesion_score REAL NOT NULL,
                    circular_deps_score REAL NOT NULL,
                    complexity_score REAL NOT NULL,
                    test_coverage_score REAL,
                    layer_violations_score REAL NOT NULL,
                    unused_exports_score REAL NOT NULL,
                    total_files INTEGER,
                    total_functions INTEGER,
                    avg_complexity REAL,
                    circular_dependencies_count INTEGER,
                    layer_violations_count INTEGER,
                    unused_exports_count INTEGER,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_arch_scores_session
                    ON architecture_scores(session_id, timestamp)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_arch_scores_timestamp
                    ON architecture_scores(timestamp)
            """)

            # Score components table for detailed breakdown
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS score_components (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    score_id INTEGER NOT NULL,
                    component_type TEXT NOT NULL,
                    component_path TEXT NOT NULL,
                    dimension TEXT NOT NULL,
                    score REAL NOT NULL,
                    raw_value REAL,
                    threshold REAL,
                    FOREIGN KEY (score_id) REFERENCES architecture_scores(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_score_components
                    ON score_components(score_id, dimension, component_path)
            """)

            # Security findings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS security_findings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    line_start INTEGER NOT NULL,
                    line_end INTEGER NOT NULL,
                    issue_type TEXT NOT NULL,
                    category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    cvss_score REAL,
                    risk_score REAL NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    remediation TEXT NOT NULL,
                    code_snippet TEXT,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    rule_id TEXT,
                    false_positive BOOLEAN DEFAULT 0,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_security_session
                    ON security_findings(session_id, severity)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_security_type
                    ON security_findings(issue_type, category)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_security_file
                    ON security_findings(file_path)
            """)

            # Git metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS git_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    total_commits INTEGER DEFAULT 0,
                    total_changes INTEGER DEFAULT 0,
                    lines_added_total INTEGER DEFAULT 0,
                    lines_deleted_total INTEGER DEFAULT 0,
                    first_commit_date TIMESTAMP,
                    last_commit_date TIMESTAMP,
                    days_since_last_change INTEGER,
                    bug_fix_count INTEGER DEFAULT 0,
                    unique_authors INTEGER DEFAULT 0,
                    churn_rate REAL DEFAULT 0.0,
                    hotspot_score REAL DEFAULT 0.0,
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_git_metrics_session
                    ON git_metrics(session_id, file_path)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_git_metrics_hotspot
                    ON git_metrics(session_id, hotspot_score)
            """)

            # Patches table for patch applications
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patches (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    suggestion_id TEXT,
                    diff_content TEXT,
                    files_affected TEXT,
                    status TEXT DEFAULT 'pending',
                    source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    applied_at TIMESTAMP,
                    rolled_back_at TIMESTAMP,
                    backup_paths TEXT,
                    errors TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_patches_session
                    ON patches(session_id, status)
            """)

            conn.commit()

    def create_session(
        self, source_path: str, session_type: str, content_hash: Optional[str] = None
    ) -> str:
        """Create a new session and return its ID."""
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sessions (id, source_path, session_type, status, created_at, updated_at, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    source_path,
                    session_type,
                    "active",
                    now,
                    now,
                    content_hash,
                ),
            )
            conn.commit()

        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None

    def insert_file(
        self,
        session_id: str,
        relative_path: str,
        absolute_path: str,
        language: str,
        size_bytes: int,
        line_count: int,
        content_hash: str,
    ) -> int:
        """Insert a file record and return its ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO files (session_id, relative_path, absolute_path, language, size_bytes, line_count, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    relative_path,
                    absolute_path,
                    language,
                    size_bytes,
                    line_count,
                    content_hash,
                ),
            )
            conn.commit()
            file_id = cursor.lastrowid
            if file_id is None:
                raise RuntimeError("Failed to get lastrowid after insert")
            return file_id

    def get_files_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all files for a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files WHERE session_id = ?", (session_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def update_file_parsed(self, file_id: int, ast_available: bool = True) -> None:
        """Update file parsing status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE files
                SET parsed_at = ?, ast_available = ?
                WHERE id = ?
                """,
                (datetime.now().isoformat(), ast_available, file_id),
            )
            conn.commit()

    def check_content_hash_exists(self, content_hash: str) -> Optional[str]:
        """Check if a content hash exists and return session_id if found."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT session_id FROM code_hashes WHERE hash = ?", (content_hash,)
            )
            row = cursor.fetchone()

            if row:
                return row["session_id"]
            return None


class Session:
    """Represents a session."""

    pass


class FileRecord:
    """Represents a file record."""

    pass
