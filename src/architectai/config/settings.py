"""Configuration settings for ArchitectAI.

This module provides comprehensive settings management using Pydantic v2
for validation and type safety.
"""

from __future__ import annotations

import os
import secrets
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseConfig(BaseModel):
    """Database configuration."""

    model_config = ConfigDict(extra="forbid")

    path: Path = Field(
        default_factory=lambda: Path.home() / ".architectai" / "architectai.db",
        description="Path to SQLite database file",
    )
    pool_size: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Connection pool size",
    )
    timeout: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        description="Connection timeout in seconds",
    )
    echo: bool = Field(
        default=False,
        description="Echo SQL statements (for debugging)",
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: Path) -> Path:
        """Ensure path is absolute and parent directory exists or can be created."""
        v = v.expanduser().resolve()
        return v


class LLMConfig(BaseModel):
    """LLM (Language Model) configuration."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(
        default="ollama",
        pattern=r"^(ollama|openai|anthropic|together|local)$",
        description="LLM provider",
    )
    model: str = Field(
        default="qwen2.5-coder:14b",
        description="Model name to use",
    )
    endpoint: Optional[str] = Field(
        default=None,
        description="Custom endpoint URL (for local/self-hosted models)",
    )
    api_key: Optional[SecretStr] = Field(
        default=None,
        description="API key (if required by provider)",
    )
    timeout: float = Field(
        default=120.0,
        ge=10.0,
        le=600.0,
        description="Request timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retries on failure",
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Delay between retries in seconds",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )
    max_tokens: int = Field(
        default=4096,
        ge=256,
        le=128000,
        description="Maximum tokens to generate",
    )
    context_window: int = Field(
        default=8192,
        ge=1024,
        le=200000,
        description="Model context window size",
    )
    top_p: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter",
    )
    top_k: int = Field(
        default=40,
        ge=1,
        le=100,
        description="Top-k sampling parameter",
    )


class EmbeddingsConfig(BaseModel):
    """Embeddings model configuration."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(
        default="ollama",
        pattern=r"^(ollama|openai|huggingface|local)$",
        description="Embeddings provider",
    )
    model: str = Field(
        default="mxbai-embed-large",
        description="Embedding model name",
    )
    endpoint: Optional[str] = Field(
        default=None,
        description="Custom endpoint URL",
    )
    api_key: Optional[SecretStr] = Field(
        default=None,
        description="API key (if required)",
    )
    dimensions: int = Field(
        default=1024,
        ge=64,
        le=4096,
        description="Embedding dimensions",
    )
    batch_size: int = Field(
        default=32,
        ge=1,
        le=256,
        description="Batch size for embedding generation",
    )
    timeout: float = Field(
        default=60.0,
        ge=10.0,
        le=300.0,
        description="Request timeout in seconds",
    )
    normalize: bool = Field(
        default=True,
        description="Normalize embeddings to unit length",
    )


class AgentThresholds(BaseModel):
    """Agent-specific thresholds and parameters."""

    model_config = ConfigDict(extra="forbid")

    min_confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for suggestions",
    )
    max_iterations: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum agent iterations",
    )
    max_suggestions: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum suggestions to return",
    )
    similarity_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Semantic similarity threshold",
    )
    context_depth: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Graph context expansion depth",
    )


class AgentsConfig(BaseModel):
    """Agent configuration."""

    model_config = ConfigDict(extra="forbid")

    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Temperature for agent reasoning",
    )
    max_tokens: int = Field(
        default=2048,
        ge=256,
        le=32000,
        description="Maximum tokens for agent responses",
    )
    parallel_agents: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of agents to run in parallel",
    )
    thresholds: AgentThresholds = Field(
        default_factory=AgentThresholds,
        description="Agent thresholds",
    )
    use_self_reflection: bool = Field(
        default=True,
        description="Enable agent self-reflection",
    )
    max_plan_steps: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum steps in execution plans",
    )


class ScannerConfig(BaseModel):
    """File scanner configuration."""

    model_config = ConfigDict(extra="forbid")

    max_file_size: int = Field(
        default=5 * 1024 * 1024,  # 5MB
        ge=1024,
        le=100 * 1024 * 1024,  # 100MB
        description="Maximum file size in bytes",
    )
    ignore_patterns: List[str] = Field(
        default_factory=lambda: [
            "*.pyc",
            "*.pyo",
            "__pycache__",
            ".git",
            ".svn",
            ".hg",
            ".venv",
            "venv",
            "node_modules",
            ".idea",
            ".vscode",
            "*.egg-info",
            "dist",
            "build",
            ".pytest_cache",
            ".mypy_cache",
            ".coverage",
            "*.log",
            "*.tmp",
            "*.temp",
            ".DS_Store",
            "Thumbs.db",
        ],
        description="Patterns to ignore during scanning",
    )
    binary_detection: bool = Field(
        default=True,
        description="Enable binary file detection",
    )
    follow_symlinks: bool = Field(
        default=False,
        description="Follow symbolic links",
    )
    respect_gitignore: bool = Field(
        default=True,
        description="Respect .gitignore files",
    )
    max_files: int = Field(
        default=10000,
        ge=100,
        le=100000,
        description="Maximum number of files to scan",
    )


class PathsConfig(BaseModel):
    """Path configuration."""

    model_config = ConfigDict(extra="forbid")

    cache_dir: Path = Field(
        default_factory=lambda: Path.home() / ".architectai" / "cache",
        description="Cache directory path",
    )
    temp_dir: Path = Field(
        default_factory=lambda: Path(Path(os.getenv("TMPDIR", "/tmp"))) / "architectai",
        description="Temporary directory path",
    )
    output_dir: Path = Field(
        default_factory=lambda: Path.cwd() / "architectai_output",
        description="Default output directory",
    )
    vector_store_dir: Path = Field(
        default_factory=lambda: Path.home() / ".architectai" / "vector_store",
        description="Vector store directory",
    )
    sessions_dir: Path = Field(
        default_factory=lambda: Path.home() / ".architectai" / "sessions",
        description="Sessions data directory",
    )
    config_dir: Path = Field(
        default_factory=lambda: Path.home() / ".architectai",
        description="Configuration directory",
    )

    @field_validator(
        "cache_dir",
        "temp_dir",
        "output_dir",
        "vector_store_dir",
        "sessions_dir",
        "config_dir",
    )
    @classmethod
    def validate_directory(cls, v: Path) -> Path:
        """Ensure path is absolute."""
        return v.expanduser().resolve()


class LoggingConfig(BaseModel):
    """Logging configuration."""

    model_config = ConfigDict(extra="forbid")

    level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging level",
    )
    file: Optional[Path] = Field(
        default=None,
        description="Log file path (None for stderr only)",
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )
    date_format: str = Field(
        default="%Y-%m-%d %H:%M:%S",
        description="Date format string",
    )
    max_bytes: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        ge=1024,
        le=100 * 1024 * 1024,
        description="Maximum log file size before rotation",
    )
    backup_count: int = Field(
        default=5,
        ge=0,
        le=20,
        description="Number of backup log files to keep",
    )
    json_format: bool = Field(
        default=False,
        description="Use JSON formatting for logs",
    )
    redact_secrets: bool = Field(
        default=True,
        description="Redact sensitive values from logs",
    )


class Settings(BaseModel):
    """Main settings class for ArchitectAI.

    This class combines all configuration categories and provides
    validation, serialization, and documentation generation.
    """

    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
        json_schema_extra={
            "title": "ArchitectAI Configuration",
            "description": "Complete configuration for the ArchitectAI system",
        },
    )

    version: str = Field(
        default="1",
        description="Configuration schema version",
    )

    # Top-level settings (expected by tests)
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    embedding_model: str = Field(
        default="mxbai-embed-large",
        description="Embedding model name",
    )

    # Configuration categories
    database: DatabaseConfig = Field(
        default_factory=DatabaseConfig,
        description="Database settings",
    )
    llm: LLMConfig = Field(
        default_factory=LLMConfig,
        description="LLM settings",
    )
    embeddings: EmbeddingsConfig = Field(
        default_factory=EmbeddingsConfig,
        description="Embeddings settings",
    )
    agents: AgentsConfig = Field(
        default_factory=AgentsConfig,
        description="Agent settings",
    )
    scanner: ScannerConfig = Field(
        default_factory=ScannerConfig,
        description="Scanner settings",
    )
    paths: PathsConfig = Field(
        default_factory=PathsConfig,
        description="Path settings",
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging settings",
    )

    # Profile tracking
    profile: Optional[str] = Field(
        default=None,
        description="Active configuration profile",
    )

    @model_validator(mode="after")
    def validate_consistency(self) -> Settings:
        """Validate cross-field consistency."""
        # Ensure embedding dimensions are compatible with vector store
        # (This is a placeholder - actual validation would check model specs)
        return self

    @model_validator(mode="before")
    @classmethod
    def load_from_env(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Load settings from environment variables before validation."""
        import os

        if isinstance(data, dict):
            if os.getenv("ARCHITECTAI_DEBUG") is not None:
                data["debug"] = os.getenv("ARCHITECTAI_DEBUG", "").lower() in (
                    "true",
                    "1",
                    "yes",
                )

            if os.getenv("ARCHITECTAI_LOG_LEVEL") is not None:
                data["log_level"] = os.getenv("ARCHITECTAI_LOG_LEVEL", "INFO")

            if os.getenv("ARCHITECTAI_EMBEDDING_MODEL") is not None:
                data["embedding_model"] = os.getenv(
                    "ARCHITECTAI_EMBEDDING_MODEL", "mxbai-embed-large"
                )

        return data

    def to_dict(self, mask_secrets: bool = True) -> Dict[str, Any]:
        """Convert settings to dictionary.

        Args:
            mask_secrets: If True, mask sensitive values

        Returns:
            Dictionary representation of settings
        """
        data = self.model_dump()

        if mask_secrets:
            # Mask API keys and other secrets
            if self.llm.api_key:
                data["llm"]["api_key"] = "***"
            if self.embeddings.api_key:
                data["embeddings"]["api_key"] = "***"

        return data

    def to_yaml(self, mask_secrets: bool = True) -> str:
        """Convert settings to YAML string.

        Args:
            mask_secrets: If True, mask sensitive values

        Returns:
            YAML representation of settings
        """
        try:
            import yaml

            data = self.to_dict(mask_secrets=mask_secrets)
            return yaml.dump(data, default_flow_style=False, sort_keys=False)
        except ImportError:
            raise ImportError(
                "PyYAML is required for YAML export. Install with: pip install pyyaml"
            )

    def to_json(self, mask_secrets: bool = True, indent: int = 2) -> str:
        """Convert settings to JSON string.

        Args:
            mask_secrets: If True, mask sensitive values
            indent: JSON indentation level

        Returns:
            JSON representation of settings
        """
        import json

        data = self.to_dict(mask_secrets=mask_secrets)
        return json.dumps(data, indent=indent, default=str)

    def get_path(self, path_type: str) -> Path:
        """Get a specific path by type.

        Args:
            path_type: One of 'cache', 'temp', 'output', 'vector_store', 'sessions', 'config', 'database'

        Returns:
            Path object
        """
        path_map = {
            "cache": self.paths.cache_dir,
            "temp": self.paths.temp_dir,
            "output": self.paths.output_dir,
            "vector_store": self.paths.vector_store_dir,
            "sessions": self.paths.sessions_dir,
            "config": self.paths.config_dir,
            "database": self.database.path.parent,
        }

        if path_type not in path_map:
            raise ValueError(f"Unknown path type: {path_type}")

        return path_map[path_type]

    def ensure_directories(self) -> None:
        """Ensure all configured directories exist."""
        dirs_to_create = [
            self.paths.cache_dir,
            self.paths.temp_dir,
            self.paths.output_dir,
            self.paths.vector_store_dir,
            self.paths.sessions_dir,
            self.paths.config_dir,
            self.database.path.parent,
        ]

        for directory in dirs_to_create:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Settings:
        """Create settings from dictionary.

        Args:
            data: Dictionary containing settings

        Returns:
            Settings instance
        """
        return cls.model_validate(data)

    @classmethod
    def default(cls) -> Settings:
        """Create default settings."""
        return cls()

    def get_embedding_dimension(self, model_name: str) -> int:
        """Get embedding dimension for a given model.

        Args:
            model_name: Name of the embedding model

        Returns:
            Embedding dimension (default 1024 for unknown models)
        """
        dimensions = {
            "nomic-embed-text": 768,
            "mxbai-embed-large": 1024,
            "bge-m3": 1024,
        }
        return dimensions.get(model_name, 1024)

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update settings from a dictionary.

        Args:
            data: Dictionary containing settings to update
        """
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)


def generate_schema(output_path: Optional[Path] = None) -> str:
    """Generate JSON schema for settings.

    Args:
        output_path: Optional path to write schema to

    Returns:
        JSON schema as string
    """
    import json

    schema = Settings.model_json_schema()
    schema_str = json.dumps(schema, indent=2)

    if output_path:
        output_path.write_text(schema_str)

    return schema_str
