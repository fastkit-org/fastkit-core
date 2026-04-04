"""
Comprehensive tests for FastKit Core Cache module.

Tests:
- AbstractCacheBackend — abstract interface contract
- InMemoryBackend — get, set, delete, invalidate, has, clear, TTL expiry, lazy cleanup
- CacheManager — backend instantiation, config validation, proxy delegation
- _CacheProxy — transparent delegation to singleton
- setup_cache / get_cache / reset_cache — singleton lifecycle
- @cached decorator — cache hit, miss, static key, lambda key, TTL, sync rejection
"""

import asyncio
import time
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from unittest.mock import patch

from fastkit_core.cache import (
    AbstractCacheBackend,
    CacheManager,
    InMemoryBackend,
    cache,
    cached,
    get_cache,
    reset_cache,
    setup_cache,
)
from fastkit_core.cache.manager import _CacheProxy
import fastkit_core.cache.manager as cache_module


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset cache singleton before and after every test."""
    reset_cache()
    yield
    reset_cache()


@pytest.fixture
def memory_backend():
    """Fresh InMemoryBackend with no TTL by default."""
    return InMemoryBackend(default_ttl=None)


@pytest.fixture
def memory_backend_with_ttl():
    """InMemoryBackend with 60s default TTL."""
    return InMemoryBackend(default_ttl=60)


def make_config(driver: str = 'memory', **extra) -> MagicMock:
    """Build a minimal ConfigManager mock for cache tests."""
    config = MagicMock()
    defaults = {'driver': driver, 'ttl': 300}
    defaults.update(extra)
    config.get.return_value = defaults
    return config


def make_redis_config(**extra) -> MagicMock:
    defaults = {'driver': 'redis', 'host': 'localhost', 'port': 6379, 'db': 0, 'ttl': 300}
    defaults.update(extra)
    config = MagicMock()
    config.get.return_value = defaults
    return config


# ============================================================================
# Test AbstractCacheBackend
# ============================================================================

class TestAbstractCacheBackend:
    """Verify the abstract contract cannot be instantiated directly."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            AbstractCacheBackend()

    def test_incomplete_subclass_cannot_be_instantiated(self):
        class Incomplete(AbstractCacheBackend):
            async def get(self, key): return None
            async def set(self, key, data, ttl=None): pass
            # delete, invalidate, has, clear missing

        with pytest.raises(TypeError):
            Incomplete()

    def test_complete_subclass_can_be_instantiated(self):
        class Complete(AbstractCacheBackend):
            async def get(self, key): return None
            async def set(self, key, data, ttl=None): pass
            async def delete(self, key): pass
            async def invalidate(self, pattern): pass
            async def has(self, key): return False
            async def clear(self): pass

        backend = Complete()
        assert backend is not None

# ============================================================================
# Test InMemoryBackend — Basic Operations
# ============================================================================

class TestInMemoryBackendBasic:
    """Test basic CRUD operations without TTL."""

    @pytest.mark.asyncio
    async def test_set_and_get(self, memory_backend):
        await memory_backend.set('key', 'value')
        assert await memory_backend.get('key') == 'value'

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, memory_backend):
        assert await memory_backend.get('nonexistent') is None

    @pytest.mark.asyncio
    async def test_set_overwrites_existing(self, memory_backend):
        await memory_backend.set('key', 'first')
        await memory_backend.set('key', 'second')
        assert await memory_backend.get('key') == 'second'

    @pytest.mark.asyncio
    async def test_delete_removes_key(self, memory_backend):
        await memory_backend.set('key', 'value')
        await memory_backend.delete('key')
        assert await memory_backend.get('key') is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_does_not_raise(self, memory_backend):
        await memory_backend.delete('nonexistent')  # should not raise

    @pytest.mark.asyncio
    async def test_has_returns_true_for_existing_key(self, memory_backend):
        await memory_backend.set('key', 'value')
        assert await memory_backend.has('key') is True

    @pytest.mark.asyncio
    async def test_has_returns_false_for_nonexistent_key(self, memory_backend):
        assert await memory_backend.has('nonexistent') is False

    @pytest.mark.asyncio
    async def test_clear_removes_all_keys(self, memory_backend):
        await memory_backend.set('a', 1)
        await memory_backend.set('b', 2)
        await memory_backend.set('c', 3)
        await memory_backend.clear()
        assert await memory_backend.get('a') is None
        assert await memory_backend.get('b') is None
        assert await memory_backend.get('c') is None

    @pytest.mark.asyncio
    async def test_stores_various_data_types(self, memory_backend):
        await memory_backend.set('list', [1, 2, 3])
        await memory_backend.set('dict', {'a': 1})
        await memory_backend.set('int', 42)
        await memory_backend.set('none', None)

        assert await memory_backend.get('list') == [1, 2, 3]
        assert await memory_backend.get('dict') == {'a': 1}
        assert await memory_backend.get('int') == 42
        # None stored as value — has() should return False, get() returns None
        assert await memory_backend.get('none') is None

