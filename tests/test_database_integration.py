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


