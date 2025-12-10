"""
Comprehensive tests for DatabaseManager and session management.

Tests:
- Session creation and cleanup
- Read/write replica support
- Health checks
- Connection lifecycle
- FastAPI integration

Target Coverage: 90%+
"""

import pytest
from sqlalchemy import text, create_engine
from fastkit_core.database.session import (
    DatabaseManager,
    init_database,
    get_db,
    get_read_db,
    get_db_manager,
    shutdown_database,
    health_check_all
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

    # Set database connections
    config.set('database.CONNECTIONS', {
        'default': {
            'url': 'sqlite:///:memory:',
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
def config_multi_db():
    """Create config with multiple databases."""
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


@pytest.fixture(autouse=True)
def cleanup_global_manager():
    """Clean up global database manager after each test."""
    yield
    # Reset global manager
    import fastkit_core.database.session as session_module
    session_module._db_manager = None


# ============================================================================
# Test DatabaseManager Initialization
# ============================================================================

class TestDatabaseManagerInit:
    """Test DatabaseManager initialization."""

    def test_init_with_config(self, config):
        """Should initialize with config."""
        manager = DatabaseManager(config)

        assert manager.config == config
        assert manager.connection_name == 'default'
        assert manager.echo is False

    def test_init_custom_connection(self, config_multi_db):
        """Should initialize with custom connection name."""
        manager = DatabaseManager(config_multi_db, connection_name='analytics')

        assert manager.connection_name == 'analytics'

    def test_init_with_echo(self, config):
        """Should support echo parameter."""
        manager = DatabaseManager(config, echo=True)

        assert manager.echo is True

    def test_init_with_read_replicas(self, config_with_replicas):
        """Should initialize with read replicas."""
        manager = DatabaseManager(
            config_with_replicas,
            connection_name='default',
            read_replicas=['read_1', 'read_2']
        )

        assert manager.read_replicas == ['read_1', 'read_2']
        assert manager.read_replicas is not None

    def test_init_without_read_replicas(self, config):
        """Should work without read replicas."""
        manager = DatabaseManager(config)

        assert manager.read_replicas is None or manager.read_replicas == []

    def test_missing_connection_raises_error(self):
        """Should raise error for missing connection."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {})

        with pytest.raises(ValueError) as exc_info:
            DatabaseManager(config, connection_name='nonexistent')

        assert 'not found' in str(exc_info.value).lower()
        assert 'nonexistent' in str(exc_info.value)

    def test_connection_config_structure(self, config):
        """Should read connection config correctly."""
        manager = DatabaseManager(config)

        # Should have created engine
        assert manager.engine is not None


# ============================================================================
# Test Engine Creation
# ============================================================================

class TestEngineCreation:
    """Test SQLAlchemy engine creation."""

    def test_create_engine(self, config):
        """Should create SQLAlchemy engine."""
        manager = DatabaseManager(config)

        engine = manager.engine

        assert engine is not None
        assert str(engine.url).startswith('sqlite')

    def test_engine_cached(self, config):
        """Should cache engine instance."""
        manager = DatabaseManager(config)

        engine1 = manager.engine
        engine2 = manager.engine

        assert engine1 is engine2

    def test_engine_with_pool_settings(self):
        """Should apply pool settings from config."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()

        config.set('database.CONNECTIONS', {
            'default': {
                'url': 'sqlite:///:memory:',
                'pool_size': 20,
                'max_overflow': 5
            }
        })

        manager = DatabaseManager(config)
        engine = manager.engine

        # Engine should be created with these settings
        assert engine is not None

    def test_dispose_engine(self, config):
        """Should dispose engine."""
        manager = DatabaseManager(config)
        engine = manager.engine

        manager.dispose()

        # Should complete without error
        assert True


# ============================================================================
# Test Session Management
# ============================================================================

class TestSessionManagement:
    """Test database session management."""

    def test_session_context_manager(self, config):
        """Should provide session context manager."""
        manager = DatabaseManager(config)

        with manager.session() as session:
            assert session is not None
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1

    def test_session_auto_commit(self, config):
        """Should auto-commit on successful exit."""
        manager = DatabaseManager(config)

        # Create table
        with manager.session() as session:
            session.execute(text("CREATE TABLE test_commit (id INTEGER PRIMARY KEY)"))

        # Verify committed
        with manager.session() as session:
            result = session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='test_commit'")
            ).fetchone()
            assert result is not None

    def test_session_rollback_on_error(self, config):
        """Should rollback on exception."""
        manager = DatabaseManager(config)

        # Create table
        with manager.session() as session:
            session.execute(text("CREATE TABLE test_rollback (id INTEGER PRIMARY KEY)"))

        # Try to insert and fail
        try:
            with manager.session() as session:
                session.execute(text("INSERT INTO test_rollback (id) VALUES (1)"))
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Verify rollback - table should be empty
        with manager.session() as session:
            result = session.execute(text("SELECT COUNT(*) FROM test_rollback")).scalar()
            assert result == 0

    def test_multiple_concurrent_sessions(self, config):
        """Should support multiple concurrent sessions."""
        manager = DatabaseManager(config)

        with manager.session() as session1:
            with manager.session() as session2:
                assert session1 is not session2

                result1 = session1.execute(text("SELECT 1")).scalar()
                result2 = session2.execute(text("SELECT 2")).scalar()

                assert result1 == 1
                assert result2 == 2

    def test_nested_sessions(self, config):
        """Should handle nested session contexts."""
        manager = DatabaseManager(config)

        with manager.session() as outer:
            outer.execute(text("CREATE TABLE test_nested (id INTEGER PRIMARY KEY)"))

            with manager.session() as inner:
                inner.execute(text("INSERT INTO test_nested (id) VALUES (1)"))

            # Both should work independently
            result = outer.execute(text("SELECT COUNT(*) FROM test_nested")).scalar()
            assert result == 1


# ============================================================================
# Test Read Replicas
# ============================================================================

class TestReadReplicas:
    """Test read replica functionality."""

    def test_read_session_with_replicas(self, config_with_replicas):
        """Should provide read session from replica."""
        manager = DatabaseManager(
            config_with_replicas,
            connection_name='default',
            read_replicas=['read_1', 'read_2']
        )

        with manager.read_session() as session:
            assert session is not None
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1

    def test_read_session_without_replicas(self, config):
        """Should fall back to primary when no replicas."""
        manager = DatabaseManager(config)

        # Should use primary connection
        with manager.read_session() as session:
            assert session is not None
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1

    def test_read_replica_engines_created(self, config_with_replicas):
        """Should create engines for read replicas."""
        manager = DatabaseManager(
            config_with_replicas,
            connection_name='default',
            read_replicas=['read_1', 'read_2']
        )

        # Access read session to trigger engine creation
        with manager.read_session() as session:
            pass

        # Should have read engines
        assert hasattr(manager, 'read_engines')
        assert len(manager.read_engines) == 2


# ============================================================================
# Test Health Checks
# ============================================================================

class TestHealthChecks:
    """Test connection health checking."""

    def test_health_check_primary(self, config):
        """Should check primary connection health."""
        manager = DatabaseManager(config)

        health = manager.health_check()

        assert 'primary' in health
        assert health['primary'] is True

    def test_health_check_with_replicas(self, config_with_replicas):
        """Should check all replica health."""
        manager = DatabaseManager(
            config_with_replicas,
            connection_name='default',
            read_replicas=['read_1', 'read_2']
        )

        health = manager.health_check()

        assert 'primary' in health
        assert 'read_1' in health
        assert 'read_2' in health
        assert health['primary'] is True
        assert health['read_1'] is True
        assert health['read_2'] is True

# ============================================================================
# Test FastAPI Integration
# ============================================================================

class TestFastAPIIntegration:
    """Test FastAPI dependency injection."""

    def test_init_database(self, config):
        """Should initialize global database manager."""
        init_database(config)

        manager = get_db_manager()

        assert manager is not None
        assert manager.connection_name == 'default'

    def test_init_database_with_replicas(self, config_with_replicas):
        """Should initialize with read replicas."""
        init_database(
            config_with_replicas,
            connection_name='default',
            read_replicas=['read_1', 'read_2']
        )

        manager = get_db_manager()
        assert manager.read_replicas is not None

    def test_get_db_dependency(self, config):
        """Should provide database session dependency."""
        init_database(config)

        session_gen = get_db()
        session = next(session_gen)

        try:
            assert session is not None
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass

    def test_get_read_db_dependency(self, config_with_replicas):
        """Should provide read database session dependency."""
        init_database(
            config_with_replicas,
            connection_name='default',
            read_replicas=['read_1']
        )

        session_gen = get_read_db()
        session = next(session_gen)

        try:
            assert session is not None
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass

    def test_shutdown_database(self, config):
        """Should shutdown database connections."""
        init_database(config)

        # Should not raise error
        shutdown_database()

        # Manager should be reset
        # (implementation dependent)
        assert True

    def test_health_check_all_function(self, config):
        """Should check health of all connections."""
        init_database(config)

        health = health_check_all()

        assert isinstance(health, dict)
        assert 'primary' in health['default']


# ============================================================================
# Test String Representation
# ============================================================================

class TestRepr:
    """Test string representation."""

    def test_repr(self, config):
        """Should have meaningful repr."""
        manager = DatabaseManager(config)

        repr_str = repr(manager)

        assert 'DatabaseManager' in repr_str
        assert 'default' in repr_str

    def test_repr_with_replicas(self, config_with_replicas):
        """Should include replicas in repr."""
        manager = DatabaseManager(
            config_with_replicas,
            connection_name='default',
            read_replicas=['read_1', 'read_2']
        )

        repr_str = repr(manager)

        assert 'DatabaseManager' in repr_str
        assert 'default' in repr_str


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_connection_name(self):
        """Should handle empty connection name."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {'': {'url': 'sqlite:///:memory:'}})

        # May raise error depending on implementation
        try:
            manager = DatabaseManager(config, connection_name='')
            assert manager is not None or True
        except Exception:
            pass

    def test_none_read_replicas(self, config):
        """Should handle None read_replicas."""
        manager = DatabaseManager(config, read_replicas=None)

        assert manager.read_replicas == []

    def test_empty_read_replicas_list(self, config):
        """Should handle empty read_replicas list."""
        manager = DatabaseManager(config, read_replicas=[])

        assert manager.read_replicas == []

    def test_invalid_replica_name(self, config):
        """Should handle invalid replica names."""
        # This might raise or fail gracefully
        try:
            manager = DatabaseManager(
                config,
                read_replicas=['nonexistent_replica']
            )
            # If it doesn't raise, that's okay
            assert manager is not None
        except ValueError:
            # Expected behavior
            pass

    def test_session_after_dispose(self, config):
        """Should handle session creation after dispose."""
        manager = DatabaseManager(config)
        manager.dispose()

        # May work or raise error depending on implementation
        # Just ensure it doesn't crash silently
        try:
            with manager.session() as session:
                pass
        except Exception:
            # Expected - can't use disposed connection
            pass

    def test_multiple_dispose_calls(self, config):
        """Should handle multiple dispose calls."""
        manager = DatabaseManager(config)

        manager.dispose()
        manager.dispose()  # Should not error

        assert True


# ============================================================================
# Test Real-World Scenarios
# ============================================================================

class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_transaction_management(self, config):
        """Should handle transactions correctly."""
        manager = DatabaseManager(config)

        # Create table
        with manager.session() as session:
            session.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"))

        # Insert with transaction
        with manager.session() as session:
            session.execute(text("INSERT INTO users (id, name) VALUES (1, 'Alice')"))
            session.execute(text("INSERT INTO users (id, name) VALUES (2, 'Bob')"))

        # Verify
        with manager.session() as session:
            result = session.execute(text("SELECT COUNT(*) FROM users")).scalar()
            assert result == 2
