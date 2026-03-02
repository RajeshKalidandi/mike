"""Public API interface for ArchitectAI.

This module provides the main entry point for using ArchitectAI programmatically.
It offers a high-level, user-friendly interface over the core orchestration engine.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Dict, Generator, List, Optional, Union

from architectai.config.settings import Settings
from architectai.config.loader import ConfigLoader
from architectai.db.models import Database
from architectai.scanner.scanner import FileScanner
from architectai.scanner.clone import clone_repository
from architectai.parser.parser import ASTParser
from architectai.orchestrator.state import (
    AgentType,
    ExecutionMode,
    ExecutionStatus,
)
from architectai.orchestrator.engine import AgentOrchestrator, Agent, AgentRegistry
from architectai.cli_orchestrator import Orchestrator, TaskProgress


logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Result of a codebase scan operation."""

    session_id: str
    files_scanned: int
    languages: Dict[str, int]
    source_path: str
    success: bool = True
    error: Optional[str] = None


@dataclass
class AnalysisResult:
    """Result of a codebase analysis operation."""

    session_id: str
    status: str
    files_analyzed: int
    dependencies_found: int
    success: bool = True
    error: Optional[str] = None


@dataclass
class DocsResult:
    """Result of documentation generation."""

    session_id: str
    output_dir: str
    files_generated: List[str]
    success: bool = True
    error: Optional[str] = None


@dataclass
class QAResult:
    """Result of a Q&A operation."""

    session_id: str
    question: str
    answer: str
    relevant_files: List[str]
    confidence: float
    success: bool = True
    error: Optional[str] = None


@dataclass
class RefactorResult:
    """Result of refactoring analysis."""

    session_id: str
    suggestions: List[Dict[str, Any]]
    files_analyzed: int
    success: bool = True
    error: Optional[str] = None


@dataclass
class RebuildResult:
    """Result of project rebuilding."""

    session_id: str
    output_dir: str
    files_created: List[str]
    success: bool = True
    error: Optional[str] = None


@dataclass
class SessionInfo:
    """Information about a session."""

    session_id: str
    source_path: str
    session_type: str
    status: str
    created_at: str
    updated_at: str
    file_count: int = 0
    parsed_count: int = 0
    total_lines: int = 0
    languages: Dict[str, int] = field(default_factory=dict)


ProgressCallback = Callable[[str, float, str], None]


class ArchitectAI:
    """Main entry point for ArchitectAI.

    This class provides a unified, high-level interface for all ArchitectAI
    functionality including scanning, analysis, documentation generation,
    Q&A, refactoring suggestions, and project rebuilding.

    Example:
        >>> from architectai import ArchitectAI
        >>> ai = ArchitectAI()
        >>>
        >>> # Scan a codebase
        >>> result = ai.scan_codebase("/path/to/project")
        >>> print(f"Session ID: {result.session_id}")
        >>>
        >>> # Generate documentation
        >>> docs = ai.generate_docs(result.session_id)
        >>> print(f"Docs generated in: {docs.output_dir}")
        >>>
        >>> # Ask questions
        >>> answer = ai.ask_question(
        ...     result.session_id,
        ...     "Where is authentication handled?"
        ... )
        >>> print(answer.answer)

    Attributes:
        settings: Configuration settings instance
        db: Database connection
        orchestrator: CLI orchestrator for task management
        engine: Agent orchestration engine
        _progress_callbacks: List of progress callback functions
    """

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        settings: Optional[Settings] = None,
        db_path: Optional[str] = None,
        verbose: bool = False,
    ):
        """Initialize ArchitectAI.

        Args:
            config_path: Path to configuration file (optional)
            settings: Settings instance (optional, overrides config_path)
            db_path: Path to database file (optional, overrides settings)
            verbose: Enable verbose logging
        """
        self._verbose = verbose
        self._progress_callbacks: List[ProgressCallback] = []

        # Setup logging
        if verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        # Load or create settings
        if settings:
            self.settings = settings
        elif config_path:
            loader = ConfigLoader()
            self.settings = loader.load(Path(config_path))
        else:
            self.settings = Settings.default()

        # Override database path if provided
        if db_path:
            self.settings.database.path = Path(db_path)

        # Ensure directories exist
        self.settings.ensure_directories()

        # Initialize database
        self.db = Database(str(self.settings.database.path))
        self.db.init()

        # Initialize orchestrators
        self.orchestrator = Orchestrator(
            db_path=str(self.settings.database.path), verbose=verbose
        )
        self.engine = AgentOrchestrator(log_dir=self.settings.paths.sessions_dir)

        logger.info(f"ArchitectAI initialized (db: {self.settings.database.path})")

    def add_progress_callback(self, callback: ProgressCallback) -> None:
        """Add a progress callback function.

        The callback will be called with (task_name, progress_percentage, message)
        during long-running operations.

        Args:
            callback: Function to call with progress updates
        """
        self._progress_callbacks.append(callback)

    def remove_progress_callback(self, callback: ProgressCallback) -> None:
        """Remove a progress callback function.

        Args:
            callback: Callback function to remove
        """
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)

    def _notify_progress(self, task_name: str, progress: float, message: str) -> None:
        """Notify all progress callbacks."""
        for callback in self._progress_callbacks:
            try:
                callback(task_name, progress, message)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

    def _run_with_progress(
        self,
        generator: Generator[TaskProgress, None, Any],
        task_name: str,
    ) -> Any:
        """Run a generator and emit progress updates.

        Args:
            generator: Generator yielding TaskProgress
            task_name: Name of the task for progress callbacks

        Returns:
            Final result from the generator
        """
        result = None
        for progress in generator:
            if self._verbose:
                logger.info(f"[{progress.status.upper()}] {progress.message}")
            self._notify_progress(task_name, progress.progress, progress.message)

            if progress.status in ["completed", "failed"]:
                if hasattr(progress, "result"):
                    result = progress.result

                if progress.status == "failed" and progress.error:
                    raise ArchitectAIError(progress.error)

        return result

    def scan_codebase(
        self,
        path: Union[str, Path],
        session_name: Optional[str] = None,
        ignore_patterns: Optional[List[str]] = None,
    ) -> ScanResult:
        """Scan and ingest a codebase.

        This method scans a local directory or clones a Git repository,
        creates a new session, and stores all file metadata in the database.

        Args:
            path: Path to local directory or Git URL
            session_name: Optional name for the session
            ignore_patterns: Additional patterns to ignore during scanning

        Returns:
            ScanResult with session information

        Raises:
            ArchitectAIError: If scanning fails

        Example:
            >>> result = ai.scan_codebase("/path/to/project")
            >>> print(f"Scanned {result.files_scanned} files")
            >>> print(f"Session ID: {result.session_id}")
        """
        path_str = str(path)
        is_git_url = path_str.startswith("http") or path_str.startswith("git@")
        temp_dir = None

        try:
            if is_git_url:
                logger.info(f"Cloning repository: {path_str}")
                import tempfile

                temp_dir = tempfile.mkdtemp(prefix="architectai_")
                clone_path = clone_repository(path_str, temp_dir)
                if clone_path is None:
                    raise ArchitectAIError(f"Failed to clone repository: {path_str}")
                scan_path = clone_path
                source_path = path_str
            else:
                scan_path = os.path.abspath(path_str)
                if not os.path.exists(scan_path):
                    raise ArchitectAIError(f"Path not found: {path_str}")
                source_path = scan_path

            # Create session
            session_id = self.db.create_session(
                source_path=source_path,
                session_type="git" if is_git_url else "local",
            )

            logger.info(f"Created session: {session_id}")
            self._notify_progress("scan", 0.1, "Scanning files...")

            # Scan directory
            scanner = FileScanner()
            if ignore_patterns:
                scanner.ignore_patterns.extend(ignore_patterns)

            files = scanner.scan_directory(scan_path)
            logger.info(f"Found {len(files)} files")
            self._notify_progress("scan", 0.5, f"Found {len(files)} files")

            # Store files in database
            for i, file_info in enumerate(files):
                self.db.insert_file(
                    session_id=session_id,
                    relative_path=file_info["relative_path"],
                    absolute_path=file_info["absolute_path"],
                    language=file_info["language"],
                    size_bytes=file_info["size_bytes"],
                    line_count=file_info["line_count"],
                    content_hash=file_info["content_hash"],
                )
                if i % 100 == 0:
                    progress = 0.5 + (0.5 * i / len(files))
                    self._notify_progress(
                        "scan", progress, f"Processing file {i}/{len(files)}"
                    )

            # Count languages
            languages = {}
            for f in files:
                lang = f["language"]
                languages[lang] = languages.get(lang, 0) + 1

            self._notify_progress("scan", 1.0, "Scan complete")

            return ScanResult(
                session_id=session_id,
                files_scanned=len(files),
                languages=languages,
                source_path=source_path,
            )

        except Exception as e:
            logger.error(f"Scan failed: {e}")
            return ScanResult(
                session_id="",
                files_scanned=0,
                languages={},
                source_path=path_str,
                success=False,
                error=str(e),
            )
        finally:
            if temp_dir and os.path.exists(temp_dir):
                import shutil

                shutil.rmtree(temp_dir)

    def analyze(
        self,
        session_id: str,
        include_graph: bool = True,
        include_embeddings: bool = False,
    ) -> AnalysisResult:
        """Run full analysis on a session.

        Performs AST parsing, dependency graph building, and optionally
        generates embeddings for the session.

        Args:
            session_id: Session ID to analyze
            include_graph: Build dependency graph
            include_embeddings: Generate embeddings (requires Ollama)

        Returns:
            AnalysisResult with analysis statistics

        Raises:
            ArchitectAIError: If analysis fails

        Example:
            >>> result = ai.analyze(session_id)
            >>> print(f"Analyzed {result.files_analyzed} files")
        """
        session = self.orchestrator.get_session(session_id)
        if session is None:
            raise ArchitectAIError(f"Session not found: {session_id}")

        self._notify_progress("analyze", 0.0, "Starting analysis...")

        # Get files
        files = self.db.get_files_for_session(session_id)
        if not files:
            return AnalysisResult(
                session_id=session_id,
                status="no_files",
                files_analyzed=0,
                dependencies_found=0,
            )

        # Parse AST
        self._notify_progress("analyze", 0.1, "Parsing AST...")
        parser = ASTParser()
        parsed_count = 0

        for i, file_record in enumerate(files):
            try:
                file_path = file_record["absolute_path"]
                if not os.path.exists(file_path):
                    continue

                content = Path(file_path).read_text(encoding="utf-8")
                language = file_record["language"]

                result = parser.parse(content, language)

                self.db.update_file_parsed(
                    file_id=file_record["id"],
                    ast_available=True,
                )
                parsed_count += 1

                progress = 0.1 + (0.4 * i / len(files))
                self._notify_progress(
                    "analyze", progress, f"Parsed {i + 1}/{len(files)} files"
                )

            except Exception as e:
                logger.warning(f"Failed to parse {file_record['relative_path']}: {e}")

        # Build graph if requested
        dependencies_found = 0
        if include_graph and parsed_count > 0:
            self._notify_progress("analyze", 0.5, "Building dependency graph...")
            try:
                from architectai.pipeline.graph_pipeline import GraphPipeline

                pipeline = GraphPipeline(self.db)
                graph = pipeline.build_from_session(session_id)
                stats = graph.get_graph_stats()
                dependencies_found = stats.get("edges", 0)
                self._notify_progress(
                    "analyze", 0.8, f"Found {dependencies_found} dependencies"
                )
            except Exception as e:
                logger.warning(f"Graph building failed: {e}")

        # Generate embeddings if requested
        if include_embeddings:
            self._notify_progress("analyze", 0.9, "Generating embeddings...")
            try:
                self._generate_embeddings(session_id)
            except Exception as e:
                logger.warning(f"Embedding generation failed: {e}")

        self._notify_progress("analyze", 1.0, "Analysis complete")

        return AnalysisResult(
            session_id=session_id,
            status="complete",
            files_analyzed=parsed_count,
            dependencies_found=dependencies_found,
        )

    def _generate_embeddings(self, session_id: str) -> None:
        """Generate embeddings for a session."""
        from architectai.chunker.chunker import CodeChunker
        from architectai.embeddings.service import EmbeddingService
        from architectai.vectorstore.store import VectorStore

        chunker = CodeChunker(chunk_size=1000, chunk_overlap=200)
        embed_service = EmbeddingService(model=self.settings.embeddings.model)

        vector_store = VectorStore(str(self.settings.paths.vector_store_dir))

        if not embed_service.check_model_available():
            logger.warning(
                f"Embedding model not available: {self.settings.embeddings.model}"
            )
            return

        files = self.db.get_files_for_session(session_id)
        all_chunks = []

        for file_record in files:
            try:
                chunks = chunker.chunk_file(
                    file_record["absolute_path"], file_record["language"]
                )
                for chunk in chunks:
                    chunk["metadata"]["file_path"] = file_record["relative_path"]
                    chunk["metadata"]["language"] = file_record["language"]
                    chunk["metadata"]["session_id"] = session_id
                all_chunks.extend(chunks)
            except Exception as e:
                logger.warning(f"Failed to chunk {file_record['relative_path']}: {e}")

        if all_chunks:
            chunks_with_embeddings = embed_service.embed_chunks(all_chunks)
            vector_store.add_chunks(chunks_with_embeddings, session_id)
            logger.info(f"Stored {len(chunks_with_embeddings)} embeddings")

    def generate_docs(
        self,
        session_id: str,
        output_dir: Optional[Union[str, Path]] = None,
        doc_types: Optional[List[str]] = None,
    ) -> DocsResult:
        """Generate documentation for a session.

        Generates README.md, ARCHITECTURE.md, and other documentation
        based on the analyzed codebase.

        Args:
            session_id: Session ID to generate docs for
            output_dir: Output directory (default: ./docs_<session_id>)
            doc_types: Types of docs to generate (default: ["readme", "architecture"])

        Returns:
            DocsResult with output information

        Raises:
            ArchitectAIError: If documentation generation fails

        Example:
            >>> docs = ai.generate_docs(session_id, output_dir="./docs")
            >>> print(f"Generated {len(docs.files_generated)} files")
        """
        try:
            result = self._run_with_progress(
                self.orchestrator.generate_documentation(
                    session_id=session_id,
                    output_dir=str(output_dir) if output_dir else None,
                    doc_types=doc_types or ["readme", "architecture"],
                ),
                "documentation",
            )

            if isinstance(result, dict) and "error" in result:
                raise ArchitectAIError(result["error"])

            return DocsResult(
                session_id=session_id,
                output_dir=result.get("output_dir", ""),
                files_generated=result.get("files_generated", []),
            )

        except Exception as e:
            logger.error(f"Documentation generation failed: {e}")
            return DocsResult(
                session_id=session_id,
                output_dir=str(output_dir) if output_dir else "",
                files_generated=[],
                success=False,
                error=str(e),
            )

    def ask_question(
        self,
        session_id: str,
        query: str,
        include_context: bool = True,
    ) -> QAResult:
        """Ask a question about the codebase.

        Uses the Q&A agent to answer natural language questions about
        the codebase, with source file references.

        Args:
            session_id: Session ID to query
            query: Natural language question
            include_context: Include semantic context in answer

        Returns:
            QAResult with answer and relevant files

        Raises:
            ArchitectAIError: If Q&A fails

        Example:
            >>> result = ai.ask_question(session_id, "Where is auth handled?")
            >>> print(result.answer)
            >>> print(f"Relevant files: {result.relevant_files}")
        """
        try:
            result = self._run_with_progress(
                self.orchestrator.ask_question(
                    session_id=session_id,
                    question=query,
                ),
                "qa",
            )

            if isinstance(result, dict) and "error" in result:
                raise ArchitectAIError(result["error"])

            return QAResult(
                session_id=session_id,
                question=query,
                answer=result.get("answer", ""),
                relevant_files=result.get("relevant_files", []),
                confidence=0.8,  # Placeholder
            )

        except Exception as e:
            logger.error(f"Q&A failed: {e}")
            return QAResult(
                session_id=session_id,
                question=query,
                answer="",
                relevant_files=[],
                confidence=0.0,
                success=False,
                error=str(e),
            )

    def suggest_refactoring(
        self,
        session_id: str,
        focus_areas: Optional[List[str]] = None,
    ) -> RefactorResult:
        """Analyze code and suggest refactoring improvements.

        Uses the Refactor Agent to detect code smells, performance issues,
        and structural problems in the codebase.

        Args:
            session_id: Session ID to analyze
            focus_areas: Areas to focus on (e.g., ["performance", "readability"])

        Returns:
            RefactorResult with suggestions

        Raises:
            ArchitectAIError: If analysis fails

        Example:
            >>> result = ai.suggest_refactoring(session_id)
            >>> for suggestion in result.suggestions:
            ...     print(f"- {suggestion['type']}: {suggestion['description']}")
        """
        try:
            result = self._run_with_progress(
                self.orchestrator.analyze_refactoring(
                    session_id=session_id,
                    focus_areas=focus_areas,
                ),
                "refactoring",
            )

            if isinstance(result, dict) and "error" in result:
                raise ArchitectAIError(result["error"])

            return RefactorResult(
                session_id=session_id,
                suggestions=result.get("suggestions", []),
                files_analyzed=result.get("files_analyzed", 0),
            )

        except Exception as e:
            logger.error(f"Refactoring analysis failed: {e}")
            return RefactorResult(
                session_id=session_id,
                suggestions=[],
                files_analyzed=0,
                success=False,
                error=str(e),
            )

    def rebuild_project(
        self,
        session_id: str,
        output_dir: Union[str, Path],
        constraints: Optional[Dict[str, Any]] = None,
    ) -> RebuildResult:
        """Generate new project from analyzed codebase.

        Uses the Rebuilder Agent to scaffold a new project based on the
        architecture of an existing codebase, applying any specified constraints.

        Args:
            session_id: Template session ID to base project on
            output_dir: Directory to create new project in
            constraints: Optional constraints (e.g., {"framework": "fastapi"})

        Returns:
            RebuildResult with scaffolding information

        Raises:
            ArchitectAIError: If scaffolding fails

        Example:
            >>> result = ai.rebuild_project(
            ...     session_id,
            ...     output_dir="./new_project",
            ...     constraints={"framework": "django"}
            ... )
            >>> print(f"Created {len(result.files_created)} files")
        """
        try:
            result = self._run_with_progress(
                self.orchestrator.rebuild_project(
                    template_session_id=session_id,
                    output_dir=str(output_dir),
                    constraints=constraints,
                ),
                "rebuild",
            )

            if isinstance(result, dict) and "error" in result:
                raise ArchitectAIError(result["error"])

            return RebuildResult(
                session_id=session_id,
                output_dir=result.get("output_dir", str(output_dir)),
                files_created=result.get("files_created", []),
            )

        except Exception as e:
            logger.error(f"Project rebuild failed: {e}")
            return RebuildResult(
                session_id=session_id,
                output_dir=str(output_dir),
                files_created=[],
                success=False,
                error=str(e),
            )

    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get detailed information about a session.

        Args:
            session_id: Session ID to look up

        Returns:
            SessionInfo if found, None otherwise

        Example:
            >>> session = ai.get_session(session_id)
            >>> if session:
            ...     print(f"Source: {session.source_path}")
            ...     print(f"Files: {session.file_count}")
        """
        session = self.orchestrator.get_session(session_id)
        if session is None:
            return None

        stats = self.orchestrator.get_session_stats(session_id)

        return SessionInfo(
            session_id=session.session_id,
            source_path=session.source_path,
            session_type=session.session_type,
            status=session.status,
            created_at=session.created_at,
            updated_at=session.updated_at,
            file_count=stats.get("file_count", 0),
            parsed_count=stats.get("parsed_count", 0),
            total_lines=stats.get("total_lines", 0),
            languages=stats.get("languages", {}),
        )

    def list_sessions(
        self,
        limit: int = 100,
        include_stats: bool = False,
    ) -> List[SessionInfo]:
        """List all sessions.

        Args:
            limit: Maximum number of sessions to return
            include_stats: Include file statistics for each session

        Returns:
            List of SessionInfo objects

        Example:
            >>> sessions = ai.list_sessions(limit=10)
            >>> for session in sessions:
            ...     print(f"{session.session_id[:8]}: {session.source_path}")
        """
        sessions = self.orchestrator.list_sessions()
        sessions = sessions[:limit]

        result = []
        for session in sessions:
            if include_stats:
                stats = self.orchestrator.get_session_stats(session.session_id)
            else:
                stats = {}

            result.append(
                SessionInfo(
                    session_id=session.session_id,
                    source_path=session.source_path,
                    session_type=session.session_type,
                    status=session.status,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    file_count=stats.get("file_count", 0),
                    parsed_count=stats.get("parsed_count", 0),
                    total_lines=stats.get("total_lines", 0),
                    languages=stats.get("languages", {}),
                )
            )

        return result

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all associated data.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted successfully, False otherwise

        Example:
            >>> if ai.delete_session(session_id):
            ...     print("Session deleted")
        """
        return self.orchestrator.delete_session(session_id)

    def get_status(self) -> Dict[str, Any]:
        """Get system status information.

        Returns:
            Dictionary with version, database info, and agent status

        Example:
            >>> status = ai.get_status()
            >>> print(f"Version: {status['version']}")
            >>> print(f"Sessions: {status['session_count']}")
        """
        return self.orchestrator.get_system_status()

    def close(self) -> None:
        """Close database connections and cleanup resources."""
        if self.engine:
            self.engine.shutdown()
        logger.info("ArchitectAI closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


class ArchitectAIError(Exception):
    """Exception raised for ArchitectAI errors."""

    pass


# Convenience function for quick initialization
def create_ai(
    config_path: Optional[Union[str, Path]] = None,
    db_path: Optional[str] = None,
    verbose: bool = False,
) -> ArchitectAI:
    """Create an ArchitectAI instance with sensible defaults.

    This is a convenience function that creates an ArchitectAI instance
    with default settings. It's the quickest way to get started.

    Args:
        config_path: Path to configuration file (optional)
        db_path: Path to database file (optional)
        verbose: Enable verbose logging

    Returns:
        Configured ArchitectAI instance

    Example:
        >>> from architectai import create_ai
        >>> ai = create_ai()
        >>> result = ai.scan_codebase("/path/to/project")
    """
    return ArchitectAI(
        config_path=config_path,
        db_path=db_path,
        verbose=verbose,
    )
