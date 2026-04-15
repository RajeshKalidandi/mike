# tests/unit/test_model_provider.py
"""Unit tests for ModelProvider abstraction."""

import json
import pytest
from unittest.mock import MagicMock, patch

from mike.orchestrator.model_provider import (
    ModelCapabilities,
    ModelProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    ModelRouter,
)


class TestModelCapabilities:
    def test_create_capabilities(self):
        caps = ModelCapabilities(
            max_context=8192,
            supports_json_mode=True,
            supports_tool_calling=False,
            supports_streaming=True,
            is_code_specialized=True,
        )
        assert caps.max_context == 8192
        assert caps.supports_json_mode is True
        assert caps.is_code_specialized is True


class TestOllamaProvider:
    def test_init_default_endpoint(self):
        provider = OllamaProvider(model="gemma3:12b")
        assert provider.model_name() == "gemma3:12b"
        assert provider._endpoint == "http://localhost:11434"

    def test_init_custom_endpoint(self):
        provider = OllamaProvider(model="qwen2.5-coder:14b", endpoint="http://gpu-box:11434")
        assert provider.model_name() == "qwen2.5-coder:14b"
        assert provider._endpoint == "http://gpu-box:11434"

    def test_capabilities_code_model(self):
        provider = OllamaProvider(model="qwen2.5-coder:14b")
        caps = provider.capabilities()
        assert caps.is_code_specialized is True

    def test_capabilities_general_model(self):
        provider = OllamaProvider(model="gemma3:12b")
        caps = provider.capabilities()
        assert caps.is_code_specialized is False

    @patch("mike.orchestrator.model_provider.httpx")
    def test_generate_calls_ollama_api(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Hello world"}
        mock_response.raise_for_status = MagicMock()
        mock_httpx.post.return_value = mock_response

        provider = OllamaProvider(model="gemma3:12b")
        result = provider.generate("Say hello")

        assert result == "Hello world"
        mock_httpx.post.assert_called_once()
        call_args = mock_httpx.post.call_args
        assert "/api/generate" in call_args[0][0]

    @patch("mike.orchestrator.model_provider.httpx")
    def test_generate_with_system_prompt(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "result"}
        mock_response.raise_for_status = MagicMock()
        mock_httpx.post.return_value = mock_response

        provider = OllamaProvider(model="gemma3:12b")
        provider.generate("query", system="You are helpful")

        call_body = mock_httpx.post.call_args[1]["json"]
        assert call_body["system"] == "You are helpful"

    @patch("mike.orchestrator.model_provider.httpx")
    def test_generate_json_parses_response(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": '{"key": "value"}'}
        mock_response.raise_for_status = MagicMock()
        mock_httpx.post.return_value = mock_response

        provider = OllamaProvider(model="gemma3:12b")
        result = provider.generate_json("Return JSON")

        assert result == {"key": "value"}

    @patch("mike.orchestrator.model_provider.httpx")
    def test_generate_json_handles_markdown_wrapped_json(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": '```json\n{"key": "value"}\n```'}
        mock_response.raise_for_status = MagicMock()
        mock_httpx.post.return_value = mock_response

        provider = OllamaProvider(model="gemma3:12b")
        result = provider.generate_json("Return JSON")

        assert result == {"key": "value"}

    @patch("mike.orchestrator.model_provider.httpx")
    def test_generate_json_returns_empty_on_invalid(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "not json at all"}
        mock_response.raise_for_status = MagicMock()
        mock_httpx.post.return_value = mock_response

        provider = OllamaProvider(model="gemma3:12b")
        result = provider.generate_json("Return JSON")

        assert result == {}


class TestOpenAICompatibleProvider:
    def test_init(self):
        provider = OpenAICompatibleProvider(
            model="llama-3.3-70b",
            endpoint="http://localhost:8000/v1",
            api_key="test-key",
        )
        assert provider.model_name() == "llama-3.3-70b"

    @patch("mike.orchestrator.model_provider.httpx")
    def test_generate_uses_chat_completions(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx.post.return_value = mock_response

        provider = OpenAICompatibleProvider(
            model="llama-3.3-70b", endpoint="http://localhost:8000/v1"
        )
        result = provider.generate("Say hello")

        assert result == "Hello"
        call_url = mock_httpx.post.call_args[0][0]
        assert "/chat/completions" in call_url


class TestModelRouter:
    def _make_provider(self, name, is_code=False, max_context=8192):
        provider = MagicMock(spec=ModelProvider)
        provider.model_name.return_value = name
        provider.capabilities.return_value = ModelCapabilities(
            max_context=max_context,
            supports_json_mode=True,
            supports_tool_calling=False,
            supports_streaming=True,
            is_code_specialized=is_code,
        )
        return provider

    def test_select_default(self):
        default = self._make_provider("default-model")
        router = ModelRouter(providers={"default": default}, default="default")
        selected = router.select("general")
        assert selected.model_name() == "default-model"

    def test_select_code_model_for_code_task(self):
        general = self._make_provider("general", is_code=False)
        coder = self._make_provider("coder", is_code=True)
        router = ModelRouter(
            providers={"general": general, "coder": coder},
            default="general",
            tags={"coder": ["code"]},
        )
        selected = router.select("code_generation")
        assert selected.model_name() == "coder"

    def test_select_largest_context_for_large_input(self):
        small = self._make_provider("small", max_context=4096)
        big = self._make_provider("big", max_context=128000)
        router = ModelRouter(
            providers={"small": small, "big": big},
            default="small",
            tags={"big": ["large_context"]},
        )
        selected = router.select("qa", context_size=32000)
        assert selected.model_name() == "big"

    def test_falls_back_to_default_when_no_tag_match(self):
        default = self._make_provider("default")
        router = ModelRouter(providers={"default": default}, default="default")
        selected = router.select("unknown_task_type")
        assert selected.model_name() == "default"
