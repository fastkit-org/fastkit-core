from typing import Callable, Any
import warnings
import dataclasses
from pydantic import BaseModel
from contextlib import contextmanager

from fastkit_core.events.backends.base import BaseSignalBackend
from fastkit_core.events.backends.inprocess import InProcessBackend


class Signal:
    _backend_instance: BaseSignalBackend | None = None

    @staticmethod
    def _get_backend() -> BaseSignalBackend:
        global _backend_instance
        if _backend_instance is None:
            _backend_instance = InProcessBackend()
        return _backend_instance

    def __init__(self, name: str):
        self.name = name
        self._backend = self._get_backend()

    def connect(self, receiver: Callable) -> Callable:
        self._backend.connect(self.name, receiver)
        return receiver

    def disconnect(self, receiver: Callable) -> None:
        self._backend.disconnect(self.name, receiver)

    async def send(self, payload: Any = None, **kwargs) -> list[Exception]:
        self._warn_if_payload_not_serializable(payload)
        return await self._backend.send(self.name, payload, **kwargs)

    @contextmanager
    def connected_to(self, receiver: Callable):
        self.connect(receiver)
        try:
            yield
        finally:
            self.disconnect(receiver)

    @property
    def receivers(self) -> list[Callable]:
        return self._backend.receivers(self.name)

    @staticmethod
    def _warn_if_payload_not_serializable(payload: Any) -> None:
        if payload is None:
            return
        if isinstance(payload, (dict, BaseModel)) or dataclasses.is_dataclass(payload):
            return
        warnings.warn(
            f"Signal payload of type '{type(payload).__name__}' may not be "
            "serializable to a message broker. Use dict, dataclass, or Pydantic model "
            "for forward compatibility with 0.5.0 broker backends.",
            UserWarning,
            stacklevel=3
        )