from abc import ABC, abstractmethod
from typing import Any


class AbstractCacheBackend(ABC):

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        pass

    @abstractmethod
    async def set(self, key: str, data: Any, ttl:int):
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        pass

    @abstractmethod
    async def invalidate(self, key: str) -> None:
        pass

    @abstractmethod
    async def has(self, key: str) -> bool:
        pass
