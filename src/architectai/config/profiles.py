"""Profile management for ArchitectAI.

Profiles allow users to quickly switch between different configuration presets
optimized for different use cases (fast analysis, thorough analysis, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from architectai.config.settings import (
    AgentsConfig,
    AgentThresholds,
    EmbeddingsConfig,
    LLMConfig,
    ScannerConfig,
    Settings,
)


@dataclass
class Profile:
    """Configuration profile definition."""

    name: str
    description: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    extends: Optional[str] = None

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split(".")
        target = self.config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        target = self.config
        for k in keys:
            if isinstance(target, dict) and k in target:
                target = target[k]
            else:
                return default
        return target

    def merge(self, other_config: Dict[str, Any]) -> None:
        """Merge another config into this profile.

        Args:
            other_config: Configuration dictionary to merge
        """
        for key, value in other_config.items():
            self.config[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        result = {
            "name": self.name,
            **self.config,
        }
        if self.description:
            result["description"] = self.description
        if self.extends:
            result["extends"] = self.extends
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Profile:
        """Create profile from dictionary."""
        config = {
            k: v for k, v in data.items() if k not in ("name", "description", "extends")
        }
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            extends=data.get("extends"),
            config=config,
        )

    @property
    def settings_overrides(self) -> Dict[str, Any]:
        """Backwards compatibility for existing code using settings_overrides."""
        return self.config


class ProfileManager:
    """Manages configuration profiles.

    Provides built-in profiles (default, fast, thorough) and supports
    loading custom profiles from files.
    """

    # Built-in profile definitions
    BUILTIN_PROFILES: Dict[str, Profile] = {
        "default": Profile(
            name="default",
            description="Balanced settings for general use. Good starting point.",
            config={},  # Uses default settings
        ),
        "fast": Profile(
            name="fast",
            description="Optimized for speed. Uses lighter models and smaller chunks.",
            config={
                "llm": {
                    "model": "qwen2.5-coder:7b",
                    "temperature": 0.5,
                    "max_tokens": 2048,
                    "context_window": 4096,
                },
                "embeddings": {
                    "model": "nomic-embed-text",
                    "dimensions": 768,
                    "batch_size": 64,
                },
                "agents": {
                    "temperature": 0.3,
                    "max_tokens": 1024,
                    "parallel_agents": 5,
                    "thresholds": {
                        "min_confidence": 0.6,
                        "max_iterations": 3,
                        "max_suggestions": 5,
                        "similarity_threshold": 0.75,
                        "context_depth": 1,
                    },
                },
                "scanner": {
                    "max_file_size": 1024 * 1024,  # 1MB
                    "max_files": 5000,
                },
            },
        ),
        "thorough": Profile(
            name="thorough",
            description="Deep analysis with comprehensive output. Uses larger models.",
            config={
                "llm": {
                    "model": "qwen2.5-coder:32b",
                    "temperature": 0.2,
                    "max_tokens": 8192,
                    "context_window": 32768,
                    "max_retries": 5,
                },
                "embeddings": {
                    "model": "mxbai-embed-large",
                    "dimensions": 1024,
                    "batch_size": 16,
                },
                "agents": {
                    "temperature": 0.1,
                    "max_tokens": 4096,
                    "parallel_agents": 2,
                    "thresholds": {
                        "min_confidence": 0.85,
                        "max_iterations": 10,
                        "max_suggestions": 20,
                        "similarity_threshold": 0.9,
                        "context_depth": 3,
                    },
                    "use_self_reflection": True,
                    "max_plan_steps": 20,
                },
                "scanner": {
                    "max_file_size": 10 * 1024 * 1024,  # 10MB
                    "max_files": 50000,
                    "respect_gitignore": True,
                },
            },
        ),
    }

    def __init__(self, custom_profiles_dir: Optional[Path] = None):
        """Initialize profile manager.

        Args:
            custom_profiles_dir: Directory to load custom profiles from
        """
        self._profiles: Dict[str, Profile] = dict(self.BUILTIN_PROFILES)
        self._custom_profiles_dir = custom_profiles_dir

        if custom_profiles_dir:
            self._load_custom_profiles(custom_profiles_dir)

    def _load_custom_profiles(self, directory: Path) -> None:
        """Load custom profiles from directory.

        Args:
            directory: Directory containing profile YAML/JSON files
        """
        if not directory.exists():
            return

        for file_path in directory.iterdir():
            if file_path.suffix in (".yaml", ".yml", ".json"):
                try:
                    profile = self._load_profile_file(file_path)
                    self._profiles[profile.name] = profile
                except Exception as e:
                    # Log error but continue loading other profiles
                    print(f"Warning: Failed to load profile from {file_path}: {e}")

    def _load_profile_file(self, file_path: Path) -> Profile:
        """Load a single profile file.

        Args:
            file_path: Path to profile file

        Returns:
            Loaded profile
        """
        import json

        content = file_path.read_text()

        if file_path.suffix in (".yaml", ".yml"):
            try:
                import yaml

                data = yaml.safe_load(content)
            except ImportError:
                raise ImportError("PyYAML required for YAML profile loading")
        else:
            data = json.loads(content)

        return Profile.from_dict(data)

    def list_profiles(self) -> List[Profile]:
        """List all available profiles.

        Returns:
            List of profiles
        """
        return list(self._profiles.values())

    def get_profile(self, name: str) -> Optional[Profile]:
        """Get a profile by name.

        Args:
            name: Profile name

        Returns:
            Profile or None if not found
        """
        return self._profiles.get(name)

    def has_profile(self, name: str) -> bool:
        """Check if a profile exists.

        Args:
            name: Profile name

        Returns:
            True if profile exists
        """
        return name in self._profiles

    def add_profile(self, profile: Profile) -> None:
        """Add a custom profile.

        Args:
            profile: Profile to add

        Raises:
            ValueError: If profile name conflicts with built-in
        """
        if profile.name in self.BUILTIN_PROFILES:
            raise ValueError(f"Cannot override built-in profile: {profile.name}")

        self._profiles[profile.name] = profile

    def remove_profile(self, name: str) -> bool:
        """Remove a custom profile.

        Args:
            name: Profile name to remove

        Returns:
            True if profile was removed, False if not found or built-in
        """
        if name in self.BUILTIN_PROFILES:
            return False

        if name in self._profiles:
            del self._profiles[name]
            return True

        return False

    def apply_profile(self, settings: Settings, profile_name: str) -> Settings:
        """Apply a profile to settings.

        Args:
            settings: Base settings
            profile_name: Name of profile to apply

        Returns:
            New settings with profile applied

        Raises:
            ValueError: If profile not found
        """
        profile = self.get_profile(profile_name)
        if profile is None:
            raise ValueError(f"Profile not found: {profile_name}")

        # Start with current settings as dict
        settings_dict = settings.model_dump()

        # Apply overrides recursively
        settings_dict = self._deep_merge(settings_dict, profile.settings_overrides)

        # Track which profile is active
        settings_dict["profile"] = profile_name

        # Create new settings instance
        return Settings.model_validate(settings_dict)

    def _deep_merge(
        self, base: Dict[str, Any], overrides: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge two dictionaries.

        Args:
            base: Base dictionary
            overrides: Dictionary with override values

        Returns:
            Merged dictionary
        """
        result = dict(base)

        for key, value in overrides.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def create_profile(
        self,
        name: str,
        description: str,
        base_settings: Settings,
        extends: Optional[str] = None,
    ) -> Profile:
        """Create a new profile from current settings.

        Args:
            name: Profile name
            description: Profile description
            base_settings: Settings to derive profile from
            extends: Optional base profile to extend

        Returns:
            Created profile
        """
        # Get base profile overrides if extending
        base_overrides: Dict[str, Any] = {}
        if extends and extends in self._profiles:
            base_overrides = dict(self._profiles[extends].settings_overrides)

        # Convert settings to dict and remove defaults
        settings_dict = base_settings.model_dump()
        default_settings = Settings.default().model_dump()

        # Only include non-default values
        overrides: Dict[str, Any] = {}
        for key, value in settings_dict.items():
            if key in ("version", "profile"):
                continue
            if value != default_settings.get(key):
                overrides[key] = value

        # Merge with base overrides
        if base_overrides:
            overrides = self._deep_merge(base_overrides, overrides)

        profile = Profile(
            name=name,
            description=description,
            extends=extends,
            config=overrides,
        )

        self.add_profile(profile)
        return profile

    def save_profile(self, profile: Profile, directory: Path) -> Path:
        """Save a profile to file.

        Args:
            profile: Profile to save
            directory: Directory to save to

        Returns:
            Path to saved file
        """
        directory.mkdir(parents=True, exist_ok=True)

        file_path = directory / f"{profile.name}.yaml"

        try:
            import yaml

            data = profile.to_dict()
            content = yaml.dump(data, default_flow_style=False, sort_keys=False)
        except ImportError:
            import json

            data = profile.to_dict()
            content = json.dumps(data, indent=2)
            file_path = directory / f"{profile.name}.json"

        file_path.write_text(content)
        return file_path

    def get_profile_descriptions(self) -> Dict[str, str]:
        """Get descriptions for all profiles.

        Returns:
            Dictionary mapping profile names to descriptions
        """
        return {name: profile.description for name, profile in self._profiles.items()}

    def validate_profile(self, profile_name: str) -> tuple[bool, List[str]]:
        """Validate a profile's settings.

        Args:
            profile_name: Name of profile to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        profile = self.get_profile(profile_name)
        if profile is None:
            return False, [f"Profile not found: {profile_name}"]

        errors: List[str] = []

        try:
            # Try to create settings with overrides
            base_settings = Settings.default()
            settings_dict = base_settings.model_dump()
            merged = self._deep_merge(settings_dict, profile.settings_overrides)
            Settings.model_validate(merged)
        except Exception as e:
            errors.append(f"Invalid settings: {e}")

        return len(errors) == 0, errors
