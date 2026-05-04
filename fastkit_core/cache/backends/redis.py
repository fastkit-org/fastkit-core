from redis.asyncio import Redis
from typing import Any

from fastkit_core.cache.backends.base import AbstractCacheBackend

class RedisBackend(AbstractCacheBackend):

    def __init__(self,
                 host: str,
                 port: int,
                 db: int = 0,
                 password: str | None = None,
                 default_ttl: int | None = 300
                ):
        self._storage = Redis(host=host, port=port, db=db, password=password or None)
        self._default_ttl = default_ttl

    async def get(self, key: str) -> Any | None:
        return await self._storage.get(key)

    async def set(self, key: str, data: Any, ttl: int | None = None) -> None:
        effective_ttl = ttl if ttl is not None else self._default_ttl
        await self._storage.set(key, data, ex=effective_ttl)

    async def delete(self, key: str) -> None:
       await self._storage.delete(key)

    async def invalidate(self, pattern: str) -> None:
        keys = await self._storage.keys(pattern)
        for key in list(keys):
           await self._storage.delete(key)

    async def has(self, key: str) -> bool:
        return bool(await self._storage.exists(key))

    async def clear(self) -> None:
        await self._storage.flushdb()
