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
        self.default_ttl = default_ttl

