from typing import Any

from fastkit_core.cache.backends.base import AbstractCacheBackend

class InMemoryBackend(AbstractCacheBackend):

    def __init__(self, default_ttl: int | None = 300):
        self._default_ttl = default_ttl
        self._store: dict[str, type[Any, float | None]] = {}

