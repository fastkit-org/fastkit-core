"""
Comprehensive tests for FastKit Core Config module.

Tests ConfigManager with all features:
- Environment variable loading
- Config file loading
- Dot notation access
- Type casting
- Multiple instances
- Error handling

"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastkit_core.config import *


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory with test files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create __init__.py
    (config_dir / "__init__.py").write_text("")

    # Create app.py config
    app_config = """
import os

APP_NAME = os.getenv('APP_NAME', 'TestApp')
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
VERSION = '1.0.0'
PORT = 8000
"""
    (config_dir / "app.py").write_text(app_config)

    # Create database.py config
    db_config = """
import os

CONNECTIONS = {
    'default': {
        'driver': os.getenv('DB_DRIVER', 'postgresql'),
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'testdb'),
        'username': os.getenv('DB_USERNAME', 'root'),
        'password': os.getenv('DB_PASSWORD', 'secret'),
    }
}

MAX_CONNECTIONS = 10
"""
    (config_dir / "database.py").write_text(db_config)

    return config_dir


@pytest.fixture
def temp_env_file(tmp_path):
    """Create temporary .env file."""
    env_file = tmp_path / ".env"
    env_content = """
APP_NAME=EnvApp
DEBUG=true
DB_HOST=envhost
DB_PORT=3306
NEW_VAR=from_env
"""
    env_file.write_text(env_content.strip())
    return env_file


@pytest.fixture
def clean_env():
    """Clean environment variables before and after test."""
    original_env = os.environ.copy()

    # Remove test variables
    test_vars = ['APP_NAME', 'DEBUG', 'DB_HOST', 'DB_PORT', 'DB_DRIVER',
                 'DB_NAME', 'DB_USERNAME', 'DB_PASSWORD', 'NEW_VAR']
    for var in test_vars:
        os.environ.pop(var, None)

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(autouse=True)
def reset_default_manager():
    """Reset default config manager before each test."""
    from fastkit_core import config as config_module
    config_module._default_manager = None
    yield
    config_module._default_manager = None

# ============================================================================
# Test ConfigManager Initialization
# ============================================================================

class TestConfigManagerInit:
    """Test ConfigManager initialization."""

    def test_init_default_modules(self, clean_env):
        """Should initialize with default modules."""
        manager = ConfigManager(auto_load=False)

        assert manager._modules == ['app', 'database', 'cache']
        assert manager._config_package == 'config'
        assert manager._loaded is False

    def test_init_custom_modules(self, clean_env):
        """Should initialize with custom modules."""
        manager = ConfigManager(
            modules=['custom1', 'custom2'],
            auto_load=False
        )

        assert manager._modules == ['custom1', 'custom2']

    def test_init_custom_package(self, clean_env):
        """Should initialize with custom package name."""
        manager = ConfigManager(
            config_package='my_config',
            auto_load=False
        )

        assert manager._config_package == 'my_config'

    def test_init_custom_env_file(self, clean_env, temp_env_file):
        """Should initialize with custom env file."""
        manager = ConfigManager(
            env_file=temp_env_file,
            auto_load=False
        )

        assert manager._env_file == temp_env_file

    def test_init_auto_load_default(self, clean_env):
        """Should auto-load by default."""
        with patch.object(ConfigManager, 'load'):
            manager = ConfigManager()
            ConfigManager.load.assert_called_once()

    def test_init_no_auto_load(self, clean_env):
        """Should not auto-load when disabled."""
        with patch.object(ConfigManager, 'load'):
            manager = ConfigManager(auto_load=False)
            ConfigManager.load.assert_not_called()

    def test_repr(self, clean_env):
        """Should have readable repr."""
        manager = ConfigManager(
            modules=['app'],
            config_package='test_config',
            auto_load=False
        )

        repr_str = repr(manager)
        assert 'ConfigManager' in repr_str
        assert 'test_config' in repr_str
        assert "['app']" in repr_str


# ============================================================================
# Test Environment Variable Loading
# ============================================================================

class TestEnvLoading:
    """Test .env file loading."""

    def test_load_explicit_env_file(self, clean_env, temp_env_file):
        """Should load specified .env file."""
        manager = ConfigManager(
            modules=[],
            env_file=temp_env_file,
            auto_load=False
        )
        manager._load_env()

        assert os.getenv('APP_NAME') == 'EnvApp'
        assert os.getenv('DEBUG') == 'true'
        assert os.getenv('DB_HOST') == 'envhost'

    def test_load_env_file_not_found(self, clean_env, tmp_path):
        """Should handle missing .env file gracefully."""
        missing_file = tmp_path / "nonexistent.env"
        manager = ConfigManager(
            modules=[],
            env_file=missing_file,
            auto_load=False
        )

        # Should not raise error
        manager._load_env()

    def test_auto_discover_env_file(self, clean_env, tmp_path, monkeypatch):
        """Should auto-discover .env file in parent directories."""
        # Create .env in parent directory
        env_file = tmp_path / ".env"
        env_file.write_text("AUTO_DISCOVERED=true")

        # Change to subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        monkeypatch.chdir(subdir)

        manager = ConfigManager(modules=[], auto_load=False)
        manager._load_env()

        assert os.getenv('AUTO_DISCOVERED') == 'true'

    def test_no_env_file_found(self, clean_env, tmp_path, monkeypatch):
        """Should handle no .env file gracefully."""
        # Change to directory without .env
        monkeypatch.chdir(tmp_path)

        manager = ConfigManager(modules=[], auto_load=False)

        # Should not raise error
        manager._load_env()