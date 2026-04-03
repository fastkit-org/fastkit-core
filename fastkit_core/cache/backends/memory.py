import time
from typing import Any
import fnmatch

from fastkit_core.cache.backends.base import AbstractCacheBackend

class InMemoryBackend(AbstractCacheBackend):

    def __init__(self, default_ttl: int | None = 300):
        self._default_ttl = default_ttl
        self._store: dict[str, type[Any, float | None]] = {}

    async def get(self, key: str) -> Any | None:
        entry = self._store.get(key)

        if entry is None:
            return None

        value, expires_at = entry
        if expires_at is not None and time.time() > expires_at:
            del self._store[key]
            return None

        return value

    async def set(self, key: str, data: Any, ttl: int | None = None) -> None:
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = time.time() + effective_ttl if effective_ttl is not None else None
        self._store[key] = (data, expires_at)

    async def delete(self, key: str) -> None:
        self._store.pop(key)

    async def invalidate(self, pattern: str) -> None:
        keys_to_delete = [
            key for key in self._store if fnmatch.fnmatch(key, pattern)
        ]

        for key in keys_to_delete:
            del self._store[key]