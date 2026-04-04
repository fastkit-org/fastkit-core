from typing import Any

from fastkit_core.cache.backends.base import AbstractCacheBackend
from fastkit_core.cache.backends.memory import InMemoryBackend
from fastkit_core.cache.backends.redis import RedisBackend
from fastkit_core.config import ConfigManager


class CacheManager(AbstractCacheBackend):

    def __init__(self, config: ConfigManager):
        self._backand_instance: AbstractCacheBackend = self._make_backend_instance(config)

    @staticmethod
    def _make_backend_instance(config: ConfigManager) -> AbstractCacheBackend | None:
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
            return RedisBackend(
                host=drivers.get('host'),
                port=drivers.get('port'),
                db=drivers.get('db'),
                default_ttl=drivers.get('ttl')
            )
        return None

    async def get(self, key: str) -> Any | None:
        return await self._backand_instance.get(key)

