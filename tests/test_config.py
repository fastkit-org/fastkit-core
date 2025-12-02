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