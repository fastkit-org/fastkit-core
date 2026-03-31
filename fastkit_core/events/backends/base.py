from abc import ABC, abstractmethod
from typing import Any


class BaseSignalBackend(ABC):

    @abstractmethod
    async def send(self, signal_name: str, payload: Any, **kwargs) -> None:
        pass

