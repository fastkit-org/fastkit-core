"""
FastKit Core Configuration Module

Supports multiple configuration instances for different environments.
"""

from __future__ import annotations

import importlib
import logging
import os
from pathlib import Path
from typing import Any, Final

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration operations fail."""
    pass


class ConfigManager:
    """
    Configuration manager with environment-specific support.

    Can be instantiated multiple times for different environments:
    - Development config
    - Test config
    - Production config

    Example:
        >>> # Development (default)
        >>> config = ConfigManager()
        >>>
        >>> # Testing with custom modules
        >>> test_config = ConfigManager(
        ...     modules=['test_app', 'test_database'],
        ...     env_file='.env.test'
        ... )
        >>>
        >>> # Custom config directory
        >>> custom_config = ConfigManager(
        ...     config_package='my_custom_config'
        ... )
    """

    __slots__ = ('_data', '_loaded', '_modules', '_config_package', '_env_file')

    def __init__(
        self,
        modules: list[str] | None = None,
        config_package: str = 'config',
        env_file: str | Path | None = None,
        auto_load: bool = True
    ) -> None:
        """
        Initialize configuration manager.

        Args:
            modules: List of config modules to load (e.g., ['app', 'database'])
                    If None, loads: ['app', 'database', 'cache']
            config_package: Python package containing config modules
                           Default: 'config'
            env_file: Path to .env file. If None, auto-discovers.
            auto_load: Whether to load config immediately

        Example:
            >>> # Default config
            >>> config = ConfigManager()
            >>>
            >>> # Test config
            >>> config = ConfigManager(
            ...     modules=['test_settings'],
            ...     env_file='.env.test'
            ... )
        """
        self._data: dict[str, dict[str, Any]] = {}
        self._loaded: bool = False
        self._modules: list[str] = modules or ['app', 'database', 'cache']
        self._config_package: str = config_package
        self._env_file: str | Path | None = env_file

        if auto_load:
            self.load()

    def load(self) -> None:
        """
        Load configuration from .env and config modules.

        Can be called multiple times to reload configuration.
        """
        # Load environment variables first
        self._load_env()

        # Load config modules
        for module_name in self._modules:
            self._load_module(module_name)

        self._loaded = True
        logger.info(f"Configuration loaded from package '{self._config_package}'")

    def _load_env(self) -> None:
        """Load .env file."""
        if self._env_file:
            # Explicit .env file provided
            env_path = Path(self._env_file)
            if env_path.exists():
                load_dotenv(env_path)
                logger.debug(f"Loaded {env_path}")
            else:
                logger.warning(f".env file not found: {env_path}")
            return

        # Auto-discover .env file
        current = Path.cwd()
        for directory in [current, *current.parents]:
            env_file = directory / '.env'
            if env_file.exists():
                load_dotenv(env_file)
                logger.debug(f"Loaded {env_file}")
                return

        logger.debug("No .env file found (this is OK)")

    def _load_module(self, name: str) -> None:
        """Load a configuration module."""
        try:
            module = importlib.import_module(f'{self._config_package}.{name}')
            self._data[name] = {}

            # Extract public attributes
            for key in dir(module):
                if not key.startswith('_'):
                    value = getattr(module, key)
                    # Skip callables except classes (which might be config)
                    if callable(value) and not isinstance(value, type):
                        continue
                    self._data[name][key] = value

            logger.debug(f"Loaded config module: {self._config_package}.{name}")

        except ModuleNotFoundError:
            logger.debug(f"Config module '{name}' not found (optional)")
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load config module '{name}': {e}"
            ) from e

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Environment variables override config files.

        Args:
            key_path: Dot-separated path (e.g., 'app.NAME')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        parts = key_path.split('.', 1)

        if len(parts) == 1:
            return self._data.get(parts[0], {}).copy()

        module, key = parts

        # Check environment variable override
        env_key = f"{module.upper()}_{key.upper()}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            return self._cast_value(env_value)

        # Get from config data
        try:
            return self._data[module][key]
        except KeyError:
            return default

    def _cast_value(self, value: str) -> bool | int | float | str:
        """Cast environment variable string to appropriate type."""
        # Boolean
        if value.lower() in ('true', 'false', 'yes', 'no', '1', '0'):
            return value.lower() in ('true', 'yes', '1')

        # Integer
        if value.lstrip('-').isdigit():
            return int(value)

        # Float
        try:
            return float(value)
        except ValueError:
            pass

        return value

    def set(self, key_path: str, value: Any) -> None:
        """
        Set configuration value at runtime.

        Useful for testing or dynamic configuration.

        Args:
            key_path: Dot-separated path
            value: Value to set
        """
        parts = key_path.split('.', 1)
        if len(parts) != 2:
            raise ConfigurationError(
                f"Invalid key format '{key_path}'. Use 'module.key' format."
            )

        module, key = parts

        if module not in self._data:
            self._data[module] = {}

        self._data[module][key] = value

    def has(self, key_path: str) -> bool:
        """Check if configuration key exists."""
        parts = key_path.split('.', 1)

        if len(parts) == 1:
            return parts[0] in self._data

        module, key = parts
        return module in self._data and key in self._data[module]

    def all(self) -> dict[str, dict[str, Any]]:
        """Get all configuration data."""
        return {
            module: config.copy()
            for module, config in self._data.items()
        }

    def reload(self) -> None:
        """Reload all configuration."""
        self._data.clear()
        self._loaded = False
        self.load()

    def __repr__(self) -> str:
        return (
            f"<ConfigManager package='{self._config_package}' "
            f"modules={self._modules} loaded={self._loaded}>"
        )


# ============================================================================
# Default Global Instance (for convenience)
# ============================================================================

_default_manager: ConfigManager | None = None


def get_config_manager() -> ConfigManager:
    """
    Get the default configuration manager.

    Creates one if it doesn't exist.

    Returns:
        Default ConfigManager instance
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = ConfigManager()
    return _default_manager


def set_config_manager(manager: ConfigManager) -> None:
    """
    Set the default configuration manager.

    Useful for testing or when you want to use custom config.

    Args:
        manager: ConfigManager instance to use as default

    Example:
        >>> test_config = ConfigManager(env_file='.env.test')
        >>> set_config_manager(test_config)
    """
    global _default_manager
    _default_manager = manager


# ============================================================================
# Convenience Functions (use default manager)
# ============================================================================

def config(key_path: str, default: Any = None) -> Any:
    """
    Get configuration value from default manager.

    Args:
        key_path: Dot notation path (e.g., 'app.NAME')
        default: Default value if key doesn't exist

    Returns:
        Configuration value or default
    """
    return get_config_manager().get(key_path, default)


def config_set(key_path: str, value: Any) -> None:
    """Set configuration value in default manager."""
    get_config_manager().set(key_path, value)


def config_has(key_path: str) -> bool:
    """Check if key exists in default manager."""
    return get_config_manager().has(key_path)


def config_all() -> dict[str, dict[str, Any]]:
    """Get all configuration from default manager."""
    return get_config_manager().all()


def config_reload() -> None:
    """Reload default manager configuration."""
    get_config_manager().reload()


# Public API
__all__ = [
    'ConfigManager',
    'ConfigurationError',
    'config',
    'config_set',
    'config_has',
    'config_all',
    'config_reload',
    'get_config_manager',
    'set_config_manager',
]