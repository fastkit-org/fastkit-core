import time
from typing import Any

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