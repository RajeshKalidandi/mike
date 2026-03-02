"""Configuration management module for ArchitectAI.

This module provides comprehensive configuration management including:
- Settings validation with Pydantic
- Profile management for different use cases
- Hierarchical configuration loading
- Configuration validation

Example:
    from architectai.config import load_config, Settings

    # Load configuration
    settings = load_config(profile="fast")

    # Access settings
    print(settings.llm.model)
    print(settings.database.path)

    # Create and save custom profile
    from architectai.config import ProfileManager
    manager = ProfileManager()
    profile = manager.create_profile("custom", "My custom profile", settings)
"""

from architectai.config.loader import ConfigLoader, ConfigLoadError, load_config
from architectai.config.profiles import Profile, ProfileManager
from architectai.config.settings import (
    AgentsConfig,
    AgentThresholds,
    DatabaseConfig,
    EmbeddingsConfig,
    LLMConfig,
    LoggingConfig,
    LogLevel,
    PathsConfig,
    ScannerConfig,
    Settings,
    generate_schema,
)
from architectai.config.validation import (
    ConfigValidator,
    ValidationError,
    ValidationResult,
    validate_config,
)

__all__ = [
    # Settings
    "Settings",
    "DatabaseConfig",
    "LLMConfig",
    "EmbeddingsConfig",
    "AgentsConfig",
    "AgentThresholds",
    "ScannerConfig",
    "PathsConfig",
    "LoggingConfig",
    "LogLevel",
    "generate_schema",
    # Profiles
    "Profile",
    "ProfileManager",
    # Validation
    "ConfigValidator",
    "ValidationResult",
    "ValidationError",
    "validate_config",
    # Loading
    "ConfigLoader",
    "ConfigLoadError",
    "load_config",
]

__version__ = "1.0.0"
