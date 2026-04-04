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


