import pytest
import tempfile
import numpy as np
from architectai.cache.embedding_cache import EmbeddingCache


class TestEmbeddingCache:
    def test_embedding_cache_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(base_path=tmpdir, model_version="nomic-1.0")
            assert cache is not None
            assert cache.model_version == "nomic-1.0"

    def test_generate_text_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(base_path=tmpdir)
            h1 = cache.generate_text_hash("hello world")
            h2 = cache.generate_text_hash("hello world")
            h3 = cache.generate_text_hash("different text")
            assert h1 == h2
            assert h1 != h3

    def test_cache_embedding_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(base_path=tmpdir, model_version="test-model")
            text = "def hello(): pass"
            embedding = np.array([0.1, 0.2, 0.3, 0.4])

            cache.set_embedding(text, embedding)
            retrieved = cache.get_embedding(text)

            assert retrieved is not None
            assert np.allclose(retrieved, embedding)

    def test_batch_cache_embeddings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(base_path=tmpdir, model_version="test-model")
            texts = ["text1", "text2", "text3"]
            embeddings = [np.array([i, i + 1, i + 2]) for i in range(3)]

            cache.batch_cache(texts, embeddings)

            for text, expected_emb in zip(texts, embeddings):
                retrieved = cache.get_embedding(text)
                assert np.allclose(retrieved, expected_emb)

    def test_get_batch_embeddings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(base_path=tmpdir)

            # Cache some embeddings
            cache.set_embedding("text1", np.array([1.0, 2.0]))
            cache.set_embedding("text3", np.array([5.0, 6.0]))

            texts = ["text1", "text2", "text3", "text4"]
            embeddings, missing = cache.get_batch_embeddings(texts)

            # text1 and text3 should be found
            assert embeddings[0] is not None
            assert embeddings[2] is not None

            # text2 and text4 should be missing
            assert embeddings[1] is None
            assert embeddings[3] is None

            # Missing indices should be [1, 3]
            assert missing == [1, 3]

    def test_has_embedding(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(base_path=tmpdir)
            assert not cache.has_embedding("missing")

            cache.set_embedding("exists", np.array([1.0]))
            assert cache.has_embedding("exists")

    def test_dimension_validation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(base_path=tmpdir, embedding_dim=3)

            # Set embedding with correct dimension
            cache.set_embedding("correct", np.array([1.0, 2.0, 3.0]))
            assert cache.get_embedding("correct") is not None

            # Set embedding with wrong dimension (should still store)
            cache.set_embedding("wrong", np.array([1.0, 2.0]))

            # Should return None due to dimension validation
            assert cache.get_embedding("wrong") is None

    def test_model_version_in_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache1 = EmbeddingCache(base_path=tmpdir, model_version="v1")
            cache2 = EmbeddingCache(base_path=tmpdir, model_version="v2")

            embedding = np.array([1.0, 2.0, 3.0])
            cache1.set_embedding("text", embedding)

            # Different model version should be a cache miss
            assert cache2.get_embedding("text") is None

            # Same model version should be a cache hit
            assert cache1.get_embedding("text") is not None

    def test_vector_compression(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(
                base_path=tmpdir, compress_vectors=True, model_version="test"
            )

            embedding = np.array([0.5, -0.3, 0.8, -0.1])
            cache.set_embedding("test", embedding)
            retrieved = cache.get_embedding("test", validate_dim=False)

            # With compression, values are binary (1 or -1)
            # This is expected behavior for binarized compression
            assert retrieved is not None
            assert len(retrieved) == len(embedding)
