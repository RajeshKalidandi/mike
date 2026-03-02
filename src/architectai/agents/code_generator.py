"""Code generation module for ArchitectAI.

Integrates with local LLMs (Ollama) to generate code files based on
templates and context. Handles prompt engineering, multi-file coordination,
and code validation.
"""

import json
import re
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class GenerationConfig:
    """Configuration for code generation."""

    model_name: str = "gemma3:12b"
    max_tokens: int = 8192
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    system_prompt: Optional[str] = None


class CodeGenerator:
    """
    Code generator using local LLM via Ollama.

    Handles:
    - Prompt engineering for code generation
    - Multi-file context coordination
    - Code validation and syntax checking
    - Retry logic for failed generations
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model_name: str = "gemma3:12b",
        max_tokens: int = 8192,
        temperature: float = 0.7,
        timeout: int = 120,
    ):
        """
        Initialize the code generator.

        Args:
            ollama_url: URL for Ollama API
            model_name: Name of the model to use
            max_tokens: Maximum tokens per generation
            temperature: Sampling temperature
            timeout: Request timeout in seconds
        """
        self.ollama_url = ollama_url.rstrip("/")
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.config = GenerationConfig(
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        logger.info(f"CodeGenerator initialized with model: {model_name}")

    def generate_file(
        self,
        file_spec: Any,
        context: Dict[str, Any],
        language: str,
        framework: Optional[str] = None,
        max_retries: int = 3,
    ) -> str:
        """
        Generate content for a single file.

        Args:
            file_spec: File specification (FileSpec object)
            context: Generation context (dependencies, templates, etc.)
            language: Target programming language
            framework: Optional target framework
            max_retries: Maximum retry attempts

        Returns:
            Generated code content
        """
        # Build prompt
        prompt = self._build_prompt(file_spec, context, language, framework)

        # Try generation with retries
        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"Generating {file_spec.path} (attempt {attempt + 1}/{max_retries})"
                )

                content = self._call_ollama(prompt)

                # Clean and validate content
                content = self._clean_generated_code(content, language)

                if self._validate_content(content, file_spec):
                    return content
                else:
                    logger.warning(
                        f"Generated content failed validation for {file_spec.path}"
                    )

            except Exception as e:
                logger.error(f"Generation failed for {file_spec.path}: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(1)  # Brief delay before retry

        raise RuntimeError(
            f"Failed to generate {file_spec.path} after {max_retries} attempts"
        )

    def _build_prompt(
        self,
        file_spec: Any,
        context: Dict[str, Any],
        language: str,
        framework: Optional[str],
    ) -> str:
        """Build generation prompt for the file."""

        # System instruction
        system_prompt = self._get_system_prompt(language)

        # File-specific context
        file_context = self._build_file_context(file_spec, context)

        # Build the complete prompt
        prompt_parts = [
            system_prompt,
            "",
            f"## Task",
            f"Generate {language} code for: {file_spec.path}",
            f"",
            f"## Purpose",
            f"{file_spec.purpose}",
            f"",
        ]

        # Add framework info if applicable
        if framework:
            prompt_parts.extend(
                [
                    f"## Framework",
                    f"This file is part of a {framework} {language} project.",
                    f"",
                ]
            )

        # Add project context
        prompt_parts.extend(
            [
                f"## Project Context",
                f"Project Name: {context.get('project_name', 'Unknown')}",
                f"Description: {context.get('project_description', 'N/A')}",
                f"Architecture Pattern: {context.get('architecture_pattern', 'generic')}",
                f"",
            ]
        )

        # Add constraints
        if context.get("constraints"):
            prompt_parts.extend(
                [
                    f"## Constraints",
                ]
            )
            for constraint in context["constraints"]:
                prompt_parts.append(f"- {constraint}")
            prompt_parts.append("")

        # Add template hints
        if file_spec.template_hints:
            prompt_parts.extend(
                [
                    f"## Template Hints",
                ]
            )
            for key, value in file_spec.template_hints.items():
                prompt_parts.append(f"- {key}: {value}")
            prompt_parts.append("")

        # Add dependency context
        if context.get("dependencies"):
            prompt_parts.extend(
                [
                    f"## Dependencies",
                    f"The following files have already been generated and may be imported:",
                    f"",
                ]
            )
            for dep_path, dep_content in list(context["dependencies"].items())[:3]:
                prompt_parts.extend(
                    [
                        f"### {dep_path}",
                        f"```{language}",
                        dep_content[:500] + "..."
                        if len(dep_content) > 500
                        else dep_content,
                        f"```",
                        f"",
                    ]
                )

        # Add template examples if available
        if context.get("template_examples"):
            prompt_parts.extend(
                [
                    f"## Example Code Style",
                    f"Here's an example of the code style used in this project:",
                    f"",
                ]
            )
            for template_name, template_content in list(
                context["template_examples"].items()
            )[:1]:
                prompt_parts.extend(
                    [
                        f"### {template_name}",
                        f"```{language}",
                        template_content[:800] + "..."
                        if len(template_content) > 800
                        else template_content,
                        f"```",
                        f"",
                    ]
                )

        # Add generation requirements
        prompt_parts.extend(
            [
                f"## Requirements",
                f"1. Generate complete, working {language} code",
                f"2. Include proper imports/dependencies",
                f"3. Add docstrings/comments where appropriate",
                f"4. Follow {language} best practices and conventions",
                f"5. Ensure code is syntactically correct",
            ]
        )

        if framework:
            prompt_parts.append(f"6. Follow {framework} conventions and patterns")

        prompt_parts.extend(
            [
                f"",
                f"## Output",
                f"Provide only the code, wrapped in ```{language} blocks. No explanations.",
            ]
        )

        return "\n".join(prompt_parts)

    def _get_system_prompt(self, language: str) -> str:
        """Get system prompt for the language."""
        prompts = {
            "python": """You are an expert Python developer. Generate clean, well-documented Python code following PEP 8 standards.
Use type hints where appropriate. Include proper docstrings following Google style.""",
            "javascript": """You are an expert JavaScript developer. Generate modern ES6+ JavaScript code.
Use async/await for asynchronous operations. Follow standard JS conventions.""",
            "typescript": """You are an expert TypeScript developer. Generate well-typed TypeScript code.
Use interfaces and types appropriately. Include proper JSDoc comments.""",
            "go": """You are an expert Go developer. Generate idiomatic Go code following Go conventions.
Include proper package comments. Handle errors explicitly.""",
            "rust": """You are an expert Rust developer. Generate idiomatic, safe Rust code.
Use proper error handling with Result types. Include documentation comments.""",
            "java": """You are an expert Java developer. Generate clean Java code following Java conventions.
Use proper class and method documentation.""",
        }

        return prompts.get(
            language,
            f"You are an expert {language} developer. Generate clean, well-documented code.",
        )

    def _build_file_context(
        self,
        file_spec: Any,
        context: Dict[str, Any],
    ) -> str:
        """Build context specific to the file being generated."""
        parts = []

        # File type-specific guidance
        if "test" in file_spec.path.lower():
            parts.append("This is a test file. Use appropriate testing framework.")

        if (
            "config" in file_spec.path.lower()
            or file_spec.path.endswith(".toml")
            or file_spec.path.endswith(".json")
        ):
            parts.append(
                "This is a configuration file. Include all necessary settings."
            )

        if "__init__" in file_spec.path:
            parts.append("This is a package initialization file.")

        return "\n".join(parts) if parts else ""

    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API for generation."""
        try:
            import requests
        except ImportError:
            logger.error(
                "requests library not installed. Install with: pip install requests"
            )
            raise

        url = f"{self.ollama_url}/api/generate"

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
                "top_p": self.config.top_p,
                "top_k": self.config.top_k,
                "repeat_penalty": self.config.repeat_penalty,
            },
        }

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()

            result = response.json()
            return result.get("response", "")

        except requests.exceptions.ConnectionError:
            logger.error(f"Could not connect to Ollama at {self.ollama_url}")
            logger.error("Make sure Ollama is running: ollama serve")
            raise RuntimeError(
                f"Ollama connection failed. Is it running at {self.ollama_url}?"
            )

        except requests.exceptions.Timeout:
            logger.error(f"Request to Ollama timed out after {self.timeout}s")
            raise RuntimeError(
                f"Ollama request timeout. Try increasing timeout or using a smaller model."
            )

        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            raise

    def _clean_generated_code(self, content: str, language: str) -> str:
        """Clean and extract code from model output."""
        # Try to extract code from markdown blocks
        patterns = [
            rf"```{language}\s*\n(.*?)```",  # Language-specific block
            r"```\s*\n(.*?)```",  # Generic code block
            r"```python\s*\n(.*?)```",
            r"```javascript\s*\n(.*?)```",
            r"```typescript\s*\n(.*?)```",
            r"```go\s*\n(.*?)```",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # If no code blocks found, return the content as-is
        # but remove common prefixes
        lines = content.split("\n")
        cleaned_lines = []

        for line in lines:
            # Remove common explanatory prefixes
            if line.strip().startswith(("Here is", "Below is", "This is")):
                continue
            if line.strip().startswith("```"):
                continue
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()

    def _validate_content(self, content: str, file_spec: Any) -> bool:
        """Validate generated content."""
        if not content or not content.strip():
            return False

        # Check minimum length
        if len(content) < 10:
            return False

        # Check for placeholder content
        placeholders = ["TODO", "FIXME", "...", "[insert", "placeholder"]
        content_lower = content.lower()
        placeholder_count = sum(1 for p in placeholders if p.lower() in content_lower)

        # Allow some placeholders but not too many
        if placeholder_count > 3:
            return False

        return True

    def generate_with_template(
        self,
        template: str,
        variables: Dict[str, str],
        language: str,
    ) -> str:
        """
        Generate code using a template with variable substitution.

        Args:
            template: Template string with {variable} placeholders
            variables: Dictionary of variable values
            language: Target language

        Returns:
            Generated code with substitutions
        """
        # First, substitute known variables
        content = template
        for key, value in variables.items():
            content = content.replace(f"{{{key}}}", value)

        # Check if there are remaining placeholders
        remaining = re.findall(r"\{([a-zA-Z_]+)\}", content)

        if remaining:
            # Generate content for remaining placeholders
            prompt = f"""Fill in the following {language} code template:

{content}

Missing values: {", ".join(remaining)}

Generate the complete code with all placeholders filled in."""

            generated = self._call_ollama(prompt)
            content = self._clean_generated_code(generated, language)

        return content

    def batch_generate(
        self,
        file_specs: List[Any],
        context: Dict[str, Any],
        language: str,
        framework: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Generate multiple files in batch.

        Args:
            file_specs: List of file specifications
            context: Generation context
            language: Target language
            framework: Optional framework

        Returns:
            Dictionary mapping file paths to generated content
        """
        results = {}

        for file_spec in file_specs:
            try:
                content = self.generate_file(file_spec, context, language, framework)
                results[file_spec.path] = content

                # Add to context for subsequent files
                context["dependencies"][file_spec.path] = content

            except Exception as e:
                logger.error(f"Failed to generate {file_spec.path}: {e}")
                results[file_spec.path] = None

        return results

    def check_model_availability(self) -> bool:
        """Check if the configured model is available in Ollama."""
        try:
            import requests

            response = requests.get(
                f"{self.ollama_url}/api/tags",
                timeout=10,
            )
            response.raise_for_status()

            models = response.json().get("models", [])
            available_models = [m.get("name") for m in models]

            # Check for exact match or partial match
            for model in available_models:
                if self.model_name in model or model in self.model_name:
                    return True

            logger.warning(
                f"Model {self.model_name} not found. Available models: {available_models}"
            )
            return False

        except Exception as e:
            logger.error(f"Failed to check model availability: {e}")
            return False

    def pull_model(self) -> bool:
        """Pull the configured model from Ollama."""
        try:
            import requests

            logger.info(f"Pulling model: {self.model_name}")

            response = requests.post(
                f"{self.ollama_url}/api/pull",
                json={"name": self.model_name, "stream": False},
                timeout=300,
            )
            response.raise_for_status()

            logger.info(f"Successfully pulled model: {self.model_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to pull model: {e}")
            return False

    def list_available_models(self) -> List[str]:
        """List all available models in Ollama."""
        try:
            import requests

            response = requests.get(
                f"{self.ollama_url}/api/tags",
                timeout=10,
            )
            response.raise_for_status()

            models = response.json().get("models", [])
            return [m.get("name") for m in models]

        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
