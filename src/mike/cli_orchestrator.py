"""Simple orchestrator wrapper for CLI integration.

Provides a simplified interface to the existing orchestrator module
for CLI command use.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Generator
import sqlite3
import os

from mike.db.models import Database


@dataclass
class TaskProgress:
    """Represents progress of a task."""

    task_id: str
    task_name: str
    status: str = "pending"  # pending, running, completed, failed
    progress: float = 0.0
    message: str = ""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    result: Any = None
    error: Optional[str] = None


@dataclass
class SessionContext:
    """Context for a session."""

    session_id: str
    source_path: str
    session_type: str
    status: str
    created_at: str
    updated_at: str
    content_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Orchestrator:
    """Simplified orchestrator for CLI use."""

    def __init__(self, db_path: str, verbose: bool = False):
        self.db_path = db_path
        self.verbose = verbose
        self._db: Optional[sqlite3.Connection] = None

    def _get_db(self) -> sqlite3.Connection:
        """Get database connection."""
        if self._db is None:
            self._db = sqlite3.connect(self.db_path)
            self._db.row_factory = sqlite3.Row
            # Initialize database schema
            db = Database(self.db_path)
            db.init()
        return self._db

    def get_session(self, session_id: str) -> Optional[SessionContext]:
        """Get session by ID."""
        db = self._get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        return SessionContext(
            session_id=row["id"],
            source_path=row["source_path"],
            session_type=row["session_type"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            content_hash=row["content_hash"] if "content_hash" in row.keys() else None,
        )

    def list_sessions(self) -> List[SessionContext]:
        """List all sessions."""
        db = self._get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM sessions ORDER BY created_at DESC")
        rows = cursor.fetchall()

        return [
            SessionContext(
                session_id=row["id"],
                source_path=row["source_path"],
                session_type=row["session_type"],
                status=row["status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                content_hash=row["content_hash"]
                if "content_hash" in row.keys()
                else None,
            )
            for row in rows
        ]

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all associated data."""
        db = self._get_db()
        cursor = db.cursor()

        cursor.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
        if cursor.fetchone() is None:
            return False

        cursor.execute("DELETE FROM files WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

        db.commit()
        return True

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session."""
        db = self._get_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT COUNT(*) as count FROM files WHERE session_id = ?", (session_id,)
        )
        file_count = cursor.fetchone()["count"]

        cursor.execute(
            "SELECT COUNT(*) as count FROM files WHERE session_id = ? AND ast_available = 1",
            (session_id,),
        )
        parsed_count = cursor.fetchone()["count"]

        cursor.execute(
            "SELECT COALESCE(SUM(line_count), 0) as total FROM files WHERE session_id = ?",
            (session_id,),
        )
        total_lines = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT language, COUNT(*) as count 
            FROM files 
            WHERE session_id = ? AND language IS NOT NULL
            GROUP BY language
            ORDER BY count DESC
            """,
            (session_id,),
        )
        languages = {row["language"]: row["count"] for row in cursor.fetchall()}

        return {
            "file_count": file_count,
            "parsed_count": parsed_count,
            "total_lines": total_lines,
            "languages": languages,
        }

    def generate_documentation(
        self,
        session_id: str,
        output_dir: Optional[str] = None,
        doc_types: Optional[List[str]] = None,
    ) -> Generator[TaskProgress, None, Dict[str, Any]]:
        """Generate documentation for a session."""
        task_id = f"docs_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        yield TaskProgress(
            task_id=task_id,
            task_name="Documentation Generation",
            status="running",
            progress=0.0,
            message="Initializing documentation agent...",
            start_time=datetime.now().isoformat(),
        )

        session = self.get_session(session_id)
        if session is None:
            yield TaskProgress(
                task_id=task_id,
                task_name="Documentation Generation",
                status="failed",
                progress=0.0,
                message="Session not found",
                error=f"Session {session_id} not found",
            )
            return {"error": f"Session {session_id} not found"}

        yield TaskProgress(
            task_id=task_id,
            task_name="Documentation Generation",
            status="running",
            progress=0.1,
            message="Loading codebase data...",
        )

        db = self._get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM files WHERE session_id = ?", (session_id,))
        files = [dict(row) for row in cursor.fetchall()]

        yield TaskProgress(
            task_id=task_id,
            task_name="Documentation Generation",
            status="running",
            progress=0.3,
            message=f"Analyzing {len(files)} files...",
        )

        if output_dir is None:
            output_dir = os.path.join(os.getcwd(), f"docs_{session_id[:8]}")
        os.makedirs(output_dir, exist_ok=True)

        yield TaskProgress(
            task_id=task_id,
            task_name="Documentation Generation",
            status="running",
            progress=0.5,
            message="Generating README.md...",
        )

        readme_path = os.path.join(output_dir, "README.md")
        with open(readme_path, "w") as f:
            f.write(f"""# Project Documentation

**Source:** {session.source_path}
**Session ID:** {session_id}
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Overview

This project contains {len(files)} files.

## File Structure

""")
            for file_info in sorted(files, key=lambda x: x["relative_path"]):
                lang = file_info.get("language", "unknown")
                lines = file_info.get("line_count", 0)
                f.write(f"- `{file_info['relative_path']}` ({lang}, {lines} lines)\n")

        yield TaskProgress(
            task_id=task_id,
            task_name="Documentation Generation",
            status="running",
            progress=0.8,
            message="Generating ARCHITECTURE.md...",
        )

        arch_path = os.path.join(output_dir, "ARCHITECTURE.md")
        with open(arch_path, "w") as f:
            f.write(f"""# Architecture Overview

**Source:** {session.source_path}
**Session ID:** {session_id}
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Components

This codebase consists of the following components:

""")
            by_lang = {}
            for file_info in files:
                lang = file_info.get("language", "unknown")
                if lang not in by_lang:
                    by_lang[lang] = []
                by_lang[lang].append(file_info)

            for lang, lang_files in sorted(by_lang.items()):
                total_lines = sum(f.get("line_count", 0) for f in lang_files)
                f.write(
                    f"\n### {lang.title()} ({len(lang_files)} files, {total_lines} lines)\n\n"
                )
                for file_info in sorted(lang_files, key=lambda x: x["relative_path"])[
                    :10
                ]:
                    f.write(f"- `{file_info['relative_path']}`\n")
                if len(lang_files) > 10:
                    f.write(f"- ... and {len(lang_files) - 10} more\n")

        yield TaskProgress(
            task_id=task_id,
            task_name="Documentation Generation",
            status="completed",
            progress=1.0,
            message=f"Documentation generated in {output_dir}",
            end_time=datetime.now().isoformat(),
            result={
                "output_dir": output_dir,
                "files_generated": [readme_path, arch_path],
            },
        )

        return {
            "output_dir": output_dir,
            "files_generated": ["README.md", "ARCHITECTURE.md"],
            "session_id": session_id,
        }

    def ask_question(
        self,
        session_id: str,
        question: str,
    ) -> Generator[TaskProgress, None, Dict[str, Any]]:
        """Ask a question about the codebase."""
        task_id = f"ask_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        yield TaskProgress(
            task_id=task_id,
            task_name="Q&A",
            status="running",
            progress=0.0,
            message="Analyzing question...",
            start_time=datetime.now().isoformat(),
        )

        session = self.get_session(session_id)
        if session is None:
            yield TaskProgress(
                task_id=task_id,
                task_name="Q&A",
                status="failed",
                progress=0.0,
                message="Session not found",
                error=f"Session {session_id} not found",
            )
            return {"error": f"Session {session_id} not found"}

        yield TaskProgress(
            task_id=task_id,
            task_name="Q&A",
            status="running",
            progress=0.3,
            message="Searching codebase...",
        )

        db = self._get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM files WHERE session_id = ?", (session_id,))
        files = [dict(row) for row in cursor.fetchall()]

        yield TaskProgress(
            task_id=task_id,
            task_name="Q&A",
            status="running",
            progress=0.6,
            message="Generating answer...",
        )

        question_lower = question.lower()
        relevant_files = []

        for file_info in files:
            path_lower = file_info["relative_path"].lower()
            if any(keyword in path_lower for keyword in question_lower.split()):
                relevant_files.append(file_info)

        answer = f"Based on the codebase analysis:\n\n"

        if relevant_files:
            answer += f"Found {len(relevant_files)} potentially relevant files:\n\n"
            for file_info in relevant_files[:10]:
                answer += f"- `{file_info['relative_path']}`\n"
        else:
            answer += f"The codebase contains {len(files)} files.\n\n"
            answer += "Could not find specific matches. Try a more specific query.\n"

        yield TaskProgress(
            task_id=task_id,
            task_name="Q&A",
            status="completed",
            progress=1.0,
            message="Answer generated",
            end_time=datetime.now().isoformat(),
            result={"answer": answer},
        )

        return {
            "question": question,
            "answer": answer,
            "relevant_files": [f["relative_path"] for f in relevant_files[:10]],
            "session_id": session_id,
        }

    def analyze_refactoring(
        self,
        session_id: str,
        focus_areas: Optional[List[str]] = None,
    ) -> Generator[TaskProgress, None, Dict[str, Any]]:
        """Analyze code for refactoring opportunities."""
        task_id = f"refactor_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        yield TaskProgress(
            task_id=task_id,
            task_name="Refactoring Analysis",
            status="running",
            progress=0.0,
            message="Initializing refactoring agent...",
            start_time=datetime.now().isoformat(),
        )

        session = self.get_session(session_id)
        if session is None:
            yield TaskProgress(
                task_id=task_id,
                task_name="Refactoring Analysis",
                status="failed",
                progress=0.0,
                message="Session not found",
                error=f"Session {session_id} not found",
            )
            return {"error": f"Session {session_id} not found"}

        yield TaskProgress(
            task_id=task_id,
            task_name="Refactoring Analysis",
            status="running",
            progress=0.3,
            message="Analyzing codebase structure...",
        )

        db = self._get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM files WHERE session_id = ?", (session_id,))
        files = [dict(row) for row in cursor.fetchall()]

        yield TaskProgress(
            task_id=task_id,
            task_name="Refactoring Analysis",
            status="running",
            progress=0.6,
            message="Detecting code smells...",
        )

        suggestions = []

        large_files = [f for f in files if f.get("line_count", 0) > 500]
        if large_files:
            suggestions.append(
                {
                    "type": "large_files",
                    "description": f"Found {len(large_files)} files with more than 500 lines",
                    "files": [f["relative_path"] for f in large_files[:5]],
                    "recommendation": "Consider splitting large files into smaller modules",
                }
            )

        unknown_lang = [
            f for f in files if not f.get("language") or f["language"] == "unknown"
        ]
        if unknown_lang:
            suggestions.append(
                {
                    "type": "unknown_language",
                    "description": f"Found {len(unknown_lang)} files with unknown language",
                    "count": len(unknown_lang),
                    "recommendation": "Review these files for proper extension or configuration",
                }
            )

        languages = set(f.get("language") for f in files if f.get("language"))
        if len(languages) > 5:
            suggestions.append(
                {
                    "type": "language_diversity",
                    "description": f"Codebase uses {len(languages)} different languages",
                    "languages": list(languages),
                    "recommendation": "Consider standardizing tech stack for maintainability",
                }
            )

        yield TaskProgress(
            task_id=task_id,
            task_name="Refactoring Analysis",
            status="completed",
            progress=1.0,
            message=f"Analysis complete. Found {len(suggestions)} suggestions.",
            end_time=datetime.now().isoformat(),
            result={"suggestions": suggestions},
        )

        return {
            "suggestions": suggestions,
            "files_analyzed": len(files),
            "session_id": session_id,
        }

    def rebuild_project(
        self,
        template_session_id: str,
        output_dir: str,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Generator[TaskProgress, None, Dict[str, Any]]:
        """Scaffold a new project based on a template session."""
        task_id = (
            f"rebuild_{template_session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        yield TaskProgress(
            task_id=task_id,
            task_name="Project Rebuild",
            status="running",
            progress=0.0,
            message="Initializing rebuilder agent...",
            start_time=datetime.now().isoformat(),
        )

        session = self.get_session(template_session_id)
        if session is None:
            yield TaskProgress(
                task_id=task_id,
                task_name="Project Rebuild",
                status="failed",
                progress=0.0,
                message="Session not found",
                error=f"Session {template_session_id} not found",
            )
            return {"error": f"Session {template_session_id} not found"}

        yield TaskProgress(
            task_id=task_id,
            task_name="Project Rebuild",
            status="running",
            progress=0.2,
            message="Analyzing template structure...",
        )

        db = self._get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT * FROM files WHERE session_id = ?", (template_session_id,)
        )
        files = [dict(row) for row in cursor.fetchall()]

        os.makedirs(output_dir, exist_ok=True)

        yield TaskProgress(
            task_id=task_id,
            task_name="Project Rebuild",
            status="running",
            progress=0.5,
            message="Scaffolding project structure...",
        )

        dirs_created = set()
        for file_info in files:
            rel_path = file_info["relative_path"]
            dir_path = os.path.dirname(rel_path)
            if dir_path and dir_path not in dirs_created:
                full_dir = os.path.join(output_dir, dir_path)
                os.makedirs(full_dir, exist_ok=True)
                dirs_created.add(dir_path)

        yield TaskProgress(
            task_id=task_id,
            task_name="Project Rebuild",
            status="running",
            progress=0.7,
            message="Creating placeholder files...",
        )

        files_created = []
        for file_info in files[:20]:
            rel_path = file_info["relative_path"]
            full_path = os.path.join(output_dir, rel_path)

            lang = file_info.get("language", "unknown")
            if lang == "python":
                content = f'"""{os.path.basename(rel_path)}"""\n\n# Auto-generated from template\n\n'
            elif lang in ["javascript", "typescript"]:
                content = f"// {os.path.basename(rel_path)}\n// Auto-generated from template\n\n"
            else:
                content = f"# {os.path.basename(rel_path)}\n# Auto-generated from template\n\n"

            with open(full_path, "w") as f:
                f.write(content)
            files_created.append(rel_path)

        yield TaskProgress(
            task_id=task_id,
            task_name="Project Rebuild",
            status="running",
            progress=0.9,
            message="Creating project configuration...",
        )

        readme_path = os.path.join(output_dir, "README.md")
        with open(readme_path, "w") as f:
            f.write(f"""# New Project

Scaffolded from: {session.source_path}
Template Session: {template_session_id}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Constraints Applied

""")
            if constraints:
                for key, value in constraints.items():
                    f.write(f"- **{key}:** {value}\n")
            else:
                f.write("No specific constraints applied.\n")

            f.write(f"""

## Structure

{len(files_created)} placeholder files created.

## Next Steps

1. Review the scaffolded structure
2. Implement your business logic
3. Add tests
4. Update documentation
""")

        yield TaskProgress(
            task_id=task_id,
            task_name="Project Rebuild",
            status="completed",
            progress=1.0,
            message=f"Project scaffolded in {output_dir}",
            end_time=datetime.now().isoformat(),
            result={"output_dir": output_dir, "files_created": len(files_created)},
        )

        return {
            "output_dir": output_dir,
            "files_created": files_created,
            "template_session_id": template_session_id,
        }

    def get_system_status(self) -> Dict[str, Any]:
        """Get system status information."""
        status = {
            "version": "0.1.0",
            "database_path": self.db_path,
            "database_exists": os.path.exists(self.db_path),
            "available_models": [
                {
                    "name": "local-llm",
                    "description": "Local LLM via Ollama (not yet configured)",
                    "status": "not_configured",
                }
            ],
            "agents": {
                "docs": {
                    "status": "available",
                    "description": "Documentation generation",
                },
                "qa": {"status": "available", "description": "Question answering"},
                "refactor": {
                    "status": "available",
                    "description": "Refactoring analysis",
                },
                "rebuild": {
                    "status": "available",
                    "description": "Project scaffolding",
                },
            },
        }

        if status["database_exists"]:
            db = self._get_db()
            cursor = db.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM sessions")
            status["session_count"] = cursor.fetchone()["count"]
        else:
            status["session_count"] = 0

        return status
