"""
Comprehensive tests for AsyncDatabaseManager and async session management.

Tests:
- Async session creation and cleanup
- Read/write replica support (async)
- Async health checks
- Async connection lifecycle
- FastAPI async integration
- URL building with async drivers
- All database drivers (PostgreSQL, MySQL, MSSQL, Oracle)

Target Coverage: 90%+
"""

import pytest
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastkit_core.database.session import (
    AsyncDatabaseManager,
    init_async_database,
    get_async_db,
    get_async_read_db,
    get_async_db_manager,
    shutdown_async_database,
    health_check_all_async,
    build_database_url,
)
from fastkit_core.config import ConfigManager


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def config():
    """Create test config with database connections."""
    config = ConfigManager(modules=[], auto_load=False)
    config.load()

    # SQLite cannot be used for async, so we skip pool settings
    # In real tests, use PostgreSQL with asyncpg
    config.set('database.CONNECTIONS', {
        'default': {
            'driver': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'test_pass',
            'echo': False,
            'pool_size': 5,
            'max_overflow': 10
        }
    })

    return config


@pytest.fixture
def config_with_replicas():
    """Create test config with read replicas."""
    config = ConfigManager(modules=[], auto_load=False)
    config.load()

    config.set('database.CONNECTIONS', {
        'default': {
            'driver': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'test_pass',
            'echo': False
        },
        'read_1': {
            'driver': 'postgresql',
            'host': 'replica1.example.com',
            'port': 5432,
            'database': 'test_db',
            'username': 'readonly',
            'password': 'test_pass',
            'echo': False
        },
        'read_2': {
            'driver': 'postgresql',
            'host': 'replica2.example.com',
            'port': 5432,
            'database': 'test_db',
            'username': 'readonly',
            'password': 'test_pass',
            'echo': False
        }
    })

    return config


@pytest.fixture
def config_multi_db():
    """Create config with multiple databases."""
    config = ConfigManager(modules=[], auto_load=False)
    config.load()

    config.set('database.CONNECTIONS', {
        'default': {
            'driver': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'database': 'main_db',
            'username': 'user',
            'password': 'pass'
        },
        'analytics': {
            'driver': 'mysql',
            'host': 'localhost',
            'port': 3306,
            'database': 'analytics_db',
            'username': 'analytics_user',
            'password': 'pass'
        },
        'cache': {
            'driver': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'database': 'cache_db',
            'username': 'cache_user',
            'password': 'pass'
        }
    })

    return config


@pytest.fixture(autouse=True)
async def cleanup_global_manager():
    """Clean up global async database manager after each test."""
    yield
    # Reset global manager
    import fastkit_core.database.session as session_module
    session_module._async_db_managers.clear()

