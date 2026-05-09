from redis.asyncio import Redis
from typing import Any
import json
from pydantic import BaseModel

from fastkit_core.cache.backends.base import AbstractCacheBackend


def _to_serializable(item):
    if isinstance(item, BaseModel):  # Pydantic v2
        return item.model_dump()
    if isinstance(item, tuple):
        return {'__tuple__': True, 'items': [_to_serializable(i) for i in item]}
    if isinstance(item, list):
        return [_to_serializable(i) for i in item]
    if isinstance(item, dict):
        return {k: _to_serializable(v) for k, v in item.items()}
    return item  # str, int, float, bool, None — already JSON-safe

def _from_serializable(item: Any) -> Any:
    """Recursively reconstruct Python types from JSON-safe structures."""
    if isinstance(item, dict):
        if item.get("__tuple__"):
            # Reconstruct tuple — recurse into each item
            return tuple(_from_serializable(i) for i in item["items"])
        # Regular dict — recurse into values
        return {k: _from_serializable(v) for k, v in item.items()}
    if isinstance(item, list):
        return [_from_serializable(i) for i in item]
    # Primitive — str, int, float, bool, None
    return item

def _serialize(value) -> str:
    """Serialize any supported value to a JSON string."""
    return json.dumps(_to_serializable(value))

def _deserialize(raw: str):
    """Deserialize a JSON string back to its original structure."""
    data = json.loads(raw)
    return _from_serializable(data)

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
        return await _deserialize(self._storage.get(key))

    async def set(self, key: str, data: Any, ttl: int | None = None) -> None:
        effective_ttl = ttl if ttl is not None else self._default_ttl
        await self._storage.set(key, _serialize(data), ex=effective_ttl)

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
