from typing import Callable

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