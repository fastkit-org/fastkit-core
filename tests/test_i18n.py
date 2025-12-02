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