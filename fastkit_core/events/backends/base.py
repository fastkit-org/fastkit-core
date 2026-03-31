from abc import ABC, abstractmethod
from typing import Any, Callable


class BaseSignalBackend(ABC):

    @abstractmethod
    async def send(self, signal_name: str, payload: Any, **kwargs) -> None:
        pass

    @abstractmethod
    def connect(self, signal_name: str, receiver: Callable) -> None:
        pass

    @abstractmethod
    def disconnect(self, signal_name: str, receiver: Callable) -> None:
        pass