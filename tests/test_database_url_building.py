"""
Comprehensive tests for database URL building and driver mapping.

Tests:
- URL building from parameters
- All database drivers (sync and async)
- Special character encoding
- Connection options
- Error handling
- Edge cases

Target Coverage: 95%+
"""

import pytest
from fastkit_core.database.session import (
    DatabaseManager,
    AsyncDatabaseManager,
    build_database_url,
)
from fastkit_core.config import ConfigManager


# ============================================================================
# Test Synchronous URL Building
# ============================================================================

class TestSyncURLBuilding:
    """Test synchronous database URL building."""

    def test_postgresql_sync_url(self):
        """Should build PostgreSQL sync URL with psycopg2."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'postgresql',
                'host': 'localhost',
                'port': 5432,
                'database': 'mydb',
                'username': 'user',
                'password': 'pass'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert url == 'postgresql+psycopg2://user:pass@localhost:5432/mydb'

    def test_mysql_sync_url(self):
        """Should build MySQL sync URL with pymysql."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'mysql',
                'host': 'localhost',
                'port': 3306,
                'database': 'mydb',
                'username': 'root',
                'password': 'secret'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert url == 'mysql+pymysql://root:secret@localhost:3306/mydb'

    def test_mariadb_sync_url(self):
        """Should build MariaDB sync URL with pymysql."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'mariadb',
                'host': 'localhost',
                'port': 3306,
                'database': 'mydb',
                'username': 'user',
                'password': 'pass'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert url == 'mysql+pymysql://user:pass@localhost:3306/mydb'

    def test_mssql_sync_url(self):
        """Should build MSSQL sync URL with pyodbc."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'mssql',
                'host': 'localhost',
                'port': 1433,
                'database': 'mydb',
                'username': 'sa',
                'password': 'Password123'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert url == 'mssql+pyodbc://sa:Password123@localhost:1433/mydb'

    def test_oracle_sync_url(self):
        """Should build Oracle sync URL with cx_oracle."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'oracle',
                'host': 'localhost',
                'port': 1521,
                'database': 'ORCL',
                'username': 'system',
                'password': 'oracle'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert url == 'oracle+cx_oracle://system:oracle@localhost:1521/ORCL'

    def test_sqlite_sync_url(self):
        """Should build SQLite URL."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'sqlite',
                'database': '/tmp/test.db'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert url == 'sqlite:////tmp/test.db'

    def test_sqlite_memory(self):
        """Should build SQLite in-memory URL."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'sqlite',
                'database': ':memory:'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert url == 'sqlite:///:memory:'

    def test_sqlite_default_memory(self):
        """Should default to in-memory if no database specified."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'sqlite'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert url == 'sqlite:///:memory:'

# ============================================================================
# Test Asynchronous URL Building
# ============================================================================

class TestAsyncURLBuilding:
    """Test asynchronous database URL building."""

    def test_postgresql_async_url(self):
        """Should build PostgreSQL async URL with asyncpg."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'postgresql',
                'host': 'localhost',
                'port': 5432,
                'database': 'mydb',
                'username': 'user',
                'password': 'pass'
            }
        })

        url = build_database_url(config, 'default', is_async=True)

        assert url == 'postgresql+asyncpg://user:pass@localhost:5432/mydb'

    def test_mysql_async_url(self):
        """Should build MySQL async URL with aiomysql."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'mysql',
                'host': 'localhost',
                'port': 3306,
                'database': 'mydb',
                'username': 'root',
                'password': 'secret'
            }
        })

        url = build_database_url(config, 'default', is_async=True)

        assert url == 'mysql+aiomysql://root:secret@localhost:3306/mydb'

    def test_mariadb_async_url(self):
        """Should build MariaDB async URL with aiomysql."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'mariadb',
                'host': 'localhost',
                'port': 3306,
                'database': 'mydb',
                'username': 'user',
                'password': 'pass'
            }
        })

        url = build_database_url(config, 'default', is_async=True)

        assert url == 'mysql+aiomysql://user:pass@localhost:3306/mydb'

    def test_mssql_async_url(self):
        """Should build MSSQL async URL with aioodbc."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'mssql',
                'host': 'localhost',
                'port': 1433,
                'database': 'mydb',
                'username': 'sa',
                'password': 'Password123'
            }
        })

        url = build_database_url(config, 'default', is_async=True)

        assert url == 'mssql+aioodbc://sa:Password123@localhost:1433/mydb'

    def test_oracle_async_url(self):
        """Should build Oracle async URL with oracledb."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'oracle',
                'host': 'localhost',
                'port': 1521,
                'database': 'ORCL',
                'username': 'system',
                'password': 'oracle'
            }
        })

        url = build_database_url(config, 'default', is_async=True)

        assert url == 'oracle+oracledb://system:oracle@localhost:1521/ORCL'

# ============================================================================
# Test Special Characters in Passwords
# ============================================================================

class TestSpecialCharacters:
    """Test URL encoding of special characters."""

    def test_password_with_at_symbol(self):
        """Should encode @ in password."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'postgresql',
                'host': 'localhost',
                'database': 'test',
                'username': 'user',
                'password': 'p@ssword'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert 'p%40ssword' in url

    def test_password_with_colon(self):
        """Should encode : in password."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'postgresql',
                'host': 'localhost',
                'database': 'test',
                'username': 'user',
                'password': 'pass:word'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert 'pass%3Aword' in url

    def test_password_with_slash(self):
        """Should encode / in password."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'postgresql',
                'host': 'localhost',
                'database': 'test',
                'username': 'user',
                'password': 'pass/word'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert 'pass%2Fword' in url

    def test_password_with_multiple_special_chars(self):
        """Should encode multiple special characters."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'postgresql',
                'host': 'localhost',
                'database': 'test',
                'username': 'user',
                'password': 'p@ss!w#rd$%'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        # Should have encoded characters
        assert '%' in url
        assert 'p%40ss%21w%23rd%24%25' in url

    def test_password_with_unicode(self):
        """Should handle unicode in password."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'postgresql',
                'host': 'localhost',
                'database': 'test',
                'username': 'user',
                'password': 'пароль'  # Cyrillic
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        # Should be encoded
        assert '%' in url
