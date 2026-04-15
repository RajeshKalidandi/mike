"""Configuration loading for Mike.

Supports hierarchical configuration loading with precedence:
1. Default settings
2. User config (~/.mike/config.yaml)
3. Project config (./.mike/config.yaml)
4. Environment variables (ARCHITECTAI_*)
5. CLI arguments

Also supports hot-reload and configuration migration.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from mike.config.profiles import ProfileManager
from mike.config.settings import Settings


class ConfigLoadError(Exception):
    """Error loading configuration."""

    pass


class ConfigLoader:
    """Loads configuration from multiple sources.

    Implements hierarchical configuration loading with proper precedence
    and supports hot-reload capabilities.
    """

    # Environment variable prefix
    ENV_PREFIX = "ARCHITECTAI_"

    # Supported config file names
    CONFIG_FILES = ["config.yaml", "config.yml", "config.json", "config.toml"]

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        user_config_dir: Optional[Path] = None,
        project_config_dir: Optional[Path] = None,
        enable_hot_reload: bool = False,
    ):
        """Initialize config loader.

        Args:
            config_path: Path to specific config file (optional)
            user_config_dir: Directory for user config (default: ~/.mike)
            project_config_dir: Directory for project config (default: ./.mike)
            enable_hot_reload: Enable hot-reload on file changes
        """
        # Set config_path first if provided
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = None

        self.user_config_dir = (
            Path(user_config_dir) if user_config_dir else (Path.home() / ".mike")
        )
        self.project_config_dir = (
            Path(project_config_dir) if project_config_dir else (Path.cwd() / ".mike")
        )

        self._settings: Optional[Settings] = None
        self._profile_manager: Optional[ProfileManager] = None
        self._config_files: List[Path] = []
        self._file_timestamps: Dict[Path, float] = {}
        self._hot_reload = enable_hot_reload
        self._reload_thread: Optional[threading.Thread] = None
        self._reload_stop_event = threading.Event()
        self._reload_callbacks: List[callable] = []

    def load(
        self,
        cli_overrides: Optional[Dict[str, Any]] = None,
        profile: Optional[str] = None,
    ) -> Settings:
        """Load configuration from all sources.

        Args:
            cli_overrides: CLI argument overrides
            profile: Profile to apply

        Returns:
            Loaded and merged configuration as a Settings object
        """
        # Start with defaults
        settings_dict: Dict[str, Any] = {}

        # 1. Load specific config file if set
        if self.config_path and self.config_path.exists():
            file_config = self._parse_config_file(self.config_path)
            settings_dict = self._deep_merge(settings_dict, file_config)
            if self.config_path not in self._config_files:
                self._config_files.append(self.config_path)
                self._file_timestamps[self.config_path] = (
                    self.config_path.stat().st_mtime
                )

        # 2. Load user config
        user_config = self._load_user_config()
        if user_config:
            settings_dict = self._deep_merge(settings_dict, user_config)

        # 3. Load project config (overrides user)
        project_config = self._load_project_config()
        if project_config:
            settings_dict = self._deep_merge(settings_dict, project_config)

        # 4. Apply environment variables (overrides files)
        env_config = self._load_env_config()
        if env_config:
            settings_dict = self._deep_merge(settings_dict, env_config)

        # 5. Apply CLI overrides (highest priority)
        if cli_overrides:
            settings_dict = self._deep_merge(settings_dict, cli_overrides)

        # Store settings internally
        self._settings = Settings.model_validate(settings_dict)

        # Apply profile if specified
        if profile:
            self._settings = self._apply_profile(self._settings, profile)
        elif self._settings.profile:
            self._settings = self._apply_profile(self._settings, self._settings.profile)

        # Setup hot-reload if enabled
        if self._hot_reload:
            self._start_hot_reload()

        return self._settings

    def save(self, config: Dict[str, Any]) -> None:
        """Save configuration to file.

        Args:
            config: Configuration dictionary to save

        Raises:
            ConfigLoadError: If config_path is not set or file cannot be written
        """
        if not self.config_path:
            raise ConfigLoadError("Cannot save: config_path is not set")

        # Ensure parent directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Determine format from file extension
        suffix = self.config_path.suffix.lower()

        try:
            if suffix in (".yaml", ".yml"):
                try:
                    import yaml

                    content = yaml.dump(
                        config, default_flow_style=False, sort_keys=False
                    )
                except ImportError:
                    raise ConfigLoadError("PyYAML required for YAML config files")
            elif suffix == ".json":
                content = json.dumps(config, indent=2)
            else:
                # Default to JSON for unknown extensions
                content = json.dumps(config, indent=2)

            self.config_path.write_text(content)

            # Update internal tracking
            if self.config_path not in self._config_files:
                self._config_files.append(self.config_path)
            self._file_timestamps[self.config_path] = self.config_path.stat().st_mtime

        except Exception as e:
            raise ConfigLoadError(f"Failed to save config to {self.config_path}: {e}")

    def _load_user_config(self) -> Optional[Dict[str, Any]]:
        """Load user configuration from ~/.mike/."""
        return self._load_config_from_dir(self.user_config_dir)

    def _load_project_config(self) -> Optional[Dict[str, Any]]:
        """Load project configuration from ./.mike/."""
        return self._load_config_from_dir(self.project_config_dir)

    def _load_config_from_dir(self, directory: Path) -> Optional[Dict[str, Any]]:
        """Load configuration from directory.

        Args:
            directory: Directory to search for config files

        Returns:
            Configuration dictionary or None
        """
        if not directory.exists():
            return None

        for config_file in self.CONFIG_FILES:
            config_path = directory / config_file
            if config_path.exists():
                self._config_files.append(config_path)
                self._file_timestamps[config_path] = config_path.stat().st_mtime
                self.config_path = config_path
                return self._parse_config_file(config_path)

        return None

    def _parse_config_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse a configuration file.

        Args:
            file_path: Path to config file

        Returns:
            Parsed configuration dictionary

        Raises:
            ConfigLoadError: If file cannot be parsed
        """
        suffix = file_path.suffix.lower()
        content = file_path.read_text()

        try:
            if suffix in (".yaml", ".yml"):
                try:
                    import yaml

                    return yaml.safe_load(content) or {}
                except ImportError:
                    raise ConfigLoadError("PyYAML required for YAML config files")
            elif suffix == ".json":
                return json.loads(content)
            elif suffix == ".toml":
                try:
                    import tomllib

                    return tomllib.loads(content)
                except ImportError:
                    try:
                        import tomli

                        return tomli.loads(content)
                    except ImportError:
                        raise ConfigLoadError("tomli required for TOML config files")
            else:
                raise ConfigLoadError(f"Unsupported config file format: {suffix}")
        except Exception as e:
            raise ConfigLoadError(f"Failed to parse {file_path}: {e}")

    def _load_env_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables.

        Environment variables should be prefixed with ARCHITECTAI_
        and use underscores to indicate nesting.

        Examples:
            ARCHITECTAI_DATABASE_PATH=/path/to/db
            ARCHITECTAI_LLM_MODEL=qwen2.5-coder:14b
            ARCHITECTAI_LLM_TEMPERATURE=0.7
            ARCHITECTAI_AGENTS_PARALLEL_AGENTS=5

        Returns:
            Configuration dictionary
        """
        config: Dict[str, Any] = {}

        for key, value in os.environ.items():
            if key.startswith(self.ENV_PREFIX):
                # Remove prefix and convert to nested dict
                config_key = key[len(self.ENV_PREFIX) :].lower()
                nested_keys = config_key.split("_")

                # Convert value to appropriate type
                typed_value = self._convert_env_value(value)

                # Build nested structure
                current = config
                for i, nested_key in enumerate(nested_keys[:-1]):
                    if nested_key not in current:
                        current[nested_key] = {}
                    current = current[nested_key]

                current[nested_keys[-1]] = typed_value

        return config

    def _convert_env_value(
        self, value: str
    ) -> Union[str, int, float, bool, None, Path]:
        """Convert environment variable string to appropriate type.

        Args:
            value: String value from environment

        Returns:
            Converted value
        """
        # Handle explicit null
        if value.lower() in ("null", "none", ""):
            return None

        # Handle booleans
        if value.lower() in ("true", "yes", "1", "on"):
            return True
        if value.lower() in ("false", "no", "0", "off"):
            return False

        # Handle numbers
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # Handle paths (check if it looks like a path)
        if value.startswith("~/") or value.startswith("/") or value.startswith("./"):
            return Path(value)

        # Default to string
        return value

    def _apply_profile(self, settings: Settings, profile_name: str) -> Settings:
        """Apply a profile to settings.

        Args:
            settings: Base settings
            profile_name: Name of profile to apply

        Returns:
            Settings with profile applied
        """
        if self._profile_manager is None:
            profiles_dir = self.user_config_dir / "profiles"
            self._profile_manager = ProfileManager(profiles_dir)

        return self._profile_manager.apply_profile(settings, profile_name)

    def _deep_merge(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge two dictionaries.

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = dict(base)

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def get_current_settings(self) -> Optional[Settings]:
        """Get currently loaded settings.

        Returns:
            Current settings or None if not loaded
        """
        return self._settings

    def reload(self) -> Settings:
        """Reload configuration from files.

        Returns:
            Reloaded configuration as a Settings object

        Raises:
            ConfigLoadError: If not previously loaded
        """
        if self._settings is None:
            raise ConfigLoadError("Cannot reload: no settings previously loaded")

        # Remember profile
        profile = self._settings.profile

        # Reload
        return self.load(profile=profile)

    def _start_hot_reload(self) -> None:
        """Start hot-reload watcher thread."""
        if self._reload_thread is not None:
            return

        self._reload_stop_event.clear()
        self._reload_thread = threading.Thread(target=self._reload_watcher, daemon=True)
        self._reload_thread.start()

    def _stop_hot_reload(self) -> None:
        """Stop hot-reload watcher thread."""
        if self._reload_thread is not None:
            self._reload_stop_event.set()
            self._reload_thread.join(timeout=5.0)
            self._reload_thread = None

    def _reload_watcher(self) -> None:
        """Watch for configuration file changes."""
        while not self._reload_stop_event.is_set():
            time.sleep(2.0)  # Check every 2 seconds

            changed = False
            for file_path, last_mtime in list(self._file_timestamps.items()):
                if not file_path.exists():
                    continue

                current_mtime = file_path.stat().st_mtime
                if current_mtime > last_mtime:
                    self._file_timestamps[file_path] = current_mtime
                    changed = True

            if changed:
                try:
                    new_settings = self.reload()
                    for callback in self._reload_callbacks:
                        try:
                            callback(new_settings)
                        except Exception as e:
                            print(f"Hot-reload callback error: {e}")
                except Exception as e:
                    print(f"Hot-reload error: {e}")

    def add_reload_callback(self, callback: callable) -> None:
        """Add a callback to be called on hot-reload.

        Args:
            callback: Function to call with new settings
        """
        self._reload_callbacks.append(callback)

    def remove_reload_callback(self, callback: callable) -> None:
        """Remove a hot-reload callback.

        Args:
            callback: Function to remove
        """
        if callback in self._reload_callbacks:
            self._reload_callbacks.remove(callback)

    def create_default_config(self, directory: Path, exist_ok: bool = False) -> Path:
        """Create a default configuration file.

        Args:
            directory: Directory to create config in
            exist_ok: If False, raise error if config exists

        Returns:
            Path to created config file

        Raises:
            FileExistsError: If config exists and exist_ok is False
        """
        directory.mkdir(parents=True, exist_ok=True)

        config_path = directory / "config.yaml"
        if config_path.exists() and not exist_ok:
            raise FileExistsError(f"Config file already exists: {config_path}")

        default_config = self._generate_default_config()
        config_path.write_text(default_config)

        return config_path

    def _generate_default_config(self) -> str:
        """Generate default configuration file content."""
        return """# Mike Configuration File
# Documentation: https://github.com/mike/mike/docs/config.md

# Schema version
version: "1"

# Database settings
database:
  # Path to SQLite database file
  path: ~/.mike/mike.db
  # Connection pool size (1-20)
  pool_size: 5
  # Connection timeout in seconds
  timeout: 30.0
  # Echo SQL statements (for debugging)
  echo: false

# LLM settings
llm:
  # Provider: ollama, openai, anthropic, together, local
  provider: ollama
  # Model name (see docs for recommended models)
  model: qwen2.5-coder:14b
  # Custom endpoint URL (optional)
  endpoint: null
  # API key for cloud providers (use env var ARCHITECTAI_LLM_API_KEY instead)
  api_key: null
  # Request timeout in seconds
  timeout: 120.0
  # Maximum retries on failure
  max_retries: 3
  # Delay between retries
  retry_delay: 1.0
  # Sampling temperature (0.0-2.0)
  temperature: 0.7
  # Maximum tokens to generate
  max_tokens: 4096
  # Model context window size
  context_window: 8192
  # Nucleus sampling parameter
  top_p: 0.9
  # Top-k sampling parameter
  top_k: 40

# Embeddings settings
embeddings:
  provider: ollama
  model: mxbai-embed-large
  endpoint: null
  api_key: null
  dimensions: 1024
  batch_size: 32
  timeout: 60.0
  normalize: true

# Agent settings
agents:
  temperature: 0.3
  max_tokens: 2048
  parallel_agents: 3
  use_self_reflection: true
  max_plan_steps: 10
  thresholds:
    min_confidence: 0.7
    max_iterations: 5
    max_suggestions: 10
    similarity_threshold: 0.8
    context_depth: 2

# Scanner settings
scanner:
  max_file_size: 5242880  # 5MB
  ignore_patterns:
    - "*.pyc"
    - "__pycache__"
    - ".git"
    - "node_modules"
    - ".venv"
    - "venv"
  binary_detection: true
  follow_symlinks: false
  respect_gitignore: true
  max_files: 10000

# Path settings
paths:
  cache_dir: ~/.mike/cache
  temp_dir: /tmp/mike
  output_dir: ./mike_output
  vector_store_dir: ~/.mike/vector_store
  sessions_dir: ~/.mike/sessions
  config_dir: ~/.mike

# Logging settings
logging:
  level: INFO
  file: null
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  date_format: "%Y-%m-%d %H:%M:%S"
  max_bytes: 10485760  # 10MB
  backup_count: 5
  json_format: false
  redact_secrets: true

# Active profile (default, fast, thorough, or custom)
profile: null
"""

    def get_config_file_paths(self) -> List[Path]:
        """Get list of loaded configuration file paths.

        Returns:
            List of config file paths
        """
        return list(self._config_files)


def load_config(
    user_config_dir: Optional[Path] = None,
    project_config_dir: Optional[Path] = None,
    cli_overrides: Optional[Dict[str, Any]] = None,
    profile: Optional[str] = None,
) -> Settings:
    """Convenience function to load configuration.

    Args:
        user_config_dir: Directory for user config
        project_config_dir: Directory for project config
        cli_overrides: CLI argument overrides
        profile: Profile to apply

    Returns:
        Loaded configuration as a Settings object
    """
    loader = ConfigLoader(
        user_config_dir=user_config_dir,
        project_config_dir=project_config_dir,
    )
    return loader.load(cli_overrides=cli_overrides, profile=profile)
