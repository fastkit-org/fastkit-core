"""
Database session management.

Provides:
- Session factory
- Context managers
- Multi-connection support (read/write replicas)
- Thread-safe connection management
- Health checks
- Dependency injection for FastAPI
"""

from __future__ import annotations

import logging
import random
import threading
from contextlib import contextmanager
from typing import Generator
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
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
            url = self._build_url_from_params(conn_config, connection_name)

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

    def _build_url_from_params(self, conn_config: dict, connection_name: str) -> str:
        """
        Build database URL from connection parameters.

        Supports Laravel-style configuration:
        - driver: postgresql, mysql, sqlite, etc.
        - host, port, database, username, password
        """
        driver = conn_config.get('driver')

        if not driver:
            raise ValueError(
                f"Connection '{connection_name}' must have either 'url' or 'driver' in config"
            )

        # Handle SQLite (special case - file-based)
        if driver == 'sqlite':
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

        # Map common driver names to SQLAlchemy dialects
        driver_mapping = {
            'postgresql': 'postgresql+psycopg2',
            'mysql': 'mysql+pymysql',  # Using pymysql by default
            'mariadb': 'mysql+pymysql',
            'mssql': 'mssql+pyodbc',
            'oracle': 'oracle+cx_oracle',
        }

        dialect = driver_mapping.get(driver.lower(), driver)

        # Build URL based on whether we have credentials
        if username and password:
            if port:
                url = f"{dialect}://{username}:{password}@{host}:{port}/{database}"
            else:
                url = f"{dialect}://{username}:{password}@{host}/{database}"
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

        return url

    @property
    def url(self) -> str:
        """
        Get database URL for this manager's connection.

        Example:
            >>> manager = DatabaseManager(config, connection_name='default')
            >>> print(manager.url)
            'postgresql+psycopg2://user:***@localhost:5432/mydb'
        """
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

        return self._build_url_from_params(conn_config, self.connection_name)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions (WRITE operations).

        Automatically commits on success, rolls back on error.

        Example:
```python
            with db.session() as session:
                user = User(name="John")
                session.add(user)
                # Auto-commits here
```
        """
        session = self.SessionLocal()
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
        Context manager for READ-ONLY sessions.

        Uses read replicas if available (load-balanced).
        Falls back to primary if no replicas configured.

        Example:
```python
            # Load-balanced across read replicas
            with db.read_session() as session:
                users = session.query(User).all()
```
        """
        session = self.get_read_session()
        try:
            yield session
        finally:
            session.close()

    def get_session(self) -> Session:
        """
        Get a new write session.

        Note: Caller is responsible for closing!

        Example:
```python
            session = db.get_session()
            try:
                user = User(name="John")
                session.add(user)
                session.commit()
            except:
                session.rollback()
                raise
            finally:
                session.close()
```
        """
        return self.SessionLocal()

    def get_read_session(self) -> Session:
        """
        Get a new read session.

        Load-balances across read replicas if available.
        Falls back to primary connection if no replicas.

        Note: Caller is responsible for closing!
        """
        if not self.read_session_factories:
            # No replicas, use primary
            return self.SessionLocal()

        # Random load balancing across replicas
        factory = random.choice(self.read_session_factories)
        return factory()

    def health_check(self, check_replicas: bool = True) -> dict[str, bool]:
        """
        Check database connectivity.

        Args:
            check_replicas: Also check read replicas

        Returns:
            Dict with health status for each connection

        Example:
```python
            health = db.health_check()
            # {'primary': True, 'read_replica_1': True, 'read_replica_2': False}
```
        """
        results = {}

        # Check primary
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            results['primary'] = True
            logger.debug(f"Health check passed: primary ({self.connection_name})")
        except Exception as e:
            results['primary'] = False
            logger.error(f"Health check failed for primary: {e}")

        # Check replicas
        if check_replicas:
            for i, engine in enumerate(self.read_engines):
                replica_name = self.read_replicas[i]
                try:
                    with engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
                    results[replica_name] = True
                    logger.debug(f"Health check passed: {replica_name}")
                except Exception as e:
                    results[replica_name] = False
                    logger.error(f"Health check failed for {replica_name}: {e}")

        return results

    def dispose(self) -> None:
        """
        Dispose all database connections.

        Call this on application shutdown.

        Example:
```python
            @app.on_event("shutdown")
            def shutdown():
                db.dispose()
```
        """
        logger.info(f"Disposing database connections for '{self.connection_name}'")

        # Dispose primary engine
        self.engine.dispose()

        # Dispose read replica engines
        for engine in self.read_engines:
            engine.dispose()

        logger.info("All connections disposed")

    def __repr__(self) -> str:
        return (
            f"<DatabaseManager "
            f"connection='{self.connection_name}' "
            f"replicas={len(self.read_engines)}>"
        )


# ============================================================================
# FastAPI Integration
# ============================================================================

# Global database managers (thread-safe)
_db_managers: dict[str, DatabaseManager] = {}
_lock = threading.Lock()


def init_database(
    config: ConfigManager,
    connection_name: str = 'default',
    read_replicas: list[str] | None = None,
    echo: bool = False
) -> DatabaseManager:
    """
    Initialize global database manager.

    Call this once at app startup for each connection you need.

    Args:
        config: Configuration manager
        connection_name: Name of connection to initialize
        read_replicas: List of read replica connection names
        echo: Echo SQL queries

    Returns:
        Initialized DatabaseManager

    Example:
```python
        # app/main.py
        from fastkit_core.database.session import init_database
        from fastkit_core.config import get_config_manager

        @app.on_event("startup")
        def startup():
            config = get_config_manager()

            # Initialize primary database
            init_database(config, connection_name='default')

            # Initialize analytics database
            init_database(config, connection_name='analytics')

            # Initialize with read replicas
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
    Get initialized database manager.

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
    FastAPI dependency for database sessions (WRITE).

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

        # Using specific connection
        def get_analytics_db():
            return get_db(connection_name='analytics')

        @app.get("/stats")
        def get_stats(db: Session = Depends(get_analytics_db)):
            return db.query(Stats).all()
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
    FastAPI dependency for READ-ONLY database sessions.

    Uses read replicas if configured, otherwise falls back to primary.

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
            # This will use read replicas if configured
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
    Cleanup all database connections.

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
    Health check for all initialized databases.

    Returns:
        Dict mapping connection names to their health status

    Example:
```python
        @app.get("/health/database")
        def database_health():
            return health_check_all()
            # {
            #   'default': {'primary': True, 'read_replica_1': True},
            #   'analytics': {'primary': True}
            # }
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


def build_database_url(config: ConfigManager, connection_name: str = 'default') -> str:
    """
    Build database URL from configuration without creating engine.

    Useful for Alembic and other tools that need the URL
    but don't need a full DatabaseManager instance.

    Args:
        config: ConfigManager instance with database configuration
        connection_name: Name of the connection (default: 'default')

    Returns:
        Database connection URL string

    Raises:
        ValueError: If connection not found or missing required params

    Example:
        >>> from fastkit_core.config import ConfigManager
        >>> from fastkit_core.database import build_database_url
        >>>
        >>> config = ConfigManager(modules=['database'])
        >>> url = build_database_url(config, 'default')
        >>> print(url)
        'postgresql+psycopg2://user:***@localhost:5432/mydb'
    """
    # Get connections config
    connections = config.get('database.CONNECTIONS', {})

    if not connections:
        raise ValueError(
            "No database connections found in config. "
            "Ensure 'database.CONNECTIONS' is configured."
        )

    # Get specific connection config
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

    # Build URL from parameters
    driver = conn_config.get('driver')

    if not driver:
        raise ValueError(
            f"Connection '{connection_name}' must have either 'url' or 'driver'"
        )

    # Handle SQLite (file-based)
    if driver == 'sqlite':
        database = conn_config.get('database', ':memory:')
        return f'sqlite:///{database}'

    # Build URL for server-based databases
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
    driver_mapping = {
        'postgresql': 'postgresql+psycopg2',
        'mysql': 'mysql+pymysql',
        'mariadb': 'mysql+pymysql',
        'mssql': 'mssql+pyodbc',
        'oracle': 'oracle+cx_oracle',
    }

    dialect = driver_mapping.get(driver.lower(), driver)

    # Build authentication part
    if username and password:
        auth = f"{username}:{password}@"
    elif username:
        auth = f"{username}@"
    else:
        auth = ""

    # Build full URL
    if port:
        return f"{dialect}://{auth}{host}:{port}/{database}"
    else:
        return f"{dialect}://{auth}{host}/{database}"