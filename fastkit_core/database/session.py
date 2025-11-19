"""
Database session management.

Provides:
- Session factory
- Context managers
- Dependency injection for FastAPI
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from fastkit_core.config import ConfigManager


class DatabaseManager:
    """
    Manages database connections and sessions.

    Example:
```python
        from fastkit_core.database import DatabaseManager
        from fastkit_core.config import ConfigManager

        config = ConfigManager()
        db = DatabaseManager(config)

        # Get session
        with db.session() as session:
            users = session.query(User).all()
```
    """

    def __init__(
            self,
            config: ConfigManager,
            connection_name: str = 'default',
            echo: bool = False
    ):
        """
        Initialize database manager.

        Args:
            config: Configuration manager
            connection_name: Which connection to use from config
            echo: Echo SQL queries (for debugging)
        """
        self.config = config
        self.connection_name = connection_name
        self.echo = echo

        # Build engine
        self.engine = self._create_engine()

        # Create session factory
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False
        )

    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine from config."""
        # Get connection config
        conn_config = self.config.get(
            f'database.CONNECTIONS.{self.connection_name}'
        )

        if not conn_config:
            raise ValueError(
                f"Database connection '{self.connection_name}' not found in config"
            )

        # Build connection URL
        driver = conn_config.get('driver', 'postgresql')
        host = conn_config.get('host', 'localhost')
        port = conn_config.get('port', 5432)
        database = conn_config.get('database')
        username = conn_config.get('username')
        password = conn_config.get('password')

        url = f"{driver}://{username}:{password}@{host}:{port}/{database}"

        # Pool configuration
        pool_config = self.config.get('database.POOL', {})

        # Create engine
        engine = create_engine(
            url,
            echo=self.echo,
            pool_size=pool_config.get('pool_size', 5),
            max_overflow=pool_config.get('max_overflow', 10),
            pool_timeout=pool_config.get('pool_timeout', 30),
            pool_recycle=pool_config.get('pool_recycle', 3600),
        )

        return engine

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.

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

    def get_session(self) -> Session:
        """
        Get a new session.

        Note: Caller is responsible for closing!

        Example:
```python
            session = db.get_session()
            try:
                # Use session
                pass
            finally:
                session.close()
```
        """
        return self.SessionLocal()


# ============================================================================
# FastAPI Integration
# ============================================================================

# Global database manager (initialized by app)
_db_manager: DatabaseManager | None = None


def init_database(config: ConfigManager) -> DatabaseManager:
    """
    Initialize global database manager.

    Call this once at app startup.

    Example:
```python
        # app/main.py
        from fastkit_core.database.session import init_database
        from fastkit_core.config import get_config_manager

        @app.on_event("startup")
        def startup():
            config = get_config_manager()
            init_database(config)
```
    """
    global _db_manager
    _db_manager = DatabaseManager(config)
    return _db_manager


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Example:
```python
        from fastapi import Depends
        from fastkit_core.database.session import get_db

        @app.get("/users")
        def list_users(db: Session = Depends(get_db)):
            return db.query(User).all()
```
    """
    if _db_manager is None:
        raise RuntimeError(
            "Database not initialized. "
            "Call init_database() at app startup."
        )

    session = _db_manager.get_session()
    try:
        yield session
    finally:
        session.close()