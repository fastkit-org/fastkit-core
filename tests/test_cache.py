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


@pytest.fixture
def mock_redis():
    """Patch redis.asyncio.Redis so no real connection is made."""
    with patch('fastkit_core.cache.backends.redis.Redis') as mock:
        yield mock


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

    def test_redis_backend_receives_password_from_config(self, mock_redis):
        """CacheManager must pass password from config to RedisBackend."""
        config = make_redis_config(password='secret123')
        CacheManager(config)
        mock_redis.assert_called_once_with(
            host='localhost',
            port=6379,
            db=0,
            password='secret123',
        )

    def test_redis_backend_receives_none_password_when_absent(self, mock_redis):
        """When password is absent from config, Redis must receive password=None."""
        config = make_redis_config()  # no password key
        CacheManager(config)
        _, kwargs = mock_redis.call_args
        assert kwargs.get('password') is None

    def test_redis_backend_receives_none_password_when_explicitly_none(self, mock_redis):
        """When password is explicitly None in config, Redis must receive password=None."""
        config = make_redis_config(password=None)
        CacheManager(config)
        _, kwargs = mock_redis.call_args
        assert kwargs.get('password') is None

    def test_redis_backend_receives_empty_string_password_as_none(self, mock_redis):
        """Empty string password should be normalised to None."""
        config = make_redis_config(password='')
        CacheManager(config)
        _, kwargs = mock_redis.call_args
        assert kwargs.get('password') is None


# ============================================================================
# Test RedisBackend
# ============================================================================

class TestRedisBackend:
    """Unit tests for RedisBackend — no real Redis connection required."""

    from fastkit_core.cache.backends.redis import RedisBackend

    # ------------------------------------------------------------------
    # Instantiation
    # ------------------------------------------------------------------

    def test_instantiates_with_required_params(self, mock_redis):
        from fastkit_core.cache.backends.redis import RedisBackend
        backend = RedisBackend(host='localhost', port=6379)
        assert backend is not None

    def test_passes_host_and_port_to_redis(self, mock_redis):
        from fastkit_core.cache.backends.redis import RedisBackend
        RedisBackend(host='redis-host', port=6380)
        mock_redis.assert_called_once()
        _, kwargs = mock_redis.call_args
        assert kwargs['host'] == 'redis-host'
        assert kwargs['port'] == 6380

    def test_passes_db_to_redis(self, mock_redis):
        from fastkit_core.cache.backends.redis import RedisBackend
        RedisBackend(host='localhost', port=6379, db=3)
        _, kwargs = mock_redis.call_args
        assert kwargs['db'] == 3

    def test_default_db_is_zero(self, mock_redis):
        from fastkit_core.cache.backends.redis import RedisBackend
        RedisBackend(host='localhost', port=6379)
        _, kwargs = mock_redis.call_args
        assert kwargs['db'] == 0

    # ------------------------------------------------------------------
    # Password — the bug fix being tested
    # ------------------------------------------------------------------

    def test_passes_password_to_redis(self, mock_redis):
        """RedisBackend must forward password to the Redis client."""
        from fastkit_core.cache.backends.redis import RedisBackend
        RedisBackend(host='localhost', port=6379, password='secret')
        _, kwargs = mock_redis.call_args
        assert kwargs['password'] == 'secret'

    def test_password_defaults_to_none(self, mock_redis):
        """Without a password, Redis must receive password=None."""
        from fastkit_core.cache.backends.redis import RedisBackend
        RedisBackend(host='localhost', port=6379)
        _, kwargs = mock_redis.call_args
        assert kwargs.get('password') is None

    def test_empty_string_password_passed_as_none(self, mock_redis):
        """Empty string password should be normalised to None."""
        from fastkit_core.cache.backends.redis import RedisBackend
        RedisBackend(host='localhost', port=6379, password='')
        _, kwargs = mock_redis.call_args
        assert kwargs.get('password') is None

    def test_explicit_none_password_passed_as_none(self, mock_redis):
        from fastkit_core.cache.backends.redis import RedisBackend
        RedisBackend(host='localhost', port=6379, password=None)
        _, kwargs = mock_redis.call_args
        assert kwargs.get('password') is None

    # ------------------------------------------------------------------
    # TTL
    # ------------------------------------------------------------------

    def test_default_ttl_is_300(self, mock_redis):
        from fastkit_core.cache.backends.redis import RedisBackend
        backend = RedisBackend(host='localhost', port=6379)
        assert backend._default_ttl == 300

    def test_custom_default_ttl(self, mock_redis):
        from fastkit_core.cache.backends.redis import RedisBackend
        backend = RedisBackend(host='localhost', port=6379, default_ttl=120)
        assert backend._default_ttl == 120

    def test_none_default_ttl(self, mock_redis):
        from fastkit_core.cache.backends.redis import RedisBackend
        backend = RedisBackend(host='localhost', port=6379, default_ttl=None)
        assert backend._default_ttl is None

    # ------------------------------------------------------------------
    # Operations — via AsyncMock
    # ------------------------------------------------------------------

    @pytest.fixture
    def backend(self, mock_redis):
        """RedisBackend with fully mocked Redis storage."""
        from fastkit_core.cache.backends.redis import RedisBackend
        backend = RedisBackend(host='localhost', port=6379, password='secret')
        backend._storage = MagicMock()
        backend._storage.get = AsyncMock(return_value=None)
        backend._storage.set = AsyncMock()
        backend._storage.delete = AsyncMock()
        backend._storage.keys = AsyncMock(return_value=[])
        backend._storage.exists = AsyncMock(return_value=0)
        backend._storage.flushdb = AsyncMock()
        return backend

    @pytest.mark.asyncio
    async def test_get_calls_storage(self, backend):
        await backend.get('key')
        backend._storage.get.assert_awaited_once_with('key')

    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_found(self, backend):
        backend._storage.get = AsyncMock(return_value=None)
        result = await backend.get('missing')
        assert result is None

    @pytest.mark.asyncio
    async def test_set_uses_explicit_ttl(self, backend):
        await backend.set('key', 'value', ttl=60)
        backend._storage.set.assert_awaited_once_with('key', 'value', ex=60)

    @pytest.mark.asyncio
    async def test_set_uses_default_ttl_when_none(self, backend):
        backend._default_ttl = 300
        await backend.set('key', 'value')  # no explicit ttl
        backend._storage.set.assert_awaited_once_with('key', 'value', ex=300)

    @pytest.mark.asyncio
    async def test_delete_calls_storage(self, backend):
        await backend.delete('key')
        backend._storage.delete.assert_awaited_once_with('key')

    @pytest.mark.asyncio
    async def test_has_returns_true_when_key_exists(self, backend):
        backend._storage.exists = AsyncMock(return_value=1)
        assert await backend.has('key') is True

    @pytest.mark.asyncio
    async def test_has_returns_false_when_key_missing(self, backend):
        backend._storage.exists = AsyncMock(return_value=0)
        assert await backend.has('key') is False

    @pytest.mark.asyncio
    async def test_clear_calls_flushdb(self, backend):
        await backend.clear()
        backend._storage.flushdb.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalidate_deletes_matched_keys(self, backend):
        backend._storage.keys = AsyncMock(return_value=['products:1', 'products:2'])
        backend._storage.delete = AsyncMock()
        await backend.invalidate('products:*')
        assert backend._storage.delete.await_count == 2

    @pytest.mark.asyncio
    async def test_invalidate_does_nothing_when_no_match(self, backend):
        backend._storage.keys = AsyncMock(return_value=[])
        await backend.invalidate('nonexistent:*')
        backend._storage.delete.assert_not_awaited()

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

# ============================================================================
# Test _CacheProxy
# ============================================================================

class TestCacheProxy:
    """Test that _CacheProxy transparently delegates to the singleton."""

    def test_proxy_raises_before_setup(self):
        proxy = _CacheProxy()
        with pytest.raises(RuntimeError):
            _ = proxy.get  # triggers __getattr__ → get_cache() → RuntimeError

    @pytest.mark.asyncio
    async def test_proxy_delegates_get_after_setup(self):
        backend = InMemoryBackend(default_ttl=None)
        await backend.set('key', 'value')

        setup_cache(make_config())
        get_cache()._backend_instance = backend

        proxy = _CacheProxy()
        result = await proxy.get('key')
        assert result == 'value'

    @pytest.mark.asyncio
    async def test_module_level_cache_proxy_works(self):
        """The exported `cache` object must behave as a transparent proxy."""
        setup_cache(make_config())
        await cache.set('x', 42, ttl=None)
        result = await cache.get('x')
        assert result == 42

    def test_proxy_reflects_singleton_changes(self):
        """After reset and re-setup, proxy should use new instance."""
        setup_cache(make_config())
        first = get_cache()

        reset_cache()
        setup_cache(make_config())
        second = get_cache()

        assert first is not second

# ============================================================================
# Test @cached Decorator
# ============================================================================

class TestCachedDecorator:
    """Test the @cached decorator end-to-end with InMemoryBackend."""

    @pytest.fixture(autouse=True)
    def setup(self):
        setup_cache(make_config(driver='memory', ttl=300))

    @pytest.mark.asyncio
    async def test_cache_miss_calls_function(self):
        call_count = 0

        @cached(ttl=60, key='test:fn')
        async def fn():
            nonlocal call_count
            call_count += 1
            return 'result'

        result = await fn()
        assert result == 'result'
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_cache_hit_does_not_call_function_again(self):
        call_count = 0

        @cached(ttl=60, key='test:hit')
        async def fn():
            nonlocal call_count
            call_count += 1
            return 'result'

        await fn()
        await fn()
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_cached_value_is_returned_on_hit(self):
        @cached(ttl=60, key='test:value')
        async def fn():
            return {'id': 1, 'name': 'Alice'}

        first = await fn()
        second = await fn()
        assert first == second == {'id': 1, 'name': 'Alice'}

    @pytest.mark.asyncio
    async def test_static_key(self):
        @cached(ttl=60, key='static:key')
        async def fn():
            return 'data'

        await fn()
        cached_val = await get_cache().get('static:key')
        assert cached_val == 'data'

    @pytest.mark.asyncio
    async def test_lambda_key_single_arg(self):
        @cached(ttl=60, key=lambda user_id: f'user:{user_id}')
        async def get_user(user_id: int):
            return {'id': user_id}

        await get_user(42)
        cached_val = await get_cache().get('user:42')
        assert cached_val == {'id': 42}

    @pytest.mark.asyncio
    async def test_lambda_key_multiple_args(self):
        @cached(ttl=60, key=lambda uid, org: f'user:{uid}:org:{org}')
        async def get_user(uid: int, org: int):
            return {'uid': uid, 'org': org}

        await get_user(1, 99)
        cached_val = await get_cache().get('user:1:org:99')
        assert cached_val == {'uid': 1, 'org': 99}

    @pytest.mark.asyncio
    async def test_different_args_produce_different_cache_entries(self):
        call_count = 0

        @cached(ttl=60, key=lambda uid: f'user:{uid}')
        async def get_user(uid: int):
            nonlocal call_count
            call_count += 1
            return {'id': uid}

        await get_user(1)
        await get_user(2)
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cached_stores_value_with_correct_ttl(self):
        @cached(ttl=120, key='ttl:test')
        async def fn():
            return 'value'

        await fn()
        _, expires_at = get_cache()._backend_instance._store['ttl:test']
        assert expires_at is not None
        assert expires_at > time.time() + 100

    @pytest.mark.asyncio
    async def test_cache_miss_after_expiry(self):
        call_count = 0

        @cached(ttl=10, key='expiry:test')
        async def fn():
            nonlocal call_count
            call_count += 1
            return 'value'

        await fn()
        assert call_count == 1

        with patch('fastkit_core.cache.backends.memory.time') as mock_time:
            mock_time.time.return_value = time.time() + 11
            await fn()

        assert call_count == 2

    def test_raises_for_sync_function(self):
        with pytest.raises(TypeError, match='async'):
            @cached(ttl=60, key='sync:test')
            def sync_fn():
                return 'value'

    @pytest.mark.asyncio
    async def test_wraps_preserves_function_metadata(self):
        @cached(ttl=60, key='meta:test')
        async def my_function():
            """My docstring."""
            return 'value'

        assert my_function.__name__ == 'my_function'
        assert my_function.__doc__ == 'My docstring.'

    @pytest.mark.asyncio
    async def test_cached_without_setup_raises(self):
        reset_cache()  # ensure no singleton

        @cached(ttl=60, key='no:setup')
        async def fn():
            return 'value'

        with pytest.raises(RuntimeError, match='setup_cache'):
            await fn()

# ============================================================================
# Test Integration
# ============================================================================

class TestCacheIntegration:
    """End-to-end integration scenarios."""

    @pytest.fixture(autouse=True)
    def setup(self):
        setup_cache(make_config(driver='memory', ttl=300))

    @pytest.mark.asyncio
    async def test_service_layer_pattern(self):
        """Simulate typical service layer cache usage."""
        db_calls = 0

        async def fetch_from_db():
            nonlocal db_calls
            db_calls += 1
            return [{'id': 1}, {'id': 2}]

        # First call — cache miss
        cached_val = await cache.get('users:all')
        if cached_val is None:
            result = await fetch_from_db()
            await cache.set('users:all', result, ttl=300)
        else:
            result = cached_val

        # Second call — cache hit
        cached_val = await cache.get('users:all')
        if cached_val is None:
            result = await fetch_from_db()
            await cache.set('users:all', result, ttl=300)
        else:
            result = cached_val

        assert db_calls == 1
        assert result == [{'id': 1}, {'id': 2}]

    @pytest.mark.asyncio
    async def test_invalidate_after_create(self):
        """Simulate cache invalidation after a write operation."""
        await cache.set('users:all', [{'id': 1}], ttl=300)
        await cache.set('users:1', {'id': 1}, ttl=300)

        # After creating a new user — invalidate user list
        await cache.invalidate('users:*')

        assert await cache.get('users:all') is None
        assert await cache.get('users:1') is None

    @pytest.mark.asyncio
    async def test_cached_decorator_in_service_context(self):
        """@cached decorator used in a service method."""
        db_calls = 0

        @cached(ttl=300, key=lambda user_id: f'user:{user_id}')
        async def get_user(user_id: int):
            nonlocal db_calls
            db_calls += 1
            return {'id': user_id, 'name': 'Alice'}

        result1 = await get_user(1)
        result2 = await get_user(1)
        result3 = await get_user(2)

        assert db_calls == 2  # user 1 cached, user 2 new
        assert result1 == result2
        assert result3['id'] == 2

    @pytest.mark.asyncio
    async def test_clear_resets_all_cache(self):
        """clear() should remove everything."""
        await cache.set('a', 1)
        await cache.set('b', 2)
        await cache.set('c', 3)

        await cache.clear()

        assert await cache.get('a') is None
        assert await cache.get('b') is None
        assert await cache.get('c') is None
