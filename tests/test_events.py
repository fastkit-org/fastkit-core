"""
Comprehensive tests for FastKit Core Event / Signal System.

Tests Signal, InProcessBackend, and BaseSignalBackend:
- Signal — connect, disconnect, send, connected_to, receivers, __bool__, __repr__
- InProcessBackend — async receivers, sync receivers, error isolation,
                     no duplicates, disconnect non-existent
- Payload warning — dict, Pydantic model, dataclass pass; plain object warns
- Conditional emit — signal sent only when condition is met
- Multiple signals — independent, no cross-contamination
- Decorator usage — @signal.connect registers and returns receiver
- Error isolation — failing receiver does not stop others
- shared backend — all Signal instances share the same backend
"""

import dataclasses
import warnings
import pytest
from pydantic import BaseModel

from fastkit_core.events import Signal
from fastkit_core.events.backends.inprocess import InProcessBackend
from fastkit_core.events.backends.base import BaseSignalBackend
import fastkit_core.events.signal as signal_module


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_backend():
    """
    Reset the shared backend singleton before every test.
    Without this, receivers registered in one test bleed into the next.
    """
    signal_module._backend_instance = None
    yield
    signal_module._backend_instance = None


# ============================================================================
# Test BaseSignalBackend — abstract interface
# ============================================================================

class TestBaseSignalBackend:
    """Verify the abstract contract cannot be instantiated directly."""

    def test_cannot_instantiate_directly(self):
        """BaseSignalBackend is abstract — direct instantiation must fail."""
        with pytest.raises(TypeError):
            BaseSignalBackend()

    def test_concrete_subclass_must_implement_all_methods(self):
        """A subclass missing any abstract method cannot be instantiated."""

        class Incomplete(BaseSignalBackend):
            async def send(self, signal_name, payload, **kwargs):
                return []
            def connect(self, signal_name, receiver):
                pass
            # disconnect and receivers intentionally missing

        with pytest.raises(TypeError):
            Incomplete()

    def test_full_subclass_can_be_instantiated(self):
        """A fully implemented subclass must be instantiable."""

        class Minimal(BaseSignalBackend):
            async def send(self, signal_name, payload, **kwargs):
                return []
            def connect(self, signal_name, receiver):
                pass
            def disconnect(self, signal_name, receiver):
                pass
            def receivers(self, signal_name):
                return []

        backend = Minimal()
        assert backend is not None

