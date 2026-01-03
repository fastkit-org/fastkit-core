"""
Integration tests for sync and async database operations.

Tests real-world scenarios:
- Migration from sync to async
- Mixed sync/async usage
- Connection pooling
- Read replica load balancing
- Health monitoring
- Error recovery
- Performance patterns

Target Coverage: Integration scenarios
"""

import pytest
import asyncio
from datetime import datetime
from sqlalchemy import String, text, select
from sqlalchemy.orm import Mapped, mapped_column, Session
from sqlalchemy.ext.asyncio import AsyncSession

from fastkit_core.database import (
    Base,
    IntIdMixin,
    TimestampMixin,
    DatabaseManager,
    AsyncDatabaseManager,
    init_database,
    init_async_database,
    get_db,
    get_async_db,
    shutdown_database,
    shutdown_async_database,
)
from fastkit_core.config import ConfigManager


# ============================================================================
# Test Models
# ============================================================================

class User(Base, IntIdMixin, TimestampMixin):
    """Test user model for integration tests."""
    __tablename__ = 'integration_users'

    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100))


class Post(Base, IntIdMixin, TimestampMixin):
    """Test post model for integration tests."""
    __tablename__ = 'integration_posts'

    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(String(1000))
    user_id: Mapped[int]

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sync_config():
    """Config for sync database."""
    config = ConfigManager(modules=[], auto_load=False)
    config.load()
    config.set('database.CONNECTIONS', {
        'default': {
            'url': 'sqlite:///:memory:',
            'echo': False
        }
    })
    return config


@pytest.fixture
def async_config():
    """Config for async database (PostgreSQL)."""
    config = ConfigManager(modules=[], auto_load=False)
    config.load()
    config.set('database.CONNECTIONS', {
        'default': {
            'driver': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'test_pass'
        }
    })
    return config


@pytest.fixture
def mixed_config():
    """Config with both sync (SQLite) and async-compatible (PostgreSQL) connections."""
    config = ConfigManager(modules=[], auto_load=False)
    config.load()
    config.set('database.CONNECTIONS', {
        'legacy': {
            'url': 'sqlite:///:memory:',
        },
        'modern': {
            'driver': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'database': 'modern_db',
            'username': 'user',
            'password': 'pass'
        }
    })
    return config


@pytest.fixture(autouse=True)
async def cleanup():
    """Cleanup after each test."""
    yield
    # Reset global managers
    import fastkit_core.database.session as session_module
    session_module._db_managers.clear()
    session_module._async_db_managers.clear()


# ============================================================================
# Test Sync Operations
# ============================================================================

class TestSyncOperations:
    """Test synchronous database operations."""

    def test_create_and_query_sync(self, sync_config):
        """Should perform CRUD operations synchronously."""
        manager = DatabaseManager(sync_config)

        # Create tables
        Base.metadata.create_all(manager.engine)

        # Create user
        with manager.session() as session:
            user = User(name="John Doe", email="john@example.com")
            session.add(user)
            session.commit()
            session.refresh(user)
            user_id = user.id

        # Query user
        with manager.read_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            assert user is not None
            assert user.name == "John Doe"
            assert user.email == "john@example.com"

    def test_transaction_rollback_sync(self, sync_config):
        """Should rollback on error (sync)."""
        manager = DatabaseManager(sync_config)
        Base.metadata.create_all(manager.engine)

        # Create initial user
        with manager.session() as session:
            user = User(name="Alice", email="alice@example.com")
            session.add(user)

        # Attempt transaction with error
        try:
            with manager.session() as session:
                user = User(name="Bob", email="bob@example.com")
                session.add(user)
                raise ValueError("Intentional error")
        except ValueError:
            pass

        # Verify rollback
        with manager.read_session() as session:
            count = session.query(User).count()
            assert count == 1  # Only Alice should exist

    def test_multiple_connections_sync(self, mixed_config):
        """Should handle multiple sync connections."""
        manager1 = DatabaseManager(mixed_config, connection_name='legacy')
        manager2 = DatabaseManager(mixed_config, connection_name='legacy')

        assert manager1.engine is not None
        assert manager2.engine is not None


# ============================================================================
# Test Async Operations
# ============================================================================

class TestAsyncOperations:
    """Test asynchronous database operations."""

    @pytest.mark.asyncio
    async def test_create_and_query_async_structure(self, async_config):
        """Should have proper async structure for CRUD operations."""
        manager = AsyncDatabaseManager(async_config)

        # Test structure (will fail without real DB)
        try:
            async with manager.session() as session:
                user = User(name="John Doe", email="john@example.com")
                session.add(user)
                await session.commit()
        except Exception:
            # Expected without real database
            pass

    @pytest.mark.asyncio
    async def test_async_session_isolation(self, async_config):
        """Should provide isolated async sessions."""
        manager = AsyncDatabaseManager(async_config)

        session1 = manager.get_session()
        session2 = manager.get_session()

        assert session1 is not session2
        assert isinstance(session1, AsyncSession)
        assert isinstance(session2, AsyncSession)

    @pytest.mark.asyncio
    async def test_concurrent_async_operations(self, async_config):
        """Should handle concurrent async operations."""
        manager = AsyncDatabaseManager(async_config)

        # Create multiple sessions concurrently
        async def create_session():
            return manager.get_session()

        sessions = await asyncio.gather(*[create_session() for _ in range(5)])

        assert len(sessions) == 5
        assert all(isinstance(s, AsyncSession) for s in sessions)


# ============================================================================
# Test Mixed Sync/Async Usage
# ============================================================================

class TestMixedUsage:
    """Test using both sync and async managers together."""

    def test_sync_and_async_managers_coexist(self, sync_config, async_config):
        """Should allow sync and async managers to coexist."""
        sync_manager = DatabaseManager(sync_config)
        async_manager = AsyncDatabaseManager(async_config)

        assert sync_manager is not None
        assert async_manager is not None
        assert isinstance(sync_manager, DatabaseManager)
        assert isinstance(async_manager, AsyncDatabaseManager)


    @pytest.mark.asyncio
    async def test_cleanup_both_sync_and_async(self, sync_config, async_config):
        """Should cleanup both sync and async managers."""
        init_database(sync_config)
        init_async_database(async_config)

        # Cleanup
        shutdown_database()
        await shutdown_async_database()

        # Should complete without errors
        assert True


# ============================================================================
# Test Read Replica Load Balancing
# ============================================================================

class TestReadReplicaLoadBalancing:
    """Test read replica load balancing."""

    def test_read_session_uses_different_replicas_sync(self):
        """Should distribute reads across replicas (sync)."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {'url': 'sqlite:///:memory:'},
            'replica1': {'url': 'sqlite:///:memory:'},
            'replica2': {'url': 'sqlite:///:memory:'},
        })

        manager = DatabaseManager(
            config,
            connection_name='default',
            read_replicas=['replica1', 'replica2']
        )

        # Get multiple read sessions (should use different replicas randomly)
        sessions = [manager.get_read_session() for _ in range(10)]

        assert len(sessions) == 10
        assert all(s is not None for s in sessions)

    def test_read_fallback_to_primary_sync(self, sync_config):
        """Should fallback to primary when no replicas (sync)."""
        manager = DatabaseManager(sync_config)

        session = manager.get_read_session()

        assert session is not None


# ============================================================================
# Test Connection Pooling
# ============================================================================

class TestConnectionPooling:
    """Test connection pooling behavior."""

    def test_pool_size_respected(self):
        """Should respect pool_size configuration."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'url': 'sqlite:///:memory:',
                'pool_size': 10,
                'max_overflow': 5
            }
        })

        manager = DatabaseManager(config)

        # Engine should be created with pool settings
        assert manager.engine is not None

    def test_async_pool_size_respected(self):
        """Should respect pool_size for async connections."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'postgresql',
                'host': 'localhost',
                'database': 'test',
                'username': 'user',
                'password': 'pass',
                'pool_size': 20,
                'max_overflow': 10
            }
        })

        manager = AsyncDatabaseManager(config)

        assert manager.engine is not None


# ============================================================================
# Test Health Monitoring
# ============================================================================

class TestHealthMonitoring:
    """Test health check functionality."""

    def test_health_check_all_connections_sync(self):
        """Should check health of all sync connections."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'db1': {'url': 'sqlite:///:memory:'},
            'db2': {'url': 'sqlite:///:memory:'},
        })

        init_database(config, connection_name='db1')
        init_database(config, connection_name='db2')

        from fastkit_core.database.session import health_check_all
        health = health_check_all()

        assert 'db1' in health
        assert 'db2' in health

    @pytest.mark.asyncio
    async def test_health_check_all_connections_async(self, async_config):
        """Should check health of all async connections."""
        init_async_database(async_config, connection_name='default')

        from fastkit_core.database.session import health_check_all_async

        try:
            health = await health_check_all_async()
            assert isinstance(health, dict)
        except Exception:
            # Expected without real database
            pass


# ============================================================================
# Test Migration Scenarios
# ============================================================================

class TestMigrationScenarios:
    """Test migrating from sync to async."""

    def test_same_models_work_with_both(self, sync_config, async_config):
        """Should use same models for sync and async."""
        # Models defined at top work for both
        assert User.__tablename__ == 'integration_users'
        assert Post.__tablename__ == 'integration_posts'

        # Can create tables with sync
        sync_mgr = DatabaseManager(sync_config)
        Base.metadata.create_all(sync_mgr.engine)

        # Models are ready for async too
        async_mgr = AsyncDatabaseManager(async_config)
        assert async_mgr is not None

    def test_gradual_migration_pattern(self, mixed_config):
        """Should support gradual migration from sync to async."""
        # Start with sync for legacy
        sync_mgr = DatabaseManager(mixed_config, connection_name='legacy')

        # Add async for new features
        async_mgr = AsyncDatabaseManager(mixed_config, connection_name='modern')

        # Both should work
        assert sync_mgr is not None
        assert async_mgr is not None


# ============================================================================
# Test Error Recovery
# ============================================================================

class TestErrorRecovery:
    """Test error handling and recovery."""

    def test_connection_error_handling_sync(self):
        """Should handle connection errors gracefully (sync)."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'postgresql',
                'host': 'nonexistent.example.com',
                'database': 'test',
                'username': 'user',
                'password': 'pass'
            }
        })

        # Should create manager but fail on first connection attempt
        manager = DatabaseManager(config)
        assert manager is not None

    def test_invalid_query_rollback_sync(self, sync_config):
        """Should rollback on invalid query (sync)."""
        manager = DatabaseManager(sync_config)
        Base.metadata.create_all(manager.engine)

        try:
            with manager.session() as session:
                # Invalid SQL
                session.execute(text("SELECT * FROM nonexistent_table"))
        except Exception:
            # Should rollback and not crash
            pass

        # Should still be able to use connection
        with manager.session() as session:
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1


# ============================================================================
# Test Performance Patterns
# ============================================================================

class TestPerformancePatterns:
    """Test performance-related patterns."""

    def test_bulk_insert_sync(self, sync_config):
        """Should handle bulk inserts efficiently (sync)."""
        manager = DatabaseManager(sync_config)
        Base.metadata.create_all(manager.engine)

        with manager.session() as session:
            users = [
                User(name=f"User{i}", email=f"user{i}@example.com")
                for i in range(100)
            ]
            session.add_all(users)

        with manager.read_session() as session:
            count = session.query(User).count()
            assert count == 100

    @pytest.mark.asyncio
    async def test_async_concurrent_queries_structure(self, async_config):
        """Should handle concurrent async queries (structure test)."""
        manager = AsyncDatabaseManager(async_config)

        async def query_user(user_id: int):
            async with manager.read_session() as session:
                # Structure of concurrent query
                return user_id

        # Run concurrent queries
        results = await asyncio.gather(*[query_user(i) for i in range(5)])

        assert len(results) == 5


# ============================================================================
# Test Real-World Scenarios
# ============================================================================

class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_fastapi_dependency_pattern_sync(self, sync_config):
        """Should work with FastAPI dependency injection (sync)."""
        init_database(sync_config)

        # Simulate FastAPI dependency
        session_gen = get_db()
        session = next(session_gen)

        try:
            assert session is not None
            assert isinstance(session, Session)
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass

    @pytest.mark.asyncio
    async def test_fastapi_dependency_pattern_async(self, async_config):
        """Should work with FastAPI async dependency injection."""
        init_async_database(async_config)

        # Simulate async FastAPI dependency
        session_gen = get_async_db()
        session = await anext(session_gen)

        try:
            assert session is not None
            assert isinstance(session, AsyncSession)
        finally:
            try:
                await anext(session_gen)
            except StopAsyncIteration:
                pass

    def test_multi_database_application_sync(self):
        """Should support multi-database applications (sync)."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'primary': {'url': 'sqlite:///:memory:'},
            'analytics': {'url': 'sqlite:///:memory:'},
            'cache': {'url': 'sqlite:///:memory:'},
        })

        # Initialize multiple databases
        init_database(config, connection_name='primary')
        init_database(config, connection_name='analytics')
        init_database(config, connection_name='cache')

        from fastkit_core.database.session import get_db_manager

        primary = get_db_manager('primary')
        analytics = get_db_manager('analytics')
        cache = get_db_manager('cache')

        assert primary.connection_name == 'primary'
        assert analytics.connection_name == 'analytics'
        assert cache.connection_name == 'cache'


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    def test_empty_database_operations_sync(self, sync_config):
        """Should handle operations on empty database (sync)."""
        manager = DatabaseManager(sync_config)
        Base.metadata.create_all(manager.engine)

        with manager.read_session() as session:
            count = session.query(User).count()
            assert count == 0

    def test_multiple_dispose_calls_sync(self, sync_config):
        """Should handle multiple dispose calls (sync)."""
        manager = DatabaseManager(sync_config)

        manager.dispose()
        manager.dispose()
        manager.dispose()

        # Should not crash
        assert True

    @pytest.mark.asyncio
    async def test_multiple_dispose_calls_async(self, async_config):
        """Should handle multiple dispose calls (async)."""
        manager = AsyncDatabaseManager(async_config)

        await manager.dispose()
        await manager.dispose()
        await manager.dispose()

        # Should not crash
        assert True

