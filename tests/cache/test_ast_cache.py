import pytest
import tempfile
from unittest.mock import Mock
from architectai.cache.ast_cache import ASTCache


class TestASTCache:
    def test_ast_cache_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ASTCache(base_path=tmpdir)
            assert cache is not None

    def test_generate_cache_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ASTCache(base_path=tmpdir)
            key = cache.generate_cache_key("python", "def foo(): pass")
            assert isinstance(key, str)
            assert len(key) == 64

    def test_cache_ast_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ASTCache(base_path=tmpdir)
            file_hash = "abc123"
            language = "python"
            ast_tree = {"type": "module", "body": []}

            cache.set_ast(file_hash, language, ast_tree)
            retrieved = cache.get_ast(file_hash, language)

            assert retrieved == ast_tree

    def test_generate_file_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ASTCache(base_path=tmpdir)
            h1 = cache.generate_file_hash("hello world")
            h2 = cache.generate_file_hash("hello world")
            h3 = cache.generate_file_hash("different content")

            assert h1 == h2
            assert h1 != h3
            assert len(h1) == 64

    def test_has_ast(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ASTCache(base_path=tmpdir)
            assert not cache.has_ast("missing", "python")

            cache.set_ast("exists", "python", {"type": "module"})
            assert cache.has_ast("exists", "python")

    def test_get_with_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ASTCache(base_path=tmpdir)
            content = "def foo(): pass"
            ast_tree = {"type": "function", "name": "foo"}

            cache.set_with_content(content, "python", ast_tree)
            retrieved = cache.get_with_content(content, "python")

            assert retrieved == ast_tree

    def test_batch_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ASTCache(base_path=tmpdir)
            items = [
                ("hash1", "python", {"type": "func1"}),
                ("hash2", "python", {"type": "func2"}),
                ("hash3", "javascript", {"type": "func3"}),
            ]

            keys = cache.batch_cache(items)
            assert len(keys) == 3

            assert cache.get_ast("hash1", "python") == {"type": "func1"}
            assert cache.get_ast("hash2", "python") == {"type": "func2"}
            assert cache.get_ast("hash3", "javascript") == {"type": "func3"}

    def test_stats_tracking(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ASTCache(base_path=tmpdir)
            cache.set_ast("hash1", "python", {"type": "func"})
            cache.get_ast("hash1", "python")

            stats = cache.get_stats()
            assert stats["sets"] == 1
            assert stats["hits"] == 1

    def test_parser_config_in_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ASTCache(base_path=tmpdir)
            file_hash = "abc123"
            language = "python"
            ast_tree = {"type": "module"}

            config1 = {"strict": True}
            config2 = {"strict": False}

            cache.set_ast(file_hash, language, ast_tree, parser_config=config1)

            # Should not match with different config
            assert cache.get_ast(file_hash, language, parser_config=config2) is None

            # Should match with same config
            assert cache.get_ast(file_hash, language, parser_config=config1) == ast_tree
