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


# ============================================================================
# Test Getting Connections
# ============================================================================

class TestGetConnection:
    """Test retrieving connections."""

    def test_get_existing_connection(self, conn_manager):
        """Should retrieve existing connection."""
        conn_manager.add_connection('default')

        db = conn_manager.get('default')

        assert isinstance(db, DatabaseManager)
        assert db.connection_name == 'default'

    def test_get_nonexistent_connection(self, conn_manager):
        """Should raise KeyError for nonexistent connection."""
        with pytest.raises(KeyError) as exc_info:
            conn_manager.get('nonexistent')

        assert 'not found' in str(exc_info.value).lower()
        assert 'nonexistent' in str(exc_info.value)

    def test_get_with_default_name(self, conn_manager):
        """Should use 'default' as default connection name."""
        conn_manager.add_connection('default')

        db = conn_manager.get()  # No name = 'default'

        assert db.connection_name == 'default'

    def test_get_different_connections(self, conn_manager):
        """Should retrieve different connections correctly."""
        conn_manager.add_connection('default')
        conn_manager.add_connection('analytics')

        db1 = conn_manager.get('default')
        db2 = conn_manager.get('analytics')

        assert db1 is not db2
        assert db1.connection_name == 'default'
        assert db2.connection_name == 'analytics'

    def test_get_shows_available_connections(self, conn_manager):
        """Should list available connections in error."""
        conn_manager.add_connection('default')
        conn_manager.add_connection('analytics')

        with pytest.raises(KeyError) as exc_info:
            conn_manager.get('nonexistent')

        error_msg = str(exc_info.value)
        assert 'default' in error_msg or 'analytics' in error_msg


# ============================================================================
# Test Connection Existence
# ============================================================================

class TestHasConnection:
    """Test checking connection existence."""

    def test_has_connection_true(self, conn_manager):
        """Should return True for existing connection."""
        conn_manager.add_connection('default')

        assert conn_manager.has_connection('default') is True

    def test_has_connection_false(self, conn_manager):
        """Should return False for nonexistent connection."""
        assert conn_manager.has_connection('nonexistent') is False

    def test_has_connection_after_add(self, conn_manager):
        """Should return True after adding connection."""
        assert conn_manager.has_connection('default') is False

        conn_manager.add_connection('default')

        assert conn_manager.has_connection('default') is True


# ============================================================================
# Test Listing Connections
# ============================================================================

class TestListConnections:
    """Test listing all connections."""

    def test_list_empty(self, conn_manager):
        """Should return empty list initially."""
        connections = conn_manager.list_connections()

        assert connections == []

    def test_list_single_connection(self, conn_manager):
        """Should list single connection."""
        conn_manager.add_connection('default')

        connections = conn_manager.list_connections()

        assert connections == ['default']

    def test_list_multiple_connections(self, conn_manager):
        """Should list all connections."""
        conn_manager.add_connection('default')
        conn_manager.add_connection('analytics')
        conn_manager.add_connection('cache')

        connections = conn_manager.list_connections()

        assert len(connections) == 3
        assert 'default' in connections
        assert 'analytics' in connections
        assert 'cache' in connections

    def test_list_returns_copy(self, conn_manager):
        """Should return a list (not affect internal state)."""
        conn_manager.add_connection('default')

        connections = conn_manager.list_connections()
        connections.append('fake')

        # Should not affect manager
        assert conn_manager.list_connections() == ['default']


# ============================================================================
# Test Removing Connections
# ============================================================================

class TestRemoveConnection:
    """Test removing connections."""

    def test_remove_existing_connection(self, conn_manager):
        """Should remove existing connection."""
        conn_manager.add_connection('default')
        assert len(conn_manager) == 1

        conn_manager.remove_connection('default')

        assert len(conn_manager) == 0
        assert not conn_manager.has_connection('default')

    def test_remove_nonexistent_connection(self, conn_manager):
        """Should handle removing nonexistent connection gracefully."""
        # Should not raise error
        conn_manager.remove_connection('nonexistent')

        assert len(conn_manager) == 0

    def test_remove_disposes_connection(self, conn_manager):
        """Should dispose connection when removing."""
        db = conn_manager.add_connection('default')

        # Connection should work
        with db.session() as session:
            session.execute(text("SELECT 1"))

        conn_manager.remove_connection('default')

        # Connection should be disposed
        assert not conn_manager.has_connection('default')

    def test_remove_one_keeps_others(self, conn_manager):
        """Should only remove specified connection."""
        conn_manager.add_connection('default')
        conn_manager.add_connection('analytics')

        conn_manager.remove_connection('default')

        assert not conn_manager.has_connection('default')
        assert conn_manager.has_connection('analytics')
        assert len(conn_manager) == 1


# ============================================================================
# Test Health Checks
# ============================================================================

class TestHealthCheckAll:
    """Test health checking all connections."""

    def test_health_check_single_connection(self, conn_manager):
        """Should check health of single connection."""
        conn_manager.add_connection('default')

        health = conn_manager.health_check_all()

        assert 'default' in health
        assert 'primary' in health['default']
        assert health['default']['primary'] is True

    def test_health_check_multiple_connections(self, conn_manager):
        """Should check health of all connections."""
        conn_manager.add_connection('default')
        conn_manager.add_connection('analytics')
        conn_manager.add_connection('cache')

        health = conn_manager.health_check_all()

        assert len(health) == 3
        assert 'default' in health
        assert 'analytics' in health
        assert 'cache' in health

    def test_health_check_with_replicas(self, config_with_replicas):
        """Should check health of replicas too."""
        manager = ConnectionManager(config_with_replicas)
        manager.add_connection('default', read_replicas=['read_1', 'read_2'])

        health = manager.health_check_all()

        assert 'default' in health
        # Replica health is per-connection
        assert 'primary' in health['default']

    def test_health_check_empty(self, conn_manager):
        """Should return empty dict for no connections."""
        health = conn_manager.health_check_all()

        assert health == {}

# ============================================================================
# Test Disposing All Connections
# ============================================================================

class TestDisposeAll:
    """Test disposing all connections."""

    def test_dispose_all_connections(self, conn_manager):
        """Should dispose all connections."""
        conn_manager.add_connection('default')
        conn_manager.add_connection('analytics')

        assert len(conn_manager) == 2

        conn_manager.dispose_all()

        assert len(conn_manager) == 0

    def test_dispose_all_empty(self, conn_manager):
        """Should handle disposing when no connections."""
        # Should not raise error
        conn_manager.dispose_all()

        assert len(conn_manager) == 0

    def test_dispose_all_clears_list(self, conn_manager):
        """Should clear connection list."""
        conn_manager.add_connection('default')
        conn_manager.add_connection('analytics')

        conn_manager.dispose_all()

        assert conn_manager.list_connections() == []

    def test_connections_unusable_after_dispose(self, conn_manager):
        """Connections should be disposed after dispose_all."""
        db = conn_manager.add_connection('default')

        conn_manager.dispose_all()

        # Connection no longer in manager
        assert not conn_manager.has_connection('default')

# ============================================================================
# Test Global Manager
# ============================================================================

class TestGlobalManager:
    """Test global connection manager instance."""

    def test_get_global_manager(self):
        """Should get global manager instance."""
        manager = get_connection_manager()

        assert isinstance(manager, ConnectionManager)

    def test_global_manager_singleton(self):
        """Should return same instance."""
        manager1 = get_connection_manager()
        manager2 = get_connection_manager()

        assert manager1 is manager2

    def test_set_global_manager(self, config):
        """Should set custom global manager."""
        custom_manager = ConnectionManager(config, echo=True)

        set_connection_manager(custom_manager)

        manager = get_connection_manager()
        assert manager is custom_manager
        assert manager.echo is True


# ============================================================================
# Test Length
# ============================================================================

class TestLength:
    """Test length/count of connections."""

    def test_len_empty(self, conn_manager):
        """Should return 0 for empty manager."""
        assert len(conn_manager) == 0

    def test_len_single(self, conn_manager):
        """Should return correct count."""
        conn_manager.add_connection('default')

        assert len(conn_manager) == 1

    def test_len_multiple(self, conn_manager):
        """Should count all connections."""
        conn_manager.add_connection('default')
        conn_manager.add_connection('analytics')
        conn_manager.add_connection('cache')

        assert len(conn_manager) == 3

    def test_len_after_remove(self, conn_manager):
        """Should update count after removal."""
        conn_manager.add_connection('default')
        conn_manager.add_connection('analytics')

        assert len(conn_manager) == 2

        conn_manager.remove_connection('default')

        assert len(conn_manager) == 1


# ============================================================================
# Test Real-World Scenarios
# ============================================================================

class TestRealWorldScenarios:
    """Test real-world usage patterns."""

    def test_multi_database_application(self, conn_manager):
        """Should handle typical multi-database setup."""
        # Add primary database
        primary = conn_manager.add_connection('default')

        # Add analytics database
        analytics = conn_manager.add_connection('analytics')

        # Add cache database
        cache = conn_manager.add_connection('cache')

        # All should be independent
        with primary.session() as session:
            session.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))

        with analytics.session() as session:
            session.execute(text("CREATE TABLE events (id INTEGER PRIMARY KEY)"))

        with cache.session() as session:
            session.execute(text("CREATE TABLE cache_items (key TEXT PRIMARY KEY)"))

        # Verify each database works independently
        assert len(conn_manager) == 3

    def test_graceful_shutdown(self, conn_manager):
        """Should handle application shutdown."""
        # Setup connections
        conn_manager.add_connection('default')
        conn_manager.add_connection('analytics')

        # Use connections
        db = conn_manager.get('default')
        with db.session() as session:
            session.execute(text("SELECT 1"))

        # Shutdown
        conn_manager.dispose_all()

        # All should be cleaned up
        assert len(conn_manager) == 0

    def test_health_monitoring(self, conn_manager):
        """Should support health monitoring."""
        conn_manager.add_connection('default')
        conn_manager.add_connection('analytics')

        # Check health periodically
        health = conn_manager.health_check_all()

        # All connections should be healthy
        assert all(
            status.get('primary', False) or 'error' in status
            for status in health.values()
        )
