"""Multi-tier cache manager with memory, disk, and SQLite backends."""

import hashlib
import json
import os
import pickle
import sqlite3
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


@dataclass
class CacheEntry:
    """Represents a cached value with metadata."""

    value: Any
    created_at: float
    expires_at: Optional[float] = None
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)


class MemoryCache:
    """Thread-safe in-memory LRU cache."""

    def __init__(self, max_size: int = 10000, default_ttl: Optional[int] = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None

            if entry.expires_at and time.time() > entry.expires_at:
                del self._cache[key]
                return None

            entry.access_count += 1
            entry.last_accessed = time.time()
            self._cache.move_to_end(key)
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)

            expires = None
            if ttl is not None:
                expires = time.time() + ttl
            elif self.default_ttl is not None:
                expires = time.time() + self.default_ttl

            self._cache[key] = CacheEntry(
                value=value, created_at=time.time(), expires_at=expires
            )

            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._cache)


class DiskCache:
    """File-based cache with serialization."""

    def __init__(self, base_path: str, default_ttl: Optional[int] = None):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self._lock = threading.RLock()
        self._metadata_path = self.base_path / "cache_metadata.json"
        self._metadata: Dict[str, Dict[str, Any]] = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Dict[str, Any]]:
        if self._metadata_path.exists():
            try:
                with open(self._metadata_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_metadata(self) -> None:
        with open(self._metadata_path, "w") as f:
            json.dump(self._metadata, f)

    def _get_path(self, key: str) -> Path:
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.base_path / f"{key_hash[:2]}" / f"{key_hash}.cache"

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._metadata:
                return None

            meta = self._metadata[key]
            if meta.get("expires_at") and time.time() > meta["expires_at"]:
                self.delete(key)
                return None

            cache_file = self._get_path(key)
            if not cache_file.exists():
                del self._metadata[key]
                self._save_metadata()
                return None

            try:
                with open(cache_file, "rb") as f:
                    return pickle.load(f)
            except (pickle.PickleError, IOError):
                self.delete(key)
                return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            cache_file = self._get_path(key)
            cache_file.parent.mkdir(parents=True, exist_ok=True)

            try:
                with open(cache_file, "wb") as f:
                    pickle.dump(value, f)

                meta = {"created_at": time.time()}
                if ttl is not None:
                    meta["expires_at"] = time.time() + ttl
                elif self.default_ttl is not None:
                    meta["expires_at"] = time.time() + self.default_ttl

                self._metadata[key] = meta
                self._save_metadata()
            except (pickle.PickleError, IOError):
                if cache_file.exists():
                    cache_file.unlink()

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._metadata:
                del self._metadata[key]
                self._save_metadata()

            cache_file = self._get_path(key)
            if cache_file.exists():
                cache_file.unlink()
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            import shutil

            if self.base_path.exists():
                for item in self.base_path.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)
                    elif item != self._metadata_path:
                        item.unlink()
            self._metadata.clear()
            self._save_metadata()


class SQLiteCache:
    """SQLite-based cache for structured storage."""

    def __init__(self, db_path: str, default_ttl: Optional[int] = None):
        self.db_path = db_path
        self.default_ttl = default_ttl
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    created_at REAL,
                    expires_at REAL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)
            """)
            conn.commit()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
                )
                row = cursor.fetchone()

                if row is None:
                    return None

                value_blob, expires_at = row
                if expires_at and time.time() > expires_at:
                    conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                    conn.commit()
                    return None

                try:
                    return pickle.loads(value_blob)
                except pickle.PickleError:
                    conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                    conn.commit()
                    return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            expires = None
            if ttl is not None:
                expires = time.time() + ttl
            elif self.default_ttl is not None:
                expires = time.time() + self.default_ttl

            try:
                value_blob = pickle.dumps(value)
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """INSERT OR REPLACE INTO cache (key, value, created_at, expires_at)
                           VALUES (?, ?, ?, ?)""",
                        (key, value_blob, time.time(), expires),
                    )
                    conn.commit()
            except pickle.PickleError:
                pass

    def delete(self, key: str) -> bool:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                conn.commit()
                return cursor.rowcount > 0

    def clear(self) -> None:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache")
                conn.commit()


class CacheManager:
    """Multi-tier cache manager coordinating memory, disk, and SQLite backends."""

    def __init__(
        self,
        base_path: str,
        memory_size: int = 10000,
        enable_disk: bool = True,
        enable_sqlite: bool = True,
        default_ttl: Optional[int] = None,
    ):
        self.base_path = Path(base_path)
        self.cache_dir = self.base_path
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl

        self._memory = MemoryCache(max_size=memory_size, default_ttl=default_ttl)
        self._disk = (
            DiskCache(str(self.base_path / "disk_cache"), default_ttl=default_ttl)
            if enable_disk
            else None
        )
        self._sqlite = (
            SQLiteCache(str(self.base_path / "cache.db"), default_ttl=default_ttl)
            if enable_sqlite
            else None
        )

        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "sets": 0,
        }
        self._stats_lock = threading.Lock()

    @property
    def stats(self) -> Dict[str, int]:
        with self._stats_lock:
            return self._stats.copy()

    def get(self, key: str, backend: Optional[str] = None) -> Optional[Any]:
        """Get value from cache, checking backends in priority order."""
        value = None

        if backend is None or backend == "memory":
            value = self._memory.get(key)

        if value is None and (backend is None or backend == "disk") and self._disk:
            value = self._disk.get(key)
            if value is not None:
                self._memory.set(key, value)

        if value is None and (backend is None or backend == "sqlite") and self._sqlite:
            value = self._sqlite.get(key)
            if value is not None:
                self._memory.set(key, value)

        with self._stats_lock:
            if value is not None:
                self._stats["hits"] += 1
            else:
                self._stats["misses"] += 1

        return value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        backend: Optional[str] = None,
    ) -> None:
        """Set value in cache."""
        if backend is None or backend == "memory":
            self._memory.set(key, value, ttl)

        if backend is None or backend == "disk" and self._disk:
            self._disk.set(key, value, ttl)

        if backend is None or backend == "sqlite" and self._sqlite:
            self._sqlite.set(key, value, ttl)

        with self._stats_lock:
            self._stats["sets"] += 1

    def delete(self, key: str) -> bool:
        """Delete value from all backends."""
        deleted = False
        deleted |= self._memory.delete(key)
        if self._disk:
            deleted |= self._disk.delete(key)
        if self._sqlite:
            deleted |= self._sqlite.delete(key)
        return deleted

    def clear(self, backend: Optional[str] = None) -> None:
        """Clear cache backends."""
        if backend is None or backend == "memory":
            self._memory.clear()
        if (backend is None or backend == "disk") and self._disk:
            self._disk.clear()
        if (backend is None or backend == "sqlite") and self._sqlite:
            self._sqlite.clear()

    def warm_cache(
        self, items: List[Tuple[str, Any]], ttl: Optional[int] = None
    ) -> None:
        """Pre-populate cache with multiple items."""
        for key, value in items:
            self.set(key, value, ttl)

    def generate_key(self, *components: Union[str, bytes, int, float]) -> str:
        """Generate a deterministic cache key from components."""
        hasher = hashlib.sha256()
        for comp in components:
            if isinstance(comp, bytes):
                hasher.update(comp)
            else:
                hasher.update(str(comp).encode())
        return hasher.hexdigest()

    def _get_cache_path(self, session_id: str, cache_type: str) -> Path:
        """Get the file path for a session cache."""
        return self.base_path / f"{session_id}_{cache_type}.json"

    def clear_session_cache(self, session_id: str) -> None:
        """Clear all cache entries for a session."""
        import glob

        pattern = f"{session_id}_*.json"
        for cache_file in self.base_path.glob(pattern):
            if cache_file.exists():
                cache_file.unlink()
