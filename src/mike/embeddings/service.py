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
    }

    def __init__(self, model: str = "mxbai-embed-large", host: Optional[str] = None):
        """Initialize embedding service.

        Args:
            model: Model name to use for embeddings
            host: Ollama host URL (defaults to localhost)
        """
        self.model = model
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")

        # Initialize Ollama client
        self.client = ollama.Client(host=self.host)

        # Get expected dimension
        self.dimension = self.MODELS.get(model, 1024)

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
        try:
            models = self.client.list()
            raw_models = models.get("models", [])
            available_models = []
            for m in raw_models:
                # Newer Ollama SDK returns Model objects; older versions return dicts
                if hasattr(m, "model"):
                    available_models.append(m.model)
                elif isinstance(m, dict):
                    available_models.append(m.get("name") or m.get("model", ""))
            return (
                self.model in available_models
                or f"{self.model}:latest" in available_models
            )
        except Exception:
            return False


    @classmethod
    def get_available_models(cls) -> List[str]:
        """Get list of supported embedding models.

        Returns:
            List of model names
        """
        return list(cls.MODELS.keys())

    @classmethod
    def get_model_dimension(cls, model: str) -> int:
        """Get embedding dimension for a model.

        Args:
            model: Model name

        Returns:
            Dimension size
        """
        return cls.MODELS.get(model, 1024)
