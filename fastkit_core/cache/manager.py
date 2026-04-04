from fastkit_core.cache.backends.base import AbstractCacheBackend
from fastkit_core.config import ConfigManager


class CacheManager(AbstractCacheBackend):

    def __init__(self, config: ConfigManager):
        self._backand_instance: AbstractCacheBackend = self._make_backend_instance(config)