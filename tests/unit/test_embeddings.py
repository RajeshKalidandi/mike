"""Unit tests for the Embedding Service module."""

import pytest
from unittest.mock import MagicMock, patch

from architectai.embeddings.service import EmbeddingService


class TestEmbeddingService:
    """Test cases for EmbeddingService."""

    def test_service_initialization_defaults(self):
        """Test service initialization with defaults."""
        with patch("architectai.embeddings.service.ollama.Client") as MockClient:
            service = EmbeddingService()

            assert service.model == "mxbai-embed-large"
            assert service.dimension == 1024
            MockClient.assert_called_once()

    def test_service_initialization_custom_model(self):
        """Test service initialization with custom model."""
        with patch("architectai.embeddings.service.ollama.Client"):
            service = EmbeddingService(model="nomic-embed-text")

            assert service.model == "nomic-embed-text"
            assert service.dimension == 768

    def test_service_initialization_custom_host(self):
        """Test service initialization with custom host."""
        with patch("architectai.embeddings.service.ollama.Client") as MockClient:
            service = EmbeddingService(host="http://custom:11434")

            MockClient.assert_called_once_with(host="http://custom:11434")

    def test_embed_single_text(self, mock_ollama_client):
        """Test embedding a single text."""
        with patch(
            "architectai.embeddings.service.ollama.Client",
            return_value=mock_ollama_client,
        ):
            service = EmbeddingService()
            result = service.embed("test text")

            assert len(result) == 1024
            assert all(isinstance(x, float) for x in result)
            mock_ollama_client.embeddings.assert_called_once_with(
                model="mxbai-embed-large", prompt="test text"
            )

    def test_embed_handles_error(self, mock_ollama_client):
        """Test that embedding error returns zero vector."""
        mock_ollama_client.embeddings.side_effect = Exception("Connection failed")

        with patch(
            "architectai.embeddings.service.ollama.Client",
            return_value=mock_ollama_client,
        ):
            service = EmbeddingService()
            result = service.embed("test text")

            assert len(result) == 1024
            assert all(x == 0.0 for x in result)

    def test_embed_batch(self, mock_ollama_client):
        """Test embedding multiple texts."""
        with patch(
            "architectai.embeddings.service.ollama.Client",
            return_value=mock_ollama_client,
        ):
            service = EmbeddingService()
            texts = ["text 1", "text 2", "text 3"]
            result = service.embed_batch(texts)

            assert len(result) == 3
            assert all(len(emb) == 1024 for emb in result)

    def test_embed_batch_custom_size(self, mock_ollama_client):
        """Test embedding with custom batch size."""
        with patch(
            "architectai.embeddings.service.ollama.Client",
            return_value=mock_ollama_client,
        ):
            service = EmbeddingService()
            texts = ["text 1", "text 2"]
            result = service.embed_batch(texts, batch_size=1)

            assert len(result) == 2

    def test_embed_chunks(self, mock_ollama_client):
        """Test embedding code chunks."""
        with patch(
            "architectai.embeddings.service.ollama.Client",
            return_value=mock_ollama_client,
        ):
            service = EmbeddingService()
            chunks = [
                {"content": "chunk 1", "metadata": {}},
                {"content": "chunk 2", "metadata": {}},
            ]
            result = service.embed_chunks(chunks)

            assert len(result) == 2
            assert "embedding" in result[0]
            assert "embedding" in result[1]
            assert len(result[0]["embedding"]) == 1024

    def test_check_model_available_true(self, mock_ollama_client):
        """Test checking if model is available (true case)."""
        with patch(
            "architectai.embeddings.service.ollama.Client",
            return_value=mock_ollama_client,
        ):
            service = EmbeddingService(model="mxbai-embed-large")
            result = service.check_model_available()

            assert result is True

    def test_check_model_available_false(self, mock_ollama_client):
        """Test checking if model is available (false case)."""
        mock_ollama_client.list.return_value = {"models": [{"name": "other-model"}]}

        with patch(
            "architectai.embeddings.service.ollama.Client",
            return_value=mock_ollama_client,
        ):
            service = EmbeddingService(model="mxbai-embed-large")
            result = service.check_model_available()

            assert result is False

    def test_check_model_available_with_latest_tag(self, mock_ollama_client):
        """Test checking model availability with :latest tag."""
        mock_ollama_client.list.return_value = {
            "models": [{"name": "mxbai-embed-large:latest"}]
        }

        with patch(
            "architectai.embeddings.service.ollama.Client",
            return_value=mock_ollama_client,
        ):
            service = EmbeddingService(model="mxbai-embed-large")
            result = service.check_model_available()

            assert result is True

    def test_check_model_available_error(self, mock_ollama_client):
        """Test checking model availability when client fails."""
        mock_ollama_client.list.side_effect = Exception("Connection failed")

        with patch(
            "architectai.embeddings.service.ollama.Client",
            return_value=mock_ollama_client,
        ):
            service = EmbeddingService()
            result = service.check_model_available()

            assert result is False

    def test_get_available_models(self):
        """Test getting list of available models."""
        models = EmbeddingService.get_available_models()

        assert isinstance(models, list)
        assert "nomic-embed-text" in models
        assert "mxbai-embed-large" in models
        assert "bge-m3" in models
        assert "snowflake-arctic-embed" in models

    def test_get_model_dimension(self):
        """Test getting dimension for known models."""
        assert EmbeddingService.get_model_dimension("nomic-embed-text") == 768
        assert EmbeddingService.get_model_dimension("mxbai-embed-large") == 1024
        assert EmbeddingService.get_model_dimension("bge-m3") == 1024
        assert EmbeddingService.get_model_dimension("snowflake-arctic-embed") == 768

    def test_get_model_dimension_unknown(self):
        """Test getting dimension for unknown model returns default."""
        assert EmbeddingService.get_model_dimension("unknown-model") == 1024

    def test_model_dimension_property(self):
        """Test model dimension property."""
        with patch("architectai.embeddings.service.ollama.Client"):
            service_nomic = EmbeddingService(model="nomic-embed-text")
            service_mxbai = EmbeddingService(model="mxbai-embed-large")

            assert service_nomic.dimension == 768
            assert service_mxbai.dimension == 1024

    def test_models_class_attribute(self):
        """Test MODELS class attribute."""
        assert isinstance(EmbeddingService.MODELS, dict)
        assert "nomic-embed-text" in EmbeddingService.MODELS
        assert "mxbai-embed-large" in EmbeddingService.MODELS
        assert EmbeddingService.MODELS["nomic-embed-text"] == 768
        assert EmbeddingService.MODELS["mxbai-embed-large"] == 1024

    def test_embed_empty_text(self, mock_ollama_client):
        """Test embedding empty text."""
        with patch(
            "architectai.embeddings.service.ollama.Client",
            return_value=mock_ollama_client,
        ):
            service = EmbeddingService()
            result = service.embed("")

            assert len(result) == 1024

    def test_embed_batch_empty_list(self, mock_ollama_client):
        """Test embedding empty batch."""
        with patch(
            "architectai.embeddings.service.ollama.Client",
            return_value=mock_ollama_client,
        ):
            service = EmbeddingService()
            result = service.embed_batch([])

            assert result == []

    def test_embed_chunks_empty_list(self, mock_ollama_client):
        """Test embedding empty chunks list."""
        with patch(
            "architectai.embeddings.service.ollama.Client",
            return_value=mock_ollama_client,
        ):
            service = EmbeddingService()
            result = service.embed_chunks([])

            assert result == []

    def test_embed_unicode_text(self, mock_ollama_client):
        """Test embedding text with unicode characters."""
        with patch(
            "architectai.embeddings.service.ollama.Client",
            return_value=mock_ollama_client,
        ):
            service = EmbeddingService()
            result = service.embed("Hello, 世界! 🌍")

            assert len(result) == 1024

    def test_embed_long_text(self, mock_ollama_client):
        """Test embedding long text."""
        with patch(
            "architectai.embeddings.service.ollama.Client",
            return_value=mock_ollama_client,
        ):
            service = EmbeddingService()
            long_text = "word " * 1000
            result = service.embed(long_text)

            assert len(result) == 1024

    def test_embed_multiline_text(self, mock_ollama_client):
        """Test embedding multiline text."""
        with patch(
            "architectai.embeddings.service.ollama.Client",
            return_value=mock_ollama_client,
        ):
            service = EmbeddingService()
            multiline_text = """Line 1
Line 2
Line 3"""
            result = service.embed(multiline_text)

            assert len(result) == 1024
