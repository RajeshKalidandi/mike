"""Embedding service using local models via Ollama."""

import os
from typing import List, Optional

import ollama


class EmbeddingService:
    """Service for generating text embeddings locally."""

    # Recommended models with their dimensions
    MODELS = {
        "nomic-embed-text": 768,
        "mxbai-embed-large": 1024,
        "bge-m3": 1024,
        "snowflake-arctic-embed": 768,
        "qwen3-embedding": 768,
        "qwen3-embedding:0.6b": 768,
    }

    # Model name patterns that indicate embedding capability
    EMBEDDING_PATTERNS = [
        "embed",
        "embedding",
    ]

    def __init__(self, model: Optional[str] = None, host: Optional[str] = None):
        """Initialize embedding service.

        Args:
            model: Model name to use for embeddings (auto-detected if None)
            host: Ollama host URL (defaults to localhost)
        """
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")

        # Initialize Ollama client
        self.client = ollama.Client(host=self.host)

        # Auto-detect model if not specified
        if model is None:
            model = self._auto_detect_model()

        self.model = model

        # Get expected dimension
        self.dimension = self.MODELS.get(model, 1024)

    def _is_embedding_model(self, model_name: str) -> bool:
        """Check if a model name indicates it's an embedding model.

        Args:
            model_name: Name of the model

        Returns:
            True if the model appears to be an embedding model
        """
        model_name_lower = model_name.lower()
        return any(pattern in model_name_lower for pattern in self.EMBEDDING_PATTERNS)

    def _get_ollama_models(self) -> List[str]:
        """Get list of all available models from Ollama.

        Returns:
            List of model names
        """
        try:
            response = self.client.list()
            raw_models = response.get("models", [])
            available_models = []
            for m in raw_models:
                # Newer Ollama SDK returns Model objects; older versions return dicts
                if hasattr(m, "model"):
                    available_models.append(m.model)
                elif isinstance(m, dict):
                    model_name = m.get("name") or m.get("model", "")
                    if model_name:
                        available_models.append(model_name)
            return available_models
        except Exception:
            return []

    def _auto_detect_model(self) -> str:
        """Auto-detect an available embedding model from Ollama.

        Returns:
            Name of the first available embedding model, or default if none found
        """
        available_models = self._get_ollama_models()

        if not available_models:
            print("Warning: Could not connect to Ollama or no models found.")
            print("Using default model: mxbai-embed-large")
            return "mxbai-embed-large"

        # Find embedding models
        embedding_models = [m for m in available_models if self._is_embedding_model(m)]

        if embedding_models:
            # Use the first available embedding model
            selected = embedding_models[0]
            print(f"Auto-detected embedding model: {selected}")
            return selected
        else:
            # No embedding models found - warn user
            print("Warning: No embedding models found in Ollama.")
            print(f"Available models: {', '.join(available_models[:5])}")
            print("Please install an embedding model, e.g.:")
            print("  ollama pull mxbai-embed-large")
            print("  ollama pull nomic-embed-text")
            print("  ollama pull qwen3-embedding:0.6b")
            print("\nUsing default model: mxbai-embed-large")
            return "mxbai-embed-large"

    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            Exception: If embedding generation fails
        """
        try:
            response = self.client.embeddings(model=self.model, prompt=text)
            return response["embedding"]
        except Exception as e:
            # Log error and return zero vector as fallback
            print(f"Embedding failed: {e}")
            return [0.0] * self.dimension

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once

        Returns:
            List of embedding vectors
        """
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            for text in batch:
                embedding = self.embed(text)
                embeddings.append(embedding)

        return embeddings

    def embed_chunks(self, chunks: List[dict]) -> List[dict]:
        """Generate embeddings for code chunks.

        Args:
            chunks: List of chunk dictionaries with 'content' key

        Returns:
            List of chunks with 'embedding' key added
        """
        # Extract texts
        texts = [chunk["content"] for chunk in chunks]

        # Generate embeddings
        embeddings = self.embed_batch(texts)

        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding

        return chunks

    def check_model_available(self) -> bool:
        """Check if the embedding model is available in Ollama.

        Returns:
            True if model is available, False otherwise
        """
        available_models = self._get_ollama_models()

        if not available_models:
            return False

        # Check if the model (or model:latest) is available
        return (
            self.model in available_models or f"{self.model}:latest" in available_models
        )

    @classmethod
    def get_available_models(cls) -> List[str]:
        """Get list of supported embedding models.

        Returns:
            List of model names
        """
        return list(cls.MODELS.keys())

    @classmethod
    def detect_embedding_models(cls, host: Optional[str] = None) -> List[str]:
        """Detect which embedding models are available in Ollama.

        Args:
            host: Ollama host URL

        Returns:
            List of available embedding model names
        """
        host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")

        try:
            client = ollama.Client(host=host)
            response = client.list()
            raw_models = response.get("models", [])

            available_models = []
            for m in raw_models:
                if hasattr(m, "model"):
                    available_models.append(m.model)
                elif isinstance(m, dict):
                    model_name = m.get("name") or m.get("model", "")
                    if model_name:
                        available_models.append(model_name)

            # Filter for embedding models
            embedding_models = [
                m
                for m in available_models
                if any(pattern in m.lower() for pattern in cls.EMBEDDING_PATTERNS)
            ]

            return embedding_models
        except Exception:
            return []

    @classmethod
    def get_model_dimension(cls, model: str) -> int:
        """Get embedding dimension for a model.

        Args:
            model: Model name

        Returns:
            Dimension size
        """
        return cls.MODELS.get(model, 1024)
