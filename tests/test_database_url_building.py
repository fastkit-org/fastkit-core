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

# ============================================================================
# Test Connection Options
# ============================================================================

class TestConnectionOptions:
    """Test connection options in URL."""

    def test_options_appended_to_url(self):
        """Should append connection options to URL."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'postgresql',
                'host': 'localhost',
                'database': 'test',
                'username': 'user',
                'password': 'pass',
                'options': {
                    'sslmode': 'require',
                    'connect_timeout': '10'
                }
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert '?' in url
        assert 'sslmode=require' in url
        assert 'connect_timeout=10' in url

    def test_multiple_options(self):
        """Should handle multiple connection options."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'mysql',
                'host': 'localhost',
                'database': 'test',
                'username': 'root',
                'password': 'pass',
                'options': {
                    'charset': 'utf8mb4',
                    'connect_timeout': '10',
                    'read_timeout': '30'
                }
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert 'charset=utf8mb4' in url
        assert 'connect_timeout=10' in url
        assert 'read_timeout=30' in url

    def test_no_options(self):
        """Should work without options."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'postgresql',
                'host': 'localhost',
                'database': 'test',
                'username': 'user',
                'password': 'pass'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert '?' not in url


# ============================================================================
# Test URL Variations
# ============================================================================

class TestURLVariations:
    """Test various URL building scenarios."""

    def test_url_without_port(self):
        """Should build URL without port."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'postgresql',
                'host': 'localhost',
                'database': 'test',
                'username': 'user',
                'password': 'pass'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert url == 'postgresql+psycopg2://user:pass@localhost/test'

    def test_url_without_password(self):
        """Should build URL without password."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'postgresql',
                'host': 'localhost',
                'database': 'test',
                'username': 'user'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert url == 'postgresql+psycopg2://user@localhost/test'

    def test_url_without_username_and_password(self):
        """Should build URL without credentials."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'postgresql',
                'host': 'localhost',
                'database': 'test'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert url == 'postgresql+psycopg2://localhost/test'

    def test_url_with_default_host(self):
        """Should use localhost as default host."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'postgresql',
                'database': 'test',
                'username': 'user',
                'password': 'pass'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert 'localhost' in url


# ============================================================================
# Test Direct URL Configuration
# ============================================================================

class TestDirectURL:
    """Test direct URL configuration."""

    def test_direct_url_sync(self):
        """Should use direct URL from config (sync)."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'url': 'postgresql+psycopg2://user:pass@localhost:5432/mydb'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert url == 'postgresql+psycopg2://user:pass@localhost:5432/mydb'

    def test_direct_url_async(self):
        """Should use direct URL from config (async)."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'url': 'postgresql+asyncpg://user:pass@localhost:5432/mydb'
            }
        })

        url = build_database_url(config, 'default', is_async=True)

        assert url == 'postgresql+asyncpg://user:pass@localhost:5432/mydb'

    def test_direct_url_ignores_is_async_param(self):
        """Direct URL should be returned as-is regardless of is_async."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'url': 'mysql+pymysql://root:pass@localhost/mydb'
            }
        })

        url_sync = build_database_url(config, 'default', is_async=False)
        url_async = build_database_url(config, 'default', is_async=True)

        # Both should return same URL
        assert url_sync == url_async
        assert url_sync == 'mysql+pymysql://root:pass@localhost/mydb'


# ============================================================================
# Test Error Cases
# ============================================================================

class TestErrorCases:
    """Test error handling in URL building."""

    def test_missing_driver_and_url(self):
        """Should raise error when both driver and url are missing."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'host': 'localhost',
                'database': 'test'
            }
        })

        with pytest.raises(ValueError) as exc_info:
            build_database_url(config, 'default', is_async=False)

        assert 'driver' in str(exc_info.value).lower() or 'url' in str(exc_info.value).lower()

    def test_missing_database_parameter(self):
        """Should raise error when database parameter is missing."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'postgresql',
                'host': 'localhost',
                'username': 'user',
                'password': 'pass'
            }
        })

        with pytest.raises(ValueError) as exc_info:
            build_database_url(config, 'default', is_async=False)

        assert 'database' in str(exc_info.value).lower()

    def test_unsupported_driver(self):
        """Should raise error for unsupported driver."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'nosql_database',
                'host': 'localhost',
                'database': 'test'
            }
        })

        with pytest.raises(ValueError) as exc_info:
            build_database_url(config, 'default', is_async=False)

        assert 'unsupported' in str(exc_info.value).lower() or 'driver' in str(exc_info.value).lower()

    def test_nonexistent_connection(self):
        """Should raise error for non-existent connection."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {})

        with pytest.raises(ValueError) as exc_info:
            build_database_url(config, 'nonexistent', is_async=False)

        assert 'no database connections' in str(exc_info.value).lower()

    def test_empty_connections_dict(self):
        """Should raise error when CONNECTIONS is empty."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {})

        with pytest.raises(ValueError) as exc_info:
            build_database_url(config, 'default', is_async=False)

        assert 'not found' in str(exc_info.value).lower() or 'connections' in str(exc_info.value).lower()


# ============================================================================
# Test Driver Aliases
# ============================================================================

class TestDriverAliases:
    """Test driver name aliases."""

    def test_postgres_alias_sync(self):
        """Should accept 'postgres' as PostgreSQL alias (sync)."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'postgres',
                'host': 'localhost',
                'database': 'test',
                'username': 'user',
                'password': 'pass'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert 'postgresql+psycopg2' in url

    def test_postgres_alias_async(self):
        """Should accept 'postgres' as PostgreSQL alias (async)."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'postgres',
                'host': 'localhost',
                'database': 'test',
                'username': 'user',
                'password': 'pass'
            }
        })

        url = build_database_url(config, 'default', is_async=True)

        assert 'postgresql+asyncpg' in url

    def test_sqlserver_alias_sync(self):
        """Should accept 'sqlserver' as MSSQL alias (sync)."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'sqlserver',
                'host': 'localhost',
                'database': 'test',
                'username': 'sa',
                'password': 'pass'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert 'mssql+pyodbc' in url

    def test_sqlserver_alias_async(self):
        """Should accept 'sqlserver' as MSSQL alias (async)."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'sqlserver',
                'host': 'localhost',
                'database': 'test',
                'username': 'sa',
                'password': 'pass'
            }
        })

        url = build_database_url(config, 'default', is_async=True)

        assert 'mssql+aioodbc' in url


# ============================================================================
# Test Case Insensitivity
# ============================================================================

class TestCaseInsensitivity:
    """Test that driver names are case-insensitive."""

    def test_uppercase_driver_name(self):
        """Should accept uppercase driver names."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'POSTGRESQL',
                'host': 'localhost',
                'database': 'test',
                'username': 'user',
                'password': 'pass'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert 'postgresql+psycopg2' in url

    def test_mixed_case_driver_name(self):
        """Should accept mixed-case driver names."""
        config = ConfigManager(modules=[], auto_load=False)
        config.load()
        config.set('database.CONNECTIONS', {
            'default': {
                'driver': 'MySQL',
                'host': 'localhost',
                'database': 'test',
                'username': 'root',
                'password': 'pass'
            }
        })

        url = build_database_url(config, 'default', is_async=False)

        assert 'mysql+pymysql' in url

