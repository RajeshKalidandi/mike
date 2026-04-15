# src/mike/orchestrator/model_provider.py
"""Model provider abstraction for Mike.

Decouples agent logic from model backend. Enables loading any free/open
model (Gemma, Qwen, Llama, Mistral, etc.) through a unified interface.
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

CODE_MODEL_PATTERNS = [
    "coder", "code", "codellama", "starcoder", "deepseek-coder",
    "wizard-coder", "phind", "magicoder",
]


@dataclass
class ModelCapabilities:
    """Describes what a model can do."""
    max_context: int = 8192
    supports_json_mode: bool = False
    supports_tool_calling: bool = False
    supports_streaming: bool = True
    is_code_specialized: bool = False


class ModelProvider(ABC):
    """Abstract base class for model providers."""

    @abstractmethod
    def generate(self, prompt: str, system: Optional[str] = None, **kwargs) -> str:
        ...

    @abstractmethod
    def generate_json(self, prompt: str, system: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        ...

    @abstractmethod
    def capabilities(self) -> ModelCapabilities:
        ...

    @abstractmethod
    def model_name(self) -> str:
        ...


def _extract_json(text: str) -> Dict[str, Any]:
    """Extract JSON from text, handling markdown code fences."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start : brace_end + 1])
        except json.JSONDecodeError:
            pass

    logger.warning(f"Could not extract JSON from response: {text[:100]}...")
    return {}


def _is_code_model(model: str) -> bool:
    """Check if a model name indicates code specialization."""
    model_lower = model.lower()
    return any(pattern in model_lower for pattern in CODE_MODEL_PATTERNS)


class OllamaProvider(ModelProvider):
    """Provider for any Ollama-hosted model."""

    def __init__(
        self,
        model: str,
        endpoint: str = "http://localhost:11434",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float = 120.0,
    ):
        self._model = model
        self._endpoint = endpoint.rstrip("/")
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout

    def generate(self, prompt: str, system: Optional[str] = None, **kwargs) -> str:
        body: Dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self._temperature),
                "num_predict": kwargs.get("max_tokens", self._max_tokens),
            },
        }
        if system:
            body["system"] = system

        response = httpx.post(
            f"{self._endpoint}/api/generate",
            json=body,
            timeout=self._timeout,
        )
        response.raise_for_status()
        return response.json()["response"]

    def generate_json(self, prompt: str, system: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        raw = self.generate(prompt, system=system, **kwargs)
        return _extract_json(raw)

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            max_context=8192,
            supports_json_mode=False,
            supports_tool_calling=False,
            supports_streaming=True,
            is_code_specialized=_is_code_model(self._model),
        )

    def model_name(self) -> str:
        return self._model


class OpenAICompatibleProvider(ModelProvider):
    """Provider for OpenAI-compatible APIs (vLLM, LM Studio, Together, OpenRouter)."""

    def __init__(
        self,
        model: str,
        endpoint: str,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float = 120.0,
    ):
        self._model = model
        self._endpoint = endpoint.rstrip("/")
        self._api_key = api_key
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def generate(self, prompt: str, system: Optional[str] = None, **kwargs) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body = {
            "model": self._model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self._temperature),
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
        }

        response = httpx.post(
            f"{self._endpoint}/chat/completions",
            json=body,
            headers=self._headers(),
            timeout=self._timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def generate_json(self, prompt: str, system: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        raw = self.generate(prompt, system=system, **kwargs)
        return _extract_json(raw)

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            max_context=8192,
            supports_json_mode=True,
            supports_tool_calling=False,
            supports_streaming=True,
            is_code_specialized=_is_code_model(self._model),
        )

    def model_name(self) -> str:
        return self._model


class ModelRouter:
    """Task-aware model selection based on tags and capabilities."""

    CODE_TASKS = {"code_generation", "refactor", "rebuild", "code_review"}

    def __init__(
        self,
        providers: Dict[str, ModelProvider],
        default: str,
        tags: Optional[Dict[str, List[str]]] = None,
    ):
        self._providers = providers
        self._default = default
        self._tags = tags or {}

    def select(self, task_type: str, context_size: int = 0) -> ModelProvider:
        if context_size > 16000:
            for name, provider in self._providers.items():
                if (
                    "large_context" in self._tags.get(name, [])
                    and provider.capabilities().max_context >= context_size
                ):
                    return provider

        if task_type in self.CODE_TASKS:
            for name, provider in self._providers.items():
                if "code" in self._tags.get(name, []):
                    return provider

        return self._providers[self._default]

    def get(self, name: str) -> Optional[ModelProvider]:
        return self._providers.get(name)

    def list_providers(self) -> List[str]:
        return list(self._providers.keys())
