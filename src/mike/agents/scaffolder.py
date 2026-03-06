"""Project scaffolding engine for Mike.

Handles template-based project scaffolding, language-specific boilerplate
generation, and config file creation for various project types.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScaffoldingConfig:
    """Configuration for project scaffolding."""

    project_name: str
    language: str
    framework: Optional[str] = None
    project_type: str = "generic"  # api, cli, library, webapp
    include_tests: bool = True
    include_docker: bool = False
    include_ci: bool = False
    python_version: str = "3.11"
    node_version: str = "20"
    go_version: str = "1.21"
    extra_options: Dict[str, Any] = field(default_factory=dict)


class ProjectScaffolder:
    """
    Scaffolds new projects based on templates and configurations.

    Supports multiple languages and frameworks:
    - Python: FastAPI, Flask, Django, CLI
    - JavaScript/TypeScript: Express, React, Vue, CLI
    - Go: Gin, Echo, Fiber, CLI
    """

    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the scaffolder.

        Args:
            templates_dir: Optional custom templates directory
        """
        if templates_dir:
            self.templates_dir = Path(templates_dir)
        else:
            self.templates_dir = Path(__file__).parent / "templates"

        self._load_templates()
        logger.info(
            f"ProjectScaffolder initialized with templates from {self.templates_dir}"
        )

    def _load_templates(self) -> None:
        """Load available templates."""
        self.templates = {
            "python": {
                "fastapi": self._get_fastapi_template,
                "flask": self._get_flask_template,
                "cli": self._get_python_cli_template,
                "library": self._get_python_library_template,
            },
            "javascript": {
                "express": self._get_express_template,
                "cli": self._get_js_cli_template,
                "library": self._get_js_library_template,
            },
            "typescript": {
                "express": self._get_ts_express_template,
                "nestjs": self._get_nestjs_template,
                "cli": self._get_ts_cli_template,
                "library": self._get_ts_library_template,
            },
            "go": {
                "gin": self._get_gin_template,
                "echo": self._get_echo_template,
                "cli": self._get_go_cli_template,
                "library": self._get_go_library_template,
            },
        }

    def scaffold(
        self,
        config: ScaffoldingConfig,
        output_path: str,
    ) -> str:
        """
        Scaffold a new project based on configuration.

        Args:
            config: Scaffolding configuration
            output_path: Output directory for the project

        Returns:
            Path to the scaffolded project
        """
        logger.info(f"Scaffolding {config.language} project: {config.project_name}")

        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        # Get appropriate template
        template_func = self._get_template(config.language, config.framework)
        structure = template_func(config)

        # Create directories
        for dir_path in structure.get("directories", []):
            full_path = output_path / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {full_path}")

        # Create files
        for file_path, content in structure.get("files", {}).items():
            full_path = output_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.debug(f"Created file: {full_path}")

        logger.info(f"Project scaffolded at: {output_path}")
        return str(output_path)

    def _get_template(self, language: str, framework: Optional[str]):
        """Get template function for language/framework combination."""
        lang_templates = self.templates.get(language, {})

        if framework and framework in lang_templates:
            return lang_templates[framework]

        # Return generic template for language
        return lang_templates.get("library", self._get_generic_template)

    def _get_generic_template(self, config: ScaffoldingConfig) -> Dict[str, Any]:
        """Generic template fallback."""
        return {
            "directories": ["src"],
            "files": {
                "README.md": f"# {config.project_name}\n\nProject description here.\n",
            },
        }

    def _get_fastapi_template(self, config: ScaffoldingConfig) -> Dict[str, Any]:
        """Generate FastAPI project structure."""
        project_slug = self._slugify(config.project_name)

        return {
            "directories": [
                project_slug,
                f"{project_slug}/routers",
                f"{project_slug}/models",
                f"{project_slug}/services",
                f"{project_slug}/core",
                "tests",
            ],
            "files": {
                "README.md": self._generate_readme(config),
                "pyproject.toml": self._generate_pyproject_toml(config),
                ".env.example": self._generate_env_example(config),
                f"{project_slug}/__init__.py": f'"""{config.project_name}."""\n\n__version__ = "0.1.0"\n',
                f"{project_slug}/main.py": self._generate_fastapi_main(config),
                f"{project_slug}/core/__init__.py": "",
                f"{project_slug}/core/config.py": self._generate_config_py(config),
                f"{project_slug}/routers/__init__.py": "",
                f"{project_slug}/routers/health.py": self._generate_health_router(
                    config
                ),
                f"{project_slug}/models/__init__.py": "",
                f"{project_slug}/services/__init__.py": "",
                "tests/__init__.py": "",
                "tests/test_main.py": self._generate_test_main(config),
                ".gitignore": self._generate_gitignore(config),
            },
        }

    def _get_flask_template(self, config: ScaffoldingConfig) -> Dict[str, Any]:
        """Generate Flask project structure."""
        project_slug = self._slugify(config.project_name)

        return {
            "directories": [
                project_slug,
                f"{project_slug}/routes",
                f"{project_slug}/models",
                f"{project_slug}/templates",
                f"{project_slug}/static",
                "tests",
            ],
            "files": {
                "README.md": self._generate_readme(config),
                "pyproject.toml": self._generate_pyproject_toml(config),
                ".env.example": self._generate_env_example(config),
                f"{project_slug}/__init__.py": f'"""{config.project_name}."""\n\n__version__ = "0.1.0"\n',
                f"{project_slug}/app.py": self._generate_flask_app(config),
                f"{project_slug}/routes/__init__.py": "",
                f"{project_slug}/routes/main.py": self._generate_flask_routes(config),
                f"{project_slug}/models/__init__.py": "",
                "tests/__init__.py": "",
                "tests/test_app.py": self._generate_test_flask(config),
                ".gitignore": self._generate_gitignore(config),
            },
        }

    def _get_python_cli_template(self, config: ScaffoldingConfig) -> Dict[str, Any]:
        """Generate Python CLI project structure."""
        project_slug = self._slugify(config.project_name)

        return {
            "directories": [
                project_slug,
                f"{project_slug}/commands",
                "tests",
            ],
            "files": {
                "README.md": self._generate_readme(config),
                "pyproject.toml": self._generate_pyproject_toml_cli(config),
                f"{project_slug}/__init__.py": f'"""{config.project_name}."""\n\n__version__ = "0.1.0"\n',
                f"{project_slug}/cli.py": self._generate_python_cli(config),
                f"{project_slug}/commands/__init__.py": "",
                "tests/__init__.py": "",
                "tests/test_cli.py": self._generate_test_cli(config),
                ".gitignore": self._generate_gitignore(config),
            },
        }

    def _get_python_library_template(self, config: ScaffoldingConfig) -> Dict[str, Any]:
        """Generate Python library project structure."""
        project_slug = self._slugify(config.project_name)

        return {
            "directories": [
                project_slug,
                "tests",
                "docs",
            ],
            "files": {
                "README.md": self._generate_readme(config),
                "pyproject.toml": self._generate_pyproject_toml(config),
                f"{project_slug}/__init__.py": f'"""{config.project_name}."""\n\n__version__ = "0.1.0"\n',
                "tests/__init__.py": "",
                "tests/test_main.py": self._generate_test_main(config),
                ".gitignore": self._generate_gitignore(config),
            },
        }

    def _get_express_template(self, config: ScaffoldingConfig) -> Dict[str, Any]:
        """Generate Express.js project structure."""
        return {
            "directories": [
                "src",
                "src/routes",
                "src/middleware",
                "tests",
            ],
            "files": {
                "README.md": self._generate_readme(config),
                "package.json": self._generate_package_json(config),
                ".env.example": self._generate_env_example(config),
                "src/index.js": self._generate_express_main(config),
                "src/app.js": self._generate_express_app(config),
                "src/routes/index.js": self._generate_express_routes(config),
                "src/middleware/errorHandler.js": self._generate_express_error_handler(
                    config
                ),
                "tests/app.test.js": self._generate_js_test(config),
                ".gitignore": self._generate_gitignore(config),
            },
        }

    def _get_ts_express_template(self, config: ScaffoldingConfig) -> Dict[str, Any]:
        """Generate TypeScript Express project structure."""
        return {
            "directories": [
                "src",
                "src/routes",
                "src/middleware",
                "tests",
                "dist",
            ],
            "files": {
                "README.md": self._generate_readme(config),
                "package.json": self._generate_ts_package_json(config),
                "tsconfig.json": self._generate_tsconfig_json(config),
                ".env.example": self._generate_env_example(config),
                "src/index.ts": self._generate_ts_express_main(config),
                "src/app.ts": self._generate_ts_express_app(config),
                "src/routes/index.ts": self._generate_ts_express_routes(config),
                "src/middleware/errorHandler.ts": self._generate_ts_error_handler(
                    config
                ),
                "tests/app.test.ts": self._generate_ts_test(config),
                ".gitignore": self._generate_gitignore(config),
            },
        }

    def _get_nestjs_template(self, config: ScaffoldingConfig) -> Dict[str, Any]:
        """Generate NestJS project structure."""
        return {
            "directories": [
                "src",
                "test",
            ],
            "files": {
                "README.md": self._generate_readme(config),
                "package.json": self._generate_nestjs_package_json(config),
                "tsconfig.json": self._generate_tsconfig_json(config),
                "nest-cli.json": self._generate_nest_cli_json(config),
                ".env.example": self._generate_env_example(config),
                "src/main.ts": self._generate_nestjs_main(config),
                "src/app.module.ts": self._generate_nestjs_app_module(config),
                "src/app.controller.ts": self._generate_nestjs_app_controller(config),
                "src/app.service.ts": self._generate_nestjs_app_service(config),
                "test/app.e2e-spec.ts": self._generate_nestjs_e2e_test(config),
                ".gitignore": self._generate_gitignore(config),
            },
        }

    def _get_gin_template(self, config: ScaffoldingConfig) -> Dict[str, Any]:
        """Generate Gin (Go) project structure."""
        return {
            "directories": [
                "cmd",
                "internal",
                "internal/handlers",
                "internal/models",
                "internal/services",
                "pkg",
                "configs",
            ],
            "files": {
                "README.md": self._generate_readme(config),
                "go.mod": self._generate_go_mod(config),
                "main.go": self._generate_go_main(config),
                "internal/handlers/health.go": self._generate_go_health_handler(config),
                ".env.example": self._generate_env_example(config),
                ".gitignore": self._generate_gitignore(config),
            },
        }

    def _get_echo_template(self, config: ScaffoldingConfig) -> Dict[str, Any]:
        """Generate Echo (Go) project structure."""
        return {
            "directories": [
                "cmd",
                "internal",
                "internal/handlers",
                "internal/models",
                "pkg",
            ],
            "files": {
                "README.md": self._generate_readme(config),
                "go.mod": self._generate_go_mod(config),
                "main.go": self._generate_echo_main(config),
                "internal/handlers/health.go": self._generate_echo_health_handler(
                    config
                ),
                ".env.example": self._generate_env_example(config),
                ".gitignore": self._generate_gitignore(config),
            },
        }

    def _get_go_cli_template(self, config: ScaffoldingConfig) -> Dict[str, Any]:
        """Generate Go CLI project structure."""
        return {
            "directories": [
                "cmd",
                "internal",
                "pkg",
            ],
            "files": {
                "README.md": self._generate_readme(config),
                "go.mod": self._generate_go_mod(config),
                "main.go": self._generate_go_cli_main(config),
                "cmd/root.go": self._generate_go_cobra_root(config),
                ".gitignore": self._generate_gitignore(config),
            },
        }

    def _get_go_library_template(self, config: ScaffoldingConfig) -> Dict[str, Any]:
        """Generate Go library project structure."""
        return {
            "directories": [
                "pkg",
            ],
            "files": {
                "README.md": self._generate_readme(config),
                "go.mod": self._generate_go_mod(config),
                ".gitignore": self._generate_gitignore(config),
            },
        }

    def _get_js_cli_template(self, config: ScaffoldingConfig) -> Dict[str, Any]:
        """Generate JavaScript CLI project structure."""
        return {
            "directories": [
                "bin",
                "lib",
                "tests",
            ],
            "files": {
                "README.md": self._generate_readme(config),
                "package.json": self._generate_js_cli_package_json(config),
                "bin/cli.js": self._generate_js_cli(config),
                "lib/index.js": self._generate_js_lib(config),
                "tests/cli.test.js": self._generate_js_test(config),
                ".gitignore": self._generate_gitignore(config),
            },
        }

    def _get_js_library_template(self, config: ScaffoldingConfig) -> Dict[str, Any]:
        """Generate JavaScript library project structure."""
        return {
            "directories": [
                "lib",
                "tests",
            ],
            "files": {
                "README.md": self._generate_readme(config),
                "package.json": self._generate_package_json(config),
                "lib/index.js": self._generate_js_lib(config),
                "tests/index.test.js": self._generate_js_test(config),
                ".gitignore": self._generate_gitignore(config),
            },
        }

    def _get_ts_cli_template(self, config: ScaffoldingConfig) -> Dict[str, Any]:
        """Generate TypeScript CLI project structure."""
        return {
            "directories": [
                "src",
                "bin",
                "tests",
            ],
            "files": {
                "README.md": self._generate_readme(config),
                "package.json": self._generate_ts_cli_package_json(config),
                "tsconfig.json": self._generate_tsconfig_json(config),
                "src/cli.ts": self._generate_ts_cli(config),
                "bin/run": "#!/usr/bin/env node\nrequire('../dist/cli.js')\n",
                "tests/cli.test.ts": self._generate_ts_test(config),
                ".gitignore": self._generate_gitignore(config),
            },
        }

    def _get_ts_library_template(self, config: ScaffoldingConfig) -> Dict[str, Any]:
        """Generate TypeScript library project structure."""
        return {
            "directories": [
                "src",
                "tests",
            ],
            "files": {
                "README.md": self._generate_readme(config),
                "package.json": self._generate_ts_package_json(config),
                "tsconfig.json": self._generate_tsconfig_json(config),
                "src/index.ts": self._generate_ts_index(config),
                "tests/index.test.ts": self._generate_ts_test(config),
                ".gitignore": self._generate_gitignore(config),
            },
        }

    # File content generators

    def _generate_readme(self, config: ScaffoldingConfig) -> str:
        """Generate README content."""
        return f"""# {config.project_name}

{config.project_name} is a {config.language} {config.framework or ""} application.

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd {config.project_name}

# Install dependencies
```

## Usage

```bash
# Start the application
```

## Development

```bash
# Run tests
```

## License

MIT
"""

    def _generate_pyproject_toml(self, config: ScaffoldingConfig) -> str:
        """Generate pyproject.toml content."""
        deps = []
        if config.framework == "fastapi":
            deps = [
                '"fastapi>=0.100.0"',
                '"uvicorn[standard]>=0.23.0"',
                '"pydantic>=2.0.0"',
            ]
        elif config.framework == "flask":
            deps = ['"flask>=2.3.0"', '"flask-cors>=4.0.0"']

        deps_str = "\n    ".join(deps) if deps else ""

        return f"""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{self._slugify(config.project_name)}"
version = "0.1.0"
description = "{config.project_name}"
readme = "README.md"
requires-python = ">={config.python_version}"
license = "MIT"
authors = [
    {{name = "Developer", email = "dev@example.com"}},
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: {config.python_version}",
]
dependencies = [
    {deps_str}
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "mypy>=1.0.0",
    "ruff>=0.1.0",
]

[tool.black]
line-length = 88
target-version = ['py{config.python_version.replace(".", "")}']

[tool.mypy]
python_version = "{config.python_version}"
strict = true

[tool.ruff]
line-length = 88
select = ["E", "F", "I", "N", "W"]
"""

    def _generate_pyproject_toml_cli(self, config: ScaffoldingConfig) -> str:
        """Generate pyproject.toml for CLI project."""
        return f"""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{self._slugify(config.project_name)}"
version = "0.1.0"
description = "{config.project_name}"
readme = "README.md"
requires-python = ">={config.python_version}"
license = "MIT"
dependencies = [
    "click>=8.0.0",
    "rich>=13.0.0",
]

[project.scripts]
{self._slugify(config.project_name)} = "{self._slugify(config.project_name)}.cli:main"

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "black>=23.0.0",
    "mypy>=1.0.0",
]
"""

    def _generate_env_example(self, config: ScaffoldingConfig) -> str:
        """Generate .env.example content."""
        env_vars = ["# Environment Variables"]

        if config.framework in ["fastapi", "flask", "express"]:
            env_vars.extend(
                [
                    "APP_ENV=development",
                    "PORT=8000",
                    "HOST=0.0.0.0",
                ]
            )

        if config.extra_options.get("include_database"):
            env_vars.extend(
                [
                    "DATABASE_URL=postgresql://user:pass@localhost/dbname",
                ]
            )

        if config.extra_options.get("include_redis"):
            env_vars.extend(
                [
                    "REDIS_URL=redis://localhost:6379/0",
                ]
            )

        return "\n".join(env_vars)

    def _generate_fastapi_main(self, config: ScaffoldingConfig) -> str:
        """Generate FastAPI main.py content."""
        project_slug = self._slugify(config.project_name)
        return f'''"""FastAPI application main module."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from {project_slug}.core.config import settings
from {project_slug}.routers import health

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="{config.project_name} API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["health"])


@app.get("/")
async def root():
    return {{"message": "Welcome to {config.project_name}"}}
'''

    def _generate_flask_app(self, config: ScaffoldingConfig) -> str:
        """Generate Flask app.py content."""
        return f'''"""Flask application factory."""

from flask import Flask
from flask_cors import CORS

from {self._slugify(config.project_name)}.routes.main import main_bp


def create_app():
    app = Flask(__name__)
    CORS(app)
    
    app.register_blueprint(main_bp)
    
    return app
'''

    def _generate_flask_routes(self, config: ScaffoldingConfig) -> str:
        """Generate Flask routes."""
        return '''"""Main routes."""

from flask import Blueprint, jsonify

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return jsonify({'message': 'Hello, World!'})


@main_bp.route('/health')
def health():
    return jsonify({'status': 'healthy'})
'''

    def _generate_config_py(self, config: ScaffoldingConfig) -> str:
        """Generate config.py content."""
        return f'''"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "{config.project_name}"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    ALLOWED_HOSTS: list[str] = ["*"]
    
    class Config:
        env_file = ".env"


settings = Settings()
'''

    def _generate_health_router(self, config: ScaffoldingConfig) -> str:
        """Generate health check router."""
        return '''"""Health check router."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def health_check():
    return {"status": "healthy", "service": "ok"}


@router.get("/ready")
async def readiness_check():
    return {"ready": True}


@router.get("/live")
async def liveness_check():
    return {"alive": True}
'''

    def _generate_python_cli(self, config: ScaffoldingConfig) -> str:
        """Generate Python CLI."""
        project_slug = self._slugify(config.project_name)
        return f'''"""CLI entry point for {config.project_name}."""

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """{config.project_name} CLI tool."""
    pass


@cli.command()
def hello():
    """Say hello."""
    console.print("[bold green]Hello from {config.project_name}![/bold green]")


@cli.command()
def info():
    """Show application info."""
    table = Table(title="Application Information")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="magenta")
    table.add_row("Name", "{config.project_name}")
    table.add_row("Version", "0.1.0")
    console.print(table)


def main():
    cli()


if __name__ == "__main__":
    main()
'''

    def _generate_test_main(self, config: ScaffoldingConfig) -> str:
        """Generate main test file."""
        return '''"""Tests for main module."""

import pytest


def test_hello():
    assert True


def test_basic_functionality():
    result = 2 + 2
    assert result == 4
'''

    def _generate_test_flask(self, config: ScaffoldingConfig) -> str:
        """Generate Flask test file."""
        return '''"""Tests for Flask application."""

import pytest
from {project_slug}.app import create_app


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_index(client):
    response = client.get('/')
    assert response.status_code == 200


def test_health(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'
'''.format(project_slug=self._slugify(config.project_name))

    def _generate_test_cli(self, config: ScaffoldingConfig) -> str:
        """Generate CLI test file."""
        from click.testing import CliRunner

        return '''"""Tests for CLI."""

from click.testing import CliRunner
from {project_slug}.cli import cli


def test_hello():
    runner = CliRunner()
    result = runner.invoke(cli, ['hello'])
    assert result.exit_code == 0
    assert 'Hello' in result.output


def test_info():
    runner = CliRunner()
    result = runner.invoke(cli, ['info'])
    assert result.exit_code == 0
    assert 'Application Information' in result.output
'''.format(project_slug=self._slugify(config.project_name))

    def _generate_package_json(self, config: ScaffoldingConfig) -> str:
        """Generate package.json content."""
        deps = {}
        if config.framework == "express":
            deps = {
                "express": "^4.18.2",
                "cors": "^2.8.5",
                "helmet": "^7.0.0",
                "dotenv": "^16.3.1",
            }

        return json.dumps(
            {
                "name": self._slugify(config.project_name),
                "version": "0.1.0",
                "description": config.project_name,
                "main": "src/index.js",
                "scripts": {
                    "start": "node src/index.js",
                    "dev": "nodemon src/index.js",
                    "test": "jest",
                    "lint": "eslint src/",
                },
                "dependencies": deps,
                "devDependencies": {
                    "jest": "^29.0.0",
                    "eslint": "^8.0.0",
                    "nodemon": "^3.0.0",
                },
                "engines": {"node": f">={config.node_version}"},
            },
            indent=2,
        )

    def _generate_ts_package_json(self, config: ScaffoldingConfig) -> str:
        """Generate TypeScript package.json content."""
        deps = {}
        if config.framework == "express":
            deps = {
                "express": "^4.18.2",
                "@types/express": "^4.17.17",
                "cors": "^2.8.5",
                "helmet": "^7.0.0",
                "dotenv": "^16.3.1",
            }

        return json.dumps(
            {
                "name": self._slugify(config.project_name),
                "version": "0.1.0",
                "description": config.project_name,
                "main": "dist/index.js",
                "scripts": {
                    "build": "tsc",
                    "start": "node dist/index.js",
                    "dev": "ts-node-dev --respawn src/index.ts",
                    "test": "jest",
                    "lint": "eslint src/",
                },
                "dependencies": deps,
                "devDependencies": {
                    "typescript": "^5.0.0",
                    "@types/node": "^20.0.0",
                    "ts-node-dev": "^2.0.0",
                    "jest": "^29.0.0",
                    "ts-jest": "^29.0.0",
                    "@types/jest": "^29.0.0",
                    "eslint": "^8.0.0",
                    "@typescript-eslint/eslint-plugin": "^6.0.0",
                    "@typescript-eslint/parser": "^6.0.0",
                },
                "engines": {"node": f">={config.node_version}"},
            },
            indent=2,
        )

    def _generate_tsconfig_json(self, config: ScaffoldingConfig) -> str:
        """Generate tsconfig.json content."""
        return json.dumps(
            {
                "compilerOptions": {
                    "target": "ES2020",
                    "module": "commonjs",
                    "lib": ["ES2020"],
                    "outDir": "./dist",
                    "rootDir": "./src",
                    "strict": True,
                    "esModuleInterop": True,
                    "skipLibCheck": True,
                    "forceConsistentCasingInFileNames": True,
                    "resolveJsonModule": True,
                    "declaration": True,
                    "declarationMap": True,
                    "sourceMap": True,
                },
                "include": ["src/**/*"],
                "exclude": ["node_modules", "dist", "tests"],
            },
            indent=2,
        )

    def _generate_nestjs_package_json(self, config: ScaffoldingConfig) -> str:
        """Generate NestJS package.json content."""
        return json.dumps(
            {
                "name": self._slugify(config.project_name),
                "version": "0.1.0",
                "description": config.project_name,
                "scripts": {
                    "build": "nest build",
                    "start": "nest start",
                    "start:dev": "nest start --watch",
                    "start:debug": "nest start --debug --watch",
                    "start:prod": "node dist/main",
                    "test": "jest",
                    "test:e2e": "jest --config ./test/jest-e2e.json",
                },
                "dependencies": {
                    "@nestjs/common": "^10.0.0",
                    "@nestjs/core": "^10.0.0",
                    "@nestjs/platform-express": "^10.0.0",
                    "reflect-metadata": "^0.1.13",
                    "rxjs": "^7.8.1",
                },
                "devDependencies": {
                    "@nestjs/cli": "^10.0.0",
                    "@nestjs/schematics": "^10.0.0",
                    "@nestjs/testing": "^10.0.0",
                    "@types/express": "^4.17.17",
                    "@types/jest": "^29.5.2",
                    "@types/node": "^20.3.1",
                    "jest": "^29.5.0",
                    "ts-jest": "^29.1.0",
                    "typescript": "^5.1.3",
                },
            },
            indent=2,
        )

    def _generate_nest_cli_json(self, config: ScaffoldingConfig) -> str:
        """Generate nest-cli.json content."""
        return json.dumps(
            {
                "$schema": "https://json.schemastore.org/nest-cli",
                "collection": "@nestjs/schematics",
                "sourceRoot": "src",
            },
            indent=2,
        )

    def _generate_nestjs_main(self, config: ScaffoldingConfig) -> str:
        """Generate NestJS main.ts content."""
        return """import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  await app.listen(3000);
}
bootstrap();
"""

    def _generate_nestjs_app_module(self, config: ScaffoldingConfig) -> str:
        """Generate NestJS app.module.ts content."""
        return """import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';

@Module({
  imports: [],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
"""

    def _generate_nestjs_app_controller(self, config: ScaffoldingConfig) -> str:
        """Generate NestJS app.controller.ts content."""
        return """import { Controller, Get } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  getHello(): string {
    return this.appService.getHello();
  }
}
"""

    def _generate_nestjs_app_service(self, config: ScaffoldingConfig) -> str:
        """Generate NestJS app.service.ts content."""
        return """import { Injectable } from '@nestjs/common';

@Injectable()
export class AppService {
  getHello(): string {
    return 'Hello World!';
  }
}
"""

    def _generate_nestjs_e2e_test(self, config: ScaffoldingConfig) -> str:
        """Generate NestJS e2e test content."""
        return """import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import * as request from 'supertest';
import { AppModule } from './../src/app.module';

describe('AppController (e2e)', () => {
  let app: INestApplication;

  beforeEach(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleFixture.createNestApplication();
    await app.init();
  });

  it('/ (GET)', () => {
    return request(app.getHttpServer())
      .get('/')
      .expect(200)
      .expect('Hello World!');
  });
});
"""

    def _generate_express_main(self, config: ScaffoldingConfig) -> str:
        """Generate Express main.js content."""
        return """const app = require('./app');

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
"""

    def _generate_express_app(self, config: ScaffoldingConfig) -> str:
        """Generate Express app.js content."""
        return """const express = require('express');
const cors = require('cors');
const helmet = require('helmet');

const routes = require('./routes');
const errorHandler = require('./middleware/errorHandler');

const app = express();

app.use(helmet());
app.use(cors());
app.use(express.json());

app.use('/', routes);
app.use(errorHandler);

module.exports = app;
"""

    def _generate_express_routes(self, config: ScaffoldingConfig) -> str:
        """Generate Express routes content."""
        return """const express = require('express');
const router = express.Router();

router.get('/', (req, res) => {
  res.json({ message: 'Hello, World!' });
});

router.get('/health', (req, res) => {
  res.json({ status: 'healthy' });
});

module.exports = router;
"""

    def _generate_express_error_handler(self, config: ScaffoldingConfig) -> str:
        """Generate Express error handler content."""
        return """const errorHandler = (err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Something went wrong!' });
};

module.exports = errorHandler;
"""

    def _generate_ts_express_main(self, config: ScaffoldingConfig) -> str:
        """Generate TypeScript Express main.ts content."""
        return """import app from './app';

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
"""

    def _generate_ts_express_app(self, config: ScaffoldingConfig) -> str:
        """Generate TypeScript Express app.ts content."""
        return """import express, { Application } from 'express';
import cors from 'cors';
import helmet from 'helmet';

import routes from './routes';
import errorHandler from './middleware/errorHandler';

const app: Application = express();

app.use(helmet());
app.use(cors());
app.use(express.json());

app.use('/', routes);
app.use(errorHandler);

export default app;
"""

    def _generate_ts_express_routes(self, config: ScaffoldingConfig) -> str:
        """Generate TypeScript Express routes content."""
        return """import { Router, Request, Response } from 'express';

const router = Router();

router.get('/', (req: Request, res: Response) => {
  res.json({ message: 'Hello, World!' });
});

router.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'healthy' });
});

export default router;
"""

    def _generate_ts_error_handler(self, config: ScaffoldingConfig) -> str:
        """Generate TypeScript error handler content."""
        return """import { Request, Response, NextFunction } from 'express';

const errorHandler = (err: Error, req: Request, res: Response, next: NextFunction) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Something went wrong!' });
};

export default errorHandler;
"""

    def _generate_js_test(self, config: ScaffoldingConfig) -> str:
        """Generate JavaScript test content."""
        return """const request = require('supertest');
const app = require('../src/app');

describe('App', () => {
  test('GET / should return hello message', async () => {
    const response = await request(app).get('/');
    expect(response.status).toBe(200);
    expect(response.body.message).toBe('Hello, World!');
  });

  test('GET /health should return healthy status', async () => {
    const response = await request(app).get('/health');
    expect(response.status).toBe(200);
    expect(response.body.status).toBe('healthy');
  });
});
"""

    def _generate_ts_test(self, config: ScaffoldingConfig) -> str:
        """Generate TypeScript test content."""
        return """import request from 'supertest';
import app from '../src/app';

describe('App', () => {
  test('GET / should return hello message', async () => {
    const response = await request(app).get('/');
    expect(response.status).toBe(200);
    expect(response.body.message).toBe('Hello, World!');
  });

  test('GET /health should return healthy status', async () => {
    const response = await request(app).get('/health');
    expect(response.status).toBe(200);
    expect(response.body.status).toBe('healthy');
  });
});
"""

    def _generate_js_cli(self, config: ScaffoldingConfig) -> str:
        """Generate JavaScript CLI content."""
        return """#!/usr/bin/env node

const {{ program }} = require('commander');
const {{ version }} = require('../package.json');

program
  .version(version)
  .description('CLI tool')
  .command('hello')
  .description('Say hello')
  .action(() => {
    console.log('Hello, World!');
  });

program.parse(process.argv);
"""

    def _generate_js_lib(self, config: ScaffoldingConfig) -> str:
        """Generate JavaScript library content."""
        return """function greet(name) {
  return `Hello, ${name}!`;
}

module.exports = { greet };
"""

    def _generate_ts_cli(self, config: ScaffoldingConfig) -> str:
        """Generate TypeScript CLI content."""
        return """import { Command } from 'commander';
import { greet } from './index';

const program = new Command();

program
  .version('0.1.0')
  .description('CLI tool');

program
  .command('hello')
  .description('Say hello')
  .action(() => {
    console.log(greet('World'));
  });

program.parse(process.argv);
"""

    def _generate_ts_index(self, config: ScaffoldingConfig) -> str:
        """Generate TypeScript index content."""
        return """export function greet(name: string): string {
  return `Hello, ${name}!`;
}
"""

    def _generate_js_cli_package_json(self, config: ScaffoldingConfig) -> str:
        """Generate JavaScript CLI package.json content."""
        return json.dumps(
            {
                "name": self._slugify(config.project_name),
                "version": "0.1.0",
                "description": config.project_name,
                "bin": {self._slugify(config.project_name): "./bin/cli.js"},
                "scripts": {"test": "jest"},
                "dependencies": {"commander": "^11.0.0"},
                "devDependencies": {"jest": "^29.0.0"},
                "engines": {"node": f">={config.node_version}"},
            },
            indent=2,
        )

    def _generate_ts_cli_package_json(self, config: ScaffoldingConfig) -> str:
        """Generate TypeScript CLI package.json content."""
        return json.dumps(
            {
                "name": self._slugify(config.project_name),
                "version": "0.1.0",
                "description": config.project_name,
                "bin": {self._slugify(config.project_name): "./bin/run"},
                "scripts": {"build": "tsc", "test": "jest"},
                "dependencies": {"commander": "^11.0.0"},
                "devDependencies": {
                    "typescript": "^5.0.0",
                    "@types/node": "^20.0.0",
                    "jest": "^29.0.0",
                    "ts-jest": "^29.0.0",
                },
                "engines": {"node": f">={config.node_version}"},
            },
            indent=2,
        )

    def _generate_go_mod(self, config: ScaffoldingConfig) -> str:
        """Generate go.mod content."""
        module_path = f"github.com/example/{self._slugify(config.project_name)}"

        deps = ""
        if config.framework == "gin":
            deps = """\n\nrequire (
\tgithub.com/gin-gonic/gin v1.9.1
)"""
        elif config.framework == "echo":
            deps = """\n\nrequire (
\tgithub.com/labstack/echo/v4 v4.11.0
)"""

        return f"""module {module_path}

go {config.go_version}{deps}
"""

    def _generate_go_main(self, config: ScaffoldingConfig) -> str:
        """Generate Go main.go content."""
        if config.framework == "gin":
            return """package main

import (
\t"github.com/gin-gonic/gin"
)

func main() {
\tr := gin.Default()
\t
\tr.GET("/", func(c *gin.Context) {
\t\tc.JSON(200, gin.H{
\t\t\t"message": "Hello, World!",
\t\t})
\t})
\t
\tr.GET("/health", func(c *gin.Context) {
\t\tc.JSON(200, gin.H{
\t\t\t"status": "healthy",
\t\t})
\t})
\t
\tr.Run(":8080")
}
"""
        else:
            return """package main

import (
\t"fmt"
\t"net/http"
)

func main() {
\thttp.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
\t\tfmt.Fprintf(w, "Hello, World!")
\t})
\t
\tfmt.Println("Server starting on :8080")
\thttp.ListenAndServe(":8080", nil)
}
"""

    def _generate_echo_main(self, config: ScaffoldingConfig) -> str:
        """Generate Echo main.go content."""
        return """package main

import (
\t"net/http"
\t
\t"github.com/labstack/echo/v4"
\t"github.com/labstack/echo/v4/middleware"
)

func main() {
\te := echo.New()
\t
\te.Use(middleware.Logger())
\te.Use(middleware.Recover())
\t
\te.GET("/", func(c echo.Context) error {
\t\treturn c.JSON(http.StatusOK, map[string]string{
\t\t\t"message": "Hello, World!",
\t\t})
\t})
\t
\te.GET("/health", func(c echo.Context) error {
\t\treturn c.JSON(http.StatusOK, map[string]string{
\t\t\t"status": "healthy",
\t\t})
\t})
\t
\te.Start(":8080")
}
"""

    def _generate_go_health_handler(self, config: ScaffoldingConfig) -> str:
        """Generate Go health handler content."""
        return """package handlers

import (
\t"net/http"
\t
\t"github.com/gin-gonic/gin"
)

// HealthCheck handles health check requests
func HealthCheck(c *gin.Context) {
\tc.JSON(http.StatusOK, gin.H{
\t\t"status": "healthy",
\t})
}
"""

    def _generate_echo_health_handler(self, config: ScaffoldingConfig) -> str:
        """Generate Echo health handler content."""
        return """package handlers

import (
\t"net/http"
\t
\t"github.com/labstack/echo/v4"
)

// HealthCheck handles health check requests
func HealthCheck(c echo.Context) error {
\treturn c.JSON(http.StatusOK, map[string]string{
\t\t"status": "healthy",
\t})
}
"""

    def _generate_go_cli_main(self, config: ScaffoldingConfig) -> str:
        """Generate Go CLI main.go content."""
        return """package main

import (
\t"fmt"
\t"os"
\t
\t"{module}/cmd"
)

func main() {
\tif err := cmd.Execute(); err != nil {
\t\tfmt.Fprintln(os.Stderr, err)
\t\tos.Exit(1)
\t}
}
""".format(module=f"github.com/example/{self._slugify(config.project_name)}")

    def _generate_go_cobra_root(self, config: ScaffoldingConfig) -> str:
        """Generate Go Cobra root command content."""
        return """package cmd

import (
\t"fmt"
\t"os"
\t
\t"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
\tUse:   "' + self._slugify(config.project_name) + '",
\tShort: "A CLI tool",
\tLong:  "A longer description of the CLI tool",
}

// Execute runs the root command
func Execute() error {
\treturn rootCmd.Execute()
}

func init() {
\trootCmd.AddCommand(helloCmd)
}

var helloCmd = &cobra.Command{
\tUse:   "hello",
\tShort: "Say hello",
\tRun: func(cmd *cobra.Command, args []string) {
\t\tfmt.Println("Hello, World!")
\t},
}
"""

    def _generate_gitignore(self, config: ScaffoldingConfig) -> str:
        """Generate .gitignore content."""
        if config.language == "python":
            return """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Environment
.env
.env.local

# Testing
.coverage
htmlcov/
.pytest_cache/
"""
        elif config.language in ["javascript", "typescript"]:
            return """# Dependencies
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Build outputs
dist/
build/
*.tsbuildinfo

# Environment
.env
.env.local

# IDE
.vscode/
.idea/
*.swp

# Testing
coverage/
.nyc_output/
"""
        elif config.language == "go":
            return """# Binaries
*.exe
*.exe~
*.dll
*.so
*.dylib

# Test binary
*.test

# Output of the go coverage tool
*.out

# Dependency directories
vendor/

# IDE
.vscode/
.idea/
*.swp

# Environment
.env
.env.local
"""
        else:
            return """# IDE
.vscode/
.idea/
*.swp

# Environment
.env
.env.local
"""

    def _slugify(self, text: str) -> str:
        """Convert text to slug format."""
        import re

        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[-\s]+", "_", text)
        return text
