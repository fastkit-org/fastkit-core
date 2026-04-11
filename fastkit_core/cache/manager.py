from typing import Any

from fastkit_core.cache.backends.base import AbstractCacheBackend
from fastkit_core.cache.backends.memory import InMemoryBackend
from fastkit_core.cache.backends.redis import RedisBackend
from fastkit_core.config import ConfigManager


class CacheManager(AbstractCacheBackend):

    def __init__(self, config: ConfigManager):
        self._backend_instance: AbstractCacheBackend = self._make_backend_instance(config)

    @staticmethod
    def _make_backend_instance(config: ConfigManager) -> AbstractCacheBackend:
        drivers = config.get('cache.DEFAULT')

        if (not drivers
            or not drivers.get('driver')
            or not drivers.get('driver') in ['redis', 'memory']
        ) :
            raise ValueError(
                f"Incorrect cache configuration, please check your `cache.DEFAULT` connection"
            )

        if drivers.get('driver') == 'memory':
            return InMemoryBackend(default_ttl=drivers.get('ttl'))
        elif drivers.get('driver') == 'redis':
            host = drivers.get('host')
            port = drivers.get('port')
            if not host or not port:
                raise ValueError(
                    "Redis driver requires 'host' and 'port' in cache.DEFAULT configuration"
                )
            return RedisBackend(
                host=host,
                port=port,
                db=drivers.get('db', 0),
                default_ttl=drivers.get('ttl')
            )
        raise ValueError(f"Unsupported driver: {drivers.get('driver')}")

    async def get(self, key: str) -> Any | None:
        return await self._backend_instance.get(key=key)

    async def set(self, key: str, data: Any, ttl: int | None = None) -> None:
        await self._backend_instance.set(key=key, data=data, ttl=ttl)

    async def delete(self, key: str) -> None:
        await self._backend_instance.delete(key=key)

    async def invalidate(self, pattern: str) -> None:
        await self._backend_instance.invalidate(pattern=pattern)

    async def has(self, key: str) -> bool:
        return await self._backend_instance.has(key=key)

    async def clear(self) -> None:
        await self._backend_instance.clear()

_cache_instance: CacheManager | None = None

def setup_cache(config: ConfigManager) -> None:
    global _cache_instance
    _cache_instance = CacheManager(config)

def get_cache() -> CacheManager:
    if _cache_instance is None:
        raise RuntimeError("Cache not initialized. Call setup_cache() first.")
    return _cache_instance

def reset_cache() -> None:
    """Reset singleton — for testing purposes only."""
    global _cache_instance
    _cache_instance = None

class _CacheProxy:
    """
    Lazy proxy for the CacheManager singleton.

    Allows module-level usage without explicit get_cache() calls:
        from fastkit_core.cache import cache
        await cache.get('key')
    """
    def __getattr__(self, name: str):
        return getattr(get_cache(), name)

cache = _CacheProxy()
