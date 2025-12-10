"""
Comprehensive tests for ConnectionManager (multiple database management).

Tests:
- Adding and managing multiple connections
- Connection retrieval and existence checks
- Health checks across all connections
- Connection disposal and cleanup
- Global manager instance
- Real-world multi-database scenarios

"""

import pytest
from fastkit_core.database.manager import (
    ConnectionManager,
    get_connection_manager,
    set_connection_manager
)
from fastkit_core.database.session import DatabaseManager
from fastkit_core.config import ConfigManager
from sqlalchemy import text


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def config():
    """Create test config with multiple database connections."""
    config = ConfigManager(modules=[], auto_load=False)
    config.load()

    config.set('database.CONNECTIONS', {
        'default': {
            'url': 'sqlite:///:memory:',
            'echo': False
        },
        'analytics': {
            'url': 'sqlite:///:memory:',
            'echo': False
        },
        'cache': {
            'url': 'sqlite:///:memory:',
            'echo': False
        }
    })

    return config


@pytest.fixture
def config_with_replicas():
    """Create config with read replicas."""
    config = ConfigManager(modules=[], auto_load=False)
    config.load()

    config.set('database.CONNECTIONS', {
        'default': {
            'url': 'sqlite:///:memory:',
            'echo': False
        },
        'read_1': {
            'url': 'sqlite:///:memory:',
            'echo': False
        },
        'read_2': {
            'url': 'sqlite:///:memory:',
            'echo': False
        }
    })

    return config


@pytest.fixture
def conn_manager(config):
    """Create connection manager instance."""
    return ConnectionManager(config)


@pytest.fixture(autouse=True)
def cleanup_global_manager():
    """Clean up global connection manager after each test."""
    yield
    # Reset global manager
    import fastkit_core.database.manager as manager_module
    manager_module._global_manager = None


# ============================================================================
# Test ConnectionManager Initialization
# ============================================================================

class TestConnectionManagerInit:
    """Test ConnectionManager initialization."""

    def test_init_with_config(self, config):
        """Should initialize with config."""
        manager = ConnectionManager(config)

        assert manager.config == config
        assert manager.echo is False
        assert len(manager) == 0

    def test_init_with_echo(self, config):
        """Should support echo parameter."""
        manager = ConnectionManager(config, echo=True)

        assert manager.echo is True

    def test_init_empty_connections(self, config):
        """Should start with no connections."""
        manager = ConnectionManager(config)

        assert len(manager) == 0
        assert manager.list_connections() == []


# ============================================================================
# Test Adding Connections
# ============================================================================

class TestAddConnection:
    """Test adding database connections."""

    def test_add_single_connection(self, conn_manager):
        """Should add a single connection."""
        db = conn_manager.add_connection('default')

        assert isinstance(db, DatabaseManager)
        assert db.connection_name == 'default'
        assert len(conn_manager) == 1

    def test_add_multiple_connections(self, conn_manager):
        """Should add multiple connections."""
        db1 = conn_manager.add_connection('default')
        db2 = conn_manager.add_connection('analytics')
        db3 = conn_manager.add_connection('cache')

        assert len(conn_manager) == 3
        assert conn_manager.has_connection('default')
        assert conn_manager.has_connection('analytics')
        assert conn_manager.has_connection('cache')

    def test_add_connection_with_replicas(self, config_with_replicas):
        """Should add connection with read replicas."""
        manager = ConnectionManager(config_with_replicas)

        db = manager.add_connection(
            'default',
            read_replicas=['read_1', 'read_2']
        )

        assert db.read_replicas == ['read_1', 'read_2']

    def test_add_connection_with_custom_echo(self, conn_manager):
        """Should override global echo setting."""
        db = conn_manager.add_connection('default', echo=True)

        assert db.echo is True

    def test_add_duplicate_connection(self, conn_manager):
        """Should return existing connection for duplicate name."""
        db1 = conn_manager.add_connection('default')
        db2 = conn_manager.add_connection('default')  # Duplicate

        assert db1 is db2
        assert len(conn_manager) == 1

    def test_add_connection_returns_database_manager(self, conn_manager):
        """Should return DatabaseManager instance."""
        db = conn_manager.add_connection('default')

        assert isinstance(db, DatabaseManager)
        assert hasattr(db, 'session')
        assert hasattr(db, 'engine')