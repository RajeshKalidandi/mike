"""System initialization and bootstrap utilities for Mike.

This module handles first-time setup, dependency checking, and system
initialization to ensure Mike is ready to use.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import sqlite3

from mike.config.settings import Settings


logger = logging.getLogger(__name__)


# Required and optional dependencies
REQUIRED_DEPENDENCIES = {
    "tree-sitter": "tree-sitter",
    "tree-sitter-languages": "tree-sitter-languages",
    "chromadb": "chromadb",
    "pydantic": "pydantic",
    "click": "click",
}

OPTIONAL_DEPENDENCIES = {
    "streamlit": ("streamlit", "Required for web UI"),
    "ollama": ("ollama", "Required for local LLM support"),
    "networkx": ("networkx", "Required for dependency graphs"),
    "pyyaml": ("pyyaml", "Required for YAML config support"),
    "rich": ("rich", "Required for rich CLI output"),
}

# Default models to download
DEFAULT_MODELS = [
    ("mxbai-embed-large", "Embedding model for semantic search"),
    ("qwen2.5-coder:14b", "Code generation and analysis model"),
]


def setup_directories(settings: Optional[Settings] = None) -> Dict[str, Path]:
    """Create all required directories for Mike.

    Creates the following directories if they don't exist:
    - ~/.mike/ (config)
    - ~/.mike/cache/
    - ~/.mike/vector_store/
    - ~/.mike/sessions/
    - ~/.mike/sessions/logs/

    Args:
        settings: Settings instance (uses defaults if None)

    Returns:
        Dictionary mapping directory names to Path objects

    Example:
        >>> dirs = setup_directories()
        >>> print(f"Cache dir: {dirs['cache']}")
    """
    if settings is None:
        settings = Settings.default()

    dirs = {
        "config": settings.paths.config_dir,
        "cache": settings.paths.cache_dir,
        "temp": settings.paths.temp_dir,
        "vector_store": settings.paths.vector_store_dir,
        "sessions": settings.paths.sessions_dir,
        "database": settings.database.path.parent,
    }

    created = []
    for name, path in dirs.items():
        try:
            path.mkdir(parents=True, exist_ok=True)
            created.append(name)
            logger.debug(f"Directory ready: {path}")
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            raise BootstrapError(f"Failed to create {name} directory: {e}")

    logger.info(f"Created {len(created)} directories")
    return dirs


def check_dependencies() -> Dict[str, Dict[str, any]]:
    """Check system dependencies and their availability.

    Checks for:
    - Required Python packages
    - Optional Python packages
    - External tools (Ollama, Git)

    Returns:
        Dictionary with dependency status information:
        {
            "required": {"package": {"installed": True, "version": "1.0.0"}},
            "optional": {"package": {"installed": True, "version": "1.0.0", "reason": "..."}},
            "external": {"tool": {"available": True, "version": "1.0.0"}}
        }

    Example:
        >>> deps = check_dependencies()
        >>> if not deps["external"]["ollama"]["available"]:
        ...     print("Please install Ollama")
    """
    result = {
        "required": {},
        "optional": {},
        "external": {},
    }

    # Check required packages
    for package, import_name in REQUIRED_DEPENDENCIES.items():
        try:
            module = __import__(import_name)
            version = getattr(module, "__version__", "unknown")
            result["required"][package] = {
                "installed": True,
                "version": version,
            }
        except ImportError:
            result["required"][package] = {
                "installed": False,
                "version": None,
            }

    # Check optional packages
    for package, (import_name, reason) in OPTIONAL_DEPENDENCIES.items():
        try:
            module = __import__(import_name)
            version = getattr(module, "__version__", "unknown")
            result["optional"][package] = {
                "installed": True,
                "version": version,
                "reason": reason,
            }
        except ImportError:
            result["optional"][package] = {
                "installed": False,
                "version": None,
                "reason": reason,
            }

    # Check external tools
    result["external"]["ollama"] = _check_ollama()
    result["external"]["git"] = _check_git()
    result["external"]["python"] = _check_python()

    return result


def _check_ollama() -> Dict[str, any]:
    """Check if Ollama is installed and running."""
    try:
        # Check if ollama command exists
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            # Try to list models to verify it's running
            try:
                subprocess.run(
                    ["ollama", "list"],
                    capture_output=True,
                    timeout=5,
                )
                return {
                    "available": True,
                    "version": version,
                    "running": True,
                }
            except (subprocess.TimeoutExpired, FileNotFoundError):
                return {
                    "available": True,
                    "version": version,
                    "running": False,
                }
        return {"available": False, "version": None, "running": False}
    except FileNotFoundError:
        return {"available": False, "version": None, "running": False}
    except subprocess.TimeoutExpired:
        return {"available": True, "version": "unknown", "running": False}


def _check_git() -> Dict[str, any]:
    """Check if Git is installed."""
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            version = result.stdout.strip().replace("git version ", "")
            return {"available": True, "version": version}
        return {"available": False, "version": None}
    except FileNotFoundError:
        return {"available": False, "version": None}


def _check_python() -> Dict[str, any]:
    """Check Python version."""
    version = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    return {
        "available": True,
        "version": version,
    }


def initialize_database(db_path: Optional[str] = None) -> str:
    """Initialize the SQLite database.

    Creates the database file and all required tables if they don't exist.

    Args:
        db_path: Path to database file (uses default if None)

    Returns:
        Path to the initialized database

    Raises:
        BootstrapError: If database initialization fails

    Example:
        >>> db_path = initialize_database()
        >>> print(f"Database ready at: {db_path}")
    """
    if db_path is None:
        settings = Settings.default()
        db_path = str(settings.database.path)

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Create tables
        conn = sqlite3.connect(db_path)
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
                edge_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                UNIQUE(session_id, source_file, target_file, edge_type)
            )
        """)

        conn.commit()
        conn.close()

        logger.info(f"Database initialized: {db_path}")
        return str(db_path)

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise BootstrapError(f"Failed to initialize database: {e}")


def download_models(
    models: Optional[List[Tuple[str, str]]] = None,
    force: bool = False,
) -> Dict[str, Dict[str, any]]:
    """Download default models from Ollama.

    Pulls the specified models from Ollama. By default, downloads
    the recommended models for embeddings and code analysis.

    Args:
        models: List of (model_name, description) tuples (uses defaults if None)
        force: Re-download even if model exists

    Returns:
        Dictionary with model download status:
        {
            "model_name": {"success": True, "message": "..."}
        }

    Example:
        >>> results = download_models()
        >>> for model, status in results.items():
        ...     if status["success"]:
        ...         print(f"✓ {model}")
    """
    if models is None:
        models = DEFAULT_MODELS

    results = {}

    # Check if Ollama is available
    deps = check_dependencies()
    if not deps["external"]["ollama"]["available"]:
        logger.error("Ollama not found. Please install from https://ollama.ai")
        for model_name, _ in models:
            results[model_name] = {
                "success": False,
                "message": "Ollama not installed",
            }
        return results

    for model_name, description in models:
        try:
            logger.info(f"Downloading model: {model_name} ({description})")

            # Check if model already exists
            if not force:
                check_result = subprocess.run(
                    ["ollama", "list"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if model_name in check_result.stdout:
                    results[model_name] = {
                        "success": True,
                        "message": "Already exists",
                        "description": description,
                    }
                    continue

            # Pull model
            result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            if result.returncode == 0:
                results[model_name] = {
                    "success": True,
                    "message": "Downloaded successfully",
                    "description": description,
                }
                logger.info(f"✓ Downloaded {model_name}")
            else:
                results[model_name] = {
                    "success": False,
                    "message": result.stderr or "Unknown error",
                    "description": description,
                }
                logger.error(f"✗ Failed to download {model_name}")

        except subprocess.TimeoutExpired:
            results[model_name] = {
                "success": False,
                "message": "Download timeout (10 minutes)",
                "description": description,
            }
            logger.error(f"✗ Timeout downloading {model_name}")
        except Exception as e:
            results[model_name] = {
                "success": False,
                "message": str(e),
                "description": description,
            }
            logger.error(f"✗ Error downloading {model_name}: {e}")

    return results


def verify_installation() -> Dict[str, any]:
    """Perform comprehensive installation verification.

    Checks all components and returns a detailed status report.

    Returns:
        Dictionary with installation status:
        {
            "ready": True,
            "components": {
                "directories": {"status": "ok", "details": [...]},
                "database": {"status": "ok", "path": "..."},
                "dependencies": {"status": "ok", "missing": []},
            },
            "issues": [],
            "recommendations": []
        }

    Example:
        >>> status = verify_installation()
        >>> if status["ready"]:
        ...     print("System ready!")
        ... else:
        ...     for issue in status["issues"]:
        ...         print(f"Issue: {issue}")
    """
    status = {
        "ready": True,
        "components": {},
        "issues": [],
        "recommendations": [],
    }

    # Check directories
    try:
        dirs = setup_directories()
        status["components"]["directories"] = {
            "status": "ok",
            "paths": {k: str(v) for k, v in dirs.items()},
        }
    except BootstrapError as e:
        status["components"]["directories"] = {"status": "error", "message": str(e)}
        status["issues"].append(f"Directory setup failed: {e}")
        status["ready"] = False

    # Check database
    try:
        db_path = initialize_database()
        status["components"]["database"] = {
            "status": "ok",
            "path": db_path,
        }
    except BootstrapError as e:
        status["components"]["database"] = {"status": "error", "message": str(e)}
        status["issues"].append(f"Database initialization failed: {e}")
        status["ready"] = False

    # Check dependencies
    deps = check_dependencies()
    missing_required = [
        pkg for pkg, info in deps["required"].items() if not info["installed"]
    ]
    missing_optional = [
        pkg for pkg, info in deps["optional"].items() if not info["installed"]
    ]

    if missing_required:
        status["components"]["dependencies"] = {
            "status": "error",
            "missing_required": missing_required,
            "missing_optional": missing_optional,
        }
        status["issues"].append(
            f"Missing required packages: {', '.join(missing_required)}"
        )
        status["ready"] = False
    else:
        status["components"]["dependencies"] = {
            "status": "ok",
            "missing_optional": missing_optional,
        }
        if missing_optional:
            status["recommendations"].append(
                f"Consider installing optional packages: {', '.join(missing_optional)}"
            )

    # Check external tools
    if not deps["external"]["ollama"]["available"]:
        status["recommendations"].append(
            "Install Ollama for local LLM support: https://ollama.ai"
        )
    elif not deps["external"]["ollama"]["running"]:
        status["recommendations"].append("Start Ollama service: ollama serve")

    return status


def bootstrap(
    download_default_models: bool = True,
    verbose: bool = False,
) -> Dict[str, any]:
    """Run complete bootstrap process.

    This is the main entry point for system initialization. It:
    1. Sets up all required directories
    2. Initializes the database
    3. Checks dependencies
    4. Optionally downloads default models

    Args:
        download_default_models: Download recommended models from Ollama
        verbose: Enable verbose logging

    Returns:
        Bootstrap result with status and details

    Example:
        >>> result = bootstrap()
        >>> if result["success"]:
        ...     print("Mike is ready!")
        ... else:
        ...     print(f"Issues: {result['issues']}")
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    logger.info("=" * 60)
    logger.info("Mike Bootstrap")
    logger.info("=" * 60)

    result = {
        "success": True,
        "steps": [],
        "issues": [],
        "models": {},
    }

    # Step 1: Setup directories
    logger.info("Step 1: Setting up directories...")
    try:
        dirs = setup_directories()
        result["steps"].append(
            {
                "name": "directories",
                "status": "success",
                "paths": {k: str(v) for k, v in dirs.items()},
            }
        )
        logger.info(f"✓ Created {len(dirs)} directories")
    except BootstrapError as e:
        result["steps"].append(
            {"name": "directories", "status": "failed", "error": str(e)}
        )
        result["issues"].append(str(e))
        result["success"] = False

    # Step 2: Initialize database
    logger.info("Step 2: Initializing database...")
    try:
        db_path = initialize_database()
        result["steps"].append(
            {"name": "database", "status": "success", "path": db_path}
        )
        logger.info(f"✓ Database ready at {db_path}")
    except BootstrapError as e:
        result["steps"].append(
            {"name": "database", "status": "failed", "error": str(e)}
        )
        result["issues"].append(str(e))
        result["success"] = False

    # Step 3: Check dependencies
    logger.info("Step 3: Checking dependencies...")
    deps = check_dependencies()
    missing_required = [
        pkg for pkg, info in deps["required"].items() if not info["installed"]
    ]

    if missing_required:
        result["steps"].append(
            {
                "name": "dependencies",
                "status": "failed",
                "missing": missing_required,
            }
        )
        result["issues"].append(
            f"Missing required packages: {', '.join(missing_required)}"
        )
        result["success"] = False
        logger.error(f"✗ Missing packages: {', '.join(missing_required)}")
    else:
        result["steps"].append({"name": "dependencies", "status": "success"})
        logger.info("✓ All required dependencies installed")

        # Check optional dependencies
        missing_optional = [
            pkg for pkg, info in deps["optional"].items() if not info["installed"]
        ]
        if missing_optional:
            logger.info(
                f"Optional packages not installed: {', '.join(missing_optional)}"
            )

    # Step 4: Download models (if requested)
    if download_default_models:
        logger.info("Step 4: Downloading models...")
        if deps["external"]["ollama"]["available"]:
            model_results = download_models()
            result["models"] = model_results

            successful = sum(1 for r in model_results.values() if r["success"])
            logger.info(f"✓ Downloaded {successful}/{len(model_results)} models")
        else:
            result["steps"].append(
                {
                    "name": "models",
                    "status": "skipped",
                    "reason": "Ollama not available",
                }
            )
            logger.warning("⚠ Ollama not available, skipping model download")
            result["recommendations"] = result.get("recommendations", [])
            result["recommendations"].append(
                "Install Ollama to download models: https://ollama.ai"
            )

    # Final status
    logger.info("=" * 60)
    if result["success"]:
        logger.info("✓ Bootstrap complete! Mike is ready.")
    else:
        logger.error("✗ Bootstrap failed. Please fix the issues above.")
    logger.info("=" * 60)

    return result


def reset_system(
    keep_database: bool = False,
    keep_models: bool = True,
    force: bool = False,
) -> Dict[str, any]:
    """Reset Mike to factory defaults.

    WARNING: This will delete all data! Use with caution.

    Args:
        keep_database: Don't delete the database
        keep_models: Don't delete downloaded models
        force: Skip confirmation prompt

    Returns:
        Dictionary with reset status

    Example:
        >>> result = reset_system(force=True)
        >>> print(f"Removed {result['files_deleted']} files")
    """
    if not force:
        response = input(
            "Are you sure you want to reset Mike? This will delete all data! [y/N]: "
        )
        if response.lower() != "y":
            return {"success": False, "message": "Cancelled by user"}

    settings = Settings.default()
    result = {
        "success": True,
        "files_deleted": 0,
        "dirs_removed": [],
    }

    # Remove cache
    if settings.paths.cache_dir.exists():
        shutil.rmtree(settings.paths.cache_dir)
        result["dirs_removed"].append(str(settings.paths.cache_dir))
        result["files_deleted"] += 1

    # Remove vector store
    if settings.paths.vector_store_dir.exists():
        shutil.rmtree(settings.paths.vector_store_dir)
        result["dirs_removed"].append(str(settings.paths.vector_store_dir))
        result["files_deleted"] += 1

    # Remove sessions
    if settings.paths.sessions_dir.exists():
        shutil.rmtree(settings.paths.sessions_dir)
        result["dirs_removed"].append(str(settings.paths.sessions_dir))
        result["files_deleted"] += 1

    # Remove database (if requested)
    if not keep_database and settings.database.path.exists():
        settings.database.path.unlink()
        result["files_deleted"] += 1

    logger.info(f"Reset complete. Removed {result['files_deleted']} items.")
    return result


class BootstrapError(Exception):
    """Exception raised during bootstrap operations."""

    pass
