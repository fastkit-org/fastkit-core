from abc import ABC, abstractmethod
from typing import Any, Callable


class BaseSignalBackend(ABC):

    @abstractmethod
    async def send(self, signal_name: str, payload: Any, **kwargs) -> list[Exception]:
        """
        Send signal to all connected receivers.

        Receiver exceptions are caught and returned — never propagated to the sender.
        Returns list of exceptions from failed receivers, empty list if all succeeded.
        """
        pass

    @abstractmethod
    def connect(self, signal_name: str, receiver: Callable) -> None:
        pass

    @abstractmethod
    def disconnect(self, signal_name: str, receiver: Callable) -> None:
        pass

    @abstractmethod
    def receivers(self, signal_name: str) -> list[Callable]:
        """Return all receivers connected to this signal."""
        pass
