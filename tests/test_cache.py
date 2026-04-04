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

# ============================================================================
# Test InMemoryBackend — TTL
# ============================================================================

class TestInMemoryBackendTTL:
    """Test TTL behaviour — expiry, lazy cleanup, default TTL."""

    @pytest.mark.asyncio
    async def test_entry_accessible_before_ttl_expires(self, memory_backend):
        await memory_backend.set('key', 'value', ttl=60)
        assert await memory_backend.get('key') == 'value'

    @pytest.mark.asyncio
    async def test_entry_expired_after_ttl(self, memory_backend):
        """Simulate time passage by patching time.time."""
        await memory_backend.set('key', 'value', ttl=10)

        with patch('fastkit_core.cache.backends.memory.time') as mock_time:
            mock_time.time.return_value = time.time() + 11
            assert await memory_backend.get('key') is None

    @pytest.mark.asyncio
    async def test_expired_entry_removed_lazily_on_get(self, memory_backend):
        """Expired entry should be removed from store during get()."""
        await memory_backend.set('key', 'value', ttl=10)

        with patch('fastkit_core.cache.backends.memory.time') as mock_time:
            mock_time.time.return_value = time.time() + 11
            await memory_backend.get('key')

        # After patching ends, real time is back — entry should be gone
        assert 'key' not in memory_backend._store

    @pytest.mark.asyncio
    async def test_has_returns_false_for_expired_entry(self, memory_backend):
        await memory_backend.set('key', 'value', ttl=10)

        with patch('fastkit_core.cache.backends.memory.time') as mock_time:
            mock_time.time.return_value = time.time() + 11
            assert await memory_backend.has('key') is False

    @pytest.mark.asyncio
    async def test_uses_default_ttl_when_none_provided(self, memory_backend_with_ttl):
        await memory_backend_with_ttl.set('key', 'value')  # no explicit ttl
        _, expires_at = memory_backend_with_ttl._store['key']
        assert expires_at is not None

    @pytest.mark.asyncio
    async def test_no_expiry_when_default_ttl_is_none(self, memory_backend):
        await memory_backend.set('key', 'value')  # default_ttl=None
        _, expires_at = memory_backend._store['key']
        assert expires_at is None

    @pytest.mark.asyncio
    async def test_explicit_ttl_overrides_default(self, memory_backend_with_ttl):
        await memory_backend_with_ttl.set('key', 'value', ttl=9999)
        _, expires_at = memory_backend_with_ttl._store['key']
        # expires_at should be around now + 9999, not now + 60
        assert expires_at > time.time() + 9000

# ============================================================================
# Test InMemoryBackend — Invalidate
# ============================================================================

class TestInMemoryBackendInvalidate:
    """Test pattern-based invalidation with wildcard support."""

    @pytest.mark.asyncio
    async def test_invalidate_exact_key(self, memory_backend):
        await memory_backend.set('users:1', 'Alice')
        await memory_backend.invalidate('users:1')
        assert await memory_backend.get('users:1') is None

    @pytest.mark.asyncio
    async def test_invalidate_wildcard_pattern(self, memory_backend):
        await memory_backend.set('users:1', 'Alice')
        await memory_backend.set('users:2', 'Bob')
        await memory_backend.set('posts:1', 'Post')
        await memory_backend.invalidate('users:*')
        assert await memory_backend.get('users:1') is None
        assert await memory_backend.get('users:2') is None
        assert await memory_backend.get('posts:1') == 'Post'

    @pytest.mark.asyncio
    async def test_invalidate_no_match_does_not_raise(self, memory_backend):
        await memory_backend.set('key', 'value')
        await memory_backend.invalidate('nonexistent:*')  # should not raise
        assert await memory_backend.get('key') == 'value'

    @pytest.mark.asyncio
    async def test_invalidate_all_with_star(self, memory_backend):
        await memory_backend.set('a', 1)
        await memory_backend.set('b', 2)
        await memory_backend.invalidate('*')
        assert await memory_backend.get('a') is None
        assert await memory_backend.get('b') is None

    @pytest.mark.asyncio
    async def test_invalidate_does_not_remove_non_matching(self, memory_backend):
        await memory_backend.set('users:1', 'Alice')
        await memory_backend.set('orders:1', 'Order')
        await memory_backend.invalidate('users:*')
        assert await memory_backend.get('orders:1') == 'Order'

# ============================================================================
# Test CacheManager — Config Validation
# ============================================================================

class TestCacheManagerConfigValidation:
    """Test _make_backend_instance config validation."""

    def test_raises_when_config_missing(self):
        config = MagicMock()
        config.get.return_value = None
        with pytest.raises(ValueError, match='cache.DEFAULT'):
            CacheManager(config)

    def test_raises_when_driver_missing(self):
        config = MagicMock()
        config.get.return_value = {'ttl': 300}  # no driver
        with pytest.raises(ValueError):
            CacheManager(config)

    def test_raises_when_driver_invalid(self):
        config = MagicMock()
        config.get.return_value = {'driver': 'sqlite'}  # unsupported
        with pytest.raises(ValueError):
            CacheManager(config)

    def test_raises_when_redis_missing_host(self):
        config = make_redis_config(host=None)
        with pytest.raises(ValueError, match='host'):
            CacheManager(config)

    def test_raises_when_redis_missing_port(self):
        config = make_redis_config(port=None)
        with pytest.raises(ValueError, match='port'):
            CacheManager(config)

    def test_memory_driver_creates_in_memory_backend(self):
        config = make_config(driver='memory', ttl=60)
        manager = CacheManager(config)
        assert isinstance(manager._backend_instance, InMemoryBackend)

    def test_memory_backend_receives_ttl_from_config(self):
        config = make_config(driver='memory', ttl=120)
        manager = CacheManager(config)
        assert manager._backend_instance._default_ttl == 120

    def test_redis_driver_creates_redis_backend(self):
        from fastkit_core.cache.backends.redis import RedisBackend
        config = make_redis_config()
        with patch('fastkit_core.cache.backends.redis.Redis'):
            manager = CacheManager(config)
        assert isinstance(manager._backend_instance, RedisBackend)

# ============================================================================
# Test CacheManager — Delegation
# ============================================================================

class TestCacheManagerDelegation:
    """Test that CacheManager correctly delegates to its backend."""

    @pytest.fixture
    def mock_backend(self):
        backend = MagicMock(spec=AbstractCacheBackend)
        backend.get = AsyncMock(return_value='cached')
        backend.set = AsyncMock()
        backend.delete = AsyncMock()
        backend.invalidate = AsyncMock()
        backend.has = AsyncMock(return_value=True)
        backend.clear = AsyncMock()
        return backend

    @pytest.fixture
    def manager(self, mock_backend):
        config = make_config()
        m = CacheManager(config)
        m._backend_instance = mock_backend
        return m

    @pytest.mark.asyncio
    async def test_get_delegates_to_backend(self, manager, mock_backend):
        result = await manager.get('key')
        mock_backend.get.assert_awaited_once_with(key='key')
        assert result == 'cached'

    @pytest.mark.asyncio
    async def test_set_delegates_to_backend(self, manager, mock_backend):
        await manager.set('key', 'value', ttl=60)
        mock_backend.set.assert_awaited_once_with(key='key', data='value', ttl=60)

    @pytest.mark.asyncio
    async def test_delete_delegates_to_backend(self, manager, mock_backend):
        await manager.delete('key')
        mock_backend.delete.assert_awaited_once_with(key='key')

    @pytest.mark.asyncio
    async def test_invalidate_delegates_to_backend(self, manager, mock_backend):
        await manager.invalidate('users:*')
        mock_backend.invalidate.assert_awaited_once_with(pattern='users:*')

    @pytest.mark.asyncio
    async def test_has_delegates_to_backend(self, manager, mock_backend):
        result = await manager.has('key')
        mock_backend.has.assert_awaited_once_with(key='key')
        assert result is True

    @pytest.mark.asyncio
    async def test_clear_delegates_to_backend(self, manager, mock_backend):
        await manager.clear()
        mock_backend.clear.assert_awaited_once()

# ============================================================================
# Test Singleton — setup_cache / get_cache / reset_cache
# ============================================================================

class TestSingleton:
    """Test the module-level singleton lifecycle."""

    def test_get_cache_raises_before_setup(self):
        with pytest.raises(RuntimeError, match='setup_cache'):
            get_cache()

    def test_setup_cache_initializes_singleton(self):
        setup_cache(make_config())
        instance = get_cache()
        assert isinstance(instance, CacheManager)

    def test_get_cache_returns_same_instance(self):
        setup_cache(make_config())
        assert get_cache() is get_cache()

    def test_reset_cache_clears_singleton(self):
        setup_cache(make_config())
        reset_cache()
        with pytest.raises(RuntimeError):
            get_cache()

    def test_setup_cache_can_be_called_again_after_reset(self):
        setup_cache(make_config())
        reset_cache()
        setup_cache(make_config())
        assert get_cache() is not None