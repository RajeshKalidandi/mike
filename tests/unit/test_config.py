"""Unit tests for Config module."""

import pytest
import os
from unittest.mock import patch

from mike.config.settings import Settings
from mike.config.loader import ConfigLoader
from mike.config.validation import ConfigValidator
from mike.config.profiles import Profile


class TestSettings:
    """Test cases for Settings."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()

        assert settings.debug is False
        assert settings.log_level == "INFO"
        assert settings.embedding_model == "mxbai-embed-large"

    def test_settings_from_env(self):
        """Test loading settings from environment variables."""
        env_vars = {
            "ARCHITECTAI_DEBUG": "true",
            "ARCHITECTAI_LOG_LEVEL": "DEBUG",
            "ARCHITECTAI_EMBEDDING_MODEL": "nomic-embed-text",
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

            assert settings.debug is True
            assert settings.log_level == "DEBUG"
            assert settings.embedding_model == "nomic-embed-text"

    def test_settings_embedding_dimensions(self):
        """Test embedding model dimensions."""
        settings = Settings()

        assert settings.get_embedding_dimension("nomic-embed-text") == 768
        assert settings.get_embedding_dimension("mxbai-embed-large") == 1024
        assert settings.get_embedding_dimension("bge-m3") == 1024

    def test_settings_invalid_embedding_model(self):
        """Test behavior with invalid embedding model."""
        settings = Settings()
        settings.embedding_model = "invalid-model"

        # Should return default dimension
        dim = settings.get_embedding_dimension(settings.embedding_model)
        assert dim == 1024  # Default dimension


class TestConfigLoader:
    """Test cases for ConfigLoader."""

    def test_initialization(self, temp_dir):
        """Test config loader initialization."""
        config_file = temp_dir / "config.json"
        loader = ConfigLoader(str(config_file))

        assert loader.config_path == config_file

    def test_load_nonexistent_config(self, temp_dir):
        """Test loading non-existent config file."""
        config_file = temp_dir / "nonexistent.json"
        loader = ConfigLoader(str(config_file))

        config = loader.load()

        # Should return default config
        assert isinstance(config, dict)

    def test_load_json_config(self, temp_dir):
        """Test loading JSON config file."""
        config_file = temp_dir / "config.json"
        config_file.write_text('{"debug": true, "log_level": "DEBUG"}')

        loader = ConfigLoader(str(config_file))
        config = loader.load()

        assert config["debug"] is True
        assert config["log_level"] == "DEBUG"

    def test_load_yaml_config(self, temp_dir):
        """Test loading YAML config file."""
        yaml = pytest.importorskip("yaml")

        config_file = temp_dir / "config.yaml"
        config_file.write_text("debug: true\nlog_level: DEBUG\n")

        loader = ConfigLoader(str(config_file))
        config = loader.load()

        assert config["debug"] is True
        assert config["log_level"] == "DEBUG"

    def test_save_config(self, temp_dir):
        """Test saving config to file."""
        config_file = temp_dir / "config.json"
        loader = ConfigLoader(str(config_file))

        config = {"debug": True, "custom_key": "value"}
        loader.save(config)

        assert config_file.exists()
        loaded = loader.load()
        assert loaded["debug"] is True
        assert loaded["custom_key"] == "value"


class TestConfigValidator:
    """Test cases for ConfigValidator."""

    def test_validate_valid_config(self):
        """Test validation of valid config."""
        validator = ConfigValidator()

        config = {
            "debug": False,
            "log_level": "INFO",
            "embedding_model": "mxbai-embed-large",
        }

        errors = validator.validate(config)

        assert len(errors) == 0

    def test_validate_invalid_log_level(self):
        """Test validation with invalid log level."""
        validator = ConfigValidator()

        config = {
            "debug": False,
            "log_level": "INVALID",
        }

        errors = validator.validate(config)

        assert any("log_level" in error.lower() for error in errors)

    def test_validate_invalid_embedding_model(self):
        """Test validation with invalid embedding model."""
        validator = ConfigValidator()

        config = {
            "embedding_model": "invalid-model",
        }

        errors = validator.validate(config)

        assert any("embedding" in error.lower() for error in errors)

    def test_validate_missing_required_fields(self):
        """Test validation with missing required fields."""
        validator = ConfigValidator()

        config = {}

        errors = validator.validate(config)

        # Should not error for optional fields
        assert len(errors) == 0

    def test_validate_refactor_config(self):
        """Test validation of refactor agent config."""
        validator = ConfigValidator()

        config = {
            "refactor": {
                "long_function_lines": 50,
                "god_class_methods": 20,
                "deep_nesting_levels": 4,
            }
        }

        errors = validator.validate(config)

        assert len(errors) == 0

    def test_validate_invalid_refactor_thresholds(self):
        """Test validation with invalid refactor thresholds."""
        validator = ConfigValidator()

        config = {
            "refactor": {
                "long_function_lines": -1,  # Invalid: negative
                "god_class_methods": 0,  # Invalid: zero
            }
        }

        errors = validator.validate(config)

        assert len(errors) > 0


class TestProfile:
    """Test cases for Profile."""

    def test_initialization(self):
        """Test profile initialization."""
        profile = Profile("test_profile")

        assert profile.name == "test_profile"
        assert profile.config == {}

    def test_set_get_config(self):
        """Test setting and getting config values."""
        profile = Profile("test")

        profile.set("debug", True)
        profile.set("nested.key", "value")

        assert profile.get("debug") is True
        assert profile.get("nested.key") == "value"
        assert profile.get("nonexistent", "default") == "default"

    def test_merge_config(self):
        """Test merging configs."""
        profile = Profile("test")
        profile.set("key1", "value1")
        profile.set("key2", "value2")

        other_config = {
            "key2": "new_value2",
            "key3": "value3",
        }

        profile.merge(other_config)

        assert profile.get("key1") == "value1"
        assert profile.get("key2") == "new_value2"
        assert profile.get("key3") == "value3"

    def test_to_dict(self):
        """Test converting profile to dictionary."""
        profile = Profile("test")
        profile.set("debug", True)
        profile.set("log_level", "DEBUG")

        config_dict = profile.to_dict()

        assert config_dict["debug"] is True
        assert config_dict["log_level"] == "DEBUG"

    def test_from_dict(self):
        """Test creating profile from dictionary."""
        config_dict = {
            "name": "production",
            "debug": False,
            "log_level": "INFO",
        }

        profile = Profile.from_dict(config_dict)

        assert profile.name == "production"
        assert profile.get("debug") is False
        assert profile.get("log_level") == "INFO"


class TestConfigIntegration:
    """Integration tests for config system."""

    def test_full_config_workflow(self, temp_dir):
        """Test complete config workflow."""
        config_file = temp_dir / "config.yaml"

        # Create config file
        config_file.write_text("""
debug: true
log_level: DEBUG
embedding_model: nomic-embed-text
refactor:
  long_function_lines: 40
  god_class_methods: 15
""")

        # Load config
        loader = ConfigLoader(str(config_file))
        config = loader.load()

        # Validate
        validator = ConfigValidator()
        errors = validator.validate(config)
        assert len(errors) == 0

        # Use with Settings
        settings = Settings()
        settings.update_from_dict(config)

        assert settings.debug is True
        assert settings.log_level == "DEBUG"

    def test_profile_switching(self, temp_dir):
        """Test switching between config profiles."""
        # Create development profile
        dev_profile = Profile("development")
        dev_profile.set("debug", True)
        dev_profile.set("log_level", "DEBUG")

        # Create production profile
        prod_profile = Profile("production")
        prod_profile.set("debug", False)
        prod_profile.set("log_level", "INFO")

        # Switch between profiles
        settings = Settings()

        settings.update_from_dict(dev_profile.to_dict())
        assert settings.debug is True

        settings.update_from_dict(prod_profile.to_dict())
        assert settings.debug is False
