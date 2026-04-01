from fastkit_core.events.backends.base import BaseSignalBackend
from fastkit_core.events.backends.inprocess import InProcessBackend


class Signal:
    _backend_instance: BaseSignalBackend | None = None

    def _get_backend(self) -> BaseSignalBackend:
        global _backend_instance
        if _backend_instance is None:
            _backend_instance = InProcessBackend()
        return _backend_instance