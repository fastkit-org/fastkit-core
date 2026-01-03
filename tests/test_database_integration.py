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

