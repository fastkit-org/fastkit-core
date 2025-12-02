"""
Comprehensive tests for FastKit Core Config module.

Tests ConfigManager with all features:
- Environment variable loading
- Config file loading
- Dot notation access
- Type casting
- Multiple instances
- Error handling

Target Coverage: 95%+
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastkit_core.config import (
    ConfigManager,
    ConfigurationError,
    config,
    config_set,
    config_has,
    config_all,
    config_reload,
    get_config_manager,
    set_config_manager,
)


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
DEFAULT_LANGUAGE = os.getenv('DEFAULT_LANGUAGE', 'en')
FALLBACK_LANGUAGE = os.getenv('FALLBACK_LANGUAGE', 'en')
TRANSLATIONS_PATH = os.getenv('TRANSLATIONS_PATH', 'translations')
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
                 'DB_NAME', 'DB_USERNAME', 'DB_PASSWORD', 'NEW_VAR',
                 'DEFAULT_LANGUAGE', 'FALLBACK_LANGUAGE', 'TRANSLATIONS_PATH']
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


# ============================================================================
# Test Config Module Loading
# ============================================================================

class TestModuleLoading:
    """Test config module loading."""

    def test_load_valid_module(self, clean_env, temp_config_dir):
        """Should load valid config module."""
        import sys
        sys.path.insert(0, str(temp_config_dir.parent))

        try:
            manager = ConfigManager(
                modules=['app'],
                config_package='config',
                auto_load=False
            )
            manager.load()

            assert 'app' in manager._data
            assert manager._data['app']['APP_NAME'] == 'TestApp'
            assert manager._data['app']['VERSION'] == '1.0.0'
            assert manager._data['app']['PORT'] == 8000
        finally:
            sys.path.pop(0)

    def test_load_multiple_modules(self, clean_env, temp_config_dir):
        """Should load multiple config modules."""
        import sys
        sys.path.insert(0, str(temp_config_dir.parent))

        try:
            manager = ConfigManager(
                modules=['app', 'database'],
                auto_load=False
            )
            manager.load()

            assert 'app' in manager._data
            assert 'database' in manager._data
            assert manager._data['database']['MAX_CONNECTIONS'] == 10
        finally:
            sys.path.pop(0)

    def test_skip_private_attributes(self, clean_env, tmp_path):
        """Should skip private attributes (starting with _)."""
        config_dir = tmp_path / "testconfig"
        config_dir.mkdir()
        (config_dir / "__init__.py").write_text("")

        config_file = config_dir / "mymodule.py"
        config_file.write_text("""
PUBLIC_VAR = 'public'
_PRIVATE_VAR = 'private'
__DUNDER_VAR = 'dunder'
""")

        import sys
        sys.path.insert(0, str(tmp_path))

        try:
            manager = ConfigManager(
                modules=['mymodule'],
                config_package='testconfig',
                auto_load=False
            )
            manager.load()

            assert 'PUBLIC_VAR' in manager._data['mymodule']
            assert '_PRIVATE_VAR' not in manager._data['mymodule']
            assert '__DUNDER_VAR' not in manager._data['mymodule']
        finally:
            sys.path.pop(0)

    def test_skip_functions(self, clean_env, tmp_path):
        """Should skip functions but keep classes."""
        config_dir = tmp_path / "testconfig2"
        config_dir.mkdir()
        (config_dir / "__init__.py").write_text("")

        config_file = config_dir / "mymodule.py"
        config_file.write_text("""
VALUE = 'value'

def some_function():
    pass

class SomeClass:
    pass
""")

        import sys
        sys.path.insert(0, str(tmp_path))

        try:
            manager = ConfigManager(
                modules=['mymodule'],
                config_package='testconfig2',
                auto_load=False
            )
            manager.load()

            assert 'VALUE' in manager._data['mymodule']
            assert 'some_function' not in manager._data['mymodule']
            assert 'SomeClass' in manager._data['mymodule']
        finally:
            sys.path.pop(0)

    def test_module_not_found(self, clean_env):
        """Should handle missing module gracefully."""
        manager = ConfigManager(
            modules=['nonexistent_module_xyz'],
            auto_load=False
        )

        # Should not raise error, just log
        manager.load()

        assert 'nonexistent_module_xyz' not in manager._data


    def test_loaded_flag(self, clean_env):
        """Should set loaded flag after loading."""
        manager = ConfigManager(modules=[], auto_load=False)

        assert manager._loaded is False

        manager.load()

        assert manager._loaded is True


# ============================================================================
# Test Config Access (get)
# ============================================================================

class TestConfigGet:
    """Test config value retrieval."""

    def test_get_module_dict(self, clean_env, temp_config_dir):
        """Should get entire module as dict."""
        import sys
        sys.path.insert(0, str(temp_config_dir.parent))

        try:
            manager = ConfigManager(modules=['app'])
            result = manager.get('app')

            assert isinstance(result, dict)
            assert 'APP_NAME' in result
            assert 'VERSION' in result
        finally:
            sys.path.pop(0)

    def test_get_specific_key(self, clean_env, temp_config_dir):
        """Should get specific config value."""
        import sys
        sys.path.insert(0, str(temp_config_dir.parent))

        try:
            manager = ConfigManager(modules=['app'])
            value = manager.get('app.VERSION')

            assert value == '1.0.0'
        finally:
            sys.path.pop(0)

    def test_get_with_default(self, clean_env):
        """Should return default for missing key."""
        manager = ConfigManager(modules=[], auto_load=False)
        manager.load()

        value = manager.get('nonexistent.key', 'default_value')

        assert value == 'default_value'

    def test_get_missing_no_default(self, clean_env):
        """Should return None for missing key without default."""
        manager = ConfigManager(modules=[], auto_load=False)
        manager.load()

        value = manager.get('nonexistent.key')

        assert value is None

    def test_env_override_config(self, clean_env, temp_config_dir):
        """Should prioritize environment variable over config file."""
        import sys
        sys.path.insert(0, str(temp_config_dir.parent))

        # Set environment variable
        os.environ['APP_VERSION'] = 'env_version'

        try:
            manager = ConfigManager(modules=['app'])
            value = manager.get('app.VERSION')

            # Should get env value, not file value
            assert value == 'env_version'
        finally:
            sys.path.pop(0)
            del os.environ['APP_VERSION']

    def test_get_nested_dict(self, clean_env, temp_config_dir):
        """Should get nested dictionary values."""
        import sys
        sys.path.insert(0, str(temp_config_dir.parent))

        try:
            manager = ConfigManager(modules=['database'])
            connections = manager.get('database.CONNECTIONS')

            assert isinstance(connections, dict)
            assert 'default' in connections
            assert connections['default']['host'] == 'localhost'
        finally:
            sys.path.pop(0)


# ============================================================================
# Test Type Casting
# ============================================================================

class TestTypeCasting:
    """Test environment variable type casting."""

    def test_cast_to_boolean_true_variants(self, clean_env):
        """Should cast true variants to True."""
        manager = ConfigManager(modules=[], auto_load=False)

        true_values = ['true', 'True', 'TRUE', 'yes', 'Yes', '1']

        for value in true_values:
            result = manager._cast_value(value)
            assert result is True, f"Failed for: {value}"

    def test_cast_to_boolean_false_variants(self, clean_env):
        """Should cast false variants to False."""
        manager = ConfigManager(modules=[], auto_load=False)

        false_values = ['false', 'False', 'FALSE', 'no', 'No', '0']

        for value in false_values:
            result = manager._cast_value(value)
            assert result is False, f"Failed for: {value}"

    def test_cast_to_integer(self, clean_env):
        """Should cast numeric strings to int."""
        manager = ConfigManager(modules=[], auto_load=False)

        assert manager._cast_value('123') == 123
        assert manager._cast_value('0') == 0
        assert manager._cast_value('-456') == -456

    def test_cast_to_float(self, clean_env):
        """Should cast decimal strings to float."""
        manager = ConfigManager(modules=[], auto_load=False)

        assert manager._cast_value('123.45') == 123.45
        assert manager._cast_value('0.0') == 0.0
        assert manager._cast_value('-67.89') == -67.89

    def test_cast_string_unchanged(self, clean_env):
        """Should keep regular strings as strings."""
        manager = ConfigManager(modules=[], auto_load=False)

        assert manager._cast_value('hello') == 'hello'
        assert manager._cast_value('mixed123') == 'mixed123'
        assert manager._cast_value('') == ''


# ============================================================================
# Test Config Modification (set)
# ============================================================================

class TestConfigSet:
    """Test runtime config modification."""

    def test_set_new_value(self, clean_env):
        """Should set new config value."""
        manager = ConfigManager(modules=[], auto_load=False)
        manager.load()

        manager.set('app.NEW_KEY', 'new_value')

        assert manager.get('app.NEW_KEY') == 'new_value'

    def test_set_existing_value(self, clean_env, temp_config_dir):
        """Should override existing value."""
        import sys
        sys.path.insert(0, str(temp_config_dir.parent))

        try:
            manager = ConfigManager(modules=['app'])

            original = manager.get('app.VERSION')
            assert original == '1.0.0'

            manager.set('app.VERSION', '2.0.0')

            assert manager.get('app.VERSION') == '2.0.0'
        finally:
            sys.path.pop(0)

    def test_set_creates_module(self, clean_env):
        """Should create module if doesn't exist."""
        manager = ConfigManager(modules=[], auto_load=False)
        manager.load()

        manager.set('newmodule.KEY', 'value')

        assert 'newmodule' in manager._data
        assert manager.get('newmodule.KEY') == 'value'

    def test_set_invalid_key_format(self, clean_env):
        """Should raise error for invalid key format."""
        manager = ConfigManager(modules=[], auto_load=False)
        manager.load()

        with pytest.raises(ConfigurationError) as exc_info:
            manager.set('invalid_key', 'value')

        assert 'Invalid key format' in str(exc_info.value)
        assert 'module.key' in str(exc_info.value)


# ============================================================================
# Test Config Checking (has)
# ============================================================================

class TestConfigHas:
    """Test config key existence checking."""

    def test_has_existing_module(self, clean_env, temp_config_dir):
        """Should return True for existing module."""
        import sys
        sys.path.insert(0, str(temp_config_dir.parent))

        try:
            manager = ConfigManager(modules=['app'])

            assert manager.has('app') is True
        finally:
            sys.path.pop(0)

    def test_has_nonexistent_module(self, clean_env):
        """Should return False for nonexistent module."""
        manager = ConfigManager(modules=[], auto_load=False)
        manager.load()

        assert manager.has('nonexistent') is False

    def test_has_existing_key(self, clean_env, temp_config_dir):
        """Should return True for existing key."""
        import sys
        sys.path.insert(0, str(temp_config_dir.parent))

        try:
            manager = ConfigManager(modules=['app'])

            assert manager.has('app.VERSION') is True
        finally:
            sys.path.pop(0)

    def test_has_nonexistent_key(self, clean_env, temp_config_dir):
        """Should return False for nonexistent key."""
        import sys
        sys.path.insert(0, str(temp_config_dir.parent))

        try:
            manager = ConfigManager(modules=['app'])

            assert manager.has('app.NONEXISTENT') is False
        finally:
            sys.path.pop(0)


# ============================================================================
# Test Get All Config
# ============================================================================

class TestConfigAll:
    """Test retrieving all configuration."""

    def test_all_returns_copy(self, clean_env, temp_config_dir):
        """Should return copy of all config."""
        import sys
        sys.path.insert(0, str(temp_config_dir.parent))

        try:
            manager = ConfigManager(modules=['app'])

            all_config = manager.all()

            assert isinstance(all_config, dict)
            assert 'app' in all_config

            # Modify returned dict
            all_config['app']['VERSION'] = 'modified'

            # Original should be unchanged
            assert manager.get('app.VERSION') == '1.0.0'
        finally:
            sys.path.pop(0)

    def test_all_empty(self, clean_env):
        """Should return empty dict when no config loaded."""
        manager = ConfigManager(modules=[], config_package='empty', auto_load=False)
        manager.load()

        all_config = manager.all()

        assert all_config == {}


# ============================================================================
# Test Config Reload
# ============================================================================

class TestConfigReload:
    """Test configuration reloading."""

    def test_reload_clears_data(self, clean_env, temp_config_dir):
        """Should clear existing data on reload."""
        import sys
        sys.path.insert(0, str(temp_config_dir.parent))

        try:
            manager = ConfigManager(modules=['app'])

            # Modify config
            manager.set('app.CUSTOM', 'value')
            assert manager.has('app.CUSTOM')

            # Reload
            manager.reload()

            # Custom value should be gone
            assert not manager.has('app.CUSTOM')
            # But original should be reloaded
            assert manager.has('app.VERSION')
        finally:
            sys.path.pop(0)

    def test_reload_resets_loaded_flag(self, clean_env):
        """Should complete reload with loaded flag True."""
        manager = ConfigManager(modules=[], auto_load=False)
        manager.load()

        assert manager._loaded is True

        manager.reload()

        # After reload completes, should be True
        assert manager._loaded is True


# ============================================================================
# Test Default Manager (Convenience Functions)
# ============================================================================

class TestDefaultManager:
    """Test default manager and convenience functions."""

    def test_get_config_manager_creates_default(self, clean_env):
        """Should create default manager if doesn't exist."""
        manager = get_config_manager()

        assert manager is not None
        assert isinstance(manager, ConfigManager)

    def test_get_config_manager_returns_same(self, clean_env):
        """Should return same manager instance."""
        manager1 = get_config_manager()
        manager2 = get_config_manager()

        assert manager1 is manager2

    def test_set_config_manager(self, clean_env):
        """Should set custom default manager."""
        custom_manager = ConfigManager(
            modules=['custom'],
            auto_load=False
        )

        set_config_manager(custom_manager)

        assert get_config_manager() is custom_manager

    def test_config_function(self, clean_env, temp_config_dir):
        """Should get config via convenience function."""
        import sys
        sys.path.insert(0, str(temp_config_dir.parent))

        try:
            # Reset and create fresh manager
            set_config_manager(ConfigManager(modules=['app']))

            value = config('app.VERSION')

            assert value == '1.0.0'
        finally:
            sys.path.pop(0)

    def test_config_function_with_default(self, clean_env):
        """Should use default value via convenience function."""
        set_config_manager(ConfigManager(modules=[], auto_load=False))

        value = config('nonexistent.key', 'default')

        assert value == 'default'

    def test_config_set_function(self, clean_env):
        """Should set config via convenience function."""
        set_config_manager(ConfigManager(modules=[], auto_load=False))

        config_set('app.KEY', 'value')

        assert config('app.KEY') == 'value'

    def test_config_has_function(self, clean_env, temp_config_dir):
        """Should check existence via convenience function."""
        import sys
        sys.path.insert(0, str(temp_config_dir.parent))

        try:
            set_config_manager(ConfigManager(modules=['app']))

            assert config_has('app.VERSION') is True
            assert config_has('app.NONEXISTENT') is False
        finally:
            sys.path.pop(0)

    def test_config_all_function(self, clean_env, temp_config_dir):
        """Should get all config via convenience function."""
        import sys
        sys.path.insert(0, str(temp_config_dir.parent))

        try:
            set_config_manager(ConfigManager(modules=['app']))

            all_config = config_all()

            assert 'app' in all_config
        finally:
            sys.path.pop(0)

    def test_config_reload_function(self, clean_env, temp_config_dir):
        """Should reload via convenience function."""
        import sys
        sys.path.insert(0, str(temp_config_dir.parent))

        try:
            set_config_manager(ConfigManager(modules=['app']))

            config_set('app.CUSTOM', 'value')
            assert config_has('app.CUSTOM')

            config_reload()

            assert not config_has('app.CUSTOM')
        finally:
            sys.path.pop(0)


# ============================================================================
# Test Multiple Instances
# ============================================================================

class TestMultipleInstances:
    """Test multiple ConfigManager instances."""

    def test_independent_instances(self, clean_env, temp_config_dir):
        """Should maintain independent state per instance."""
        import sys
        sys.path.insert(0, str(temp_config_dir.parent))

        try:
            manager1 = ConfigManager(modules=['app'], auto_load=False)
            manager1.load()

            manager2 = ConfigManager(modules=[], auto_load=False)
            manager2.load()

            manager1.set('app.VALUE', 'instance1')
            manager2.set('app.VALUE', 'instance2')

            assert manager1.get('app.VALUE') == 'instance1'
            assert manager2.get('app.VALUE') == 'instance2'
        finally:
            sys.path.pop(0)

    def test_different_env_files(self, clean_env, tmp_path):
        """Should load different env files per instance."""
        env1 = tmp_path / ".env1"
        env1.write_text("VAR=env1")

        env2 = tmp_path / ".env2"
        env2.write_text("VAR=env2")

        manager1 = ConfigManager(modules=[], env_file=env1, auto_load=False)
        manager1._load_env()
        value1 = os.getenv('VAR')

        os.environ.pop('VAR', None)

        manager2 = ConfigManager(modules=[], env_file=env2, auto_load=False)
        manager2._load_env()
        value2 = os.getenv('VAR')

        # Each should have loaded their env file
        assert value2 == 'env2'


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_config_module(self, clean_env, tmp_path):
        """Should handle empty config module."""
        config_dir = tmp_path / "testconfig"
        config_dir.mkdir()
        (config_dir / "__init__.py").write_text("")
        (config_dir / "empty.py").write_text("")

        import sys
        sys.path.insert(0, str(tmp_path))

        try:
            manager = ConfigManager(
                modules=['empty'],
                config_package='testconfig'
            )
            assert 'empty' not in manager._data
        finally:
            sys.path.pop(0)

    def test_very_long_key_path(self, clean_env):
        """Should handle very long key paths."""
        manager = ConfigManager(modules=[], auto_load=False)
        manager.load()

        long_key = 'a' * 1000
        manager.set(f'module.{long_key}', 'value')

        assert manager.get(f'module.{long_key}') == 'value'

    def test_special_characters_in_values(self, clean_env):
        """Should handle special characters in values."""
        manager = ConfigManager(modules=[], auto_load=False)
        manager.load()

        special_value = '!@#$%^&*(){}[]|\\<>?,./"\':;'
        manager.set('app.SPECIAL', special_value)

        assert manager.get('app.SPECIAL') == special_value

    def test_unicode_in_values(self, clean_env):
        """Should handle Unicode in values."""
        manager = ConfigManager(modules=[], auto_load=False)
        manager.load()

        unicode_value = '你好世界 🌍 Привет مرحبا'
        manager.set('app.UNICODE', unicode_value)

        assert manager.get('app.UNICODE') == unicode_value

    def test_none_as_value(self, clean_env):
        """Should handle None as config value."""
        manager = ConfigManager(modules=[], auto_load=False)
        manager.load()

        manager.set('app.NULL_VALUE', None)

        assert manager.get('app.NULL_VALUE') is None

    def test_complex_nested_structures(self, clean_env):
        """Should handle complex nested data structures."""
        manager = ConfigManager(modules=[], auto_load=False)
        manager.load()

        complex_value = {
            'level1': {
                'level2': {
                    'level3': ['a', 'b', 'c']
                }
            }
        }

        manager.set('app.COMPLEX', complex_value)

        retrieved = manager.get('app.COMPLEX')
        assert retrieved == complex_value


# ============================================================================
# Test Integration Scenarios
# ============================================================================

class TestIntegration:
    """Test real-world integration scenarios."""

    def test_typical_app_usage(self, clean_env, temp_config_dir, temp_env_file):
        """Should work in typical application scenario."""
        import sys
        sys.path.insert(0, str(temp_config_dir.parent))

        try:
            # Simulate app startup
            manager = ConfigManager(
                modules=['app', 'database'],
                env_file=temp_env_file
            )

            # Access various config
            app_name = manager.get('app.APP_NAME')  # From env
            version = manager.get('app.VERSION')  # From file
            db_connections = manager.get('database.CONNECTIONS')
            db_host = db_connections['default']['host']  # From env

            assert app_name == 'TestApp'
            assert version == '1.0.0'
            assert db_host == 'localhost'
        finally:
            sys.path.pop(0)

    def test_testing_environment(self, clean_env, tmp_path):
        """Should support separate test configuration."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "__init__.py").write_text("")

        # Production config
        (config_dir / "app.py").write_text("ENV = 'production'")

        # Test env file
        test_env = tmp_path / ".env.test"
        test_env.write_text("APP_ENV=test")

        import sys
        sys.path.insert(0, str(tmp_path))

        try:
            # Test config instance
            test_config = ConfigManager(
                modules=['app'],
                env_file=test_env
            )

            assert os.getenv('APP_ENV') == 'test'
        finally:
            sys.path.pop(0)