"""Rebuilder Agent for ArchitectAI.

This agent generates new software inspired by analyzed codebases.
It uses architecture templates from analyzed code and creates new projects
based on user constraints.

M8: Full Rebuilder Agent - Complete implementation with:
- Architecture extraction
- Build plan generation
- Project scaffolding
- Code generation
- Self-review
- Constraint application
"""

import json
import os
import re
import subprocess
import tempfile
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import logging
import sys

from .scaffolder import ProjectScaffolder, ScaffoldingConfig
from .code_generator import CodeGenerator, GenerationConfig


logger = logging.getLogger(__name__)


class BuildPlanStatus(Enum):
    """Status of a build plan."""

    DRAFT = "draft"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationPhase(Enum):
    """Phases of the generation process."""

    ARCHITECTURE_EXTRACTION = "architecture_extraction"
    PLAN_GENERATION = "plan_generation"
    HUMAN_REVIEW = "human_review"
    SCAFFOLDING = "scaffolding"
    CODE_GENERATION = "code_generation"
    SELF_REVIEW = "self_review"
    COMPLETION = "completion"


@dataclass
class ArchitecturePattern:
    """Represents a detected architectural pattern."""

    pattern_type: str  # e.g., 'mvc', 'layered', 'microservices', 'cli'
    confidence: float  # 0.0 to 1.0
    components: List[str]
    description: str
    files_involved: List[str]
    relationships: Dict[str, List[str]]  # component -> list of related components


@dataclass
class ArchitectureTemplate:
    """Template extracted from analyzed codebase."""

    source_repo: str
    languages: List[str]
    frameworks: List[str]
    patterns: List[ArchitecturePattern]
    directory_structure: Dict[str, Any]
    dependencies: Dict[str, List[str]]
    file_templates: Dict[str, str]
    config_patterns: Dict[str, Any]
    entry_points: List[str]
    tests_structure: Optional[Dict[str, Any]]
    documentation_structure: Optional[Dict[str, Any]]


@dataclass
class FileSpec:
    """Specification for a file to be generated."""

    path: str
    purpose: str
    dependencies: List[str]
    estimated_lines: int
    template_hints: Dict[str, Any]
    content: Optional[str] = None
    status: str = "pending"  # pending, generating, completed, failed


@dataclass
class BuildPlan:
    """Structured plan for building a new project."""

    plan_id: str
    project_name: str
    description: str
    target_language: str
    target_framework: Optional[str]
    architecture_pattern: str
    constraints: List[str]
    modifications: List[str]
    files: List[FileSpec]
    dependencies: Dict[str, Any]
    config_requirements: Dict[str, Any]
    testing_strategy: Dict[str, Any]
    documentation_plan: Dict[str, Any]
    status: BuildPlanStatus
    created_at: str
    approved_at: Optional[str] = None
    completed_at: Optional[str] = None
    ambiguities: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ReviewResult:
    """Result of self-review process."""

    passed: bool
    issues: List[Dict[str, Any]]
    suggestions: List[str]
    coverage_score: float  # 0.0 to 1.0
    missing_files: List[str]
    extra_files: List[str]


@dataclass
class GenerationProgress:
    """Tracks progress of code generation."""

    current_phase: GenerationPhase
    total_files: int
    completed_files: int
    failed_files: int
    current_file: Optional[str]
    phase_progress: float  # 0.0 to 1.0
    messages: List[str]
    errors: List[str]


class RebuilderAgent:
    """
    Agent for rebuilding/generating new software from architecture templates.

    This agent:
    1. Extracts architecture patterns from analyzed codebases
    2. Generates structured build plans with human approval checkpoints
    3. Scaffolds project structures
    4. Generates code file by file using local LLMs
    5. Performs self-review against the plan
    6. Flags ambiguities for human review

    All operations work 100% offline with local models via Ollama.
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model_name: str = "gemma3:12b",
        output_dir: str = "./generated_projects",
        sandbox_enabled: bool = True,
        max_context_tokens: int = 32768,
        temperature: float = 0.7,
    ):
        """
        Initialize the Rebuilder Agent.

        Args:
            ollama_url: URL for Ollama API
            model_name: Name of the local model to use
            output_dir: Directory for generated projects
            sandbox_enabled: Whether to use sandboxed execution
            max_context_tokens: Maximum tokens for model context
            temperature: Sampling temperature for generation
        """
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sandbox_enabled = sandbox_enabled
        self.max_context_tokens = max_context_tokens
        self.temperature = temperature

        # Initialize sub-components
        self.scaffolder = ProjectScaffolder()
        self.code_generator = CodeGenerator(
            ollama_url=ollama_url,
            model_name=model_name,
            max_tokens=max_context_tokens,
            temperature=temperature,
        )

        # State management
        self.current_plan: Optional[BuildPlan] = None
        self.current_template: Optional[ArchitectureTemplate] = None
        self.progress: Optional[GenerationProgress] = None
        self.generated_files: Dict[str, str] = {}

        logger.info(f"RebuilderAgent initialized with model: {model_name}")

    def extract_architecture_template(
        self,
        codebase_path: str,
        dependency_graph: Optional[Dict] = None,
        semantic_chunks: Optional[List[Dict]] = None,
    ) -> ArchitectureTemplate:
        """
        Extract architecture template from analyzed codebase.

        Analyzes the structure, patterns, and relationships in the source
        codebase to create a reusable template for generating similar projects.

        Args:
            codebase_path: Path to the analyzed codebase
            dependency_graph: Optional dependency graph from prior analysis
            semantic_chunks: Optional semantic chunks from prior analysis

        Returns:
            ArchitectureTemplate containing extracted patterns
        """
        logger.info(f"Extracting architecture template from: {codebase_path}")

        codebase_path = Path(codebase_path)
        if not codebase_path.exists():
            raise ValueError(f"Codebase path does not exist: {codebase_path}")

        # Detect languages
        languages = self._detect_languages(codebase_path)
        logger.info(f"Detected languages: {languages}")

        # Detect frameworks
        frameworks = self._detect_frameworks(codebase_path, languages)
        logger.info(f"Detected frameworks: {frameworks}")

        # Analyze directory structure
        directory_structure = self._analyze_directory_structure(codebase_path)

        # Detect architectural patterns
        patterns = self._detect_patterns(
            codebase_path, languages, frameworks, dependency_graph
        )

        # Extract dependency patterns
        dependencies = self._extract_dependencies(codebase_path, languages)

        # Identify file templates
        file_templates = self._extract_file_templates(codebase_path, languages)

        # Detect configuration patterns
        config_patterns = self._extract_config_patterns(codebase_path, frameworks)

        # Find entry points
        entry_points = self._find_entry_points(codebase_path, languages)

        # Analyze test structure
        tests_structure = self._analyze_tests_structure(codebase_path)

        # Analyze documentation structure
        documentation_structure = self._analyze_documentation_structure(codebase_path)

        template = ArchitectureTemplate(
            source_repo=str(codebase_path),
            languages=languages,
            frameworks=frameworks,
            patterns=patterns,
            directory_structure=directory_structure,
            dependencies=dependencies,
            file_templates=file_templates,
            config_patterns=config_patterns,
            entry_points=entry_points,
            tests_structure=tests_structure,
            documentation_structure=documentation_structure,
        )

        self.current_template = template
        logger.info(
            f"Successfully extracted architecture template with {len(patterns)} patterns"
        )

        return template

    def _detect_languages(self, codebase_path: Path) -> List[str]:
        """Detect programming languages used in the codebase."""
        language_extensions = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".rb": "ruby",
            ".php": "php",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
        }

        language_counts: Dict[str, int] = {}

        for file_path in codebase_path.rglob("*"):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in language_extensions:
                    lang = language_extensions[ext]
                    language_counts[lang] = language_counts.get(lang, 0) + 1

        # Sort by count and return languages with more than 5 files
        sorted_languages = sorted(
            language_counts.items(), key=lambda x: x[1], reverse=True
        )

        return [lang for lang, count in sorted_languages if count >= 5]

    def _detect_frameworks(
        self, codebase_path: Path, languages: List[str]
    ) -> List[str]:
        """Detect frameworks used based on config files and imports."""
        frameworks = []

        framework_indicators = {
            "python": {
                "fastapi": ["fastapi", "FastAPI"],
                "flask": ["flask", "Flask"],
                "django": ["django", "Django"],
                "pytest": ["pytest", "conftest.py"],
                "pydantic": ["pydantic"],
                "sqlalchemy": ["sqlalchemy"],
            },
            "javascript": {
                "express": ["express"],
                "react": ["react", "React"],
                "vue": ["vue", "Vue"],
                "angular": ["@angular"],
                "next": ["next"],
            },
            "typescript": {
                "express": ["express"],
                "react": ["react", "React"],
                "vue": ["vue", "Vue"],
                "angular": ["@angular"],
                "next": ["next"],
                "nestjs": ["@nestjs"],
            },
            "go": {
                "gin": ["gin-gonic/gin"],
                "echo": ["labstack/echo"],
                "fiber": ["gofiber/fiber"],
            },
        }

        for language in languages:
            if language in framework_indicators:
                for framework, indicators in framework_indicators[language].items():
                    for file_path in codebase_path.rglob("*"):
                        if (
                            file_path.is_file()
                            and file_path.stat().st_size < 1024 * 1024
                        ):
                            try:
                                with open(
                                    file_path, "r", encoding="utf-8", errors="ignore"
                                ) as f:
                                    content = f.read()
                                    for indicator in indicators:
                                        if indicator in content:
                                            if framework not in frameworks:
                                                frameworks.append(framework)
                                            break
                            except:
                                continue

        # Check for config files
        config_files = {
            "package.json": ["javascript", "typescript"],
            "requirements.txt": ["python"],
            "pyproject.toml": ["python"],
            "setup.py": ["python"],
            "go.mod": ["go"],
            "Cargo.toml": ["rust"],
            "pom.xml": ["java"],
            "build.gradle": ["java"],
        }

        for config_file, langs in config_files.items():
            if any((codebase_path / config_file).exists() for _ in [1]):
                if not any(l in languages for l in langs):
                    languages.extend(langs)

        return frameworks

    def _analyze_directory_structure(self, codebase_path: Path) -> Dict[str, Any]:
        """Analyze and extract directory structure patterns."""
        structure = {
            "root_files": [],
            "source_dirs": [],
            "test_dirs": [],
            "config_dirs": [],
            "docs_dirs": [],
            "depth_analysis": {},
        }

        test_patterns = {"test", "tests", "__tests__", "spec", "specs"}
        config_patterns = {"config", "configuration", "settings", "conf"}
        docs_patterns = {"docs", "documentation", "doc", "wiki"}

        for item in codebase_path.iterdir():
            if item.is_file():
                structure["root_files"].append(item.name)
            elif item.is_dir():
                dir_name = item.name.lower()
                if any(p in dir_name for p in test_patterns):
                    structure["test_dirs"].append(item.name)
                elif any(p in dir_name for p in config_patterns):
                    structure["config_dirs"].append(item.name)
                elif any(p in dir_name for p in docs_patterns):
                    structure["docs_dirs"].append(item.name)
                elif not dir_name.startswith(".") and dir_name not in {
                    "node_modules",
                    "__pycache__",
                    "venv",
                    ".git",
                }:
                    structure["source_dirs"].append(item.name)

        # Analyze depth
        max_depth = 0
        dir_depths = []

        for root, dirs, files in os.walk(codebase_path):
            depth = root.replace(str(codebase_path), "").count(os.sep)
            max_depth = max(max_depth, depth)
            dir_depths.append(depth)

        if dir_depths:
            structure["depth_analysis"] = {
                "max_depth": max_depth,
                "avg_depth": sum(dir_depths) / len(dir_depths),
            }

        return structure

    def _detect_patterns(
        self,
        codebase_path: Path,
        languages: List[str],
        frameworks: List[str],
        dependency_graph: Optional[Dict] = None,
    ) -> List[ArchitecturePattern]:
        """Detect architectural patterns in the codebase."""
        patterns = []

        # Pattern detection heuristics
        pattern_indicators = {
            "mvc": {
                "indicators": [
                    "model",
                    "view",
                    "controller",
                    "models",
                    "views",
                    "controllers",
                ],
                "files": ["*.model.*", "*.view.*", "*.controller.*"],
            },
            "layered": {
                "indicators": [
                    "service",
                    "repository",
                    "dao",
                    "dto",
                    "entity",
                    "domain",
                ],
                "files": ["*service*", "*repository*", "*dao*"],
            },
            "microservices": {
                "indicators": ["service", "gateway", "registry", "config-server"],
                "files": ["docker-compose*.yml", "k8s/", "kubernetes/"],
            },
            "cli": {
                "indicators": ["cli", "command", "argparse", "click", "typer", "cobra"],
                "files": ["cli.py", "main.py", "cmd/"],
            },
            "api": {
                "indicators": ["api", "endpoint", "route", "handler"],
                "files": ["routes*", "endpoints*", "api*"],
            },
            "event_driven": {
                "indicators": ["event", "listener", "handler", "queue", "pubsub"],
                "files": ["*event*", "*listener*", "*handler*"],
            },
        }

        for pattern_name, pattern_info in pattern_indicators.items():
            score = 0
            components = []
            files_involved = []

            # Check directory indicators
            for indicator in pattern_info["indicators"]:
                for dir_path in codebase_path.rglob("*"):
                    if dir_path.is_dir() and indicator in dir_path.name.lower():
                        score += 1
                        components.append(dir_path.name)

            # Check file patterns
            for file_pattern in pattern_info["files"]:
                matches = list(codebase_path.rglob(file_pattern))
                if matches:
                    score += len(matches)
                    files_involved.extend(
                        [str(m.relative_to(codebase_path)) for m in matches]
                    )

            if score > 0:
                confidence = min(score / 10, 1.0)
                patterns.append(
                    ArchitecturePattern(
                        pattern_type=pattern_name,
                        confidence=confidence,
                        components=list(set(components)),
                        description=f"Detected {pattern_name} architectural pattern",
                        files_involved=list(set(files_involved))[
                            :20
                        ],  # Limit to 20 files
                        relationships={},
                    )
                )

        # Sort by confidence
        patterns.sort(key=lambda x: x.confidence, reverse=True)

        return patterns

    def _extract_dependencies(
        self, codebase_path: Path, languages: List[str]
    ) -> Dict[str, List[str]]:
        """Extract dependency patterns from the codebase."""
        dependencies = {
            "production": [],
            "development": [],
            "peer": [],
        }

        # Python dependencies
        if "python" in languages:
            req_file = codebase_path / "requirements.txt"
            if req_file.exists():
                with open(req_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            dep = line.split("==")[0].split(">=")[0].split("<=")[0]
                            dependencies["production"].append(dep)

            pyproject_file = codebase_path / "pyproject.toml"
            if pyproject_file.exists():
                try:
                    import tomllib

                    with open(pyproject_file, "rb") as f:
                        pyproject = tomllib.load(f)
                        if (
                            "project" in pyproject
                            and "dependencies" in pyproject["project"]
                        ):
                            dependencies["production"].extend(
                                pyproject["project"]["dependencies"]
                            )
                        if (
                            "project" in pyproject
                            and "optional-dependencies" in pyproject["project"]
                        ):
                            for opt_deps in pyproject["project"][
                                "optional-dependencies"
                            ].values():
                                dependencies["development"].extend(opt_deps)
                except:
                    pass

        # JavaScript/TypeScript dependencies
        if "javascript" in languages or "typescript" in languages:
            package_file = codebase_path / "package.json"
            if package_file.exists():
                try:
                    with open(package_file, "r") as f:
                        package = json.load(f)
                        if "dependencies" in package:
                            dependencies["production"].extend(
                                list(package["dependencies"].keys())
                            )
                        if "devDependencies" in package:
                            dependencies["development"].extend(
                                list(package["devDependencies"].keys())
                            )
                        if "peerDependencies" in package:
                            dependencies["peer"].extend(
                                list(package["peerDependencies"].keys())
                            )
                except:
                    pass

        # Go dependencies
        if "go" in languages:
            go_mod_file = codebase_path / "go.mod"
            if go_mod_file.exists():
                with open(go_mod_file, "r") as f:
                    content = f.read()
                    # Extract module names from go.mod
                    import re

                    modules = re.findall(r"^\t([^\s]+)", content, re.MULTILINE)
                    dependencies["production"].extend(modules)

        return dependencies

    def _extract_file_templates(
        self, codebase_path: Path, languages: List[str]
    ) -> Dict[str, str]:
        """Extract reusable file templates from the codebase."""
        templates = {}

        # Find representative files for each language
        for language in languages:
            lang_files = []

            if language == "python":
                lang_files = list(codebase_path.rglob("*.py"))
            elif language == "javascript":
                lang_files = list(codebase_path.rglob("*.js"))
            elif language == "typescript":
                lang_files = list(codebase_path.rglob("*.ts"))
            elif language == "go":
                lang_files = list(codebase_path.rglob("*.go"))

            # Find a good representative file (not too small, not too large)
            for file_path in lang_files[:20]:  # Check first 20 files
                try:
                    stat = file_path.stat()
                    if 100 < stat.st_size < 5000:  # Between 100 bytes and 5KB
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            # Remove specific identifiers
                            content = self._sanitize_template(content)
                            templates[f"{language}_example"] = content
                            break
                except:
                    continue

        return templates

    def _sanitize_template(self, content: str) -> str:
        """Sanitize template content by removing project-specific identifiers."""
        # This is a simplified version - in production, use more sophisticated sanitization
        lines = content.split("\n")
        sanitized_lines = []

        for line in lines:
            # Skip lines that might contain sensitive info
            if any(
                keyword in line.lower()
                for keyword in ["password", "secret", "key", "token", "api_key"]
            ):
                continue
            sanitized_lines.append(line)

        return "\n".join(sanitized_lines)

    def _extract_config_patterns(
        self, codebase_path: Path, frameworks: List[str]
    ) -> Dict[str, Any]:
        """Extract configuration patterns from the codebase."""
        config_patterns = {}

        # Check for common config files
        config_files = {
            ".env": "env",
            ".env.example": "env_example",
            "config.yaml": "yaml",
            "config.yml": "yaml",
            "config.json": "json",
            "config.toml": "toml",
            "setup.cfg": "cfg",
            "tox.ini": "tox",
            "pytest.ini": "pytest",
        }

        for config_file, config_type in config_files.items():
            config_path = codebase_path / config_file
            if config_path.exists():
                try:
                    with open(config_path, "r") as f:
                        content = f.read()
                        config_patterns[config_type] = {
                            "filename": config_file,
                            "content": content[:1000],  # First 1000 chars
                            "exists": True,
                        }
                except:
                    config_patterns[config_type] = {"exists": True}

        # Framework-specific configs
        if "fastapi" in frameworks:
            config_patterns["fastapi"] = {
                "app_location": self._find_fastapi_app(codebase_path),
            }

        if "flask" in frameworks:
            config_patterns["flask"] = {
                "app_location": self._find_flask_app(codebase_path),
            }

        return config_patterns

    def _find_fastapi_app(self, codebase_path: Path) -> Optional[str]:
        """Find FastAPI application entry point."""
        for py_file in codebase_path.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "FastAPI(" in content and "__name__" in content:
                        return str(py_file.relative_to(codebase_path))
            except:
                continue
        return None

    def _find_flask_app(self, codebase_path: Path) -> Optional[str]:
        """Find Flask application entry point."""
        for py_file in codebase_path.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "Flask(" in content and "__name__" in content:
                        return str(py_file.relative_to(codebase_path))
            except:
                continue
        return None

    def _find_entry_points(
        self, codebase_path: Path, languages: List[str]
    ) -> List[str]:
        """Find entry points in the codebase."""
        entry_points = []

        for language in languages:
            if language == "python":
                # Check for main files
                for main_pattern in [
                    "main.py",
                    "app.py",
                    "run.py",
                    "__main__.py",
                    "cli.py",
                ]:
                    main_file = codebase_path / main_pattern
                    if main_file.exists():
                        entry_points.append(str(main_file.relative_to(codebase_path)))

                # Check for if __name__ == "__main__"
                for py_file in codebase_path.rglob("*.py"):
                    try:
                        with open(py_file, "r", encoding="utf-8") as f:
                            content = f.read()
                            if "__name__" in content and "__main__" in content:
                                rel_path = str(py_file.relative_to(codebase_path))
                                if rel_path not in entry_points:
                                    entry_points.append(rel_path)
                    except:
                        continue

            elif language in ["javascript", "typescript"]:
                for main_pattern in [
                    "index.js",
                    "index.ts",
                    "main.js",
                    "main.ts",
                    "app.js",
                    "app.ts",
                ]:
                    main_file = codebase_path / main_pattern
                    if main_file.exists():
                        entry_points.append(str(main_file.relative_to(codebase_path)))

        return entry_points[:10]  # Limit to 10 entry points

    def _analyze_tests_structure(self, codebase_path: Path) -> Optional[Dict[str, Any]]:
        """Analyze the test structure of the codebase."""
        test_dirs = []
        test_frameworks = []
        test_files = []

        test_patterns = ["test", "tests", "__tests__", "spec", "specs"]

        for test_pattern in test_patterns:
            for dir_path in codebase_path.rglob(test_pattern):
                if dir_path.is_dir():
                    test_dirs.append(str(dir_path.relative_to(codebase_path)))

        # Detect test frameworks
        for py_file in codebase_path.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "import pytest" in content or "from pytest" in content:
                        if "pytest" not in test_frameworks:
                            test_frameworks.append("pytest")
                    if "import unittest" in content:
                        if "unittest" not in test_frameworks:
                            test_frameworks.append("unittest")
            except:
                continue

        if test_dirs or test_frameworks:
            return {
                "test_dirs": test_dirs,
                "test_frameworks": test_frameworks,
                "test_files_count": len(test_files),
            }
        return None

    def _analyze_documentation_structure(
        self, codebase_path: Path
    ) -> Optional[Dict[str, Any]]:
        """Analyze the documentation structure of the codebase."""
        docs_dirs = []
        doc_files = []

        doc_patterns = ["docs", "documentation", "doc"]

        for doc_pattern in doc_patterns:
            for dir_path in codebase_path.rglob(doc_pattern):
                if dir_path.is_dir():
                    docs_dirs.append(str(dir_path.relative_to(codebase_path)))

        # Look for common doc files
        for doc_file in [
            "README.md",
            "README.rst",
            "CONTRIBUTING.md",
            "CHANGELOG.md",
            "LICENSE",
        ]:
            doc_path = codebase_path / doc_file
            if doc_path.exists():
                doc_files.append(doc_file)

        if docs_dirs or doc_files:
            return {
                "docs_dirs": docs_dirs,
                "doc_files": doc_files,
            }
        return None

    def generate_build_plan(
        self,
        template: ArchitectureTemplate,
        project_name: str,
        description: str,
        constraints: List[str],
        target_language: Optional[str] = None,
        target_framework: Optional[str] = None,
    ) -> BuildPlan:
        """
        Generate a structured build plan based on architecture template.

        Creates a comprehensive plan for building a new project, incorporating
        user constraints and modifications to the original architecture.

        Args:
            template: Architecture template extracted from source
            project_name: Name for the new project
            description: Description of the new project
            constraints: List of constraints to apply (e.g., "multi-tenant")
            target_language: Target language (defaults to template primary)
            target_framework: Target framework (defaults to template primary)

        Returns:
            BuildPlan containing detailed generation specifications
        """
        logger.info(f"Generating build plan for project: {project_name}")

        # Determine target language and framework
        if target_language is None:
            target_language = template.languages[0] if template.languages else "python"

        if target_framework is None:
            target_framework = template.frameworks[0] if template.frameworks else None

        # Select primary architecture pattern
        primary_pattern = self._select_primary_pattern(template, constraints)

        # Generate plan ID
        plan_id = hashlib.md5(
            f"{project_name}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        # Create file specifications
        files = self._generate_file_specs(
            template,
            target_language,
            target_framework,
            primary_pattern,
            constraints,
        )

        # Determine dependencies
        dependencies = self._determine_dependencies(
            target_language,
            target_framework,
            constraints,
        )

        # Generate config requirements
        config_requirements = self._generate_config_requirements(
            target_language,
            target_framework,
            constraints,
        )

        # Plan testing strategy
        testing_strategy = self._plan_testing_strategy(
            target_language,
            target_framework,
            template.tests_structure,
        )

        # Plan documentation
        documentation_plan = self._plan_documentation(
            template.documentation_structure,
        )

        # Identify ambiguities
        ambiguities = self._identify_ambiguities(
            template,
            constraints,
            target_language,
            target_framework,
        )

        plan = BuildPlan(
            plan_id=plan_id,
            project_name=project_name,
            description=description,
            target_language=target_language,
            target_framework=target_framework,
            architecture_pattern=primary_pattern.pattern_type
            if primary_pattern
            else "generic",
            constraints=constraints,
            modifications=[],  # Will be populated during constraint application
            files=files,
            dependencies=dependencies,
            config_requirements=config_requirements,
            testing_strategy=testing_strategy,
            documentation_plan=documentation_plan,
            status=BuildPlanStatus.DRAFT,
            created_at=datetime.now().isoformat(),
            ambiguities=ambiguities,
        )

        self.current_plan = plan
        logger.info(f"Generated build plan with {len(files)} files")

        return plan

    def _select_primary_pattern(
        self, template: ArchitectureTemplate, constraints: List[str]
    ) -> Optional[ArchitecturePattern]:
        """Select primary architecture pattern based on template and constraints."""
        if not template.patterns:
            return None

        # Check constraints for pattern hints
        constraint_lower = " ".join(constraints).lower()

        for pattern in template.patterns:
            if pattern.pattern_type in constraint_lower:
                return pattern

        # Return highest confidence pattern
        return template.patterns[0]

    def _generate_file_specs(
        self,
        template: ArchitectureTemplate,
        target_language: str,
        target_framework: Optional[str],
        primary_pattern: Optional[ArchitecturePattern],
        constraints: List[str],
    ) -> List[FileSpec]:
        """Generate file specifications for the build plan."""
        files = []

        constraint_lower = " ".join(constraints).lower()

        # Language-specific file generation
        if target_language == "python":
            files = self._generate_python_file_specs(
                template, target_framework, primary_pattern, constraints
            )
        elif target_language == "javascript":
            files = self._generate_javascript_file_specs(
                template, target_framework, primary_pattern, constraints
            )
        elif target_language == "typescript":
            files = self._generate_typescript_file_specs(
                template, target_framework, primary_pattern, constraints
            )
        elif target_language == "go":
            files = self._generate_go_file_specs(
                template, target_framework, primary_pattern, constraints
            )

        # Add constraint-specific files
        if "multi-tenant" in constraint_lower or "multitenant" in constraint_lower:
            files.extend(self._generate_multitenant_files(target_language))

        if "redis" in constraint_lower or "cache" in constraint_lower:
            files.extend(self._generate_redis_files(target_language))

        if "auth" in constraint_lower or "authentication" in constraint_lower:
            files.extend(self._generate_auth_files(target_language, target_framework))

        return files

    def _generate_python_file_specs(
        self,
        template: ArchitectureTemplate,
        framework: Optional[str],
        pattern: Optional[ArchitecturePattern],
        constraints: List[str],
    ) -> List[FileSpec]:
        """Generate file specifications for Python projects."""
        files = []

        # Core files
        files.append(
            FileSpec(
                path="README.md",
                purpose="Project documentation and setup instructions",
                dependencies=[],
                estimated_lines=100,
                template_hints={"type": "documentation"},
            )
        )

        # Package structure
        project_name_slug = "src"  # Simplified
        files.append(
            FileSpec(
                path=f"{project_name_slug}/__init__.py",
                purpose="Package initialization",
                dependencies=[],
                estimated_lines=10,
                template_hints={"type": "package_init"},
            )
        )

        # Framework-specific files
        if framework == "fastapi":
            files.append(
                FileSpec(
                    path=f"{project_name_slug}/main.py",
                    purpose="FastAPI application entry point",
                    dependencies=[f"{project_name_slug}/__init__.py"],
                    estimated_lines=50,
                    template_hints={"type": "fastapi_main", "framework": "fastapi"},
                )
            )
            files.append(
                FileSpec(
                    path=f"{project_name_slug}/routers/__init__.py",
                    purpose="Routers package initialization",
                    dependencies=[],
                    estimated_lines=5,
                    template_hints={"type": "package_init"},
                )
            )
            files.append(
                FileSpec(
                    path=f"{project_name_slug}/models/__init__.py",
                    purpose="Models package initialization",
                    dependencies=[],
                    estimated_lines=5,
                    template_hints={"type": "package_init"},
                )
            )
        elif framework == "flask":
            files.append(
                FileSpec(
                    path=f"{project_name_slug}/app.py",
                    purpose="Flask application factory",
                    dependencies=[f"{project_name_slug}/__init__.py"],
                    estimated_lines=40,
                    template_hints={"type": "flask_app", "framework": "flask"},
                )
            )
        elif framework is None:
            # Generic Python CLI or library
            files.append(
                FileSpec(
                    path=f"{project_name_slug}/main.py",
                    purpose="Main application entry point",
                    dependencies=[f"{project_name_slug}/__init__.py"],
                    estimated_lines=100,
                    template_hints={"type": "cli_main"},
                )
            )

        # Configuration
        files.append(
            FileSpec(
                path="pyproject.toml",
                purpose="Python project configuration and dependencies",
                dependencies=[],
                estimated_lines=50,
                template_hints={"type": "config", "format": "toml"},
            )
        )

        # Tests
        files.append(
            FileSpec(
                path="tests/__init__.py",
                purpose="Tests package initialization",
                dependencies=[],
                estimated_lines=5,
                template_hints={"type": "package_init"},
            )
        )
        files.append(
            FileSpec(
                path="tests/test_main.py",
                purpose="Main test file",
                dependencies=[f"{project_name_slug}/main.py"],
                estimated_lines=50,
                template_hints={"type": "test"},
            )
        )

        return files

    def _generate_javascript_file_specs(
        self,
        template: ArchitectureTemplate,
        framework: Optional[str],
        pattern: Optional[ArchitecturePattern],
        constraints: List[str],
    ) -> List[FileSpec]:
        """Generate file specifications for JavaScript projects."""
        files = []

        files.append(
            FileSpec(
                path="README.md",
                purpose="Project documentation",
                dependencies=[],
                estimated_lines=100,
                template_hints={"type": "documentation"},
            )
        )

        files.append(
            FileSpec(
                path="package.json",
                purpose="Node.js project configuration",
                dependencies=[],
                estimated_lines=40,
                template_hints={"type": "config", "format": "json"},
            )
        )

        files.append(
            FileSpec(
                path="src/index.js",
                purpose="Main entry point",
                dependencies=[],
                estimated_lines=50,
                template_hints={"type": "main"},
            )
        )

        if framework == "express":
            files.append(
                FileSpec(
                    path="src/app.js",
                    purpose="Express application setup",
                    dependencies=["src/index.js"],
                    estimated_lines=40,
                    template_hints={"type": "express_app", "framework": "express"},
                )
            )
            files.append(
                FileSpec(
                    path="src/routes/index.js",
                    purpose="Route definitions",
                    dependencies=["src/app.js"],
                    estimated_lines=30,
                    template_hints={"type": "routes"},
                )
            )

        files.append(
            FileSpec(
                path="tests/index.test.js",
                purpose="Main test file",
                dependencies=["src/index.js"],
                estimated_lines=40,
                template_hints={"type": "test"},
            )
        )

        return files

    def _generate_typescript_file_specs(
        self,
        template: ArchitectureTemplate,
        framework: Optional[str],
        pattern: Optional[ArchitecturePattern],
        constraints: List[str],
    ) -> List[FileSpec]:
        """Generate file specifications for TypeScript projects."""
        files = []

        files.append(
            FileSpec(
                path="README.md",
                purpose="Project documentation",
                dependencies=[],
                estimated_lines=100,
                template_hints={"type": "documentation"},
            )
        )

        files.append(
            FileSpec(
                path="package.json",
                purpose="Node.js project configuration",
                dependencies=[],
                estimated_lines=50,
                template_hints={"type": "config", "format": "json"},
            )
        )

        files.append(
            FileSpec(
                path="tsconfig.json",
                purpose="TypeScript configuration",
                dependencies=[],
                estimated_lines=30,
                template_hints={"type": "config", "format": "json"},
            )
        )

        files.append(
            FileSpec(
                path="src/index.ts",
                purpose="Main entry point",
                dependencies=[],
                estimated_lines=50,
                template_hints={"type": "main"},
            )
        )

        if framework == "express":
            files.append(
                FileSpec(
                    path="src/app.ts",
                    purpose="Express application setup",
                    dependencies=["src/index.ts"],
                    estimated_lines=40,
                    template_hints={"type": "express_app", "framework": "express"},
                )
            )
            files.append(
                FileSpec(
                    path="src/routes/index.ts",
                    purpose="Route definitions",
                    dependencies=["src/app.ts"],
                    estimated_lines=30,
                    template_hints={"type": "routes"},
                )
            )
        elif framework == "nestjs":
            files.append(
                FileSpec(
                    path="src/app.module.ts",
                    purpose="NestJS root module",
                    dependencies=["src/index.ts"],
                    estimated_lines=30,
                    template_hints={"type": "nestjs_module", "framework": "nestjs"},
                )
            )
            files.append(
                FileSpec(
                    path="src/app.controller.ts",
                    purpose="NestJS root controller",
                    dependencies=["src/app.module.ts"],
                    estimated_lines=25,
                    template_hints={"type": "nestjs_controller"},
                )
            )

        files.append(
            FileSpec(
                path="tests/index.test.ts",
                purpose="Main test file",
                dependencies=["src/index.ts"],
                estimated_lines=40,
                template_hints={"type": "test"},
            )
        )

        return files

    def _generate_go_file_specs(
        self,
        template: ArchitectureTemplate,
        framework: Optional[str],
        pattern: Optional[ArchitecturePattern],
        constraints: List[str],
    ) -> List[FileSpec]:
        """Generate file specifications for Go projects."""
        files = []

        files.append(
            FileSpec(
                path="README.md",
                purpose="Project documentation",
                dependencies=[],
                estimated_lines=100,
                template_hints={"type": "documentation"},
            )
        )

        files.append(
            FileSpec(
                path="go.mod",
                purpose="Go module definition",
                dependencies=[],
                estimated_lines=10,
                template_hints={"type": "config", "format": "go.mod"},
            )
        )

        files.append(
            FileSpec(
                path="main.go",
                purpose="Main application entry point",
                dependencies=[],
                estimated_lines=50,
                template_hints={"type": "main"},
            )
        )

        if framework == "gin":
            files.append(
                FileSpec(
                    path="router/router.go",
                    purpose="Gin router setup",
                    dependencies=["main.go"],
                    estimated_lines=40,
                    template_hints={"type": "gin_router", "framework": "gin"},
                )
            )
            files.append(
                FileSpec(
                    path="handlers/handlers.go",
                    purpose="HTTP handlers",
                    dependencies=["router/router.go"],
                    estimated_lines=50,
                    template_hints={"type": "handlers"},
                )
            )
        elif framework == "echo":
            files.append(
                FileSpec(
                    path="server/server.go",
                    purpose="Echo server setup",
                    dependencies=["main.go"],
                    estimated_lines=40,
                    template_hints={"type": "echo_server", "framework": "echo"},
                )
            )

        files.append(
            FileSpec(
                path="main_test.go",
                purpose="Main test file",
                dependencies=["main.go"],
                estimated_lines=40,
                template_hints={"type": "test"},
            )
        )

        return files

    def _generate_multitenant_files(self, language: str) -> List[FileSpec]:
        """Generate additional files for multi-tenancy support."""
        files = []

        if language == "python":
            files.append(
                FileSpec(
                    path="src/middleware/tenant.py",
                    purpose="Multi-tenant middleware for request isolation",
                    dependencies=["src/__init__.py"],
                    estimated_lines=60,
                    template_hints={"type": "middleware", "feature": "multitenant"},
                )
            )
            files.append(
                FileSpec(
                    path="src/models/tenant.py",
                    purpose="Tenant model definition",
                    dependencies=["src/models/__init__.py"],
                    estimated_lines=40,
                    template_hints={"type": "model", "feature": "multitenant"},
                )
            )
        elif language in ["javascript", "typescript"]:
            files.append(
                FileSpec(
                    path="src/middleware/tenant.js",
                    purpose="Multi-tenant middleware for request isolation",
                    dependencies=["src/index.js"],
                    estimated_lines=60,
                    template_hints={"type": "middleware", "feature": "multitenant"},
                )
            )
        elif language == "go":
            files.append(
                FileSpec(
                    path="middleware/tenant.go",
                    purpose="Multi-tenant middleware for request isolation",
                    dependencies=["main.go"],
                    estimated_lines=60,
                    template_hints={"type": "middleware", "feature": "multitenant"},
                )
            )

        return files

    def _generate_redis_files(self, language: str) -> List[FileSpec]:
        """Generate additional files for Redis/cache support."""
        files = []

        if language == "python":
            files.append(
                FileSpec(
                    path="src/cache/redis_client.py",
                    purpose="Redis client wrapper",
                    dependencies=["src/__init__.py"],
                    estimated_lines=50,
                    template_hints={"type": "client", "feature": "redis"},
                )
            )
        elif language in ["javascript", "typescript"]:
            files.append(
                FileSpec(
                    path="src/cache/redis.js",
                    purpose="Redis client wrapper",
                    dependencies=["src/index.js"],
                    estimated_lines=50,
                    template_hints={"type": "client", "feature": "redis"},
                )
            )
        elif language == "go":
            files.append(
                FileSpec(
                    path="cache/redis.go",
                    purpose="Redis client wrapper",
                    dependencies=["main.go"],
                    estimated_lines=50,
                    template_hints={"type": "client", "feature": "redis"},
                )
            )

        return files

    def _generate_auth_files(
        self, language: str, framework: Optional[str]
    ) -> List[FileSpec]:
        """Generate additional files for authentication support."""
        files = []

        if language == "python":
            files.append(
                FileSpec(
                    path="src/auth/__init__.py",
                    purpose="Authentication package initialization",
                    dependencies=[],
                    estimated_lines=5,
                    template_hints={"type": "package_init"},
                )
            )
            files.append(
                FileSpec(
                    path="src/auth/jwt.py",
                    purpose="JWT authentication utilities",
                    dependencies=["src/auth/__init__.py"],
                    estimated_lines=80,
                    template_hints={"type": "auth", "feature": "jwt"},
                )
            )
            files.append(
                FileSpec(
                    path="src/auth/middleware.py",
                    purpose="Authentication middleware",
                    dependencies=["src/auth/jwt.py"],
                    estimated_lines=60,
                    template_hints={"type": "middleware", "feature": "auth"},
                )
            )
        elif language in ["javascript", "typescript"]:
            files.append(
                FileSpec(
                    path="src/auth/jwt.js",
                    purpose="JWT authentication utilities",
                    dependencies=["src/index.js"],
                    estimated_lines=80,
                    template_hints={"type": "auth", "feature": "jwt"},
                )
            )
            files.append(
                FileSpec(
                    path="src/auth/middleware.js",
                    purpose="Authentication middleware",
                    dependencies=["src/auth/jwt.js"],
                    estimated_lines=60,
                    template_hints={"type": "middleware", "feature": "auth"},
                )
            )
        elif language == "go":
            files.append(
                FileSpec(
                    path="auth/jwt.go",
                    purpose="JWT authentication utilities",
                    dependencies=["main.go"],
                    estimated_lines=80,
                    template_hints={"type": "auth", "feature": "jwt"},
                )
            )
            files.append(
                FileSpec(
                    path="auth/middleware.go",
                    purpose="Authentication middleware",
                    dependencies=["auth/jwt.go"],
                    estimated_lines=60,
                    template_hints={"type": "middleware", "feature": "auth"},
                )
            )

        return files

    def _determine_dependencies(
        self,
        target_language: str,
        target_framework: Optional[str],
        constraints: List[str],
    ) -> Dict[str, Any]:
        """Determine required dependencies based on language and constraints."""
        dependencies = {
            "production": [],
            "development": [],
        }

        constraint_lower = " ".join(constraints).lower()

        if target_language == "python":
            dependencies["development"].extend(["pytest", "black", "mypy", "ruff"])

            if target_framework == "fastapi":
                dependencies["production"].extend(["fastapi", "uvicorn", "pydantic"])
            elif target_framework == "flask":
                dependencies["production"].extend(["flask", "flask-cors"])

            if "auth" in constraint_lower or "authentication" in constraint_lower:
                dependencies["production"].append("pyjwt")

            if "redis" in constraint_lower or "cache" in constraint_lower:
                dependencies["production"].append("redis")

            if "sql" in constraint_lower or "database" in constraint_lower:
                dependencies["production"].extend(["sqlalchemy", "alembic"])

        elif target_language == "javascript":
            dependencies["development"].extend(["jest", "eslint", "prettier"])

            if target_framework == "express":
                dependencies["production"].extend(["express", "cors", "helmet"])

            if "auth" in constraint_lower or "authentication" in constraint_lower:
                dependencies["production"].extend(["jsonwebtoken", "bcrypt"])

            if "redis" in constraint_lower or "cache" in constraint_lower:
                dependencies["production"].append("redis")

        elif target_language == "typescript":
            dependencies["development"].extend(
                ["typescript", "@types/node", "jest", "ts-jest", "eslint", "prettier"]
            )

            if target_framework == "express":
                dependencies["production"].extend(
                    ["express", "@types/express", "cors", "helmet"]
                )
            elif target_framework == "nestjs":
                dependencies["production"].extend(
                    ["@nestjs/common", "@nestjs/core", "@nestjs/platform-express"]
                )

            if "auth" in constraint_lower or "authentication" in constraint_lower:
                dependencies["production"].extend(
                    ["jsonwebtoken", "@types/jsonwebtoken", "bcrypt", "@types/bcrypt"]
                )

        elif target_language == "go":
            if target_framework == "gin":
                dependencies["production"].append("github.com/gin-gonic/gin")
            elif target_framework == "echo":
                dependencies["production"].append("github.com/labstack/echo/v4")

            if "auth" in constraint_lower or "authentication" in constraint_lower:
                dependencies["production"].append("github.com/golang-jwt/jwt/v5")

            if "redis" in constraint_lower or "cache" in constraint_lower:
                dependencies["production"].append("github.com/redis/go-redis/v9")

        return dependencies

    def _generate_config_requirements(
        self,
        target_language: str,
        target_framework: Optional[str],
        constraints: List[str],
    ) -> Dict[str, Any]:
        """Generate configuration requirements."""
        config = {
            "files": [],
            "env_variables": [],
        }

        constraint_lower = " ".join(constraints).lower()

        if target_language == "python":
            config["files"].append({"name": "pyproject.toml", "type": "toml"})
            config["files"].append({"name": ".env.example", "type": "env"})
        elif target_language in ["javascript", "typescript"]:
            config["files"].append({"name": "package.json", "type": "json"})
            if target_language == "typescript":
                config["files"].append({"name": "tsconfig.json", "type": "json"})
            config["files"].append({"name": ".env.example", "type": "env"})
        elif target_language == "go":
            config["files"].append({"name": "go.mod", "type": "go.mod"})
            config["files"].append({"name": ".env.example", "type": "env"})

        # Environment variables based on constraints
        if "redis" in constraint_lower:
            config["env_variables"].extend(["REDIS_URL", "REDIS_PASSWORD"])

        if "auth" in constraint_lower:
            config["env_variables"].extend(
                ["JWT_SECRET", "JWT_ALGORITHM", "JWT_EXPIRATION"]
            )

        if "multi-tenant" in constraint_lower or "multitenant" in constraint_lower:
            config["env_variables"].append("TENANT_HEADER_NAME")

        return config

    def _plan_testing_strategy(
        self,
        target_language: str,
        target_framework: Optional[str],
        existing_tests: Optional[Dict],
    ) -> Dict[str, Any]:
        """Plan testing strategy for the project."""
        strategy = {
            "framework": "",
            "test_structure": "",
            "coverage_target": 80,
            "test_types": [],
        }

        if target_language == "python":
            strategy["framework"] = "pytest"
            strategy["test_structure"] = "tests/ directory with mirror structure"
            strategy["test_types"] = ["unit", "integration"]
        elif target_language in ["javascript", "typescript"]:
            strategy["framework"] = "jest"
            strategy["test_structure"] = "__tests__/ or tests/ directory"
            strategy["test_types"] = ["unit", "integration"]
        elif target_language == "go":
            strategy["framework"] = "go test"
            strategy["test_structure"] = "*_test.go files alongside source"
            strategy["test_types"] = ["unit", "integration"]

        return strategy

    def _plan_documentation(self, existing_docs: Optional[Dict]) -> Dict[str, Any]:
        """Plan documentation structure."""
        return {
            "required_files": [
                "README.md",
                "CONTRIBUTING.md",
                "LICENSE",
            ],
            "optional_files": [
                "CHANGELOG.md",
                "API.md",
            ],
            "inline_docs": "docstrings/comments",
        }

    def _identify_ambiguities(
        self,
        template: ArchitectureTemplate,
        constraints: List[str],
        target_language: str,
        target_framework: Optional[str],
    ) -> List[str]:
        """Identify potential ambiguities in the plan."""
        ambiguities = []

        # Check for language mismatch
        if target_language not in template.languages:
            ambiguities.append(
                f"Target language {target_language} differs from source languages {template.languages}. "
                "Architecture patterns may need adaptation."
            )

        # Check for framework mismatch
        if target_framework and target_framework not in template.frameworks:
            ambiguities.append(
                f"Target framework {target_framework} differs from source frameworks {template.frameworks}. "
                "Generated code will use idioms appropriate to the new framework."
            )

        # Check for constraint complexity
        if len(constraints) > 3:
            ambiguities.append(
                f"Multiple constraints ({len(constraints)}) may interact in complex ways. "
                "Please review the build plan carefully."
            )

        return ambiguities

    def scaffold_project(
        self,
        plan: BuildPlan,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Scaffold the project directory structure.

        Creates all directories and empty files according to the build plan.
        Does not generate file content yet - that's done in write_code().

        Args:
            plan: The build plan to scaffold
            output_path: Optional custom output path (defaults to self.output_dir)

        Returns:
            Path to the scaffolded project directory
        """
        logger.info(f"Scaffolding project: {plan.project_name}")

        if output_path is None:
            output_path = self.output_dir / plan.project_name
        else:
            output_path = Path(output_path)

        output_path.mkdir(parents=True, exist_ok=True)

        # Initialize progress tracking
        self.progress = GenerationProgress(
            current_phase=GenerationPhase.SCAFFOLDING,
            total_files=len(plan.files),
            completed_files=0,
            failed_files=0,
            current_file=None,
            phase_progress=0.0,
            messages=[f"Scaffolding project in {output_path}"],
            errors=[],
        )

        # Create directories
        directories_created = set()

        for file_spec in plan.files:
            file_path = output_path / file_spec.path
            dir_path = file_path.parent

            if str(dir_path) not in directories_created and not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                directories_created.add(str(dir_path))
                self.progress.messages.append(f"Created directory: {dir_path}")

        # Create placeholder files
        for file_spec in plan.files:
            file_path = output_path / file_spec.path
            self.progress.current_file = file_spec.path

            try:
                if not file_path.exists():
                    file_path.touch()
                    self.progress.completed_files += 1
                    self.progress.messages.append(
                        f"Created file placeholder: {file_spec.path}"
                    )
            except Exception as e:
                self.progress.failed_files += 1
                self.progress.errors.append(f"Failed to create {file_spec.path}: {e}")

        self.progress.phase_progress = 1.0
        self.progress.messages.append(
            f"Scaffolding complete: {self.progress.completed_files} files created"
        )

        logger.info(f"Project scaffolded at: {output_path}")
        return str(output_path)

    def write_code(
        self,
        plan: BuildPlan,
        project_path: str,
        template: Optional[ArchitectureTemplate] = None,
        batch_size: int = 5,
    ) -> Dict[str, str]:
        """
        Generate code for all files in the build plan.

        Uses the local LLM to generate code file by file, coordinating
        dependencies and maintaining consistency across the codebase.

        Args:
            plan: The build plan with file specifications
            project_path: Path to the scaffolded project
            template: Optional architecture template for reference
            batch_size: Number of files to generate before reviewing

        Returns:
            Dictionary mapping file paths to generated content
        """
        logger.info(f"Starting code generation for {len(plan.files)} files")

        project_path = Path(project_path)
        self.generated_files = {}

        # Initialize progress
        self.progress = GenerationProgress(
            current_phase=GenerationPhase.CODE_GENERATION,
            total_files=len(plan.files),
            completed_files=0,
            failed_files=0,
            current_file=None,
            phase_progress=0.0,
            messages=["Starting code generation"],
            errors=[],
        )

        # Sort files by dependencies (topological order)
        sorted_files = self._topological_sort_files(plan.files)

        # Generate code in batches
        for i in range(0, len(sorted_files), batch_size):
            batch = sorted_files[i : i + batch_size]

            for file_spec in batch:
                self.progress.current_file = file_spec.path
                self._update_progress_message(f"Generating: {file_spec.path}")

                try:
                    # Generate file content
                    content = self._generate_file_content(
                        file_spec=file_spec,
                        plan=plan,
                        template=template,
                        project_path=project_path,
                        generated_files=self.generated_files,
                    )

                    # Validate generated content
                    if self._validate_code(
                        content, plan.target_language, file_spec.path
                    ):
                        # Write to file
                        file_path = project_path / file_spec.path
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(content)

                        self.generated_files[file_spec.path] = content
                        file_spec.content = content
                        file_spec.status = "completed"
                        self.progress.completed_files += 1
                        self._update_progress_message(f"Completed: {file_spec.path}")
                    else:
                        raise ValueError(
                            f"Generated code failed validation for {file_spec.path}"
                        )

                except Exception as e:
                    logger.error(f"Failed to generate {file_spec.path}: {e}")
                    file_spec.status = "failed"
                    self.progress.failed_files += 1
                    self.progress.errors.append(f"{file_spec.path}: {str(e)}")

            # Update phase progress
            self.progress.phase_progress = (i + len(batch)) / len(sorted_files)

        self.progress.current_phase = GenerationPhase.COMPLETION
        self.progress.phase_progress = 1.0
        self.progress.messages.append(
            f"Code generation complete: {self.progress.completed_files} successful, "
            f"{self.progress.failed_files} failed"
        )

        logger.info(
            f"Code generation complete: {len(self.generated_files)} files generated"
        )

        return self.generated_files

    def _topological_sort_files(self, files: List[FileSpec]) -> List[FileSpec]:
        """Sort files by dependencies for correct generation order."""
        file_map = {f.path: f for f in files}
        visited = set()
        sorted_files = []

        def visit(file_spec: FileSpec):
            if file_spec.path in visited:
                return
            visited.add(file_spec.path)

            # Visit dependencies first
            for dep_path in file_spec.dependencies:
                if dep_path in file_map:
                    visit(file_map[dep_path])

            sorted_files.append(file_spec)

        for file_spec in files:
            visit(file_spec)

        return sorted_files

    def _generate_file_content(
        self,
        file_spec: FileSpec,
        plan: BuildPlan,
        template: Optional[ArchitectureTemplate],
        project_path: Path,
        generated_files: Dict[str, str],
    ) -> str:
        """Generate content for a single file."""
        # Build context from already generated files
        context = self._build_generation_context(
            file_spec, plan, template, generated_files
        )

        # Use code generator to generate content
        content = self.code_generator.generate_file(
            file_spec=file_spec,
            context=context,
            language=plan.target_language,
            framework=plan.target_framework,
        )

        return content

    def _build_generation_context(
        self,
        file_spec: FileSpec,
        plan: BuildPlan,
        template: Optional[ArchitectureTemplate],
        generated_files: Dict[str, str],
    ) -> Dict[str, Any]:
        """Build context for code generation."""
        context = {
            "project_name": plan.project_name,
            "project_description": plan.description,
            "target_language": plan.target_language,
            "target_framework": plan.target_framework,
            "architecture_pattern": plan.architecture_pattern,
            "constraints": plan.constraints,
            "file_purpose": file_spec.purpose,
            "file_path": file_spec.path,
            "dependencies": {},
            "template_hints": file_spec.template_hints,
        }

        # Add dependencies content
        for dep_path in file_spec.dependencies:
            if dep_path in generated_files:
                context["dependencies"][dep_path] = generated_files[dep_path]

        # Add template examples if available
        if template and template.file_templates:
            context["template_examples"] = template.file_templates

        return context

    def _validate_code(self, content: str, language: str, file_path: str) -> bool:
        """Validate generated code for syntax correctness."""
        if not content or not content.strip():
            return False

        # Language-specific validation
        if language == "python":
            return self._validate_python_code(content, file_path)
        elif language == "javascript":
            return self._validate_javascript_code(content, file_path)
        elif language == "typescript":
            return self._validate_typescript_code(content, file_path)
        elif language == "go":
            return self._validate_go_code(content, file_path)

        return True  # Default to accepting for unsupported languages

    def _validate_python_code(self, content: str, file_path: str) -> bool:
        """Validate Python code using AST."""
        try:
            import ast

            ast.parse(content)
            return True
        except SyntaxError as e:
            logger.warning(f"Python syntax error in {file_path}: {e}")
            return False

    def _validate_javascript_code(self, content: str, file_path: str) -> bool:
        """Validate JavaScript code."""
        # Basic validation - check for balanced braces and quotes
        try:
            open_braces = content.count("{")
            close_braces = content.count("}")
            open_parens = content.count("(")
            close_parens = content.count(")")

            return open_braces == close_braces and open_parens == close_parens
        except:
            return False

    def _validate_typescript_code(self, content: str, file_path: str) -> bool:
        """Validate TypeScript code."""
        # Same basic validation as JavaScript
        return self._validate_javascript_code(content, file_path)

    def _validate_go_code(self, content: str, file_path: str) -> bool:
        """Validate Go code."""
        # Check for package declaration
        if "package " not in content:
            return False

        # Basic brace validation
        open_braces = content.count("{")
        close_braces = content.count("}")

        return open_braces == close_braces

    def self_review(self, plan: BuildPlan, project_path: str) -> ReviewResult:
        """
        Perform self-review of generated code against the plan.

        Reviews the generated project to ensure it meets the build plan
        requirements, checking for missing files, inconsistencies, and
        potential issues.

        Args:
            plan: The original build plan
            project_path: Path to the generated project

        Returns:
            ReviewResult containing review findings
        """
        logger.info("Starting self-review of generated code")

        project_path = Path(project_path)
        issues = []
        suggestions = []
        missing_files = []
        extra_files = []

        # Check for missing files
        for file_spec in plan.files:
            file_path = project_path / file_spec.path
            if not file_path.exists():
                missing_files.append(file_spec.path)
                issues.append(
                    {
                        "type": "missing_file",
                        "file": file_spec.path,
                        "severity": "high",
                        "message": f"Expected file not found: {file_spec.path}",
                    }
                )
            elif file_spec.status == "failed":
                issues.append(
                    {
                        "type": "generation_failed",
                        "file": file_spec.path,
                        "severity": "high",
                        "message": f"File generation failed for: {file_spec.path}",
                    }
                )

        # Calculate coverage score
        total_files = len(plan.files)
        completed_files = sum(1 for f in plan.files if f.status == "completed")
        coverage_score = completed_files / total_files if total_files > 0 else 0.0

        # Check for extra files
        expected_paths = {f.path for f in plan.files}
        for file_path in project_path.rglob("*"):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(project_path))
                if rel_path not in expected_paths and not rel_path.startswith("."):
                    extra_files.append(rel_path)

        # Language-specific reviews
        if plan.target_language == "python":
            python_issues = self._review_python_project(project_path, plan)
            issues.extend(python_issues)
        elif plan.target_language in ["javascript", "typescript"]:
            js_issues = self._review_js_project(project_path, plan)
            issues.extend(js_issues)

        # Check for common issues
        if coverage_score < 0.8:
            suggestions.append(
                f"Coverage is {coverage_score:.0%}. Consider regenerating failed files."
            )

        if missing_files:
            suggestions.append(
                f"{len(missing_files)} files are missing. Run scaffold_project() to create placeholders."
            )

        # Generate suggestions based on plan constraints
        for constraint in plan.constraints:
            suggestion = self._check_constraint_implementation(
                constraint, project_path, plan
            )
            if suggestion:
                suggestions.append(suggestion)

        passed = (
            len([i for i in issues if i["severity"] == "high"]) == 0
            and coverage_score >= 0.8
        )

        result = ReviewResult(
            passed=passed,
            issues=issues,
            suggestions=suggestions,
            coverage_score=coverage_score,
            missing_files=missing_files,
            extra_files=extra_files,
        )

        logger.info(
            f"Self-review complete: {len(issues)} issues, {coverage_score:.0%} coverage"
        )

        return result

    def _review_python_project(self, project_path: Path, plan: BuildPlan) -> List[Dict]:
        """Review Python-specific aspects of the project."""
        issues = []

        # Check for pyproject.toml or setup.py
        if (
            not (project_path / "pyproject.toml").exists()
            and not (project_path / "setup.py").exists()
        ):
            issues.append(
                {
                    "type": "missing_config",
                    "file": "pyproject.toml or setup.py",
                    "severity": "medium",
                    "message": "Python project should have pyproject.toml or setup.py",
                }
            )

        # Check for __init__.py files in packages
        for dir_path in project_path.rglob("*"):
            if dir_path.is_dir() and dir_path.name != "__pycache__":
                py_files = list(dir_path.glob("*.py"))
                if py_files and not (dir_path / "__init__.py").exists():
                    # Check if it's a package (has Python files but no __init__.py)
                    if len(py_files) > 0:
                        issues.append(
                            {
                                "type": "missing_init",
                                "file": str(dir_path / "__init__.py"),
                                "severity": "low",
                                "message": f"Package directory missing __init__.py: {dir_path.name}",
                            }
                        )

        return issues

    def _review_js_project(self, project_path: Path, plan: BuildPlan) -> List[Dict]:
        """Review JavaScript/TypeScript-specific aspects."""
        issues = []

        # Check for package.json
        if not (project_path / "package.json").exists():
            issues.append(
                {
                    "type": "missing_config",
                    "file": "package.json",
                    "severity": "high",
                    "message": "Node.js project must have package.json",
                }
            )

        # Check for TypeScript config if TypeScript
        if plan.target_language == "typescript":
            if not (project_path / "tsconfig.json").exists():
                issues.append(
                    {
                        "type": "missing_config",
                        "file": "tsconfig.json",
                        "severity": "medium",
                        "message": "TypeScript project should have tsconfig.json",
                    }
                )

        return issues

    def _check_constraint_implementation(
        self, constraint: str, project_path: Path, plan: BuildPlan
    ) -> Optional[str]:
        """Check if a constraint has been implemented."""
        constraint_lower = constraint.lower()

        if "multi-tenant" in constraint_lower or "multitenant" in constraint_lower:
            tenant_files = list(project_path.rglob("*tenant*"))
            if not tenant_files:
                return f"Multi-tenancy constraint specified but no tenant-related files found"

        if "redis" in constraint_lower or "cache" in constraint_lower:
            redis_files = list(project_path.rglob("*redis*")) + list(
                project_path.rglob("*cache*")
            )
            if not redis_files:
                return (
                    f"Redis/cache constraint specified but no cache-related files found"
                )

        if "auth" in constraint_lower:
            auth_files = list(project_path.rglob("*auth*"))
            if not auth_files:
                return f"Authentication constraint specified but no auth-related files found"

        return None

    def apply_constraints(
        self,
        plan: BuildPlan,
        new_constraints: List[str],
    ) -> BuildPlan:
        """
        Apply new constraints to an existing build plan.

        Modifies the build plan to incorporate additional user constraints
        such as "make it multi-tenant" or "add Redis cache".

        Args:
            plan: Existing build plan
            new_constraints: New constraints to apply

        Returns:
            Modified build plan with constraints applied
        """
        logger.info(f"Applying {len(new_constraints)} new constraints to plan")

        # Add new constraints to plan
        plan.constraints.extend(new_constraints)
        plan.modifications.append(
            {
                "type": "constraints_added",
                "constraints": new_constraints,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Add files based on new constraints
        for constraint in new_constraints:
            constraint_lower = constraint.lower()

            if "multi-tenant" in constraint_lower or "multitenant" in constraint_lower:
                new_files = self._generate_multitenant_files(plan.target_language)
                for file_spec in new_files:
                    if not any(f.path == file_spec.path for f in plan.files):
                        plan.files.append(file_spec)

            if "redis" in constraint_lower or "cache" in constraint_lower:
                new_files = self._generate_redis_files(plan.target_language)
                for file_spec in new_files:
                    if not any(f.path == file_spec.path for f in plan.files):
                        plan.files.append(file_spec)

            if "auth" in constraint_lower or "authentication" in constraint_lower:
                new_files = self._generate_auth_files(
                    plan.target_language, plan.target_framework
                )
                for file_spec in new_files:
                    if not any(f.path == file_spec.path for f in plan.files):
                        plan.files.append(file_spec)

            # Update dependencies based on constraint
            constraint_deps = self._determine_dependencies(
                plan.target_language,
                plan.target_framework,
                [constraint],
            )

            for dep_type, deps in constraint_deps.items():
                if dep_type in plan.dependencies:
                    for dep in deps:
                        if dep not in plan.dependencies[dep_type]:
                            plan.dependencies[dep_type].append(dep)
                else:
                    plan.dependencies[dep_type] = deps

        # Update ambiguities
        new_ambiguities = self._identify_ambiguities(
            self.current_template
            or ArchitectureTemplate(
                source_repo="",
                languages=[plan.target_language],
                frameworks=[plan.target_framework] if plan.target_framework else [],
                patterns=[],
                directory_structure={},
                dependencies={},
                file_templates={},
                config_patterns={},
                entry_points=[],
                tests_structure=None,
                documentation_structure=None,
            ),
            plan.constraints,
            plan.target_language,
            plan.target_framework,
        )

        # Add new ambiguities
        for ambiguity in new_ambiguities:
            if ambiguity not in plan.ambiguities:
                plan.ambiguities.append(ambiguity)

        logger.info(f"Applied constraints. Plan now has {len(plan.files)} files")

        return plan

    def approve_plan(self, plan: BuildPlan) -> BuildPlan:
        """
        Mark a build plan as approved by human reviewer.

        Args:
            plan: Build plan to approve

        Returns:
            Approved build plan
        """
        plan.status = BuildPlanStatus.APPROVED
        plan.approved_at = datetime.now().isoformat()
        logger.info(f"Build plan {plan.plan_id} approved")
        return plan

    def get_progress(self) -> Optional[GenerationProgress]:
        """Get current generation progress."""
        return self.progress

    def _update_progress_message(self, message: str) -> None:
        """Update progress with a new message."""
        if self.progress:
            self.progress.messages.append(message)
            logger.debug(message)

    def export_plan(self, plan: BuildPlan, output_path: Optional[str] = None) -> str:
        """
        Export build plan to JSON file.

        Args:
            plan: Build plan to export
            output_path: Optional output path

        Returns:
            Path to exported file
        """
        if output_path is None:
            output_path = self.output_dir / f"{plan.plan_id}_plan.json"
        else:
            output_path = Path(output_path)

        # Convert dataclass to dict
        plan_dict = {
            "plan_id": plan.plan_id,
            "project_name": plan.project_name,
            "description": plan.description,
            "target_language": plan.target_language,
            "target_framework": plan.target_framework,
            "architecture_pattern": plan.architecture_pattern,
            "constraints": plan.constraints,
            "modifications": plan.modifications,
            "files": [
                {
                    "path": f.path,
                    "purpose": f.purpose,
                    "dependencies": f.dependencies,
                    "estimated_lines": f.estimated_lines,
                    "status": f.status,
                }
                for f in plan.files
            ],
            "dependencies": plan.dependencies,
            "config_requirements": plan.config_requirements,
            "testing_strategy": plan.testing_strategy,
            "documentation_plan": plan.documentation_plan,
            "status": plan.status.value,
            "created_at": plan.created_at,
            "approved_at": plan.approved_at,
            "completed_at": plan.completed_at,
            "ambiguities": plan.ambiguities,
            "warnings": plan.warnings,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(plan_dict, f, indent=2)

        logger.info(f"Build plan exported to: {output_path}")
        return str(output_path)

    def import_plan(self, plan_path: str) -> BuildPlan:
        """
        Import build plan from JSON file.

        Args:
            plan_path: Path to plan JSON file

        Returns:
            BuildPlan object
        """
        with open(plan_path, "r", encoding="utf-8") as f:
            plan_dict = json.load(f)

        files = [
            FileSpec(
                path=f["path"],
                purpose=f["purpose"],
                dependencies=f["dependencies"],
                estimated_lines=f["estimated_lines"],
                template_hints={},
                status=f.get("status", "pending"),
            )
            for f in plan_dict["files"]
        ]

        plan = BuildPlan(
            plan_id=plan_dict["plan_id"],
            project_name=plan_dict["project_name"],
            description=plan_dict["description"],
            target_language=plan_dict["target_language"],
            target_framework=plan_dict.get("target_framework"),
            architecture_pattern=plan_dict["architecture_pattern"],
            constraints=plan_dict["constraints"],
            modifications=plan_dict.get("modifications", []),
            files=files,
            dependencies=plan_dict["dependencies"],
            config_requirements=plan_dict["config_requirements"],
            testing_strategy=plan_dict["testing_strategy"],
            documentation_plan=plan_dict["documentation_plan"],
            status=BuildPlanStatus(plan_dict["status"]),
            created_at=plan_dict["created_at"],
            approved_at=plan_dict.get("approved_at"),
            completed_at=plan_dict.get("completed_at"),
            ambiguities=plan_dict.get("ambiguities", []),
            warnings=plan_dict.get("warnings", []),
        )

        self.current_plan = plan
        logger.info(f"Build plan imported from: {plan_path}")

        return plan


class RebuilderWorkflow:
    """
    High-level workflow orchestrator for the Rebuilder Agent.

    Provides a simplified interface for the complete rebuild process:
    1. Extract architecture template
    2. Generate build plan
    3. Human approval checkpoint
    4. Scaffold and generate code
    5. Self-review
    """

    def __init__(self, agent: Optional[RebuilderAgent] = None, **kwargs):
        """
        Initialize the workflow.

        Args:
            agent: Optional pre-configured RebuilderAgent
            **kwargs: Arguments to pass to RebuilderAgent if not provided
        """
        self.agent = agent or RebuilderAgent(**kwargs)
        self.current_plan: Optional[BuildPlan] = None
        self.current_template: Optional[ArchitectureTemplate] = None

    def run(
        self,
        source_codebase: str,
        project_name: str,
        description: str,
        constraints: List[str],
        target_language: Optional[str] = None,
        target_framework: Optional[str] = None,
        auto_approve: bool = False,
    ) -> Tuple[str, BuildPlan, ReviewResult]:
        """
        Run the complete rebuild workflow.

        Args:
            source_codebase: Path to source codebase
            project_name: Name for new project
            description: Description of new project
            constraints: List of constraints to apply
            target_language: Target language (optional)
            target_framework: Target framework (optional)
            auto_approve: Skip human approval (for testing)

        Returns:
            Tuple of (project_path, build_plan, review_result)
        """
        logger.info(f"Starting rebuild workflow for: {project_name}")

        # Step 1: Extract architecture template
        print("Step 1/5: Extracting architecture template...")
        template = self.agent.extract_architecture_template(source_codebase)
        self.current_template = template

        # Step 2: Generate build plan
        print("Step 2/5: Generating build plan...")
        plan = self.agent.generate_build_plan(
            template=template,
            project_name=project_name,
            description=description,
            constraints=constraints,
            target_language=target_language,
            target_framework=target_framework,
        )
        self.current_plan = plan

        # Export plan for review
        plan_path = self.agent.export_plan(plan)
        print(f"Build plan exported to: {plan_path}")

        # Step 3: Human approval checkpoint
        if not auto_approve:
            print("\n" + "=" * 60)
            print("HUMAN APPROVAL REQUIRED")
            print("=" * 60)
            print(f"Project: {plan.project_name}")
            print(f"Language: {plan.target_language}")
            print(f"Framework: {plan.target_framework}")
            print(f"Files to generate: {len(plan.files)}")
            print(f"Ambiguities: {len(plan.ambiguities)}")

            if plan.ambiguities:
                print("\nAmbiguities:")
                for amb in plan.ambiguities:
                    print(f"  - {amb}")

            print("\nFiles to be generated:")
            for file_spec in plan.files[:10]:
                print(f"  - {file_spec.path} ({file_spec.purpose})")
            if len(plan.files) > 10:
                print(f"  ... and {len(plan.files) - 10} more files")

            response = input("\nApprove this plan? (yes/no): ").lower()
            if response not in ["yes", "y"]:
                print("Build plan not approved. Exiting.")
                return None, plan, None

        plan = self.agent.approve_plan(plan)
        print("Plan approved. Proceeding with generation...")

        # Step 4: Scaffold and generate code
        print("Step 4/5: Scaffolding project...")
        project_path = self.agent.scaffold_project(plan)

        print("Step 4/5: Generating code...")
        generated_files = self.agent.write_code(
            plan=plan,
            project_path=project_path,
            template=template,
        )

        # Step 5: Self-review
        print("Step 5/5: Performing self-review...")
        review = self.agent.self_review(plan, project_path)

        print("\n" + "=" * 60)
        print("REBUILD COMPLETE")
        print("=" * 60)
        print(f"Project location: {project_path}")
        print(f"Files generated: {len(generated_files)}")
        print(f"Coverage: {review.coverage_score:.0%}")
        print(f"Issues: {len(review.issues)}")
        print(f"Suggestions: {len(review.suggestions)}")

        if review.suggestions:
            print("\nSuggestions:")
            for suggestion in review.suggestions:
                print(f"  - {suggestion}")

        return project_path, plan, review

    def add_constraints(self, constraints: List[str]) -> BuildPlan:
        """
        Add constraints to the current plan.

        Args:
            constraints: New constraints to apply

        Returns:
            Updated build plan
        """
        if self.current_plan is None:
            raise ValueError("No current plan. Run workflow first.")

        self.current_plan = self.agent.apply_constraints(self.current_plan, constraints)
        return self.current_plan
