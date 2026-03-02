"""Configuration validation for ArchitectAI.

Provides comprehensive validation of settings including path checks,
model availability, threshold validation, and dependency checks.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from architectai.config.settings import Settings


@dataclass
class ValidationError:
    """Single validation error."""

    field: str
    message: str
    severity: str = "error"  # error, warning


@dataclass
class ValidationResult:
    """Result of configuration validation."""

    is_valid: bool = True
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

    def add_error(self, field: str, message: str) -> None:
        """Add an error."""
        self.errors.append(ValidationError(field, message, "error"))
        self.is_valid = False

    def add_warning(self, field: str, message: str) -> None:
        """Add a warning."""
        self.warnings.append(ValidationError(field, message, "warning"))

    def merge(self, other: ValidationResult) -> ValidationResult:
        """Merge another validation result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.is_valid = self.is_valid and other.is_valid
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "errors": [{"field": e.field, "message": e.message} for e in self.errors],
            "warnings": [
                {"field": w.field, "message": w.message} for w in self.warnings
            ],
        }


class ConfigValidator:
    """Validates ArchitectAI configuration."""

    # Known valid Ollama models
    KNOWN_OLLAMA_MODELS: Set[str] = {
        "llama2",
        "llama2:13b",
        "llama2:70b",
        "llama3",
        "llama3:8b",
        "llama3:70b",
        "mistral",
        "mistral:7b",
        "mixtral",
        "mixtral:8x7b",
        "mixtral:8x22b",
        "codellama",
        "codellama:7b",
        "codellama:13b",
        "codellama:34b",
        "qwen",
        "qwen:7b",
        "qwen:14b",
        "qwen:72b",
        "qwen2.5-coder",
        "qwen2.5-coder:7b",
        "qwen2.5-coder:14b",
        "qwen2.5-coder:32b",
        "phi4",
        "phi4:14b",
        "gemma",
        "gemma:2b",
        "gemma:7b",
        "nomic-embed-text",
        "mxbai-embed-large",
        "snowflake-arctic-embed",
        "bge-m3",
    }

    def __init__(self, check_models: bool = True):
        """Initialize validator.

        Args:
            check_models: Whether to check model availability
        """
        self.check_models = check_models

    def validate(self, settings: Settings) -> ValidationResult:
        """Validate complete settings.

        Args:
            settings: Settings to validate

        Returns:
            Validation result
        """
        result = ValidationResult()

        # Validate each category
        result.merge(self._validate_database(settings))
        result.merge(self._validate_llm(settings))
        result.merge(self._validate_embeddings(settings))
        result.merge(self._validate_agents(settings))
        result.merge(self._validate_scanner(settings))
        result.merge(self._validate_paths(settings))
        result.merge(self._validate_logging(settings))

        return result

    def _validate_database(self, settings: Settings) -> ValidationResult:
        """Validate database settings."""
        result = ValidationResult()
        db = settings.database

        # Check database path
        db_path = db.path
        parent_dir = db_path.parent

        if parent_dir.exists():
            if not parent_dir.is_dir():
                result.add_error(
                    "database.path", f"Parent path is not a directory: {parent_dir}"
                )
            elif not os.access(parent_dir, os.W_OK):
                result.add_error(
                    "database.path", f"Parent directory is not writable: {parent_dir}"
                )
        else:
            # Check if we can create the parent directory
            try:
                parent_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                result.add_error(
                    "database.path", f"Cannot create parent directory: {parent_dir}"
                )
            except OSError as e:
                result.add_error(
                    "database.path", f"Cannot create parent directory: {e}"
                )

        return result

    def _validate_llm(self, settings: Settings) -> ValidationResult:
        """Validate LLM settings."""
        result = ValidationResult()
        llm = settings.llm

        # Validate provider
        valid_providers = {"ollama", "openai", "anthropic", "together", "local"}
        if llm.provider not in valid_providers:
            result.add_error("llm.provider", f"Invalid provider: {llm.provider}")

        # Validate temperature range
        if not 0.0 <= llm.temperature <= 2.0:
            result.add_error(
                "llm.temperature",
                f"Temperature must be between 0.0 and 2.0: {llm.temperature}",
            )

        # Validate token ranges
        if llm.max_tokens < 256:
            result.add_error(
                "llm.max_tokens", f"max_tokens must be at least 256: {llm.max_tokens}"
            )

        if llm.context_window < 1024:
            result.add_error(
                "llm.context_window",
                f"context_window must be at least 1024: {llm.context_window}",
            )

        # Check model availability for Ollama
        if self.check_models and llm.provider == "ollama":
            model_check = self._check_ollama_model(llm.model)
            if not model_check.is_valid:
                result.merge(model_check)
            elif model_check.warnings:
                result.warnings.extend(model_check.warnings)

        return result

    def _validate_embeddings(self, settings: Settings) -> ValidationResult:
        """Validate embeddings settings."""
        result = ValidationResult()
        emb = settings.embeddings

        # Validate provider
        valid_providers = {"ollama", "openai", "huggingface", "local"}
        if emb.provider not in valid_providers:
            result.add_error("embeddings.provider", f"Invalid provider: {emb.provider}")

        # Validate dimensions
        if emb.dimensions < 64:
            result.add_error(
                "embeddings.dimensions",
                f"Dimensions must be at least 64: {emb.dimensions}",
            )
        elif emb.dimensions > 4096:
            result.add_warning(
                "embeddings.dimensions",
                f"Very large dimensions may impact performance: {emb.dimensions}",
            )

        # Validate batch size
        if emb.batch_size < 1:
            result.add_error(
                "embeddings.batch_size",
                f"Batch size must be at least 1: {emb.batch_size}",
            )

        # Check model availability for Ollama
        if self.check_models and emb.provider == "ollama":
            model_check = self._check_ollama_model(emb.model)
            if not model_check.is_valid:
                result.merge(model_check)
            elif model_check.warnings:
                result.warnings.extend(model_check.warnings)

        return result

    def _validate_agents(self, settings: Settings) -> ValidationResult:
        """Validate agent settings."""
        result = ValidationResult()
        agents = settings.agents
        thresholds = agents.thresholds

        # Validate temperature
        if not 0.0 <= agents.temperature <= 2.0:
            result.add_error(
                "agents.temperature",
                f"Temperature must be between 0.0 and 2.0: {agents.temperature}",
            )

        # Validate thresholds
        if not 0.0 <= thresholds.min_confidence <= 1.0:
            result.add_error(
                "agents.thresholds.min_confidence",
                f"min_confidence must be between 0.0 and 1.0: {thresholds.min_confidence}",
            )

        if not 0.0 <= thresholds.similarity_threshold <= 1.0:
            result.add_error(
                "agents.thresholds.similarity_threshold",
                f"similarity_threshold must be between 0.0 and 1.0: {thresholds.similarity_threshold}",
            )

        # Validate positive integers
        if agents.max_tokens < 1:
            result.add_error(
                "agents.max_tokens", f"max_tokens must be positive: {agents.max_tokens}"
            )

        if thresholds.max_iterations < 1:
            result.add_error(
                "agents.thresholds.max_iterations",
                f"max_iterations must be positive: {thresholds.max_iterations}",
            )

        if thresholds.max_suggestions < 1:
            result.add_error(
                "agents.thresholds.max_suggestions",
                f"max_suggestions must be positive: {thresholds.max_suggestions}",
            )

        return result

    def _validate_scanner(self, settings: Settings) -> ValidationResult:
        """Validate scanner settings."""
        result = ValidationResult()
        scanner = settings.scanner

        # Validate file size
        if scanner.max_file_size < 1024:
            result.add_warning(
                "scanner.max_file_size",
                f"Very small max_file_size may exclude valid files: {scanner.max_file_size}",
            )
        elif scanner.max_file_size > 50 * 1024 * 1024:
            result.add_warning(
                "scanner.max_file_size",
                f"Very large max_file_size may impact performance: {scanner.max_file_size}",
            )

        # Validate max files
        if scanner.max_files < 100:
            result.add_warning(
                "scanner.max_files",
                f"Very low max_files may miss code: {scanner.max_files}",
            )

        return result

    def _validate_paths(self, settings: Settings) -> ValidationResult:
        """Validate path settings."""
        result = ValidationResult()
        paths = settings.paths

        # Check each directory path
        path_checks = [
            ("cache_dir", paths.cache_dir),
            ("temp_dir", paths.temp_dir),
            ("output_dir", paths.output_dir),
            ("vector_store_dir", paths.vector_store_dir),
            ("sessions_dir", paths.sessions_dir),
            ("config_dir", paths.config_dir),
        ]

        for name, path in path_checks:
            if path.exists():
                if not path.is_dir():
                    result.add_error(
                        f"paths.{name}", f"Path exists but is not a directory: {path}"
                    )
                elif not os.access(path, os.W_OK):
                    result.add_error(
                        f"paths.{name}", f"Directory is not writable: {path}"
                    )
            else:
                # Check if we can create it
                try:
                    path.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    result.add_error(
                        f"paths.{name}",
                        f"Cannot create directory (permission denied): {path}",
                    )
                except OSError as e:
                    result.add_error(f"paths.{name}", f"Cannot create directory: {e}")

        return result

    def _validate_logging(self, settings: Settings) -> ValidationResult:
        """Validate logging settings."""
        result = ValidationResult()
        logging = settings.logging

        # Check log file if specified
        if logging.file:
            log_path = Path(logging.file)
            log_dir = log_path.parent

            if log_dir.exists():
                if not log_dir.is_dir():
                    result.add_error(
                        "logging.file", f"Log directory is not a directory: {log_dir}"
                    )
                elif not os.access(log_dir, os.W_OK):
                    result.add_error(
                        "logging.file", f"Log directory is not writable: {log_dir}"
                    )
            else:
                try:
                    log_dir.mkdir(parents=True, exist_ok=True)
                except (PermissionError, OSError) as e:
                    result.add_error(
                        "logging.file", f"Cannot create log directory: {e}"
                    )

        return result

    def _check_ollama_model(self, model: str) -> ValidationResult:
        """Check if an Ollama model is available.

        Args:
            model: Model name to check

        Returns:
            Validation result
        """
        result = ValidationResult()

        # Check if Ollama is installed
        if not shutil.which("ollama"):
            result.add_warning(
                "llm.model",
                "Ollama not found in PATH. Model availability cannot be verified.",
            )
            return result

        # Try to list available models
        try:
            output = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if output.returncode == 0:
                # Parse available models
                available_models = set()
                for line in output.stdout.strip().split("\n")[1:]:  # Skip header
                    if line.strip():
                        model_name = line.split()[0]
                        available_models.add(model_name)

                # Check if requested model is available
                if model not in available_models:
                    # Check if it's a known model
                    base_model = model.split(":")[0]
                    if (
                        model not in self.KNOWN_OLLAMA_MODELS
                        and base_model not in self.KNOWN_OLLAMA_MODELS
                    ):
                        result.add_warning(
                            "llm.model",
                            f"Model '{model}' is not in known models list. "
                            f"It may not be a valid Ollama model.",
                        )
                    else:
                        result.add_warning(
                            "llm.model",
                            f"Model '{model}' not found locally. "
                            f"Run: ollama pull {model}",
                        )
            else:
                result.add_warning(
                    "llm.model", f"Could not check model availability: {output.stderr}"
                )

        except subprocess.TimeoutExpired:
            result.add_warning("llm.model", "Timeout checking model availability")
        except Exception as e:
            result.add_warning("llm.model", f"Could not check model availability: {e}")

        return result

    def check_dependencies(self) -> ValidationResult:
        """Check external dependencies.

        Returns:
            Validation result with dependency status
        """
        result = ValidationResult()

        # Check for Ollama
        if not shutil.which("ollama"):
            result.add_warning(
                "dependencies.ollama",
                "Ollama not found. Install from https://ollama.ai",
            )

        # Check for git
        if not shutil.which("git"):
            result.add_warning(
                "dependencies.git", "Git not found. Repository cloning will not work."
            )

        return result


def validate_config(settings: Settings, check_models: bool = True) -> ValidationResult:
    """Convenience function to validate settings.

    Args:
        settings: Settings to validate
        check_models: Whether to check model availability

    Returns:
        Validation result
    """
    validator = ConfigValidator(check_models=check_models)
    return validator.validate(settings)
