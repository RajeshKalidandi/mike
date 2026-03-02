"""AST caching layer for parse tree optimization."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from architectai.cache.manager import CacheManager


class ASTCache:
    """Cache for parsed AST trees with incremental parsing support."""

    def __init__(
        self,
        base_path: str,
        parser_version: str = "1.0.0",
        config_hash: str = "default",
        memory_size: int = 5000,
        default_ttl: Optional[int] = None,
    ):
        self.cache_dir = Path(base_path)
        self.base_path = self.cache_dir
        self.parser_version = parser_version
        self.config_hash = config_hash
        self._cache = CacheManager(
            base_path=str(self.base_path / "ast"),
            memory_size=memory_size,
            default_ttl=default_ttl,
        )

    def generate_cache_key(
        self,
        language: str,
        file_content: Union[str, bytes],
        parser_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate cache key from language, content, and parser config."""
        if isinstance(file_content, str):
            file_content = file_content.encode("utf-8")

        hasher = hashlib.sha256()
        hasher.update(f"ast:{self.parser_version}:{self.config_hash}".encode())
        hasher.update(f":{language}:".encode())
        hasher.update(file_content)

        if parser_config:
            config_str = json.dumps(parser_config, sort_keys=True)
            hasher.update(f":{config_str}".encode())

        return hasher.hexdigest()

    def generate_file_hash(self, content: Union[str, bytes]) -> str:
        """Generate SHA-256 hash of file content."""
        if isinstance(content, str):
            content = content.encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    def get_ast(
        self,
        file_hash: str,
        language: str,
        parser_config: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve cached AST for a file."""
        cache_key = self.generate_cache_key(language, file_hash, parser_config)
        cached = self._cache.get(cache_key)

        if cached:
            return cached.get("ast_tree")
        return None

    def set_ast(
        self,
        file_hash: str,
        language: str,
        ast_tree: Dict[str, Any],
        parser_config: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> None:
        """Cache an AST tree."""
        cache_key = self.generate_cache_key(language, file_hash, parser_config)
        entry = {
            "file_hash": file_hash,
            "language": language,
            "ast_tree": ast_tree,
            "parser_version": self.parser_version,
            "config_hash": self.config_hash,
            "parser_config": parser_config,
        }
        self._cache.set(cache_key, entry, ttl=ttl)

    def get_with_content(
        self,
        file_content: Union[str, bytes],
        language: str,
        parser_config: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get AST using file content directly."""
        file_hash = self.generate_file_hash(file_content)
        return self.get_ast(file_hash, language, parser_config)

    def set_with_content(
        self,
        file_content: Union[str, bytes],
        language: str,
        ast_tree: Dict[str, Any],
        parser_config: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> str:
        """Cache AST with content, returns file hash."""
        file_hash = self.generate_file_hash(file_content)
        self.set_ast(file_hash, language, ast_tree, parser_config, ttl)
        return file_hash

    def has_ast(
        self,
        file_hash: str,
        language: str,
        parser_config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if AST is cached without retrieving it."""
        cache_key = self.generate_cache_key(language, file_hash, parser_config)
        return self._cache.get(cache_key) is not None

    def invalidate_file(self, file_hash: str) -> bool:
        """Invalidate all AST entries for a file hash."""
        return self._cache.delete(file_hash)

    def batch_cache(
        self,
        items: List[Tuple[str, str, Dict[str, Any]]],
        parser_config: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> List[str]:
        """Cache multiple ASTs in batch. Returns list of cache keys."""
        keys = []
        for file_hash, language, ast_tree in items:
            cache_key = self.generate_cache_key(language, file_hash, parser_config)
            entry = {
                "file_hash": file_hash,
                "language": language,
                "ast_tree": ast_tree,
                "parser_version": self.parser_version,
                "config_hash": self.config_hash,
                "parser_config": parser_config,
            }
            self._cache.set(cache_key, entry, ttl=ttl)
            keys.append(cache_key)
        return keys

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return self._cache.stats

    def clear(self) -> None:
        """Clear all cached ASTs."""
        self._cache.clear()

    def get_languages(self) -> List[str]:
        """Get list of languages in cache (requires iteration)."""
        languages = set()
        return list(languages)

    def set(self, file_path: str, language: str, value: Dict[str, Any]) -> None:
        """Cache AST data with a simple key-value interface."""
        cache_key = self.generate_cache_key(language, file_path)
        entry = {
            "file_hash": file_path,
            "language": language,
            "ast_tree": value,
            "parser_version": self.parser_version,
            "config_hash": self.config_hash,
            "parser_config": None,
        }
        self._cache.set(cache_key, entry)

    def get(self, file_path: str, language: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached AST data by file path and language."""
        cache_key = self.generate_cache_key(language, file_path)
        cached = self._cache.get(cache_key)
        if cached:
            return cached.get("ast_tree")
        return None

    def invalidate(self, file_path: str) -> bool:
        """Invalidate all AST entries for a file."""
        # Try common languages for the file
        languages = [
            "python",
            "javascript",
            "typescript",
            "go",
            "java",
            "rust",
            "c",
            "cpp",
            "ruby",
            "php",
        ]
        deleted = False
        for lang in languages:
            cache_key = self.generate_cache_key(lang, file_path)
            if self._cache.delete(cache_key):
                deleted = True
        return deleted

    def clear_all(self) -> None:
        """Clear all cached AST entries."""
        self._cache.clear()
