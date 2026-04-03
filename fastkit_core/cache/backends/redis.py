import time
from typing import Any

import redis

from fastkit_core.cache.backends.base import AbstractCacheBackend

class RedisBackend(AbstractCacheBackend):

    def __init__(self,
                 host: str,
                 port: int,
                 db: int = 0,
                 default_ttl: int | None = 300
                ):
        self._storage = redis.Redis(host=host, port=port, db=db)
        self._default_ttl = default_ttl

    async def get(self, key: str) -> Any | None:
        return self._storage.get(key)

    async def set(self, key: str, data: Any, ttl: int | None = None) -> None:
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = time.time() + effective_ttl if effective_ttl is not None else None
        self._storage.set(key, data, ex=expires_at)

    async def delete(self, key: str) -> None:
        self._storage.delete(key)

    async def invalidate(self, pattern: str) -> None:
        keys_to_delete = [
            key for key in self._storage.keys(pattern)
        ]

        for key in keys_to_delete:
            self._storage.delete(key)

    async def has(self, key: str) -> bool:
        return self._storage.exists(key)
