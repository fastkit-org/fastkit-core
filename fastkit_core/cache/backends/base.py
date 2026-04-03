from abc import ABC, abstractmethod
from typing import Any


class AbstractCacheBackend(ABC):

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        pass

    @abstractmethod
    async def set(self, key: str, data: Any, ttl: int | None = None) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a single exact key."""
        pass

    @abstractmethod
    async def invalidate(self, pattern: str) -> None:
        """Delete all keys matching a pattern. Supports * wildcard."""
        pass

    @abstractmethod
    async def has(self, key: str) -> bool:
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all keys from the cache."""
        pass