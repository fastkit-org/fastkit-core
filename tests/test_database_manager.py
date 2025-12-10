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