"""
Database session management with async support.

Provides:
- Session factory (sync and async)
- Context managers for both modes
- Multi-connection support (read/write replicas)
- Thread-safe connection management
- Health checks
- Dependency injection for FastAPI
- Full support for PostgreSQL, MySQL, MariaDB, MSSQL, Oracle

Supported databases:
- PostgreSQL (sync: psycopg2, async: asyncpg)
- MySQL (sync: pymysql, async: aiomysql)
- MariaDB (sync: pymysql, async: aiomysql)
- MSSQL (sync: pyodbc, async: aioodbc)
- Oracle (sync: cx_oracle, async: oracledb)
- SQLite (sync only)

"""

from __future__ import annotations

import logging
import random
import threading
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from fastkit_core.config import ConfigManager

logger = logging.getLogger(__name__)



class DatabaseManager:
    """
    Manages database connections and sessions.

    Supports:
    - Multiple named connections (default, analytics, etc.)
    - Read replicas for load balancing
    - Connection pooling
    - Health checks
    - PostgreSQL, MySQL, MariaDB, MSSQL, Oracle, SQLite

    Example:
```python
        from fastkit_core.database import DatabaseManager
        from fastkit_core.config import ConfigManager

        config = ConfigManager()

        # Single connection
        db = DatabaseManager(config)

        # With read replicas
        db = DatabaseManager(
            config,
            connection_name='default',
            read_replicas=['read_replica_1', 'read_replica_2']
        )

        # Write operation
        with db.session() as session:
            user = User(name="John")
            session.add(user)
            # Auto-commits here

        # Read operation (load-balanced across replicas)
        with db.read_session() as session:
            users = session.query(User).all()
```
    """

    def __init__(
        self,
        config: ConfigManager,
        connection_name: str = 'default',
        read_replicas: list[str] | None = None,
        echo: bool = False
    ):
        """
        Initialize database manager.

        Args:
            config: Configuration manager
            connection_name: Which connection to use from config
            read_replicas: List of read replica connection names
            echo: Echo SQL queries (for debugging)
        """
        self.config = config
        self.connection_name = connection_name
        self.echo = echo

        # Build primary (write) engine
        self.engine = self._create_engine(connection_name)

        # Create primary session factory
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False
        )

        # Setup read replicas
        self.read_replicas = read_replicas or []
        self.read_engines: list[Engine] = []
        self.read_session_factories: list[sessionmaker] = []

        for replica_name in self.read_replicas:
            try:
                engine = self._create_engine(replica_name)
                self.read_engines.append(engine)
                self.read_session_factories.append(
                    sessionmaker(
                        bind=engine,
                        autocommit=False,
                        autoflush=False
                    )
                )
                logger.info(f"Read replica '{replica_name}' configured")
            except Exception as e:
                logger.warning(
                    f"Failed to configure read replica '{replica_name}': {e}"
                )

        logger.info(
            f"DatabaseManager initialized: "
            f"connection='{connection_name}', "
            f"replicas={len(self.read_session_factories)}"
        )

    def _create_engine(self, connection_name: str) -> Engine:
        """
        Create SQLAlchemy engine from config.

        Supports two config formats:

        1. Direct URL:
            'default': {
                'url': 'postgresql://user:pass@localhost/db'
            }

        2. Connection parameters (like Laravel):
            'default': {
                'driver': 'postgresql',
                'host': 'localhost',
                'port': 5432,
                'database': 'mydb',
                'username': 'user',
                'password': 'secret'
            }
        """
        # Get all connections dict
        connections = self.config.get('database.CONNECTIONS', {})

        # Get specific connection config
        conn_config = connections.get(connection_name)

        if not conn_config:
            available = list(connections.keys())
            raise ValueError(
                f"Database connection '{connection_name}' not found in config. "
                f"Available connections: {available}"
            )

        # Get or build connection URL
        url = conn_config.get('url')

        if not url:
            # Build URL from parameters (Laravel-style)
            url = self._build_url_from_params(conn_config, connection_name, is_async=False)

        is_sqlite = url.startswith('sqlite')

        # Base engine options (always applicable)
        engine_options = {
            'echo': conn_config.get('echo', self.echo),
        }

        # Add pooling options only for non-SQLite databases
        if not is_sqlite:
            engine_options.update({
                'pool_size': conn_config.get('pool_size', 5),
                'max_overflow': conn_config.get('max_overflow', 10),
                'pool_timeout': conn_config.get('pool_timeout', 30),
                'pool_recycle': conn_config.get('pool_recycle', 3600),
            })

        # Create and return engine
        return create_engine(url, **engine_options)

    def _build_url_from_params(
            self,
            conn_config: dict,
            connection_name: str,
            is_async: bool = False
    ) -> str:
        """
        Build database URL from connection parameters.

        Supports Laravel-style configuration with full driver support:
        - PostgreSQL (psycopg2 sync, asyncpg async)
        - MySQL (pymysql sync, aiomysql async)
        - MariaDB (pymysql sync, aiomysql async)
        - MSSQL (pyodbc sync, aioodbc async)
        - Oracle (cx_oracle sync, oracledb async)
        - SQLite (sync only)

        Args:
            conn_config: Connection configuration dict
            connection_name: Name of the connection
            is_async: Whether to use async drivers

        Returns:
            SQLAlchemy connection URL
        """
        driver = conn_config.get('driver')

        if not driver:
            raise ValueError(
                f"Connection '{connection_name}' must have either 'url' or 'driver' in config"
            )

        # Handle SQLite (special case - file-based, sync only)
        if driver.lower() in ('sqlite', 'sqlite3'):
            if is_async:
                raise ValueError(
                    f"SQLite does not support async mode. "
                    f"Use synchronous DatabaseManager for SQLite connections."
                )
            database = conn_config.get('database', ':memory:')
            return f'sqlite:///{database}'

        # For other databases, build URL
        host = conn_config.get('host', 'localhost')
        port = conn_config.get('port')
        database = conn_config.get('database')
        username = conn_config.get('username')
        password = conn_config.get('password')

        if not database:
            raise ValueError(
                f"Connection '{connection_name}' missing 'database' parameter"
            )

        # Map driver names to SQLAlchemy dialects
        # Support both sync and async drivers
        if is_async:
            driver_mapping = {
                'postgresql': 'postgresql+asyncpg',
                'postgres': 'postgresql+asyncpg',
                'mysql': 'mysql+aiomysql',
                'mariadb': 'mysql+aiomysql',
                'mssql': 'mssql+aioodbc',
                'sqlserver': 'mssql+aioodbc',
                'oracle': 'oracle+oracledb',
            }
        else:
            driver_mapping = {
                'postgresql': 'postgresql+psycopg2',
                'postgres': 'postgresql+psycopg2',
                'mysql': 'mysql+pymysql',
                'mariadb': 'mysql+pymysql',
                'mssql': 'mssql+pyodbc',
                'sqlserver': 'mssql+pyodbc',
                'oracle': 'oracle+cx_oracle',
            }

        dialect = driver_mapping.get(driver.lower())

        if not dialect:
            raise ValueError(
                f"Unsupported driver '{driver}'. "
                f"Supported drivers: {', '.join(driver_mapping.keys())}"
            )

        # URL-encode password if it contains special characters
        encoded_password = quote_plus(password) if password else None

        # Build URL based on whether we have credentials
        if username and encoded_password:
            if port:
                url = f"{dialect}://{username}:{encoded_password}@{host}:{port}/{database}"
            else:
                url = f"{dialect}://{username}:{encoded_password}@{host}/{database}"
        elif username:
            if port:
                url = f"{dialect}://{username}@{host}:{port}/{database}"
            else:
                url = f"{dialect}://{username}@{host}/{database}"
        else:
            if port:
                url = f"{dialect}://{host}:{port}/{database}"
            else:
                url = f"{dialect}://{host}/{database}"

        # Add connection options if specified
        options = conn_config.get('options', {})
        if options:
            option_str = '&'.join(f"{k}={v}" for k, v in options.items())
            url = f"{url}?{option_str}"

        return url

    @property
    def url(self) -> str:
        """Get database URL for this manager's connection."""
        connections = self.config.get('database.CONNECTIONS', {})
        conn_config = connections.get(self.connection_name)

        if not conn_config:
            raise ValueError(
                f"Database connection '{self.connection_name}' not found"
            )

        # Return existing URL or build from params
        url = conn_config.get('url')
        if url:
            return url

        return self._build_url_from_params(conn_config, self.connection_name, is_async=False)

    def get_session(self) -> Session:
        """Get a new database session (for write operations)."""
        return self.SessionLocal()

    def get_read_session(self) -> Session:
        """
        Get a read-only session (load-balanced across replicas).

        Falls back to primary if no replicas configured.
        """
        if not self.read_session_factories:
            # No replicas, use primary
            return self.SessionLocal()

        # Random load balancing across replicas
        factory = random.choice(self.read_session_factories)
        return factory()

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Context manager for write sessions.

        Auto-commits on success, rolls back on error.

        Example:
        ```python
            with db.session() as session:
                user = User(name="John")
                session.add(user)
                # Auto-commits here
        ```
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def read_session(self) -> Generator[Session, None, None]:
        """
        Context manager for read-only sessions.

        Uses read replicas if configured.

        Example:
        ```python
            with db.read_session() as session:
                users = session.query(User).all()
        ```
        """
        session = self.get_read_session()
        try:
            yield session
        finally:
            session.close()

    def health_check(self) -> dict[str, bool]:
        """
        Check database connectivity.

        Returns:
            Dict with health status for primary and replicas

        Example:
        ```python
            status = db.health_check()
            # {'primary': True, 'read_replica_1': True, 'read_replica_2': False}
        ```
        """
        results = {}

        # Check primary
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                results['primary'] = True
        except Exception as e:
            logger.error(f"Primary connection health check failed: {e}")
            results['primary'] = False

        # Check replicas
        for i, engine in enumerate(self.read_engines):
            replica_name = self.read_replicas[i]
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                    results[replica_name] = True
            except Exception as e:
                logger.error(f"Replica '{replica_name}' health check failed: {e}")
                results[replica_name] = False

        return results

    def dispose(self) -> None:
        """Dispose all database connections."""
        logger.info(f"Disposing connection '{self.connection_name}'")

        self.engine.dispose()

        for engine in self.read_engines:
            engine.dispose()

        logger.info(f"Connection '{self.connection_name}' disposed")


    def __repr__(self) -> str:
        return (
            f"<DatabaseManager "
            f"connection='{self.connection_name}' "
            f"replicas={len(self.read_engines)}>"
        )


class AsyncDatabaseManager:
    """
    Manages asynchronous database connections and sessions.

    Supports:
    - Multiple named connections (default, analytics, etc.)
    - Read replicas for load balancing
    - Connection pooling
    - Health checks
    - PostgreSQL (asyncpg), MySQL/MariaDB (aiomysql), MSSQL (aioodbc), Oracle (oracledb)

    Example:
    ```python
        from fastkit_core.database import AsyncDatabaseManager
        from fastkit_core.config import ConfigManager

        config = ConfigManager()

        # Single connection
        db = AsyncDatabaseManager(config)

        # With read replicas
        db = AsyncDatabaseManager(
            config,
            connection_name='default',
            read_replicas=['read_replica_1', 'read_replica_2']
        )

        # Write operation
        async with db.session() as session:
            user = User(name="John")
            session.add(user)
            await session.commit()

        # Read operation (load-balanced across replicas)
        async with db.read_session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
    ```
    """

    def __init__(
            self,
            config: ConfigManager,
            connection_name: str = 'default',
            read_replicas: list[str] | None = None,
            echo: bool = False
    ):
        """
        Initialize async database manager.

        Args:
            config: Configuration manager
            connection_name: Which connection to use from config
            read_replicas: List of read replica connection names
            echo: Echo SQL queries (for debugging)
        """
        self.config = config
        self.connection_name = connection_name
        self.echo = echo

        # Build primary (write) engine
        self.engine = self._create_async_engine(connection_name)

        # Create primary session factory
        self.AsyncSessionLocal = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )

        # Setup read replicas
        self.read_replicas = read_replicas or []
        self.read_engines: list[AsyncEngine] = []
        self.read_session_factories: list[async_sessionmaker] = []

        for replica_name in self.read_replicas:
            try:
                engine = self._create_async_engine(replica_name)
                self.read_engines.append(engine)
                self.read_session_factories.append(
                    async_sessionmaker(
                        bind=engine,
                        class_=AsyncSession,
                        autocommit=False,
                        autoflush=False,
                        expire_on_commit=False
                    )
                )
                logger.info(f"Async read replica '{replica_name}' configured")
            except Exception as e:
                logger.warning(
                    f"Failed to configure async read replica '{replica_name}': {e}"
                )

        logger.info(
            f"AsyncDatabaseManager initialized: "
            f"connection='{connection_name}', "
            f"replicas={len(self.read_session_factories)}"
        )

    def _create_async_engine(self, connection_name: str) -> AsyncEngine:
        """Create async SQLAlchemy engine from config."""
        # Get all connections dict
        connections = self.config.get('database.CONNECTIONS', {})

        # Get specific connection config
        conn_config = connections.get(connection_name)

        if not conn_config:
            available = list(connections.keys())
            raise ValueError(
                f"Database connection '{connection_name}' not found in config. "
                f"Available connections: {available}"
            )

        # Get or build connection URL
        url = conn_config.get('url')

        if not url:
            # Build URL from parameters with async drivers
            url = self._build_url_from_params(conn_config, connection_name, is_async=True)

        # Validate that URL is async-compatible
        if url.startswith('sqlite'):
            raise ValueError(
                f"SQLite does not support async mode. "
                f"Use synchronous DatabaseManager for connection '{connection_name}'."
            )

        # Base engine options
        engine_options = {
            'echo': conn_config.get('echo', self.echo),
            'pool_size': conn_config.get('pool_size', 5),
            'max_overflow': conn_config.get('max_overflow', 10),
            'pool_timeout': conn_config.get('pool_timeout', 30),
            'pool_recycle': conn_config.get('pool_recycle', 3600),
        }

        # Create and return async engine
        return create_async_engine(url, **engine_options)

    def _build_url_from_params(
            self,
            conn_config: dict,
            connection_name: str,
            is_async: bool = True
    ) -> str:
        """
        Build async database URL from connection parameters.

        Reuses the sync version's logic with is_async=True.
        """
        # Create a temporary sync manager instance just to use its method
        # This avoids code duplication
        temp_manager = DatabaseManager.__new__(DatabaseManager)
        return temp_manager._build_url_from_params(conn_config, connection_name, is_async)

    @property
    def url(self) -> str:
        """Get database URL for this manager's connection."""
        connections = self.config.get('database.CONNECTIONS', {})
        conn_config = connections.get(self.connection_name)

        if not conn_config:
            raise ValueError(
                f"Database connection '{self.connection_name}' not found"
            )

        url = conn_config.get('url')
        if url:
            return url

        return self._build_url_from_params(conn_config, self.connection_name, is_async=True)

    def get_session(self) -> AsyncSession:
        """Get a new async database session (for write operations)."""
        return self.AsyncSessionLocal()

    def get_read_session(self) -> AsyncSession:
        """
        Get an async read-only session (load-balanced across replicas).

        Falls back to primary if no replicas configured.
        """
        if not self.read_session_factories:
            return self.AsyncSessionLocal()

        # Random load balancing across replicas
        factory = random.choice(self.read_session_factories)
        return factory()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Async context manager for write sessions.

        Auto-commits on success, rolls back on error.

        Example:
```python
            async with db.session() as session:
                user = User(name="John")
                session.add(user)
                await session.commit()
```
        """
        session = self.get_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @asynccontextmanager
    async def read_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Async context manager for read-only sessions.

        Uses read replicas if configured.

        Example:
```python
            async with db.read_session() as session:
                result = await session.execute(select(User))
                users = result.scalars().all()
```
        """
        session = self.get_read_session()
        try:
            yield session
        finally:
            await session.close()

    async def health_check(self) -> dict[str, bool]:
        """
        Check async database connectivity.

        Returns:
            Dict with health status for primary and replicas
        """
        results = {}

        # Check primary
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                results['primary'] = True
        except Exception as e:
            logger.error(f"Async primary connection health check failed: {e}")
            results['primary'] = False

        # Check replicas
        for i, engine in enumerate(self.read_engines):
            replica_name = self.read_replicas[i]
            try:
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                    results[replica_name] = True
            except Exception as e:
                logger.error(f"Async replica '{replica_name}' health check failed: {e}")
                results[replica_name] = False

        return results

    async def dispose(self) -> None:
        """Dispose all async database connections."""
        logger.info(f"Disposing async connection '{self.connection_name}'")

        await self.engine.dispose()

        for engine in self.read_engines:
            await engine.dispose()

        logger.info(f"Async connection '{self.connection_name}' disposed")

# ============================================================================
# Global Manager Registry (Sync)
# ============================================================================

_db_managers: dict[str, DatabaseManager] = {}
_lock = threading.Lock()


def init_database(
    config: ConfigManager,
    connection_name: str = 'default',
    read_replicas: list[str] | None = None,
    echo: bool = False
) -> DatabaseManager:
    """
    Initialize a database connection globally (sync).

    Thread-safe initialization that prevents duplicate connections.

    Args:
        config: Configuration manager
        connection_name: Name for this connection
        read_replicas: List of read replica connection names
        echo: Echo SQL queries

    Returns:
        DatabaseManager instance

    Example:
```python
        from fastkit_core.config import ConfigManager
        from fastkit_core.database import init_database

        @app.on_event("startup")
        def startup():
            config = ConfigManager()

            # Initialize primary database
            init_database(config)

            # Initialize with replicas
            init_database(
                config,
                connection_name='default',
                read_replicas=['read_replica_1', 'read_replica_2']
            )
```
    """
    with _lock:
        if connection_name in _db_managers:
            logger.warning(
                f"Database manager '{connection_name}' already initialized. "
                "Skipping."
            )
            return _db_managers[connection_name]

        manager = DatabaseManager(
            config,
            connection_name=connection_name,
            read_replicas=read_replicas,
            echo=echo
        )
        _db_managers[connection_name] = manager

        logger.info(f"Database manager '{connection_name}' initialized globally")
        return manager


def get_db_manager(connection_name: str = 'default') -> DatabaseManager:
    """
    Get initialized database manager (sync).

    Args:
        connection_name: Name of connection to get

    Returns:
        DatabaseManager instance

    Raises:
        RuntimeError: If database not initialized
    """
    if connection_name not in _db_managers:
        raise RuntimeError(
            f"Database '{connection_name}' not initialized. "
            f"Call init_database(config, connection_name='{connection_name}') "
            "at app startup."
        )
    return _db_managers[connection_name]


def get_db(connection_name: str = 'default') -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions (WRITE) - sync.

    Args:
        connection_name: Which database connection to use

    Yields:
        Database session

    Example:
```python
        from fastapi import Depends
        from fastkit_core.database.session import get_db

        @app.get("/users")
        def list_users(db: Session = Depends(get_db)):
            return db.query(User).all()
```
    """
    manager = get_db_manager(connection_name)
    session = manager.get_session()
    try:
        yield session
    finally:
        session.close()


def get_read_db(connection_name: str = 'default') -> Generator[Session, None, None]:
    """
    FastAPI dependency for READ-ONLY database sessions - sync.

    Uses read replicas if configured.

    Args:
        connection_name: Which database connection to use

    Yields:
        Database session (read-only)

    Example:
```python
        from fastapi import Depends
        from fastkit_core.database.session import get_read_db

        @app.get("/users")
        def list_users(db: Session = Depends(get_read_db)):
            return db.query(User).all()
```
    """
    manager = get_db_manager(connection_name)
    session = manager.get_read_session()
    try:
        yield session
    finally:
        session.close()


def shutdown_database() -> None:
    """
    Cleanup all sync database connections.

    Call this on application shutdown.

    Example:
```python
        @app.on_event("shutdown")
        def shutdown():
            shutdown_database()
```
    """
    with _lock:
        logger.info("Shutting down all database connections...")

        for name, manager in _db_managers.items():
            try:
                manager.dispose()
                logger.info(f"Database '{name}' disposed successfully")
            except Exception as e:
                logger.error(f"Error disposing database '{name}': {e}")

        _db_managers.clear()
        logger.info("All database connections shut down")


def health_check_all() -> dict[str, dict[str, bool]]:
    """
    Health check for all initialized databases (sync).

    Returns:
        Dict mapping connection names to their health status

    Example:
```python
        @app.get("/health/database")
        def database_health():
            return health_check_all()
```
    """
    results = {}

    with _lock:
        for name, manager in _db_managers.items():
            try:
                results[name] = manager.health_check()
            except Exception as e:
                logger.error(f"Health check failed for '{name}': {e}")
                results[name] = {'error': str(e)}

    return results


# ============================================================================
# Global Manager Registry (Async)
# ============================================================================

_async_db_managers: dict[str, AsyncDatabaseManager] = {}
_async_lock = threading.Lock()


def init_async_database(
        config: ConfigManager,
        connection_name: str = 'default',
        read_replicas: list[str] | None = None,
        echo: bool = False
) -> AsyncDatabaseManager:
    """
    Initialize an async database connection globally.

    Thread-safe initialization that prevents duplicate connections.

    Args:
        config: Configuration manager
        connection_name: Name for this connection
        read_replicas: List of read replica connection names
        echo: Echo SQL queries

    Returns:
        AsyncDatabaseManager instance

    Example:
    ```python
        from fastkit_core.config import ConfigManager
        from fastkit_core.database import init_async_database

        @app.on_event("startup")
        async def startup():
            config = ConfigManager()

            # Initialize async database
            init_async_database(config)

            # With replicas
            init_async_database(
                config,
                connection_name='default',
                read_replicas=['read_replica_1', 'read_replica_2']
            )
    ```
    """
    with _async_lock:
        if connection_name in _async_db_managers:
            logger.warning(
                f"Async database manager '{connection_name}' already initialized. "
                "Skipping."
            )
            return _async_db_managers[connection_name]

        manager = AsyncDatabaseManager(
            config,
            connection_name=connection_name,
            read_replicas=read_replicas,
            echo=echo
        )
        _async_db_managers[connection_name] = manager

        logger.info(f"Async database manager '{connection_name}' initialized globally")
        return manager


def get_async_db_manager(connection_name: str = 'default') -> AsyncDatabaseManager:
    """
    Get initialized async database manager.

    Args:
        connection_name: Name of connection to get

    Returns:
        AsyncDatabaseManager instance

    Raises:
        RuntimeError: If database not initialized
    """
    if connection_name not in _async_db_managers:
        raise RuntimeError(
            f"Async database '{connection_name}' not initialized. "
            f"Call init_async_database(config, connection_name='{connection_name}') "
            "at app startup."
        )
    return _async_db_managers[connection_name]


async def get_async_db(
        connection_name: str = 'default'
) -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for async database sessions (WRITE).

    Args:
        connection_name: Which database connection to use

    Yields:
        Async database session

    Example:
    ```python
        from fastapi import Depends
        from fastkit_core.database.session import get_async_db
        from sqlalchemy.ext.asyncio import AsyncSession

        @app.get("/users")
        async def list_users(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    ```
    """
    manager = get_async_db_manager(connection_name)
    session = manager.get_session()
    try:
        yield session
    finally:
        await session.close()


async def get_async_read_db(
        connection_name: str = 'default'
) -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for async READ-ONLY database sessions.

    Uses read replicas if configured.

    Args:
        connection_name: Which database connection to use

    Yields:
        Async database session (read-only)

    Example:
    ```python
        from fastapi import Depends
        from fastkit_core.database.session import get_async_read_db
        from sqlalchemy.ext.asyncio import AsyncSession

        @app.get("/users")
        async def list_users(db: AsyncSession = Depends(get_async_read_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    ```
    """
    manager = get_async_db_manager(connection_name)
    session = manager.get_read_session()
    try:
        yield session
    finally:
        await session.close()


async def shutdown_async_database() -> None:
    """
    Cleanup all async database connections.

    Call this on application shutdown.

    Example:
    ```python
        @app.on_event("shutdown")
        async def shutdown():
            await shutdown_async_database()
    ```
    """
    with _async_lock:
        logger.info("Shutting down all async database connections...")

        for name, manager in _async_db_managers.items():
            try:
                await manager.dispose()
                logger.info(f"Async database '{name}' disposed successfully")
            except Exception as e:
                logger.error(f"Error disposing async database '{name}': {e}")

        _async_db_managers.clear()
        logger.info("All async database connections shut down")


async def health_check_all_async() -> dict[str, dict[str, bool]]:
    """
    Health check for all initialized async databases.

    Returns:
        Dict mapping connection names to their health status

    Example:
    ```python
        @app.get("/health/database")
        async def database_health():
            return await health_check_all_async()
    ```
    """
    results = {}

    with _async_lock:
        for name, manager in _async_db_managers.items():
            try:
                results[name] = await manager.health_check()
            except Exception as e:
                logger.error(f"Async health check failed for '{name}': {e}")
                results[name] = {'error': str(e)}

    return results


def build_database_url(
        config: ConfigManager,
        connection_name: str = 'default',
        is_async: bool = False
) -> str:
    """
    Build database URL from configuration without creating engine.

    Useful for Alembic and other tools.

    Args:
        config: ConfigManager instance with database configuration
        connection_name: Name of the connection (default: 'default')
        is_async: Whether to build async URL (default: False)

    Returns:
        Database connection URL string

    Raises:
        ValueError: If connection not found or missing required params

    Example:
    ```python
        from fastkit_core.config import ConfigManager
        from fastkit_core.database import build_database_url

        config = ConfigManager(modules=['database'])

        # Sync URL
        url = build_database_url(config, 'default')
        # 'postgresql+psycopg2://user:***@localhost:5432/mydb'

        # Async URL
        async_url = build_database_url(config, 'default', is_async=True)
        # 'postgresql+asyncpg://user:***@localhost:5432/mydb'
    ```
    """
    connections = config.get('database.CONNECTIONS', {})

    if not connections:
        raise ValueError(
            "No database connections found in config. "
            "Ensure 'database.CONNECTIONS' is configured."
        )

    conn_config = connections.get(connection_name)

    if not conn_config:
        available = list(connections.keys())
        raise ValueError(
            f"Database connection '{connection_name}' not found. "
            f"Available connections: {available}"
        )

    # If URL is directly provided, return it
    url = conn_config.get('url')
    if url:
        return url

    # Build URL from parameters using temporary manager instance
    temp_manager = DatabaseManager.__new__(DatabaseManager)
    return temp_manager._build_url_from_params(conn_config, connection_name, is_async)
