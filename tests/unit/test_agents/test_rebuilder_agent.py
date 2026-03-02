"""Unit tests for Rebuilder Agent."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from architectai.agents.rebuilder_agent import (
    RebuilderAgent,
    ArchitecturePattern,
    ArchitectureTemplate,
    FileSpec,
    BuildPlan,
    BuildPlanStatus,
    GenerationPhase,
)


class TestRebuilderAgent:
    """Test cases for RebuilderAgent."""

    def test_initialization(self):
        """Test agent initialization."""
        agent = RebuilderAgent()

        assert agent.ollama_url == "http://localhost:11434"
        assert agent.model_name == "gemma3:12b"
        assert agent.output_dir.exists()
        assert agent.sandbox_enabled is True

    def test_initialization_with_custom_params(self):
        """Test initialization with custom parameters."""
        agent = RebuilderAgent(
            ollama_url="http://custom:11434",
            model_name="custom-model",
            output_dir="/custom/output",
            sandbox_enabled=False,
        )

        assert agent.ollama_url == "http://custom:11434"
        assert agent.model_name == "custom-model"
        assert agent.sandbox_enabled is False

    def test_detect_languages_python(self, temp_dir):
        """Test language detection for Python."""
        agent = RebuilderAgent()

        # Create Python files
        (temp_dir / "main.py").write_text("pass")
        (temp_dir / "utils.py").write_text("pass")
        (temp_dir / "test.py").write_text("pass")

        languages = agent._detect_languages(temp_dir)

        assert "python" in languages

    def test_detect_languages_javascript(self, temp_dir):
        """Test language detection for JavaScript."""
        agent = RebuilderAgent()

        # Create JavaScript files
        (temp_dir / "index.js").write_text("const x = 1;")
        (temp_dir / "app.js").write_text("const y = 2;")

        languages = agent._detect_languages(temp_dir)

        assert "javascript" in languages

    def test_detect_languages_multiple(self, temp_dir):
        """Test detection of multiple languages."""
        agent = RebuilderAgent()

        # Create files in multiple languages
        (temp_dir / "main.py").write_text("pass")
        (temp_dir / "index.js").write_text("const x = 1;")
        (temp_dir / "main.go").write_text("package main")
        (temp_dir / "lib.rs").write_text("fn main() {}")

        languages = agent._detect_languages(temp_dir)

        assert "python" in languages
        assert "javascript" in languages
        assert "go" in languages
        assert "rust" in languages

    def test_detect_frameworks_fastapi(self, temp_dir):
        """Test FastAPI framework detection."""
        agent = RebuilderAgent()

        # Create Python files with FastAPI imports
        (temp_dir / "main.py").write_text("from fastapi import FastAPI")

        frameworks = agent._detect_frameworks(temp_dir, ["python"])

        assert "fastapi" in frameworks

    def test_detect_frameworks_flask(self, temp_dir):
        """Test Flask framework detection."""
        agent = RebuilderAgent()

        # Create Python files with Flask imports
        (temp_dir / "app.py").write_text("from flask import Flask")

        frameworks = agent._detect_frameworks(temp_dir, ["python"])

        assert "flask" in frameworks

    def test_analyze_directory_structure(self, temp_dir):
        """Test directory structure analysis."""
        agent = RebuilderAgent()

        # Create structure
        (temp_dir / "src").mkdir()
        (temp_dir / "tests").mkdir()
        (temp_dir / "docs").mkdir()
        (temp_dir / "config").mkdir()
        (temp_dir / "README.md").write_text("# Test")

        structure = agent._analyze_directory_structure(temp_dir)

        assert "src" in structure["source_dirs"]
        assert "tests" in structure["test_dirs"]
        assert "docs" in structure["docs_dirs"]
        assert "config" in structure["config_dirs"]
        assert "README.md" in structure["root_files"]

    def test_detect_patterns_mvc(self, temp_dir):
        """Test MVC pattern detection."""
        agent = RebuilderAgent()

        # Create MVC structure
        (temp_dir / "models").mkdir()
        (temp_dir / "views").mkdir()
        (temp_dir / "controllers").mkdir()

        patterns = agent._detect_patterns(temp_dir, ["python"], [], None)

        pattern_types = [p.pattern_type for p in patterns]
        assert "mvc" in pattern_types

    def test_detect_patterns_layered(self, temp_dir):
        """Test layered architecture detection."""
        agent = RebuilderAgent()

        # Create layered structure
        (temp_dir / "services").mkdir()
        (temp_dir / "repositories").mkdir()
        (temp_dir / "dto").mkdir()

        patterns = agent._detect_patterns(temp_dir, ["python"], [], None)

        pattern_types = [p.pattern_type for p in patterns]
        assert "layered" in pattern_types

    def test_find_entry_points_python(self, temp_dir):
        """Test finding Python entry points."""
        agent = RebuilderAgent()

        # Create entry point files
        (temp_dir / "main.py").write_text('if __name__ == "__main__": pass')
        (temp_dir / "cli.py").write_text("import click")

        entry_points = agent._find_entry_points(temp_dir, ["python"])

        assert "main.py" in entry_points

    def test_find_entry_points_javascript(self, temp_dir):
        """Test finding JavaScript entry points."""
        agent = RebuilderAgent()

        # Create entry point files
        (temp_dir / "index.js").write_text("const x = 1;")
        (temp_dir / "main.js").write_text("console.log('main');")

        entry_points = agent._find_entry_points(temp_dir, ["javascript"])

        assert "index.js" in entry_points

    def test_generate_build_plan(self):
        """Test build plan generation."""
        agent = RebuilderAgent()

        template = ArchitectureTemplate(
            source_repo="/test/repo",
            languages=["python"],
            frameworks=["fastapi"],
            patterns=[],
            directory_structure={},
            dependencies={},
            file_templates={},
            config_patterns={},
            entry_points=["main.py"],
            tests_structure=None,
            documentation_structure=None,
        )

        plan = agent.generate_build_plan(
            template=template,
            project_name="test-project",
            description="A test project",
            constraints=["multi-tenant"],
        )

        assert plan.project_name == "test-project"
        assert plan.description == "A test project"
        assert plan.target_language == "python"
        assert plan.target_framework == "fastapi"
        assert len(plan.files) > 0
        assert plan.status == BuildPlanStatus.DRAFT

    def test_generate_python_file_specs(self):
        """Test Python file spec generation."""
        agent = RebuilderAgent()

        template = ArchitectureTemplate(
            source_repo="/test/repo",
            languages=["python"],
            frameworks=[],
            patterns=[],
            directory_structure={},
            dependencies={},
            file_templates={},
            config_patterns={},
            entry_points=[],
            tests_structure=None,
            documentation_structure=None,
        )

        files = agent._generate_python_file_specs(template, "fastapi", None, [])

        file_paths = [f.path for f in files]
        assert "README.md" in file_paths
        assert any("main.py" in fp or "app.py" in fp for fp in file_paths)
        assert "pyproject.toml" in file_paths or "requirements.txt" in file_paths

    def test_generate_multitenant_files(self):
        """Test multi-tenant file generation."""
        agent = RebuilderAgent()

        files = agent._generate_multitenant_files("python")

        file_paths = [f.path for f in files]
        assert any("tenant" in fp for fp in file_paths)

    def test_select_primary_pattern(self):
        """Test primary pattern selection."""
        agent = RebuilderAgent()

        mvc_pattern = ArchitecturePattern(
            pattern_type="mvc",
            confidence=0.8,
            components=[],
            description="",
            files_involved=[],
            relationships={},
        )

        template = ArchitectureTemplate(
            source_repo="/test/repo",
            languages=["python"],
            frameworks=[],
            patterns=[mvc_pattern],
            directory_structure={},
            dependencies={},
            file_templates={},
            config_patterns={},
            entry_points=[],
            tests_structure=None,
            documentation_structure=None,
        )

        pattern = agent._select_primary_pattern(template, ["use mvc pattern"])

        assert pattern.pattern_type == "mvc"

    def test_sanitize_template(self):
        """Test template sanitization."""
        agent = RebuilderAgent()

        content = """
API_KEY = "secret123"
password = "mypassword"
normal_code = "safe"
"""

        sanitized = agent._sanitize_template(content)

        assert "API_KEY" not in sanitized
        assert "password" not in sanitized
        assert "normal_code" in sanitized


class TestFileSpec:
    """Test cases for FileSpec dataclass."""

    def test_initialization(self):
        """Test FileSpec initialization."""
        spec = FileSpec(
            path="src/main.py",
            purpose="Main module",
            dependencies=[],
            estimated_lines=100,
            template_hints={},
        )

        assert spec.path == "src/main.py"
        assert spec.status == "pending"
        assert spec.content is None


class TestBuildPlan:
    """Test cases for BuildPlan dataclass."""

    def test_initialization(self):
        """Test BuildPlan initialization."""
        plan = BuildPlan(
            plan_id="test-123",
            project_name="Test Project",
            description="A test project",
            target_language="python",
            target_framework=None,
            architecture_pattern="generic",
            constraints=[],
            modifications=[],
            files=[],
            dependencies={},
            config_requirements={},
            testing_strategy={},
            documentation_plan={},
            status=BuildPlanStatus.DRAFT,
            created_at="2026-01-01T00:00:00",
        )

        assert plan.plan_id == "test-123"
        assert plan.status == BuildPlanStatus.DRAFT
        assert plan.approved_at is None


class TestBuildPlanStatus:
    """Test cases for BuildPlanStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert BuildPlanStatus.DRAFT.value == "draft"
        assert BuildPlanStatus.APPROVED.value == "approved"
        assert BuildPlanStatus.IN_PROGRESS.value == "in_progress"
        assert BuildPlanStatus.COMPLETED.value == "completed"
        assert BuildPlanStatus.FAILED.value == "failed"


class TestGenerationPhase:
    """Test cases for GenerationPhase enum."""

    def test_phase_values(self):
        """Test phase enum values."""
        assert (
            GenerationPhase.ARCHITECTURE_EXTRACTION.value == "architecture_extraction"
        )
        assert GenerationPhase.PLAN_GENERATION.value == "plan_generation"
        assert GenerationPhase.SCAFFOLDING.value == "scaffolding"
        assert GenerationPhase.CODE_GENERATION.value == "code_generation"
