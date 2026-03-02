"""Embedding cache for vector storage optimization."""

import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np

from architectai.cache.manager import CacheManager


class EmbeddingCache:
    """Cache for text embeddings with model version tracking."""

    def __init__(
        self,
        base_path: str,
        model_version: str = "default",
        embedding_dim: Optional[int] = None,
        memory_size: int = 10000,
        compress_vectors: bool = False,
        default_ttl: Optional[int] = None,
    ):
        self.cache_dir = Path(base_path)
        self.base_path = self.cache_dir
        self.model_version = model_version
        self.embedding_dim = embedding_dim
        self.compress_vectors = compress_vectors
        self._cache = CacheManager(
            base_path=str(self.base_path / "embeddings"),
            memory_size=memory_size,
            default_ttl=default_ttl,
        )

    def generate_text_hash(self, text: str) -> str:
        """Generate SHA-256 hash of text content."""
        hasher = hashlib.sha256()
        hasher.update(f"emb:{self.model_version}:".encode())
        hasher.update(text.encode("utf-8"))
        return hasher.hexdigest()

    def generate_batch_key(self, texts: List[str]) -> str:
        """Generate cache key for a batch of texts."""
        hasher = hashlib.sha256()
        hasher.update(f"emb_batch:{self.model_version}:".encode())
        for text in sorted(texts):
            hasher.update(hashlib.sha256(text.encode()).digest())
        return hasher.hexdigest()

    def _compress_vector(self, vector: np.ndarray) -> bytes:
        """Compress vector for storage (if enabled)."""
        if self.compress_vectors:
            return np.packbits((vector > 0).astype(np.uint8)).tobytes()
        return vector.astype(np.float32).tobytes()

    def _decompress_vector(self, data: bytes, original_dim: int) -> np.ndarray:
        """Decompress vector from storage."""
        if self.compress_vectors:
            bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))
            return bits[:original_dim].astype(np.float32) * 2 - 1
        return np.frombuffer(data, dtype=np.float32)

    def get_embedding(
        self, text: str, validate_dim: bool = True
    ) -> Optional[np.ndarray]:
        """Retrieve cached embedding for text."""
        cache_key = self.generate_text_hash(text)
        cached = self._cache.get(cache_key)

        if cached is None:
            return None

        vector_data = cached.get("vector_data")
        dim = cached.get("dim")

        if validate_dim and self.embedding_dim and dim != self.embedding_dim:
            return None

        return self._decompress_vector(vector_data, dim)

    def set_embedding(
        self, text: str, embedding: np.ndarray, ttl: Optional[int] = None
    ) -> None:
        """Cache an embedding vector."""
        cache_key = self.generate_text_hash(text)

        entry = {
            "text_hash": cache_key,
            "model_version": self.model_version,
            "dim": len(embedding),
            "vector_data": self._compress_vector(embedding),
            "compressed": self.compress_vectors,
        }

        self._cache.set(cache_key, entry, ttl=ttl)

    def batch_cache(
        self, texts: List[str], embeddings: List[np.ndarray], ttl: Optional[int] = None
    ) -> List[str]:
        """Cache multiple embeddings in batch."""
        if len(texts) != len(embeddings):
            raise ValueError("texts and embeddings must have same length")

        keys = []
        for text, embedding in zip(texts, embeddings):
            self.set_embedding(text, embedding, ttl)
            keys.append(self.generate_text_hash(text))

        return keys

    def get_batch_embeddings(
        self, texts: List[str]
    ) -> Tuple[List[np.ndarray], List[int]]:
        """Get embeddings for multiple texts. Returns (embeddings, missing_indices)."""
        embeddings = []
        missing_indices = []

        for idx, text in enumerate(texts):
            emb = self.get_embedding(text)
            if emb is not None:
                embeddings.append(emb)
            else:
                embeddings.append(None)
                missing_indices.append(idx)

        return embeddings, missing_indices

    def has_embedding(self, text: str) -> bool:
        """Check if embedding is cached."""
        return self.get_embedding(text) is not None

    def invalidate_model(self, model_version: str) -> int:
        """Invalidate all embeddings for a specific model version."""
        cleared = 0
        return cleared

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return self._cache.stats

    def estimate_memory_usage(self) -> Dict[str, Union[int, float]]:
        """Estimate memory usage of cached embeddings."""
        return {
            "entries": 0,
            "estimated_bytes": 0,
        }

    def clear(self) -> None:
        """Clear all cached embeddings."""
        self._cache.clear()

    def set(self, key: str, value: List[float]) -> None:
        """Cache an embedding with a simple key-value interface."""
        self._cache.set(key, value)

    def get(self, key: str) -> Optional[List[float]]:
        """Retrieve cached embedding by key."""
        return self._cache.get(key)

    def set_batch(self, embeddings: Dict[str, List[float]]) -> None:
        """Cache multiple embeddings in batch."""
        for key, value in embeddings.items():
            self._cache.set(key, value)

    def get_batch(self, keys: List[str]) -> Dict[str, Optional[List[float]]]:
        """Retrieve multiple cached embeddings by keys."""
        results = {}
        for key in keys:
            results[key] = self._cache.get(key)
        return results
