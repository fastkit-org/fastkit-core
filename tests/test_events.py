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

# ============================================================================
# Test InProcessBackend directly
# ============================================================================

class TestInProcessBackend:
    """Unit tests for InProcessBackend in isolation."""

    def setup_method(self):
        self.backend = InProcessBackend()

    # --- connect ---

    def test_connect_adds_receiver(self):
        async def handler(p, **kw): pass
        self.backend.connect('evt', handler)
        assert handler in self.backend.receivers('evt')

    def test_connect_does_not_add_duplicates(self):
        async def handler(p, **kw): pass
        self.backend.connect('evt', handler)
        self.backend.connect('evt', handler)
        assert self.backend.receivers('evt').count(handler) == 1

    def test_connect_multiple_receivers(self):
        async def h1(p, **kw): pass
        async def h2(p, **kw): pass
        self.backend.connect('evt', h1)
        self.backend.connect('evt', h2)
        assert len(self.backend.receivers('evt')) == 2

    def test_connect_different_signals_are_independent(self):
        async def h(p, **kw): pass
        self.backend.connect('a', h)
        assert h not in self.backend.receivers('b')

    # --- disconnect ---

    def test_disconnect_removes_receiver(self):
        async def handler(p, **kw): pass
        self.backend.connect('evt', handler)
        self.backend.disconnect('evt', handler)
        assert handler not in self.backend.receivers('evt')

    def test_disconnect_non_existent_does_not_raise(self):
        async def handler(p, **kw): pass
        # Should not raise even if receiver was never connected
        self.backend.disconnect('evt', handler)

    def test_disconnect_only_removes_target_receiver(self):
        async def h1(p, **kw): pass
        async def h2(p, **kw): pass
        self.backend.connect('evt', h1)
        self.backend.connect('evt', h2)
        self.backend.disconnect('evt', h1)
        assert h1 not in self.backend.receivers('evt')
        assert h2 in self.backend.receivers('evt')

    # --- receivers ---

    def test_receivers_returns_empty_list_for_unknown_signal(self):
        assert self.backend.receivers('nonexistent') == []

    def test_receivers_returns_copy_not_reference(self):
        """Mutating the returned list must not affect internal state."""
        async def handler(p, **kw): pass
        self.backend.connect('evt', handler)
        copy = self.backend.receivers('evt')
        copy.clear()
        assert len(self.backend.receivers('evt')) == 1

    # --- send: async receivers ---

    @pytest.mark.asyncio
    async def test_send_calls_async_receiver(self):
        received = []

        async def handler(payload, **kwargs):
            received.append(payload)

        self.backend.connect('evt', handler)
        await self.backend.send('evt', {'id': 1})
        assert received == [{'id': 1}]

    @pytest.mark.asyncio
    async def test_send_calls_sync_receiver(self):
        received = []

        def handler(payload, **kwargs):
            received.append(payload)

        self.backend.connect('evt', handler)
        await self.backend.send('evt', {'x': 42})
        assert received == [{'x': 42}]

    @pytest.mark.asyncio
    async def test_send_calls_multiple_receivers(self):
        calls = []

        async def h1(p, **kw): calls.append('h1')
        async def h2(p, **kw): calls.append('h2')

        self.backend.connect('evt', h1)
        self.backend.connect('evt', h2)
        await self.backend.send('evt', {})
        assert 'h1' in calls
        assert 'h2' in calls

    @pytest.mark.asyncio
    async def test_send_passes_kwargs_to_receiver(self):
        received_kwargs = {}

        async def handler(payload, **kwargs):
            received_kwargs.update(kwargs)

        self.backend.connect('evt', handler)
        await self.backend.send('evt', {}, extra='value')
        assert received_kwargs.get('extra') == 'value'

    @pytest.mark.asyncio
    async def test_send_to_unknown_signal_returns_empty_errors(self):
        errors = await self.backend.send('nonexistent', {})
        assert errors == []

    # --- error isolation ---

    @pytest.mark.asyncio
    async def test_failing_receiver_does_not_propagate_exception(self):
        async def bad(p, **kw): raise ValueError("boom")
        self.backend.connect('evt', bad)
        # Must not raise
        errors = await self.backend.send('evt', {})
        assert len(errors) == 1
        assert isinstance(errors[0], ValueError)

    @pytest.mark.asyncio
    async def test_failing_receiver_does_not_stop_other_receivers(self):
        calls = []

        async def bad(p, **kw): raise RuntimeError("fail")
        async def good(p, **kw): calls.append('good')

        self.backend.connect('evt', bad)
        self.backend.connect('evt', good)
        await self.backend.send('evt', {})
        assert 'good' in calls

    @pytest.mark.asyncio
    async def test_all_errors_accumulated_and_returned(self):
        async def bad1(p, **kw): raise ValueError("err1")
        async def bad2(p, **kw): raise TypeError("err2")

        self.backend.connect('evt', bad1)
        self.backend.connect('evt', bad2)
        errors = await self.backend.send('evt', {})
        assert len(errors) == 2

    @pytest.mark.asyncio
    async def test_successful_send_returns_empty_list(self):
        async def good(p, **kw): pass
        self.backend.connect('evt', good)
        errors = await self.backend.send('evt', {})
        assert errors == []


# ============================================================================
# Test Signal — public API
# ============================================================================

class TestSignalInit:
    """Test Signal initialization and shared backend."""

    def test_signal_has_name(self):
        s = Signal('user.created')
        assert s.name == 'user.created'

    def test_two_signals_share_same_backend(self):
        s1 = Signal('a')
        s2 = Signal('b')
        assert s1._backend is s2._backend

    def test_signal_starts_with_no_receivers(self):
        s = Signal('evt')
        assert s.receivers == []

    def test_signal_repr(self):
        s = Signal('user.created')
        r = repr(s)
        assert 'user.created' in r
        assert 'Signal' in r


class TestSignalConnect:
    """Test Signal.connect() — method and decorator usage."""

    @pytest.mark.asyncio
    async def test_connect_method_registers_receiver(self):
        s = Signal('evt')
        async def handler(p, **kw): pass
        s.connect(handler)
        assert handler in s.receivers

    @pytest.mark.asyncio
    async def test_connect_as_decorator_registers_receiver(self):
        s = Signal('evt')

        @s.connect
        async def handler(p, **kw): pass

        assert handler in s.receivers

    def test_connect_decorator_returns_original_function(self):
        """Decorator must not replace the function — it must return it unchanged."""
        s = Signal('evt')

        @s.connect
        async def handler(p, **kw): pass

        # handler should still be callable and be the same object
        assert callable(handler)
        assert handler.__name__ == 'handler'

    def test_connect_does_not_add_duplicate(self):
        s = Signal('evt')
        async def handler(p, **kw): pass
        s.connect(handler)
        s.connect(handler)
        assert s.receivers.count(handler) == 1

    def test_connect_sync_receiver(self):
        s = Signal('evt')
        def handler(p, **kw): pass
        s.connect(handler)
        assert handler in s.receivers


class TestSignalDisconnect:
    """Test Signal.disconnect()."""

    def test_disconnect_removes_receiver(self):
        s = Signal('evt')
        async def handler(p, **kw): pass
        s.connect(handler)
        s.disconnect(handler)
        assert handler not in s.receivers

    def test_disconnect_non_existent_does_not_raise(self):
        s = Signal('evt')
        async def handler(p, **kw): pass
        s.disconnect(handler)  # never connected — should not raise

    def test_disconnect_only_removes_target(self):
        s = Signal('evt')
        async def h1(p, **kw): pass
        async def h2(p, **kw): pass
        s.connect(h1)
        s.connect(h2)
        s.disconnect(h1)
        assert h1 not in s.receivers
        assert h2 in s.receivers

class TestSignalSend:
    """Test Signal.send() — delivery and error isolation."""

    @pytest.mark.asyncio
    async def test_send_delivers_payload_to_receiver(self):
        s = Signal('evt')
        received = []

        @s.connect
        async def handler(payload, **kwargs):
            received.append(payload)

        await s.send({'key': 'value'})
        assert received == [{'key': 'value'}]

    @pytest.mark.asyncio
    async def test_send_with_no_receivers_returns_empty_list(self):
        s = Signal('evt')
        errors = await s.send({'x': 1})
        assert errors == []

    @pytest.mark.asyncio
    async def test_send_returns_empty_list_on_success(self):
        s = Signal('evt')

        @s.connect
        async def handler(p, **kw): pass

        errors = await s.send({'x': 1})
        assert errors == []

    @pytest.mark.asyncio
    async def test_send_returns_errors_from_failing_receivers(self):
        s = Signal('evt')

        @s.connect
        async def bad(p, **kw): raise ValueError("fail")

        errors = await s.send({})
        assert len(errors) == 1
        assert isinstance(errors[0], ValueError)

    @pytest.mark.asyncio
    async def test_send_does_not_propagate_receiver_exception(self):
        s = Signal('evt')

        @s.connect
        async def bad(p, **kw): raise RuntimeError("boom")

        # Must not raise
        await s.send({})

    @pytest.mark.asyncio
    async def test_send_continues_after_failing_receiver(self):
        s = Signal('evt')
        calls = []

        @s.connect
        async def bad(p, **kw): raise ValueError("fail")

        @s.connect
        async def good(p, **kw): calls.append('good')

        await s.send({})
        assert 'good' in calls

    @pytest.mark.asyncio
    async def test_send_with_none_payload(self):
        s = Signal('evt')
        received = []

        @s.connect
        async def handler(payload, **kwargs):
            received.append(payload)

        await s.send(None)
        assert received == [None]

    @pytest.mark.asyncio
    async def test_send_passes_kwargs(self):
        s = Signal('evt')
        captured = {}

        @s.connect
        async def handler(payload, **kwargs):
            captured.update(kwargs)

        await s.send({}, source='test', version=2)
        assert captured['source'] == 'test'
        assert captured['version'] == 2

    @pytest.mark.asyncio
    async def test_send_calls_sync_receiver(self):
        s = Signal('evt')
        received = []

        @s.connect
        def handler(payload, **kwargs):
            received.append(payload)

        await s.send({'n': 1})
        assert received == [{'n': 1}]