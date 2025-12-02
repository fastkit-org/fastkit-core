"""
Comprehensive tests for FastKit Core i18n (Internationalization) module.

Tests TranslationManager with all features:
- Translation file loading
- Dot notation access
- Variable replacement
- Locale management
- Fallback behavior
- Context integration
- Helper functions

Target Coverage: 95%+
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from contextvars import ContextVar

from fastkit_core.i18n import (
    TranslationManager,
    get_translation_manager,
    set_translation_manager,
    _,
    gettext,
    set_locale,
    get_locale,
)
from fastkit_core.config import ConfigManager, set_config_manager


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def translations_dir(tmp_path):
    """Create temporary translations directory with test files."""
    trans_dir = tmp_path / "translations"
    trans_dir.mkdir()

    # English translations
    en_content = {
        "messages": {
            "welcome": "Welcome!",
            "hello": "Hello, {name}!",
            "goodbye": "Goodbye, {name}!",
            "items": "{count} item|{count} items"
        },
        "errors": {
            "not_found": "Not found",
            "server_error": "Server error"
        },
        "validation": {
            "required": "The {field} field is required",
            "email": "The {field} must be a valid email"
        },
        "nested": {
            "level1": {
                "level2": {
                    "deep": "Deep value"
                }
            }
        }
    }

    with open(trans_dir / "en.json", "w", encoding="utf-8") as f:
        json.dump(en_content, f, ensure_ascii=False, indent=2)

    # Spanish translations
    es_content = {
        "messages": {
            "welcome": "¡Bienvenido!",
            "hello": "¡Hola, {name}!",
            "goodbye": "¡Adiós, {name}!",
            "items": "{count} artículo|{count} artículos"
        },
        "errors": {
            "not_found": "No encontrado",
            "server_error": "Error del servidor"
        },
        "validation": {
            "required": "El campo {field} es obligatorio",
            "email": "El campo {field} debe ser un correo válido"
        }
    }

    with open(trans_dir / "es.json", "w", encoding="utf-8") as f:
        json.dump(es_content, f, ensure_ascii=False, indent=2)

    # French translations (partial - for fallback testing)
    fr_content = {
        "messages": {
            "welcome": "Bienvenue!",
            "hello": "Bonjour, {name}!"
        }
    }

    with open(trans_dir / "fr.json", "w", encoding="utf-8") as f:
        json.dump(fr_content, f, ensure_ascii=False, indent=2)

    return trans_dir


@pytest.fixture
def config_with_translations(translations_dir):
    """Create config manager with translations path."""
    config = ConfigManager(modules=[], auto_load=False)
    config.load()
    config.set('app.TRANSLATIONS_PATH', str(translations_dir))
    config.set('app.DEFAULT_LANGUAGE', 'en')
    config.set('app.FALLBACK_LANGUAGE', 'en')
    set_config_manager(config)
    return config


@pytest.fixture(autouse=True)
def reset_translation_manager():
    """Reset global translation manager before each test."""
    from fastkit_core import i18n
    i18n._translation_manager = None

    # Reset locale context
    from fastkit_core.i18n.translation import _current_locale
    _current_locale.set(None)

    yield

    i18n._translation_manager = None
    _current_locale.set(None)


@pytest.fixture
def manager(config_with_translations, translations_dir):
    """Create TranslationManager instance."""
    return TranslationManager(translations_dir=translations_dir)


# ============================================================================
# Test TranslationManager Initialization
# ============================================================================

class TestTranslationManagerInit:
    """Test TranslationManager initialization."""

    def test_init_with_explicit_path(self, translations_dir):
        """Should initialize with explicit translations directory."""
        manager = TranslationManager(translations_dir=translations_dir)

        assert manager.translations_dir == translations_dir
        assert len(manager._translations) > 0

    def test_init_from_config(self, config_with_translations):
        """Should load translations path from config."""
        manager = TranslationManager()

        assert manager.translations_dir.exists()
        assert len(manager._translations) > 0

    def test_init_default_locale_from_config(self, config_with_translations):
        """Should load default locale from config."""
        manager = TranslationManager()

        assert manager.default_locale == 'en'

    def test_init_fallback_locale_from_config(self, config_with_translations):
        """Should load fallback locale from config."""
        manager = TranslationManager()

        assert manager.fallback_locale == 'en'

    def test_init_nonexistent_directory(self, tmp_path):
        """Should handle nonexistent translations directory."""
        nonexistent = tmp_path / "nonexistent"
        manager = TranslationManager(translations_dir=nonexistent)

        assert manager._translations == {}

    def test_load_multiple_locales(self, manager):
        """Should load all locale files."""
        assert 'en' in manager._translations
        assert 'es' in manager._translations
        assert 'fr' in manager._translations


# ============================================================================
# Test Translation File Loading
# ============================================================================

class TestTranslationLoading:
    """Test translation file loading."""

    def test_load_valid_json(self, manager):
        """Should load valid JSON files."""
        assert 'messages' in manager._translations['en']
        assert 'errors' in manager._translations['en']

    def test_load_utf8_content(self, manager):
        """Should handle UTF-8 content correctly."""
        welcome_es = manager._translations['es']['messages']['welcome']
        assert '¡' in welcome_es
        assert 'Bienvenido' in welcome_es

    def test_load_nested_structure(self, manager):
        """Should load nested JSON structure."""
        nested = manager._translations['en']['nested']
        assert 'level1' in nested
        assert 'level2' in nested['level1']
        assert 'deep' in nested['level1']['level2']

    def test_load_invalid_json(self, tmp_path, config_with_translations):
        """Should handle invalid JSON gracefully."""
        trans_dir = tmp_path / "bad_translations"
        trans_dir.mkdir()

        # Create invalid JSON file
        bad_file = trans_dir / "bad.json"
        bad_file.write_text("{invalid json content!!!")

        manager = TranslationManager(translations_dir=trans_dir)

        # Should not have loaded bad file
        assert 'bad' not in manager._translations

    def test_load_empty_json_file(self, tmp_path, config_with_translations):
        """Should handle empty JSON file."""
        trans_dir = tmp_path / "empty_translations"
        trans_dir.mkdir()

        empty_file = trans_dir / "empty.json"
        empty_file.write_text("{}")

        manager = TranslationManager(translations_dir=trans_dir)

        assert 'empty' in manager._translations
        assert manager._translations['empty'] == {}

    def test_ignore_non_json_files(self, tmp_path, config_with_translations):
        """Should ignore non-JSON files."""
        trans_dir = tmp_path / "mixed_translations"
        trans_dir.mkdir()

        # Create JSON file
        (trans_dir / "en.json").write_text('{"test": "value"}')

        # Create non-JSON files
        (trans_dir / "readme.txt").write_text("readme")
        (trans_dir / "config.yaml").write_text("test: value")

        manager = TranslationManager(translations_dir=trans_dir)

        assert 'en' in manager._translations
        assert 'readme' not in manager._translations
        assert 'config' not in manager._translations


# ============================================================================
# Test Translation Retrieval (get)
# ============================================================================

class TestTranslationGet:
    """Test translation retrieval."""

    def test_get_simple_key(self, manager):
        """Should get simple translation."""
        result = manager.get('messages.welcome', locale='en')
        assert result == "Welcome!"

    def test_get_with_dot_notation(self, manager):
        """Should access nested keys with dot notation."""
        result = manager.get('errors.not_found', locale='en')
        assert result == "Not found"

    def test_get_deeply_nested(self, manager):
        """Should access deeply nested keys."""
        result = manager.get('nested.level1.level2.deep', locale='en')
        assert result == "Deep value"

    def test_get_nonexistent_key(self, manager):
        """Should return key if translation not found."""
        result = manager.get('nonexistent.key', locale='en')
        assert result == 'nonexistent.key'

    def test_get_with_variable_replacement(self, manager):
        """Should replace variables in translation."""
        result = manager.get('messages.hello', locale='en', name='John')
        assert result == "Hello, John!"

    def test_get_with_multiple_variables(self, manager):
        """Should replace multiple variables."""
        # Add translation with multiple variables
        manager._translations['en']['test'] = {'multi': '{first} and {second}'}

        result = manager.get('test.multi', locale='en', first='A', second='B')
        assert result == "A and B"

    def test_get_with_missing_variable(self, manager):
        """Should handle missing variable gracefully."""
        result = manager.get('messages.hello', locale='en')
        # Should still return string with placeholder
        assert '{name}' in result

    def test_get_different_locales(self, manager):
        """Should get translations for different locales."""
        en_result = manager.get('messages.welcome', locale='en')
        es_result = manager.get('messages.welcome', locale='es')

        assert en_result == "Welcome!"
        assert es_result == "¡Bienvenido!"

    def test_get_uses_current_locale(self, manager):
        """Should use current context locale if not specified."""
        manager.set_locale('es')
        result = manager.get('messages.welcome')
        assert result == "¡Bienvenido!"

    def test_get_uses_default_locale(self, manager):
        """Should use default locale if no context locale set."""
        result = manager.get('messages.welcome')
        assert result == "Welcome!"