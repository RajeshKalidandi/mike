"""Documentation generation engine."""

from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, PackageLoader, BaseLoader, DictLoader

from .aggregator import DataAggregator


class DocumentationGenerator:
    """Generates documentation from codebase analysis."""

    def __init__(self, db):
        """Initialize generator with database."""
        self.db = db
        self.aggregator = DataAggregator(db)

        # Setup Jinja2 environment
        template_dir = Path(__file__).parent / "templates"

        # Try to load from filesystem first, fall back to inline templates
        if template_dir.exists():
            self.env = Environment(loader=FileSystemLoader(str(template_dir)))
        else:
            # Use inline templates as fallback
            self.env = Environment(loader=DictLoader(self._get_inline_templates()))

    def _get_inline_templates(self) -> Dict[str, str]:
        """Get inline templates for fallback."""
        return {
            "README.md.j2": """# {{ project_name }}

## Overview

This project contains {{ summary.total_files }} file(s) with {{ summary.total_lines }} total lines of code.

{% for lang, count in summary.languages.items() %}- {{ lang }}: {{ count }} file(s)
{% endfor %}

## File Structure

```
{{ file_tree | format_tree }}
```

## Generation Info

- Generated at: {{ generation_time }}
- Session ID: {{ session_id }}
""",
            "ARCHITECTURE.md.j2": """# Architecture Overview

## Module Tree

```
{{ module_tree }}
```

## Directory Structure

{% for dir, files in directory_structure.items() %}
### {{ dir }}

{% for file in files %}- `{{ file.name }}` ({{ file.language }}, {{ file.lines }} lines)
{% endfor %}
{% endfor %}

## Components

{% if components %}
{% for component in components %}- {{ component }}
{% endfor %}
{% else %}
Components will be listed here once dependency analysis is complete.
{% endif %}

## Dependencies

{% if dependencies %}
{% for dep in dependencies %}- {{ dep }}
{% endfor %}
{% else %}
Dependency analysis pending.
{% endif %}

---
Generated at: {{ generation_time }}
""",
            "API_REFERENCE.md.j2": """# API Reference

## Functions

{% if functions %}
{% for func in functions %}
### {{ func.name }}

{{ func.signature }}

{{ func.docstring }}

---
{% endfor %}
{% else %}
Function documentation will be generated when AST parsing data is available.
{% endif %}

## Classes

{% if classes %}
{% for cls in classes %}
### {{ cls.name }}

{{ cls.docstring }}

---
{% endfor %}
{% else %}
Class documentation will be generated when AST parsing data is available.
{% endif %}

## Imports

{% if imports %}
{% for imp in imports %}- {{ imp }}
{% endfor %}
{% else %}
Import analysis pending.
{% endif %}

---
Generated at: {{ generation_time }}
""",
            "ENV_GUIDE.md.j2": """# Environment Guide

## Configuration Files

{% if config_files %}
{% for config in config_files %}
### {{ config.name }}

- Path: `{{ config.path }}`
- Type: {{ config.type }}

{% endfor %}
{% else %}
No configuration files detected.
{% endif %}

## Environment Variables

{% if env_variables %}
{% for var in env_variables %}
### {{ var.name }}

- Description: {{ var.description }}
- Default: {{ var.default }}
- Required: {{ var.required }}

{% endfor %}
{% else %}
Environment variable detection pending AST parsing.
{% endif %}

---
Generated at: {{ generation_time }}
""",
        }

    def generate_and_save(
        self, session_id: str, doc_type: str, project_name: Optional[str] = None
    ) -> int:
        """Generate documentation and save to database.

        Args:
            session_id: Session ID
            doc_type: Type of documentation (README, ARCHITECTURE, API_REFERENCE, ENV_GUIDE)
            project_name: Optional project name override

        Returns:
            Documentation record ID
        """
        if doc_type == "README":
            content = self.generate_readme(session_id, project_name)
            title = f"{project_name or 'Project'} README"
            file_path = "README.md"
        elif doc_type == "ARCHITECTURE":
            content = self.generate_architecture(session_id)
            title = "Architecture Overview"
            file_path = "ARCHITECTURE.md"
        elif doc_type == "API_REFERENCE":
            content = self.generate_api_reference(session_id)
            title = "API Reference"
            file_path = "API_REFERENCE.md"
        elif doc_type == "ENV_GUIDE":
            content = self.generate_env_guide(session_id)
            title = "Environment Guide"
            file_path = "ENV_GUIDE.md"
        else:
            raise ValueError(f"Unknown doc type: {doc_type}")

        # Save to database
        doc_id = self.db.save_documentation(
            session_id=session_id,
            doc_type=doc_type,
            title=title,
            content=content,
            file_path=file_path,
        )

        return doc_id

    def generate_readme(
        self, session_id: str, project_name: Optional[str] = None
    ) -> str:
        """Generate README.md content."""
        # Get aggregated data
        summary = self.aggregator.aggregate_session_data(session_id)

        # Get session info for project name
        session = self.db.get_session(session_id)
        if project_name is None and session:
            # Extract project name from source path
            source_path = session.get("source_path", "")
            project_name = Path(source_path).name or "Project"
        project_name = project_name or "Project"

        # Build template data
        template_data = {
            "project_name": project_name,
            "summary": summary,
            "file_tree": summary["file_tree"],
            "generation_time": datetime.now().isoformat(),
            "session_id": session_id[:8],
        }

        # Add custom filter for tree formatting
        def format_tree(tree, indent=0):
            lines = []
            for key, value in tree.items():
                if key == "__files__":
                    for file_info in value:
                        lines.append("  " * indent + f"- {file_info['name']}")
                else:
                    lines.append("  " * indent + f"📁 {key}/")
                    if isinstance(value, dict):
                        lines.append(format_tree(value, indent + 1))
            return "\n".join(lines)

        template = self.env.get_template("README.md.j2")
        # Add the filter to the template context
        template_data["format_tree"] = format_tree
        return template.render(**template_data)

    def generate_architecture(self, session_id: str) -> str:
        """Generate ARCHITECTURE.md content."""
        summary = self.aggregator.aggregate_session_data(session_id)
        files = summary["files"]

        # Build directory structure
        directory_structure = {}
        for file_info in files:
            path = file_info["relative_path"]
            dir_path = str(Path(path).parent)
            if dir_path == ".":
                dir_path = "root"

            if dir_path not in directory_structure:
                directory_structure[dir_path] = []

            directory_structure[dir_path].append(
                {
                    "name": Path(path).name,
                    "language": file_info.get("language", "Unknown"),
                    "lines": file_info.get("line_count", 0),
                }
            )

        template_data = {
            "module_tree": self._format_tree(summary["file_tree"]),
            "directory_structure": directory_structure,
            "components": [],  # Will be populated when dependency analysis is added
            "dependencies": [],  # Will be populated when dependency analysis is added
            "generation_time": datetime.now().isoformat(),
        }

        template = self.env.get_template("ARCHITECTURE.md.j2")
        return template.render(**template_data)

    def generate_api_reference(self, session_id: str) -> str:
        """Generate API_REFERENCE.md content."""
        # Note: Full API reference requires parsing function signatures
        # For now, create a placeholder structure

        template_data = {
            "functions": [],  # Will be populated from parsed AST data
            "classes": [],  # Will be populated from parsed AST data
            "imports": [],  # Will be populated from parsed AST data
            "generation_time": datetime.now().isoformat(),
        }

        template = self.env.get_template("API_REFERENCE.md.j2")
        return template.render(**template_data)

    def generate_env_guide(self, session_id: str) -> str:
        """Generate ENV_GUIDE.md content."""
        summary = self.aggregator.aggregate_session_data(session_id)

        # Detect config files
        config_files = []
        config_patterns = [
            ".env",
            ".env.example",
            ".env.local",
            "config.yaml",
            "config.yml",
            "config.json",
            "settings.py",
            "settings.toml",
            "settings.ini",
            "docker-compose.yml",
            "Dockerfile",
        ]

        for file_info in summary["files"]:
            filename = Path(file_info["relative_path"]).name
            if any(
                filename.endswith(pattern) or filename == pattern
                for pattern in config_patterns
            ):
                config_files.append(
                    {
                        "name": filename,
                        "path": file_info["relative_path"],
                        "type": file_info.get("language", "Config"),
                    }
                )

        template_data = {
            "config_files": config_files,
            "env_variables": [],  # Will be populated when env var detection is added
            "generation_time": datetime.now().isoformat(),
        }

        template = self.env.get_template("ENV_GUIDE.md.j2")
        return template.render(**template_data)

    def _format_tree(self, tree: Dict, indent: int = 0) -> str:
        """Format file tree for display."""
        lines = []
        for key, value in tree.items():
            if key == "__files__":
                for file_info in value:
                    lines.append("  " * indent + f"- {file_info['name']}")
            else:
                lines.append("  " * indent + f"📁 {key}/")
                if isinstance(value, dict):
                    lines.append(self._format_tree(value, indent + 1))
        return "\n".join(lines)

    def generate_all(
        self, session_id: str, project_name: Optional[str] = None
    ) -> Dict[str, int]:
        """Generate all documentation types.

        Returns:
            Dict mapping doc_type to doc_id
        """
        results = {}

        for doc_type in ["README", "ARCHITECTURE", "API_REFERENCE", "ENV_GUIDE"]:
            doc_id = self.generate_and_save(session_id, doc_type, project_name)
            results[doc_type] = doc_id

        return results
