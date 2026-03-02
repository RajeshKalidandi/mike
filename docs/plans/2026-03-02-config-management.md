# Configuration Management System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Build a comprehensive configuration management system for ArchitectAI with Pydantic validation, profiles, and CLI integration.

**Architecture:** Settings management using Pydantic v2 for validation, with hierarchical config loading (defaults → files → env vars → CLI args), profile-based presets, and hot-reload capability.

**Tech Stack:** Pydantic v2, PyYAML, python-dotenv, Click for CLI

---

## Task 1: Core Settings Module

**Files:**
- Create: `src/architectai/config/settings.py`
- Test: `tests/config/test_settings.py`

**Implementation:**
Create comprehensive Settings class with all configuration categories:
- DatabaseConfig (path, pool size, timeout)
- LLMConfig (model names, endpoints, timeouts, retries)
- EmbeddingsConfig (model, dimensions, batch size)
- AgentsConfig (temperature, max tokens, thresholds)
- ScannerConfig (ignore patterns, max file size, binary detection)
- PathsConfig (cache, temp, output directories)
- LoggingConfig (level, file, format)

**Key features:**
- Pydantic v2 BaseSettings with validation
- Sensitive value masking (API keys, passwords)
- JSON Schema generation for documentation
- Type hints throughout

**Step 1:** Write failing test for Settings instantiation
**Step 2:** Run test, verify it fails
**Step 3:** Implement Settings class with all sub-configs
**Step 4:** Run tests, verify they pass
**Step 5:** Commit

---

## Task 2: Profile Management

**Files:**
- Create: `src/architectai/config/profiles.py`
- Test: `tests/config/test_profiles.py`

**Implementation:**
Create profile management system:
- `Profile` dataclass with name, description, settings overrides
- `ProfileManager` class
- Built-in profiles: default, fast, thorough
- Custom profile loading from files
- Profile validation and merging
- Profile switching mechanism

**Built-in profiles:**
- `default`: Balanced settings for general use
- `fast`: Lightweight models, smaller chunks, faster processing
- `thorough`: Deep analysis, larger models, comprehensive output

**Step 1:** Write failing test for profile loading
**Step 2:** Run test, verify it fails
**Step 3:** Implement Profile and ProfileManager
**Step 4:** Run tests, verify they pass
**Step 5:** Commit

---

## Task 3: Configuration Validation

**Files:**
- Create: `src/architectai/config/validation.py`
- Test: `tests/config/test_validation.py`

**Implementation:**
Create validation utilities:
- `ConfigValidator` class
- Path existence checks (directories must exist or be creatable)
- Model availability checks (validate Ollama models exist)
- Threshold validation (ensure values in valid ranges)
- Dependency checks (verify external tools available)
- ValidationResult with detailed error messages

**Validations:**
- Database path is writable
- Model names are valid strings
- Temperature is between 0.0 and 2.0
- Max tokens is positive
- Embedding dimensions match model specs
- Cache directory exists or can be created

**Step 1:** Write failing test for validation
**Step 2:** Run test, verify it fails
**Step 3:** Implement ConfigValidator
**Step 4:** Run tests, verify they pass
**Step 5:** Commit

---

## Task 4: Configuration Loader

**Files:**
- Create: `src/architectai/config/loader.py`
- Test: `tests/config/test_loader.py`

**Implementation:**
Create hierarchical config loading:
- `ConfigLoader` class
- Support YAML, JSON, TOML formats
- Loading precedence: defaults → ~/.architectai/config.yaml → ./.architectai/config.yaml → env vars → CLI args
- Environment variable mapping (ARCHITECTAI_DATABASE_PATH, etc.)
- Deep merging of nested configs
- Hot-reload capability with file watching
- Config migration support (version checking)

**Config file locations:**
- `~/.architectai/config.yaml` - User config
- `./.architectai/config.yaml` - Project config

**Step 1:** Write failing test for config loading
**Step 2:** Run test, verify it fails
**Step 3:** Implement ConfigLoader with all features
**Step 4:** Run tests, verify they pass
**Step 5:** Commit

---

## Task 5: Module Initialization and CLI Integration

**Files:**
- Create: `src/architectai/config/__init__.py`
- Modify: `src/architectai/cli.py` (add config commands)
- Test: `tests/config/test_init.py`

**Implementation:**
Create module exports and CLI commands:
- `__init__.py` with exports (Settings, ProfileManager, ConfigLoader, etc.)
- CLI commands:
  * `architectai config init` - Create default config file
  * `architectai config show` - Display current config
  * `architectai config validate` - Validate config
  * `architectai config set <key> <value>` - Set value
  * `architectai config get <key>` - Get value
  * `architectai config profiles` - List profiles
  * `architectai config use-profile <name>` - Switch profile

**Features:**
- Default config generation with comments
- Config display with sensitive value masking
- Interactive validation with helpful errors
- Profile listing with descriptions

**Step 1:** Write failing test for CLI commands
**Step 2:** Run test, verify it fails
**Step 3:** Implement __init__.py and CLI commands
**Step 4:** Run tests, verify they pass
**Step 5:** Commit

---

## Task 6: Integration and Final Testing

**Files:**
- Create: `tests/config/test_integration.py`
- Modify: `pyproject.toml` (add dependencies)

**Implementation:**
Integration tests and final setup:
- End-to-end config loading test
- Profile switching test
- CLI command integration test
- Add PyYAML and python-dotenv to dependencies
- Verify all tests pass
- Run linting and type checking

**Step 1:** Write integration tests
**Step 2:** Run all tests
**Step 3:** Fix any issues
**Step 4:** Run linting (ruff, mypy)
**Step 5:** Commit

---

## Summary

**Total Tasks:** 6
**Estimated Time:** 2-3 hours
**Deliverables:**
- 5 new Python modules in `src/architectai/config/`
- 6 test files in `tests/config/`
- Updated CLI with 7 config commands
- Updated pyproject.toml

**Dependencies to add:**
- PyYAML >= 6.0
- python-dotenv >= 1.0
- tomli >= 2.0 (for TOML support on Python < 3.11)
