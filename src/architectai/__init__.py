"""ArchitectAI - Local AI Software Architect for Private Codebases.

A fully local, offline-capable AI system that ingests any codebase or GitHub
repository and produces detailed documentation, architecture overviews,
Q&A capabilities, refactor suggestions, and code generation.

Example:
    >>> from architectai import ArchitectAI, create_ai
    >>>
    >>> # Initialize
    >>> ai = create_ai()
    >>>
    >>> # Scan a codebase
    >>> result = ai.scan_codebase("/path/to/project")
    >>> print(f"Session ID: {result.session_id}")
    >>>
    >>> # Generate documentation
    >>> docs = ai.generate_docs(result.session_id)
    >>>
    >>> # Ask questions
    >>> answer = ai.ask_question(result.session_id, "Where is auth handled?")
    >>> print(answer.answer)
"""

__version__ = "0.1.0"
__author__ = "Rajesh"

from architectai.api import (
    ArchitectAI,
    ArchitectAIError,
    create_ai,
    ScanResult,
    AnalysisResult,
    DocsResult,
    QAResult,
    RefactorResult,
    RebuildResult,
    SessionInfo,
)

from architectai.bootstrap import (
    bootstrap,
    setup_directories,
    check_dependencies,
    initialize_database,
    download_models,
    verify_installation,
    BootstrapError,
)

__all__ = [
    # Main API
    "ArchitectAI",
    "create_ai",
    "ArchitectAIError",
    # Result types
    "ScanResult",
    "AnalysisResult",
    "DocsResult",
    "QAResult",
    "RefactorResult",
    "RebuildResult",
    "SessionInfo",
    # Bootstrap utilities
    "bootstrap",
    "setup_directories",
    "check_dependencies",
    "initialize_database",
    "download_models",
    "verify_installation",
    "BootstrapError",
    # Metadata
    "__version__",
    "__author__",
]
