"""
Centralized Database Connection Manager.

Simplifies managing multiple database connections.
"""

from __future__ import annotations

import logging
from typing import Dict

from fastkit_core.config import ConfigManager
from fastkit_core.database.session import DatabaseManager

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Centralized manager for all database connections.

    Provides a clean API for managing multiple databases
    and their read replicas.

    Example:
```python
        from fastkit_core.database import ConnectionManager
        from fastkit_core.config import ConfigManager

        config = ConfigManager()
        conn_manager = ConnectionManager(config)

        # Setup primary database with read replicas
        conn_manager.add_connection(
            name='default',
            read_replicas=['read_1', 'read_2']
        )

        # Setup analytics database
        conn_manager.add_connection(
            name='analytics'
        )

        # Get connections
        primary_db = conn_manager.get('default')
        analytics_db = conn_manager.get('analytics')

        # Health check all
        health = conn_manager.health_check_all()
```
    """

    def __init__(self, config: ConfigManager, echo: bool = False):
        """
        Initialize connection manager.

        Args:
            config: Configuration manager
            echo: Echo SQL queries globally
        """
        self.config = config
        self.echo = echo
        self._connections: Dict[str, DatabaseManager] = {}

    def add_connection(
            self,
            name: str,
            read_replicas: list[str] | None = None,
            echo: bool | None = None
    ) -> DatabaseManager:
        """
        Add a new database connection.

        Args:
            name: Connection name (must exist in config)
            read_replicas: List of read replica connection names
            echo: Override global echo setting for this connection

        Returns:
            DatabaseManager instance

        Example:
```python
            # Simple connection
            conn_manager.add_connection('default')

            # With read replicas
            conn_manager.add_connection(
                'default',
                read_replicas=['read_1', 'read_2']
            )

            # With debug logging
            conn_manager.add_connection('debug_db', echo=True)
```
        """
        if name in self._connections:
            logger.warning(f"Connection '{name}' already exists. Returning existing.")
            return self._connections[name]

        manager = DatabaseManager(
            config=self.config,
            connection_name=name,
            read_replicas=read_replicas,
            echo=echo if echo is not None else self.echo
        )

        self._connections[name] = manager
        logger.info(f"Connection '{name}' added to ConnectionManager")

        return manager

    def get(self, name: str = 'default') -> DatabaseManager:
        """
        Get database manager by name.

        Args:
            name: Connection name

        Returns:
            DatabaseManager instance

        Raises:
            KeyError: If connection doesn't exist
        """
        if name not in self._connections:
            raise KeyError(
                f"Connection '{name}' not found. "
                f"Available: {list(self._connections.keys())}"
            )
        return self._connections[name]

    def has_connection(self, name: str) -> bool:
        """Check if connection exists."""
        return name in self._connections

    def remove_connection(self, name: str) -> None:
        """
        Remove and dispose a connection.

        Args:
            name: Connection name to remove
        """
        if name not in self._connections:
            logger.warning(f"Connection '{name}' not found. Nothing to remove.")
            return

        manager = self._connections[name]
        manager.dispose()
        del self._connections[name]

        logger.info(f"Connection '{name}' removed from ConnectionManager")

    def list_connections(self) -> list[str]:
        """Get list of all connection names."""
        return list(self._connections.keys())

    def health_check_all(self) -> dict[str, dict[str, bool]]:
        """
        Run health check on all connections.

        Returns:
            Dict mapping connection names to their health status

        Example:
```python
            health = conn_manager.health_check_all()
            # {
            #     'default': {'primary': True, 'read_1': True},
            #     'analytics': {'primary': True}
            # }
```
        """
        results = {}

        for name, manager in self._connections.items():
            try:
                results[name] = manager.health_check()
            except Exception as e:
                logger.error(f"Health check failed for '{name}': {e}")
                results[name] = {'error': str(e)}

        return results

    def dispose_all(self) -> None:
        """
        Dispose all database connections.

        Call this on application shutdown.
        """
        logger.info("Disposing all database connections...")

        for name, manager in self._connections.items():
            try:
                manager.dispose()
                logger.info(f"Connection '{name}' disposed")
            except Exception as e:
                logger.error(f"Error disposing '{name}': {e}")

        self._connections.clear()
        logger.info("All connections disposed")

    def __repr__(self) -> str:
        return (
            f"<ConnectionManager "
            f"connections={list(self._connections.keys())}>"
        )

    def __len__(self) -> int:
        """Number of connections."""
        return len(self._connections)


# ============================================================================
# Global Instance (Optional Convenience)
# ============================================================================

_global_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    """
    Get global connection manager.

    Creates one if it doesn't exist (requires ConfigManager).

    Returns:
        Global ConnectionManager instance
    """
    global _global_manager

    if _global_manager is None:
        from fastkit_core.config import get_config_manager
        config = get_config_manager()
        _global_manager = ConnectionManager(config)

    return _global_manager


def set_connection_manager(manager: ConnectionManager) -> None:
    """
    Set global connection manager.

    Args:
        manager: ConnectionManager to use globally
    """
    global _global_manager
    _global_manager = manager