"""
Bounded LRU/TTL Memory Cache for Loaded Model Artifacts.
Prevents unbounded memory leakage in long-running serving API / worker processes.
"""

import time
import threading
from collections import OrderedDict
from typing import Any


class BoundedModelCache:
    """
    Thread-safe Bounded LRU + TTL in-memory model cache.
    Configurable max entries (default 20) and TTL (default 30 mins).
    """

    def __init__(self, max_entries: int = 20, ttl_seconds: float = 1800.0):
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key not in self._cache:
                return None
            inserted_at, val = self._cache[key]
            if time.time() - inserted_at > self.ttl_seconds:
                del self._cache[key]
                return None
            # Move to end (MRU)
            self._cache.move_to_end(key)
            return val

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            elif len(self._cache) >= self.max_entries:
                # Evict least recently used item (oldest entry)
                self._cache.popitem(last=False)
            self._cache[key] = (time.time(), value)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def __getitem__(self, key: str) -> Any:
        val = self.get(key)
        if val is None:
            raise KeyError(key)
        return val

    def __setitem__(self, key: str, value: Any) -> None:
        self.put(key, value)

    def pop(self, key: str, default: Any = None) -> Any:
        with self._lock:
            item = self._cache.pop(key, None)
            return item[1] if item is not None else default
